"""Kubernetes client wrapper for EasyScale."""

import logging
from typing import Optional

from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class K8sClientError(Exception):
    """Raised when Kubernetes client operations fail."""

    pass


class K8sClient:
    """Simple Kubernetes client wrapper."""

    def __init__(self, in_cluster: bool = True):
        """
        Initialize Kubernetes client.

        Args:
            in_cluster: If True, load in-cluster config. If False, load from kubeconfig.
        """
        self.in_cluster = in_cluster
        self._apps_v1_api: Optional[client.AppsV1Api] = None
        self._core_v1_api: Optional[client.CoreV1Api] = None
        self._custom_objects_api: Optional[client.CustomObjectsApi] = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize Kubernetes configuration and API clients."""
        try:
            if self.in_cluster:
                logger.info("Loading in-cluster Kubernetes configuration")
                config.load_incluster_config()
            else:
                logger.info("Loading Kubernetes configuration from kubeconfig")
                config.load_kube_config()

            self._apps_v1_api = client.AppsV1Api()
            self._core_v1_api = client.CoreV1Api()
            self._custom_objects_api = client.CustomObjectsApi()
            logger.info("Kubernetes client initialized successfully")

        except Exception as e:
            raise K8sClientError(f"Failed to initialize Kubernetes client: {e}") from e

    @property
    def apps_v1(self) -> client.AppsV1Api:
        """Get AppsV1Api client."""
        if self._apps_v1_api is None:
            raise K8sClientError("AppsV1Api not initialized")
        return self._apps_v1_api

    @property
    def core_v1(self) -> client.CoreV1Api:
        """Get CoreV1Api client."""
        if self._core_v1_api is None:
            raise K8sClientError("CoreV1Api not initialized")
        return self._core_v1_api

    @property
    def custom_objects_api(self) -> client.CustomObjectsApi:
        """Get CustomObjectsApi client."""
        if self._custom_objects_api is None:
            raise K8sClientError("CustomObjectsApi not initialized")
        return self._custom_objects_api

    def test_connection(self) -> bool:
        """
        Test connection to Kubernetes API server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to list namespaces as a connectivity test
            self.core_v1.list_namespace(limit=1)
            logger.info("Kubernetes API connection test successful")
            return True
        except ApiException as e:
            logger.error(f"Kubernetes API connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection test: {e}")
            return False
