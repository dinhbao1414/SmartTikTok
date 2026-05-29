# Project Agent Notes

Follow `AGENT_INIT.md` for development task coordination and subagent handoffs.

Before changing browser automation code, read `docs/automation-rules.md`.

Automation in this project must use the local `remote_browser` stack and
`Controller/BrowserController.py` wrapper. Do not introduce alternate browser
driver frameworks or profile providers.
