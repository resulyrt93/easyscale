"""Kubernetes resource manager for scaling operations."""

import logging
from typing import Literal, Optional

from kubernetes.client.rest import ApiException

from easyscale.k8s.client import K8sClient, K8sClientError

logger = logging.getLogger(__name__)


class ResourceManagerError(Exception):
    """Raised when resource management operations fail."""

    pass


class ResourceManager:
    """Manage Kubernetes resource scaling operations."""

    def __init__(self, k8s_client: K8sClient):
        """
        Initialize ResourceManager.

        Args:
            k8s_client: Kubernetes client instance
        """
        self.client = k8s_client

    def get_current_replicas(
        self,
        kind: Literal["Deployment", "StatefulSet"],
        name: str,
        namespace: str
    ) -> int:
        """
        Get current replica count for a resource.

        Args:
            kind: Type of resource (Deployment or StatefulSet)
            name: Name of the resource
            namespace: Namespace of the resource

        Returns:
            Current replica count

        Raises:
            ResourceManagerError: If operation fails
        """
        try:
            if kind == "Deployment":
                deployment = self.client.apps_v1.read_namespaced_deployment(
                    name=name,
                    namespace=namespace
                )
                replicas = deployment.spec.replicas
                logger.debug(f"Deployment {namespace}/{name} has {replicas} replicas")
                return replicas or 0

            elif kind == "StatefulSet":
                statefulset = self.client.apps_v1.read_namespaced_stateful_set(
                    name=name,
                    namespace=namespace
                )
                replicas = statefulset.spec.replicas
                logger.debug(f"StatefulSet {namespace}/{name} has {replicas} replicas")
                return replicas or 0

            else:
                raise ResourceManagerError(f"Unsupported resource kind: {kind}")

        except ApiException as e:
            if e.status == 404:
                raise ResourceManagerError(
                    f"{kind} {namespace}/{name} not found"
                ) from e
            raise ResourceManagerError(
                f"Failed to get replicas for {kind} {namespace}/{name}: {e}"
            ) from e
        except Exception as e:
            raise ResourceManagerError(
                f"Unexpected error getting replicas for {kind} {namespace}/{name}: {e}"
            ) from e

    def scale_resource(
        self,
        kind: Literal["Deployment", "StatefulSet"],
        name: str,
        namespace: str,
        replicas: int,
        dry_run: bool = False
    ) -> bool:
        """
        Scale a Kubernetes resource to desired replica count.

        Args:
            kind: Type of resource (Deployment or StatefulSet)
            name: Name of the resource
            namespace: Namespace of the resource
            replicas: Desired replica count
            dry_run: If True, don't actually scale (for testing)

        Returns:
            True if scaling was successful

        Raises:
            ResourceManagerError: If operation fails
        """
        if replicas < 0:
            raise ResourceManagerError(f"Replica count cannot be negative: {replicas}")

        try:
            current_replicas = self.get_current_replicas(kind, name, namespace)

            if current_replicas == replicas:
                logger.info(
                    f"{kind} {namespace}/{name} already at {replicas} replicas, no scaling needed"
                )
                return True

            if dry_run:
                logger.info(
                    f"[DRY-RUN] Would scale {kind} {namespace}/{name} "
                    f"from {current_replicas} to {replicas} replicas"
                )
                return True

            # Patch the resource with new replica count
            body = {"spec": {"replicas": replicas}}

            if kind == "Deployment":
                self.client.apps_v1.patch_namespaced_deployment_scale(
                    name=name,
                    namespace=namespace,
                    body=body
                )
                logger.info(
                    f"Scaled Deployment {namespace}/{name} from {current_replicas} to {replicas} replicas"
                )

            elif kind == "StatefulSet":
                self.client.apps_v1.patch_namespaced_stateful_set_scale(
                    name=name,
                    namespace=namespace,
                    body=body
                )
                logger.info(
                    f"Scaled StatefulSet {namespace}/{name} from {current_replicas} to {replicas} replicas"
                )

            return True

        except ApiException as e:
            if e.status == 404:
                raise ResourceManagerError(
                    f"{kind} {namespace}/{name} not found"
                ) from e
            raise ResourceManagerError(
                f"Failed to scale {kind} {namespace}/{name}: {e}"
            ) from e
        except ResourceManagerError:
            raise
        except Exception as e:
            raise ResourceManagerError(
                f"Unexpected error scaling {kind} {namespace}/{name}: {e}"
            ) from e

    def resource_exists(
        self,
        kind: Literal["Deployment", "StatefulSet"],
        name: str,
        namespace: str
    ) -> bool:
        """
        Check if a resource exists.

        Args:
            kind: Type of resource (Deployment or StatefulSet)
            name: Name of the resource
            namespace: Namespace of the resource

        Returns:
            True if resource exists, False otherwise
        """
        try:
            if kind == "Deployment":
                self.client.apps_v1.read_namespaced_deployment(
                    name=name,
                    namespace=namespace
                )
            elif kind == "StatefulSet":
                self.client.apps_v1.read_namespaced_stateful_set(
                    name=name,
                    namespace=namespace
                )
            else:
                raise ResourceManagerError(f"Unsupported resource kind: {kind}")

            logger.debug(f"{kind} {namespace}/{name} exists")
            return True

        except ApiException as e:
            if e.status == 404:
                logger.debug(f"{kind} {namespace}/{name} does not exist")
                return False
            logger.warning(
                f"Error checking if {kind} {namespace}/{name} exists: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error checking if {kind} {namespace}/{name} exists: {e}"
            )
            return False

    def get_resource_status(
        self,
        kind: Literal["Deployment", "StatefulSet"],
        name: str,
        namespace: str
    ) -> Optional[dict]:
        """
        Get resource status information.

        Args:
            kind: Type of resource (Deployment or StatefulSet)
            name: Name of the resource
            namespace: Namespace of the resource

        Returns:
            Dict with status info (replicas, ready_replicas, etc.) or None if not found
        """
        try:
            if kind == "Deployment":
                deployment = self.client.apps_v1.read_namespaced_deployment_status(
                    name=name,
                    namespace=namespace
                )
                status = deployment.status
                return {
                    "replicas": status.replicas or 0,
                    "ready_replicas": status.ready_replicas or 0,
                    "available_replicas": status.available_replicas or 0,
                    "updated_replicas": status.updated_replicas or 0,
                }

            elif kind == "StatefulSet":
                statefulset = self.client.apps_v1.read_namespaced_stateful_set_status(
                    name=name,
                    namespace=namespace
                )
                status = statefulset.status
                return {
                    "replicas": status.replicas or 0,
                    "ready_replicas": status.ready_replicas or 0,
                    "current_replicas": status.current_replicas or 0,
                    "updated_replicas": status.updated_replicas or 0,
                }

            else:
                raise ResourceManagerError(f"Unsupported resource kind: {kind}")

        except ApiException as e:
            if e.status == 404:
                logger.debug(f"{kind} {namespace}/{name} not found")
                return None
            logger.error(f"Failed to get status for {kind} {namespace}/{name}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error getting status for {kind} {namespace}/{name}: {e}"
            )
            return None
