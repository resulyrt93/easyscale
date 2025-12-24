"""Pydantic models for EasyScale configuration."""

from datetime import date, time
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class DayOfWeek(str, Enum):
    """Days of the week enumeration."""

    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


class TargetResource(BaseModel):
    """Target Kubernetes resource to scale."""

    kind: Literal["Deployment", "StatefulSet"] = Field(
        description="Type of Kubernetes resource to scale"
    )
    name: str = Field(description="Name of the resource")
    namespace: str = Field(default="default", description="Namespace of the resource")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate resource name follows Kubernetes naming conventions."""
        if not v:
            raise ValueError("Resource name cannot be empty")
        if len(v) > 253:
            raise ValueError("Resource name cannot exceed 253 characters")
        return v


class ScheduleRule(BaseModel):
    """Scheduling rule for scaling operations."""

    name: str = Field(description="Human-readable name for this rule")
    days: Optional[list[DayOfWeek]] = Field(
        default=None,
        description="Days of week when this rule applies"
    )
    dates: Optional[list[date]] = Field(
        default=None,
        description="Specific dates when this rule applies (YYYY-MM-DD)"
    )
    time_start: Optional[time] = Field(
        default=None,
        alias="timeStart",
        description="Start time for this rule (HH:MM format)"
    )
    time_end: Optional[time] = Field(
        default=None,
        alias="timeEnd",
        description="End time for this rule (HH:MM format)"
    )
    replicas: int = Field(
        ge=0,
        description="Desired number of replicas when this rule is active"
    )
    priority: int = Field(
        default=0,
        description="Priority for conflict resolution (higher value = higher priority)"
    )
    timezone: str = Field(
        default="UTC",
        description="Timezone for time-based rules (e.g., 'UTC', 'America/New_York')"
    )

    @model_validator(mode="after")
    def validate_time_range(self) -> "ScheduleRule":
        """Validate that time_start comes before time_end if both are specified."""
        if self.time_start and self.time_end:
            # Note: This is a simple check. Rules spanning midnight need special handling
            if self.time_start >= self.time_end:
                raise ValueError(
                    f"time_start ({self.time_start}) must be before time_end ({self.time_end}). "
                    "For rules spanning midnight, create two separate rules."
                )
        return self

    @model_validator(mode="after")
    def validate_schedule_rule(self) -> "ScheduleRule":
        """Validate that at least one scheduling condition is specified."""
        if not self.days and not self.dates:
            raise ValueError("At least one of 'days' or 'dates' must be specified")
        return self

    model_config = {"populate_by_name": True}


class DefaultConfig(BaseModel):
    """Default scaling configuration when no rules match."""

    replicas: int = Field(
        ge=0,
        description="Default number of replicas when no schedule rules match"
    )


class ScalingLimits(BaseModel):
    """Safety limits for scaling operations."""

    min_replicas: int = Field(
        ge=0,
        alias="minReplicas",
        description="Minimum allowed replicas"
    )
    max_replicas: int = Field(
        ge=1,
        alias="maxReplicas",
        description="Maximum allowed replicas"
    )

    @model_validator(mode="after")
    def validate_limits(self) -> "ScalingLimits":
        """Validate that min_replicas <= max_replicas."""
        if self.min_replicas > self.max_replicas:
            raise ValueError(
                f"min_replicas ({self.min_replicas}) cannot be greater than "
                f"max_replicas ({self.max_replicas})"
            )
        return self

    model_config = {"populate_by_name": True}


class Metadata(BaseModel):
    """Metadata for scaling rules."""

    name: str = Field(description="Name of the scaling rule")
    namespace: Optional[str] = Field(
        default=None,
        description="Namespace for this rule (if different from target)"
    )
    labels: Optional[dict[str, str]] = Field(
        default=None,
        description="Optional labels for organization"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate rule name."""
        if not v:
            raise ValueError("Rule name cannot be empty")
        if len(v) > 253:
            raise ValueError("Rule name cannot exceed 253 characters")
        return v


class ScalingSpec(BaseModel):
    """Specification for scaling behavior."""

    target: TargetResource = Field(description="Target resource to scale")
    schedule: list[ScheduleRule] = Field(
        min_length=1,
        description="List of scheduling rules"
    )
    default: DefaultConfig = Field(description="Default scaling configuration")
    limits: Optional[ScalingLimits] = Field(
        default=None,
        description="Optional safety limits for scaling"
    )

    @model_validator(mode="after")
    def validate_default_within_limits(self) -> "ScalingSpec":
        """Validate that default replicas are within limits if specified."""
        if self.limits:
            if self.default.replicas < self.limits.min_replicas:
                raise ValueError(
                    f"Default replicas ({self.default.replicas}) cannot be less than "
                    f"min_replicas ({self.limits.min_replicas})"
                )
            if self.default.replicas > self.limits.max_replicas:
                raise ValueError(
                    f"Default replicas ({self.default.replicas}) cannot be greater than "
                    f"max_replicas ({self.limits.max_replicas})"
                )
        return self

    @model_validator(mode="after")
    def validate_schedule_replicas_within_limits(self) -> "ScalingSpec":
        """Validate that all schedule rule replicas are within limits if specified."""
        if self.limits:
            for rule in self.schedule:
                if rule.replicas < self.limits.min_replicas:
                    raise ValueError(
                        f"Rule '{rule.name}' replicas ({rule.replicas}) cannot be less than "
                        f"min_replicas ({self.limits.min_replicas})"
                    )
                if rule.replicas > self.limits.max_replicas:
                    raise ValueError(
                        f"Rule '{rule.name}' replicas ({rule.replicas}) cannot be greater than "
                        f"max_replicas ({self.limits.max_replicas})"
                    )
        return self


class ScalingRule(BaseModel):
    """Root model for EasyScale scaling rules."""

    api_version: str = Field(
        default="easyscale.io/v1",
        alias="apiVersion",
        description="API version"
    )
    kind: Literal["ScalingRule"] = Field(
        default="ScalingRule",
        description="Kind of resource"
    )
    metadata: Metadata = Field(description="Rule metadata")
    spec: ScalingSpec = Field(description="Scaling specification")

    model_config = {"populate_by_name": True}
