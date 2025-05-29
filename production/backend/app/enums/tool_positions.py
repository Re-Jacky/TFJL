from enum import Enum

## 游戏坐标 (x, y)
class ToolPositions(Enum):
    # 老马
    GAME_START = (700, 270)  # 游戏开始
    GAME_PAUSE = (740, 90)  # 游戏暂停
    GAME_STOP = (740, 155)  # 游戏停止
    GAME_CONTINUE = (768, 270)  # 游戏继续