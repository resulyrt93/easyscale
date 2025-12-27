<div align="center">
  <a href="https://easyscale.readthedocs.io">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://co-datazone-public.s3.amazonaws.com/media/easyscale-logo.png">
      <img alt="easyscalelogo" src="https://co-datazone-public.s3.amazonaws.com/media/easyscale-logo.png" height="256">
    </picture>
  </a>
  <h1>EasyScale</h1>
  <p>
    <a href="https://easyscale.readthedocs.io"><img src="https://readthedocs.org/projects/easyscale/badge/?version=latest" alt="Documentation Status"></a>
    <a href="https://github.com/resulyrt93/easyscale/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
    <a href="https://github.com/resulyrt93/easyscale"><img src="https://img.shields.io/badge/python-3.12-blue.svg" alt="Python 3.12"></a>
  </p>
</div>

> Simple Kubernetes time-based pod scaling daemon

EasyScale is a lightweight, easy-to-configure tool for managing Kubernetes workload scaling based on time schedules. Perfect for predictable workloads that need different capacity at different times.

## ✨ Features

- **Simple Configuration**: YAML-based rules that anyone can understand
- **Time-Based Scaling**: Scale based on days of week, specific dates, and time ranges
- **Priority Resolution**: Handle overlapping rules with priority-based conflict resolution
- **Timezone Support**: Full timezone support with IANA timezone database
- **Safety Limits**: Optional min/max replica constraints
- **Multiple Targets**: Support for Deployments and StatefulSets
- **Dry-Run Mode**: Test rules without actually scaling resources

## 🚀 Quick Start

### Installation

```bash
# Install EasyScale daemon to your cluster
kubectl apply -f https://raw.githubusercontent.com/resulyrt93/easyscale/main/deploy/kubernetes/install.yaml
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

Apply the configuration:

```bash
kubectl apply -f weekend-scale.yaml
```

## 📖 Documentation

**Complete documentation is available at [easyscale.readthedocs.io](https://easyscale.readthedocs.io)**

- [Getting Started](https://easyscale.readthedocs.io/en/latest/getting-started.html) - 5-minute setup guide
- [Installation](https://easyscale.readthedocs.io/en/latest/installation.html) - Detailed installation instructions
- [Configuration Reference](https://easyscale.readthedocs.io/en/latest/configuration.html) - Complete configuration options
- [Examples](https://easyscale.readthedocs.io/en/latest/examples.html) - Real-world use cases
- [Architecture](https://easyscale.readthedocs.io/en/latest/architecture.html) - How EasyScale works
- [API Reference](https://easyscale.readthedocs.io/en/latest/api-reference.html) - Python API documentation
- [FAQ](https://easyscale.readthedocs.io/en/latest/faq.html) - Common questions and troubleshooting

## 🎯 Use Cases

- **Cost Optimization**: Scale down non-production environments outside business hours
- **Peak Traffic Handling**: Scale up during known peak periods (lunch rush, end-of-month)
- **Holiday/Special Events**: Handle Black Friday, product launches with high-priority rules
- **Multi-Region Operations**: Follow-the-sun scaling across timezones
- **Development Workflows**: Auto-shutdown test environments after hours

## 🏗️ Architecture

EasyScale runs as a Kubernetes daemon that:
1. Loads ScalingRule custom resources from your cluster via CRD
2. Evaluates rules every 60 seconds (configurable)
3. Scales Deployments/StatefulSets when needed
4. Enforces cooldown periods to prevent thrashing
5. Logs all scaling decisions and operations

Complete Kubernetes manifests (CRD, RBAC, Deployment) are available in the `/deploy/kubernetes/` directory.

See the [Architecture Documentation](https://easyscale.readthedocs.io/en/latest/architecture.html) for details.

## 🧪 Development

```bash
# Clone repository
git clone https://github.com/resulyrt93/easyscale.git
cd easyscale

# Setup environment
conda create -n easyscale python=3.12
conda activate easyscale
poetry install

# Run tests (194 tests, 86% coverage)
pytest --cov=easyscale

# Test locally with dry-run
python -m easyscale --rules-dir ./examples --kubeconfig --dry-run
```

## 📊 Status

- ✅ Core functionality complete
- ✅ 194 tests passing
- ✅ 86% code coverage
- ✅ Comprehensive documentation
- ✅ Kubernetes manifests available
- 🚧 Helm chart planned

## 📋 Roadmap

- [x] Time-based, day-based, and date-based scheduling
- [x] Priority resolution
- [x] Configuration validation
- [x] Comprehensive documentation
- [x] CRD-based rule management
- [ ] Prometheus metrics
- [ ] Datadog integration
- [ ] Webhook notifications
- [ ] Web UI

## 🤝 Contributing

Contributions are welcome! Please see our [Contributing Guide](https://easyscale.readthedocs.io/en/latest/) and feel free to submit Pull Requests.

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 📞 Support

- 📖 [Documentation](https://easyscale.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/resulyrt93/easyscale/issues)
- 💬 [Discussions](https://github.com/resulyrt93/easyscale/discussions)

---

Made with ❤️ for simplicity
