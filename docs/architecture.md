# Architecture

Understanding how EasyScale works internally.

## Overview

EasyScale is a Kubernetes-native daemon that continuously evaluates time-based scaling rules and executes scaling operations on your workloads.

```
┌─────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster                     │
│                                                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │            EasyScale Controller                   │   │
│  │                                                    │   │
│  │  ┌──────────────┐      ┌──────────────┐         │   │
│  │  │              │      │              │         │   │
│  │  │  Rule Loader │─────▶│  Validator   │         │   │
│  │  │              │      │              │         │   │
│  │  └──────────────┘      └──────┬───────┘         │   │
│  │                               │                  │   │
│  │                               ▼                  │   │
│  │                    ┌──────────────────┐         │   │
│  │                    │                  │         │   │
│  │                    │  Main Loop       │         │   │
│  │                    │  (Every 60s)     │         │   │
│  │                    │                  │         │   │
│  │                    └────────┬─────────┘         │   │
│  │                             │                   │   │
│  │              ┌──────────────┼──────────────┐   │   │
│  │              │              │              │   │   │
│  │              ▼              ▼              ▼   │   │
│  │      ┌─────────────┐ ┌───────────┐ ┌──────────┐   │   │
│  │      │             │ │           │ │          │   │   │
│  │      │  Scheduler  │ │  Executor │ │  State   │   │   │
│  │      │  Evaluator  │ │           │ │  Manager │   │   │
│  │      │             │ │           │ │          │   │   │
│  │      └──────┬──────┘ └─────┬─────┘ └────┬─────┘   │   │
│  │             │               │            │         │   │
│  └─────────────┼───────────────┼────────────┼─────────┘   │
│                │               │            │             │
│                │               ▼            │             │
│                │      ┌─────────────────┐   │             │
│                │      │                 │   │             │
│                └─────▶│  K8s API Server │◀──┘             │
│                       │                 │                 │
│                       └────────┬────────┘                 │
│                                │                          │
│                                ▼                          │
│                     ┌──────────────────┐                  │
│                     │                  │                  │
│                     │  Deployments /   │                  │
│                     │  StatefulSets    │                  │
│                     │                  │                  │
│                     └──────────────────┘                  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Configuration Loader

**Purpose**: Load and parse scaling rules from YAML files or Kubernetes ConfigMaps.

**Key Features**:
- Loads multiple rules from directory
- Parses YAML into Pydantic models
- Supports hot-reload capabilities
- Handles multiple configuration sources

**Code Location**: `easyscale/config/loader.py`

### 2. Configuration Validator

**Purpose**: Validate rules for correctness before execution.

**Validates**:
- Timezone strings (IANA database)
- Time range consistency
- Replica count bounds
- Priority conflicts
- Schedule completeness

**Returns**: ValidationResult with errors and warnings

**Code Location**: `easyscale/config/validator.py`

### 3. Rule Evaluator (Scheduler)

**Purpose**: Determine desired replica count based on current time and schedule rules.

**Algorithm**:
1. Get current time in rule's timezone
2. Check each schedule rule:
   - Day of week match?
   - Specific date match?
   - Within time range?
3. Collect all matching rules
4. Select highest priority rule
5. Apply min/max limits
6. Return ScheduleResult

**Code Location**: `easyscale/controller/scheduler.py`

**Example Flow**:
```python
# Input: ScalingRule, current_time
# Output: ScheduleResult(desired_replicas=10, matched_rule=..., reason="...")

evaluator = RuleEvaluator(scaling_rule)
result = evaluator.evaluate(current_time)
# result.desired_replicas = 10
# result.matched_rule.name = "Business hours"
# result.reason = "Matched rule: Business hours"
```

### 4. Scaling Executor

**Purpose**: Execute scaling operations on Kubernetes resources.

**Workflow**:
1. **Make Decision**:
   - Check if resource exists
   - Get current replica count
   - Check if already at desired replicas
   - Verify cooldown period
2. **Execute**:
   - Call Kubernetes API to scale
   - Record operation in history
   - Update resource state
   - Log success/failure

**Safety Features**:
- Dry-run mode support
- Cooldown period enforcement
- Error handling and retry
- Operation history tracking

**Code Location**: `easyscale/controller/scaler.py`

### 5. State Manager

**Purpose**: Track scaling operations and prevent thrashing.

**State Tracking**:
- Last scaled time per resource
- Last replica count
- Active rule name
- Scaling operation count

**Cooldown Logic**:
```python
if (current_time - last_scaled_time) < cooldown_seconds:
    # Skip scaling (in cooldown)
    return False
```

**History**:
- All scaling operations recorded
- Filterable by namespace, name, kind
- Includes success/failure status
- Error messages preserved

**Code Location**: `easyscale/utils/state.py`

### 6. Kubernetes Client

**Purpose**: Interact with Kubernetes API.

**Operations**:
- Get current replica count
- Scale resource (Deployment/StatefulSet)
- Check resource existence
- Get resource status

**Configuration**:
- Auto-detects in-cluster vs kubeconfig
- Retry logic for transient failures
- Connection pooling

**Code Location**: `easyscale/k8s/client.py`, `easyscale/k8s/resource_manager.py`

### 7. Main Daemon

**Purpose**: Orchestrate the entire scaling operation.

**Main Loop**:
```python
while not shutdown:
    for each rule in rules:
        # 1. Evaluate schedule
        result = evaluator.evaluate(current_time)

        # 2. Make scaling decision
        decision = executor.make_decision(resource, result, current_time)

        # 3. Execute if needed
        if decision.should_scale:
            executor.execute(resource, decision, current_time)

    # 4. Sleep until next cycle
    sleep(check_interval)
```

**Features**:
- Configurable check interval (default: 60 seconds)
- Graceful shutdown (SIGTERM/SIGINT)
- Health check endpoint
- Error recovery

**Code Location**: `easyscale/controller/daemon.py`

## Data Flow

### 1. Startup

```
1. Parse command-line arguments
2. Setup logging
3. Initialize Kubernetes client
4. Test cluster connection
5. Create state manager
6. Load scaling rules from directory
7. Validate each rule
8. Start main loop
```

### 2. Evaluation Cycle

```
Every 60 seconds (configurable):

For each ScalingRule:
  │
  ├─▶ Get current time in rule's timezone
  │
  ├─▶ Evaluate schedule rules
  │   ├─ Check day of week
  │   ├─ Check specific dates
  │   ├─ Check time range
  │   └─ Select highest priority match
  │
  ├─▶ Make scaling decision
  │   ├─ Check resource exists
  │   ├─ Get current replicas
  │   ├─ Check if change needed
  │   └─ Verify cooldown
  │
  └─▶ Execute scaling (if needed)
      ├─ Call Kubernetes API
      ├─ Record operation
      └─ Update state
```

### 3. Scaling Operation

```
1. Executor receives ScheduleResult
   ├─ desired_replicas = 10
   ├─ matched_rule = "Business hours"
   └─ reason = "Matched rule: Business hours"

2. Make Decision:
   ├─ Current replicas: 5
   ├─ Desired replicas: 10
   ├─ Should scale: True
   └─ In cooldown: False

3. Execute:
   ├─ API call: PATCH /apis/apps/v1/namespaces/default/deployments/my-app/scale
   ├─ Body: {"spec": {"replicas": 10}}
   └─ Success: True

4. Record:
   ├─ State: last_replicas = 10, last_time = now
   ├─ History: Add ScalingOperation record
   └─ Logs: "Scaled Deployment/default/my-app to 10 replicas"
```

## Rule Evaluation Algorithm

### Priority Resolution

```python
def evaluate(self, current_time):
    matching_rules = []

    for rule in self.schedule_rules:
        if self._matches(rule, current_time):
            matching_rules.append(rule)

    if matching_rules:
        # Select highest priority
        best_rule = max(matching_rules, key=lambda r: r.priority)
        desired = best_rule.replicas
    else:
        # Use default
        desired = self.default_replicas

    # Apply limits
    if self.limits:
        desired = max(self.limits.min_replicas, desired)
        desired = min(self.limits.max_replicas, desired)

    return ScheduleResult(
        desired_replicas=desired,
        matched_rule=best_rule if matching_rules else None,
        reason="...",
        evaluation_time=current_time
    )
```

### Time Matching

```python
def _matches_time(self, rule, current_time):
    # Get time components
    current_hour_min = current_time.time()

    # Check start time (inclusive)
    if rule.time_start and current_hour_min < rule.time_start:
        return False

    # Check end time (exclusive)
    if rule.time_end and current_hour_min >= rule.time_end:
        return False

    return True
```

### Day Matching

```python
def _matches_day(self, rule, current_time):
    if not rule.days:
        return True

    # Get day of week (Monday=0, Sunday=6)
    current_day = DayOfWeek(current_time.strftime("%A"))

    return current_day in rule.days
```

## Performance Considerations

### Evaluation Frequency

- **Default**: 60 seconds
- **Minimum**: 1 second (not recommended)
- **Trade-off**: Faster checks = more CPU usage

### Cooldown Period

- **Purpose**: Prevent rapid scaling (thrashing)
- **Default**: 60 seconds
- **Per Resource**: Each resource has independent cooldown

### Scalability

- **Rules**: Handles 100+ rules efficiently
- **Memory**: ~50-100MB baseline + ~1KB per rule
- **CPU**: Minimal (<0.1 core for 100 rules)

### Kubernetes API Load

- **Read Operations**: `check_interval * num_rules` per minute
- **Write Operations**: Only when scaling needed
- **Best Practice**: Use `check_interval >= 30` for production

## High Availability

### Single Controller

Current design: Single controller instance

**Pros**:
- Simple architecture
- No coordination needed
- Predictable behavior

**Cons**:
- Single point of failure
- No horizontal scaling

### Future: Multiple Controllers

For HA deployments (future):
- Leader election
- Distributed state management
- Shared history in ConfigMap/etcd

## Security

### RBAC Permissions

Minimum required permissions:

```yaml
rules:
  # Read workloads
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets"]
    verbs: ["get", "list", "watch"]

  # Scale workloads
  - apiGroups: ["apps"]
    resources: ["deployments/scale", "statefulsets/scale"]
    verbs: ["get", "update", "patch"]

  # Manage CRDs
  - apiGroups: ["easyscale.io"]
    resources: ["scalingrules"]
    verbs: ["get", "list", "watch"]

  # Create events
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["create", "patch"]
```

### Best Practices

1. **Namespace Isolation**: Deploy in dedicated namespace
2. **ServiceAccount**: Use dedicated ServiceAccount
3. **Network Policies**: Restrict ingress/egress
4. **Resource Limits**: Set CPU/memory limits
5. **Audit Logs**: Enable Kubernetes audit logging

## Monitoring

### Logs

Structured logs with levels:
- **DEBUG**: Evaluation details, rule matching
- **INFO**: Scaling operations, rule loading
- **WARNING**: Validation warnings, retries
- **ERROR**: Failures, API errors

### Metrics (Future)

Planned Prometheus metrics:
- `easyscale_rules_total`: Total scaling rules
- `easyscale_evaluations_total`: Total evaluations
- `easyscale_scaling_operations_total`: Scaling operations
- `easyscale_scaling_failures_total`: Failed operations
- `easyscale_evaluation_duration_seconds`: Evaluation time

### Health Checks

- **Liveness**: Process running
- **Readiness**: Kubernetes API accessible
- **Health Endpoint**: Returns daemon status

## Testing

### Unit Tests

- Configuration models
- Rule evaluation logic
- State management
- Kubernetes client

**Coverage**: 86%

### Integration Tests

- End-to-end workflows
- Multiple rules evaluation
- Cooldown enforcement
- Dry-run mode

**Total**: 194 tests passing

### Local Testing

```bash
# Run with dry-run
python -m easyscale \
  --rules-dir ./examples \
  --kubeconfig \
  --dry-run \
  --log-level DEBUG
```

## Extensibility

### Adding New Features

1. **Custom Metrics**: Extend RuleEvaluator for CPU/memory-based scaling
2. **Webhooks**: Add notification on scaling events
3. **Multiple Namespaces**: Watch rules across namespaces
4. **Rule Templates**: Support for reusable rule templates

### Plugin Architecture (Future)

- **Metric Providers**: Prometheus, Datadog, custom
- **Notifiers**: Slack, email, PagerDuty
- **Decision Engines**: Custom scaling algorithms

## Limitations

### Current Limitations

1. **No HPA Integration**: Doesn't work with Kubernetes HPA
2. **Time-Based Only**: No metric-based scaling (yet)
3. **Single Controller**: No HA support
4. **CRD Watch**: Currently loads from directory, not CRD watch

### Future Enhancements

- CRD-based rule management
- Metric-based scaling integration
- Multi-controller HA setup
- Webhook support for notifications
- Web UI for rule management

## Next Steps

- [Configuration Reference](configuration.md) - Detailed options
- [Examples](examples.md) - Real-world use cases
- [FAQ](faq.md) - Common questions
