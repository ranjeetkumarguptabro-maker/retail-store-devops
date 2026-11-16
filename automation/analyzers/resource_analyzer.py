"""Analyzes cluster and pod resource utilization, capacity limits, and anomalies."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("operations_engine.analyzers.resource")


class ResourceAnomalyAnalyzer:
    """Detects resource bottlenecks, capacity exhaustion, and configuration anomalies."""

    def __init__(
        self,
        cpu_warning_pct: float = 80.0,
        cpu_critical_pct: float = 90.0,
        memory_warning_pct: float = 80.0,
        memory_critical_pct: float = 90.0,
    ):
        self.cpu_warning_pct = cpu_warning_pct
        self.cpu_critical_pct = cpu_critical_pct
        self.memory_warning_pct = memory_warning_pct
        self.memory_critical_pct = memory_critical_pct

    def analyze(
        self,
        resource_data: Dict[str, Any],
        nodes_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Performs resource anomaly detection across pods, services, and nodes."""
        anomalies: List[Dict[str, Any]] = []
        recommendations: List[str] = []

        services = resource_data.get("services", {})
        total_cpu_req = resource_data.get("total_requested_cpu_cores", 0.0)
        total_mem_mb = resource_data.get("total_requested_memory_mb", 0.0)

        # 1. Audit microservices for missing requests or limits
        for svc_name, svc_info in services.items():
            containers = svc_info.get("containers", [])
            for c in containers:
                pod = c.get("pod", "unknown")
                c_name = c.get("container", "unknown")
                cpu_req = c.get("cpu_request", 0.0)
                cpu_lim = c.get("cpu_limit", 0.0)
                mem_req = c.get("memory_request_bytes", 0)
                mem_lim = c.get("memory_limit_bytes", 0)

                if cpu_req == 0.0 or mem_req == 0:
                    anomalies.append({
                        "type": "MissingResourceRequests",
                        "severity": "WARNING",
                        "target": f"{svc_name}/{pod}/{c_name}",
                        "message": f"Container {c_name} in service {svc_name} lacks CPU or Memory requests.",
                    })
                    recommendations.append(
                        f"Define CPU and memory requests for '{svc_name}' to guarantee scheduler reservation."
                    )

                if cpu_lim == 0.0 or mem_lim == 0:
                    anomalies.append({
                        "type": "MissingResourceLimits",
                        "severity": "WARNING",
                        "target": f"{svc_name}/{pod}/{c_name}",
                        "message": f"Container {c_name} in service {svc_name} lacks CPU or Memory limits.",
                    })
                    recommendations.append(
                        f"Enforce memory limits on '{svc_name}' to prevent noisy neighbor starvation."
                    )

        # 2. Check node capacity vs total requests if node data is available
        total_node_cpu = 0.0
        total_node_mem_mb = 0.0

        if nodes_data:
            for node in nodes_data:
                name = node.get("name", "node")
                ready = node.get("ready", False)
                conditions = node.get("conditions", {})

                if not ready:
                    anomalies.append({
                        "type": "NodeNotReady",
                        "severity": "CRITICAL",
                        "target": name,
                        "message": f"Cluster node '{name}' is in NotReady state.",
                    })
                if conditions.get("MemoryPressure"):
                    anomalies.append({
                        "type": "NodeMemoryPressure",
                        "severity": "CRITICAL",
                        "target": name,
                        "message": f"Cluster node '{name}' is experiencing MemoryPressure.",
                    })
                if conditions.get("DiskPressure"):
                    anomalies.append({
                        "type": "NodeDiskPressure",
                        "severity": "HIGH",
                        "target": name,
                        "message": f"Cluster node '{name}' is reporting DiskPressure.",
                    })

                # Parse allocatable capacity
                alloc = node.get("allocatable", {})
                cpu_str = str(alloc.get("cpu", "0"))
                try:
                    total_node_cpu += float(cpu_str)
                except ValueError:
                    pass

                mem_str = str(alloc.get("memory", "0Ki"))
                if mem_str.endswith("Ki"):
                    total_node_mem_mb += float(mem_str[:-2]) / 1024.0
                elif mem_str.endswith("Mi"):
                    total_node_mem_mb += float(mem_str[:-2])
                elif mem_str.endswith("Gi"):
                    total_node_mem_mb += float(mem_str[:-2]) * 1024.0

        # Calculate allocation percentage if nodes are present
        cpu_alloc_pct = round((total_cpu_req / total_node_cpu) * 100.0, 1) if total_node_cpu > 0 else 0.0
        mem_alloc_pct = round((total_mem_mb / total_node_mem_mb) * 100.0, 1) if total_node_mem_mb > 0 else 0.0

        if cpu_alloc_pct >= self.cpu_critical_pct:
            anomalies.append({
                "type": "ClusterCPUCapacityCritical",
                "severity": "CRITICAL",
                "target": "cluster",
                "message": f"Cluster CPU allocation at {cpu_alloc_pct}% (critical threshold: {self.cpu_critical_pct}%).",
            })
            recommendations.append("Scale out node group or reduce microservice CPU requests.")
        elif cpu_alloc_pct >= self.cpu_warning_pct:
            anomalies.append({
                "type": "ClusterCPUCapacityWarning",
                "severity": "WARNING",
                "target": "cluster",
                "message": f"Cluster CPU allocation at {cpu_alloc_pct}% (warning threshold: {self.cpu_warning_pct}%).",
            })

        if mem_alloc_pct >= self.memory_critical_pct:
            anomalies.append({
                "type": "ClusterMemoryCapacityCritical",
                "severity": "CRITICAL",
                "target": "cluster",
                "message": f"Cluster memory allocation at {mem_alloc_pct}% (critical threshold: {self.memory_critical_pct}%).",
            })
            recommendations.append("Add worker nodes to prevent OOM evictions.")
        elif mem_alloc_pct >= self.memory_warning_pct:
            anomalies.append({
                "type": "ClusterMemoryCapacityWarning",
                "severity": "WARNING",
                "target": "cluster",
                "message": f"Cluster memory allocation at {mem_alloc_pct}% (warning threshold: {self.memory_warning_pct}%).",
            })

        # Deduplicate recommendations
        unique_recommendations = list(dict.fromkeys(recommendations))

        status = "HEALTHY"
        if any(a["severity"] == "CRITICAL" for a in anomalies):
            status = "CRITICAL"
        elif any(a["severity"] in ("HIGH", "WARNING") for a in anomalies):
            status = "WARNING"

        return {
            "status": status,
            "cpu_allocation_percent": cpu_alloc_pct,
            "memory_allocation_percent": mem_alloc_pct,
            "total_requested_cpu_cores": total_cpu_req,
            "total_requested_memory_mb": total_mem_mb,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "recommendations": unique_recommendations,
        }
