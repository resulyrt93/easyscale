"""Tests for state management."""

from datetime import datetime, timedelta

import pytest
import pytz

from easyscale.utils.state import ResourceState, ScalingOperation, StateManager


class TestResourceState:
    """Tests for ResourceState dataclass."""

    def test_create_resource_state(self):
        """Test creating a resource state."""
        state = ResourceState(namespace="default", name="test-deployment", kind="Deployment")

        assert state.namespace == "default"
        assert state.name == "test-deployment"
        assert state.kind == "Deployment"
        assert state.last_scaled_time is None
        assert state.last_replicas is None
        assert state.last_rule_name is None
        assert state.scaling_count == 0

    def test_resource_state_with_values(self):
        """Test resource state with all fields populated."""
        now = datetime.now(pytz.UTC)
        state = ResourceState(
            namespace="production",
            name="api-service",
            kind="StatefulSet",
            last_scaled_time=now,
            last_replicas=5,
            last_rule_name="business-hours",
            scaling_count=3,
        )

        assert state.namespace == "production"
        assert state.name == "api-service"
        assert state.kind == "StatefulSet"
        assert state.last_scaled_time == now
        assert state.last_replicas == 5
        assert state.last_rule_name == "business-hours"
        assert state.scaling_count == 3


class TestScalingOperation:
    """Tests for ScalingOperation dataclass."""

    def test_create_scaling_operation(self):
        """Test creating a scaling operation."""
        now = datetime.now(pytz.UTC)
        op = ScalingOperation(
            timestamp=now,
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            rule_name="weekend-scale",
            previous_replicas=5,
            desired_replicas=2,
            reason="Weekend scale down",
            success=True,
        )

        assert op.timestamp == now
        assert op.namespace == "default"
        assert op.name == "test-deployment"
        assert op.kind == "Deployment"
        assert op.rule_name == "weekend-scale"
        assert op.previous_replicas == 5
        assert op.desired_replicas == 2
        assert op.reason == "Weekend scale down"
        assert op.success is True
        assert op.error is None

    def test_scaling_operation_with_error(self):
        """Test scaling operation with error."""
        now = datetime.now(pytz.UTC)
        op = ScalingOperation(
            timestamp=now,
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            rule_name=None,
            previous_replicas=5,
            desired_replicas=2,
            reason="Default scaling",
            success=False,
            error="Resource not found",
        )

        assert op.success is False
        assert op.error == "Resource not found"
        assert op.rule_name is None


class TestStateManager:
    """Tests for StateManager."""

    @pytest.fixture
    def state_manager(self):
        """Create a state manager for testing."""
        return StateManager(cooldown_seconds=60)

    def test_create_state_manager(self):
        """Test creating a state manager."""
        manager = StateManager(cooldown_seconds=120)
        assert manager.cooldown_seconds == 120

    def test_get_state_creates_new(self, state_manager):
        """Test getting state creates new state if not exists."""
        state = state_manager.get_state("default", "test-deployment", "Deployment")

        assert state.namespace == "default"
        assert state.name == "test-deployment"
        assert state.kind == "Deployment"
        assert state.last_scaled_time is None
        assert state.scaling_count == 0

    def test_get_state_returns_existing(self, state_manager):
        """Test getting state returns existing state."""
        # Get state first time
        state1 = state_manager.get_state("default", "test-deployment", "Deployment")
        state1.scaling_count = 5

        # Get state second time
        state2 = state_manager.get_state("default", "test-deployment", "Deployment")

        assert state1 is state2
        assert state2.scaling_count == 5

    def test_different_resources_have_different_states(self, state_manager):
        """Test different resources have different states."""
        state1 = state_manager.get_state("default", "deployment-1", "Deployment")
        state2 = state_manager.get_state("default", "deployment-2", "Deployment")
        state3 = state_manager.get_state("production", "deployment-1", "Deployment")

        assert state1 is not state2
        assert state1 is not state3
        assert state2 is not state3

    def test_is_in_cooldown_no_previous_scaling(self, state_manager):
        """Test cooldown when no previous scaling."""
        now = datetime.now(pytz.UTC)
        result = state_manager.is_in_cooldown("default", "test-deployment", "Deployment", now)

        assert result is False

    def test_is_in_cooldown_within_period(self, state_manager):
        """Test cooldown within cooldown period."""
        now = datetime.now(pytz.UTC)

        # Record scaling
        state_manager.record_scaling(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            rule_name="test-rule",
            previous_replicas=3,
            desired_replicas=5,
            reason="Scale up",
            success=True,
            timestamp=now,
        )

        # Check cooldown 30 seconds later (within 60 second cooldown)
        check_time = now + timedelta(seconds=30)
        result = state_manager.is_in_cooldown("default", "test-deployment", "Deployment", check_time)

        assert result is True

    def test_is_in_cooldown_after_period(self, state_manager):
        """Test cooldown after cooldown period."""
        now = datetime.now(pytz.UTC)

        # Record scaling
        state_manager.record_scaling(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            rule_name="test-rule",
            previous_replicas=3,
            desired_replicas=5,
            reason="Scale up",
            success=True,
            timestamp=now,
        )

        # Check cooldown 90 seconds later (after 60 second cooldown)
        check_time = now + timedelta(seconds=90)
        result = state_manager.is_in_cooldown("default", "test-deployment", "Deployment", check_time)

        assert result is False

    def test_record_scaling_updates_state(self, state_manager):
        """Test recording scaling updates state."""
        now = datetime.now(pytz.UTC)

        state_manager.record_scaling(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            rule_name="weekend-scale",
            previous_replicas=5,
            desired_replicas=2,
            reason="Weekend scale down",
            success=True,
            timestamp=now,
        )

        state = state_manager.get_state("default", "test-deployment", "Deployment")
        assert state.last_scaled_time == now
        assert state.last_replicas == 2
        assert state.last_rule_name == "weekend-scale"
        assert state.scaling_count == 1

    def test_record_scaling_adds_to_history(self, state_manager):
        """Test recording scaling adds to history."""
        now = datetime.now(pytz.UTC)

        state_manager.record_scaling(
            namespace="default",
            name="test-deployment",
            kind="Deployment",
            rule_name="test-rule",
            previous_replicas=3,
            desired_replicas=5,
            reason="Scale up",
            success=True,
            timestamp=now,
        )

        history = state_manager.get_history()
        assert len(history) == 1
        assert history[0].namespace == "default"
        assert history[0].name == "test-deployment"
        assert history[0].previous_replicas == 3
        assert history[0].desired_replicas == 5

    def test_get_history_no_filters(self, state_manager):
        """Test getting history without filters."""
        now = datetime.now(pytz.UTC)

        # Record multiple operations
        for i in range(3):
            state_manager.record_scaling(
                namespace="default",
                name=f"deployment-{i}",
                kind="Deployment",
                rule_name=None,
                previous_replicas=i,
                desired_replicas=i + 1,
                reason=f"Scale {i}",
                success=True,
                timestamp=now + timedelta(seconds=i),
            )

        history = state_manager.get_history()
        assert len(history) == 3
        # Should be newest first
        assert history[0].name == "deployment-2"
        assert history[1].name == "deployment-1"
        assert history[2].name == "deployment-0"

    def test_get_history_filter_by_namespace(self, state_manager):
        """Test filtering history by namespace."""
        now = datetime.now(pytz.UTC)

        state_manager.record_scaling(
            namespace="default",
            name="deployment-1",
            kind="Deployment",
            rule_name=None,
            previous_replicas=1,
            desired_replicas=2,
            reason="Scale",
            success=True,
            timestamp=now,
        )

        state_manager.record_scaling(
            namespace="production",
            name="deployment-2",
            kind="Deployment",
            rule_name=None,
            previous_replicas=2,
            desired_replicas=3,
            reason="Scale",
            success=True,
            timestamp=now,
        )

        history = state_manager.get_history(namespace="default")
        assert len(history) == 1
        assert history[0].namespace == "default"

    def test_get_history_filter_by_name(self, state_manager):
        """Test filtering history by name."""
        now = datetime.now(pytz.UTC)

        for name in ["deployment-1", "deployment-2"]:
            state_manager.record_scaling(
                namespace="default",
                name=name,
                kind="Deployment",
                rule_name=None,
                previous_replicas=1,
                desired_replicas=2,
                reason="Scale",
                success=True,
                timestamp=now,
            )

        history = state_manager.get_history(name="deployment-1")
        assert len(history) == 1
        assert history[0].name == "deployment-1"

    def test_get_history_filter_by_kind(self, state_manager):
        """Test filtering history by kind."""
        now = datetime.now(pytz.UTC)

        state_manager.record_scaling(
            namespace="default",
            name="resource-1",
            kind="Deployment",
            rule_name=None,
            previous_replicas=1,
            desired_replicas=2,
            reason="Scale",
            success=True,
            timestamp=now,
        )

        state_manager.record_scaling(
            namespace="default",
            name="resource-2",
            kind="StatefulSet",
            rule_name=None,
            previous_replicas=2,
            desired_replicas=3,
            reason="Scale",
            success=True,
            timestamp=now,
        )

        history = state_manager.get_history(kind="Deployment")
        assert len(history) == 1
        assert history[0].kind == "Deployment"

    def test_get_history_with_limit(self, state_manager):
        """Test getting history with limit."""
        now = datetime.now(pytz.UTC)

        # Record 5 operations
        for i in range(5):
            state_manager.record_scaling(
                namespace="default",
                name="deployment",
                kind="Deployment",
                rule_name=None,
                previous_replicas=i,
                desired_replicas=i + 1,
                reason=f"Scale {i}",
                success=True,
                timestamp=now + timedelta(seconds=i),
            )

        history = state_manager.get_history(limit=3)
        assert len(history) == 3
        # Should get newest 3
        assert history[0].desired_replicas == 5
        assert history[1].desired_replicas == 4
        assert history[2].desired_replicas == 3

    def test_clear_history(self, state_manager):
        """Test clearing history."""
        now = datetime.now(pytz.UTC)

        state_manager.record_scaling(
            namespace="default",
            name="deployment",
            kind="Deployment",
            rule_name=None,
            previous_replicas=1,
            desired_replicas=2,
            reason="Scale",
            success=True,
            timestamp=now,
        )

        assert len(state_manager.get_history()) == 1

        state_manager.clear_history()
        assert len(state_manager.get_history()) == 0

    def test_clear_state(self, state_manager):
        """Test clearing state for specific resource."""
        now = datetime.now(pytz.UTC)

        # Create states for two resources
        state_manager.record_scaling(
            namespace="default",
            name="deployment-1",
            kind="Deployment",
            rule_name=None,
            previous_replicas=1,
            desired_replicas=2,
            reason="Scale",
            success=True,
            timestamp=now,
        )

        state_manager.record_scaling(
            namespace="default",
            name="deployment-2",
            kind="Deployment",
            rule_name=None,
            previous_replicas=1,
            desired_replicas=2,
            reason="Scale",
            success=True,
            timestamp=now,
        )

        # Clear state for deployment-1
        state_manager.clear_state("default", "deployment-1", "Deployment")

        # Get state for deployment-1 should create new state
        state1 = state_manager.get_state("default", "deployment-1", "Deployment")
        assert state1.scaling_count == 0

        # Get state for deployment-2 should have existing state
        state2 = state_manager.get_state("default", "deployment-2", "Deployment")
        assert state2.scaling_count == 1

    def test_record_scaling_with_error(self, state_manager):
        """Test recording failed scaling operation."""
        now = datetime.now(pytz.UTC)

        state_manager.record_scaling(
            namespace="default",
            name="deployment",
            kind="Deployment",
            rule_name="test-rule",
            previous_replicas=3,
            desired_replicas=5,
            reason="Scale up",
            success=False,
            timestamp=now,
            error="API error",
        )

        history = state_manager.get_history()
        assert len(history) == 1
        assert history[0].success is False
        assert history[0].error == "API error"

    def test_multiple_scaling_operations(self, state_manager):
        """Test multiple scaling operations for same resource."""
        now = datetime.now(pytz.UTC)

        # First scaling
        state_manager.record_scaling(
            namespace="default",
            name="deployment",
            kind="Deployment",
            rule_name="rule-1",
            previous_replicas=3,
            desired_replicas=5,
            reason="Scale up",
            success=True,
            timestamp=now,
        )

        # Second scaling
        state_manager.record_scaling(
            namespace="default",
            name="deployment",
            kind="Deployment",
            rule_name="rule-2",
            previous_replicas=5,
            desired_replicas=2,
            reason="Scale down",
            success=True,
            timestamp=now + timedelta(seconds=120),
        )

        state = state_manager.get_state("default", "deployment", "Deployment")
        assert state.scaling_count == 2
        assert state.last_replicas == 2
        assert state.last_rule_name == "rule-2"

        history = state_manager.get_history(name="deployment")
        assert len(history) == 2
