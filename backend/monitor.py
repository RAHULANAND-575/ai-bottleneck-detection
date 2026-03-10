"""
System Metrics Collector
Collects real-time CPU, RAM, disk I/O, and GPU metrics from the host system.
"""

import time
import psutil

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

import random


class SystemMonitor:
    """Collects system-level performance metrics for bottleneck analysis."""

    def get_metrics(self) -> dict:
        """
        Gather CPU, RAM, and disk I/O metrics using psutil.

        Returns:
            dict: Structured metrics with cpu_percent, memory_percent,
                  disk_read_bytes, disk_write_bytes, and timestamp.
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()

        return {
            "cpu_percent": round(cpu_percent, 1),
            "memory_percent": round(memory.percent, 1),
            "memory_used_gb": round(memory.used / (1024 ** 3), 2),
            "memory_total_gb": round(memory.total / (1024 ** 3), 2),
            "disk_read_bytes": disk_io.read_bytes if disk_io else 0,
            "disk_write_bytes": disk_io.write_bytes if disk_io else 0,
            "cpu_count": psutil.cpu_count(logical=True),
            "timestamp": time.time(),
        }

    def get_gpu_metrics(self) -> dict:
        """
        Gather GPU metrics using GPUtil. Falls back to simulated values
        if no GPU is detected or GPUtil is unavailable.

        Returns:
            dict: GPU load %, memory usage %, temperature, and availability flag.
        """
        if GPU_AVAILABLE:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return {
                    "gpu_available": True,
                    "gpu_name": gpu.name,
                    "gpu_load_percent": round(gpu.load * 100, 1),
                    "gpu_memory_percent": round(
                        (gpu.memoryUsed / gpu.memoryTotal) * 100, 1
                    ) if gpu.memoryTotal > 0 else 0,
                    "gpu_memory_used_mb": round(gpu.memoryUsed, 1),
                    "gpu_memory_total_mb": round(gpu.memoryTotal, 1),
                    "gpu_temperature": gpu.temperature,
                    "timestamp": time.time(),
                }

        # Simulated GPU metrics when no physical GPU is available
        return {
            "gpu_available": False,
            "gpu_name": "Simulated GPU",
            "gpu_load_percent": round(random.uniform(20, 95), 1),
            "gpu_memory_percent": round(random.uniform(15, 85), 1),
            "gpu_memory_used_mb": round(random.uniform(512, 6000), 1),
            "gpu_memory_total_mb": 8192.0,
            "gpu_temperature": round(random.uniform(45, 82), 1),
            "timestamp": time.time(),
        }

    def get_all_metrics(self) -> dict:
        """
        Collect and merge all system and GPU metrics into a single dict.

        Returns:
            dict: Combined CPU, memory, disk, and GPU metrics.
        """
        metrics = self.get_metrics()
        gpu_metrics = self.get_gpu_metrics()
        metrics.update(gpu_metrics)
        # Simulated PCIe throughput in GB/s
        metrics["pcie_throughput_gbps"] = round(random.uniform(0.5, 16.0), 2)
        return metrics
