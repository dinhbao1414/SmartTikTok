# Agent Init

For future development tasks, the main agent coordinates work and keeps scope clear.

- Subagents are mandatory for implementation and review when subagent tools are available.
- The main agent plans, assigns ownership, and avoids doing subagent-owned work locally.
- Each subagent must do its assigned work, then hand off a short report to the next subagent or main agent.
- Every handoff must include status, files changed, tests run, blockers, and next recommended action.
- The main agent must integrate handoffs, resolve conflicts, verify final state, and report a short final summary.
- If subagents are unavailable, or the task is too small or urgent for delegation, the main agent must state the fallback before proceeding.
