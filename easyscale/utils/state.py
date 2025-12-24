"""State management for tracking scaling operations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ResourceState:
    """State for a single resource."""

    namespace: str
    name: str
    kind: str
    last_scaled_time: Optional[datetime] = None
    last_replicas: Optional[int] = None
    last_rule_name: Optional[str] = None
    scaling_count: int = 0


@dataclass
class ScalingOperation:
    """Record of a scaling operation."""

    timestamp: datetime
    namespace: str
    name: str
    kind: str
    rule_name: Optional[str]
    previous_replicas: int
    desired_replicas: int
    reason: str
    success: bool
    error: Optional[str] = None


class StateManager:
    """Manages state for scaling operations."""

    def __init__(self, cooldown_seconds: int = 60):
        """
        Initialize state manager.

        Args:
            cooldown_seconds: Minimum seconds between scaling operations for same resource
        """
        self.cooldown_seconds = cooldown_seconds
        self._states: dict[str, ResourceState] = {}
        self._history: list[ScalingOperation] = []

    def _get_key(self, namespace: str, name: str, kind: str) -> str:
        """Generate unique key for resource."""
        return f"{kind}/{namespace}/{name}"

    def get_state(self, namespace: str, name: str, kind: str) -> ResourceState:
        """
        Get state for a resource.

        Args:
            namespace: Kubernetes namespace
            name: Resource name
            kind: Resource kind (Deployment or StatefulSet)

        Returns:
            ResourceState for the resource
        """
        key = self._get_key(namespace, name, kind)
        if key not in self._states:
            self._states[key] = ResourceState(
                namespace=namespace, name=name, kind=kind
            )
        return self._states[key]

    def is_in_cooldown(
        self, namespace: str, name: str, kind: str, current_time: datetime
    ) -> bool:
        """
        Check if resource is in cooldown period.

        Args:
            namespace: Kubernetes namespace
            name: Resource name
            kind: Resource kind
            current_time: Current time to check against

        Returns:
            True if resource is in cooldown period
        """
        state = self.get_state(namespace, name, kind)
        if state.last_scaled_time is None:
            return False

        elapsed = (current_time - state.last_scaled_time).total_seconds()
        return elapsed < self.cooldown_seconds

    def record_scaling(
        self,
        namespace: str,
        name: str,
        kind: str,
        rule_name: Optional[str],
        previous_replicas: int,
        desired_replicas: int,
        reason: str,
        success: bool,
        timestamp: datetime,
        error: Optional[str] = None,
    ) -> None:
        """
        Record a scaling operation.

        Args:
            namespace: Kubernetes namespace
            name: Resource name
            kind: Resource kind
            rule_name: Name of the rule that triggered scaling
            previous_replicas: Number of replicas before scaling
            desired_replicas: Number of replicas after scaling
            reason: Reason for scaling
            success: Whether scaling was successful
            timestamp: Time of scaling operation
            error: Error message if scaling failed
        """
        # Update state
        state = self.get_state(namespace, name, kind)
        state.last_scaled_time = timestamp
        state.last_replicas = desired_replicas
        state.last_rule_name = rule_name
        state.scaling_count += 1

        # Record operation
        operation = ScalingOperation(
            timestamp=timestamp,
            namespace=namespace,
            name=name,
            kind=kind,
            rule_name=rule_name,
            previous_replicas=previous_replicas,
            desired_replicas=desired_replicas,
            reason=reason,
            success=success,
            error=error,
        )
        self._history.append(operation)

    def get_history(
        self,
        namespace: Optional[str] = None,
        name: Optional[str] = None,
        kind: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[ScalingOperation]:
        """
        Get scaling operation history.

        Args:
            namespace: Filter by namespace (optional)
            name: Filter by name (optional)
            kind: Filter by kind (optional)
            limit: Maximum number of operations to return (optional)

        Returns:
            List of scaling operations, newest first
        """
        filtered = self._history

        if namespace is not None:
            filtered = [op for op in filtered if op.namespace == namespace]
        if name is not None:
            filtered = [op for op in filtered if op.name == name]
        if kind is not None:
            filtered = [op for op in filtered if op.kind == kind]

        # Sort by timestamp descending
        filtered = sorted(filtered, key=lambda op: op.timestamp, reverse=True)

        if limit is not None:
            filtered = filtered[:limit]

        return filtered

    def clear_history(self) -> None:
        """Clear all scaling operation history."""
        self._history.clear()

    def clear_state(self, namespace: str, name: str, kind: str) -> None:
        """
        Clear state for a specific resource.

        Args:
            namespace: Kubernetes namespace
            name: Resource name
            kind: Resource kind
        """
        key = self._get_key(namespace, name, kind)
        if key in self._states:
            del self._states[key]
