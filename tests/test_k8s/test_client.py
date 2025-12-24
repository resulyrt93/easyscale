"""Tests for Kubernetes client wrapper."""

from unittest.mock import MagicMock, patch

import pytest
from kubernetes.client.rest import ApiException

from easyscale.k8s.client import K8sClient, K8sClientError


class TestK8sClient:
    """Tests for K8sClient."""

    @patch("easyscale.k8s.client.config.load_incluster_config")
    @patch("easyscale.k8s.client.client.AppsV1Api")
    @patch("easyscale.k8s.client.client.CoreV1Api")
    def test_init_in_cluster(self, mock_core_api, mock_apps_api, mock_load_incluster):
        """Test initialization with in-cluster config."""
        k8s_client = K8sClient(in_cluster=True)

        mock_load_incluster.assert_called_once()
        mock_apps_api.assert_called_once()
        mock_core_api.assert_called_once()
        assert k8s_client.in_cluster is True

    @patch("easyscale.k8s.client.config.load_kube_config")
    @patch("easyscale.k8s.client.client.AppsV1Api")
    @patch("easyscale.k8s.client.client.CoreV1Api")
    def test_init_kubeconfig(self, mock_core_api, mock_apps_api, mock_load_kubeconfig):
        """Test initialization with kubeconfig."""
        k8s_client = K8sClient(in_cluster=False)

        mock_load_kubeconfig.assert_called_once()
        mock_apps_api.assert_called_once()
        mock_core_api.assert_called_once()
        assert k8s_client.in_cluster is False

    @patch("easyscale.k8s.client.config.load_incluster_config")
    @patch("easyscale.k8s.client.client.AppsV1Api")
    @patch("easyscale.k8s.client.client.CoreV1Api")
    def test_init_failure(self, mock_core_api, mock_apps_api, mock_load_incluster):
        """Test initialization failure."""
        mock_load_incluster.side_effect = Exception("Config load failed")

        with pytest.raises(K8sClientError) as exc_info:
            K8sClient(in_cluster=True)

        assert "Failed to initialize" in str(exc_info.value)

    @patch("easyscale.k8s.client.config.load_incluster_config")
    @patch("easyscale.k8s.client.client.AppsV1Api")
    @patch("easyscale.k8s.client.client.CoreV1Api")
    def test_apps_v1_property(self, mock_core_api, mock_apps_api, mock_load_incluster):
        """Test apps_v1 property access."""
        k8s_client = K8sClient(in_cluster=True)

        apps_api = k8s_client.apps_v1
        assert apps_api is not None

    @patch("easyscale.k8s.client.config.load_incluster_config")
    @patch("easyscale.k8s.client.client.AppsV1Api")
    @patch("easyscale.k8s.client.client.CoreV1Api")
    def test_core_v1_property(self, mock_core_api, mock_apps_api, mock_load_incluster):
        """Test core_v1 property access."""
        k8s_client = K8sClient(in_cluster=True)

        core_api = k8s_client.core_v1
        assert core_api is not None

    @patch("easyscale.k8s.client.config.load_incluster_config")
    @patch("easyscale.k8s.client.client.AppsV1Api")
    @patch("easyscale.k8s.client.client.CoreV1Api")
    def test_test_connection_success(self, mock_core_api_cls, mock_apps_api, mock_load_incluster):
        """Test successful connection test."""
        mock_core_instance = MagicMock()
        mock_core_api_cls.return_value = mock_core_instance

        k8s_client = K8sClient(in_cluster=True)
        result = k8s_client.test_connection()

        assert result is True
        mock_core_instance.list_namespace.assert_called_once_with(limit=1)

    @patch("easyscale.k8s.client.config.load_incluster_config")
    @patch("easyscale.k8s.client.client.AppsV1Api")
    @patch("easyscale.k8s.client.client.CoreV1Api")
    def test_test_connection_api_exception(self, mock_core_api_cls, mock_apps_api, mock_load_incluster):
        """Test connection test with API exception."""
        mock_core_instance = MagicMock()
        mock_core_instance.list_namespace.side_effect = ApiException("Connection failed")
        mock_core_api_cls.return_value = mock_core_instance

        k8s_client = K8sClient(in_cluster=True)
        result = k8s_client.test_connection()

        assert result is False

    @patch("easyscale.k8s.client.config.load_incluster_config")
    @patch("easyscale.k8s.client.client.AppsV1Api")
    @patch("easyscale.k8s.client.client.CoreV1Api")
    def test_test_connection_unexpected_error(self, mock_core_api_cls, mock_apps_api, mock_load_incluster):
        """Test connection test with unexpected error."""
        mock_core_instance = MagicMock()
        mock_core_instance.list_namespace.side_effect = Exception("Unexpected error")
        mock_core_api_cls.return_value = mock_core_instance

        k8s_client = K8sClient(in_cluster=True)
        result = k8s_client.test_connection()

        assert result is False
