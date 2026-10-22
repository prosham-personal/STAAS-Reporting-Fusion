"""Matching logic of .claude/hooks/gh_account_guard.py (no gh, no network)."""
import importlib.util
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "gh_account_guard.py"
_spec = importlib.util.spec_from_file_location("gh_account_guard", _HOOK)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


@pytest.mark.parametrize("cmd", [
    "gh issue list",
    "  gh pr create --body-file b.md",
    "cd x && gh api user",
    "echo hi; gh repo view",
    "FOO=bar gh issue list",
    "env gh issue list",
    "env -i FOO=1 gh issue list",
    "command gh issue list",
    "sudo gh issue list",
    "sudo -u root gh issue list",
    "echo 1 | xargs gh issue view",
    "echo 1 | xargs -n 1 gh issue view",
    "bash -c 'gh issue list'",
    'sh -c "cd x && gh pr list"',
    "/opt/homebrew/bin/gh issue list",
    "gh auth status && gh issue list",
    "$(gh api user)",
])
def test_gh_calls_are_checked(cmd):
    assert guard.needs_account_check(cmd)


@pytest.mark.parametrize("cmd", [
    "gh auth status",
    "gh auth switch --hostname github.com --user prosham-personal",
    "env gh auth login",
    "sudo gh auth status",
    "bash -c 'gh auth status'",
    "GH_CONFIG_DIR=/x gh auth status",
])
def test_gh_auth_is_allowed(cmd):
    assert not guard.needs_account_check(cmd)


@pytest.mark.parametrize("cmd", [
    "",
    "git status",
    "ghost --help",
    "echo ghost",
    "command -v gh",
    "ls gh-notes",
    "uv run pytest -q tests",
])
def test_non_gh_commands_are_ignored(cmd):
    assert not guard.needs_account_check(cmd)
