"""Tests for the result retrieval API endpoint."""

from pathlib import Path


class TestResultEndpoint:
    def test_rejects_disallowed_file(self):
        from agentforge.api.routes_tasks import _ALLOWED_RESULT_FILES

        assert "output.md" in _ALLOWED_RESULT_FILES
        assert "stdout.log" in _ALLOWED_RESULT_FILES
        assert "stderr.log" in _ALLOWED_RESULT_FILES
        assert "usage.json" in _ALLOWED_RESULT_FILES
        assert "../../../etc/passwd" not in _ALLOWED_RESULT_FILES
        assert "secrets.env" not in _ALLOWED_RESULT_FILES

    def test_whitelist_is_four_files(self):
        from agentforge.api.routes_tasks import _ALLOWED_RESULT_FILES

        assert len(_ALLOWED_RESULT_FILES) == 4

    def test_result_file_path_construction(self, tmp_path):
        """Verify file path is constructed safely from results_path + file name."""
        results_dir = tmp_path / "run-001"
        results_dir.mkdir()
        (results_dir / "output.md").write_text("# Results\nDone.")
        (results_dir / "usage.json").write_text('{"tokens": 500}')

        # Simulate the path construction from the endpoint
        file_path = Path(str(results_dir)) / "output.md"
        assert file_path.is_file()
        assert file_path.read_text() == "# Results\nDone."

        json_path = Path(str(results_dir)) / "usage.json"
        assert json_path.is_file()

    def test_missing_file_detected(self, tmp_path):
        """File not present in results dir should be caught."""
        results_dir = tmp_path / "run-002"
        results_dir.mkdir()

        file_path = Path(str(results_dir)) / "output.md"
        assert not file_path.is_file()


class TestExecutionResponseSchema:
    def test_includes_results_path(self):
        from agentforge.api.schemas import ExecutionResponse

        fields = ExecutionResponse.model_fields
        assert "results_path" in fields
        assert fields["results_path"].default is None
