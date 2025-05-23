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
  const [currentRound, setCurrentRound] = useState<number>(0);
  const [rolesReady, setRolesReady] = useState<Array<boolean>>([false, false]); // only 2 roles
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentRoundRef = useRef(currentRound);
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

  const startGame = async () => {
    const start = !active;
    setActive(start);

    if (start) {
      if (!roleRef_0?.current || !roleRef_1?.current) {
        return;
      }
      api.startAutoGame({ ...getValidSelectedWindows(), mode });
      setCurrentRound((pre) => pre + 1);
      // create a interval to check if the game is over every 10 seconds
      const interval = setInterval(() => {
        const { main, sub } = getValidSelectedWindows();
        api.isInGame({ main: main.game, sub: sub.game }).then((res) => {
          if (!res.status) {
            // start a new game
            if (currentRoundRef.current < gameRounds) {
              api.startAutoGame({ ...getValidSelectedWindows(), mode });
              setCurrentRound((pre) => pre + 1);
            } else {
              clearInterval(interval);
              intervalRef.current = null;
              setActive(false);
            }
          }
        });
      }, 1000);
      intervalRef.current = interval;
    } else {
      //
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  };

  const onValidChange = (index: number) => (ready: boolean) => {
    const newReady = [...rolesReady];
    newReady[index] = ready;
    setRolesReady(newReady);
  };

  const checkWindow = (handler: RoleHandler | null) => () => {
    const options = handler?.getSelectedWindow();
    if (options?.game && options?.tool) {
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

  return (
    <div className={styles.automator}>
      <div className={styles.header}>
        <div>
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
            onChange={(e) => setGameRounds(parseInt(e.target.value))}
          />
        </div>
        <Button
          type={active ? 'default' : 'primary'}
          onClick={startGame}
          danger={active}
          disabled={!(rolesReady[0] && rolesReady[1])}
        >
          {active ? '停止' : '开始'}
        </Button>
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
          <Role role='主卡' onValidChange={onValidChange(0)} ref={roleRef_0} />
          <Button
            icon={<AimOutlined />}
            disabled={!rolesReady[0]}
            onClick={checkWindow(roleRef_0?.current)}
          >
            检查窗口
          </Button>
        </div>
        <div className={styles.contentRow}>
          <Role role='副卡' onValidChange={onValidChange(1)} ref={roleRef_1} />
          <Button
            icon={<AimOutlined />}
            disabled={!rolesReady[1]}
            onClick={checkWindow(roleRef_1?.current)}
          >
            检查窗口
          </Button>
        </div>
      </div>
      <div>
        <Checkbox>结束后开始对战</Checkbox>
      </div>
      <h2 className={styles.footerNote}>{`第 ${currentRound} 轮`}</h2>
    </div>
  );
};

export default Automator;
