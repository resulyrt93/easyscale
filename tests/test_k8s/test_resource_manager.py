"""Tests for Kubernetes resource manager."""

from unittest.mock import MagicMock, patch

import pytest
from kubernetes.client.rest import ApiException

from easyscale.k8s.client import K8sClient
from easyscale.k8s.resource_manager import ResourceManager, ResourceManagerError


@pytest.fixture
def mock_k8s_client():
    """Create a mock K8s client."""
    client = MagicMock(spec=K8sClient)
    client.apps_v1 = MagicMock()
    client.core_v1 = MagicMock()
    return client


@pytest.fixture
def resource_manager(mock_k8s_client):
    """Create a ResourceManager with mock client."""
    return ResourceManager(mock_k8s_client)


class TestResourceManager:
    """Tests for ResourceManager."""

    def test_init(self, mock_k8s_client):
        """Test ResourceManager initialization."""
        manager = ResourceManager(mock_k8s_client)
        assert manager.client == mock_k8s_client

    def test_get_current_replicas_deployment(self, resource_manager, mock_k8s_client):
        """Test getting current replicas for Deployment."""
        mock_deployment = MagicMock()
        mock_deployment.spec.replicas = 5
        mock_k8s_client.apps_v1.read_namespaced_deployment.return_value = mock_deployment

        replicas = resource_manager.get_current_replicas("Deployment", "test-app", "default")

        assert replicas == 5
        mock_k8s_client.apps_v1.read_namespaced_deployment.assert_called_once_with(
            name="test-app",
            namespace="default"
        )

    def test_get_current_replicas_statefulset(self, resource_manager, mock_k8s_client):
        """Test getting current replicas for StatefulSet."""
        mock_statefulset = MagicMock()
        mock_statefulset.spec.replicas = 3
        mock_k8s_client.apps_v1.read_namespaced_stateful_set.return_value = mock_statefulset

        replicas = resource_manager.get_current_replicas("StatefulSet", "test-stateful", "default")

        assert replicas == 3
        mock_k8s_client.apps_v1.read_namespaced_stateful_set.assert_called_once_with(
            name="test-stateful",
            namespace="default"
        )

    def test_get_current_replicas_none(self, resource_manager, mock_k8s_client):
        """Test getting replicas when spec.replicas is None."""
        mock_deployment = MagicMock()
        mock_deployment.spec.replicas = None
        mock_k8s_client.apps_v1.read_namespaced_deployment.return_value = mock_deployment

        replicas = resource_manager.get_current_replicas("Deployment", "test-app", "default")

        assert replicas == 0

    def test_get_current_replicas_not_found(self, resource_manager, mock_k8s_client):
        """Test getting replicas for non-existent resource."""
        mock_k8s_client.apps_v1.read_namespaced_deployment.side_effect = ApiException(status=404)

        with pytest.raises(ResourceManagerError) as exc_info:
            resource_manager.get_current_replicas("Deployment", "test-app", "default")

        assert "not found" in str(exc_info.value)

    def test_get_current_replicas_invalid_kind(self, resource_manager):
        """Test getting replicas with invalid kind."""
        with pytest.raises(ResourceManagerError) as exc_info:
            resource_manager.get_current_replicas("DaemonSet", "test-app", "default")

        assert "Unsupported resource kind" in str(exc_info.value)

    def test_scale_resource_deployment(self, resource_manager, mock_k8s_client):
        """Test scaling a Deployment."""
        mock_deployment = MagicMock()
        mock_deployment.spec.replicas = 3
        mock_k8s_client.apps_v1.read_namespaced_deployment.return_value = mock_deployment

        result = resource_manager.scale_resource("Deployment", "test-app", "default", 5)

        assert result is True
        mock_k8s_client.apps_v1.patch_namespaced_deployment_scale.assert_called_once_with(
            name="test-app",
            namespace="default",
            body={"spec": {"replicas": 5}}
        )

    def test_scale_resource_statefulset(self, resource_manager, mock_k8s_client):
        """Test scaling a StatefulSet."""
        mock_statefulset = MagicMock()
        mock_statefulset.spec.replicas = 2
        mock_k8s_client.apps_v1.read_namespaced_stateful_set.return_value = mock_statefulset

        result = resource_manager.scale_resource("StatefulSet", "test-stateful", "default", 4)

        assert result is True
        mock_k8s_client.apps_v1.patch_namespaced_stateful_set_scale.assert_called_once_with(
            name="test-stateful",
            namespace="default",
            body={"spec": {"replicas": 4}}
        )

    def test_scale_resource_no_change(self, resource_manager, mock_k8s_client):
        """Test scaling when replicas already at desired count."""
        mock_deployment = MagicMock()
        mock_deployment.spec.replicas = 5
        mock_k8s_client.apps_v1.read_namespaced_deployment.return_value = mock_deployment

        result = resource_manager.scale_resource("Deployment", "test-app", "default", 5)

        assert result is True
        # Should not call patch when already at desired replicas
        mock_k8s_client.apps_v1.patch_namespaced_deployment_scale.assert_not_called()

    def test_scale_resource_dry_run(self, resource_manager, mock_k8s_client):
        """Test scaling in dry-run mode."""
        mock_deployment = MagicMock()
        mock_deployment.spec.replicas = 3
        mock_k8s_client.apps_v1.read_namespaced_deployment.return_value = mock_deployment

        result = resource_manager.scale_resource("Deployment", "test-app", "default", 5, dry_run=True)

        assert result is True
        # Should not call patch in dry-run mode
        mock_k8s_client.apps_v1.patch_namespaced_deployment_scale.assert_not_called()

    def test_scale_resource_negative_replicas(self, resource_manager):
        """Test scaling with negative replica count."""
        with pytest.raises(ResourceManagerError) as exc_info:
            resource_manager.scale_resource("Deployment", "test-app", "default", -1)

        assert "cannot be negative" in str(exc_info.value)

    def test_scale_resource_not_found(self, resource_manager, mock_k8s_client):
        """Test scaling non-existent resource."""
        mock_k8s_client.apps_v1.read_namespaced_deployment.side_effect = ApiException(status=404)

        with pytest.raises(ResourceManagerError) as exc_info:
            resource_manager.scale_resource("Deployment", "test-app", "default", 5)

        assert "not found" in str(exc_info.value)

    def test_resource_exists_deployment_true(self, resource_manager, mock_k8s_client):
        """Test checking if Deployment exists - positive case."""
        mock_k8s_client.apps_v1.read_namespaced_deployment.return_value = MagicMock()

        exists = resource_manager.resource_exists("Deployment", "test-app", "default")

        assert exists is True

    def test_resource_exists_deployment_false(self, resource_manager, mock_k8s_client):
        """Test checking if Deployment exists - negative case."""
        mock_k8s_client.apps_v1.read_namespaced_deployment.side_effect = ApiException(status=404)

        exists = resource_manager.resource_exists("Deployment", "test-app", "default")

        assert exists is False

    def test_resource_exists_statefulset(self, resource_manager, mock_k8s_client):
        """Test checking if StatefulSet exists."""
        mock_k8s_client.apps_v1.read_namespaced_stateful_set.return_value = MagicMock()

        exists = resource_manager.resource_exists("StatefulSet", "test-stateful", "default")

        assert exists is True

    def test_resource_exists_invalid_kind(self, resource_manager):
        """Test checking existence with invalid kind."""
        # Invalid kind returns False and logs error, doesn't raise
        exists = resource_manager.resource_exists("DaemonSet", "test-app", "default")
        assert exists is False

    def test_get_resource_status_deployment(self, resource_manager, mock_k8s_client):
        """Test getting Deployment status."""
        mock_deployment = MagicMock()
        mock_deployment.status.replicas = 5
        mock_deployment.status.ready_replicas = 4
        mock_deployment.status.available_replicas = 4
        mock_deployment.status.updated_replicas = 5
        mock_k8s_client.apps_v1.read_namespaced_deployment_status.return_value = mock_deployment

        status = resource_manager.get_resource_status("Deployment", "test-app", "default")

        assert status is not None
        assert status["replicas"] == 5
        assert status["ready_replicas"] == 4
        assert status["available_replicas"] == 4
        assert status["updated_replicas"] == 5

    def test_get_resource_status_statefulset(self, resource_manager, mock_k8s_client):
        """Test getting StatefulSet status."""
        mock_statefulset = MagicMock()
        mock_statefulset.status.replicas = 3
        mock_statefulset.status.ready_replicas = 3
        mock_statefulset.status.current_replicas = 3
        mock_statefulset.status.updated_replicas = 3
        mock_k8s_client.apps_v1.read_namespaced_stateful_set_status.return_value = mock_statefulset

        status = resource_manager.get_resource_status("StatefulSet", "test-stateful", "default")

        assert status is not None
        assert status["replicas"] == 3
        assert status["ready_replicas"] == 3
        assert status["current_replicas"] == 3
        assert status["updated_replicas"] == 3

    def test_get_resource_status_not_found(self, resource_manager, mock_k8s_client):
        """Test getting status for non-existent resource."""
        mock_k8s_client.apps_v1.read_namespaced_deployment_status.side_effect = ApiException(status=404)

        status = resource_manager.get_resource_status("Deployment", "test-app", "default")

        assert status is None

    def test_get_resource_status_none_values(self, resource_manager, mock_k8s_client):
        """Test getting status with None values."""
        mock_deployment = MagicMock()
        mock_deployment.status.replicas = None
        mock_deployment.status.ready_replicas = None
        mock_deployment.status.available_replicas = None
        mock_deployment.status.updated_replicas = None
        mock_k8s_client.apps_v1.read_namespaced_deployment_status.return_value = mock_deployment

        status = resource_manager.get_resource_status("Deployment", "test-app", "default")

        assert status is not None
        assert status["replicas"] == 0
        assert status["ready_replicas"] == 0
        assert status["available_replicas"] == 0
        assert status["updated_replicas"] == 0

    def test_get_resource_status_invalid_kind(self, resource_manager):
        """Test getting status with invalid kind."""
        # Invalid kind returns None and logs error, doesn't raise
        status = resource_manager.get_resource_status("DaemonSet", "test-app", "default")
        assert status is None
