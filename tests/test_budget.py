"""Tests for budget enforcement logic."""

from agentforge.api.schemas import TaskConstraints, TaskCreateRequest


class TestTaskConstraints:
    def test_defaults(self):
        c = TaskConstraints()
        assert c.timeout is None
        assert c.max_cost_usd is None

    def test_explicit_values(self):
        c = TaskConstraints(timeout=600, max_cost_usd=5.0)
        assert c.timeout == 600
        assert c.max_cost_usd == 5.0

    def test_task_request_with_constraints(self):
        req = TaskCreateRequest(
            agent_id="test-agent",
            inputs={"topic": "AI"},
            constraints=TaskConstraints(timeout=900, max_cost_usd=10.0),
        )
        assert req.constraints.timeout == 900
        assert req.constraints.max_cost_usd == 10.0

    def test_task_request_default_constraints(self):
        req = TaskCreateRequest(agent_id="test-agent")
        assert req.constraints.timeout is None
        assert req.constraints.max_cost_usd is None


class TestBudgetEnforcement:
    """Tests for the budget check logic extracted from route handler."""

    def _check_budget(self, agent_price: float, max_cost: float | None) -> bool:
        """Simulate budget check from create_task route."""
        if max_cost is not None and agent_price > max_cost:
            return False
        return True

    def test_within_budget(self):
        assert self._check_budget(3.0, 5.0) is True

    def test_exceeds_budget(self):
        assert self._check_budget(10.0, 5.0) is False

    def test_exact_budget(self):
        assert self._check_budget(5.0, 5.0) is True

    def test_no_budget_cap(self):
        assert self._check_budget(100.0, None) is True

    def _enforce_timeout(self, task_timeout: int | None, agent_max: int) -> int:
        """Simulate timeout enforcement from create_task route."""
        if task_timeout is not None:
            return max(60, min(task_timeout, agent_max))
        return agent_max

    def test_timeout_within_agent_max(self):
        assert self._enforce_timeout(600, 3600) == 600

    def test_timeout_exceeds_agent_max(self):
        assert self._enforce_timeout(7200, 3600) == 3600

    def test_timeout_below_floor(self):
        assert self._enforce_timeout(10, 3600) == 60

    def test_timeout_default(self):
        assert self._enforce_timeout(None, 1800) == 1800
