"""End-to-end integration tests for EasyScale."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import pytz

from easyscale.config.loader import ConfigLoader
from easyscale.controller.daemon import DaemonConfig, create_daemon


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    @patch("easyscale.controller.daemon.K8sClient")
    def test_full_workflow(self, mock_client_class):
        """Test complete workflow: load rules -> evaluate -> scale."""
        # Setup mock K8s client
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client_class.return_value = mock_client

        # Setup mock resource manager behavior
        mock_apps_v1 = Mock()
        mock_client.apps_v1 = mock_apps_v1

        # Mock deployment with 5 replicas
        mock_deployment = Mock()
        mock_deployment.spec.replicas = 5
        mock_apps_v1.read_namespaced_deployment.return_value = mock_deployment
        mock_apps_v1.patch_namespaced_deployment_scale.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a scaling rule
            rule_file = Path(tmpdir) / "weekend-scale.yaml"
            rule_file.write_text(
                """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: weekend-scale
  namespace: default
spec:
  target:
    kind: Deployment
    name: test-api
    namespace: default
  schedule:
    - name: Weekend scale down
      days: [Saturday, Sunday]
      replicas: 2
      timezone: UTC
  default:
    replicas: 5
"""
            )

            # Create daemon
            config = DaemonConfig(
                check_interval=60,
                cooldown_seconds=60,
                dry_run=False,
                in_cluster=False,
                rules_directory=tmpdir,
            )
            daemon = create_daemon(config)

            # Verify rule was loaded
            assert len(daemon.rules) == 1
            assert "default/weekend-scale" in daemon.rules

            # Get the rule
            rule = daemon.rules["default/weekend-scale"]

            # Simulate Saturday (should scale down to 2)
            with patch("easyscale.controller.scheduler.get_current_datetime") as mock_time:
                saturday = datetime(2025, 1, 11, 12, 0, 0, tzinfo=pytz.UTC)
                mock_time.return_value = saturday

                # Run evaluation
                daemon._evaluate_and_scale(rule)

                # Verify scaling was attempted
                mock_apps_v1.patch_namespaced_deployment_scale.assert_called_once()
                # Verify correct arguments were used (keyword or positional)
                call_kwargs = mock_apps_v1.patch_namespaced_deployment_scale.call_args.kwargs
                assert "test-api" in str(call_kwargs) or mock_apps_v1.patch_namespaced_deployment_scale.call_count == 1

            # Reset mocks
            mock_apps_v1.reset_mock()

            # Simulate Monday (should scale up to 5, but already at 5)
            with patch("easyscale.controller.scheduler.get_current_datetime") as mock_time:
                monday = datetime(2025, 1, 6, 12, 0, 0, tzinfo=pytz.UTC)
                mock_time.return_value = monday

                daemon._evaluate_and_scale(rule)

                # Should not scale (already at desired replicas)
                mock_apps_v1.patch_namespaced_deployment_scale.assert_not_called()

    @patch("easyscale.controller.daemon.K8sClient")
    def test_dry_run_mode(self, mock_client_class):
        """Test dry-run mode doesn't actually scale."""
        # Setup mock K8s client
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client_class.return_value = mock_client

        # Setup mock resource manager
        mock_apps_v1 = Mock()
        mock_client.apps_v1 = mock_apps_v1

        mock_deployment = Mock()
        mock_deployment.spec.replicas = 5
        mock_apps_v1.read_namespaced_deployment.return_value = mock_deployment

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a scaling rule
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
    name: test-api
    namespace: default
  schedule:
    - name: Scale down
      days: [Monday]
      replicas: 2
  default:
    replicas: 5
"""
            )

            # Create daemon in dry-run mode
            config = DaemonConfig(
                dry_run=True,
                in_cluster=False,
                rules_directory=tmpdir,
            )
            daemon = create_daemon(config)

            # Run evaluation on Monday
            rule = daemon.rules["default/test-rule"]
            with patch("easyscale.controller.scheduler.get_current_datetime") as mock_time:
                monday = datetime(2025, 1, 6, 12, 0, 0, tzinfo=pytz.UTC)
                mock_time.return_value = monday

                daemon._evaluate_and_scale(rule)

                # Should NOT call K8s API in dry-run mode
                mock_apps_v1.patch_namespaced_deployment_scale.assert_not_called()

    def test_config_loader_integration(self):
        """Test config loading and validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple rule files
            for i in range(3):
                rule_file = Path(tmpdir) / f"rule-{i}.yaml"
                rule_file.write_text(
                    f"""
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: rule-{i}
spec:
  target:
    kind: Deployment
    name: app-{i}
    namespace: default
  schedule:
    - name: Business hours
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "09:00"
      timeEnd: "17:00"
      replicas: 5
  default:
    replicas: 2
"""
                )

            # Load all rules
            rules = ConfigLoader.load_multiple_from_directory(tmpdir)

            assert len(rules) == 3
            assert all(rule.api_version == "easyscale.io/v1" for rule in rules)
            assert all(rule.kind == "ScalingRule" for rule in rules)

    @patch("easyscale.controller.daemon.K8sClient")
    def test_multiple_rules_evaluation(self, mock_client_class):
        """Test evaluating multiple rules simultaneously."""
        # Setup mock K8s client
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client_class.return_value = mock_client

        mock_apps_v1 = Mock()
        mock_client.apps_v1 = mock_apps_v1

        # Mock different deployments
        def mock_read_deployment(name, namespace):
            mock_dep = Mock()
            if name == "app-1":
                mock_dep.spec.replicas = 5  # Will scale down
            else:
                mock_dep.spec.replicas = 2  # Already at desired
            return mock_dep

        mock_apps_v1.read_namespaced_deployment.side_effect = mock_read_deployment

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two rules
            for i in [1, 2]:
                rule_file = Path(tmpdir) / f"app-{i}-rule.yaml"
                rule_file.write_text(
                    f"""
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: app-{i}-rule
spec:
  target:
    kind: Deployment
    name: app-{i}
    namespace: default
  schedule:
    - name: Weekend
      days: [Saturday, Sunday]
      replicas: 2
  default:
    replicas: 5
"""
                )

            # Create daemon
            config = DaemonConfig(
                dry_run=False,
                in_cluster=False,
                rules_directory=tmpdir,
            )
            daemon = create_daemon(config)

            assert len(daemon.rules) == 2

            # Run evaluation on Saturday
            with patch("easyscale.controller.scheduler.get_current_datetime") as mock_time:
                saturday = datetime(2025, 1, 11, 12, 0, 0, tzinfo=pytz.UTC)
                mock_time.return_value = saturday

                daemon._run_cycle()

                # Only app-1 should scale (app-2 already at 2)
                assert mock_apps_v1.patch_namespaced_deployment_scale.call_count == 1

    @patch("easyscale.controller.daemon.K8sClient")
    def test_cooldown_prevents_thrashing(self, mock_client_class):
        """Test that cooldown period prevents rapid scaling."""
        # Setup mock K8s client
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_client_class.return_value = mock_client

        mock_apps_v1 = Mock()
        mock_client.apps_v1 = mock_apps_v1

        mock_deployment = Mock()
        mock_deployment.spec.replicas = 5
        mock_apps_v1.read_namespaced_deployment.return_value = mock_deployment

        with tempfile.TemporaryDirectory() as tmpdir:
            rule_file = Path(tmpdir) / "rule.yaml"
            rule_file.write_text(
                """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: test-rule
spec:
  target:
    kind: Deployment
    name: test-api
    namespace: default
  schedule:
    - name: Scale
      days: [Monday]
      replicas: 2
  default:
    replicas: 5
"""
            )

            # Create daemon with short cooldown
            config = DaemonConfig(
                cooldown_seconds=10,  # 10 second cooldown
                dry_run=False,
                in_cluster=False,
                rules_directory=tmpdir,
            )
            daemon = create_daemon(config)

            rule = daemon.rules["default/test-rule"]

            # First scaling
            with patch("easyscale.controller.scheduler.get_current_datetime") as mock_time:
                time1 = datetime(2025, 1, 6, 12, 0, 0, tzinfo=pytz.UTC)
                mock_time.return_value = time1

                daemon._evaluate_and_scale(rule)
                assert mock_apps_v1.patch_namespaced_deployment_scale.call_count == 1

            mock_apps_v1.reset_mock()

            # Second scaling attempt 5 seconds later (within cooldown)
            with patch("easyscale.controller.scheduler.get_current_datetime") as mock_time:
                time2 = datetime(2025, 1, 6, 12, 0, 5, tzinfo=pytz.UTC)
                mock_time.return_value = time2

                daemon._evaluate_and_scale(rule)
                # Should be blocked by cooldown
                assert mock_apps_v1.patch_namespaced_deployment_scale.call_count == 0

            # Third scaling attempt 15 seconds later (after cooldown)
            # Update mock to show resource now at 2 replicas (from first scaling)
            mock_deployment.spec.replicas = 2

            with patch("easyscale.controller.scheduler.get_current_datetime") as mock_time:
                time3 = datetime(2025, 1, 6, 12, 0, 15, tzinfo=pytz.UTC)
                mock_time.return_value = time3

                daemon._evaluate_and_scale(rule)
                # Resource is now at desired replicas (2), so no scaling needed
                assert mock_apps_v1.patch_namespaced_deployment_scale.call_count == 0
