from typing import Dict, Any

class MetricsNormalizer:

    @staticmethod
    def normalize_metrics(raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "cpu_average": round(float(raw_metrics.get("cpu_average", 0.0)), 2),
            "cpu_p95": round(float(raw_metrics.get("cpu_p95", 0.0)), 2),
            "memory_average": round(float(raw_metrics.get("memory_average", 0.0)), 2),
            "memory_p95": round(float(raw_metrics.get("memory_p95", 0.0)), 2),
        }
