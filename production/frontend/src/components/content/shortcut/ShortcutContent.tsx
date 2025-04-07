import React, { useState } from 'react';
import { Radio, type RadioChangeEvent } from 'antd';
import styles from './ShortcutContent.module.scss';
import Vehicle from '../components/Vehicle';
import LabelInput from './LabelInput';
import Mask from './Mask';

export enum GameMode {
  NONE,
  SINGLE_PLAYER,
  SINGLE_PLAYER_SAILING,
  TWO_PLAYER,
  TWO_PLAYER_SKY,
}

const ShortcutContent = () => {
  const [mode, setMode] = useState<GameMode>(GameMode.NONE);
  const onChange = (e: RadioChangeEvent) => {
    setMode(e.target.value);
    // TODO: send to servic
  };

  const renderVehicle = () => {
    switch (mode) {
      case GameMode.SINGLE_PLAYER:
      case GameMode.SINGLE_PLAYER_SAILING:
        return <Vehicle />;
      case GameMode.TWO_PLAYER:
      case GameMode.TWO_PLAYER_SKY:
        return (
          <>
            <Vehicle label='左' />
            <Vehicle label='右' />
          </>
        );
      default:
        return <Vehicle />;
    }
  };
  return (
    <div className={styles.shortcut}>
      <Radio.Group
        className={styles.modeOptions}
        onChange={onChange}
        value={mode}
        options={[
          { label: '无', value: GameMode.NONE },
          { label: '单人', value: GameMode.SINGLE_PLAYER },
          { label: '单人-航海', value: GameMode.SINGLE_PLAYER_SAILING },
          { label: '双人', value: GameMode.TWO_PLAYER },
          { label: '双人-天空', value: GameMode.TWO_PLAYER_SKY },
        ]}
      />
      <div className={styles.contentArea}>
        {mode === GameMode.NONE && <Mask />}
        <div className={styles.vehicleGroup}>{renderVehicle()}</div>
        <div className={styles.inputGroup}>
          <LabelInput label='扩建' />
          <LabelInput label='刷新' />
          <LabelInput label='卖卡' />
          <LabelInput label='投降' />
          <Radio>一键卖卡</Radio>
        </div>
      </div>
    </div>
  );
};
export default ShortcutContent;
