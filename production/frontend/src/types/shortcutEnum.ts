export enum ShortcutMode {
  SINGLE_PLAYER,
  SINGLE_PLAYER_SAILING,
  TWO_PLAYER,
  TWO_PLAYER_SKY,
  AUCTION
}

export enum GameMode {
  Collab,
  IceCastle,
  MoonIsland,
}

export enum VehicleSide {
  LEFT = 'left',
  RIGHT = 'right',
}

export enum GeneralShortcut {
  FIRST_CARD = 'firstCard',
  SECOND_CARD = 'secondCard',
  THIRD_CARD = 'thirdCard',
  UPGRADE_VEHICLE = 'upgradeVehicle',
  REFRESH = 'refresh',
  SELL_CARD = 'sellCard',
  QUICK_SELL = 'quickSell',
  QUICK_SELL_DELAY = 'quickSellDelay',
  QUICK_REFRESH = 'quickRefresh',
  ENHANCED_BTN_PRESS = 'enhancedBtnPress',
}

export enum BattleShortcut {
  SURRENDER = 'surrender',
  CONFIRM = 'confirm',
  BATTLE = 'battle',
  AUTO_QUICK_MATCH = 'autoQuickMatch',
  VIEW_OPPONENT_HALO = 'viewOpponentHalo',
  CLOSE_CARD = 'closeCard',
}

export enum AuctionShortcut {
  CARD_0 = 'auctionCard0', 
  CARD_1 = 'auctionCard1',
  CARD_2 = 'auctionCard2',
  CARD_3 = 'auctionCard3'
}