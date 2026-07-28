"""Tests for EU AI Act Art. 19 retention floor enforcement."""

from agentforge import cleanup


class TestRetentionFloor:
    def test_default_meets_art_19_floor(self):
        assert cleanup.enforce_ai_act_retention_floor() >= cleanup.AI_ACT_MIN_LOG_RETENTION_DAYS

    def test_below_floor_is_clamped(self, monkeypatch):
        monkeypatch.setattr(cleanup.settings, "event_log_retention_days", 30)
        assert cleanup.enforce_ai_act_retention_floor() == cleanup.AI_ACT_MIN_LOG_RETENTION_DAYS

    def test_above_floor_is_kept(self, monkeypatch):
        monkeypatch.setattr(cleanup.settings, "event_log_retention_days", 365)
        assert cleanup.enforce_ai_act_retention_floor() == 365

    def test_exactly_at_floor(self, monkeypatch):
        monkeypatch.setattr(cleanup.settings, "event_log_retention_days", 180)
        assert cleanup.enforce_ai_act_retention_floor() == 180
