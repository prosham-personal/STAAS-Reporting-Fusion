#!/usr/bin/env python3
"""GitHub account guard (PreToolUse hook) for STAAS-Reporting-Fusion.

Blocks `gh` invocations from this repository when the GitHub CLI's ACTIVE
account is not `prosham-personal`. `gh` holds exactly one active account per
machine with no per-repository binding, and this workstation also carries the
opexit, LBC and infraglobal accounts. Every session files or comments on an
issue, so the wrong active account would leak this repo's work into another
account, or fail as a misleading "Could not resolve to a Repository".

The check is an ALLOWLIST: it asserts the expected account and never names
another organisation's. `gh auth ...` is never blocked, since it is how the
account gets fixed. Fails OPEN on any error: never brick a session over a guard.

Reads the hook JSON on stdin; emits a PreToolUse "deny" JSON to block.
"""
import json
import os
import re
import sys

EXPECTED = "prosham-personal"

# A command position: start of line, after a separator/subshell opener, or just
# inside a quote (so `bash -c 'gh ...'` and `sh -c "... ; gh ..."` are seen).
_BOUNDARY = r"(?:^|[\n;&|(`'\"]|\$\()\s*"
_ASSIGN = r"[A-Za-z_][A-Za-z0-9_]*=\S*\s+"
# Launchers that run the next word as a command: env, command, sudo, xargs, ...
# Their options are skipped; an option may take one argument (sudo -u root, xargs -n 1).
# `command -v gh` only looks the binary up, so -v/-V is not skipped for it.
_WRAPPER = (
    r"(?:(?:env|command|sudo|xargs|exec|nohup|time)\b"
    r"(?:\s+(?!-[vV]\b)-\S+(?:\s+(?!gh\b)[^\s\-;&|'\"]\S*)?|\s+" + _ASSIGN.strip() + r")*\s+)"
)
_GH_PATH = r"(?:[^\s;&|'\"()]*/)?gh"
GH_CALL = re.compile(
    _BOUNDARY + r"(?:" + _ASSIGN + r"|" + _WRAPPER + r")*" + _GH_PATH + r"(?=\s|$|['\"])(?P<rest>[^\n;&|]*)"
)
GH_AUTH_REST = re.compile(r"^\s*auth\b")


def needs_account_check(cmd):
    """True if `cmd` runs `gh` for anything other than `gh auth ...`.

    Every gh invocation is inspected, so `gh auth status && gh issue list`
    is still checked. `gh auth ...` stays allowed: it is how the account is fixed.
    """
    return any(not GH_AUTH_REST.match(m.group("rest")) for m in GH_CALL.finditer(cmd))


def hosts_yml():
    """The hosts.yml `gh` will read: GH_CONFIG_DIR > $XDG_CONFIG_HOME/gh > ~/.config/gh."""
    d = os.environ.get("GH_CONFIG_DIR")
    if not d:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        d = os.path.join(xdg, "gh") if xdg else "~/.config/gh"
    return os.path.join(os.path.expanduser(d), "hosts.yml")


def active_account():
    """gh's active account: the `user:` key directly under the github.com host."""
    with open(hosts_yml()) as f:
        lines = f.read().splitlines()
    in_host = False
    for line in lines:
        if re.match(r"^\S", line):
            in_host = line.startswith("github.com:")
            continue
        if not in_host:
            continue
        m = re.match(r"^ {1,4}user:\s*(\S+)\s*$", line)
        if m:
            return m.group(1)
    return None


def deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def main():
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not needs_account_check(cmd):
        return

    if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
        deny(
            "GH_TOKEN/GITHUB_TOKEN is set, which overrides gh's stored account, "
            "so this guard cannot tell which identity `gh` will act as. Unset it "
            "and use `gh auth switch --hostname github.com --user %s`." % EXPECTED
        )
        return

    active = active_account()
    if active is None or active == EXPECTED:
        return

    deny(
        "gh's ACTIVE GitHub account is '%s' (per %s), not '%s'. Run:\n"
        "    gh auth switch --hostname github.com --user %s\n"
        "then retry. Verify with `gh api user --jq .login`."
        % (active, hosts_yml(), EXPECTED, EXPECTED)
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
