"""Scaling executor for EasyScale."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from easyscale.controller.scheduler import ScheduleResult
from easyscale.k8s.resource_manager import ResourceManager
from easyscale.utils.state import StateManager

logger = logging.getLogger(__name__)


@dataclass
class ScalingDecision:
    """Decision about whether to scale a resource."""

    should_scale: bool
    current_replicas: int
    desired_replicas: int
    reason: str
    rule_name: Optional[str] = None
    in_cooldown: bool = False


class ScalingExecutor:
    """Executes scaling operations."""

    def __init__(
        self,
        resource_manager: ResourceManager,
        state_manager: StateManager,
        dry_run: bool = False,
    ):
        """
        Initialize scaling executor.

        Args:
            resource_manager: K8s resource manager
            state_manager: State manager for tracking operations
            dry_run: If True, don't actually scale resources
        """
        self.resource_manager = resource_manager
        self.state_manager = state_manager
        self.dry_run = dry_run

    def make_decision(
        self,
        namespace: str,
        name: str,
        kind: str,
        schedule_result: ScheduleResult,
        current_time: datetime,
    ) -> ScalingDecision:
        """
        Decide whether to scale a resource.

        Args:
            namespace: Kubernetes namespace
            name: Resource name
            kind: Resource kind (Deployment or StatefulSet)
            schedule_result: Result from rule evaluation
            current_time: Current time for cooldown check

        Returns:
            ScalingDecision with details about whether to scale
        """
        # Check if resource exists
        if not self.resource_manager.resource_exists(kind, name, namespace):
            return ScalingDecision(
                should_scale=False,
                current_replicas=0,
                desired_replicas=schedule_result.desired_replicas,
                reason=f"Resource {kind}/{namespace}/{name} does not exist",
            )

        # Get current replicas
        current_replicas = self.resource_manager.get_current_replicas(
            kind, name, namespace
        )

        # Check if already at desired replicas
        if current_replicas == schedule_result.desired_replicas:
            return ScalingDecision(
                should_scale=False,
                current_replicas=current_replicas,
                desired_replicas=schedule_result.desired_replicas,
                reason=f"Already at desired replicas ({current_replicas})",
                rule_name=(
                    schedule_result.matched_rule.name
                    if schedule_result.matched_rule
                    else None
                ),
            )

        # Check cooldown period
        if self.state_manager.is_in_cooldown(namespace, name, kind, current_time):
            return ScalingDecision(
                should_scale=False,
                current_replicas=current_replicas,
                desired_replicas=schedule_result.desired_replicas,
                reason="Resource is in cooldown period",
                rule_name=(
                    schedule_result.matched_rule.name
                    if schedule_result.matched_rule
                    else None
                ),
                in_cooldown=True,
            )

        # Should scale
        return ScalingDecision(
            should_scale=True,
            current_replicas=current_replicas,
            desired_replicas=schedule_result.desired_replicas,
            reason=schedule_result.reason,
            rule_name=(
                schedule_result.matched_rule.name
                if schedule_result.matched_rule
                else None
            ),
        )

    def execute(
        self,
        namespace: str,
        name: str,
        kind: str,
        decision: ScalingDecision,
        current_time: datetime,
    ) -> bool:
        """
        Execute a scaling operation.

        Args:
            namespace: Kubernetes namespace
            name: Resource name
            kind: Resource kind (Deployment or StatefulSet)
            decision: Scaling decision from make_decision()
            current_time: Current time for recording

        Returns:
            True if scaling was successful (or dry-run mode)
        """
        if not decision.should_scale:
            logger.debug(
                f"Skipping scaling for {kind}/{namespace}/{name}: {decision.reason}"
            )
            return False

        # Log scaling operation
        log_msg = (
            f"{'[DRY-RUN] ' if self.dry_run else ''}"
            f"Scaling {kind}/{namespace}/{name} "
            f"from {decision.current_replicas} to {decision.desired_replicas} replicas"
        )
        if decision.rule_name:
            log_msg += f" (rule: {decision.rule_name})"

        logger.info(log_msg)

        # Perform scaling
        success = True
        error = None

        if not self.dry_run:
            try:
                success = self.resource_manager.scale_resource(
                    kind=kind,
                    name=name,
                    namespace=namespace,
                    replicas=decision.desired_replicas,
                    dry_run=False,
                )
                if not success:
                    error = "Scaling operation returned False"
                    logger.error(f"Failed to scale {kind}/{namespace}/{name}")
            except Exception as e:
                success = False
                error = str(e)
                logger.error(
                    f"Error scaling {kind}/{namespace}/{name}: {e}", exc_info=True
                )

        # Record operation
        self.state_manager.record_scaling(
            namespace=namespace,
            name=name,
            kind=kind,
            rule_name=decision.rule_name,
            previous_replicas=decision.current_replicas,
            desired_replicas=decision.desired_replicas,
            reason=decision.reason,
            success=success,
            timestamp=current_time,
            error=error,
        )

        return success

    def process_schedule_result(
        self,
        namespace: str,
        name: str,
        kind: str,
        schedule_result: ScheduleResult,
        current_time: Optional[datetime] = None,
    ) -> bool:
        """
        Process a schedule result and execute scaling if needed.

        This is a convenience method that combines make_decision() and execute().

        Args:
            namespace: Kubernetes namespace
            name: Resource name
            kind: Resource kind (Deployment or StatefulSet)
            schedule_result: Result from rule evaluation
            current_time: Current time (defaults to schedule_result.evaluation_time)

        Returns:
            True if scaling was performed successfully
        """
        if current_time is None:
            current_time = schedule_result.evaluation_time

        decision = self.make_decision(namespace, name, kind, schedule_result, current_time)
        return self.execute(namespace, name, kind, decision, current_time)
