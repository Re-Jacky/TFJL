# Backend Services

Business logic layer. All services use static methods.

## Files

| File | Purpose |
|------|--------|
| `utility_services.py` | File I/O, script parsing, shortcuts, custom operations |
| `game_service.py` | Game automation (collab, ice castle, moon island) |
| `action_executer.py` | Execute parsed commands, level-specific operations |
| `image_services.py` | Template matching, OCR, level detection |
| `level_monitoring_service.py` | Real-time level monitoring, level transition detection |
| `custom_operations_service.py` | Custom operations management, configuration |
| `window_control_services.py` | Window positioning, locking |
| `shortcut_service.py` | Hotkey listeners |
| `event_services.py` | SSE broadcast to frontend |
| `script_parser.py` | DSL parser for script automation (see SCRIPT_AUTOMATION.md) |
| `script_validator.py` | Semantic validation for scripts |
| `script_simulator.py` | Dry-run simulation for testing scripts |
| `script_executor.py` | Real-time script execution with game window |
| `event_detector.py` | Image template matching for game events |
| `screenshot_service.py` | Screenshot capture, folder browsing, crop extraction |

## Pattern

```python
class ServiceName:
    @staticmethod
    def method_name(param: Type) -> ReturnType:
        try:
            # logic
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
```

## Dependencies

- Services import each other directly (no DI)
- Use `from app.utils.logger import logger`
- Use `from app.enums.X import Y` for positions/types

## Key Integrations

- `game_service` → `action_executer` → `image_services`
- `shortcut_service` → `window_control_services`
- `event_services` → All (for SSE logging)
- `script_parser` → `script_validator` → `script_executor` (see below)
- `screenshot_service` → `card_dataset_service` (crop extraction + labeling)

## Script Automation System

Detailed documentation: **[SCRIPT_AUTOMATION.md](./SCRIPT_AUTOMATION.md)**

```
Parser → Validator → Executor
                  ↓
              Simulator (dry-run)
```

- **Parser**: DSL text → Script model (handles Chinese punctuation)
- **Validator**: Semantic checks (deck, duplicates, events)
- **Simulator**: Test execution without game window
- **Executor**: Real execution with level monitoring

## Known TODOs

- `action_executer.py`: Implement same-row check logic
- `action_executer.py`: Integrate card deployment
- `script_executor.py`: Integrate with ActionExecuter for game interactions
- `event_detector.py`: Complete event template matching
