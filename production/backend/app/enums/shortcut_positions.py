from enum import Enum
from app.enums.game_positions import GamePositions

class GameMode(Enum):
    SINGLE_PLAYER = 0
    SINGLE_PLAYER_SAILING = 1
    TWO_PLAYER = 2
    TWO_PLAYER_SKY = 3

## 游戏坐标 (x, y)
class SingleModeVehiclePositions(Enum):
    VEHICLE_0 = (97, 440)   # 单模式车辆0
    VEHICLE_1 = (54, 440)   # 单模式车辆1
    VEHICLE_2 = (97, 365)   # 单模式车辆2
    VEHICLE_3 = (54, 365)   # 单模式车辆3
    VEHICLE_4 = (97, 296)   # 单模式车辆4
    VEHICLE_5 = (54, 296)   # 单模式车辆5
    VEHICLE_6 = (153, 365)   # 单模式车辆6

class SingleModeEnemyVehiclePositions(Enum):
    VEHICLE_0 = (1000, 440)   # 单模式敌人0
    VEHICLE_1 = (955, 440)   # 单模式敌人1
    VEHICLE_2 = (1000, 365)   # 单模式敌人2
    VEHICLE_3 = (955, 365)   # 单模式敌人3
    VEHICLE_4 = (1000, 296)   # 单模式敌人4
    VEHICLE_5 = (955, 296)   # 单模式敌人5
    VEHICLE_6 = (896, 360)   # 单模式敌人6