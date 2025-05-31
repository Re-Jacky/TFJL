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
    QUICK_MATCH = (700, 510)   # 开始战斗
    SURRENDER = (50, 165)   # 投降
    SURRENDER_CONFIRM = (660, 465)   # 投降确认
    BATTLE_END_CONFIRM = (520, 535)   # 战斗结束确认
    UPGRADE_VEHICLE = (320, 570)   # 升级车辆
    REFRESH_CARD = (720, 570)   # 刷新卡片
    ENEMY_STATUS = (920, 130)   # 敌人状态
    SELL_CARD = (330, 460)   # 出售卡片
    CLOST_CARD = (810, 128)   # 关闭卡片信息
    
    CARD_0 = (440, 560)   # 卡片0
    CARD_1 = (525, 560)   # 卡片1
    CARD_2 = (610, 560)   # 卡片2

    ## Auction
    AUCTION_CONFIRM = (650, 465)   # 确认购买
    AUNCTION_CARD_0 = (755, 242)   # 卡片0
    AUNCTION_CARD_1 = (755, 326)   # 卡片1
    AUNCTION_CARD_2 = (755, 412)   # 卡片2
    AUNCTION_CARD_3 = (755, 497)   # 卡片3

    ## Text Area
    TEXT_AREA = (525, 360)    # 文本区域
    TEXT_AREA_CONFIRM = (465, 375)   # 确认

    ## Input Room Number
    ROOM_INPUT_FIELD = (525, 360)   # 房间号输入框
    ROOM_INPUT_CONFIRM = (530, 430)   # 确认输入

    ## Collab
    PLAY_WITH_FRIEND = (350, 510)
    START_ROOM = (437, 430)
    JOIN_ROOM = (615, 430)
    JOIN_ROOM_CONFIRM = (530, 430)
    ADS_REGION = (535, 430)  # 广告区域，用于检测广告是否出现
    
    ## Ice Castle
    ICE_CASTLE = (850, 565)
    ICE_BUY_ROUND = (655, 460)
    ICE_SUPPORT = (395, 460)

    ## moon island
    MOON_ISLAND = (845, 570)
  