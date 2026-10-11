# STAAS-Reporting-Fusion — Claude Code project context

Operating rules for Claude Code sessions in this repository. Portable: true for
any engineer, machine or account. Workstation specifics go in the gitignored
`.claude/CLAUDE.local.md` and `.claude/settings.local.json`; never here.

## What this repo is

Python tooling that reports on and tags STaaS (storage) volumes: `staas-reporting.py`,
`staas-tag_vols.py` and shared code in `staas_common.py`. See `README.md`. Owned by
Paul's personal GitHub account (`prosham-personal`).

## Isolation (mirrors the other repos under ~/Src)

- **Identity:** repo-local git config pins `Paul Rosham <paul@rosham.com>`. Claude
  sessions sign with `~/.ssh/claude_prosham_signing`, selected by `GIT_CONFIG_*`
  in the gitignored `.claude/settings.local.json`. Never use opexit or LBC identities.
- **Transport:** `origin` is `git@github-personal:prosham-personal/STAAS-Reporting-Fusion.git`
  via the `github-personal` SSH alias and the 1Password agent. Do not add a plain
  `github.com` remote or an HTTPS remote, and do not set `IdentitiesOnly`.
- **GitHub CLI:** `.claude/hooks/gh_account_guard.py` blocks `gh` unless the active
  account is `prosham-personal`; `settings.local.json` points `GH_CONFIG_DIR` at
  `~/.config/gh-prosham`. `GH_TOKEN`/`GITHUB_TOKEN` must not be set.
- **Secrets:** none belong in this repo. STAAS API credentials and the real config
  workbook live in the gitignored `config/` directory or the 1Password vault, never
  in tracked files. Only `STAAS_Config_example.xlsx` (placeholders) is committed. Never
  write a value to a file, commit, chat, log or screenshot. `.gitleaks.toml` backs this up.

## Workflow guardrails (mandatory)

- **Log every session to a GitHub issue** before work starts (title
  `Session <yyyymmdd>-<hex>: <title>`); post the plan, non-obvious decisions and a
  closing summary as comments from a file (`--body-file`), never inline, never with secrets.
- **One session = one branch + one worktree.** Never commit directly to `main`
  (except a single-file near-zero-collision fix). Worktrees live under
  `~/Src/STAAS-Reporting-Fusion-wt/`. Reference the issue in the branch and PR (`Closes #NN`).
- **No heredocs** in shell commands except to create a file in the session scratchpad.
  Commit messages use `git commit -F <file>`; PR/issue bodies use `--body-file`.
- **CI and review:** merge to `main` by pull request with CI green, `--no-ff`. Every PR
  gets `/code-review`; changes touching credentials or auth also get `/security-review`.
- Outward-facing changes (pushes to shared infrastructure, running tagging against real
  volumes) are shown first and applied only after Paul agrees; log them on the issue.

## Standards

- Python 3.12 managed with `uv`: dependencies in `pyproject.toml`, locked in the committed `uv.lock`, installed to the gitignored `.venv` by `uv sync`. Run scripts with `uv run`; tests with `uv run pytest -q tests`. Do not add `requirements.txt`.
- API tests: `tests/test_api_contract.py` checks every `client.*` call against the published FlashArray spec (PureStorage-OpenConnect/swagger, `STAAS_API_VERSION`, default 2.42) and the installed SDK; no array needed. `tests/test_live_array.py` is read-only smoke tests against a lab array, skipped unless `PURE_FUSION_SERVER`, `PURE_USER_NAME` and `PURE_API_TOKEN` are set; run with `uv run pytest -m live`. Never point live tests at production or add write calls to them.
- Commits: `scope: imperative summary` with bullets; scopes `reporting`, `tagging`,
  `common`, `ci`, `docs`. Signing follows the workstation; never disable it.

## Portability contract

| Context | Home |
| --- | --- |
| Repo operating rules | this file, committed |
| Workstation specifics | `.claude/CLAUDE.local.md`, `.claude/settings.local.json`, gitignored |
