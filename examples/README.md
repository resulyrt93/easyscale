# EasyScale Configuration Examples

This directory contains example configurations for EasyScale.

## Examples Overview

### 1. [basic-schedule.yaml](basic-schedule.yaml)
The simplest example showing weekend scaling.
- Scales down to 2 replicas on weekends
- Runs 5 replicas on weekdays (default)

**Use case**: Reduce costs during low-traffic weekend periods.

### 2. [simple-time-based.yaml](simple-time-based.yaml)
Simple time-based scaling for business hours.
- 5 replicas during business hours (8 AM - 8 PM, Mon-Fri)
- 2 replicas outside business hours

**Use case**: Match capacity with expected traffic patterns.

### 3. [business-hours.yaml](business-hours.yaml)
More sophisticated business hours with peak times.
- 5 replicas during peak hours (4 PM - 6 PM)
- 3 replicas during regular business hours (9 AM - 6 PM)
- 1 replica outside business hours
- Uses priority to handle overlapping rules

**Use case**: Handle peak traffic periods with extra capacity.

### 4. [advanced-schedule.yaml](advanced-schedule.yaml)
Complex schedule with multiple conditions.
- Holiday-specific scaling (specific dates)
- Late night scale down on weekdays
- Weekend minimal capacity
- Safety limits to prevent over-scaling

**Use case**: Production ML service with predictable usage patterns and holiday considerations.

## Configuration Fields

### Required Fields
- `apiVersion`: Always `easyscale.io/v1`
- `kind`: Always `ScalingRule`
- `metadata.name`: Unique name for this rule
- `spec.target`: The Kubernetes resource to scale
- `spec.schedule`: At least one scheduling rule
- `spec.default`: Default replica count

### Optional Fields
- `metadata.labels`: Labels for organization
- `spec.limits`: Min/max replica constraints
- Schedule rule `priority`: For resolving conflicts (higher wins)
- Schedule rule `timezone`: Defaults to UTC

## Testing Your Configuration

Validate your configuration before deploying:

```bash
# Validate a configuration file
easyscale validate examples/basic-schedule.yaml

# Dry-run to see what would happen
easyscale dry-run examples/basic-schedule.yaml
```

## Tips

1. **Priorities**: Use priorities when rules might overlap. Higher priority wins.
2. **Timezones**: Always specify timezone for time-based rules to avoid confusion.
3. **Limits**: Use limits to prevent accidental over-scaling and control costs.
4. **Testing**: Start with simple rules and gradually add complexity.
5. **Midnight spanning**: Rules cannot span midnight. Create two separate rules instead.
