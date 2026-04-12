"""Tests for the trust scoring algorithm."""

from agentforge.trust import compute_trust_score


class TestTrustScore:
    def test_zero_executions_returns_zero(self):
        assert compute_trust_score(0, 0, 0, 300) == 0.0

    def test_perfect_agent(self):
        """Agent with 100% success, exact duration, 200 runs."""
        score = compute_trust_score(
            total_executions=200,
            success_count=200,
            avg_duration=300,
            expected_duration=300,
        )
        # Should be very close to 1.0
        assert score >= 0.95

    def test_failing_agent(self):
        """Agent with 0% success rate."""
        score = compute_trust_score(
            total_executions=50,
            success_count=0,
            avg_duration=300,
            expected_duration=300,
        )
        # Success component is 0, so score should be low
        assert score < 0.60

    def test_slow_agent_penalized(self):
        """Agent taking 3x expected duration gets penalized."""
        fast = compute_trust_score(100, 90, 300, 300)
        slow = compute_trust_score(100, 90, 900, 300)
        assert fast > slow

    def test_low_volume_penalty(self):
        """Agent with few runs gets lower confidence."""
        few = compute_trust_score(3, 3, 300, 300)
        many = compute_trust_score(100, 100, 300, 300)
        assert many > few

    def test_score_bounded(self):
        """Score always between 0 and 1."""
        for total in [1, 5, 10, 50, 100, 1000]:
            for success in [0, total // 2, total]:
                score = compute_trust_score(total, success, 300, 300)
                assert 0.0 <= score <= 1.0

    def test_recency_decay(self):
        """Old agents get penalized."""
        recent = compute_trust_score(50, 45, 300, 300, last_execution_age_hours=1)
        old = compute_trust_score(50, 45, 300, 300, last_execution_age_hours=720)
        assert recent > old

    def test_mixed_performance(self):
        """Realistic 80% success, 1.5x duration, 30 runs."""
        score = compute_trust_score(
            total_executions=30,
            success_count=24,
            avg_duration=450,
            expected_duration=300,
        )
        # Should be moderate
        assert 0.40 < score < 0.80

    def test_duration_accuracy_symmetric(self):
        """Both too fast and too slow are penalized."""
        exact = compute_trust_score(50, 50, 300, 300)
        fast = compute_trust_score(50, 50, 100, 300)
        slow = compute_trust_score(50, 50, 600, 300)
        assert exact > fast
        assert exact > slow
