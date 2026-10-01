"""Tests for custom environment hooks (e.g., sudo execution)."""

import pytest


@pytest.fixture
def mock_allowed_log_paths(mocker):
    """Fixture factory to set CONFIG.allowed_log_paths for read_log_file tests."""

    def _set_paths(paths=""):
        mock_config = mocker.patch("linux_mcp_server.tools.logs.CONFIG")
        mock_config.allowed_log_paths = paths
        return mock_config

    return _set_paths


class TestCustomSudoLogReading:
    """Tests that remote head/tail commands are wrapped with sudo -n when enabled."""

    @pytest.mark.parametrize("first_lines", [True, False])
    async def test_remote_read_log_file_uses_sudo_when_configured(
        self, mcp_client, mock_allowed_log_paths, monkeypatch, mock_execute_with_fallback, first_lines
    ):
        log_path = "/var/log/messages"
        mock_allowed_log_paths(log_path)
        monkeypatch.setenv("LINUX_MCP_LOG_USE_SUDO", "true")
        mock_execute_with_fallback.return_value = (0, "Log entry\n", "")

        arguments: dict[str, object] = {"log_path": log_path, "host": "remote.server.com"}
        arguments["first_lines" if first_lines else "last_lines"] = 5
        await mcp_client.call_tool("read_log_file", arguments)

        assert mock_execute_with_fallback.called
        called_cmd = mock_execute_with_fallback.call_args[0][0]
        assert called_cmd[:2] == ("/usr/bin/sudo", "-n")
        assert "head" in called_cmd[2] or "tail" in called_cmd[2]

    async def test_remote_read_log_file_without_sudo_runs_standard_command(
        self, mcp_client, mock_allowed_log_paths, monkeypatch, mock_execute_with_fallback
    ):
        log_path = "/var/log/messages"
        mock_allowed_log_paths(log_path)
        monkeypatch.delenv("LINUX_MCP_LOG_USE_SUDO", raising=False)
        mock_execute_with_fallback.return_value = (0, "Log entry\n", "")

        await mcp_client.call_tool("read_log_file", {"log_path": log_path, "host": "remote.server.com"})

        assert mock_execute_with_fallback.called
        called_cmd = mock_execute_with_fallback.call_args[0][0]
        assert called_cmd[0] != "/usr/bin/sudo"

    async def test_local_read_log_file_never_uses_sudo(
        self, mcp_client, mock_allowed_log_paths, monkeypatch, mock_execute_with_fallback, tmp_path
    ):
        log_file = tmp_path / "allowed.log"
        log_file.write_text("local log\n")
        mock_allowed_log_paths(str(log_file))
        monkeypatch.setenv("LINUX_MCP_LOG_USE_SUDO", "true")
        mock_execute_with_fallback.return_value = (0, "local log\n", "")

        await mcp_client.call_tool("read_log_file", {"log_path": str(log_file), "host": "localhost"})

        command_args = mock_execute_with_fallback.call_args.args[0]
        assert command_args[0] != "sudo"
