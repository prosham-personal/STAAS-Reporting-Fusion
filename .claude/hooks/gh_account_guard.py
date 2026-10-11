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

GH_CALL = re.compile(
    r"(?:^|[\n;&|(`]|\$\()\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*gh(?=\s|$)"
)
GH_AUTH = re.compile(
    r"(?:^|[\n;&|(`]|\$\()\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*gh\s+auth\b"
)


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
    if not GH_CALL.search(cmd) or GH_AUTH.search(cmd):
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
