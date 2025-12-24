"""Rule evaluation engine for EasyScale."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from easyscale.config.models import ScalingRule, ScheduleRule
from easyscale.utils.time_utils import (
    format_datetime,
    get_current_datetime,
    is_date_match,
    is_day_match,
    is_time_in_range,
)

logger = logging.getLogger(__name__)


@dataclass
class ScheduleResult:
    """Result of rule evaluation."""

    desired_replicas: int
    matched_rule: Optional[ScheduleRule]
    reason: str
    evaluation_time: datetime

    @property
    def is_default(self) -> bool:
        """Check if result is using default replicas."""
        return self.matched_rule is None


class RuleEvaluator:
    """Evaluate scheduling rules and determine desired replica count."""

    def __init__(self, scaling_rule: ScalingRule):
        """
        Initialize RuleEvaluator.

        Args:
            scaling_rule: The ScalingRule to evaluate
        """
        self.scaling_rule = scaling_rule
        self.target = scaling_rule.spec.target
        self.schedule_rules = scaling_rule.spec.schedule
        self.default_replicas = scaling_rule.spec.default.replicas
        self.limits = scaling_rule.spec.limits

    def evaluate(self, current_time: Optional[datetime] = None) -> ScheduleResult:
        """
        Evaluate all schedule rules and determine desired replica count.

        Args:
            current_time: Time to evaluate at (defaults to now)

        Returns:
            ScheduleResult with desired replicas and matched rule
        """
        if current_time is None:
            # Use UTC as default, rules will be evaluated in their own timezones
            current_time = get_current_datetime("UTC")

        logger.debug(
            f"Evaluating rules for {self.target.kind} {self.target.namespace}/{self.target.name} "
            f"at {format_datetime(current_time)}"
        )

        # Find all matching rules
        matching_rules = []
        for rule in self.schedule_rules:
            if self._rule_matches(rule, current_time):
                matching_rules.append(rule)
                logger.debug(f"Rule '{rule.name}' matches (priority: {rule.priority})")

        # If no rules match, use default
        if not matching_rules:
            logger.info(
                f"No schedule rules match, using default replicas: {self.default_replicas}"
            )
            return ScheduleResult(
                desired_replicas=self._apply_limits(self.default_replicas),
                matched_rule=None,
                reason="No schedule rules matched, using default",
                evaluation_time=current_time
            )

        # Select highest priority rule
        best_rule = max(matching_rules, key=lambda r: r.priority)
        desired_replicas = self._apply_limits(best_rule.replicas)

        logger.info(
            f"Rule '{best_rule.name}' selected (priority: {best_rule.priority}), "
            f"desired replicas: {desired_replicas}"
        )

        return ScheduleResult(
            desired_replicas=desired_replicas,
            matched_rule=best_rule,
            reason=f"Matched rule: {best_rule.name}",
            evaluation_time=current_time
        )

    def _rule_matches(self, rule: ScheduleRule, current_time: datetime) -> bool:
        """
        Check if a schedule rule matches the current time.

        Args:
            rule: ScheduleRule to check
            current_time: Current time to check against

        Returns:
            True if rule matches
        """
        # Convert current time to rule's timezone
        try:
            rule_time = current_time.astimezone(
                get_current_datetime(rule.timezone).tzinfo
            )
        except ValueError as e:
            logger.error(f"Invalid timezone '{rule.timezone}' in rule '{rule.name}': {e}")
            return False

        # Check date match (specific dates)
        if rule.dates:
            if not is_date_match(rule_time.date(), rule.dates):
                logger.debug(
                    f"Rule '{rule.name}': Date {rule_time.date()} not in target dates"
                )
                return False

        # Check day of week match
        if rule.days:
            if not is_day_match(rule_time, rule.days):
                logger.debug(
                    f"Rule '{rule.name}': Day {rule_time.strftime('%A')} not in target days"
                )
                return False

        # Check time range
        if rule.time_start is not None or rule.time_end is not None:
            if not is_time_in_range(rule_time.time(), rule.time_start, rule.time_end):
                logger.debug(
                    f"Rule '{rule.name}': Time {rule_time.time()} not in range "
                    f"[{rule.time_start} - {rule.time_end}]"
                )
                return False

        # All conditions passed
        logger.debug(
            f"Rule '{rule.name}' matches at {format_datetime(rule_time)} "
            f"(timezone: {rule.timezone})"
        )
        return True

    def _apply_limits(self, replicas: int) -> int:
        """
        Apply min/max limits to replica count.

        Args:
            replicas: Desired replica count

        Returns:
            Replica count after applying limits
        """
        if self.limits is None:
            return replicas

        original = replicas
        replicas = max(self.limits.min_replicas, replicas)
        replicas = min(self.limits.max_replicas, replicas)

        if replicas != original:
            logger.info(
                f"Applied limits: {original} -> {replicas} "
                f"(min: {self.limits.min_replicas}, max: {self.limits.max_replicas})"
            )

        return replicas

    def get_next_change_time(self, current_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        Calculate when the next rule change will occur.

        Args:
            current_time: Time to calculate from (defaults to now)

        Returns:
            DateTime when next change will occur, or None if cannot determine

        Note:
            This is a simplified implementation that doesn't account for
            all edge cases. For production, more sophisticated scheduling
            logic would be needed.
        """
        # This would require more complex logic to properly implement
        # For now, return None to indicate we should check periodically
        return None
