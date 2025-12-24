"""Tests for configuration loader."""

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from easyscale.config.loader import ConfigLoadError, ConfigLoader
from easyscale.config.models import ScalingRule


class TestConfigLoader:
    """Tests for ConfigLoader."""

    def test_load_from_dict(self):
        """Test loading from dictionary."""
        data = {
            "apiVersion": "easyscale.io/v1",
            "kind": "ScalingRule",
            "metadata": {"name": "test-rule"},
            "spec": {
                "target": {
                    "kind": "Deployment",
                    "name": "my-app"
                },
                "schedule": [
                    {
                        "name": "Weekend",
                        "days": ["Saturday", "Sunday"],
                        "replicas": 2
                    }
                ],
                "default": {"replicas": 5}
            }
        }
        rule = ConfigLoader.load_from_dict(data)
        assert isinstance(rule, ScalingRule)
        assert rule.metadata.name == "test-rule"

    def test_load_from_yaml_string(self):
        """Test loading from YAML string."""
        yaml_content = """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: test-rule
spec:
  target:
    kind: Deployment
    name: my-app
  schedule:
    - name: Weekend
      days: [Saturday, Sunday]
      replicas: 2
  default:
    replicas: 5
"""
        rule = ConfigLoader.load_from_yaml_string(yaml_content)
        assert isinstance(rule, ScalingRule)
        assert rule.metadata.name == "test-rule"
        assert len(rule.spec.schedule) == 1

    def test_load_from_file(self):
        """Test loading from file."""
        yaml_content = """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: file-test-rule
spec:
  target:
    kind: Deployment
    name: my-app
  schedule:
    - name: Weekend
      days: [Saturday, Sunday]
      replicas: 2
  default:
    replicas: 5
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            rule = ConfigLoader.load_from_file(temp_path)
            assert isinstance(rule, ScalingRule)
            assert rule.metadata.name == "file-test-rule"
        finally:
            Path(temp_path).unlink()

    def test_load_from_nonexistent_file(self):
        """Test loading from non-existent file."""
        with pytest.raises(ConfigLoadError) as exc_info:
            ConfigLoader.load_from_file("/nonexistent/path/config.yaml")
        assert "not found" in str(exc_info.value)

    def test_load_from_invalid_yaml(self):
        """Test loading from invalid YAML."""
        invalid_yaml = """
apiVersion: easyscale.io/v1
kind: ScalingRule
  - invalid: structure
metadata:
  name: test
"""
        with pytest.raises(ConfigLoadError) as exc_info:
            ConfigLoader.load_from_yaml_string(invalid_yaml)
        assert "Failed to parse YAML" in str(exc_info.value)

    def test_load_from_invalid_config(self):
        """Test loading from invalid configuration."""
        invalid_config = """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: test
spec:
  target:
    kind: InvalidKind
    name: my-app
  schedule: []
  default:
    replicas: 5
"""
        with pytest.raises(ValidationError):
            ConfigLoader.load_from_yaml_string(invalid_config)

    def test_load_multiple_from_directory(self):
        """Test loading multiple files from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple YAML files
            config1 = """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: rule-1
spec:
  target:
    kind: Deployment
    name: app-1
  schedule:
    - name: Weekend
      days: [Saturday]
      replicas: 2
  default:
    replicas: 5
"""
            config2 = """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: rule-2
spec:
  target:
    kind: Deployment
    name: app-2
  schedule:
    - name: Weekend
      days: [Sunday]
      replicas: 3
  default:
    replicas: 6
"""
            Path(tmpdir, "config1.yaml").write_text(config1)
            Path(tmpdir, "config2.yml").write_text(config2)
            # Create a non-YAML file that should be ignored
            Path(tmpdir, "readme.txt").write_text("This should be ignored")

            rules = ConfigLoader.load_multiple_from_directory(tmpdir)
            assert len(rules) == 2
            names = {rule.metadata.name for rule in rules}
            assert names == {"rule-1", "rule-2"}

    def test_load_from_empty_directory(self):
        """Test loading from empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules = ConfigLoader.load_multiple_from_directory(tmpdir)
            assert len(rules) == 0

    def test_load_from_directory_with_invalid_file(self):
        """Test loading from directory with some invalid files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Valid config
            valid_config = """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: valid-rule
spec:
  target:
    kind: Deployment
    name: app
  schedule:
    - name: Weekend
      days: [Saturday]
      replicas: 2
  default:
    replicas: 5
"""
            # Invalid config
            invalid_config = """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: invalid-rule
spec:
  invalid: structure
"""
            Path(tmpdir, "valid.yaml").write_text(valid_config)
            Path(tmpdir, "invalid.yaml").write_text(invalid_config)

            # Should load only the valid one
            rules = ConfigLoader.load_multiple_from_directory(tmpdir)
            assert len(rules) == 1
            assert rules[0].metadata.name == "valid-rule"

    def test_load_from_configmap_data(self):
        """Test loading from Kubernetes ConfigMap data."""
        configmap_data = {
            "rule1.yaml": """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: configmap-rule-1
spec:
  target:
    kind: Deployment
    name: app-1
  schedule:
    - name: Weekend
      days: [Saturday]
      replicas: 2
  default:
    replicas: 5
""",
            "rule2.yaml": """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: configmap-rule-2
spec:
  target:
    kind: Deployment
    name: app-2
  schedule:
    - name: Sunday
      days: [Sunday]
      replicas: 3
  default:
    replicas: 6
""",
            "non-yaml-key": "This should be ignored"
        }

        rules = ConfigLoader.load_from_kubernetes_configmap(configmap_data)
        assert len(rules) == 2
        names = {rule.metadata.name for rule in rules}
        assert names == {"configmap-rule-1", "configmap-rule-2"}

    def test_load_from_empty_configmap(self):
        """Test loading from empty ConfigMap."""
        rules = ConfigLoader.load_from_kubernetes_configmap({})
        assert len(rules) == 0

    def test_load_from_configmap_with_invalid_yaml(self):
        """Test loading from ConfigMap with invalid YAML."""
        configmap_data = {
            "valid.yaml": """
apiVersion: easyscale.io/v1
kind: ScalingRule
metadata:
  name: valid
spec:
  target:
    kind: Deployment
    name: app
  schedule:
    - name: Test
      days: [Monday]
      replicas: 2
  default:
    replicas: 5
""",
            "invalid.yaml": "invalid: yaml: content:"
        }

        # Should load only the valid one
        rules = ConfigLoader.load_from_kubernetes_configmap(configmap_data)
        assert len(rules) == 1
        assert rules[0].metadata.name == "valid"

    def test_yaml_not_dict(self):
        """Test YAML that doesn't parse to a dict."""
        with pytest.raises(ConfigLoadError) as exc_info:
            ConfigLoader.load_from_yaml_string("- item1\n- item2")
        assert "must contain a YAML object" in str(exc_info.value) or "must be a YAML object" in str(exc_info.value)
