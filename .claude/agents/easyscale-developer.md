---
name: easyscale-developer
description: when I mention it
model: sonnet
color: yellow
---

I want to create a open source tool with python. it's name easyscale. basically it manages k8s hpa scalings in cluster. user will configure some metrics and by this configurations this tool will manage the scaling of specified pods. I want to create simply and shortly what we can do with this tool? my personal goal is set some configurations for my some inference services like "scale down x pod to 2 replicaset in weekends", "scale up y pod to 5 replicaset between 16:00 - 18:00". as you see my first goal is time based conditions. but in future we can add resource usages, or custom metrics, even calling third party tools like prometheus or datadog. 

motto of tool is simplicity. even someone who don't know any infreastructure or k8s knowledge, will be able to configure this tool. let's start. (don't write me code. only outlines)

# EasyScale - Development Steps

## Phase 1: Foundation & Core Setup

### 1. Project File Architecture
```
easyscale/
├── README.md
├── LICENSE
├── setup.py / pyproject.toml
├── requirements.txt
├── Dockerfile
├── .gitignore
├── easyscale/
│   ├── __init__.py
│   ├── __main__.py              # Entry point
│   ├── config/
│   │   ├── __init__.py
│   │   ├── models.py            # Pydantic models
│   │   ├── validator.py         # Config validation logic
│   │   └── loader.py            # Config loading from files/ConfigMaps
│   ├── controller/
│   │   ├── __init__.py
│   │   ├── daemon.py            # Main controller loop
│   │   ├── scheduler.py         # Rule evaluation engine
│   │   └── scaler.py            # Scaling execution logic
│   ├── k8s/
│   │   ├── __init__.py
│   │   ├── client.py            # Kubernetes client wrapper
│   │   └── resource_manager.py  # HPA/Deployment operations
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py            # Logging setup
│   │   ├── time_utils.py        # Time/timezone helpers
│   │   └── state.py             # State management
│   └── cli/
│       ├── __init__.py
│       └── commands.py          # CLI commands (validate, dry-run, etc.)
├── tests/
│   ├── __init__.py
│   ├── test_config/
│   ├── test_controller/
│   └── test_k8s/
├── examples/
│   ├── basic-schedule.yaml
│   ├── weekend-scale.yaml
│   └── business-hours.yaml
├── deploy/
│   ├── kubernetes/
│   │   ├── deployment.yaml
│   │   ├── serviceaccount.yaml
│   │   ├── rbac.yaml
│   │   └── configmap.yaml
│   └── helm/
│       └── easyscale/
│           ├── Chart.yaml
│           ├── values.yaml
│           └── templates/
└── docs/
    ├── configuration.md
    ├── architecture.md
    └── getting-started.md
```

### 2. Example Configuration Files

**examples/basic-schedule.yaml**
```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: inference-weekend-scale
spec:
  target:
    kind: Deployment  # or StatefulSet
    name: inference-service-x
    namespace: default
  schedule:
    - name: "Weekend scale down"
      days: [Saturday, Sunday]
      replicas: 2
      timezone: "UTC"
  
  # Optional: what to do when no rules match
  default:
    replicas: 5
```

**examples/business-hours.yaml**
```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: peak-hours-scaling
spec:
  target:
    kind: Deployment
    name: inference-service-y
    namespace: production
  schedule:
    - name: "Peak hours"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "16:00"
      timeEnd: "18:00"
      replicas: 5
      timezone: "America/New_York"
    
    - name: "Business hours baseline"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "09:00"
      timeEnd: "18:00"
      replicas: 3
      timezone: "America/New_York"
  
  default:
    replicas: 1
```

**examples/advanced-schedule.yaml**
```yaml
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: ml-model-complex-schedule
spec:
  target:
    kind: Deployment
    name: ml-model-api
    namespace: ml-services
  
  schedule:
    - name: "Late night scale down"
      days: [Monday, Tuesday, Wednesday, Thursday, Friday]
      timeStart: "22:00"
      timeEnd: "06:00"
      replicas: 1
      priority: 100
      timezone: "Europe/London"
    
    - name: "Weekend minimal"
      days: [Saturday, Sunday]
      replicas: 1
      priority: 50
      timezone: "Europe/London"
    
    - name: "Holiday mode"
      dates: ["2025-12-25", "2025-01-01"]
      replicas: 1
      priority: 200
      timezone: "Europe/London"
  
  default:
    replicas: 3
  
  # Optional safety limits
  limits:
    minReplicas: 1
    maxReplicas: 10
```

### 3. Defining Model Classes with Pydantic

**easyscale/config/models.py**
```python
Key models to define:

- ScalingRule (root model)
  - metadata: Metadata
  - spec: ScalingSpec

- Metadata
  - name: str
  - namespace: Optional[str]
  - labels: Optional[Dict]

- ScalingSpec
  - target: TargetResource
  - schedule: List[ScheduleRule]
  - default: DefaultConfig
  - limits: Optional[ScalingLimits]

- TargetResource
  - kind: Literal["Deployment", "StatefulSet"]
  - name: str
  - namespace: str

- ScheduleRule
  - name: str
  - days: Optional[List[DayOfWeek]]  # Enum
  - dates: Optional[List[date]]
  - timeStart: Optional[time]
  - timeEnd: Optional[time]
  - replicas: int
  - priority: int = 0
  - timezone: str = "UTC"

- DefaultConfig
  - replicas: int

- ScalingLimits
  - minReplicas: int
  - maxReplicas: int

- DayOfWeek (Enum)
  - Monday, Tuesday, ..., Sunday
```

### 4. Configuration Loader

**easyscale/config/loader.py**
- Load from YAML file
- Load from Kubernetes ConfigMap
- Load from multiple ConfigMaps (multi-file support)
- Validate against Pydantic schema
- Handle file watching for hot-reload
- Error handling with clear messages

### 5. Kubernetes Client Wrapper

**easyscale/k8s/client.py**
- Initialize kubernetes client (in-cluster vs local kubeconfig)
- Handle authentication
- Connection pooling
- Retry logic
- Error handling

**easyscale/k8s/resource_manager.py**
- Get current replica count of Deployment/StatefulSet
- Scale Deployment/StatefulSet
- Check if resource exists
- Get HPA status (if exists)
- Create/Update/Delete operations
- Event recording (for audit trail)

### 6. Rule Evaluation Engine

**easyscale/controller/scheduler.py**
- Evaluate time-based conditions
- Evaluate day-based conditions
- Evaluate date-based conditions
- Handle timezone conversions
- Priority-based conflict resolution
- Determine which rule applies right now
- Return desired replica count

### 7. Main Daemon/Controller Loop

**easyscale/controller/daemon.py**
- Initialize on startup
- Load configurations
- Main event loop (every N seconds, configurable)
- For each ScalingRule:
  - Evaluate current conditions
  - Determine desired replicas
  - Compare with current state
  - Execute scaling if needed
  - Log actions
- Handle graceful shutdown
- Health check endpoint

### 8. Scaling Executor

**easyscale/controller/scaler.py**
- Execute scaling operation
- Dry-run mode support
- State tracking (last scaled time, last replica count)
- Prevent thrashing (cooldown period)
- Audit logging
- Emit Kubernetes events
- Error handling and rollback

### 9. State Management

**easyscale/utils/state.py**
- In-memory state store
- Track last scaling action per resource
- Track current active rule per resource
- Cooldown tracking
- Optional: persist to ConfigMap for multi-instance support

### 10. CLI Tool

**easyscale/cli/commands.py**
- `easyscale validate <config-file>` - Validate configuration
- `easyscale dry-run <config-file>` - Show what would happen
- `easyscale run` - Start the daemon
- `easyscale version` - Show version info
- Future: `easyscale generate` - Config wizard

### 11. Logging & Observability

**easyscale/utils/logger.py**
- Structured logging (JSON format)
- Log levels configuration
- Log scaling decisions
- Log errors and warnings
- Future: Prometheus metrics

### 12. Docker Container

**Dockerfile**
- Python base image (slim/alpine)
- Install dependencies
- Copy application code
- Non-root user
- Health check
- Minimal image size

### 13. Kubernetes Deployment Manifests

**deploy/kubernetes/serviceaccount.yaml**
- ServiceAccount for EasyScale

**deploy/kubernetes/rbac.yaml**
- ClusterRole with permissions:
  - Get/List/Watch Deployments, StatefulSets
  - Get/List/Watch ConfigMaps
  - Update/Patch Deployments, StatefulSets (scale subresource)
  - Create Events
- ClusterRoleBinding

**deploy/kubernetes/deployment.yaml**
- EasyScale controller deployment
- Mount ConfigMap for configurations
- Resource requests/limits
- Health probes

**deploy/kubernetes/configmap.yaml**
- Example configurations

### 14. Testing

**tests/**
- Unit tests for Pydantic models
- Unit tests for scheduler logic (time evaluation)
- Mock tests for Kubernetes client
- Integration tests (with kind/minikube)
- Timezone tests
- Priority/conflict resolution tests

### 15. Documentation

**README.md**
- Project description
- Quick start (5-minute guide)
- Installation instructions
- Basic examples
- Contributing

**docs/configuration.md**
- Complete configuration reference
- All options explained
- Multiple examples

**docs/getting-started.md**
- Step-by-step tutorial
- Common use cases

**docs/architecture.md**
- How it works
- Design decisions
- Component diagram

---

## Development Order Recommendation

1. ✅ Project structure setup
2. ✅ Define Pydantic models
3. ✅ Implement config loader (file-based first)
4. ✅ Write unit tests for models
5. ✅ Implement scheduler/rule evaluation engine
6. ✅ Write tests for scheduler
7. ✅ Implement K8s client wrapper (can mock initially)
8. ✅ Implement scaler executor
9. ✅ Implement daemon loop
10. ✅ Add CLI commands
11. ✅ Create Dockerfile
12. ✅ Create K8s manifests
13. ✅ Add ConfigMap reader support
14. ✅ Integration testing
15. ✅ Documentation
16. ✅ Helm chart (optional but recommended)

This gives you a clear roadmap from concept to production-ready tool!


