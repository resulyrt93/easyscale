"""CRD loader for loading ScalingRule custom resources from Kubernetes."""

import logging
from typing import Optional

from pydantic import ValidationError

from easyscale.config.models import ScalingRule
from easyscale.k8s.client import K8sClient

logger = logging.getLogger(__name__)


class CRDLoadError(Exception):
    """Raised when CRD loading fails."""

    pass


class CRDLoader:
    """Load ScalingRule CRDs from Kubernetes cluster."""

    def __init__(self, k8s_client: K8sClient):
        """
        Initialize CRD loader.

        Args:
            k8s_client: Kubernetes client instance
        """
        self.k8s_client = k8s_client

    def load_all_scaling_rules(self, namespace: Optional[str] = None) -> list[ScalingRule]:
        """
        Load all ScalingRule CRDs from the cluster.

        Args:
            namespace: Optional namespace to filter rules. If None, loads from all namespaces.

        Returns:
            List of validated ScalingRule instances

        Raises:
            CRDLoadError: If CRDs cannot be loaded
        """
        try:
            # Get custom objects API
            custom_api = self.k8s_client.custom_objects_api

            # List ScalingRule CRDs
            if namespace:
                response = custom_api.list_namespaced_custom_object(
                    group="easyscale.io",
                    version="v1",
                    namespace=namespace,
                    plural="scalingrules",
                )
            else:
                response = custom_api.list_cluster_custom_object(
                    group="easyscale.io",
                    version="v1",
                    plural="scalingrules",
                )

            rules = []
            items = response.get("items", [])

            logger.info(f"Found {len(items)} ScalingRule CRD(s) in {'namespace ' + namespace if namespace else 'cluster'}")

            for item in items:
                try:
                    # Convert CRD to ScalingRule model
                    rule = self._crd_to_scaling_rule(item)
                    rules.append(rule)
                    rule_name = rule.metadata.name
                    rule_namespace = rule.metadata.namespace
                    logger.info(f"Loaded ScalingRule CRD '{rule_name}' from namespace '{rule_namespace}'")
                except (ValidationError, KeyError) as e:
                    # Log error but continue loading other rules
                    crd_name = item.get("metadata", {}).get("name", "unknown")
                    crd_namespace = item.get("metadata", {}).get("namespace", "unknown")
                    logger.error(f"Failed to load ScalingRule CRD '{crd_name}' from namespace '{crd_namespace}': {e}")
                    continue

            return rules

        except Exception as e:
            raise CRDLoadError(f"Failed to list ScalingRule CRDs: {e}") from e

    def load_scaling_rule(self, name: str, namespace: str) -> ScalingRule:
        """
        Load a specific ScalingRule CRD by name and namespace.

        Args:
            name: Name of the ScalingRule
            namespace: Namespace of the ScalingRule

        Returns:
            Validated ScalingRule instance

        Raises:
            CRDLoadError: If CRD cannot be loaded
            ValidationError: If CRD data is invalid
        """
        try:
            custom_api = self.k8s_client.custom_objects_api

            crd = custom_api.get_namespaced_custom_object(
                group="easyscale.io",
                version="v1",
                namespace=namespace,
                plural="scalingrules",
                name=name,
            )

            return self._crd_to_scaling_rule(crd)

        except Exception as e:
            raise CRDLoadError(f"Failed to load ScalingRule CRD '{name}' from namespace '{namespace}': {e}") from e

    def _crd_to_scaling_rule(self, crd_data: dict) -> ScalingRule:
        """
        Convert CRD data to ScalingRule model.

        Args:
            crd_data: Raw CRD data from Kubernetes API

        Returns:
            Validated ScalingRule instance

        Raises:
            ValidationError: If CRD data is invalid
            KeyError: If required fields are missing
        """
        # Extract relevant fields from CRD
        metadata = crd_data["metadata"]
        spec = crd_data["spec"]

        # Build ScalingRule data structure
        rule_data = {
            "apiVersion": crd_data.get("apiVersion", "easyscale.io/v1"),
            "kind": crd_data.get("kind", "ScalingRule"),
            "metadata": {
                "name": metadata["name"],
                "namespace": metadata["namespace"],
            },
            "spec": spec,
        }

        # Validate and return
        return ScalingRule.model_validate(rule_data)

    def update_scaling_rule_status(
        self,
        name: str,
        namespace: str,
        status: dict,
    ) -> None:
        """
        Update the status of a ScalingRule CRD.

        Args:
            name: Name of the ScalingRule
            namespace: Namespace of the ScalingRule
            status: Status data to update

        Raises:
            CRDLoadError: If status update fails
        """
        try:
            custom_api = self.k8s_client.custom_objects_api

            # Patch the status subresource
            custom_api.patch_namespaced_custom_object_status(
                group="easyscale.io",
                version="v1",
                namespace=namespace,
                plural="scalingrules",
                name=name,
                body={"status": status},
            )

            logger.debug(f"Updated status for ScalingRule '{name}' in namespace '{namespace}'")

        except Exception as e:
            raise CRDLoadError(
                f"Failed to update status for ScalingRule '{name}' in namespace '{namespace}': {e}"
            ) from e
