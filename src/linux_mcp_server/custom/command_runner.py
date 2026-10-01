"""Custom runner wrapper to support sudo commands without editing core files."""

from collections.abc import Sequence
from pathlib import Path

import linux_mcp_server.commands as commands_mod

from linux_mcp_server.custom.config import is_log_use_sudo_enabled
from linux_mcp_server.utils.types import Host
from linux_mcp_server.utils.types import LOCALHOST


_orig_run = commands_mod.CommandSpec.run
_orig_run_bytes = commands_mod.CommandSpec.run_bytes


def _adjust_args_for_sudo(args: Sequence[str], host: Host) -> Sequence[str]:
    """Prepend sudo -n to remote head/tail commands if enabled."""
    if host != LOCALHOST and is_log_use_sudo_enabled() and args:
        bin_name = Path(args[0]).name
        if bin_name in {"head", "tail"}:
            if not (len(args) >= 2 and args[0] == "sudo" and args[1] == "-n"):
                return ("/usr/bin/sudo", "-n", *args)
    return args


async def custom_run(self: commands_mod.CommandSpec, host: Host, **kwargs: object) -> tuple[int, str, str]:
    """Wrapped CommandSpec.run with sudo support."""
    args = list(commands_mod.substitute_command_args(self.args, **kwargs))
    if self.optional_flags:
        for param_name, flag_args in self.optional_flags.items():
            if kwargs.get(param_name):
                args.extend(commands_mod.substitute_command_args(flag_args, **kwargs))

    args = list(_adjust_args_for_sudo(args, host))

    returncode, stdout, stderr = await commands_mod.execute_with_fallback(
        tuple(args), fallback=self.fallback, host=host
    )
    stdout = stdout if isinstance(stdout, str) else stdout.decode("utf-8", errors="replace")
    stderr = stderr if isinstance(stderr, str) else stderr.decode("utf-8", errors="replace")
    return returncode, stdout, stderr


async def custom_run_bytes(self: commands_mod.CommandSpec, host: Host, **kwargs: object) -> tuple[int, bytes, bytes]:
    """Wrapped CommandSpec.run_bytes with sudo support."""
    args = list(commands_mod.substitute_command_args(self.args, **kwargs))
    if self.optional_flags:
        for param_name, flag_args in self.optional_flags.items():
            if kwargs.get(param_name):
                args.extend(commands_mod.substitute_command_args(flag_args, **kwargs))

    args = list(_adjust_args_for_sudo(args, host))

    returncode, stdout, stderr = await commands_mod.execute_with_fallback(
        tuple(args), fallback=self.fallback, host=host, encoding=None
    )
    stdout = stdout if isinstance(stdout, bytes) else stdout.encode("utf-8")
    stderr = stderr if isinstance(stderr, bytes) else stderr.encode("utf-8")
    return returncode, stdout, stderr


def install_custom_command_runner() -> None:
    """Patch CommandSpec methods to support custom rules."""
    commands_mod.CommandSpec.run = custom_run
    commands_mod.CommandSpec.run_bytes = custom_run_bytes
