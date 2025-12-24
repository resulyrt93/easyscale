# Installation

This guide covers different ways to install EasyScale in your Kubernetes cluster.

## Prerequisites

- Kubernetes cluster version 1.19 or higher
- `kubectl` command-line tool configured
- Appropriate cluster permissions to create:
  - Namespaces
  - ServiceAccounts
  - ClusterRoles and ClusterRoleBindings
  - Deployments

## Installation Methods

### Method 1: Using kubectl (Recommended)

The simplest way to install EasyScale:

```bash
kubectl apply -f https://raw.githubusercontent.com/resulyrt93/easyscale/main/deploy/kubernetes/install.yaml
```

This creates:
- `easyscale-system` namespace
- ServiceAccount for the controller
- ClusterRole with necessary permissions
- ClusterRoleBinding
- Deployment for the EasyScale controller
- ScalingRule CustomResourceDefinition (CRD)

### Method 2: Using Helm

Install using Helm chart:

```bash
# Add EasyScale Helm repository
helm repo add easyscale https://resulyrt93.github.io/easyscale
helm repo update

# Install EasyScale
helm install easyscale easyscale/easyscale \
  --namespace easyscale-system \
  --create-namespace
```

#### Helm Configuration Options

Customize the installation with values:

```bash
helm install easyscale easyscale/easyscale \
  --namespace easyscale-system \
  --create-namespace \
  --set checkInterval=30 \
  --set cooldownSeconds=120 \
  --set image.tag=v0.2.0
```

Available values:

```yaml
# values.yaml
image:
  repository: easyscale/easyscale
  tag: latest
  pullPolicy: IfNotPresent

replicaCount: 1

checkInterval: 60      # Seconds between evaluation cycles
cooldownSeconds: 60    # Minimum seconds between scaling operations

resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi

logLevel: INFO         # DEBUG, INFO, WARNING, ERROR, CRITICAL
logFormat: text        # text or json
```

### Method 3: Manual Installation

For more control, install components manually:

```bash
# Create namespace
kubectl create namespace easyscale-system

# Apply CRD
kubectl apply -f deploy/kubernetes/crd.yaml

# Create ServiceAccount and RBAC
kubectl apply -f deploy/kubernetes/rbac.yaml

# Deploy controller
kubectl apply -f deploy/kubernetes/deployment.yaml
```

## Verification

After installation, verify EasyScale is running:

```bash
# Check pods
kubectl get pods -n easyscale-system

# Expected output:
# NAME                                    READY   STATUS    RESTARTS   AGE
# easyscale-controller-xxxxxxxxxx-xxxxx   1/1     Running   0          1m
```

Check logs:

```bash
kubectl logs -n easyscale-system deployment/easyscale-controller
```

You should see logs indicating successful startup:

```
============================================================
EasyScale - Kubernetes Time-Based Pod Scaling Daemon
============================================================
Configuration:
  Check interval: 60s
  Cooldown period: 60s
  Dry-run mode: False
  Kubernetes config: in-cluster
  Log level: INFO
  Log format: text
Successfully connected to Kubernetes API
EasyScale daemon starting (check_interval=60s, dry_run=False)
```

## Upgrading

### Using kubectl

```bash
kubectl apply -f https://raw.githubusercontent.com/resulyrt93/easyscale/main/deploy/kubernetes/install.yaml
```

### Using Helm

```bash
helm upgrade easyscale easyscale/easyscale \
  --namespace easyscale-system \
  --reuse-values
```

To upgrade with new values:

```bash
helm upgrade easyscale easyscale/easyscale \
  --namespace easyscale-system \
  --set checkInterval=30
```

## Uninstallation

### Using kubectl

```bash
kubectl delete -f https://raw.githubusercontent.com/resulyrt93/easyscale/main/deploy/kubernetes/install.yaml
```

This removes all EasyScale components. Your scaling rules will be deleted as well.

### Using Helm

```bash
helm uninstall easyscale --namespace easyscale-system
kubectl delete namespace easyscale-system
```

## RBAC Permissions

EasyScale requires the following permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: easyscale-controller
rules:
  # Read Deployments and StatefulSets
  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets"]
    verbs: ["get", "list", "watch"]

  # Scale Deployments and StatefulSets
  - apiGroups: ["apps"]
    resources: ["deployments/scale", "statefulsets/scale"]
    verbs: ["get", "update", "patch"]

  # Manage ScalingRule CRDs
  - apiGroups: ["easyscale.io"]
    resources: ["scalingrules"]
    verbs: ["get", "list", "watch"]

  # Create events for audit trail
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["create", "patch"]
```

## Configuration

### Environment Variables

The controller supports the following environment variables:

- `CHECK_INTERVAL`: Seconds between evaluation cycles (default: 60)
- `COOLDOWN_SECONDS`: Cooldown period in seconds (default: 60)
- `LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
- `LOG_FORMAT`: Log format - text or json (default: text)
- `DRY_RUN`: Enable dry-run mode - true or false (default: false)

Example deployment with custom configuration:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: easyscale-controller
  namespace: easyscale-system
spec:
  template:
    spec:
      containers:
      - name: controller
        image: easyscale/easyscale:latest
        env:
        - name: CHECK_INTERVAL
          value: "30"
        - name: COOLDOWN_SECONDS
          value: "120"
        - name: LOG_LEVEL
          value: "DEBUG"
```

## Next Steps

- [Getting Started Guide](getting-started.md) - Create your first scaling rule
- [Configuration Reference](configuration.md) - Learn about all configuration options
- [Examples](examples.md) - See common use cases
