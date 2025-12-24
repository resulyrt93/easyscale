<div align="center">
  <a href="https://nextjs.org">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://co-datazone-public.s3.amazonaws.com/media/easyscale-logo.png">
      <img alt="easyscalelogo" src="https://co-datazone-public.s3.amazonaws.com/media/easyscale-logo.png" height="256">
    </picture>
  </a>
  <h1>EasyScale</h1>
</div>

> Simple Kubernetes HPA scaling manager with time-based rules

EasyScale is a lightweight, easy-to-configure tool for managing Kubernetes workload scaling based on time schedules. Perfect for predictable workloads that need different capacity at different times.

## ✨ Features

- **Simple Configuration**: YAML-based rules that anyone can understand
- **Time-Based Scaling**: Scale based on days of week, specific dates, and time ranges
- **Priority Resolution**: Handle overlapping rules with priority-based conflict resolution
- **Timezone Support**: Full timezone support with IANA timezone database
- **Safety Limits**: Optional min/max replica constraints
- **Multiple Targets**: Support for Deployments and StatefulSets
- **Validation**: Built-in configuration validation and dry-run mode

## 🚀 Quick Start

### Installation

```bash
# Install EasyScale daemon to your cluster
kubectl apply -f https://raw.githubusercontent.com/yourusername/easyscale/main/deploy/kubernetes/install.yaml
```

### Basic Example

Create a file `weekend-scale.yaml`:

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

Apply the configuration:

```bash
# Apply scaling rule to your cluster
kubectl apply -f weekend-scale.yaml

# View scaling rules
kubectl get scalingrules

# Check EasyScale daemon logs
kubectl logs -n easyscale-system deployment/easyscale-controller
```

## 📖 Documentation

### Configuration Reference

#### Target Resource

```yaml
target:
  kind: Deployment          # or StatefulSet
  name: my-service          # Name of the resource
  namespace: default        # Kubernetes namespace
```

#### Schedule Rules

```yaml
schedule:
  - name: "Rule name"
    days: [Monday, Tuesday]           # Days of week
    dates: ["2025-12-25", "2026-01-01"]  # Specific dates
    timeStart: "09:00"                # Start time (HH:MM)
    timeEnd: "17:00"                  # End time (HH:MM)
    replicas: 5                       # Desired replicas
    priority: 100                     # Priority (higher wins)
    timezone: "America/New_York"      # IANA timezone
```

#### Limits (Optional)

```yaml
limits:
  minReplicas: 1   # Minimum allowed replicas
  maxReplicas: 10  # Maximum allowed replicas
```

### Examples

See the [examples/](examples/) directory for more configurations:

- [basic-schedule.yaml](examples/basic-schedule.yaml) - Simple weekend scaling
- [simple-time-based.yaml](examples/simple-time-based.yaml) - Business hours scaling
- [business-hours.yaml](examples/business-hours.yaml) - Peak hours with priorities
- [advanced-schedule.yaml](examples/advanced-schedule.yaml) - Complex multi-rule setup

## 🎯 Use Cases

### Cost Optimization

Scale down non-production environments outside business hours:

```yaml
schedule:
  - name: "Business hours"
    days: [Monday, Tuesday, Wednesday, Thursday, Friday]
    timeStart: "08:00"
    timeEnd: "18:00"
    replicas: 3
default:
  replicas: 0  # Shut down outside business hours
```

### Peak Traffic Handling

Scale up during known peak periods:

```yaml
schedule:
  - name: "Lunch rush"
    days: [Monday, Tuesday, Wednesday, Thursday, Friday]
    timeStart: "11:30"
    timeEnd: "13:30"
    replicas: 10
    priority: 100
```

### Holiday/Special Events

Handle special dates with high priority:

```yaml
schedule:
  - name: "Black Friday"
    dates: ["2025-11-28", "2025-11-29"]
    replicas: 20
    priority: 200
```

## 🏗️ Architecture

EasyScale is a Kubernetes-native daemon that consists of:

1. **Configuration Models** - Pydantic-based ScalingRule validation
2. **Rule Evaluation Engine** - Time-based scheduling logic
3. **Controller Daemon** - Watches ScalingRules and executes scaling
4. **K8s Integration** - Scales Deployments and StatefulSets
5. **RBAC** - Minimal permissions (read pods, scale resources)

**How it works:**
1. User creates a ScalingRule YAML and applies it: `kubectl apply -f rule.yaml`
2. EasyScale daemon watches for ScalingRule resources
3. Every minute, daemon evaluates all rules against current time
4. If desired replicas differ from current, daemon scales the resource
5. All operations are logged and visible in daemon logs

## 🧪 Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/easyscale.git
cd easyscale

# Create conda environment
conda create -n easyscale python=3.12
conda activate easyscale

# Install dependencies
poetry install

# Run tests
pytest

# Run linter
ruff check .

# Format code
ruff format .
```

### Running Tests

```bash
# All tests (129 tests, 92% coverage)
pytest

# With coverage report
pytest --cov=easyscale --cov-report=html

# Specific test file
pytest tests/test_config/test_models.py

# Verbose output
pytest -v
```

### Testing Locally

```bash
# Build Docker image
docker build -t easyscale:dev .

# Deploy to local cluster (minikube/kind)
kubectl apply -f deploy/kubernetes/

# Watch logs
kubectl logs -f -n easyscale-system deployment/easyscale-controller
```

## 🚢 Deployment

### Install to Kubernetes

```bash
# Install EasyScale daemon
kubectl apply -f deploy/kubernetes/install.yaml

# Or using Helm
helm repo add easyscale https://yourusername.github.io/easyscale
helm install easyscale easyscale/easyscale
```

### Uninstall

```bash
# Remove EasyScale
kubectl delete -f deploy/kubernetes/install.yaml

# Or with Helm
helm uninstall easyscale
```

### Multiple Scaling Rules

```bash
# Apply multiple rules
kubectl apply -f scaling-rules/

# Each file is a separate ScalingRule
# The daemon automatically detects and applies all rules
```

## 📋 Roadmap

- [x] Time-based scheduling
- [x] Day-based scheduling
- [x] Date-based scheduling
- [x] Priority resolution
- [x] Configuration validation
- [ ] Prometheus metrics integration
- [ ] Resource usage-based scaling
- [ ] Datadog integration
- [ ] Slack/webhook notifications
- [ ] Web UI for configuration

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Pydantic](https://docs.pydantic.dev/) for data validation
- Uses [kubernetes-client](https://github.com/kubernetes-client/python) for K8s API
- Inspired by the need for simple, predictable scaling

## 📞 Support

- 📖 [Documentation](https://github.com/yourusername/easyscale/wiki)
- 🐛 [Issue Tracker](https://github.com/yourusername/easyscale/issues)
- 💬 [Discussions](https://github.com/yourusername/easyscale/discussions)

---

Made with ❤️ for simplicity
