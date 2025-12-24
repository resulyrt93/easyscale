"""Configuration loader for EasyScale."""

import logging
from pathlib import Path
from typing import Union

import yaml
from pydantic import ValidationError

from easyscale.config.models import ScalingRule

logger = logging.getLogger(__name__)


class ConfigLoadError(Exception):
    """Raised when configuration loading fails."""

    pass


class ConfigLoader:
    """Load and parse EasyScale configuration files."""

    @staticmethod
    def load_from_file(file_path: Union[str, Path]) -> ScalingRule:
        """
        Load a ScalingRule from a YAML file.

        Args:
            file_path: Path to the YAML configuration file

        Returns:
            Validated ScalingRule instance

        Raises:
            ConfigLoadError: If file cannot be read or parsed
            ValidationError: If configuration is invalid
        """
        path = Path(file_path)

        if not path.exists():
            raise ConfigLoadError(f"Configuration file not found: {path}")

        if not path.is_file():
            raise ConfigLoadError(f"Path is not a file: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Failed to parse YAML file {path}: {e}") from e
        except Exception as e:
            raise ConfigLoadError(f"Failed to read file {path}: {e}") from e

        if not isinstance(data, dict):
            raise ConfigLoadError(f"Configuration file must contain a YAML object, got {type(data).__name__}")

        try:
            return ScalingRule.model_validate(data)
        except ValidationError as e:
            logger.error(f"Validation error in {path}: {e}")
            raise

    @staticmethod
    def load_from_dict(data: dict) -> ScalingRule:
        """
        Load a ScalingRule from a dictionary.

        Args:
            data: Dictionary containing configuration

        Returns:
            Validated ScalingRule instance

        Raises:
            ValidationError: If configuration is invalid
        """
        return ScalingRule.model_validate(data)

    @staticmethod
    def load_from_yaml_string(yaml_str: str) -> ScalingRule:
        """
        Load a ScalingRule from a YAML string.

        Args:
            yaml_str: YAML configuration as string

        Returns:
            Validated ScalingRule instance

        Raises:
            ConfigLoadError: If YAML cannot be parsed
            ValidationError: If configuration is invalid
        """
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Failed to parse YAML string: {e}") from e

        if not isinstance(data, dict):
            raise ConfigLoadError(f"Configuration must be a YAML object, got {type(data).__name__}")

        return ScalingRule.model_validate(data)

    @staticmethod
    def load_multiple_from_directory(directory: Union[str, Path]) -> list[ScalingRule]:
        """
        Load all YAML configuration files from a directory.

        Args:
            directory: Path to directory containing YAML files

        Returns:
            List of validated ScalingRule instances

        Raises:
            ConfigLoadError: If directory cannot be read
        """
        path = Path(directory)

        if not path.exists():
            raise ConfigLoadError(f"Directory not found: {path}")

        if not path.is_dir():
            raise ConfigLoadError(f"Path is not a directory: {path}")

        rules = []
        yaml_files = list(path.glob("*.yaml")) + list(path.glob("*.yml"))

        if not yaml_files:
            logger.warning(f"No YAML files found in directory: {path}")
            return rules

        for yaml_file in sorted(yaml_files):
            try:
                rule = ConfigLoader.load_from_file(yaml_file)
                rules.append(rule)
                logger.info(f"Loaded rule '{rule.metadata.name}' from {yaml_file}")
            except (ConfigLoadError, ValidationError) as e:
                logger.error(f"Failed to load {yaml_file}: {e}")
                # Continue loading other files instead of failing completely
                continue

        return rules

    @staticmethod
    def load_from_kubernetes_configmap(configmap_data: dict[str, str]) -> list[ScalingRule]:
        """
        Load ScalingRules from Kubernetes ConfigMap data.

        Args:
            configmap_data: ConfigMap data field containing YAML configurations

        Returns:
            List of validated ScalingRule instances

        Raises:
            ConfigLoadError: If any configuration cannot be parsed
        """
        rules = []

        for key, value in configmap_data.items():
            if not (key.endswith(".yaml") or key.endswith(".yml")):
                logger.debug(f"Skipping non-YAML key in ConfigMap: {key}")
                continue

            try:
                rule = ConfigLoader.load_from_yaml_string(value)
                rules.append(rule)
                logger.info(f"Loaded rule '{rule.metadata.name}' from ConfigMap key '{key}'")
            except (ConfigLoadError, ValidationError) as e:
                logger.error(f"Failed to load ConfigMap key '{key}': {e}")
                # Continue loading other keys instead of failing completely
                continue

        if not rules:
            logger.warning("No valid scaling rules found in ConfigMap")

        return rules
