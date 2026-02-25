# TFJL Project Knowledge Base

**Generated:** 2026-02-24 | **Commit:** f208c7f | **Branch:** main

## Overview

Desktop automation app for a tower defense game. Python FastAPI backend (runs as local exe), React/TypeScript UI, Electron wrapper.

## Structure

```
production/
├── backend/           # FastAPI server → PyInstaller exe
│   ├── app/services/  # Business logic (see local AGENTS.md)
│   ├── app/enums/     # Game positions, commands, shortcuts
│   ├── app/tests/     # unittest (run from backend/)
│   └── main.py        # All routes in single file
├── frontend/          # React + Vite + Redux + Ant Design
│   └── src/components/content/  # Feature modules (see local AGENTS.md)
├── electron/          # Spawns Python exe, manages window
└── build.sh           # Full build: backend exe → frontend → Electron package
```

## Commands

| Task | Command | Working Dir |
|------|---------|-------------|
| Backend dev | `python -m uvicorn main:app --reload` | production/backend/ |
| Frontend dev | `npm run dev` | production/frontend/ |
| Electron dev | `npm run electron:dev` | production/electron/ |
| Lint | `npm run lint` | production/frontend/ |
| Format | `npm run format` | production/frontend/ |
| Build all | `./build.sh` | production/ |
| Single test | `python -m unittest app.tests.test_command_parser` | production/backend/ |
| Specific test | `python -m unittest app.tests.test_command_parser.TestCommandParser.test_case_1` | production/backend/ |

## Where to Look

| Task | Location | Notes |
|------|----------|-------|
| Add API endpoint | `production/backend/main.py` | All routes in single file |
| Add service logic | `production/backend/app/services/` | Static method classes |
| Add UI feature | `production/frontend/src/components/content/` | Each feature = subdir |
| Add Redux state | `production/frontend/src/store/slices/` | Uses @reduxjs/toolkit |
| Add types | `production/frontend/src/types/` | Exports via index.ts |
| Modify window behavior | `production/electron/src/main.js` | Spawns Python exe |

## Conventions

### TypeScript (Frontend)

- **Imports**: External → `@src/...` alias → relative
- **Quotes**: Single (including JSX)
- **Semicolons**: Required
- **Components**: PascalCase files, `React.FC` type
- **Path alias**: `@src/*` → `./src/*`

### Python (Backend)

- **Imports**: stdlib → third-party → local (`app.services`, `app.utils`)
- **Services**: Classes with `@staticmethod` methods
- **Errors**: Catch `HTTPException` separately, log then raise
- **Types**: Use hints for params and returns

## Anti-Patterns (This Project)

- **NO** tests in frontend/electron yet
- **NO** CI/CD configured - manual `./build.sh` only
- **NO** dependency injection - services instantiated at module level
- **AVOID** adding routes outside `main.py` - all routes centralized
- **AVOID** `any` type - strict mode enabled

## Known TODOs

- `action_executer.py`: Implement same-row check logic
- `action_executer.py`: Integrate card deployment with GameService
- `test_command_parser.py`: Fix card list parsing ('火灵蛇女' → ['火灵', '蛇女'])

## Build Notes

- Backend builds to single exe via PyInstaller (`build_server.py`)
- Electron spawns `tfjl_server.exe` on startup (prod mode)
- No hot reload between frontend/backend - restart manually
- CORS is permissive (`*`) for local dev

## Gotchas

- **venv**: Always activate before backend work
- **Port**: Backend runs on 8000, check for conflicts
- **Chinese paths**: Files in `public/合作脚本/` and `public/活动脚本/`
- **Windows-specific**: Uses `pywin32`, `pygetwindow` - won't work on Linux
