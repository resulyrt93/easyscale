"""Kubernetes client integration for EasyScale."""

from easyscale.k8s.client import K8sClient
from easyscale.k8s.resource_manager import ResourceManager

__all__ = ["K8sClient", "ResourceManager"]
