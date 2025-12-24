# Frequently Asked Questions

Common questions and answers about EasyScale.

## General

### What is EasyScale?

EasyScale is a Kubernetes-native daemon that automatically scales your workloads (Deployments and StatefulSets) based on time-based schedules. It's perfect for predictable workloads that need different capacity at different times.

### How is EasyScale different from Kubernetes HPA?

| Feature | EasyScale | Kubernetes HPA |
|---------|-----------|----------------|
| Scaling Trigger | Time-based schedules | CPU/Memory metrics |
| Use Case | Predictable patterns | Dynamic load response |
| Configuration | Simple YAML rules | Metric queries |
| Works With | Deployments, StatefulSets | Deployments, StatefulSets, ReplicationControllers |
| Can Combine | ❌ Not compatible | ✅ With metric-based HPAs |

**Best Practice**: Use EasyScale for predictable time-based scaling and HPA for dynamic metric-based scaling. Don't use both on the same resource.

### Does EasyScale support Horizontal Pod Autoscaler (HPA)?

Currently, EasyScale does not integrate with HPA. If a resource has HPA configured, EasyScale's scaling operations may conflict with HPA's decisions. We recommend using EasyScale for resources without HPA.

### What Kubernetes versions are supported?

EasyScale supports Kubernetes 1.19 and higher.

## Configuration

### How many scaling rules can I create?

There's no hard limit, but we recommend keeping it reasonable (< 100 rules per cluster) for performance. Each rule is evaluated on every check cycle.

### Can I have multiple rules for the same resource?

No. Each resource (Deployment/StatefulSet) should have only one ScalingRule. However, that rule can have multiple schedule entries with different priorities.

### What happens if I have overlapping schedule times?

EasyScale uses priority-based resolution. The rule with the highest `priority` value wins. If priorities are equal, the first matching rule is used.

**Example**:
```yaml
schedule:
  - name: "Peak hours"
    timeStart: "12:00"
    timeEnd: "14:00"
    replicas: 20
    priority: 200  # This wins during 12:00-14:00

  - name: "Business hours"
    timeStart: "09:00"
    timeEnd: "17:00"
    replicas: 10
    priority: 100
```

### What timezone does EasyScale use?

By default, UTC. You can specify any IANA timezone for each schedule rule:

```yaml
schedule:
  - name: "NY business hours"
    timeStart: "09:00"
    timeEnd: "17:00"
    timezone: "America/New_York"
```

### Can I scale to zero replicas?

Yes! This is useful for cost optimization:

```yaml
default:
  replicas: 0  # Shut down when no rules match
```

However, ensure your application can handle cold starts.

### How do I test my rules without affecting production?

Use dry-run mode:

```bash
python -m easyscale --rules-dir ./rules --kubeconfig --dry-run --log-level DEBUG
```

This evaluates rules and logs what would happen, but doesn't actually scale anything.

## Operations

### How often does EasyScale check and evaluate rules?

By default, every 60 seconds. This is configurable:

```bash
python -m easyscale --rules-dir ./rules --check-interval 30
```

Or in Helm:
```bash
helm install easyscale easyscale/easyscale --set checkInterval=30
```

### What is the cooldown period?

The cooldown period prevents rapid scaling (thrashing). After a resource is scaled, EasyScale waits for the cooldown period before scaling it again.

**Default**: 60 seconds

**Configure**:
```bash
python -m easyscale --rules-dir ./rules --cooldown 120
```

### Why isn't my resource scaling?

Common reasons:

1. **Current time doesn't match schedule**: Check your days/dates/times
2. **Wrong timezone**: Verify timezone setting
3. **Cooldown active**: Resource was recently scaled
4. **Already at desired replicas**: No scaling needed
5. **Resource doesn't exist**: Check resource name/namespace
6. **Validation errors**: Check EasyScale logs

**Debugging**:
```bash
kubectl logs -n easyscale-system deployment/easyscale-controller -f
```

Use `--log-level DEBUG` for detailed evaluation logs.

### Can I see scaling history?

Yes, check the EasyScale logs:

```bash
kubectl logs -n easyscale-system deployment/easyscale-controller | grep "Scaled"
```

You'll see entries like:
```
Scaled Deployment/default/my-app from 5 to 10 replicas (rule: business-hours)
```

Future versions will expose this via API or metrics.

### How do I update a scaling rule?

Simply edit and reapply:

```bash
kubectl apply -f updated-rule.yaml
```

EasyScale will pick up the changes on the next evaluation cycle (within check_interval seconds).

### How do I delete a scaling rule?

```bash
kubectl delete scalingrule <rule-name>
```

The resource will maintain its current replica count. EasyScale will no longer manage it.

## Troubleshooting

### EasyScale pod is CrashLooping

Check logs for the error:

```bash
kubectl logs -n easyscale-system deployment/easyscale-controller
```

Common issues:
- Can't connect to Kubernetes API (check RBAC)
- Invalid rule configuration (check validation errors)
- Missing rules directory
- Image pull errors

### Scaling happens but then reverts

This could be:

1. **HPA Conflict**: If HPA is configured on the resource, it may override EasyScale
2. **Another Controller**: Check if another tool is managing the resource
3. **Manual Scaling**: Someone/something else is scaling the resource

**Solution**: Ensure only EasyScale manages the resource.

### Timezone issues - scaling at wrong time

Verify timezone setting:

```yaml
schedule:
  - name: "My rule"
    timezone: "America/New_York"  # Use IANA timezone
```

Test with correct timezone:
```bash
python -m easyscale --rules-dir ./rules --kubeconfig --dry-run --log-level DEBUG
```

Check logs for evaluation time in the specified timezone.

### Permission denied errors

EasyScale needs appropriate RBAC permissions. Check ServiceAccount and ClusterRole:

```bash
kubectl get clusterrole easyscale-controller -o yaml
kubectl get clusterrolebinding easyscale-controller -o yaml
```

Ensure it has:
- Read: Deployments, StatefulSets
- Update: Deployments/scale, StatefulSets/scale
- Read: ScalingRules
- Create: Events

## Advanced

### Can I use EasyScale for StatefulSets?

Yes! EasyScale supports both Deployments and StatefulSets:

```yaml
target:
  kind: StatefulSet
  name: my-statefulset
  namespace: default
```

### Can I scale based on metrics (CPU/memory)?

Not currently. EasyScale is focused on time-based scaling. For metric-based scaling, use Kubernetes HPA.

**Future**: We plan to add support for custom metrics and Prometheus integration.

### Can I get notifications when scaling happens?

Not yet. This is planned for a future release.

**Workaround**: Monitor EasyScale logs or Kubernetes events:

```bash
kubectl get events -n default --field-selector involvedObject.name=my-app
```

### Can EasyScale work with multiple clusters?

Yes, but you need to deploy EasyScale to each cluster separately. Each instance manages rules for its cluster only.

**Future**: Multi-cluster support is planned.

### How do I backup my scaling rules?

Rules are Kubernetes resources, so standard backup tools work:

```bash
# Export all rules
kubectl get scalingrules -A -o yaml > rules-backup.yaml

# Restore
kubectl apply -f rules-backup.yaml
```

Or use tools like Velero for comprehensive cluster backups.

### Can I use EasyScale in GitOps workflows?

Absolutely! Store your ScalingRule YAML files in Git and use tools like ArgoCD or Flux:

```
repo/
  ├── applications/
  │   └── my-app/
  │       ├── deployment.yaml
  │       └── scaling-rule.yaml  # EasyScale rule
  └── ...
```

ArgoCD/Flux will sync rules to your cluster automatically.

### What happens if EasyScale pod crashes?

EasyScale is stateless (state is in memory). If it crashes:

1. Kubernetes restarts the pod automatically
2. Rules are reloaded from directory/CRDs
3. Evaluation resumes within one check interval
4. Resources maintain their current replica count

**No data is lost** as rules are stored in Kubernetes.

### Can I run multiple EasyScale instances for HA?

Currently, no. Running multiple instances will cause conflicts as they both try to scale resources.

**Future**: Leader election and HA support are planned.

### How do I monitor EasyScale?

Current options:

1. **Logs**: Use kubectl logs or logging aggregation
2. **Kubernetes Events**: Check events on scaled resources
3. **Health Checks**: Pod readiness/liveness probes

**Future**: Prometheus metrics will be added for monitoring:
- Rule evaluation count
- Scaling operation count
- Failures
- Evaluation duration

## Performance

### What's the resource usage of EasyScale?

Typical usage:
- **CPU**: 50-100m (0.05-0.1 cores)
- **Memory**: 128-256 MB
- **Storage**: Minimal (logs only)

### How many resources can EasyScale manage?

EasyScale is lightweight and can easily manage:
- **100+ scaling rules**
- **500+ resources** (Deployments/StatefulSets)
- **Large clusters** (1000+ nodes)

**Limiting Factor**: Kubernetes API rate limits, not EasyScale itself.

### Does EasyScale put load on the Kubernetes API?

Minimal load:
- **Reads**: `check_interval * num_rules` per minute (default: 1 read per rule per minute)
- **Writes**: Only when scaling needed (typically rare)

**Best Practice**: Use `check_interval >= 30` for production to reduce API calls.

## Comparison

### EasyScale vs Kubernetes CronJob-based scaling

| Feature | EasyScale | CronJob Scripts |
|---------|-----------|-----------------|
| Setup | Simple YAML rules | Write scripts, manage CronJobs |
| Validation | Built-in | Manual |
| Timezone Support | Native | Complex |
| Cooldown | Automatic | Manual implementation |
| Dry-run | Built-in | Manual |
| Audit Log | Automatic | Manual |
| Maintenance | Low | High |

### EasyScale vs KEDA

| Feature | EasyScale | KEDA |
|---------|-----------|------|
| Primary Use | Time-based scaling | Event/metric-based scaling |
| Complexity | Simple | More complex |
| Integrations | None needed | External metrics required |
| Learning Curve | Minimal | Moderate |
| Best For | Predictable patterns | Dynamic events |

## Contributing

### How can I contribute?

We welcome contributions! See:
- [GitHub Repository](https://github.com/resulyrt93/easyscale)
- [Contributing Guide](https://github.com/resulyrt93/easyscale/blob/main/CONTRIBUTING.md)
- [Issue Tracker](https://github.com/resulyrt93/easyscale/issues)

### I found a bug, what should I do?

1. Check if it's a known issue in [GitHub Issues](https://github.com/resulyrt93/easyscale/issues)
2. If not, create a new issue with:
   - EasyScale version
   - Kubernetes version
   - Rule configuration (sanitized)
   - Logs showing the error
   - Steps to reproduce

### I have a feature request

Great! Open a [GitHub Discussion](https://github.com/resulyrt93/easyscale/discussions) or [Issue](https://github.com/resulyrt93/easyscale/issues) describing:
- The feature
- Use case
- Why it would be valuable
- Example configuration (if applicable)

## Still Have Questions?

- 📖 [Documentation](README.md)
- 💬 [GitHub Discussions](https://github.com/resulyrt93/easyscale/discussions)
- 🐛 [Issue Tracker](https://github.com/resulyrt93/easyscale/issues)
