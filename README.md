# EasyScale

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
# Using pip
pip install easyscale

# Using poetry
poetry add easyscale
```

### Basic Example

Create a file `weekend-scale.yaml`:

```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: weekend-scale-down
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

Validate and test:

```bash
# Validate configuration
easyscale validate weekend-scale.yaml

# Dry-run to see what would happen
easyscale dry-run weekend-scale.yaml

# Run the controller
easyscale run --config weekend-scale.yaml
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

EasyScale consists of:

1. **Configuration Models** - Pydantic-based validation
2. **Config Loader** - YAML/ConfigMap loading
3. **Scheduler** - Rule evaluation engine
4. **Controller** - Main control loop
5. **K8s Client** - Kubernetes API integration

## 🧪 Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/easyscale.git
cd easyscale

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run linter
poetry run ruff check .

# Format code
poetry run ruff format .
```

### Running Tests

```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov=easyscale

# Specific test file
poetry run pytest tests/test_config/test_models.py

# Verbose output
poetry run pytest -v
```

## 🚢 Deployment

### Kubernetes Deployment

```bash
# Apply RBAC and deployment
kubectl apply -f deploy/kubernetes/

# Using Helm
helm install easyscale deploy/helm/easyscale
```

### Configuration via ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: easyscale-config
data:
  rule1.yaml: |
    apiVersion: easyscale.io/v1
    kind: ScalingRule
    # ... your config here
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
