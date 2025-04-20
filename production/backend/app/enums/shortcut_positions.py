from enum import Enum
from app.enums.game_positions import GamePositions

class GameMode(Enum):
    SINGLE_PLAYER = 0
    SINGLE_PLAYER_SAILING = 1
    TWO_PLAYER = 2
    TWO_PLAYER_SKY = 3
    AUCTION = 4

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

class TwoModeLeftVehiclePositions(Enum):
    VEHICLE_0 = (130, 440)   # 双人模式车辆0
    VEHICLE_1 = (90, 440)   # 双人模式车辆1
    VEHICLE_2 = (130, 365)   # 双人模式车辆2
    VEHICLE_3 = (90, 365)   # 双人模式车辆3
    VEHICLE_4 = (130, 296)   # 双人模式车辆4
    VEHICLE_5 = (90, 296)   # 双人模式车辆5
    VEHICLE_6 = (108, 220)   # 双人模式车辆6

class TwoModeRightVehiclePositions(Enum):
    VEHICLE_0 = (260, 440)   # 双人模式车辆0
    VEHICLE_1 = (220, 440)   # 双人模式车辆1
    VEHICLE_2 = (260, 365)   # 双人模式车辆2
    VEHICLE_3 = (220, 365)   # 双模式车辆3
    VEHICLE_4 = (260, 296)   # 双人模式车辆4
    VEHICLE_5 = (220, 296)   # 双人模式车辆5
    VEHICLE_6 = (212, 220)   # 双人模式车辆6

class SailModeVehiclePositions(Enum):
    VEHICLE_0 = (140, 440)   # 航海模式车辆0
    VEHICLE_1 = (100, 440)   # 航海模式车辆1
    VEHICLE_2 = (140, 365)   # 航海模式车辆2
    VEHICLE_3 = (100, 365)   # 航海模式车辆3
    VEHICLE_4 = (140, 296)   # 航海模式车辆4
    VEHICLE_5 = (100, 296)   # 航海模式车辆5
    VEHICLE_6 = (196, 360)   # 航海模式车辆6

class SkyTwoModeLeftVehiclePositions(Enum):
    VEHICLE_0 = (113, 440)   # 天空模式车辆0
    VEHICLE_1 = (73, 440)   # 天空模式车辆1
    VEHICLE_2 = (113, 365)   # 天空模式车辆2
    VEHICLE_3 = (73, 365)   # 天空模式车辆3
    VEHICLE_4 = (113, 296)   # 天空模式车辆4
    VEHICLE_5 = (73, 296)   # 天空模式车辆5
    VEHICLE_6 = (91, 240)   # 天空模式车辆6 TBD

class SkyTwoModeRightVehiclePositions(Enum):
    VEHICLE_0 = (244, 440)   # 天空模式车辆0
    VEHICLE_1 = (204, 440)   # 天空模式车辆1
    VEHICLE_2 = (244, 370)   # 天空模式车辆2
    VEHICLE_3 = (204, 370)   # 天空模式车辆3
    VEHICLE_4 = (244, 300)   # 天空模式车辆4
    VEHICLE_5 = (204, 300)   # 天空模式车辆5
    VEHICLE_6 = (196, 240)   # 天空模式车辆6 TBD