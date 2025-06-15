import React, { useEffect, useState } from 'react';
import { Button, Radio, RadioChangeEvent } from 'antd';
import { InfoCircleTwoTone } from '@ant-design/icons';
import styles from './ShortcutContent.module.scss';
import { produceEmptyCellValues } from '../components/Vehicle';
import Content, { ShortcutModel } from './Content';
import {
  ShortcutMode,
  VehicleSide,
  GeneralShortcut,
  BattleShortcut,
  AuctionShortcut,
} from '@src/types';
import { api } from '@src/services/api';
import { isEqual } from 'lodash-es';
import { useSelector } from 'react-redux';
import { selectInitializing } from '@src/store/selectors';

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
    [GeneralShortcut.ENHANCED_BTN_PRESS_DELAY]: 0,
  },
  battleShortcut: {
    [BattleShortcut.SURRENDER]: '',
    [BattleShortcut.CONFIRM]: '',
    [BattleShortcut.BATTLE]: '',
    [BattleShortcut.AUTO_QUICK_MATCH]: false,
    [BattleShortcut.VIEW_OPPONENT_HALO]: '',
    [BattleShortcut.CLOSE_CARD]: '',
  },
  auctionShortcut: {
    [AuctionShortcut.CARD_0]: '',
    [AuctionShortcut.CARD_1]: '',
    [AuctionShortcut.CARD_2]: '',
    [AuctionShortcut.CARD_3]: '',
  },
};

const ShortcutContent: React.FC = () => {
  const [mode, setMode] = useState<ShortcutMode>(ShortcutMode.SINGLE_PLAYER);
  const [shortcut, setShortcut] = useState<ShortcutModel>(emptyShortcut);
  const [defaultShortcut, setDefaultShortcut] = useState<ShortcutModel | null>(
    null
  );
  const [loading, setLoading] = useState<boolean>(true);
  const [active, setActive] = useState<boolean>(false);
  const initializing = useSelector(selectInitializing);

  const onModeChange = (e: RadioChangeEvent) => {
    const mode = e.target.value as ShortcutMode;
    setMode(mode);
    // service
    api.setShortcutConfig({ mode });
  };

  const handleSave = () => {
    // service
    api.saveShortcut(shortcut);
    setDefaultShortcut(shortcut);
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
    if (!initializing) {
      api
        .getShortcut()
        .then((res) => {
          setShortcut(res.shortcut);
          setDefaultShortcut(res.shortcut);
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [initializing]);
  return (
    <div className={styles.shortcut}>
      <div className={styles.header}>
        <Radio.Group
          className={styles.modeOptions}
          onChange={onModeChange}
          value={mode}
          options={[
            { label: '对战', value: ShortcutMode.SINGLE_PLAYER },
            { label: '单人-航海', value: ShortcutMode.SINGLE_PLAYER_SAILING },
            { label: '双人', value: ShortcutMode.TWO_PLAYER },
            { label: '双人-天空', value: ShortcutMode.TWO_PLAYER_SKY },
            { label: '竞拍', value: ShortcutMode.AUCTION },
          ]}
        />
        <Button
          type={active ? 'default' : 'primary'}
          onClick={toggleActive}
          danger={active}
        >
          {active ? '停用' : '启用'}
        </Button>
      </div>
      <div className={styles.info}>
        <InfoCircleTwoTone />
        <span className={styles.infoText}>
          注意：请不要使用特殊键位，如：
          <span className={styles.highlight}>Ctrl</span>、
          <span className={styles.highlight}>Alt</span>、
          <span className={styles.highlight}>Meta/Win</span>
        </span>
      </div>
      <Content
        mode={mode}
        shortcut={shortcut}
        setShortcut={setShortcut}
        onSideChange={onSideChange}
        onSave={handleSave}
        onReset={onReset}
        isLoading={loading}
        disableSave={isEqual(shortcut, defaultShortcut)}
      />
    </div>
  );
};
export default ShortcutContent;
