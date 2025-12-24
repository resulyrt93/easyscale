"""Tests for scaling executor."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
import pytz

from easyscale.config.models import DayOfWeek, ScheduleRule
from easyscale.controller.scaler import ScalingDecision, ScalingExecutor
from easyscale.controller.scheduler import ScheduleResult
from easyscale.k8s.resource_manager import ResourceManager
from easyscale.utils.state import StateManager


class TestScalingDecision:
    """Tests for ScalingDecision dataclass."""

    def test_create_scaling_decision(self):
        """Test creating a scaling decision."""
        decision = ScalingDecision(
            should_scale=True,
            current_replicas=3,
            desired_replicas=5,
            reason="Scale up for peak hours",
            rule_name="peak-hours",
        )

        assert decision.should_scale is True
        assert decision.current_replicas == 3
        assert decision.desired_replicas == 5
        assert decision.reason == "Scale up for peak hours"
        assert decision.rule_name == "peak-hours"
        assert decision.in_cooldown is False

    def test_scaling_decision_no_scale(self):
        """Test scaling decision when no scaling needed."""
        decision = ScalingDecision(
            should_scale=False,
            current_replicas=5,
            desired_replicas=5,
            reason="Already at desired replicas (5)",
        )

        assert decision.should_scale is False
        assert decision.current_replicas == decision.desired_replicas


class TestScalingExecutor:
    """Tests for ScalingExecutor."""

    @pytest.fixture
    def mock_resource_manager(self):
        """Create a mock resource manager."""
        manager = Mock(spec=ResourceManager)
        manager.resource_exists.return_value = True
        manager.get_current_replicas.return_value = 3
        manager.scale_resource.return_value = True
        return manager

    @pytest.fixture
    def state_manager(self):
        """Create a state manager."""
        return StateManager(cooldown_seconds=60)

    @pytest.fixture
    def executor(self, mock_resource_manager, state_manager):
        """Create a scaling executor."""
        return ScalingExecutor(
            resource_manager=mock_resource_manager,
            state_manager=state_manager,
            dry_run=False,
        )

    @pytest.fixture
    def schedule_result(self):
        """Create a basic schedule result."""
        now = datetime.now(pytz.UTC)
        rule = ScheduleRule(
            name="test-rule",
            days=[DayOfWeek.MONDAY],
            replicas=5,
            timezone="UTC",
        )
        return ScheduleResult(
            desired_replicas=5,
            matched_rule=rule,
            reason="Matched rule: test-rule",
            evaluation_time=now,
        )

    def test_create_executor(self, mock_resource_manager, state_manager):
        """Test creating a scaling executor."""
        executor = ScalingExecutor(
            resource_manager=mock_resource_manager,
            state_manager=state_manager,
            dry_run=True,
        )

        assert executor.resource_manager == mock_resource_manager
        assert executor.state_manager == state_manager
        assert executor.dry_run is True

    def test_make_decision_resource_not_exists(self, executor, schedule_result):
        """Test making decision when resource doesn't exist."""
        executor.resource_manager.resource_exists.return_value = False
        now = datetime.now(pytz.UTC)

        decision = executor.make_decision(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=now,
        )

        assert decision.should_scale is False
        assert "does not exist" in decision.reason

    def test_make_decision_already_at_desired(self, executor, schedule_result):
        """Test making decision when already at desired replicas."""
        executor.resource_manager.get_current_replicas.return_value = 5
        now = datetime.now(pytz.UTC)

        decision = executor.make_decision(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=now,
        )

        assert decision.should_scale is False
        assert decision.current_replicas == 5
        assert decision.desired_replicas == 5
        assert "Already at desired replicas" in decision.reason

    def test_make_decision_in_cooldown(self, executor, schedule_result):
        """Test making decision when resource is in cooldown."""
        executor.resource_manager.get_current_replicas.return_value = 3
        now = datetime.now(pytz.UTC)

        # Record a recent scaling operation
        executor.state_manager.record_scaling(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            rule_name="previous-rule",
            previous_replicas=2,
            desired_replicas=3,
            reason="Previous scale",
            success=True,
            timestamp=now - timedelta(seconds=30),
        )

        decision = executor.make_decision(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=now,
        )

        assert decision.should_scale is False
        assert decision.in_cooldown is True
        assert "cooldown period" in decision.reason

    def test_make_decision_should_scale(self, executor, schedule_result):
        """Test making decision when should scale."""
        executor.resource_manager.get_current_replicas.return_value = 3
        now = datetime.now(pytz.UTC)

        decision = executor.make_decision(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=now,
        )

        assert decision.should_scale is True
        assert decision.current_replicas == 3
        assert decision.desired_replicas == 5
        assert decision.rule_name == "test-rule"

    def test_execute_no_scale(self, executor):
        """Test executing when should not scale."""
        now = datetime.now(pytz.UTC)
        decision = ScalingDecision(
            should_scale=False,
            current_replicas=5,
            desired_replicas=5,
            reason="Already at desired replicas",
        )

        result = executor.execute(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            decision=decision,
            current_time=now,
        )

        assert result is False
        executor.resource_manager.scale_resource.assert_not_called()

    def test_execute_scale_success(self, executor):
        """Test executing successful scaling."""
        now = datetime.now(pytz.UTC)
        decision = ScalingDecision(
            should_scale=True,
            current_replicas=3,
            desired_replicas=5,
            reason="Scale up",
            rule_name="test-rule",
        )

        result = executor.execute(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            decision=decision,
            current_time=now,
        )

        assert result is True
        executor.resource_manager.scale_resource.assert_called_once_with(
            kind="Deployment",
            name="test-deployment",
            namespace="default",
            replicas=5,
            dry_run=False,
        )

        # Check state was recorded
        state = executor.state_manager.get_state("default", "test-deployment", "Deployment")
        assert state.last_replicas == 5
        assert state.last_rule_name == "test-rule"
        assert state.scaling_count == 1

    def test_execute_scale_failure(self, executor):
        """Test executing failed scaling."""
        executor.resource_manager.scale_resource.return_value = False
        now = datetime.now(pytz.UTC)
        decision = ScalingDecision(
            should_scale=True,
            current_replicas=3,
            desired_replicas=5,
            reason="Scale up",
        )

        result = executor.execute(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            decision=decision,
            current_time=now,
        )

        assert result is False  # execute() returns False when scaling fails
        # Check error was recorded in history
        history = executor.state_manager.get_history(limit=1)
        assert len(history) == 1
        assert history[0].success is False
        assert history[0].error is not None

    def test_execute_scale_exception(self, executor):
        """Test executing when scaling raises exception."""
        executor.resource_manager.scale_resource.side_effect = Exception("API error")
        now = datetime.now(pytz.UTC)
        decision = ScalingDecision(
            should_scale=True,
            current_replicas=3,
            desired_replicas=5,
            reason="Scale up",
        )

        result = executor.execute(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            decision=decision,
            current_time=now,
        )

        assert result is False  # execute() returns False when exception occurs
        # Check error was recorded
        history = executor.state_manager.get_history(limit=1)
        assert len(history) == 1
        assert history[0].success is False
        assert "API error" in history[0].error

    def test_execute_dry_run(self, mock_resource_manager, state_manager):
        """Test executing in dry-run mode."""
        executor = ScalingExecutor(
            resource_manager=mock_resource_manager,
            state_manager=state_manager,
            dry_run=True,
        )

        now = datetime.now(pytz.UTC)
        decision = ScalingDecision(
            should_scale=True,
            current_replicas=3,
            desired_replicas=5,
            reason="Scale up",
            rule_name="test-rule",
        )

        result = executor.execute(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            decision=decision,
            current_time=now,
        )

        assert result is True
        # In dry-run mode, should not call scale_resource
        executor.resource_manager.scale_resource.assert_not_called()

        # But should still record operation
        history = executor.state_manager.get_history(limit=1)
        assert len(history) == 1

    def test_process_schedule_result_integration(self, executor, schedule_result):
        """Test process_schedule_result integration."""
        executor.resource_manager.get_current_replicas.return_value = 3
        now = datetime.now(pytz.UTC)

        result = executor.process_schedule_result(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=now,
        )

        assert result is True
        executor.resource_manager.scale_resource.assert_called_once()

    def test_process_schedule_result_uses_evaluation_time(self, executor, schedule_result):
        """Test process_schedule_result uses evaluation_time if current_time not provided."""
        executor.resource_manager.get_current_replicas.return_value = 3

        result = executor.process_schedule_result(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=None,  # Should use schedule_result.evaluation_time
        )

        assert result is True

    def test_process_schedule_result_no_scale_needed(self, executor, schedule_result):
        """Test process_schedule_result when no scaling needed."""
        executor.resource_manager.get_current_replicas.return_value = 5

        result = executor.process_schedule_result(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            schedule_result=schedule_result,
        )

        assert result is False
        executor.resource_manager.scale_resource.assert_not_called()

    def test_multiple_scaling_operations(self, executor, schedule_result):
        """Test multiple scaling operations for same resource."""
        executor.resource_manager.get_current_replicas.return_value = 3
        now = datetime.now(pytz.UTC)

        # First scaling
        result1 = executor.process_schedule_result(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=now,
        )
        assert result1 is True

        # Second scaling (should be blocked by cooldown)
        result2 = executor.process_schedule_result(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=now + timedelta(seconds=30),
        )
        assert result2 is False

        # Third scaling (after cooldown)
        executor.resource_manager.get_current_replicas.return_value = 5
        result3 = executor.process_schedule_result(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=now + timedelta(seconds=120),
        )
        # Should be False because already at desired replicas
        assert result3 is False

    def test_scaling_different_resources(self, executor, schedule_result):
        """Test scaling different resources concurrently."""
        executor.resource_manager.get_current_replicas.return_value = 3
        now = datetime.now(pytz.UTC)

        # Scale first resource
        result1 = executor.process_schedule_result(
            namespace="default",
            name="deployment-1",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=now,
        )
        assert result1 is True

        # Scale second resource (should work even though first is in cooldown)
        result2 = executor.process_schedule_result(
            namespace="default",
            name="deployment-2",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=now,
        )
        assert result2 is True

        # Check both resources have state
        state1 = executor.state_manager.get_state("default", "deployment-1", "Deployment")
        state2 = executor.state_manager.get_state("default", "deployment-2", "Deployment")
        assert state1.scaling_count == 1
        assert state2.scaling_count == 1

    def test_scaling_with_default_rule(self, executor):
        """Test scaling with default rule (no matched rule)."""
        now = datetime.now(pytz.UTC)
        schedule_result = ScheduleResult(
            desired_replicas=3,
            matched_rule=None,
            reason="Using default replicas",
            evaluation_time=now,
        )

        executor.resource_manager.get_current_replicas.return_value = 5

        result = executor.process_schedule_result(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            schedule_result=schedule_result,
            current_time=now,
        )

        assert result is True
        # Check that rule_name is None in recorded operation
        history = executor.state_manager.get_history(limit=1)
        assert len(history) == 1
        assert history[0].rule_name is None
