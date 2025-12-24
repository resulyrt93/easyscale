"""Configuration validator for EasyScale."""

import logging
from typing import Optional

import pytz
from pydantic import ValidationError

from easyscale.config.models import ScalingRule

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of configuration validation."""

    def __init__(self, valid: bool, errors: Optional[list[str]] = None, warnings: Optional[list[str]] = None):
        """
        Initialize validation result.

        Args:
            valid: Whether the configuration is valid
            errors: List of validation errors
            warnings: List of validation warnings
        """
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []

    def __bool__(self) -> bool:
        """Return validation status."""
        return self.valid

    def __str__(self) -> str:
        """Return human-readable validation result."""
        lines = []
        if self.valid:
            lines.append("✓ Configuration is valid")
        else:
            lines.append("✗ Configuration is invalid")

        if self.errors:
            lines.append("\nErrors:")
            for error in self.errors:
                lines.append(f"  - {error}")

        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


class ConfigValidator:
    """Validate EasyScale configuration."""

    @staticmethod
    def validate(rule: ScalingRule) -> ValidationResult:
        """
        Validate a ScalingRule configuration.

        Args:
            rule: The ScalingRule to validate

        Returns:
            ValidationResult with any errors or warnings
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Validate timezone strings
        for schedule_rule in rule.spec.schedule:
            try:
                pytz.timezone(schedule_rule.timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                errors.append(
                    f"Rule '{schedule_rule.name}': Invalid timezone '{schedule_rule.timezone}'. "
                    "Use IANA timezone names (e.g., 'UTC', 'America/New_York')"
                )

        # Check for schedule rule conflicts with same priority
        priority_groups: dict[int, list[str]] = {}
        for schedule_rule in rule.spec.schedule:
            if schedule_rule.priority not in priority_groups:
                priority_groups[schedule_rule.priority] = []
            priority_groups[schedule_rule.priority].append(schedule_rule.name)

        for priority, rule_names in priority_groups.items():
            if len(rule_names) > 1:
                warnings.append(
                    f"Multiple rules with priority {priority}: {', '.join(rule_names)}. "
                    "Consider using different priorities to avoid ambiguity."
                )

        # Check if default replicas differ significantly from schedule rules
        schedule_replicas = {r.replicas for r in rule.spec.schedule}
        if rule.spec.default.replicas not in schedule_replicas:
            warnings.append(
                f"Default replicas ({rule.spec.default.replicas}) differs from all schedule rules "
                f"({sorted(schedule_replicas)}). Ensure this is intentional."
            )

        # Warn about rules with only dates (one-time events)
        for schedule_rule in rule.spec.schedule:
            if schedule_rule.dates and not schedule_rule.days:
                warnings.append(
                    f"Rule '{schedule_rule.name}' uses specific dates without recurring days. "
                    "This rule will only apply on those specific dates."
                )

        # Warn about time ranges without days or dates
        for schedule_rule in rule.spec.schedule:
            if (schedule_rule.time_start or schedule_rule.time_end) and not schedule_rule.days and not schedule_rule.dates:
                errors.append(
                    f"Rule '{schedule_rule.name}' specifies time range but no days or dates. "
                    "Time ranges must be combined with days or dates."
                )

        valid = len(errors) == 0
        return ValidationResult(valid=valid, errors=errors, warnings=warnings)

    @staticmethod
    def validate_from_dict(data: dict) -> ValidationResult:
        """
        Validate configuration from a dictionary.

        Args:
            data: Dictionary containing configuration

        Returns:
            ValidationResult with any errors or warnings
        """
        try:
            rule = ScalingRule.model_validate(data)
            return ConfigValidator.validate(rule)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                loc = " -> ".join(str(x) for x in error["loc"])
                errors.append(f"{loc}: {error['msg']}")
            return ValidationResult(valid=False, errors=errors)

    @staticmethod
    def quick_validate(rule: ScalingRule) -> bool:
        """
        Quickly validate a ScalingRule (only checks for errors, not warnings).

        Args:
            rule: The ScalingRule to validate

        Returns:
            True if valid, False otherwise
        """
        result = ConfigValidator.validate(rule)
        return result.valid
