"""Configuration loader module for the Platform Operations Automation Engine."""

import os
from pathlib import Path
from typing import Any, Dict
import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "settings.yaml"


class ConfigManager:
    """Loads, validates, and manages platform operations settings."""

    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Loads YAML settings file and merges with environment variable overrides."""
        if not self.config_path.exists():
            return self._default_fallback()

        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        # Apply environment variable overrides
        if os.getenv("OPS_NAMESPACE"):
            cfg.setdefault("cluster", {})["default_namespace"] = os.getenv("OPS_NAMESPACE")

        if os.getenv("OPS_DRY_RUN"):
            val = os.getenv("OPS_DRY_RUN").strip().lower() in ("1", "true", "yes")
            cfg.setdefault("remediation", {})["dry_run_default"] = val

        if os.getenv("OPS_METRICS_PORT"):
            try:
                cfg.setdefault("metrics", {})["port"] = int(os.getenv("OPS_METRICS_PORT"))
            except ValueError:
                pass

        return cfg

    def _default_fallback(self) -> Dict[str, Any]:
        return {
            "cluster": {
                "default_namespace": "retail-store",
                "monitored_services": ["ui", "catalog", "cart", "checkout", "orders"],
                "connect_timeout_seconds": 10,
                "request_timeout_seconds": 30,
            },
            "thresholds": {
                "restart_spike_threshold": 3,
                "cpu_warning_percentage": 80.0,
                "cpu_critical_percentage": 95.0,
                "memory_warning_percentage": 85.0,
                "memory_critical_percentage": 95.0,
            },
            "detection": {
                "critical_reasons": ["CrashLoopBackOff", "ImagePullBackOff", "OOMKilled"],
                "max_event_age_minutes": 30,
                "recent_log_lines": 50,
            },
            "remediation": {
                "dry_run_default": True,
                "require_confirmation": True,
                "max_consecutive_rollbacks": 1,
            },
            "reporting": {
                "output_dir": "reports",
                "default_report_file": "cluster-diagnostics.json",
                "pretty_print": True,
            },
            "metrics": {
                "enabled": True,
                "port": 9102,
                "metrics_path": "/metrics",
            },
        }

    def get(self, section: str, key: str = None, default: Any = None) -> Any:
        """Retrieves a configuration value or section."""
        sec = self._config.get(section, {})
        if key is None:
            return sec
        if isinstance(sec, dict):
            return sec.get(key, default)
        return default

    @property
    def namespace(self) -> str:
        return self.get("cluster", "default_namespace", "retail-store")

    @property
    def cluster_name(self) -> str:
        return self.get("cluster", "name", "retail-store-cluster")

    @property
    def metrics_port(self) -> int:
        return self.get("metrics", "port", 9102)

    @property
    def dry_run(self) -> bool:
        return self.get("remediation", "dry_run_default", True)

    @property
    def failure_rules(self) -> Dict[str, Any]:
        return self.get("thresholds", default={})

    @property
    def raw(self) -> Dict[str, Any]:
        return self._config


# Global singleton instance
_default_manager = None


def get_config(config_path: str = None) -> ConfigManager:
    """Returns the active configuration manager instance."""
    global _default_manager
    if _default_manager is None or config_path is not None:
        _default_manager = ConfigManager(config_path)
    return _default_manager
