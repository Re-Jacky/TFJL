import React, { useState, useEffect } from 'react';
import styles from './Content.module.scss';
import LabelInput from '@src/components/content/shortcut/LabelInput';
import { Button, Checkbox, InputNumber, Popover } from 'antd';
import {
  InfoCircleTwoTone,
  ReloadOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import {
  GameMode,
  VehicleSide,
  GeneralShortcut,
  BattleShortcut,
} from '@src/types';
import Vehicle, { type CellValues } from '../components/Vehicle';
import LoadingMask from '@src/components/loading/LoadingMask';

export interface ShortcutModel {
  vehicleShortcut: Record<VehicleSide, CellValues>;
  generalShortcut: Record<GeneralShortcut, string | boolean | number>;
  battleShortcut: Record<BattleShortcut, string>;
}

export interface ContentProps {
  mode: GameMode;
  shortcut: ShortcutModel;
  setShortcut: (shortcut: ShortcutModel) => void;
  onSave: () => void;
  onReset: () => void;
  onSideChange?: (side: VehicleSide) => void;
  isLoading?: boolean;
}

const Content: React.FC<ContentProps> = (props) => {
  const {
    mode,
    shortcut,
    setShortcut,
    onReset,
    onSave,
    onSideChange,
    isLoading = true,
  } = props;
  const [active, setActive] = useState<VehicleSide>(VehicleSide.LEFT);

  const onVehShortcutChange = (cellValue: CellValues, side: VehicleSide) => {
    setShortcut({
      ...shortcut,
      vehicleShortcut: {
        ...shortcut.vehicleShortcut,
        [side]: cellValue,
      },
    });
  };

  const onGenerageInputChange = (
    val: string | boolean | number,
    key: string
  ) => {
    setShortcut({
      ...shortcut,
      generalShortcut: {
        ...shortcut.generalShortcut,
        [key]: val,
      },
    });
  };

  const onBattleInputChange = (val: string, key: string) => {
    setShortcut({
      ...shortcut,
      battleShortcut: {
        ...shortcut.battleShortcut,
        [key]: val,
      },
    });
  };

  const renderVehicle = () => {
    switch (mode) {
      case GameMode.SINGLE_PLAYER_SAILING:
        return (
          <Vehicle
            active
            onChange={(val) => onVehShortcutChange(val, VehicleSide.LEFT)}
            value={shortcut.vehicleShortcut[VehicleSide.LEFT]}
          />
        );
      case GameMode.SINGLE_PLAYER:
      case GameMode.TWO_PLAYER:
      case GameMode.TWO_PLAYER_SKY:
        return (
          <>
            <Vehicle
              label={mode === GameMode.SINGLE_PLAYER ? '我方' : '左'}
              active={active === VehicleSide.LEFT}
              onClick={() => setActive(VehicleSide.LEFT)}
              onChange={(val) => onVehShortcutChange(val, VehicleSide.LEFT)}
              value={shortcut.vehicleShortcut[VehicleSide.LEFT]}
            />
            <Vehicle
              label={mode === GameMode.SINGLE_PLAYER ? '敌方' : '右'}
              active={active === VehicleSide.RIGHT}
              onClick={() => {
                if (mode === GameMode.SINGLE_PLAYER) {
                  return;
                }
                setActive(VehicleSide.RIGHT);
              }}
              onChange={(val) => onVehShortcutChange(val, VehicleSide.RIGHT)}
              value={shortcut.vehicleShortcut[VehicleSide.RIGHT]}
            />
          </>
        );
      default:
        return (
          <Vehicle active value={shortcut.vehicleShortcut[VehicleSide.LEFT]} />
        );
    }
  };

  useEffect(() => {
    onSideChange?.(active);
  }, [active]);

  const EnhanceButtonDesc = () => {
    return (
      <>
        <div>
          1. 防止短时间内重复按同一按键
        </div>
        <div>
          2. 优化自动卖卡逻辑，防止在卖卡间隔内上卡触发刷新
        </div>
      </>
    );
  }

  return (
    <div className={styles.contentArea}>
      <LoadingMask visible={isLoading} />
      <div className={styles.vehicleGroup}>{renderVehicle()}</div>
      <div className={styles.inputGroup}>
        <div className={styles.inputTop}>
          <LabelInput
            label='卡1'
            onChange={(val) =>
              onGenerageInputChange(val, GeneralShortcut.FIRST_CARD)
            }
            value={
              shortcut.generalShortcut[GeneralShortcut.FIRST_CARD] as string
            }
          />
          <LabelInput
            label='卡2'
            onChange={(val) =>
              onGenerageInputChange(val, GeneralShortcut.SECOND_CARD)
            }
            value={
              shortcut.generalShortcut[GeneralShortcut.SECOND_CARD] as string
            }
          />
          <LabelInput
            label='卡3'
            onChange={(val) =>
              onGenerageInputChange(val, GeneralShortcut.THIRD_CARD)
            }
            value={
              shortcut.generalShortcut[GeneralShortcut.THIRD_CARD] as string
            }
          />
        </div>
        <div className={styles.inputMiddle}>
          <div className={styles.generalInputs}>
            <LabelInput
              label='扩建'
              onChange={(val) =>
                onGenerageInputChange(val, GeneralShortcut.UPGRADE_VEHICLE)
              }
              value={
                shortcut.generalShortcut[
                  GeneralShortcut.UPGRADE_VEHICLE
                ] as string
              }
            />
            <LabelInput
              label='刷新'
              onChange={(val) =>
                onGenerageInputChange(val, GeneralShortcut.REFRESH)
              }
              value={
                shortcut.generalShortcut[GeneralShortcut.REFRESH] as string
              }
            />
            <LabelInput
              label='卖卡'
              onChange={(val) =>
                onGenerageInputChange(val, GeneralShortcut.SELL_CARD)
              }
              value={
                shortcut.generalShortcut[GeneralShortcut.SELL_CARD] as string
              }
            />
            <div className={styles.quickSell}>
              <Checkbox
                onChange={(e) => {
                  onGenerageInputChange(
                    e.target.checked,
                    GeneralShortcut.QUICK_SELL
                  );
                }}
                checked={
                  shortcut.generalShortcut[
                    GeneralShortcut.QUICK_SELL
                  ] as boolean
                }
              >
                一键卖卡
              </Checkbox>
              <InputNumber
                placeholder={'延时'}
                className={styles.quickSellDelay}
                suffix={'ms'}
                value={
                  shortcut.generalShortcut[
                    GeneralShortcut.QUICK_SELL_DELAY
                  ] as number
                }
                onChange={(val) => {
                  if (val) {
                    onGenerageInputChange(
                      val as number,
                      GeneralShortcut.QUICK_SELL_DELAY
                    );
                  }
                }}
              />
            </div>
            <Checkbox
              onChange={(e) => {
                onGenerageInputChange(
                  e.target.checked,
                  GeneralShortcut.QUICK_REFRESH
                );
              }}
              checked={
                shortcut.generalShortcut[
                  GeneralShortcut.QUICK_REFRESH
                ] as boolean
              }
            >
              自动刷新
            </Checkbox>
            <div>
              <Checkbox
                onChange={(e) => {
                  onGenerageInputChange(
                    e.target.checked,
                    GeneralShortcut.ENHANCED_BTN_PRESS
                  );
                }}
                checked={
                  shortcut.generalShortcut[
                    GeneralShortcut.ENHANCED_BTN_PRESS
                  ] as boolean
                }
              >
                按键优化
              </Checkbox>
              <Popover placement='right' content={<EnhanceButtonDesc />}>
                <InfoCircleTwoTone />
              </Popover>
            </div>
          </div>
          {mode === GameMode.SINGLE_PLAYER ? (
            <div className={styles.battleInputs}>
              <LabelInput
                label='投降'
                onChange={(val) =>
                  onBattleInputChange(val, BattleShortcut.SURRENDER)
                }
                value={shortcut.battleShortcut[BattleShortcut.SURRENDER]}
              />
              <LabelInput
                label='确认'
                onChange={(val) =>
                  onBattleInputChange(val, BattleShortcut.CONFIRM)
                }
                value={shortcut.battleShortcut[BattleShortcut.CONFIRM]}
              />
              <LabelInput
                label='对战'
                onChange={(val) =>
                  onBattleInputChange(val, BattleShortcut.BATTLE)
                }
                value={shortcut.battleShortcut[BattleShortcut.BATTLE]}
              />
              <LabelInput
                label='快速匹配'
                onChange={(val) =>
                  onBattleInputChange(val, BattleShortcut.QUICK_MATCH)
                }
                value={shortcut.battleShortcut[BattleShortcut.QUICK_MATCH]}
              />
              <LabelInput
                label='查看对方光环'
                onChange={(val) =>
                  onBattleInputChange(val, BattleShortcut.VIEW_OPPONENT_HALO)
                }
                value={
                  shortcut.battleShortcut[BattleShortcut.VIEW_OPPONENT_HALO]
                }
              />
              <LabelInput
                label='关闭卡牌信息'
                onChange={(val) =>
                  onBattleInputChange(val, BattleShortcut.CLOSE_CARD)
                }
                value={shortcut.battleShortcut[BattleShortcut.CLOSE_CARD]}
              />
            </div>
          ) : null}
        </div>
      </div>
      <div className={styles.actionBtn}>
        <Button type='primary' icon={<SaveOutlined />} onClick={onSave}>
          保存
        </Button>
        <Button icon={<ReloadOutlined />} onClick={onReset}>
          重置
        </Button>
      </div>
    </div>
  );
};

export default Content;
