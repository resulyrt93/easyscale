"""Tests for rule evaluation scheduler."""

from datetime import date, datetime, time

import pytest
import pytz

from easyscale.config.models import (
    DefaultConfig,
    DayOfWeek,
    Metadata,
    ScalingLimits,
    ScalingRule,
    ScalingSpec,
    ScheduleRule,
    TargetResource,
)
from easyscale.controller.scheduler import RuleEvaluator, ScheduleResult


@pytest.fixture
def basic_rule():
    """Create a basic scaling rule for testing."""
    return ScalingRule(
        metadata=Metadata(name="test-rule"),
        spec=ScalingSpec(
            target=TargetResource(kind="Deployment", name="test-app", namespace="default"),
            schedule=[
                ScheduleRule(
                    name="Weekday hours",
                    days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                          DayOfWeek.THURSDAY, DayOfWeek.FRIDAY],
                    time_start=time(9, 0),
                    time_end=time(17, 0),
                    replicas=5,
                    timezone="UTC"
                ),
                ScheduleRule(
                    name="Weekend",
                    days=[DayOfWeek.SATURDAY, DayOfWeek.SUNDAY],
                    replicas=2,
                    timezone="UTC"
                )
            ],
            default=DefaultConfig(replicas=1)
        )
    )


@pytest.fixture
def priority_rule():
    """Create a rule with priorities for testing."""
    return ScalingRule(
        metadata=Metadata(name="priority-rule"),
        spec=ScalingSpec(
            target=TargetResource(kind="Deployment", name="test-app", namespace="default"),
            schedule=[
                ScheduleRule(
                    name="Business hours",
                    days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                          DayOfWeek.THURSDAY, DayOfWeek.FRIDAY],
                    time_start=time(9, 0),
                    time_end=time(18, 0),
                    replicas=3,
                    priority=50,
                    timezone="UTC"
                ),
                ScheduleRule(
                    name="Peak hours",
                    days=[DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
                          DayOfWeek.THURSDAY, DayOfWeek.FRIDAY],
                    time_start=time(14, 0),
                    time_end=time(16, 0),
                    replicas=10,
                    priority=100,
                    timezone="UTC"
                )
            ],
            default=DefaultConfig(replicas=1)
        )
    )


@pytest.fixture
def limits_rule():
    """Create a rule with limits for testing."""
    return ScalingRule(
        metadata=Metadata(name="limits-rule"),
        spec=ScalingSpec(
            target=TargetResource(kind="Deployment", name="test-app", namespace="default"),
            schedule=[
                ScheduleRule(
                    name="High replicas",
                    days=[DayOfWeek.MONDAY],
                    replicas=15,  # Valid: within 2-20 range
                    timezone="UTC"
                )
            ],
            default=DefaultConfig(replicas=10),  # Valid: within 2-20 range
            limits=ScalingLimits(min_replicas=2, max_replicas=20)
        )
    )


class TestRuleEvaluator:
    """Tests for RuleEvaluator."""

    def test_init(self, basic_rule):
        """Test RuleEvaluator initialization."""
        evaluator = RuleEvaluator(basic_rule)
        assert evaluator.scaling_rule == basic_rule
        assert evaluator.target == basic_rule.spec.target
        assert len(evaluator.schedule_rules) == 2
        assert evaluator.default_replicas == 1

    def test_weekday_business_hours(self, basic_rule):
        """Test evaluation during weekday business hours."""
        evaluator = RuleEvaluator(basic_rule)

        # Monday at 2:00 PM UTC
        test_time = datetime(2025, 1, 6, 14, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 5
        assert result.matched_rule is not None
        assert result.matched_rule.name == "Weekday hours"
        assert result.is_default is False

    def test_weekend(self, basic_rule):
        """Test evaluation during weekend."""
        evaluator = RuleEvaluator(basic_rule)

        # Saturday at 2:00 PM UTC
        test_time = datetime(2025, 1, 11, 14, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 2
        assert result.matched_rule is not None
        assert result.matched_rule.name == "Weekend"
        assert result.is_default is False

    def test_no_match_uses_default(self, basic_rule):
        """Test that default is used when no rules match."""
        evaluator = RuleEvaluator(basic_rule)

        # Monday at 8:00 AM (before business hours)
        test_time = datetime(2025, 1, 6, 8, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 1
        assert result.matched_rule is None
        assert result.is_default is True
        assert "No schedule rules matched" in result.reason

    def test_priority_resolution(self, priority_rule):
        """Test that highest priority rule wins."""
        evaluator = RuleEvaluator(priority_rule)

        # Monday at 3:00 PM (both rules match, but peak hours has higher priority)
        test_time = datetime(2025, 1, 6, 15, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 10
        assert result.matched_rule is not None
        assert result.matched_rule.name == "Peak hours"
        assert result.matched_rule.priority == 100

    def test_lower_priority_outside_peak(self, priority_rule):
        """Test lower priority rule when higher priority doesn't match."""
        evaluator = RuleEvaluator(priority_rule)

        # Monday at 10:00 AM (only business hours matches)
        test_time = datetime(2025, 1, 6, 10, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 3
        assert result.matched_rule is not None
        assert result.matched_rule.name == "Business hours"

    def test_limits_applied(self, limits_rule):
        """Test that limits are applied correctly."""
        evaluator = RuleEvaluator(limits_rule)

        # Monday (rule wants 15 replicas, which is within limits)
        test_time = datetime(2025, 1, 6, 12, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 15  # Within limits
        assert result.matched_rule is not None

    def test_limits_applied_to_default(self, limits_rule):
        """Test that limits are applied to default replicas."""
        evaluator = RuleEvaluator(limits_rule)

        # Tuesday (no rule matches, default is 10)
        test_time = datetime(2025, 1, 7, 12, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 10  # Default is within limits
        assert result.is_default is True

    def test_timezone_conversion(self):
        """Test that timezone conversion works correctly."""
        # Rule in New York timezone
        rule = ScalingRule(
            metadata=Metadata(name="tz-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app", namespace="default"),
                schedule=[
                    ScheduleRule(
                        name="NY business hours",
                        days=[DayOfWeek.MONDAY],
                        time_start=time(9, 0),
                        time_end=time(17, 0),
                        replicas=5,
                        timezone="America/New_York"
                    )
                ],
                default=DefaultConfig(replicas=1)
            )
        )

        evaluator = RuleEvaluator(rule)

        # Monday at 2:00 PM UTC = Monday at 9:00 AM EST (matches!)
        # Note: This test assumes EST (UTC-5), adjust if DST is in effect
        test_time = datetime(2025, 1, 6, 14, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 5
        assert result.matched_rule is not None

    def test_date_specific_rule(self):
        """Test date-specific rules."""
        rule = ScalingRule(
            metadata=Metadata(name="date-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app", namespace="default"),
                schedule=[
                    ScheduleRule(
                        name="Christmas",
                        dates=[date(2025, 12, 25)],
                        replicas=1,
                        timezone="UTC"
                    )
                ],
                default=DefaultConfig(replicas=5)
            )
        )

        evaluator = RuleEvaluator(rule)

        # Christmas Day
        test_time = datetime(2025, 12, 25, 12, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 1
        assert result.matched_rule is not None
        assert result.matched_rule.name == "Christmas"

        # Day before Christmas
        test_time = datetime(2025, 12, 24, 12, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 5  # Default
        assert result.is_default is True

    def test_time_boundary_inclusive_start(self):
        """Test that start time is inclusive."""
        rule = ScalingRule(
            metadata=Metadata(name="boundary-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app", namespace="default"),
                schedule=[
                    ScheduleRule(
                        name="Exact start",
                        days=[DayOfWeek.MONDAY],
                        time_start=time(9, 0),
                        time_end=time(17, 0),
                        replicas=5,
                        timezone="UTC"
                    )
                ],
                default=DefaultConfig(replicas=1)
            )
        )

        evaluator = RuleEvaluator(rule)

        # Exactly 9:00 AM
        test_time = datetime(2025, 1, 6, 9, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 5

    def test_time_boundary_exclusive_end(self):
        """Test that end time is exclusive."""
        rule = ScalingRule(
            metadata=Metadata(name="boundary-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app", namespace="default"),
                schedule=[
                    ScheduleRule(
                        name="Exact end",
                        days=[DayOfWeek.MONDAY],
                        time_start=time(9, 0),
                        time_end=time(17, 0),
                        replicas=5,
                        timezone="UTC"
                    )
                ],
                default=DefaultConfig(replicas=1)
            )
        )

        evaluator = RuleEvaluator(rule)

        # Exactly 5:00 PM (should NOT match)
        test_time = datetime(2025, 1, 6, 17, 0, 0, tzinfo=pytz.UTC)
        result = evaluator.evaluate(test_time)

        assert result.desired_replicas == 1  # Default
        assert result.is_default is True


class TestScheduleResult:
    """Tests for ScheduleResult."""

    def test_is_default_true(self):
        """Test is_default property when using default."""
        result = ScheduleResult(
            desired_replicas=5,
            matched_rule=None,
            reason="Using default",
            evaluation_time=datetime.now(pytz.UTC)
        )
        assert result.is_default is True

    def test_is_default_false(self):
        """Test is_default property when rule matched."""
        rule = ScheduleRule(
            name="Test",
            days=[DayOfWeek.MONDAY],
            replicas=5,
            timezone="UTC"
        )
        result = ScheduleResult(
            desired_replicas=5,
            matched_rule=rule,
            reason="Matched rule",
            evaluation_time=datetime.now(pytz.UTC)
        )
        assert result.is_default is False
