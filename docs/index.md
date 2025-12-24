# EasyScale Documentation

Welcome to **EasyScale** - a Kubernetes-native daemon that manages pod scaling based on time-based schedules!

```{toctree}
:maxdepth: 2
:caption: Getting Started

getting-started
installation
```

```{toctree}
:maxdepth: 2
:caption: User Guide

configuration
examples
```

```{toctree}
:maxdepth: 2
:caption: Reference

architecture
api-reference
faq
```

## What is EasyScale?

EasyScale is a lightweight, easy-to-configure tool for managing Kubernetes workload scaling based on time schedules. Perfect for predictable workloads that need different capacity at different times.

### Key Features

- **Simple Configuration**: YAML-based rules that anyone can understand
- **Time-Based Scaling**: Scale based on days of week, specific dates, and time ranges
- **Priority Resolution**: Handle overlapping rules with priority-based conflict resolution
- **Timezone Support**: Full timezone support with IANA timezone database
- **Safety Limits**: Optional min/max replica constraints
- **Multiple Targets**: Support for Deployments and StatefulSets
- **Dry-Run Mode**: Test your rules without actually scaling resources

### Quick Example

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

This rule automatically scales your service to 2 replicas on weekends and back to 5 replicas on weekdays!

## Use Cases

### Cost Optimization

Scale down non-production environments outside business hours to save costs.

### Peak Traffic Handling

Scale up during known peak periods like lunch hours or end-of-month processing.

### Holiday/Special Events

Handle special dates like Black Friday with high priority rules.

### Weekend Scaling

Reduce capacity during weekends when traffic is lower.

## Getting Help

- 📖 **Documentation**: You're reading it!
- 🐛 **Report Issues**: [GitHub Issues](https://github.com/resulyrt93/easyscale/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/resulyrt93/easyscale/discussions)
- 📦 **Source Code**: [GitHub Repository](https://github.com/resulyrt93/easyscale)

## Quick Links

::::{grid} 2
:gutter: 3

:::{grid-item-card} 🚀 Getting Started
:link: getting-started
:link-type: doc

Get EasyScale running in 5 minutes
:::

:::{grid-item-card} 📦 Installation
:link: installation
:link-type: doc

Install EasyScale in your cluster
:::

:::{grid-item-card} ⚙️ Configuration
:link: configuration
:link-type: doc

Complete configuration reference
:::

:::{grid-item-card} 📚 Examples
:link: examples
:link-type: doc

Real-world use cases and examples
:::

::::

## Next Steps

1. [**Getting Started**](getting-started.md) - Set up EasyScale in minutes
2. [**Configuration**](configuration.md) - Learn about all configuration options
3. [**Examples**](examples.md) - Explore real-world use cases
4. [**Architecture**](architecture.md) - Understand how EasyScale works

## License

EasyScale is licensed under the MIT License. See the [LICENSE](https://github.com/resulyrt93/easyscale/blob/main/LICENSE) file for details.

---

Made with ❤️ for simplicity
