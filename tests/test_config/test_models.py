"""Tests for Pydantic models."""

from datetime import date, time

import pytest
from pydantic import ValidationError

from easyscale.config.models import (
    DayOfWeek,
    DefaultConfig,
    Metadata,
    ScalingLimits,
    ScalingRule,
    ScalingSpec,
    ScheduleRule,
    TargetResource,
)


class TestDayOfWeek:
    """Tests for DayOfWeek enum."""

    def test_valid_days(self):
        """Test that all days of week are valid."""
        assert DayOfWeek.MONDAY.value == "Monday"
        assert DayOfWeek.SUNDAY.value == "Sunday"

    def test_day_from_string(self):
        """Test creating day from string."""
        assert DayOfWeek("Monday") == DayOfWeek.MONDAY
        assert DayOfWeek("Friday") == DayOfWeek.FRIDAY


class TestTargetResource:
    """Tests for TargetResource model."""

    def test_valid_deployment(self):
        """Test valid deployment target."""
        target = TargetResource(kind="Deployment", name="my-app", namespace="default")
        assert target.kind == "Deployment"
        assert target.name == "my-app"
        assert target.namespace == "default"

    def test_valid_statefulset(self):
        """Test valid statefulset target."""
        target = TargetResource(kind="StatefulSet", name="my-stateful", namespace="prod")
        assert target.kind == "StatefulSet"

    def test_default_namespace(self):
        """Test default namespace."""
        target = TargetResource(kind="Deployment", name="my-app")
        assert target.namespace == "default"

    def test_invalid_kind(self):
        """Test invalid resource kind."""
        with pytest.raises(ValidationError) as exc_info:
            TargetResource(kind="DaemonSet", name="my-app")
        assert "kind" in str(exc_info.value)

    def test_empty_name(self):
        """Test empty resource name."""
        with pytest.raises(ValidationError) as exc_info:
            TargetResource(kind="Deployment", name="")
        assert "cannot be empty" in str(exc_info.value)

    def test_name_too_long(self):
        """Test resource name that exceeds 253 characters."""
        long_name = "a" * 254
        with pytest.raises(ValidationError) as exc_info:
            TargetResource(kind="Deployment", name=long_name)
        assert "cannot exceed 253 characters" in str(exc_info.value)


class TestScheduleRule:
    """Tests for ScheduleRule model."""

    def test_valid_day_based_rule(self):
        """Test valid day-based schedule rule."""
        rule = ScheduleRule(
            name="Weekend scale",
            days=[DayOfWeek.SATURDAY, DayOfWeek.SUNDAY],
            replicas=2
        )
        assert rule.name == "Weekend scale"
        assert len(rule.days) == 2
        assert rule.replicas == 2
        assert rule.timezone == "UTC"
        assert rule.priority == 0

    def test_valid_date_based_rule(self):
        """Test valid date-based schedule rule."""
        rule = ScheduleRule(
            name="Holiday",
            dates=[date(2025, 12, 25), date(2026, 1, 1)],
            replicas=1
        )
        assert len(rule.dates) == 2
        assert rule.replicas == 1

    def test_time_range(self):
        """Test time range validation."""
        rule = ScheduleRule(
            name="Business hours",
            days=[DayOfWeek.MONDAY],
            time_start=time(9, 0),
            time_end=time(17, 0),
            replicas=5
        )
        assert rule.time_start == time(9, 0)
        assert rule.time_end == time(17, 0)

    def test_invalid_time_range(self):
        """Test invalid time range (end before start)."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleRule(
                name="Invalid",
                days=[DayOfWeek.MONDAY],
                time_start=time(17, 0),
                time_end=time(9, 0),
                replicas=5
            )
        assert "must be before" in str(exc_info.value)

    def test_no_schedule_condition(self):
        """Test rule without days or dates."""
        with pytest.raises(ValidationError) as exc_info:
            ScheduleRule(name="Invalid", replicas=3)
        assert "At least one of 'days' or 'dates' must be specified" in str(exc_info.value)

    def test_negative_replicas(self):
        """Test negative replica count."""
        with pytest.raises(ValidationError):
            ScheduleRule(name="Invalid", days=[DayOfWeek.MONDAY], replicas=-1)

    def test_custom_timezone(self):
        """Test custom timezone."""
        rule = ScheduleRule(
            name="NY hours",
            days=[DayOfWeek.MONDAY],
            replicas=3,
            timezone="America/New_York"
        )
        assert rule.timezone == "America/New_York"

    def test_camel_case_alias(self):
        """Test that camelCase aliases work."""
        data = {
            "name": "Test",
            "days": ["Monday"],
            "timeStart": "09:00",
            "timeEnd": "17:00",
            "replicas": 3
        }
        rule = ScheduleRule.model_validate(data)
        assert rule.time_start == time(9, 0)
        assert rule.time_end == time(17, 0)


class TestDefaultConfig:
    """Tests for DefaultConfig model."""

    def test_valid_default(self):
        """Test valid default config."""
        config = DefaultConfig(replicas=3)
        assert config.replicas == 3

    def test_zero_replicas(self):
        """Test zero replicas is valid."""
        config = DefaultConfig(replicas=0)
        assert config.replicas == 0

    def test_negative_replicas(self):
        """Test negative replicas is invalid."""
        with pytest.raises(ValidationError):
            DefaultConfig(replicas=-1)


class TestScalingLimits:
    """Tests for ScalingLimits model."""

    def test_valid_limits(self):
        """Test valid scaling limits."""
        limits = ScalingLimits(min_replicas=1, max_replicas=10)
        assert limits.min_replicas == 1
        assert limits.max_replicas == 10

    def test_invalid_limits(self):
        """Test min greater than max."""
        with pytest.raises(ValidationError) as exc_info:
            ScalingLimits(min_replicas=10, max_replicas=1)
        assert "cannot be greater than" in str(exc_info.value)

    def test_equal_limits(self):
        """Test min equal to max."""
        limits = ScalingLimits(min_replicas=5, max_replicas=5)
        assert limits.min_replicas == limits.max_replicas

    def test_camel_case_alias(self):
        """Test that camelCase aliases work."""
        data = {"minReplicas": 1, "maxReplicas": 10}
        limits = ScalingLimits.model_validate(data)
        assert limits.min_replicas == 1
        assert limits.max_replicas == 10


class TestMetadata:
    """Tests for Metadata model."""

    def test_valid_metadata(self):
        """Test valid metadata."""
        metadata = Metadata(name="my-rule", labels={"env": "prod"})
        assert metadata.name == "my-rule"
        assert metadata.labels == {"env": "prod"}

    def test_minimal_metadata(self):
        """Test minimal metadata."""
        metadata = Metadata(name="my-rule")
        assert metadata.name == "my-rule"
        assert metadata.namespace is None
        assert metadata.labels is None

    def test_empty_name(self):
        """Test empty rule name."""
        with pytest.raises(ValidationError) as exc_info:
            Metadata(name="")
        assert "cannot be empty" in str(exc_info.value)


class TestScalingSpec:
    """Tests for ScalingSpec model."""

    def test_valid_spec(self):
        """Test valid scaling spec."""
        spec = ScalingSpec(
            target=TargetResource(kind="Deployment", name="app"),
            schedule=[
                ScheduleRule(name="Weekend", days=[DayOfWeek.SATURDAY], replicas=2)
            ],
            default=DefaultConfig(replicas=5)
        )
        assert spec.target.name == "app"
        assert len(spec.schedule) == 1
        assert spec.default.replicas == 5

    def test_spec_with_limits(self):
        """Test spec with scaling limits."""
        spec = ScalingSpec(
            target=TargetResource(kind="Deployment", name="app"),
            schedule=[
                ScheduleRule(name="Weekend", days=[DayOfWeek.SATURDAY], replicas=2)
            ],
            default=DefaultConfig(replicas=5),
            limits=ScalingLimits(min_replicas=1, max_replicas=10)
        )
        assert spec.limits.min_replicas == 1
        assert spec.limits.max_replicas == 10

    def test_default_below_min_limit(self):
        """Test default replicas below minimum limit."""
        with pytest.raises(ValidationError) as exc_info:
            ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(name="Test", days=[DayOfWeek.MONDAY], replicas=5)
                ],
                default=DefaultConfig(replicas=0),
                limits=ScalingLimits(min_replicas=1, max_replicas=10)
            )
        assert "cannot be less than min_replicas" in str(exc_info.value)

    def test_schedule_rule_exceeds_max_limit(self):
        """Test schedule rule exceeds maximum limit."""
        with pytest.raises(ValidationError) as exc_info:
            ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(name="Test", days=[DayOfWeek.MONDAY], replicas=15)
                ],
                default=DefaultConfig(replicas=5),
                limits=ScalingLimits(min_replicas=1, max_replicas=10)
            )
        assert "cannot be greater than max_replicas" in str(exc_info.value)

    def test_empty_schedule(self):
        """Test empty schedule list."""
        with pytest.raises(ValidationError):
            ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[],
                default=DefaultConfig(replicas=5)
            )


class TestScalingRule:
    """Tests for complete ScalingRule model."""

    def test_valid_scaling_rule(self):
        """Test valid complete scaling rule."""
        rule = ScalingRule(
            metadata=Metadata(name="test-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(name="Weekend", days=[DayOfWeek.SATURDAY], replicas=2)
                ],
                default=DefaultConfig(replicas=5)
            )
        )
        assert rule.api_version == "easyscale.io/v1"
        assert rule.kind == "ScalingRule"
        assert rule.metadata.name == "test-rule"

    def test_from_dict(self):
        """Test creating ScalingRule from dictionary."""
        data = {
            "apiVersion": "easyscale.io/v1",
            "kind": "ScalingRule",
            "metadata": {"name": "test-rule"},
            "spec": {
                "target": {
                    "kind": "Deployment",
                    "name": "my-app",
                    "namespace": "default"
                },
                "schedule": [
                    {
                        "name": "Weekend",
                        "days": ["Saturday", "Sunday"],
                        "replicas": 2
                    }
                ],
                "default": {"replicas": 5}
            }
        }
        rule = ScalingRule.model_validate(data)
        assert rule.metadata.name == "test-rule"
        assert len(rule.spec.schedule) == 1
        assert rule.spec.schedule[0].replicas == 2

    def test_complex_rule(self):
        """Test complex scaling rule with all features."""
        data = {
            "apiVersion": "easyscale.io/v1",
            "kind": "ScalingRule",
            "metadata": {
                "name": "complex-rule",
                "labels": {"env": "prod"}
            },
            "spec": {
                "target": {
                    "kind": "Deployment",
                    "name": "api-service",
                    "namespace": "production"
                },
                "schedule": [
                    {
                        "name": "Holiday",
                        "dates": ["2025-12-25"],
                        "replicas": 1,
                        "priority": 100,
                        "timezone": "UTC"
                    },
                    {
                        "name": "Business hours",
                        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                        "timeStart": "09:00",
                        "timeEnd": "17:00",
                        "replicas": 5,
                        "timezone": "America/New_York"
                    }
                ],
                "default": {"replicas": 2},
                "limits": {
                    "minReplicas": 1,
                    "maxReplicas": 10
                }
            }
        }
        rule = ScalingRule.model_validate(data)
        assert rule.metadata.name == "complex-rule"
        assert len(rule.spec.schedule) == 2
        assert rule.spec.limits.max_replicas == 10
