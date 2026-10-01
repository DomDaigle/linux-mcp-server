"""Custom environment configuration."""

import os


def is_log_use_sudo_enabled() -> bool:
    """Check if remote log reading should use sudo -n."""
    val = os.getenv("LINUX_MCP_LOG_USE_SUDO", "").strip().lower()
    return val in {"1", "true", "yes", "on"}
