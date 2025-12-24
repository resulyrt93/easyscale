# EasyScale Documentation

Welcome to EasyScale documentation! EasyScale is a Kubernetes-native daemon that manages pod scaling based on time-based schedules.

## Quick Links

- [Getting Started](getting-started.md)
- [Installation](installation.md)
- [Configuration Reference](configuration.md)
- [Examples](examples.md)
- [Architecture](architecture.md)
- [API Reference](api-reference.md)
- [FAQ](faq.md)

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

### Use Cases

- **Cost Optimization**: Scale down non-production environments outside business hours
- **Peak Traffic Handling**: Scale up during known peak periods
- **Holiday/Special Events**: Handle special dates with high priority rules
- **Weekend Scaling**: Reduce capacity during weekends when traffic is lower

## Getting Help

- Report issues: [GitHub Issues](https://github.com/yourusername/easyscale/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/easyscale/discussions)
- Documentation: This site

## License

EasyScale is licensed under the MIT License. See [LICENSE](../LICENSE) for details.
