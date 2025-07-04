import React, { useEffect, useRef, useState } from 'react';
import { Button, Radio, RadioChangeEvent, Input, Checkbox } from 'antd';
import { InfoCircleTwoTone, AimOutlined } from '@ant-design/icons';
import styles from './Automator.module.scss';
import Role, { RoleHandler } from './Role';
import { useSelector } from 'react-redux';
import { selectInitializing } from '@src/store/selectors';
import { useAppDispatch } from '@src/store/store';
import { getToolWindows } from '@src/store/thunks';
import { api } from '@src/services/api';
import { GameMode } from '@src/types';
import { updateLogRecords } from '@src/store/actions';
import { LogRecord } from '@src/store/slices/uiSlice';

const getDefaultGameRounds = (gameMode: GameMode) => {
  switch (gameMode) {
    case GameMode.Collab:
      return 6;
    case GameMode.IceCastle:
      return 6;
    case GameMode.MoonIsland:
      return 4;
    default:
      return 0;
  }
};

function assertIsDefined<T>(value: T): asserts value is NonNullable<T> {
  if (value === null || value === undefined) {
    throw new Error(`Expected 'value' to be defined, but received ${value}`);
  }
}

const Automator: React.FC = () => {
  const [mode, setMode] = useState<GameMode>(GameMode.Collab);
  const [active, setActive] = useState<boolean>(false);
  const [gameRounds, setGameRounds] = useState<number>(
    getDefaultGameRounds(mode)
  );
  const [iceOnlySupport, setIceOnlySupport] = useState<boolean>(false);
  const [currentRound, setCurrentRound] = useState<number>(0);
  const [autoBattle, setAutoBattle] = useState<boolean>(false);
  const [autoTurnOff, setAutoTurnOff] = useState<boolean>(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentRoundRef = useRef(currentRound);
  const autoBattleRef = useRef(autoBattle);
  const autoTurnOffRef = useRef(autoTurnOff);
  const roleRef_0 = useRef<RoleHandler | null>(null);
  const roleRef_1 = useRef<RoleHandler | null>(null);

  const initializing = useSelector(selectInitializing);
  const dispatch = useAppDispatch();

  useEffect(() => {
    setGameRounds(getDefaultGameRounds(mode));
  }, [mode]);

  const onModeChange = (e: RadioChangeEvent) => {
    const newMode = e.target.value as GameMode;
    setMode(newMode);
  };

  const getValidSelectedWindows = () => {
    assertIsDefined(roleRef_0.current);
    assertIsDefined(roleRef_1.current);
    return {
      main: roleRef_0.current.getSelectedWindow(),
      sub: roleRef_1.current.getSelectedWindow(),
    };
  };

  const formatDate = (date: Date) => {
    // toISOString() returns format like: "2025-07-04T18:01:48.000Z"
    // So we need to replace the 'T' with space and remove milliseconds and 'Z'
    return date.toISOString().replace('T', ' ').split('.')[0];
  };

  const addLog = (msg: string, level?: LogRecord['level']) => {
    dispatch(
      updateLogRecords({
        level: level ?? 'info',
        message: msg,
        timestamp: formatDate(new Date()),
      })
    );
  };

  const inGameHeartbeat = () => {
    const { main, sub } = getValidSelectedWindows();
    // if inGame check failed in the first heartbeat, it means the game hasn't start yet, could be due to the wrong root number.
    // in this case we need to start new game while not increase the game round.
    let heartbeatIdx = 1;
    const interval = setInterval(() => {
      api.isInGame({ main: main.game, sub: sub.game }).then((res) => {
        if (res.status) {
          if (heartbeatIdx === 1) {
            addLog('已进入游戏...');
          } else {
            addLog('游戏中...');
          }
          heartbeatIdx++;
        } else {
          // start a new game
          if (currentRoundRef.current < gameRounds) {
            api.startAutoGame({ main, sub, mode, iceOnlySupport });
            // only increate the round count if it's not the first heartbeat
            if (heartbeatIdx === 1) {
              addLog('进入游戏失败, 重试...', 'warn');
            } else {
              addLog('已退出游戏, 开始下一局...');
              setCurrentRound((pre) => pre + 1);
            }
            // when start a new game, reset this flag
            heartbeatIdx = 1;
          } else {
            addLog('任务结束');
            clearInterval(interval);
            intervalRef.current = null;
            setActive(false);
            if (autoTurnOffRef.current) {
              api.turnOffPC();
            }
            if (autoBattleRef.current) {
              api.startAutoBattle({ main, sub });
            }
          }
        }
      });
    }, 10000);
    intervalRef.current = interval;
  };
  const startGame = async () => {
    const start = !active;

    if (start) {
      if (!roleRef_0?.current || !roleRef_1?.current) {
        return;
      }
      const result = await api.startAutoGame({
        ...getValidSelectedWindows(),
        mode,
        iceOnlySupport,
      });
      if (!result.status) {
        return;
      }
      setActive(start);
      setCurrentRound((pre) => pre + 1);
      // create a interval to check if the game is over every 10 seconds
      inGameHeartbeat();
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setActive(false);
    }
  };

  const continueGame = () => {
    if (!roleRef_0?.current || !roleRef_1?.current) {
      return;
    }
    setActive(true);
    inGameHeartbeat();
  };
  const checkWindow = (idx: 0 | 1) => () => {
    const handler = idx === 0 ? roleRef_0.current : roleRef_1.current;
    const options = handler?.getSelectedWindow();
    if (options?.game && options?.tool) {
      api.locateAutoWindow({ game: options.game, tool: options.tool, idx });
    }
  };

  useEffect(() => {
    if (!initializing) {
      dispatch(getToolWindows());
    }
  }, [initializing]);

  useEffect(() => {
    //cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    // update ref so the interval can get the latest value
    currentRoundRef.current = currentRound;
  }, [currentRound]);

  useEffect(() => {
    // update ref so the interval can get the latest value
    autoBattleRef.current = autoBattle;
  }, [autoBattle]);

  useEffect(() => {
    // update ref so the interval can get the latest value
    autoTurnOffRef.current = autoTurnOff;
  }, [autoTurnOff]);

  return (
    <div className={styles.automator}>
      <div className={styles.bodyArea}>
        <div className={styles.leftPanel}>
          <div className={styles.header}>
            <Radio.Group
              className={styles.modeOptions}
              onChange={onModeChange}
              value={mode}
              options={[
                { label: '合作', value: GameMode.Collab },
                { label: '寒冰', value: GameMode.IceCastle },
                { label: '暗月', value: GameMode.MoonIsland },
              ]}
            />
            <Input
              className={styles.gameRoundsInput}
              prefix='次数'
              value={gameRounds}
              onChange={(e) => {
                const newValue = e.target.value;
                setGameRounds(newValue ? parseInt(newValue) : 0);
              }}
            />
          </div>
          <div className={styles.info}>
            <InfoCircleTwoTone />
            <span className={styles.infoText}>
              注意：先通过本软件设置好游戏、老马窗口后，才能在老马中
              <b>
                <i>锁定窗口</i>
              </b>
              <br />
              在老马中设置好脚本后，点击{' '}
              <b>
                <i>开始</i>
              </b>{' '}
              按钮，即可开始自动执行脚本
            </span>
          </div>
          <div className={styles.content}>
            <div className={styles.contentRow}>
              <Role role='主卡' ref={roleRef_0} defaultSelectedIndex={0} />
              <Button icon={<AimOutlined />} onClick={checkWindow(0)}>
                检查窗口
              </Button>
            </div>
            <div className={styles.contentRow}>
              <Role role='副卡' ref={roleRef_1} defaultSelectedIndex={1} />
              <Button icon={<AimOutlined />} onClick={checkWindow(1)}>
                检查窗口
              </Button>
              {mode === GameMode.IceCastle ? (
                <Checkbox
                  className={styles.iceCastleOnlySupport}
                  onChange={(e) => {
                    setIceOnlySupport(e.target.checked);
                  }}
                >
                  仅助战
                </Checkbox>
              ) : null}
            </div>
          </div>
          <div>
            <Checkbox
              checked={autoBattle}
              onChange={(e) => {
                const val = e.target.checked;
                setAutoBattle(val);
                if (val) {
                  setAutoTurnOff(false);
                }
              }}
            >
              结束后开始对战(使用老马自动关机)
            </Checkbox>
          </div>
          <div>
            <Checkbox
              checked={autoTurnOff}
              onChange={(e) => {
                const val = e.target.checked;
                setAutoTurnOff(val);
                if (val) {
                  setAutoBattle(false);
                }
              }}
            >
              结束后关机
            </Checkbox>
          </div>
        </div>
        <div className={styles.rightPanel}>
          <Button
            type={active ? 'default' : 'primary'}
            onClick={startGame}
            danger={active}
          >
            {active ? '停止' : '开始'}
          </Button>
          <Button
            onClick={continueGame}
            color='orange'
            variant='outlined'
            disabled={active}
          >
            继续
          </Button>
        </div>
      </div>
      <h2 className={styles.footerNote}>
        第
        <Input
          type='number'
          value={currentRound}
          className={styles.roundInput}
          onChange={(e) => {
            const newValue = e.target.value;
            setCurrentRound(newValue ? parseInt(newValue) : 0);
          }}
        />
        轮
      </h2>
    </div>
  );
};

export default Automator;
