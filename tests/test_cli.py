"""Tests for the AgentForge CLI."""

import json

from typer.testing import CliRunner

from agentforge.cli.main import app

runner = CliRunner()


class TestCLIHelp:
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Agent Commerce Infrastructure CLI" in result.output

    def test_login_help(self):
        result = runner.invoke(app, ["login", "--help"])
        assert result.exit_code == 0
        assert "api-key" in result.output.lower()

    def test_agents_help(self):
        result = runner.invoke(app, ["agents", "--help"])
        assert result.exit_code == 0
        assert "search" in result.output.lower() or "query" in result.output.lower()

    def test_run_help(self):
        result = runner.invoke(app, ["run", "--help"])
        assert result.exit_code == 0
        assert "agent" in result.output.lower()

    def test_status_help(self):
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0

    def test_results_help(self):
        result = runner.invoke(app, ["results", "--help"])
        assert result.exit_code == 0

    def test_health_help(self):
        result = runner.invoke(app, ["health", "--help"])
        assert result.exit_code == 0

    def test_publish_help(self):
        result = runner.invoke(app, ["publish", "--help"])
        assert result.exit_code == 0
        assert "yaml" in result.output.lower() or "json" in result.output.lower()

    def test_rate_help(self):
        result = runner.invoke(app, ["rate", "--help"])
        assert result.exit_code == 0

    def test_inspect_help(self):
        result = runner.invoke(app, ["inspect", "--help"])
        assert result.exit_code == 0

    def test_all_commands_present(self):
        result = runner.invoke(app, ["--help"])
        commands = [
            "login", "logout", "whoami", "agents", "inspect",
            "publish", "run", "status", "results", "logs", "health", "rate",
        ]
        for cmd in commands:
            assert cmd in result.output, f"Command '{cmd}' missing from help"


class TestCLIConfig:
    def test_login_saves_config(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        monkeypatch.setattr(
            "agentforge.cli.config.CONFIG_FILE", config_file
        )
        monkeypatch.setattr(
            "agentforge.cli.config.CONFIG_DIR", tmp_path
        )
        # Also patch the main module's imports
        monkeypatch.setattr(
            "agentforge.cli.main.save_config",
            lambda key, endpoint=None: config_file.write_text(
                json.dumps({"api_key": key, "endpoint": endpoint})
            ),
        )

        result = runner.invoke(app, ["login", "--api-key", "af_test123"])
        assert result.exit_code == 0
        assert "logged in" in result.output.lower()

    def test_logout(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"api_key": "af_test"}))
        monkeypatch.setattr("agentforge.cli.config.CONFIG_FILE", config_file)
        monkeypatch.setattr(
            "agentforge.cli.main.clear_config",
            lambda: config_file.unlink(missing_ok=True),
        )
        result = runner.invoke(app, ["logout"])
        assert result.exit_code == 0
        assert "logged out" in result.output.lower()

    def test_whoami_not_logged_in(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "agentforge.cli.main.get_api_key", lambda: None
        )
        result = runner.invoke(app, ["whoami"])
        assert result.exit_code == 1
        assert "not logged in" in result.output.lower()


class TestCLIValidation:
    def test_run_invalid_json(self, monkeypatch):
        monkeypatch.setattr(
            "agentforge.cli.main.get_client",
            lambda: None,
        )
        monkeypatch.setattr("agentforge.cli.main.get_api_key", lambda: "af_test")
        result = runner.invoke(app, ["run", "test-agent", "-i", "{invalid json}"])
        assert result.exit_code == 1

    def test_rate_invalid_score(self, monkeypatch):
        monkeypatch.setattr("agentforge.cli.main.get_api_key", lambda: "af_test")
        result = runner.invoke(app, ["rate", "task-123", "6"])
        assert result.exit_code == 1

    def test_publish_file_not_found(self, monkeypatch):
        monkeypatch.setattr("agentforge.cli.main.get_api_key", lambda: "af_test")
        result = runner.invoke(app, ["publish", "/nonexistent/agent.yaml"])
        assert result.exit_code == 1
