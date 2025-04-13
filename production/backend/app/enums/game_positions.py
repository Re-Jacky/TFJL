from enum import Enum

## 游戏坐标 (x, y)
class GamePositions(Enum):
    COLLAB = (650, 570)  # 合作模式
    STORE = (70, 235)    # 商店
    TASK = (70, 320)   # 任务
    EVENT = (70, 405)   # 活动
    BACK = (55, 70)   # 返回
    ### BATTLE
    BATTLE = (910, 560)  # 对战模式
    BATTLE_START = (700, 510)   # 开始战斗
    SURRENDER = (50, 165)   # 投降
    BATTLE_END_CONFIRM = (520, 535)   # 战斗结束确认
    UPGRADE_VEHICLE = (320, 570)   # 升级车辆
    REFRESH_CARD = (720, 570)   # 刷新卡片
    ENEMY_STATUS = (920, 130)   # 敌人状态
    
    CARD_0 = (440, 560)   # 卡片0
    CARD_1 = (525, 560)   # 卡片1
    CARD_2 = (610, 560)   # 卡片2
    
