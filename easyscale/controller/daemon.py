"""Main daemon controller for EasyScale."""

import logging
import signal
import sys
import time
from datetime import datetime
from typing import Optional

import pytz

from easyscale.config.crd_loader import CRDLoader
from easyscale.config.loader import ConfigLoader
from easyscale.config.models import ScalingRule
from easyscale.config.validator import ConfigValidator
from easyscale.controller.scaler import ScalingExecutor
from easyscale.controller.scheduler import RuleEvaluator
from easyscale.k8s.client import K8sClient
from easyscale.k8s.resource_manager import ResourceManager
from easyscale.utils.state import StateManager
from easyscale.utils.time_utils import get_current_datetime

logger = logging.getLogger(__name__)


class EasyScaleDaemon:
    """Main daemon that manages scaling operations."""

    def __init__(
        self,
        k8s_client: K8sClient,
        state_manager: StateManager,
        check_interval: int = 60,
        dry_run: bool = False,
    ):
        """
        Initialize EasyScale daemon.

        Args:
            k8s_client: Kubernetes client
            state_manager: State manager for tracking operations
            check_interval: Seconds between evaluation cycles
            dry_run: If True, don't actually scale resources
        """
        self.k8s_client = k8s_client
        self.state_manager = state_manager
        self.check_interval = check_interval
        self.dry_run = dry_run

        self.resource_manager = ResourceManager(k8s_client)
        self.executor = ScalingExecutor(
            resource_manager=self.resource_manager,
            state_manager=state_manager,
            dry_run=dry_run,
        )

        # Scaling rules to monitor
        self.rules: dict[str, ScalingRule] = {}

        # Shutdown flag
        self._shutdown = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self._shutdown = True

    def load_rules_from_directory(self, directory: str) -> int:
        """
        Load scaling rules from a directory.

        Args:
            directory: Path to directory containing YAML files

        Returns:
            Number of rules loaded successfully
        """
        try:
            rules = ConfigLoader.load_multiple_from_directory(directory)
            loaded_count = 0

            for rule in rules:
                # Validate rule
                validation = ConfigValidator.validate(rule)
                if not validation.valid:
                    logger.error(
                        f"Invalid rule '{rule.metadata.name}': {validation.errors}"
                    )
                    continue

                if validation.warnings:
                    logger.warning(
                        f"Rule '{rule.metadata.name}' has warnings: {validation.warnings}"
                    )

                # Add to managed rules
                rule_key = self._get_rule_key(rule)
                self.rules[rule_key] = rule
                loaded_count += 1
                logger.info(f"Loaded rule: {rule.metadata.name}")

            logger.info(f"Successfully loaded {loaded_count}/{len(rules)} rules")
            return loaded_count

        except Exception as e:
            logger.error(f"Error loading rules from directory: {e}", exc_info=True)
            return 0

    def load_rules_from_crds(self, namespace: Optional[str] = None) -> int:
        """
        Load scaling rules from Kubernetes CRDs.

        Args:
            namespace: Optional namespace to filter rules. If None, loads from all namespaces.

        Returns:
            Number of rules loaded successfully
        """
        try:
            crd_loader = CRDLoader(self.k8s_client)
            rules = crd_loader.load_all_scaling_rules(namespace=namespace)
            loaded_count = 0

            for rule in rules:
                # Validate rule
                validation = ConfigValidator.validate(rule)
                if not validation.valid:
                    logger.error(
                        f"Invalid CRD rule '{rule.metadata.name}' in namespace '{rule.metadata.namespace}': {validation.errors}"
                    )
                    continue

                if validation.warnings:
                    logger.warning(
                        f"CRD rule '{rule.metadata.name}' in namespace '{rule.metadata.namespace}' has warnings: {validation.warnings}"
                    )

                # Add to managed rules
                rule_key = self._get_rule_key(rule)
                self.rules[rule_key] = rule
                loaded_count += 1
                logger.info(f"Loaded CRD rule: {rule.metadata.name} (namespace: {rule.metadata.namespace})")

            logger.info(f"Successfully loaded {loaded_count}/{len(rules)} CRD rules")
            return loaded_count

        except Exception as e:
            logger.error(f"Error loading rules from CRDs: {e}", exc_info=True)
            return 0

    def add_rule(self, rule: ScalingRule) -> bool:
        """
        Add a scaling rule to monitor.

        Args:
            rule: ScalingRule to add

        Returns:
            True if rule was added successfully
        """
        try:
            # Validate rule
            validation = ConfigValidator.validate(rule)
            if not validation.valid:
                logger.error(
                    f"Cannot add invalid rule '{rule.metadata.name}': {validation.errors}"
                )
                return False

            if validation.warnings:
                logger.warning(
                    f"Rule '{rule.metadata.name}' has warnings: {validation.warnings}"
                )

            rule_key = self._get_rule_key(rule)
            self.rules[rule_key] = rule
            logger.info(f"Added rule: {rule.metadata.name}")
            return True

        except Exception as e:
            logger.error(f"Error adding rule: {e}", exc_info=True)
            return False

    def remove_rule(self, name: str, namespace: str = "default") -> bool:
        """
        Remove a scaling rule.

        Args:
            name: Rule name
            namespace: Rule namespace

        Returns:
            True if rule was removed
        """
        rule_key = f"{namespace}/{name}"
        if rule_key in self.rules:
            del self.rules[rule_key]
            logger.info(f"Removed rule: {name} (namespace: {namespace})")
            return True
        return False

    def _get_rule_key(self, rule: ScalingRule) -> str:
        """Get unique key for a rule."""
        namespace = rule.metadata.namespace or "default"
        return f"{namespace}/{rule.metadata.name}"

    def _evaluate_and_scale(self, rule: ScalingRule) -> None:
        """
        Evaluate a single rule and execute scaling if needed.

        Args:
            rule: ScalingRule to evaluate
        """
        try:
            # Get target resource info
            target = rule.spec.target
            namespace = target.namespace
            name = target.name
            kind = target.kind

            # Evaluate schedule
            evaluator = RuleEvaluator(rule)
            schedule_result = evaluator.evaluate()

            # Log evaluation
            logger.debug(
                f"Rule '{rule.metadata.name}': {schedule_result.reason} "
                f"(desired: {schedule_result.desired_replicas} replicas)"
            )

            # Execute scaling
            success = self.executor.process_schedule_result(
                namespace=namespace,
                name=name,
                kind=kind,
                schedule_result=schedule_result,
            )

            if success:
                logger.info(
                    f"Scaled {kind}/{namespace}/{name} to {schedule_result.desired_replicas} replicas "
                    f"(rule: {rule.metadata.name})"
                )

        except Exception as e:
            logger.error(
                f"Error processing rule '{rule.metadata.name}': {e}", exc_info=True
            )

    def _run_cycle(self) -> None:
        """Run one evaluation cycle for all rules."""
        # Reload CRDs every cycle to pick up new/modified rules
        self.load_rules_from_crds()

        if not self.rules:
            logger.debug("No rules to evaluate")
            return

        logger.debug(f"Running evaluation cycle for {len(self.rules)} rules")
        start_time = time.time()

        for rule_key, rule in self.rules.items():
            self._evaluate_and_scale(rule)

        elapsed = time.time() - start_time
        logger.debug(f"Evaluation cycle completed in {elapsed:.2f}s")

    def run(self) -> None:
        """
        Run the daemon main loop.

        This will continuously evaluate rules and execute scaling operations
        until shutdown is requested.
        """
        logger.info(
            f"EasyScale daemon starting (check_interval={self.check_interval}s, "
            f"dry_run={self.dry_run})"
        )
        logger.info(f"Monitoring {len(self.rules)} scaling rules")

        cycle_count = 0

        while not self._shutdown:
            try:
                cycle_count += 1
                logger.debug(f"Starting evaluation cycle #{cycle_count}")

                self._run_cycle()

                # Sleep until next cycle
                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in daemon loop: {e}", exc_info=True)
                # Continue running even if there's an error
                time.sleep(self.check_interval)

        logger.info("EasyScale daemon shutting down")
        self._cleanup()

    def _cleanup(self) -> None:
        """Cleanup resources before shutdown."""
        logger.info("Performing cleanup...")
        # Add any cleanup logic here
        logger.info("Cleanup complete")

    def health_check(self) -> dict:
        """
        Get health status of the daemon.

        Returns:
            Dictionary with health information
        """
        return {
            "status": "healthy" if not self._shutdown else "shutting_down",
            "rules_count": len(self.rules),
            "dry_run": self.dry_run,
            "check_interval": self.check_interval,
        }


class DaemonConfig:
    """Configuration for the daemon."""

    def __init__(
        self,
        check_interval: int = 60,
        cooldown_seconds: int = 60,
        dry_run: bool = False,
        in_cluster: bool = True,
        rules_directory: Optional[str] = None,
    ):
        """
        Initialize daemon configuration.

        Args:
            check_interval: Seconds between evaluation cycles
            cooldown_seconds: Minimum seconds between scaling operations
            dry_run: If True, don't actually scale resources
            in_cluster: If True, use in-cluster Kubernetes config
            rules_directory: Directory containing scaling rule YAML files
        """
        self.check_interval = check_interval
        self.cooldown_seconds = cooldown_seconds
        self.dry_run = dry_run
        self.in_cluster = in_cluster
        self.rules_directory = rules_directory


def create_daemon(config: DaemonConfig) -> EasyScaleDaemon:
    """
    Create and configure an EasyScale daemon.

    Args:
        config: Daemon configuration

    Returns:
        Configured EasyScaleDaemon instance
    """
    # Initialize Kubernetes client
    logger.info(
        f"Initializing Kubernetes client (in_cluster={config.in_cluster})..."
    )
    k8s_client = K8sClient(in_cluster=config.in_cluster)

    # Test connection
    if not k8s_client.test_connection():
        logger.error("Failed to connect to Kubernetes API")
        raise RuntimeError("Cannot connect to Kubernetes API")

    logger.info("Successfully connected to Kubernetes API")

    # Initialize state manager
    state_manager = StateManager(cooldown_seconds=config.cooldown_seconds)

    # Create daemon
    daemon = EasyScaleDaemon(
        k8s_client=k8s_client,
        state_manager=state_manager,
        check_interval=config.check_interval,
        dry_run=config.dry_run,
    )

    # Load rules if directory specified
    if config.rules_directory:
        logger.info(f"Loading rules from directory: {config.rules_directory}")
        count = daemon.load_rules_from_directory(config.rules_directory)
        if count == 0:
            logger.warning("No rules were loaded successfully")

    return daemon
