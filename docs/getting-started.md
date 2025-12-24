# Getting Started

This guide will help you get started with EasyScale in just a few minutes.

## Prerequisites

Before you begin, ensure you have:

- A Kubernetes cluster (v1.19+)
- `kubectl` configured to access your cluster
- Basic understanding of Kubernetes concepts (Deployments, StatefulSets)

## Quick Start

### Step 1: Install EasyScale

Deploy EasyScale to your cluster:

```bash
kubectl apply -f https://raw.githubusercontent.com/yourusername/easyscale/main/deploy/kubernetes/install.yaml
```

This will create:
- `easyscale-system` namespace
- ServiceAccount with appropriate RBAC permissions
- EasyScale controller deployment

### Step 2: Verify Installation

Check that EasyScale is running:

```bash
kubectl get pods -n easyscale-system
```

You should see the EasyScale controller pod in a `Running` state.

Check the logs:

```bash
kubectl logs -n easyscale-system deployment/easyscale-controller
```

### Step 3: Create Your First Scaling Rule

Create a file called `weekend-scale.yaml`:

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: weekend-scale-down
  namespace: default
spec:
  target:
    kind: Deployment
    name: my-api-service
    namespace: default

  schedule:
    - name: "Weekend scale down"
      days: [Saturday, Sunday]
      replicas: 2

  default:
    replicas: 5
```

This rule will:
- Scale `my-api-service` to 2 replicas on weekends
- Scale it back to 5 replicas on weekdays

### Step 4: Apply the Scaling Rule

```bash
kubectl apply -f weekend-scale.yaml
```

### Step 5: Verify the Rule

List all scaling rules:

```bash
kubectl get scalingrules
```

View rule details:

```bash
kubectl describe scalingrule weekend-scale-down
```

Check EasyScale logs to see the rule being processed:

```bash
kubectl logs -n easyscale-system deployment/easyscale-controller -f
```

## What's Next?

Now that you have EasyScale running, explore more features:

- [Configuration Reference](configuration.md) - Learn about all configuration options
- [Examples](examples.md) - See more scaling rule examples
- [Architecture](architecture.md) - Understand how EasyScale works

## Troubleshooting

### EasyScale pod not starting

Check the pod status and events:

```bash
kubectl describe pod -n easyscale-system -l app=easyscale-controller
```

### Rules not being applied

1. Verify the rule is valid:
   ```bash
   kubectl get scalingrule <rule-name> -o yaml
   ```

2. Check EasyScale logs for errors:
   ```bash
   kubectl logs -n easyscale-system deployment/easyscale-controller
   ```

3. Ensure the target Deployment/StatefulSet exists:
   ```bash
   kubectl get deployment <deployment-name> -n <namespace>
   ```

### Scaling not happening

- Check that the current time matches your schedule rule
- Verify timezone settings in your rule
- Check if cooldown period is blocking scaling
- Review logs for decision-making details with `--log-level DEBUG`

## Development Setup

For local development and testing:

```bash
# Clone the repository
git clone https://github.com/yourusername/easyscale.git
cd easyscale

# Create conda environment
conda create -n easyscale python=3.12
conda activate easyscale

# Install dependencies
poetry install

# Run tests
pytest

# Run locally with kubeconfig
python -m easyscale --rules-dir ./examples --kubeconfig --dry-run
```

The `--dry-run` flag ensures no actual scaling happens during testing.
