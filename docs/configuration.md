# Configuration Reference

Complete reference for configuring EasyScale scaling rules.

## ScalingRule Specification

A `ScalingRule` is a Kubernetes custom resource that defines when and how to scale your workloads.

### Basic Structure

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: <rule-name>
  namespace: <namespace>
spec:
  target:
    kind: <Deployment|StatefulSet>
    name: <resource-name>
    namespace: <namespace>
  schedule:
    - name: <schedule-name>
      days: [<day-list>]
      dates: [<date-list>]
      timeStart: <HH:MM>
      timeEnd: <HH:MM>
      replicas: <number>
      priority: <number>
      timezone: <timezone>
  default:
    replicas: <number>
  limits:
    minReplicas: <number>
    maxReplicas: <number>
```

## Metadata

### name (required)
The name of the scaling rule. Must be unique within the namespace.

**Example:**
```yaml
metadata:
  name: production-api-scaling
```

### namespace (optional)
The Kubernetes namespace where the rule is stored. Defaults to `default`.

**Example:**
```yaml
metadata:
  name: my-rule
  namespace: production
```

### labels (optional)
Standard Kubernetes labels for organizing rules.

**Example:**
```yaml
metadata:
  name: my-rule
  labels:
    environment: production
    team: platform
```

## Target Resource

Specifies which Kubernetes resource to scale.

### kind (required)
Type of resource to scale. Supported values:
- `Deployment`
- `StatefulSet`

### name (required)
Name of the resource to scale.

### namespace (required)
Namespace where the resource is located.

**Example:**
```yaml
target:
  kind: Deployment
  name: api-service
  namespace: production
```

## Schedule Rules

An array of scheduling rules that define when to scale. Rules are evaluated in priority order.

### name (required)
Descriptive name for the schedule rule.

**Example:**
```yaml
- name: "Business hours"
```

### days (optional)
Array of days when the rule applies. Valid values:
- `Monday`
- `Tuesday`
- `Wednesday`
- `Thursday`
- `Friday`
- `Saturday`
- `Sunday`

**Example:**
```yaml
days: [Monday, Tuesday, Wednesday, Thursday, Friday]
```

### dates (optional)
Array of specific dates when the rule applies. Format: `YYYY-MM-DD`

**Example:**
```yaml
dates: ["2025-12-25", "2025-12-26", "2026-01-01"]
```

### timeStart (optional)
Start time for the rule in 24-hour format (`HH:MM`). Inclusive.

**Example:**
```yaml
timeStart: "09:00"
```

### timeEnd (optional)
End time for the rule in 24-hour format (`HH:MM`). Exclusive.

**Example:**
```yaml
timeEnd: "17:00"
```

### replicas (required)
Number of replicas to scale to when this rule matches.

**Example:**
```yaml
replicas: 10
```

### priority (optional)
Priority level for conflict resolution. Higher numbers win. Default: `0`

**Example:**
```yaml
priority: 100
```

### timezone (optional)
IANA timezone for time-based rules. Default: `UTC`

Common timezones:
- `UTC`
- `America/New_York`
- `America/Los_Angeles`
- `Europe/London`
- `Europe/Paris`
- `Asia/Tokyo`
- `Australia/Sydney`

**Example:**
```yaml
timezone: "America/New_York"
```

## Default Configuration

Specifies the default number of replicas when no schedule rules match.

### replicas (required)
Default number of replicas.

**Example:**
```yaml
default:
  replicas: 5
```

## Limits (optional)

Safety constraints to prevent scaling beyond specified bounds.

### minReplicas (optional)
Minimum number of replicas. EasyScale will never scale below this value.

### maxReplicas (optional)
Maximum number of replicas. EasyScale will never scale above this value.

**Example:**
```yaml
limits:
  minReplicas: 1
  maxReplicas: 10
```

## Rule Evaluation Logic

### Matching Process

1. **Time Check**: Current time is checked against each rule's time constraints
2. **Day Check**: Current day of week is checked against `days` field
3. **Date Check**: Current date is checked against `dates` field
4. **Priority Resolution**: If multiple rules match, the highest priority wins
5. **Default Fallback**: If no rules match, the default replicas value is used
6. **Limits Application**: Final replica count is constrained by min/max limits

### Priority Resolution

When multiple rules match simultaneously:

```yaml
schedule:
  - name: "Peak hours"
    days: [Monday, Tuesday, Wednesday, Thursday, Friday]
    timeStart: "12:00"
    timeEnd: "14:00"
    replicas: 20
    priority: 200    # Highest priority

  - name: "Business hours"
    days: [Monday, Tuesday, Wednesday, Thursday, Friday]
    timeStart: "09:00"
    timeEnd: "17:00"
    replicas: 10
    priority: 100    # Lower priority
```

At 12:30 on Monday, both rules match, but "Peak hours" wins due to higher priority.

### Time Boundaries

- **timeStart**: Inclusive (rule applies at exactly this time)
- **timeEnd**: Exclusive (rule stops just before this time)

**Example:**
```yaml
timeStart: "09:00"  # Rule starts at 09:00:00
timeEnd: "17:00"    # Rule stops at 16:59:59
```

### Timezone Handling

All time comparisons use the specified timezone:

```yaml
- name: "NY business hours"
  days: [Monday, Tuesday, Wednesday, Thursday, Friday]
  timeStart: "09:00"
  timeEnd: "17:00"
  replicas: 10
  timezone: "America/New_York"  # 9 AM - 5 PM in New York
```

## Complete Examples

### Example 1: Simple Weekend Scaling

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: weekend-scale
  namespace: default
spec:
  target:
    kind: Deployment
    name: api-service
    namespace: default
  schedule:
    - name: "Weekend scale down"
      days: [Saturday, Sunday]
      replicas: 2
  default:
    replicas: 5
```

### Example 2: Business Hours with Peak Times

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: business-hours-scaling
  namespace: production
spec:
  target:
    kind: Deployment
    name: web-api
    namespace: production
  schedule:
    - name: "Lunch rush"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "11:30"
      timeEnd: "13:30"
      replicas: 15
      priority: 200
      timezone: "America/New_York"

    - name: "Business hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "08:00"
      timeEnd: "18:00"
      replicas: 10
      priority: 100
      timezone: "America/New_York"
  default:
    replicas: 3
  limits:
    minReplicas: 2
    maxReplicas: 20
```

### Example 3: Holiday Scaling

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: holiday-scaling
  namespace: ecommerce
spec:
  target:
    kind: Deployment
    name: checkout-service
    namespace: ecommerce
  schedule:
    - name: "Black Friday"
      dates: ["2025-11-28", "2025-11-29"]
      replicas: 30
      priority: 300

    - name: "Holiday season"
      dates: ["2025-12-20", "2025-12-21", "2025-12-22", "2025-12-23", "2025-12-24"]
      replicas: 20
      priority: 200

    - name: "Weekends"
      days: [Saturday, Sunday]
      replicas: 8
      priority: 100
  default:
    replicas: 5
  limits:
    minReplicas: 3
    maxReplicas: 50
```

### Example 4: Multi-Timezone Operations

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: global-api-scaling
  namespace: global
spec:
  target:
    kind: Deployment
    name: global-api
    namespace: global
  schedule:
    # APAC business hours
    - name: "APAC hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "09:00"
      timeEnd: "17:00"
      replicas: 15
      priority: 100
      timezone: "Asia/Tokyo"

    # EMEA business hours
    - name: "EMEA hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "09:00"
      timeEnd: "17:00"
      replicas: 15
      priority: 100
      timezone: "Europe/London"

    # Americas business hours
    - name: "Americas hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "09:00"
      timeEnd: "17:00"
      replicas: 15
      priority: 100
      timezone: "America/New_York"
  default:
    replicas: 5
```

## Validation

EasyScale validates all rules before applying them. Common validation errors:

### Invalid Timezone
```
Error: Invalid timezone 'Invalid/Zone'
```
Use a valid IANA timezone name.

### Time Range Error
```
Error: timeEnd (08:00) must be after timeStart (17:00)
```
Ensure end time is after start time.

### Missing Required Fields
```
Error: 'target.name' is required
```
All required fields must be specified.

### Limit Violations
```
Error: Default replicas (50) exceeds maxReplicas (20)
```
Replica counts must respect min/max limits.

## Best Practices

1. **Use Descriptive Names**: Make rule names clear and descriptive
2. **Set Appropriate Priorities**: Use priority to handle overlapping rules
3. **Test with Dry-Run**: Verify rules with `--dry-run` before applying
4. **Monitor Logs**: Check EasyScale logs to verify rule evaluation
5. **Set Safety Limits**: Use min/max limits to prevent unexpected scaling
6. **Document Complex Rules**: Add comments in your YAML for complex schedules
7. **Use Timezone Carefully**: Ensure timezone matches your intended schedule
8. **Consider Cooldown**: Account for the cooldown period between scaling operations

## Next Steps

- [Examples](examples.md) - See more real-world examples
- [Architecture](architecture.md) - Understand how EasyScale works
- [FAQ](faq.md) - Common questions and answers
