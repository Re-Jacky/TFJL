import React, { useEffect, useState } from 'react';
import { Button, Radio, RadioChangeEvent } from 'antd';
import styles from './ShortcutContent.module.scss';
import { produceEmptyCellValues } from '../components/Vehicle';
import Content, { ShortcutModel } from './Content';
import {
  GameMode,
  VehicleSide,
  GeneralShortcut,
  BattleShortcut,
} from '@src/types';
import { api } from '@src/services/api';
import _ from 'lodash';

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
    [GeneralShortcut.QUICK_SELL]: false,
    [GeneralShortcut.QUICK_REFRESH]: false,
    [GeneralShortcut.QUICK_SELL_DELAY]: 0,
    [GeneralShortcut.ENHANCED_BTN_PRESS]: false,
  },
  battleShortcut: {
    [BattleShortcut.SURRENDER]: '',
    [BattleShortcut.CONFIRM]: '',
    [BattleShortcut.BATTLE]: '',
    [BattleShortcut.QUICK_MATCH]: '',
    [BattleShortcut.VIEW_OPPONENT_HALO]: '',
    [BattleShortcut.CLOSE_CARD]: '',
  },
};

const ShortcutContent: React.FC = () => {
  const [mode, setMode] = useState<GameMode>(GameMode.SINGLE_PLAYER);
  const [shortcut, setShortcut] = useState<ShortcutModel>(emptyShortcut);
  const [defaultShortcut, setDefaultShortcut] = useState<ShortcutModel | null>(
    null
  );
  const [loading, setLoading] = useState<boolean>(true);
  const [active, setActive] = useState<boolean>(false);

  const onModeChange = (e: RadioChangeEvent) => {
    const mode = e.target.value as GameMode;
    setMode(mode);
    // service
    api.setShortcutConfig({ mode });
  };

  const handleSave = () => {
    // service
    api.saveShortcut(shortcut);
  };

  const onReset = () => {
    setShortcut(defaultShortcut ?? emptyShortcut);
  };

  const onSideChange = (side: VehicleSide) => {
    // service
  };

  const toggleActive = () => {
    setActive(!active);
    api.monitorShortcut(!active);
  };

  useEffect(() => {
    api
      .getShortcut()
      .then((res) => {
        setShortcut(res.shortcut);
        setDefaultShortcut(res.shortcut);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);
  return (
    <div className={styles.shortcut}>
      <div className={styles.header}>
        <Radio.Group
          className={styles.modeOptions}
          onChange={onModeChange}
          value={mode}
          options={[
            { label: '对战', value: GameMode.SINGLE_PLAYER },
            { label: '单人-航海', value: GameMode.SINGLE_PLAYER_SAILING },
            { label: '双人', value: GameMode.TWO_PLAYER },
            { label: '双人-天空', value: GameMode.TWO_PLAYER_SKY },
          ]}
        />
        <Button type={active ? 'default' : 'primary'} onClick={toggleActive} danger={active}>
          {active ? '停用' : '启用'}
        </Button>
      </div>

      <Content
        mode={mode}
        shortcut={shortcut}
        setShortcut={setShortcut}
        onSideChange={onSideChange}
        onSave={handleSave}
        onReset={onReset}
        isLoading={loading}
        disableSave={_.isEqual(shortcut, defaultShortcut)}
      />
    </div>
  );
};
export default ShortcutContent;
