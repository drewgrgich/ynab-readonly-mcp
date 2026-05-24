# Publishing & Distribution

How to get this server in front of people. None of these are required to use it
locally — they're for sharing it. Do them in whatever order suits you.

Before anything: replace the `your-username` placeholders in `pyproject.toml`
(`[project.urls]`) and the README with your real GitHub handle, and double-check
nothing personal is committed (`git status`, and a quick scan for your token).

## 1. Publish to PyPI (so people can `uvx` / `pipx` install it)

Once on PyPI, anyone can run it with `uvx ynab-readonly-mcp` — no clone needed.

```bash
# Build the wheel + sdist
python -m pip install --upgrade build twine
python -m build

# Upload (you'll need a PyPI account + API token)
python -m twine upload dist/*
```

Bump the `version` in `pyproject.toml` and add a `CHANGELOG.md` entry for each release.

## 2. List on the GitHub MCP Registry

The [MCP Registry](https://github.com/mcp) is the most universal discovery point
for MCP servers. Submission is via a `server.json` describing the server and how
to run it. See the registry's contribution guide for the current schema and
submission flow (it evolves, so follow the live docs rather than hard-coding a
format here). The key fields you'll provide: name, description, the run command
(`uvx ynab-readonly-mcp` once on PyPI), and the required `YNAB_API_TOKEN` env var.

## 3. List on Smithery

[Smithery](https://smithery.ai/) is a popular MCP catalog with one-command
installs. Add a `smithery.yaml` describing the start command and required config
(your `YNAB_API_TOKEN`), then submit the repo at smithery.ai. Their docs cover
the current `smithery.yaml` format.

## 4. Tell people what makes it different

Wherever you list it, lead with the angle: a **read-only** YNAB server — safe to
point an AI at a real budget because it cannot create, edit, or delete anything,
and the guarantee is enforced by a test. That's the one-line reason someone picks
this over a more full-featured server.
