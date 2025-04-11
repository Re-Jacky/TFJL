import React, { useState } from 'react';
import {  Radio, RadioChangeEvent } from 'antd';
import styles from './ShortcutContent.module.scss';
import { produceEmptyCellValues } from '../components/Vehicle';
import Content, { ShortcutModel } from './Content';
import {
  GameMode,
  VehicleSide,
  GeneralShortcut,
  BattleShortcut,
} from './enums';

const emptyShortcut: ShortcutModel = {
  vehicleShortcut: {
    [VehicleSide.LEFT]: produceEmptyCellValues(),
    [VehicleSide.RIGHT]: produceEmptyCellValues(),
  },
  generalShortcut: {
    [GeneralShortcut.FIRST_CARD]: '',
    [GeneralShortcut.SECOND_CARD]: '',
    [GeneralShortcut.THIRD_CARD]: '',
    [GeneralShortcut.UPGRADE_VEHICLE]: '',
    [GeneralShortcut.REFRESH]: '',
    [GeneralShortcut.SELL_CARD]: '',
    [GeneralShortcut.ONE_KEY_SELL_CARD]: false,
  },
  battleShortcut: {
    [BattleShortcut.SURRENDER]: '',
    [BattleShortcut.CONFIRM]: '',
    [BattleShortcut.BATTLE]: '',
    [BattleShortcut.QUICK_MATCH]: '',
    [BattleShortcut.VIEW_OPPONENT_HALO]: '',
  },
};

const ShortcutContent: React.FC = () => {
  
  const [mode, setMode] = useState<GameMode>(GameMode.NONE);
  const [shortcut, setShortcut] = useState<ShortcutModel>(emptyShortcut);

  const onModeChange = (e: RadioChangeEvent) => {
    setMode(e.target.value);
    // service
  };

  const handleSave = () => {
    // service
  };

  const onReset = () => {
    setShortcut(emptyShortcut);
  };

  const onSideChange = (side: VehicleSide) => {
    // service
  };

  return (
    <div className={styles.shortcut}>
      <Radio.Group
        className={styles.modeOptions}
        onChange={onModeChange}
        value={mode}
        options={[
          { label: '无', value: GameMode.NONE },
          { label: '对战', value: GameMode.SINGLE_PLAYER },
          { label: '单人-航海', value: GameMode.SINGLE_PLAYER_SAILING },
          { label: '双人', value: GameMode.TWO_PLAYER },
          { label: '双人-天空', value: GameMode.TWO_PLAYER_SKY },
        ]}
      />
      <Content
        mode={mode}
        shortcut={shortcut}
        setShortcut={(a) => {
          setShortcut(a)
        }}
        onSideChange={onSideChange}
        onSave={handleSave}
        onReset={onReset}
      />
    </div>
  );
};
export default ShortcutContent;
