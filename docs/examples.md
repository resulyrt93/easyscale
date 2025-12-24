# Examples

Real-world examples of EasyScale scaling rules for common use cases.

## Cost Optimization

### Scale Down Non-Production After Hours

Save costs by scaling down development and staging environments outside business hours.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: dev-after-hours
  namespace: development
spec:
  target:
    kind: Deployment
    name: api-service
    namespace: development
  schedule:
    - name: "Business hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "08:00"
      timeEnd: "18:00"
      replicas: 3
      timezone: "America/New_York"
  default:
    replicas: 0  # Shut down outside business hours
```

### Weekend Scale Down

Reduce capacity during weekends when traffic is lower.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: weekend-scale
  namespace: production
spec:
  target:
    kind: Deployment
    name: backend-api
    namespace: production
  schedule:
    - name: "Weekend"
      days: [Saturday, Sunday]
      replicas: 5
  default:
    replicas: 15
  limits:
    minReplicas: 3
    maxReplicas: 20
```

## Peak Traffic Handling

### Daily Lunch Rush

Scale up during predictable peak periods.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: lunch-rush-scaling
  namespace: production
spec:
  target:
    kind: Deployment
    name: food-delivery-api
    namespace: production
  schedule:
    - name: "Lunch rush"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "11:30"
      timeEnd: "13:30"
      replicas: 20
      priority: 100
      timezone: "America/Los_Angeles"
  default:
    replicas: 8
```

### Business Hours Baseline

Maintain higher capacity during business hours.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: business-hours
  namespace: production
spec:
  target:
    kind: Deployment
    name: customer-portal
    namespace: production
  schedule:
    - name: "Peak hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "14:00"
      timeEnd: "16:00"
      replicas: 15
      priority: 200

    - name: "Business hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "09:00"
      timeEnd: "17:00"
      replicas: 10
      priority: 100
  default:
    replicas: 5
```

## Special Events

### Black Friday / Cyber Monday

Prepare for high-traffic events.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: black-friday-scaling
  namespace: ecommerce
spec:
  target:
    kind: Deployment
    name: checkout-service
    namespace: ecommerce
  schedule:
    - name: "Black Friday weekend"
      dates: ["2025-11-28", "2025-11-29", "2025-11-30"]
      replicas: 50
      priority: 300

    - name: "Cyber Monday"
      dates: ["2025-12-01"]
      replicas: 45
      priority: 300

    - name: "Holiday preparation"
      dates: ["2025-11-24", "2025-11-25", "2025-11-26", "2025-11-27"]
      replicas: 30
      priority: 200
  default:
    replicas: 10
  limits:
    minReplicas: 5
    maxReplicas: 100
```

### Conference or Product Launch

Scale for anticipated traffic spikes.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: product-launch
  namespace: marketing
spec:
  target:
    kind: Deployment
    name: landing-page
    namespace: marketing
  schedule:
    - name: "Launch day"
      dates: ["2025-06-15"]
      timeStart: "09:00"
      timeEnd: "23:00"
      replicas: 30
      priority: 300
      timezone: "America/New_York"

    - name: "Launch week"
      dates: ["2025-06-16", "2025-06-17", "2025-06-18", "2025-06-19"]
      replicas: 20
      priority: 200
  default:
    replicas: 3
```

## Multi-Region Operations

### Follow-the-Sun Scaling

Scale based on business hours across different regions.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: global-support-scaling
  namespace: support
spec:
  target:
    kind: Deployment
    name: support-api
    namespace: support
  schedule:
    # APAC business hours (Tokyo time)
    - name: "APAC hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "09:00"
      timeEnd: "18:00"
      replicas: 15
      priority: 100
      timezone: "Asia/Tokyo"

    # EMEA business hours (London time)
    - name: "EMEA hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "09:00"
      timeEnd: "18:00"
      replicas: 15
      priority: 100
      timezone: "Europe/London"

    # Americas business hours (New York time)
    - name: "Americas hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "09:00"
      timeEnd: "18:00"
      replicas: 15
      priority: 100
      timezone: "America/New_York"
  default:
    replicas: 5  # Minimal coverage during off-hours
```

## Development Workflows

### Testing Environment Auto-Shutdown

Automatically shut down test environments after work hours.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: test-env-auto-shutdown
  namespace: testing
spec:
  target:
    kind: Deployment
    name: test-api
    namespace: testing
  schedule:
    - name: "Testing hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "07:00"
      timeEnd: "20:00"
      replicas: 2
  default:
    replicas: 0  # Shut down overnight and weekends
```

### Staging Environment Schedule

Keep staging environment available during work hours only.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: staging-schedule
  namespace: staging
spec:
  target:
    kind: Deployment
    name: staging-app
    namespace: staging
  schedule:
    - name: "Work hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "08:00"
      timeEnd: "19:00"
      replicas: 3
      timezone: "America/Los_Angeles"
  default:
    replicas: 1  # Minimal for automated tests
```

## Batch Processing

### Nightly Batch Job Scaling

Scale up for scheduled batch processing.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: batch-processor-scaling
  namespace: data
spec:
  target:
    kind: Deployment
    name: batch-processor
    namespace: data
  schedule:
    - name: "Nightly processing"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday]
      timeStart: "23:00"
      timeEnd: "05:00"
      replicas: 10
      timezone: "UTC"
  default:
    replicas: 1  # Keep one for ad-hoc jobs
```

## Machine Learning Workloads

### Model Training Schedule

Scale ML training infrastructure during off-peak hours.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: ml-training-schedule
  namespace: ml
spec:
  target:
    kind: StatefulSet
    name: training-workers
    namespace: ml
  schedule:
    - name: "Training window"
      days: [Saturday, Sunday]
      replicas: 20
      priority: 200

    - name: "Night training"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "20:00"
      timeEnd: "06:00"
      replicas: 10
      priority: 100
  default:
    replicas: 2  # Minimal for inference
```

### Inference API Scaling

Scale inference API based on usage patterns.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: inference-api-scaling
  namespace: ml
spec:
  target:
    kind: Deployment
    name: inference-api
    namespace: ml
  schedule:
    - name: "Peak inference hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "09:00"
      timeEnd: "17:00"
      replicas: 15
      timezone: "America/New_York"

    - name: "Weekend"
      days: [Saturday, Sunday]
      replicas: 3
  default:
    replicas: 5
  limits:
    minReplicas: 2
    maxReplicas: 30
```

## Gaming Applications

### Game Server Scaling

Scale game servers based on player activity patterns.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: game-server-scaling
  namespace: gaming
spec:
  target:
    kind: StatefulSet
    name: game-servers
    namespace: gaming
  schedule:
    - name: "Weekend peak"
      days: [Saturday, Sunday]
      timeStart: "10:00"
      timeEnd: "02:00"
      replicas: 50
      priority: 200

    - name: "Evening peak"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "18:00"
      timeEnd: "23:00"
      replicas: 30
      priority: 100
  default:
    replicas: 10
  limits:
    minReplicas: 5
    maxReplicas: 100
```

## Database Workloads

### Read Replica Scaling

Scale read replicas based on query patterns.

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: read-replica-scaling
  namespace: database
spec:
  target:
    kind: StatefulSet
    name: postgres-read-replicas
    namespace: database
  schedule:
    - name: "Business hours high load"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "09:00"
      timeEnd: "18:00"
      replicas: 5

    - name: "Night load"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "23:00"
      timeEnd: "05:00"
      replicas: 3  # Analytics queries
  default:
    replicas: 2
  limits:
    minReplicas: 1
    maxReplicas: 10
```

## Tips for Creating Rules

### 1. Start Simple

Begin with basic day-based or time-based rules:

```yaml
schedule:
  - name: "Weekdays"
    days: [Monday, Tuesday, Wednesday, Thursday, Friday]
    replicas: 10
```

### 2. Add Time Ranges Gradually

```yaml
schedule:
  - name: "Business hours"
    days: [Monday, Tuesday, Wednesday, Thursday, Friday]
    timeStart: "09:00"
    timeEnd: "17:00"
    replicas: 10
```

### 3. Use Priority for Overlaps

```yaml
schedule:
  - name: "Lunch peak"
    days: [Monday, Tuesday, Wednesday, Thursday, Friday]
    timeStart: "12:00"
    timeEnd: "14:00"
    replicas: 15
    priority: 200  # Higher priority

  - name: "Business hours"
    days: [Monday, Tuesday, Wednesday, Thursday, Friday]
    timeStart: "09:00"
    timeEnd: "17:00"
    replicas: 10
    priority: 100  # Lower priority
```

### 4. Test with Dry-Run

```bash
# Test rules without actually scaling
python -m easyscale --rules-dir ./rules --kubeconfig --dry-run --log-level DEBUG
```

### 5. Monitor and Adjust

Check logs to see rule evaluations:

```bash
kubectl logs -n easyscale-system deployment/easyscale-controller -f
```

## Next Steps

- [Configuration Reference](configuration.md) - Detailed configuration options
- [Architecture](architecture.md) - How EasyScale works internally
- [FAQ](faq.md) - Common questions and troubleshooting
