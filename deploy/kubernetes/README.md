# Kubernetes Deployment Manifests

This directory contains Kubernetes manifests for deploying EasyScale to your cluster.

## Quick Install

Install EasyScale with default configuration:

```bash
kubectl apply -f https://raw.githubusercontent.com/resulyrt93/easyscale/main/deploy/kubernetes/install.yaml
```

Or clone the repository and install locally:

```bash
kubectl apply -f deploy/kubernetes/install.yaml
```

## What Gets Installed

The `install.yaml` file includes:

1. **Namespace**: `easyscale-system` - Isolated namespace for EasyScale
2. **CRD**: `ScalingRule` custom resource definition
3. **ServiceAccount**: `easyscale` - Service account for the controller
4. **RBAC**: ClusterRole and ClusterRoleBinding with minimal permissions
5. **Deployment**: EasyScale controller with security best practices

## Individual Manifests

You can also apply manifests individually for more control:

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Install CRD
kubectl apply -f crd.yaml

# Create service account
kubectl apply -f serviceaccount.yaml

# Setup RBAC
kubectl apply -f rbac.yaml

# Deploy controller
kubectl apply -f deployment.yaml

# Optional: Apply example rules
kubectl apply -f configmap.yaml
```

## Configuration

### Using ConfigMap for Rules

The default deployment expects rules in a ConfigMap named `easyscale-rules`:

```bash
# Apply example rules
kubectl apply -f configmap.yaml

# Or create your own
kubectl create configmap easyscale-rules \
  --from-file=my-rules.yaml \
  --namespace=easyscale-system
```

### Using Custom Resources

Alternatively, use ScalingRule CRDs directly:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: my-scaling-rule
  namespace: default
spec:
  target:
    kind: Deployment
    name: my-app
    namespace: default
  schedule:
    - name: "Business hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      time_ranges:
        - start: "09:00"
          end: "18:00"
      replicas: 10
  default:
    replicas: 3
EOF
```

## Customization

### Change Check Interval

Edit `deployment.yaml` and modify the `--check-interval` arg:

```yaml
args:
  - "--check-interval=30"  # Check every 30 seconds
```

### Change Log Level

Modify the `--log-level` arg:

```yaml
args:
  - "--log-level=DEBUG"  # More verbose logging
```

### Resource Limits

Adjust resource requests/limits in `deployment.yaml`:

```yaml
resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### Use Specific Image Version

Change the image tag in `deployment.yaml`:

```yaml
image: resulyrt93/easyscale:v0.1.0  # Pin to specific version
```

## Verification

Check that EasyScale is running:

```bash
# Check deployment status
kubectl get deployment -n easyscale-system

# Check pod logs
kubectl logs -n easyscale-system -l app.kubernetes.io/name=easyscale

# List scaling rules
kubectl get scalingrules --all-namespaces

# Describe a specific rule
kubectl describe scalingrule my-scaling-rule -n default
```

## Monitoring

View EasyScale logs:

```bash
# Follow logs
kubectl logs -n easyscale-system -l app.kubernetes.io/name=easyscale -f

# Get recent logs
kubectl logs -n easyscale-system -l app.kubernetes.io/name=easyscale --tail=100
```

## Troubleshooting

### Controller Not Starting

Check pod events:

```bash
kubectl describe pod -n easyscale-system -l app.kubernetes.io/name=easyscale
```

### RBAC Permission Issues

Verify service account has correct permissions:

```bash
kubectl auth can-i get deployments --as=system:serviceaccount:easyscale-system:easyscale
kubectl auth can-i patch deployments/scale --as=system:serviceaccount:easyscale-system:easyscale
```

### Rules Not Applied

Check rule validation:

```bash
kubectl get scalingrule -n default -o yaml
kubectl logs -n easyscale-system -l app.kubernetes.io/name=easyscale | grep -i error
```

## Uninstall

Remove EasyScale from your cluster:

```bash
kubectl delete -f install.yaml
```

Or manually:

```bash
kubectl delete deployment easyscale-controller -n easyscale-system
kubectl delete clusterrolebinding easyscale-controller
kubectl delete clusterrole easyscale-controller
kubectl delete serviceaccount easyscale -n easyscale-system
kubectl delete crd scalingrules.easyscale.io
kubectl delete namespace easyscale-system
```

## Security

EasyScale follows Kubernetes security best practices:

- **Non-root user**: Runs as UID 1000
- **Read-only root filesystem**: No write access to container filesystem
- **No privilege escalation**: All capabilities dropped
- **Minimal RBAC**: Only required permissions granted
- **Pod Security Standards**: Compatible with restricted pod security standards

## Next Steps

- Read the [Configuration Reference](https://easyscale.readthedocs.io/en/latest/configuration.html)
- Check out [Examples](https://easyscale.readthedocs.io/en/latest/examples.html)
- See [Architecture](https://easyscale.readthedocs.io/en/latest/architecture.html) for internals
