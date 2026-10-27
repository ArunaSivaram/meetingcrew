# MeetingCrew

## What this is
A learning project: a Django app where I paste meeting notes, a CrewAI crew extracts action items, creates GitHub issues through the GitHub MCP server, and emails each owner. The goal is to learn CrewAI and MCP end-to-end, not to ship production software.

## Stack
- **Django** — web app, admin, DB (SQLite for now), templates/views for the paste-notes UI.
- **CrewAI** — orchestrates the agents that read notes and decide actions.
- **crewai-tools `MCPServerAdapter`** — bridges CrewAI tools to an MCP server.
- **GitHub MCP server** — exposes GitHub as MCP tools; run locally as the compiled Go binary (`github-mcp-server stdio`) over stdio. Docker is an alternative transport if we want it later; stdio with the local binary is the default here.
- **OpenAI** — the LLM backing the CrewAI agents (model configured via `OPENAI_MODEL_NAME`).

## How to work on this
- **Small steps.** One change per step. Build, run, verify, then move on.
- **Explain for a learner.** Every change should include a plain-language note: what the file does, why we edited it, and what the user should see when it works. Prefer intuition over jargon; link to Django/CrewAI/MCP docs if a concept is new.
- **Trace the data.** When wiring something up, say what flows where (e.g., "notes form → view → Crew → MCP tool call → GitHub issue").

## Secrets rules
- Secrets live in `.env` (gitignored). Current keys: `GITHUB_PERSONAL_ACCESS_TOKEN`, `GITHUB_MCP_BINARY`, `OPENAI_API_KEY`, `OPENAI_MODEL_NAME`.
- **Never print the value of a secret** in logs, terminal output, error messages, or commit messages. If you need to confirm one is set, print only a boolean / length / masked prefix (e.g., `sk-...` + last 4).
- **Never commit `.env`** or any file containing secrets. Verify `git status` before every commit.
- Secrets are loaded in `meetingcrew/settings.py` via `python-dotenv` from `BASE_DIR/.env`. Read them with `os.environ[...]` or `os.getenv(...)` elsewhere.

## Current state
- Step 1 done: Django project `meetingcrew` + app `meetings`, `.env` loaded in settings, initial migrations applied.
- Next: build the paste-notes form and view in `meetings/`.
