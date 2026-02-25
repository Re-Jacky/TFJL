# Script Automation System

**Created:** 2026-02-25 | **Status:** Active Development

## Overview

A DSL-based script automation system that allows users to define game actions in text files and have them executed automatically based on game level transitions and events.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                    │
│  ScriptEditorContent.tsx                                                │
│  ├── File management (list, create, save, delete)                       │
│  ├── CodeEditor (script editing)                                        │
│  ├── Validate button → /script/validate                                 │
│  ├── Test button → /script/test (dry-run simulation)                    │
│  └── Execution controls (Start/Pause/Resume/Stop) → /script/execute     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API Endpoints                                  │
│  main.py (lines 424-619)                                                │
│  ├── POST /script/parse     → ScriptParserService                       │
│  ├── POST /script/validate  → ScriptValidatorService                    │
│  ├── POST /script/test      → ScriptSimulatorService (dry-run)          │
│  ├── POST /script/execute   → ScriptExecutorService (real execution)    │
│  ├── GET  /script/status/{pid}                                          │
│  └── GET  /script/list/{type}                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Service Layer                                  │
│                                                                          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │ ScriptParser    │    │ ScriptValidator │    │ ScriptSimulator │     │
│  │ Service         │───▶│ Service         │    │ Service         │     │
│  │                 │    │                 │    │ (dry-run)       │     │
│  │ DSL → Models    │    │ Semantic checks │    │ Action logging  │     │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘     │
│           │                                                              │
│           ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ScriptExecutorService                                            │   │
│  │ ├── Per-window instance (singleton per PID)                      │   │
│  │ ├── Threaded execution loop                                      │   │
│  │ ├── Level monitoring via OCR (ImageService)                      │   │
│  │ ├── State machine: idle → running → paused → stopped             │   │
│  │ └── Delegates to ActionExecuter for actual game interactions     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Data Models                                    │
│  app/models/script_models.py                                            │
│                                                                          │
│  Script                                                                  │
│  ├── metadata: ScriptMetadata (name, type, version)                     │
│  ├── setup: ScriptSetup (deck, skins, enhanced, vehicles)               │
│  └── commands: ScriptCommands                                           │
│       ├── level_commands: List[LevelCommand]                            │
│       │    └── level: int, actions: List[Action]                        │
│       └── event_commands: List[EventCommand]                            │
│            └── event: str, actions: List[Action], card_filter, etc.     │
│                                                                          │
│  Action Types (Union):                                                   │
│  ├── DeployAction      (上{card}{level?})                               │
│  ├── RemoveAction      (下{card})                                       │
│  ├── PrepareAction     (预备手牌{card})                                  │
│  ├── SwitchEquipmentAction (换{equipment})                              │
│  ├── WaitUntilAction   (时钟秒{n})                                      │
│  ├── RepeatAction      (每{n}秒共{m}次{card})                           │
│  ├── DelayAction       (延时{n}毫秒)                                    │
│  ├── StopBallAction    (停球)                                           │
│  ├── CloseVerifyAction (关闭验光)                                       │
│  ├── SameRowAction     ({card1}{card2}同排)                             │
│  ├── CancelSameRowAction (同排取消)                                     │
│  ├── ForceOrderAction  (强制顺序上卡)                                   │
│  ├── VerifyDeployAction (验卡补星)                                      │
│  ├── DiscardPlayAction (弃牌出牌{card})                                 │
│  └── RawAction         (unrecognized, stored as-is)                     │
└─────────────────────────────────────────────────────────────────────────┘
```

## DSL Specification

### File Format

Scripts are plain text files with Chinese commands. Located in:
- `public/合作脚本/` - Collaboration scripts (`collab` type)
- `public/活动脚本/` - Activity scripts (`activity` type)

### Header Section

```
上阵：电法，酋长，死神，海妖，冰骑，萌萌，风灵，潜艇，光精灵，冰精灵，
皮肤：
魔化：死神，海妖，冰骑，
主战车：未设置
副战车：未设置
```

| Header | Pattern | Purpose |
|--------|---------|---------|
| 上阵 | `上阵[：:]{cards}` | Deck composition (required) |
| 皮肤 | `皮肤[：:]{cards}` | Card skins (optional) |
| 魔化 | `魔化[：:]{cards}` | Enhanced cards (optional) |
| 主战车 | `主战车[：:]{name}` | Main vehicle (optional) |
| 副战车 | `副战车[：:]{name}` | Sub vehicle (optional) |

### Level Commands

Format: `{level},{action1},{action2},...`

```
1,强制顺序上卡,上电法满,上酋长满,上风灵满,
50,下海妖,上冰骑满,
69,时钟秒20,下萌萌,下风灵,时钟秒27,上风灵满,上萌萌满,
```

- Level is an integer (1-999)
- Actions are comma-separated
- Chinese punctuation (，) auto-normalized to ASCII (,)

### Event Commands

Format: `{event_name},{action1},{action2},...`

```
寒冰雷神红球,上火灵
暗月地精不吃,5,8,9,10,J,Q,K
暗月财阀完成,牌点总数50点
```

- Event names must match known events (see `script_commands.py`)
- Card filters: single card values like `A,2,3,J,Q,K`
- Point totals: `牌点总数{n}点`

### Action Patterns

| Action | Pattern | Example | Description |
|--------|---------|---------|-------------|
| Deploy | `上{card}{level?}` | `上火灵满`, `上蛇女3级` | Deploy card to field |
| Remove | `下{card}` | `下萌萌` | Remove card from field |
| Prepare | `预备手牌{card}` | `预备手牌火灵` | Prepare card in hand |
| Switch Equipment | `换{equipment}` | `换龙心` | Switch equipment |
| Wait Until | `时钟秒{n}` | `时钟秒20` | Wait until clock second |
| Repeat | `每{n}秒共{m}次{card}` | `每1秒共3次魔精灵` | Repeat action |
| Delay | `延时{n}毫秒` | `延时500毫秒` | Delay execution |
| Stop Ball | `停球` | `停球` | Stop ball |
| Close Verify | `关闭验光` | `关闭验光` | Close verification panel |
| Same Row | `{card1}{card2}同排` | `火灵蛇女同排` | Deploy cards same row |
| Cancel Same Row | `同排取消` | `同排取消` | Cancel same row mode |
| Force Order | `强制顺序上卡` | `强制顺序上卡` | Force deploy order |
| Verify Deploy | `验卡补星{仅满级?}{n次?}` | `验卡补星仅满级3次` | Verify and deploy |
| Discard Play | `弃牌出牌{card}` | `弃牌出牌火灵` | Discard and play |
| After Previous | `过后` | `过后` | Chain to previous action |

### Card Level Specifiers

| Specifier | Meaning |
|-----------|---------|
| `满` | Max level |
| `不满` | Not max level |
| `1级`-`9级` | Specific level |
| (none) | Any level |

## Service Details

### ScriptParserService (`script_parser.py`)

**Purpose:** Parse raw DSL text into structured `Script` model.

**Key Methods:**
```python
@staticmethod
def parse_script(content: str, name: str, script_type: str) -> Tuple[Script, List[str], List[str]]
    # Returns: (Script or None, errors, warnings)

@staticmethod
def normalize_text(text: str) -> str
    # Converts Chinese punctuation to ASCII

@staticmethod
def serialize_script(script: Script) -> str
    # Convert Script back to DSL format
```

**Punctuation Normalization:**
```python
PUNCTUATION_MAP = {
    '，': ',',  # Chinese comma
    '：': ':',  # Chinese colon
    '；': ';',  # Chinese semicolon
    '。': '.',  # Chinese period
    '（': '(',  # Chinese left paren
    '）': ')',  # Chinese right paren
    '　': ' ',  # Full-width space
}
```

**Parse Flow:**
1. Normalize entire content (Chinese → ASCII punctuation)
2. Parse header section (deck, skins, enhanced, vehicles)
3. Parse remaining lines as level commands or event commands
4. Sort level commands by level number
5. Return Script object with errors/warnings

### ScriptValidatorService (`script_validator.py`)

**Purpose:** Semantic validation of parsed scripts.

**Validations:**
- Deck configuration exists
- No duplicate level definitions
- Cards used in actions are in deck
- Events are recognized (with fuzzy matching suggestions)

**Key Method:**
```python
@staticmethod
def validate(script: Script) -> ValidationResult
    # Returns: ValidationResult(is_valid, errors, warnings)
```

### ScriptSimulatorService (`script_simulator.py`)

**Purpose:** Dry-run simulation without game window. Used by "Test" button.

**Key Method:**
```python
@staticmethod
def simulate_script(content: str, name: str, script_type: str) -> Dict[str, Any]
    # Returns: {success, action_log, errors, warnings, summary}
```

**Action Log Entry:**
```python
{
    "level": 69,
    "second": 20.0,
    "action_type": "DEPLOY",
    "description": "Deploy card: 风灵 (level: 满)",
    "details": {"card": "风灵", "card_level": "满"}
}
```

**Summary:**
```python
{
    "script_name": "test.txt",
    "script_type": "collab",
    "total_actions": 23,
    "levels_covered": [1, 50, 69],
    "level_count": 3,
    "event_count": 0,
    "action_type_counts": {"DEPLOY": 12, "REMOVE": 5, ...},
    "cards_used": ["火灵", "蛇女", ...],
    "deck": ["电法", "酋长", ...]
}
```

### ScriptExecutorService (`script_executor.py`)

**Purpose:** Real-time script execution with game window.

**Singleton Pattern:**
```python
# One instance per window PID
executor = ScriptExecutorService.get_instance(window_pid)
```

**State Machine:**
```
idle → running → paused → running → stopped
         ↓                    ↓
       error              stopped
```

**Execution Loop (threaded):**
1. Monitor current game level via OCR (`ImageService.get_level()`)
2. On level change, find matching `LevelCommand`
3. Execute actions in sequence, respecting `WaitUntilAction` timing
4. Handle events via `EventDetectorService` (future)
5. Update status accessible via `/script/status/{pid}`

**Key Methods:**
```python
def load_script(self, script: Script) -> None
def start(self) -> None
def pause(self) -> None
def resume(self) -> None
def stop(self) -> None
def get_status(self) -> ScriptExecutionStatus
```

**Status Model:**
```python
class ScriptExecutionStatus:
    state: ExecutionState  # 'idle', 'running', 'paused', 'stopped', 'error'
    script_name: Optional[str]
    current_level: int
    current_second: float
    actions_executed: int
    error_message: Optional[str]
```

## API Endpoints

### POST /script/parse

Parse script content into structured model.

**Request:**
```json
{
    "content": "上阵：火灵，蛇女，\n1,上火灵满,",
    "name": "test.txt",
    "script_type": "collab"
}
```

**Response:**
```json
{
    "success": true,
    "script": { /* Script model */ },
    "errors": [],
    "warnings": []
}
```

### POST /script/validate

Validate script for semantic correctness.

**Request:**
```json
{
    "content": "..."
}
```

**Response:**
```json
{
    "valid": true,
    "errors": [],
    "warnings": ["Card 'X' used but not in deck"]
}
```

### POST /script/test

Dry-run simulation (no game window required).

**Request:**
```json
{
    "content": "...",
    "name": "test.txt",
    "script_type": "collab"
}
```

**Response:**
```json
{
    "success": true,
    "action_log": [
        {"level": 1, "second": null, "action_type": "DEPLOY", "description": "...", "details": {...}}
    ],
    "errors": [],
    "warnings": [],
    "summary": {
        "total_actions": 23,
        "level_count": 3,
        "cards_used": [...]
    }
}
```

### POST /script/execute

Control script execution (requires active game window).

**Request:**
```json
{
    "script_name": "test.txt",
    "script_type": "collab",
    "window_pid": 12345,
    "action": "start"  // start | pause | resume | stop
}
```

**Response:**
```json
{
    "success": true,
    "message": "Script started",
    "status": {
        "state": "running",
        "script_name": "test.txt",
        "current_level": 1,
        "current_second": 0.0,
        "actions_executed": 0
    }
}
```

### GET /script/status/{window_pid}

Get current execution status.

**Response:**
```json
{
    "success": true,
    "status": {
        "state": "running",
        "script_name": "test.txt",
        "current_level": 50,
        "current_second": 23.5,
        "actions_executed": 15,
        "error_message": null
    }
}
```

## Frontend Integration

### Types (`frontend/src/types/script.ts`)

```typescript
interface TestScriptResponse {
    success: boolean;
    action_log: SimulatedActionLog[];
    errors: string[];
    warnings: string[];
    summary: TestScriptSummary | null;
}

interface SimulatedActionLog {
    level: number;
    second: number | null;
    action_type: string;
    description: string;
    details: Record<string, unknown>;
}

interface TestScriptSummary {
    script_name: string;
    script_type: string;
    total_actions: number;
    levels_covered: number[];
    level_count: number;
    event_count: number;
    action_type_counts: Record<string, number>;
    cards_used: string[];
    deck: string[];
}
```

### API Methods (`frontend/src/services/api.ts`)

```typescript
parseScript(content: string, name: string, scriptType: string): Promise<ParseScriptResponse>
validateScript(content: string): Promise<ValidateScriptResponse>
testScript(content: string, name: string, scriptType: string): Promise<TestScriptResponse>
executeScript(request: ScriptExecutionRequest): Promise<ScriptExecutionResponse>
getScriptStatus(windowPid: number): Promise<{success: boolean, status: ScriptExecutionStatus}>
```

### UI Component (`ScriptEditorContent.tsx`)

- **Validate button**: Calls `/script/parse` + `/script/validate`, shows modal with results
- **Test button**: Calls `/script/test`, shows action log table in modal
- **Start/Pause/Resume/Stop**: Calls `/script/execute` with respective action
- **Status display**: Polls `/script/status/{pid}` every 1s when active

## File Locations

| Component | Path |
|-----------|------|
| API Endpoints | `production/backend/main.py` (lines 424-619) |
| Data Models | `production/backend/app/models/script_models.py` |
| Parser Service | `production/backend/app/services/script_parser.py` |
| Validator Service | `production/backend/app/services/script_validator.py` |
| Simulator Service | `production/backend/app/services/script_simulator.py` |
| Executor Service | `production/backend/app/services/script_executor.py` |
| Event Detector | `production/backend/app/services/event_detector.py` |
| Command Enums | `production/backend/app/enums/script_commands.py` |
| Frontend Types | `production/frontend/src/types/script.ts` |
| Frontend API | `production/frontend/src/services/api.ts` |
| Frontend UI | `production/frontend/src/components/content/script-editor/ScriptEditorContent.tsx` |
| Sample Scripts | `production/public/sample/*.txt` |

## Known TODOs

- [ ] `script_executor.py`: Integrate with `ActionExecuter` for actual game interactions
- [ ] `script_executor.py`: Implement event detection loop using `EventDetectorService`
- [ ] `script_executor.py`: Handle `WaitUntilAction` with real clock synchronization
- [ ] `event_detector.py`: Complete event template matching implementation
- [ ] Add more known events to `script_commands.py` as discovered
- [ ] Frontend: Add visual progress indicator during execution
- [ ] Frontend: Add script diff/history feature

## Testing

### Manual Testing

```bash
# Test parser directly
cd production/backend
python3 << 'EOF'
from app.services.script_parser import ScriptParserService

content = """上阵：火灵，蛇女，
1,上火灵满,上蛇女满,
"""

script, errors, warnings = ScriptParserService.parse_script(content, "test")
print(f"Levels: {[cmd.level for cmd in script.commands.level_commands]}")
print(f"Actions: {len(script.commands.level_commands[0].actions)}")
EOF
```

### Unit Tests

```bash
cd production/backend
python -m unittest app.tests.test_script_parser  # (when created)
```

## Design Decisions

1. **Static Methods**: All services use `@staticmethod` to match existing codebase pattern
2. **Chinese Punctuation**: Auto-normalized at parse time for user convenience
3. **Singleton Executor**: One executor per window PID to prevent conflicts
4. **Threaded Execution**: Non-blocking execution with state machine for control
5. **Dry-run Simulation**: Test button allows validation without game window
6. **Action Chaining**: `过后` marker chains actions to execute after previous completes
