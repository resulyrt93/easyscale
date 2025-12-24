"""Tests for daemon controller."""

import signal
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import pytz

from easyscale.config.models import (
    DayOfWeek,
    DefaultConfig,
    Metadata,
    ScalingRule,
    ScalingSpec,
    ScheduleRule,
    TargetResource,
)
from easyscale.controller.daemon import DaemonConfig, EasyScaleDaemon, create_daemon
from easyscale.k8s.client import K8sClient
from easyscale.utils.state import StateManager


class TestDaemonConfig:
    """Tests for DaemonConfig."""

    def test_default_config(self):
        """Test default daemon configuration."""
        config = DaemonConfig()

        assert config.check_interval == 60
        assert config.cooldown_seconds == 60
        assert config.dry_run is False
        assert config.in_cluster is True
        assert config.rules_directory is None

    def test_custom_config(self):
        """Test custom daemon configuration."""
        config = DaemonConfig(
            check_interval=30,
            cooldown_seconds=120,
            dry_run=True,
            in_cluster=False,
            rules_directory="/etc/easyscale/rules",
        )

        assert config.check_interval == 30
        assert config.cooldown_seconds == 120
        assert config.dry_run is True
        assert config.in_cluster is False
        assert config.rules_directory == "/etc/easyscale/rules"


class TestEasyScaleDaemon:
    """Tests for EasyScaleDaemon."""

    @pytest.fixture
    def mock_k8s_client(self):
        """Create a mock Kubernetes client."""
        client = Mock(spec=K8sClient)
        client.test_connection.return_value = True
        return client

    @pytest.fixture
    def state_manager(self):
        """Create a state manager."""
        return StateManager(cooldown_seconds=60)

    @pytest.fixture
    def daemon(self, mock_k8s_client, state_manager):
        """Create a daemon instance."""
        return EasyScaleDaemon(
            k8s_client=mock_k8s_client,
            state_manager=state_manager,
            check_interval=60,
            dry_run=False,
        )

    @pytest.fixture
    def sample_rule(self):
        """Create a sample scaling rule."""
        return ScalingRule(
            metadata=Metadata(name="test-rule", namespace="default"),
            spec=ScalingSpec(
                target=TargetResource(
                    kind="Deployment", name="test-deployment", namespace="default"
                ),
                schedule=[
                    ScheduleRule(
                        name="Weekend scale down",
                        days=[DayOfWeek.SATURDAY, DayOfWeek.SUNDAY],
                        replicas=2,
                        timezone="UTC",
                    )
                ],
                default=DefaultConfig(replicas=5),
            ),
        )

    def test_init(self, daemon, mock_k8s_client, state_manager):
        """Test daemon initialization."""
        assert daemon.k8s_client == mock_k8s_client
        assert daemon.state_manager == state_manager
        assert daemon.check_interval == 60
        assert daemon.dry_run is False
        assert len(daemon.rules) == 0
        assert daemon._shutdown is False

    def test_add_rule(self, daemon, sample_rule):
        """Test adding a rule."""
        result = daemon.add_rule(sample_rule)

        assert result is True
        assert len(daemon.rules) == 1
        assert "default/test-rule" in daemon.rules

    def test_add_invalid_rule(self, daemon):
        """Test adding an invalid rule with invalid timezone."""
        # Create rule with invalid timezone (will pass Pydantic but fail ConfigValidator)
        invalid_rule = ScalingRule(
            metadata=Metadata(name="invalid-rule", namespace="default"),
            spec=ScalingSpec(
                target=TargetResource(
                    kind="Deployment", name="test", namespace="default"
                ),
                schedule=[
                    ScheduleRule(
                        name="Invalid timezone",
                        days=[DayOfWeek.MONDAY],
                        replicas=3,
                        timezone="Invalid/Timezone",  # Invalid timezone
                    )
                ],
                default=DefaultConfig(replicas=5),
            ),
        )

        result = daemon.add_rule(invalid_rule)
        assert result is False
        assert len(daemon.rules) == 0

    def test_remove_rule(self, daemon, sample_rule):
        """Test removing a rule."""
        daemon.add_rule(sample_rule)
        assert len(daemon.rules) == 1

        result = daemon.remove_rule("test-rule", "default")
        assert result is True
        assert len(daemon.rules) == 0

    def test_remove_nonexistent_rule(self, daemon):
        """Test removing a rule that doesn't exist."""
        result = daemon.remove_rule("nonexistent", "default")
        assert result is False

    def test_get_rule_key(self, daemon, sample_rule):
        """Test getting rule key."""
        key = daemon._get_rule_key(sample_rule)
        assert key == "default/test-rule"

    def test_health_check(self, daemon):
        """Test health check."""
        health = daemon.health_check()

        assert health["status"] == "healthy"
        assert health["rules_count"] == 0
        assert health["dry_run"] is False
        assert health["check_interval"] == 60

    def test_health_check_shutdown(self, daemon):
        """Test health check when shutting down."""
        daemon._shutdown = True
        health = daemon.health_check()

        assert health["status"] == "shutting_down"

    @patch("easyscale.controller.daemon.time.sleep")
    def test_run_single_cycle(self, mock_sleep, daemon, sample_rule):
        """Test running a single evaluation cycle."""
        # Add a rule
        daemon.add_rule(sample_rule)

        # Mock resource manager
        daemon.resource_manager.resource_exists = Mock(return_value=True)
        daemon.resource_manager.get_current_replicas = Mock(return_value=5)

        # Make daemon shutdown after first cycle
        def stop_daemon(*args):
            daemon._shutdown = True

        mock_sleep.side_effect = stop_daemon

        # Run daemon
        daemon.run()

        # Verify it ran
        assert mock_sleep.called

    def test_evaluate_and_scale(self, daemon, sample_rule):
        """Test evaluating and scaling a rule."""
        # Add rule
        daemon.add_rule(sample_rule)

        # Mock resource manager
        daemon.resource_manager.resource_exists = Mock(return_value=True)
        daemon.resource_manager.get_current_replicas = Mock(return_value=5)
        daemon.resource_manager.scale_resource = Mock(return_value=True)

        # Evaluate on a Saturday (should scale down)
        with patch("easyscale.controller.scheduler.get_current_datetime") as mock_time:
            saturday = datetime(2025, 1, 11, 12, 0, 0, tzinfo=pytz.UTC)  # Saturday
            mock_time.return_value = saturday

            daemon._evaluate_and_scale(sample_rule)

            # Should have tried to scale to 2 replicas
            daemon.resource_manager.scale_resource.assert_called_once_with(
                kind="Deployment",
                name="test-deployment",
                namespace="default",
                replicas=2,
                dry_run=False,
            )

    def test_evaluate_and_scale_error_handling(self, daemon, sample_rule):
        """Test error handling during evaluation."""
        # Add rule
        daemon.add_rule(sample_rule)

        # Mock resource manager to raise exception
        daemon.resource_manager.resource_exists = Mock(
            side_effect=Exception("API error")
        )

        # Should not raise exception, just log error
        daemon._evaluate_and_scale(sample_rule)

    def test_load_rules_from_directory(self, daemon):
        """Test loading rules from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test rule file
            rule_file = Path(tmpdir) / "test-rule.yaml"
            rule_file.write_text(
                """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: test-rule
  namespace: default
spec:
  target:
    kind: Deployment
    name: test-deployment
    namespace: default
  schedule:
    - name: Weekend scale down
      days: [Saturday, Sunday]
      replicas: 2
  default:
    replicas: 5
"""
            )

            count = daemon.load_rules_from_directory(tmpdir)
            assert count == 1
            assert len(daemon.rules) == 1

    def test_load_rules_from_empty_directory(self, daemon):
        """Test loading rules from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            count = daemon.load_rules_from_directory(tmpdir)
            assert count == 0
            assert len(daemon.rules) == 0

    def test_signal_handler(self, daemon):
        """Test signal handler."""
        assert daemon._shutdown is False

        # Simulate SIGTERM
        daemon._handle_shutdown(signal.SIGTERM, None)

        assert daemon._shutdown is True

    def test_dry_run_mode(self, mock_k8s_client, state_manager):
        """Test daemon in dry-run mode."""
        daemon = EasyScaleDaemon(
            k8s_client=mock_k8s_client,
            state_manager=state_manager,
            check_interval=60,
            dry_run=True,
        )

        assert daemon.dry_run is True
        assert daemon.executor.dry_run is True


class TestCreateDaemon:
    """Tests for create_daemon function."""

    @patch("easyscale.controller.daemon.K8sClient")
    def test_create_daemon_basic(self, mock_client_class):
        """Test creating a daemon with basic config."""
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client_class.return_value = mock_client

        config = DaemonConfig()
        daemon = create_daemon(config)

        assert isinstance(daemon, EasyScaleDaemon)
        assert daemon.check_interval == 60
        assert daemon.dry_run is False

    @patch("easyscale.controller.daemon.K8sClient")
    def test_create_daemon_connection_failure(self, mock_client_class):
        """Test daemon creation with connection failure."""
        mock_client = Mock()
        mock_client.test_connection.return_value = False
        mock_client_class.return_value = mock_client

        config = DaemonConfig()

        with pytest.raises(RuntimeError, match="Cannot connect to Kubernetes API"):
            create_daemon(config)

    @patch("easyscale.controller.daemon.K8sClient")
    def test_create_daemon_with_rules_directory(self, mock_client_class):
        """Test creating daemon with rules directory."""
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client_class.return_value = mock_client

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test rule file
            rule_file = Path(tmpdir) / "test-rule.yaml"
            rule_file.write_text(
                """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: test-rule
spec:
  target:
    kind: Deployment
    name: test-deployment
    namespace: default
  schedule:
    - name: Test rule
      days: [Monday]
      replicas: 3
  default:
    replicas: 5
"""
            )

            config = DaemonConfig(rules_directory=tmpdir)
            daemon = create_daemon(config)

            assert len(daemon.rules) == 1
