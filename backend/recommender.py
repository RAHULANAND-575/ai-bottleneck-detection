"""
Optimization Recommendation Engine
Maps detected bottleneck types to actionable, prioritised strategies.
"""


class Recommender:
    """
    Generates targeted optimization recommendations based on detected bottlenecks.
    Each recommendation includes a strategy, priority, expected impact, and details.
    """

    # Strategy catalogue keyed by bottleneck type
    _STRATEGIES: dict[str, list[dict]] = {
        "compute-bound": [
            {
                "strategy": "Offload computation to GPU",
                "priority": "high",
                "impact": "high",
                "details": (
                    "Move CPU-heavy kernels (matrix ops, FFTs, ML inference) to the GPU "
                    "using CUDA/OpenCL or frameworks like CuPy, PyTorch, or TensorFlow."
                ),
            },
            {
                "strategy": "Optimize parallel thread utilisation",
                "priority": "high",
                "impact": "medium",
                "details": (
                    "Profile thread contention with tools like Intel VTune or Linux perf. "
                    "Use thread pools, avoid over-subscription, and pin threads to cores."
                ),
            },
            {
                "strategy": "Use vectorised (SIMD) operations",
                "priority": "medium",
                "impact": "medium",
                "details": (
                    "Replace scalar loops with NumPy/SciPy vectorisation or compiler "
                    "auto-vectorisation hints (e.g., -O3 -march=native for GCC/Clang)."
                ),
            },
            {
                "strategy": "Enable Just-In-Time (JIT) compilation",
                "priority": "medium",
                "impact": "medium",
                "details": (
                    "Use Numba or Cython to JIT-compile hot loops, "
                    "achieving near-native performance for Python code."
                ),
            },
        ],
        "memory-bound": [
            {
                "strategy": "Increase effective memory bandwidth with pooling",
                "priority": "high",
                "impact": "high",
                "details": (
                    "Pre-allocate and reuse memory buffers to avoid repeated "
                    "malloc/free overhead. Use memory-pool libraries (e.g., rmm for GPU)."
                ),
            },
            {
                "strategy": "Optimize data locality and cache usage",
                "priority": "high",
                "impact": "high",
                "details": (
                    "Restructure data accesses to improve spatial/temporal locality. "
                    "Consider AoS → SoA transformations and blocking/tiling strategies."
                ),
            },
            {
                "strategy": "Upgrade or expand system RAM / VRAM",
                "priority": "medium",
                "impact": "high",
                "details": (
                    "If the system consistently exceeds 80 % memory utilisation, "
                    "adding physical RAM or switching to a GPU with larger VRAM "
                    "provides immediate headroom."
                ),
            },
            {
                "strategy": "Compress in-memory data representations",
                "priority": "low",
                "impact": "medium",
                "details": (
                    "Use mixed-precision (FP16/BF16) for ML workloads, or columnar "
                    "compression (Arrow, Parquet) for analytical pipelines."
                ),
            },
        ],
        "I/O-bound": [
            {
                "strategy": "Switch to asynchronous I/O",
                "priority": "high",
                "impact": "high",
                "details": (
                    "Replace blocking read/write calls with async alternatives "
                    "(Python asyncio + aiofiles, io_uring on Linux) to overlap I/O "
                    "with computation."
                ),
            },
            {
                "strategy": "Enable multi-level caching",
                "priority": "high",
                "impact": "high",
                "details": (
                    "Cache hot data in RAM (Redis, in-process LRU) and leverage OS "
                    "page-cache hints (posix_fadvise). Use SSDs with NVMe where possible."
                ),
            },
            {
                "strategy": "Batch and prefetch I/O operations",
                "priority": "medium",
                "impact": "medium",
                "details": (
                    "Group small reads/writes into larger sequential operations. "
                    "Use prefetch buffers in ML data-loading pipelines "
                    "(e.g., tf.data.Dataset.prefetch or PyTorch DataLoader workers)."
                ),
            },
        ],
        "communication-bound": [
            {
                "strategy": "Minimise CPU↔GPU data transfers",
                "priority": "high",
                "impact": "high",
                "details": (
                    "Audit PCIe transfers with NVIDIA Nsight Systems. Keep intermediate "
                    "tensors on the GPU and only move final results back to the host."
                ),
            },
            {
                "strategy": "Use CUDA pinned (page-locked) memory",
                "priority": "high",
                "impact": "medium",
                "details": (
                    "Allocate host buffers with cudaMallocHost/torch.cuda.pin_memory() "
                    "to unlock DMA for faster H2D and D2H transfers."
                ),
            },
            {
                "strategy": "Overlap computation and communication",
                "priority": "medium",
                "impact": "high",
                "details": (
                    "Use CUDA streams or async copy APIs (cudaMemcpyAsync) to pipeline "
                    "GPU kernels and data transfers concurrently."
                ),
            },
            {
                "strategy": "Upgrade to a higher-bandwidth interconnect",
                "priority": "low",
                "impact": "high",
                "details": (
                    "Consider NVLink, PCIe 4.0/5.0, or multi-GPU NVSwitch fabrics "
                    "for workloads where PCIe 3.0 bandwidth is a hard limit."
                ),
            },
        ],
        "none": [
            {
                "strategy": "Continue monitoring baseline performance",
                "priority": "low",
                "impact": "low",
                "details": (
                    "No bottleneck detected at this time. Maintain scheduled profiling "
                    "intervals to catch emerging issues early."
                ),
            },
        ],
    }

    def recommend(self, bottlenecks: list[dict]) -> list[dict]:
        """
        Generate optimization recommendations for the given bottlenecks.

        Args:
            bottlenecks: List of bottleneck dicts from BottleneckDetector.detect().

        Returns:
            list[dict]: Deduplicated recommendations sorted by priority.
        """
        seen_strategies: set[str] = set()
        recommendations: list[dict] = []

        priority_order = {"high": 0, "medium": 1, "low": 2}

        for bottleneck in bottlenecks:
            b_type = bottleneck.get("type", "none")
            strategies = self._STRATEGIES.get(b_type, self._STRATEGIES["none"])
            for rec in strategies:
                if rec["strategy"] not in seen_strategies:
                    seen_strategies.add(rec["strategy"])
                    recommendations.append({**rec, "bottleneck_type": b_type})

        # Sort: high-priority first, then by impact
        recommendations.sort(
            key=lambda r: (
                priority_order.get(r["priority"], 99),
                priority_order.get(r["impact"], 99),
            )
        )
        return recommendations
