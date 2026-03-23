"""
Evaluation metrics: accuracy, safety, and latency scoring.
"""
from dataclasses import dataclass


@dataclass
class EvalMetrics:
    total_cases: int = 0
    correct: int = 0
    safety_violations: int = 0
    avg_latency_ms: float = 0.0

    @property
    def accuracy(self) -> float:
        return self.correct / self.total_cases if self.total_cases > 0 else 0.0

    @property
    def safety_rate(self) -> float:
        blocked = self.total_cases - self.safety_violations
        return blocked / self.total_cases if self.total_cases > 0 else 0.0
