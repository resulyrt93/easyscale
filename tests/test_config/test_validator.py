"""Tests for configuration validator."""

import pytest

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
from easyscale.config.validator import ConfigValidator, ValidationResult


class TestValidationResult:
    """Tests for ValidationResult."""

    def test_valid_result(self):
        """Test valid validation result."""
        result = ValidationResult(valid=True)
        assert result.valid
        assert bool(result) is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_invalid_result(self):
        """Test invalid validation result."""
        result = ValidationResult(valid=False, errors=["Error 1", "Error 2"])
        assert not result.valid
        assert bool(result) is False
        assert len(result.errors) == 2

    def test_result_with_warnings(self):
        """Test result with warnings."""
        result = ValidationResult(valid=True, warnings=["Warning 1"])
        assert result.valid
        assert len(result.warnings) == 1

    def test_result_str(self):
        """Test string representation."""
        result = ValidationResult(
            valid=False,
            errors=["Error 1"],
            warnings=["Warning 1"]
        )
        result_str = str(result)
        assert "invalid" in result_str.lower()
        assert "Error 1" in result_str
        assert "Warning 1" in result_str


class TestConfigValidator:
    """Tests for ConfigValidator."""

    def test_valid_configuration(self):
        """Test validation of valid configuration."""
        rule = ScalingRule(
            metadata=Metadata(name="test-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(
                        name="Weekend",
                        days=[DayOfWeek.SATURDAY, DayOfWeek.SUNDAY],
                        replicas=2,
                        timezone="UTC"
                    )
                ],
                default=DefaultConfig(replicas=5)
            )
        )
        result = ConfigValidator.validate(rule)
        assert result.valid
        assert len(result.errors) == 0

    def test_invalid_timezone(self):
        """Test validation with invalid timezone."""
        rule = ScalingRule(
            metadata=Metadata(name="test-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(
                        name="Weekend",
                        days=[DayOfWeek.SATURDAY],
                        replicas=2,
                        timezone="Invalid/Timezone"
                    )
                ],
                default=DefaultConfig(replicas=5)
            )
        )
        result = ConfigValidator.validate(rule)
        assert not result.valid
        assert len(result.errors) > 0
        assert "Invalid timezone" in result.errors[0]

    def test_multiple_rules_same_priority(self):
        """Test warning for multiple rules with same priority."""
        rule = ScalingRule(
            metadata=Metadata(name="test-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(
                        name="Rule 1",
                        days=[DayOfWeek.SATURDAY],
                        replicas=2,
                        priority=10
                    ),
                    ScheduleRule(
                        name="Rule 2",
                        days=[DayOfWeek.SUNDAY],
                        replicas=3,
                        priority=10
                    )
                ],
                default=DefaultConfig(replicas=5)
            )
        )
        result = ConfigValidator.validate(rule)
        assert result.valid  # Still valid, just a warning
        assert len(result.warnings) > 0
        assert "priority 10" in result.warnings[0].lower()

    def test_default_differs_from_schedule(self):
        """Test warning when default differs from all schedule rules."""
        rule = ScalingRule(
            metadata=Metadata(name="test-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(
                        name="Weekend",
                        days=[DayOfWeek.SATURDAY],
                        replicas=2
                    )
                ],
                default=DefaultConfig(replicas=10)  # Different from schedule
            )
        )
        result = ConfigValidator.validate(rule)
        assert result.valid
        assert len(result.warnings) > 0
        assert "differs from all schedule rules" in result.warnings[0].lower()

    def test_date_only_rule_warning(self):
        """Test warning for date-only rules."""
        from datetime import date

        rule = ScalingRule(
            metadata=Metadata(name="test-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(
                        name="Holiday",
                        dates=[date(2025, 12, 25)],
                        replicas=1
                    )
                ],
                default=DefaultConfig(replicas=5)
            )
        )
        result = ConfigValidator.validate(rule)
        assert result.valid
        assert len(result.warnings) >= 1
        # Should have at least the date-only warning
        date_warning = any("specific dates" in w.lower() for w in result.warnings)
        assert date_warning, f"Expected date warning not found in: {result.warnings}"

    def test_time_without_days_or_dates(self):
        """Test error for time range without days or dates."""
        from datetime import time

        rule = ScalingRule(
            metadata=Metadata(name="test-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(
                        name="Invalid time rule",
                        time_start=time(9, 0),
                        time_end=time(17, 0),
                        replicas=5,
                        days=[DayOfWeek.MONDAY]  # This makes it valid
                    )
                ],
                default=DefaultConfig(replicas=2)
            )
        )
        result = ConfigValidator.validate(rule)
        assert result.valid

    def test_validate_from_dict(self):
        """Test validation from dictionary."""
        data = {
            "apiVersion": "easyscale.io/v1",
            "kind": "ScalingRule",
            "metadata": {"name": "test-rule"},
            "spec": {
                "target": {
                    "kind": "Deployment",
                    "name": "app"
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
        result = ConfigValidator.validate_from_dict(data)
        assert result.valid

    def test_validate_from_invalid_dict(self):
        """Test validation from invalid dictionary."""
        data = {
            "apiVersion": "easyscale.io/v1",
            "kind": "ScalingRule",
            "metadata": {"name": "test-rule"},
            "spec": {
                "target": {
                    "kind": "InvalidKind",
                    "name": "app"
                },
                "schedule": [],
                "default": {"replicas": 5}
            }
        }
        result = ConfigValidator.validate_from_dict(data)
        assert not result.valid
        assert len(result.errors) > 0

    def test_quick_validate(self):
        """Test quick validation."""
        rule = ScalingRule(
            metadata=Metadata(name="test-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(
                        name="Weekend",
                        days=[DayOfWeek.SATURDAY],
                        replicas=2,
                        timezone="UTC"
                    )
                ],
                default=DefaultConfig(replicas=5)
            )
        )
        assert ConfigValidator.quick_validate(rule) is True

    def test_quick_validate_invalid(self):
        """Test quick validation with invalid config."""
        rule = ScalingRule(
            metadata=Metadata(name="test-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(
                        name="Weekend",
                        days=[DayOfWeek.SATURDAY],
                        replicas=2,
                        timezone="Invalid/Timezone"
                    )
                ],
                default=DefaultConfig(replicas=5)
            )
        )
        assert ConfigValidator.quick_validate(rule) is False

    def test_multiple_validation_errors(self):
        """Test configuration with multiple validation errors."""
        rule = ScalingRule(
            metadata=Metadata(name="test-rule"),
            spec=ScalingSpec(
                target=TargetResource(kind="Deployment", name="app"),
                schedule=[
                    ScheduleRule(
                        name="Rule 1",
                        days=[DayOfWeek.SATURDAY],
                        replicas=2,
                        timezone="Invalid/Timezone1"
                    ),
                    ScheduleRule(
                        name="Rule 2",
                        days=[DayOfWeek.SUNDAY],
                        replicas=3,
                        timezone="Invalid/Timezone2"
                    )
                ],
                default=DefaultConfig(replicas=5)
            )
        )
        result = ConfigValidator.validate(rule)
        assert not result.valid
        assert len(result.errors) == 2
