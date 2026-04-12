"""Trust Score Algorithm.

Computes a weighted trust score (0.00 to 1.00) for agents based on:
  - Success Rate (40%): ratio of successful executions
  - Duration Accuracy (30%): how close actual avg matches estimated
  - Volume Confidence (20%): logarithmic scaling, full confidence at 100+ runs
  - Recency Bonus (10%): reserved for future decay based on last execution time

The score becomes meaningful after 5+ executions. Below that, it returns
a provisional score with a volume penalty.
"""

import math


def compute_trust_score(
    total_executions: int,
    success_count: int,
    avg_duration: float,
    expected_duration: float,
    last_execution_age_hours: float = 0,
) -> float:
    """Compute weighted trust score for an agent.

    Returns a score between 0.00 and 1.00.
    """
    if total_executions == 0:
        return 0.0

    # 1. Success Rate (weight: 0.40)
    success_rate = success_count / total_executions
    w_success = success_rate * 0.40

    # 2. Duration Accuracy (weight: 0.30)
    # How close is the actual avg to the estimated duration?
    # Perfect = 1.0, decays as ratio diverges from 1.0
    if expected_duration > 0 and avg_duration > 0:
        ratio = avg_duration / expected_duration
        # Gaussian-like decay: 1.0 at ratio=1.0, drops off for over/under
        duration_accuracy = math.exp(-2.0 * (ratio - 1.0) ** 2)
    else:
        duration_accuracy = 0.5  # unknown, neutral
    w_duration = duration_accuracy * 0.30

    # 3. Volume Confidence (weight: 0.20)
    # Logarithmic scaling: reaches ~1.0 at 100 executions
    volume_confidence = min(1.0, math.log1p(total_executions) / math.log1p(100))
    w_volume = volume_confidence * 0.20

    # 4. Recency (weight: 0.10)
    # Full score if last execution was recent, decays over 30 days
    if last_execution_age_hours > 0:
        recency = min(1.0, math.exp(-last_execution_age_hours / 720))  # 30 day half-life
    else:
        recency = 1.0  # assume recent if unknown
    w_recency = recency * 0.10

    score = w_success + w_duration + w_volume + w_recency

    # Clamp to [0, 1]
    return round(max(0.0, min(1.0, score)), 2)
