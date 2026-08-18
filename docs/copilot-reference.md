# Copilot Skills, Agents & Rules Reference

> Extracted from VS Code Copilot Chat configuration.
> **Keep this file updated** when skills, agents, or rules change.

---

## Agents

| Agent | Description |
|-------|-------------|
| **Explore** | Fast read-only codebase exploration and Q&A subagent. Use for searching code, reading files, understanding structure. Safe to call in parallel. Specify thoroughness: `quick`, `medium`, or `thorough`. |

---

## Skills

Skills are domain-specific knowledge modules that enhance agent capabilities.

### Code Quality & Analysis

| Skill | Description | Trigger |
|-------|-------------|---------|
| **python-fact-grounded-coding** | Python coding/debugging grounded in verified Pylance facts, runtime values, diagnostics, tests, or debugger evidence before changing code. | Python coding, debugging, explanation, bug-fix tasks |
| **pylance-docs** | Official Pylance documentation for settings, diagnostics, configuration, troubleshooting, feature behavior. | Questions about Pylance docs |
| **pylance-refactoring** | Automated Python refactorings: unused-import cleanup, wildcard-import conversion, inferred type annotations, Pylance fix-all. | Named automated Python refactorings |
| **pylance-python-profiling** | Profile Python code with Pylance: CPU time (Tachyon), call tracing (sys.monitoring), memory (Memray). Requires Python 3.15+. | Python profiling requests |

### Project Setup

| Skill | Description | Trigger |
|-------|-------------|---------|
| **project-setup-info-local** | Full project initialization and scaffolding (TypeScript, React, Node.js, Next.js, Vite, MCP servers, VS Code extensions). NOT for single files or simple code. | "new project", "create a workspace", "set up a [framework] project" |

### Agent Customization

| Skill | Description | Trigger |
|-------|-------------|---------|
| **agent-customization** | Create, update, review, fix, or debug VS Code agent customization files (`.instructions.md`, `.prompt.md`, `.agent.md`, `SKILL.md`, `copilot-instructions.md`, `AGENTS.md`). | Saving coding preferences, troubleshooting instructions/skills, configuring applyTo patterns, defining tool restrictions, creating custom agent modes |
| **find-skills** | Discover and install agent skills when users ask "how do I do X", "find a skill for X", "is there a skill that can...". | Looking for new functionality |

### Session & History

| Skill | Description | Trigger |
|-------|-------------|---------|
| **chronicle** | Analyze Copilot session history for standup reports, usage tips, session search, and reindexing. | Standup, daily summary, usage tips, workflow recommendations, session search |
| **get-search-view-results** | Get the current search results from the Search view in VS Code. | Need to access VS Code search results |

---

## MCP Tool Servers

Model Context Protocol tools available for specialized tasks.

| Toolset | Capabilities |
|---------|-------------|
| **FreeCAD** | 3D CAD: create documents, objects, execute code, run FEM analysis |
| **KiCAD** | PCB design: schematics, board layout, footprints, 3D models, copper pours |
| **Sketchfab** | Search/download 3D models, get model details, list categories/licenses |
| **Thingiverse** | Search/inspect/download 3D printable models via REST API |
| **Printables** | Search/download 3D printable models and files |
| **MakerWorld** | Download profiles, get designs, parse URLs from MakerWorld |
| **SnapEDA** | Search/download electronic component symbols and footprints |
| **Pylance MCP** | Code analysis: trace values, type inference, flow graphs, syntax errors, refactoring, debugging, profiling |

---

## Project Rules (AGENTS.md)

### Source of Truth Priority
1. `docs/requirements.md` — product contract (`FR-*`, `NFR-*`)
2. `docs/architecture.md` — modules and threading
3. `docs/plan.md` — phased implementation (don't skip phases)
4. `docs/openocd-integration.md` — OpenOCD CLI behavior
5. `docs/dual-flash-strategy.md` — parallel HLA vs sequential clone
6. `docs/stlink-clone-serial.md` — clone USB serial conflicts
7. `CHANGELOG.md` — update under **Unreleased** for user-visible changes

**Rule**: If chat disagrees with docs → **update docs first**, then code.

### Stack (don't change casually)
- **Python 3.11+**, package `batch_stlink_flasher` under `src/`
- **UI**: PySide6
- **Backend**: OpenOCD subprocesses (one per adapter)

### Implementation Rules
- Keep UI thread free of blocking OpenOCD/USB work
- One OpenOCD process per selected adapter; unique TCP ports; always bind serial
- Prefer small, testable modules (`openocd.py` command builder must be unit-tested)
- Don't commit secrets, firmware binaries, or machine-specific paths
- Don't expand scope beyond current `docs/plan.md` phase unless asked

### Commands
```bash
pip install -e ".[dev]"   # Install deps
pytest                     # Run tests
python -m batch_stlink_flasher  # Launch app
```

Coverage must stay ≥ **85%** (`--cov-fail-under=85`). Build deps: `scripts/install_build_deps.ps1`. Packaging steps: `scripts/README.md`.

Release tags use `vMAJOR.MINOR.PATCH` (e.g. `v0.1.0`); see `scripts/create_release_tag.ps1` and `.github/workflows/release.yml`.

### When Stuck
Document the blocker in PR/commit message and **Unreleased** notes. Prefer fixing with a real probe before guessing UI workarounds.

---

## Memory Scopes

| Scope | Path | Purpose |
|-------|------|---------|
| **User** | `/memories/` | Persistent notes across all workspaces. Preferences, patterns, frequently used commands. First 200 lines auto-loaded. |
| **Session** | `/memories/session/` | Current conversation only. Task-specific context, in-progress notes. |
| **Repository** | `/memories/repo/` | Workspace-scoped. Codebase conventions, build commands, project structure. |

---

## Documentation Map

| File | Purpose |
|------|---------|
| `AGENTS.md` | AI agent working rules |
| `docs/requirements.md` | Product contract (FR-*, NFR-*) |
| `docs/architecture.md` | Modules, threading, data flow |
| `docs/plan.md` | Phased implementation checklist |
| `docs/openocd-integration.md` | OpenOCD CLI recipes, ports, serial |
| `docs/dual-flash-strategy.md` | HLA parallel vs clone sequential |
| `docs/stlink-clone-serial.md` | Clone USB serial conflicts |
| `docs/packaging.md` | PyInstaller, installer, CI |
| `CHANGELOG.md` | User-visible change history |
| `README.md` | Install, run, operator quick start |
| **`docs/copilot-reference.md`** | **This file — skills, agents, rules** |
