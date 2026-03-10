"""
AI/ML Bottleneck Detector
Hybrid rule-based and ML-scored bottleneck detection for heterogeneous systems.
"""

import time
import numpy as np
from backend.monitor import SystemMonitor


class BottleneckDetector:
    """
    Detects CPU/GPU/memory/I-O/communication bottlenecks using a combination
    of rule-based thresholds and simulated ML confidence scoring.
    """

    # Rule-based thresholds
    THRESHOLDS = {
        "compute_bound_cpu": 85.0,    # CPU % above this → compute-bound
        "memory_bound": 80.0,          # RAM % above this → memory-bound
        "gpu_memory_bound": 80.0,      # GPU memory % above this → memory-bound
        "io_bound_disk": 100 * 1024 * 1024,  # 100 MB/s disk throughput
        "communication_bound_pcie": 10.0,     # PCIe throughput > 10 GB/s
    }

    def __init__(self):
        self.monitor = SystemMonitor()
        self._rng = np.random.default_rng(seed=int(time.time()) % 1000)

    def _ml_confidence(self, base_score: float) -> float:
        """
        Simulate an ML model confidence score by adding calibrated noise to a
        rule-based base score. Keeps result in [0.0, 1.0].
        """
        noise = self._rng.normal(0, 0.05)
        return float(np.clip(base_score + noise, 0.0, 1.0))

    @staticmethod
    def _severity(confidence: float) -> str:
        """Map a confidence score to a human-readable severity level."""
        if confidence < 0.4:
            return "low"
        if confidence < 0.7:
            return "medium"
        return "high"

    def detect(self) -> list[dict]:
        """
        Run the full bottleneck detection pipeline.

        Returns:
            list[dict]: Each element has keys: type, severity, confidence,
                        description, and timestamp.
        """
        metrics = self.monitor.get_all_metrics()
        bottlenecks = []
        ts = metrics.get("timestamp", time.time())

        # ── Compute-bound ────────────────────────────────────────────────────
        cpu = metrics.get("cpu_percent", 0)
        gpu_load = metrics.get("gpu_load_percent", 0)
        compute_score = max(
            cpu / 100.0,
            gpu_load / 100.0,
        )
        if cpu > self.THRESHOLDS["compute_bound_cpu"] or gpu_load > self.THRESHOLDS["compute_bound_cpu"]:
            conf = self._ml_confidence(compute_score)
            bottlenecks.append({
                "type": "compute-bound",
                "severity": self._severity(conf),
                "confidence": round(conf, 3),
                "description": (
                    f"CPU at {cpu}% and GPU at {gpu_load}% — system is "
                    "heavily compute-bound. Parallelism or GPU offloading recommended."
                ),
                "timestamp": ts,
            })

        # ── Memory-bound ─────────────────────────────────────────────────────
        ram = metrics.get("memory_percent", 0)
        gpu_mem = metrics.get("gpu_memory_percent", 0)
        mem_score = max(ram / 100.0, gpu_mem / 100.0)
        if ram > self.THRESHOLDS["memory_bound"] or gpu_mem > self.THRESHOLDS["gpu_memory_bound"]:
            conf = self._ml_confidence(mem_score)
            bottlenecks.append({
                "type": "memory-bound",
                "severity": self._severity(conf),
                "confidence": round(conf, 3),
                "description": (
                    f"RAM at {ram}%, GPU memory at {gpu_mem}% — "
                    "memory pressure is limiting throughput."
                ),
                "timestamp": ts,
            })

        # ── I/O-bound ────────────────────────────────────────────────────────
        disk_read = metrics.get("disk_read_bytes", 0)
        disk_write = metrics.get("disk_write_bytes", 0)
        total_disk = disk_read + disk_write
        io_score = min(total_disk / (500 * 1024 * 1024), 1.0)  # normalise to 500 MB/s
        if total_disk > self.THRESHOLDS["io_bound_disk"]:
            conf = self._ml_confidence(io_score)
            bottlenecks.append({
                "type": "I/O-bound",
                "severity": self._severity(conf),
                "confidence": round(conf, 3),
                "description": (
                    f"Disk I/O at {round(total_disk / (1024**2), 1)} MB/s — "
                    "storage throughput may be constraining performance."
                ),
                "timestamp": ts,
            })

        # ── Communication-bound ──────────────────────────────────────────────
        pcie = metrics.get("pcie_throughput_gbps", 0)
        pcie_score = pcie / 16.0  # normalise to PCIe 3.0 x16 max
        if pcie > self.THRESHOLDS["communication_bound_pcie"]:
            conf = self._ml_confidence(pcie_score)
            bottlenecks.append({
                "type": "communication-bound",
                "severity": self._severity(conf),
                "confidence": round(conf, 3),
                "description": (
                    f"PCIe throughput at {pcie} GB/s — CPU↔GPU data transfers "
                    "are saturating the interconnect."
                ),
                "timestamp": ts,
            })

        # Always return at least one entry so the UI is never empty
        if not bottlenecks:
            bottlenecks.append({
                "type": "none",
                "severity": "low",
                "confidence": round(self._ml_confidence(0.1), 3),
                "description": (
                    f"System operating normally. CPU {cpu}%, RAM {ram}%, "
                    f"GPU {gpu_load}% — no significant bottleneck detected."
                ),
                "timestamp": ts,
            })

        return bottlenecks
