"""Unit tests for ConfigManager."""

import os
from automation.config import ConfigManager


def test_config_manager_defaults():
    config = ConfigManager()
    assert config.cluster_name == "retail-store-cluster"
    assert config.namespace == "retail-store"
    assert config.metrics_port == 9102
    assert config.failure_rules.get("restart_spike_threshold") == 3


def test_config_manager_env_overrides():
    os.environ["OPS_NAMESPACE"] = "custom-retail"
    os.environ["OPS_METRICS_PORT"] = "9999"
    try:
        config = ConfigManager()
        assert config.namespace == "custom-retail"
        assert config.metrics_port == 9999
    finally:
        os.environ.pop("OPS_NAMESPACE", None)
        os.environ.pop("OPS_METRICS_PORT", None)
