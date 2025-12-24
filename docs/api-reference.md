# API Reference

Python API reference for EasyScale core modules.

## Core Modules

### easyscale.config

Configuration loading and validation.

#### ConfigLoader

Load scaling rules from various sources.

```python
from easyscale.config.loader import ConfigLoader

# Load from file
rule = ConfigLoader.load_from_file("rule.yaml")

# Load from dict
rule = ConfigLoader.load_from_dict(config_dict)

# Load from YAML string
rule = ConfigLoader.load_from_yaml_string(yaml_content)

# Load multiple from directory
rules = ConfigLoader.load_multiple_from_directory("/path/to/rules")

# Load from Kubernetes ConfigMap
rules = ConfigLoader.load_from_kubernetes_configmap(configmap_data)
```

#### ConfigValidator

Validate scaling rules.

```python
from easyscale.config.validator import ConfigValidator

# Validate a rule
result = ConfigValidator.validate(rule)

if result.valid:
    print("✓ Rule is valid")
    if result.warnings:
        print(f"Warnings: {result.warnings}")
else:
    print(f"✗ Validation failed: {result.errors}")

# Quick validate from dict
result = ConfigValidator.validate_from_dict(config_dict)

# Quick validate (raises exception on error)
try:
    ConfigValidator.quick_validate(rule)
    print("Valid!")
except ValueError as e:
    print(f"Invalid: {e}")
```

**ValidationResult**:
```python
@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
```

### easyscale.config.models

Pydantic models for configuration.

#### ScalingRule

Main configuration model.

```python
from easyscale.config.models import ScalingRule

rule = ScalingRule(
    api_version="easyscale.io/v1",
    kind="ScalingRule",
    metadata=Metadata(name="my-rule"),
    spec=ScalingSpec(
        target=TargetResource(
            kind="Deployment",
            name="my-app",
            namespace="default"
        ),
        schedule=[
            ScheduleRule(
                name="Business hours",
                days=[DayOfWeek.MONDAY, DayOfWeek.FRIDAY],
                time_start=time(9, 0),
                time_end=time(17, 0),
                replicas=10
            )
        ],
        default=DefaultConfig(replicas=5)
    )
)
```

#### Models

**Metadata**:
```python
class Metadata(BaseModel):
    name: str  # Required
    namespace: str = "default"
    labels: Optional[dict[str, str]] = None
```

**TargetResource**:
```python
class TargetResource(BaseModel):
    kind: Literal["Deployment", "StatefulSet"]  # Required
    name: str  # Required
    namespace: str = "default"
```

**ScheduleRule**:
```python
class ScheduleRule(BaseModel):
    name: str  # Required
    days: Optional[list[DayOfWeek]] = None
    dates: Optional[list[date]] = None
    time_start: Optional[time] = None
    time_end: Optional[time] = None
    replicas: int  # Required, >= 0
    priority: int = 0
    timezone: str = "UTC"
```

**DefaultConfig**:
```python
class DefaultConfig(BaseModel):
    replicas: int  # Required, >= 0
```

**ScalingLimits**:
```python
class ScalingLimits(BaseModel):
    min_replicas: int  # >= 0
    max_replicas: int  # > min_replicas
```

**DayOfWeek** (Enum):
```python
class DayOfWeek(str, Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"
```

### easyscale.controller

Controller components.

#### RuleEvaluator

Evaluate schedule rules to determine desired replicas.

```python
from easyscale.controller.scheduler import RuleEvaluator
from datetime import datetime
import pytz

evaluator = RuleEvaluator(scaling_rule)

# Evaluate at current time
result = evaluator.evaluate()

# Evaluate at specific time
test_time = datetime(2025, 1, 6, 14, 0, 0, tzinfo=pytz.UTC)
result = evaluator.evaluate(test_time)

print(f"Desired replicas: {result.desired_replicas}")
print(f"Matched rule: {result.matched_rule.name if result.matched_rule else 'Default'}")
print(f"Reason: {result.reason}")
print(f"Is default: {result.is_default}")
```

**ScheduleResult**:
```python
@dataclass
class ScheduleResult:
    desired_replicas: int
    matched_rule: Optional[ScheduleRule]
    reason: str
    evaluation_time: datetime

    @property
    def is_default(self) -> bool:
        return self.matched_rule is None
```

#### ScalingExecutor

Execute scaling operations.

```python
from easyscale.controller.scaler import ScalingExecutor
from easyscale.k8s.resource_manager import ResourceManager
from easyscale.utils.state import StateManager

# Initialize components
resource_manager = ResourceManager(k8s_client)
state_manager = StateManager(cooldown_seconds=60)
executor = ScalingExecutor(
    resource_manager=resource_manager,
    state_manager=state_manager,
    dry_run=False
)

# Make scaling decision
decision = executor.make_decision(
    namespace="default",
    name="my-app",
    kind="Deployment",
    schedule_result=schedule_result,
    current_time=datetime.now(pytz.UTC)
)

if decision.should_scale:
    # Execute scaling
    success = executor.execute(
        namespace="default",
        name="my-app",
        kind="Deployment",
        decision=decision,
        current_time=datetime.now(pytz.UTC)
    )

# Or use convenience method
success = executor.process_schedule_result(
    namespace="default",
    name="my-app",
    kind="Deployment",
    schedule_result=schedule_result
)
```

**ScalingDecision**:
```python
@dataclass
class ScalingDecision:
    should_scale: bool
    current_replicas: int
    desired_replicas: int
    reason: str
    rule_name: Optional[str] = None
    in_cooldown: bool = False
```

#### EasyScaleDaemon

Main daemon controller.

```python
from easyscale.controller.daemon import EasyScaleDaemon, DaemonConfig, create_daemon

# Create daemon configuration
config = DaemonConfig(
    check_interval=60,
    cooldown_seconds=60,
    dry_run=False,
    in_cluster=True,
    rules_directory="/etc/easyscale/rules"
)

# Create daemon
daemon = create_daemon(config)

# Or create manually
daemon = EasyScaleDaemon(
    k8s_client=k8s_client,
    state_manager=state_manager,
    check_interval=60,
    dry_run=False
)

# Add rules
daemon.add_rule(scaling_rule)

# Load from directory
count = daemon.load_rules_from_directory("/path/to/rules")

# Check health
health = daemon.health_check()
# {'status': 'healthy', 'rules_count': 5, 'dry_run': False, ...}

# Run daemon (blocking)
daemon.run()
```

### easyscale.k8s

Kubernetes integration.

#### K8sClient

Kubernetes client wrapper.

```python
from easyscale.k8s.client import K8sClient

# Auto-detect configuration
client = K8sClient(in_cluster=True)  # Use in-cluster config
client = K8sClient(in_cluster=False)  # Use kubeconfig

# Test connection
if client.test_connection():
    print("Connected to Kubernetes API")

# Access API clients
apps_v1 = client.apps_v1
core_v1 = client.core_v1
```

#### ResourceManager

Manage Kubernetes resources.

```python
from easyscale.k8s.resource_manager import ResourceManager

manager = ResourceManager(k8s_client)

# Get current replicas
replicas = manager.get_current_replicas(
    kind="Deployment",
    name="my-app",
    namespace="default"
)

# Scale resource
success = manager.scale_resource(
    kind="Deployment",
    name="my-app",
    namespace="default",
    replicas=10,
    dry_run=False
)

# Check if resource exists
exists = manager.resource_exists(
    kind="Deployment",
    name="my-app",
    namespace="default"
)

# Get resource status
status = manager.get_resource_status(
    kind="Deployment",
    name="my-app",
    namespace="default"
)
# {'ready_replicas': 5, 'replicas': 5, 'updated_replicas': 5}
```

### easyscale.utils

Utility functions.

#### StateManager

Track scaling operations and cooldowns.

```python
from easyscale.utils.state import StateManager
from datetime import datetime
import pytz

manager = StateManager(cooldown_seconds=60)

# Check cooldown
in_cooldown = manager.is_in_cooldown(
    namespace="default",
    name="my-app",
    kind="Deployment",
    current_time=datetime.now(pytz.UTC)
)

# Record scaling operation
manager.record_scaling(
    namespace="default",
    name="my-app",
    kind="Deployment",
    rule_name="business-hours",
    previous_replicas=5,
    desired_replicas=10,
    reason="Business hours scale up",
    success=True,
    timestamp=datetime.now(pytz.UTC)
)

# Get history
history = manager.get_history(
    namespace="default",
    name="my-app",
    limit=10
)

for operation in history:
    print(f"{operation.timestamp}: {operation.previous_replicas} -> {operation.desired_replicas}")

# Get resource state
state = manager.get_state("default", "my-app", "Deployment")
print(f"Last scaled: {state.last_scaled_time}")
print(f"Last replicas: {state.last_replicas}")
print(f"Scaling count: {state.scaling_count}")
```

**ResourceState**:
```python
@dataclass
class ResourceState:
    namespace: str
    name: str
    kind: str
    last_scaled_time: Optional[datetime] = None
    last_replicas: Optional[int] = None
    last_rule_name: Optional[str] = None
    scaling_count: int = 0
```

**ScalingOperation**:
```python
@dataclass
class ScalingOperation:
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
```

#### Time Utilities

Helper functions for time operations.

```python
from easyscale.utils.time_utils import (
    get_current_datetime,
    is_date_match,
    is_day_match,
    is_time_in_range,
    format_datetime,
    format_time
)
from datetime import date, time
from easyscale.config.models import DayOfWeek

# Get current datetime in timezone
dt = get_current_datetime("America/New_York")

# Check date match
matches = is_date_match(
    current_date=date(2025, 12, 25),
    target_dates=[date(2025, 12, 25), date(2025, 12, 26)]
)

# Check day match
matches = is_day_match(
    current_datetime=dt,
    target_days=[DayOfWeek.MONDAY, DayOfWeek.FRIDAY]
)

# Check time range
in_range = is_time_in_range(
    current_time=time(14, 30),
    start_time=time(9, 0),
    end_time=time(17, 0)
)

# Format functions
datetime_str = format_datetime(dt)  # "2025-01-06 14:30:00 EST"
time_str = format_time(time(14, 30))  # "14:30"
```

#### Logging

Setup structured logging.

```python
from easyscale.utils.logger import setup_logging

# Setup with defaults
setup_logging()

# Custom configuration
setup_logging(
    level="DEBUG",
    format_type="json"  # or "text"
)
```

## CLI Interface

### Command-Line Tool

```bash
python -m easyscale [OPTIONS]
```

**Options**:
```
--rules-dir DIRECTORY       Directory with ScalingRule YAML files
--check-interval SECONDS    Evaluation cycle interval (default: 60)
--cooldown SECONDS          Cooldown period (default: 60)
--dry-run                   Don't actually scale resources
--kubeconfig                Use local kubeconfig (default: in-cluster)
--log-level LEVEL           DEBUG|INFO|WARNING|ERROR|CRITICAL
--log-format FORMAT         text|json
--version                   Show version
--help                      Show help
```

**Examples**:
```bash
# Production
python -m easyscale --rules-dir /etc/easyscale/rules

# Development
python -m easyscale --rules-dir ./examples --kubeconfig --dry-run --log-level DEBUG

# Custom intervals
python -m easyscale --rules-dir ./rules --check-interval 30 --cooldown 120

# JSON logging
python -m easyscale --rules-dir ./rules --log-format json
```

## Error Handling

### Exceptions

**ConfigurationError**: Invalid configuration
```python
from easyscale.config.loader import ConfigurationError

try:
    rule = ConfigLoader.load_from_file("invalid.yaml")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

**ResourceManagerError**: Kubernetes API errors
```python
from easyscale.k8s.resource_manager import ResourceManagerError

try:
    success = manager.scale_resource(...)
except ResourceManagerError as e:
    print(f"Failed to scale: {e}")
```

**ValidationError**: Pydantic validation errors
```python
from pydantic import ValidationError

try:
    rule = ScalingRule(**invalid_data)
except ValidationError as e:
    print(f"Validation failed: {e}")
```

## Testing

### Unit Testing

```python
import pytest
from easyscale.controller.scheduler import RuleEvaluator
from datetime import datetime
import pytz

def test_rule_evaluation():
    rule = create_test_rule()
    evaluator = RuleEvaluator(rule)

    # Test Monday business hours
    monday_10am = datetime(2025, 1, 6, 10, 0, 0, tzinfo=pytz.UTC)
    result = evaluator.evaluate(monday_10am)

    assert result.desired_replicas == 10
    assert result.matched_rule.name == "Business hours"
```

### Integration Testing

See [tests/test_integration.py](../tests/test_integration.py) for examples.

## Next Steps

- [Examples](examples.md) - Practical usage examples
- [Architecture](architecture.md) - System architecture
- [Configuration Reference](configuration.md) - Detailed configuration options
