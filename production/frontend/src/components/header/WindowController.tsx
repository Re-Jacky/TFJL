import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Select, Button, Checkbox } from 'antd';
import { WindowsFilled, AimOutlined, ReloadOutlined } from '@ant-design/icons';
import styles from './WindowController.module.scss';
import { useSelector } from 'react-redux';
import { selectActiveWindow, selectInitializing, selectGameWindows, selectIsThunderPlayer } from '@src/store/selectors';
import { setActiveWindow  } from '@src/store/actions';
import { useAppDispatch } from '@src/store/store';
import { getGameWindows,setIsThunderPlayer } from '@src/store/thunks';
import { api } from '@src/services/api';

const WindowController: React.FC = () => {
  const activeWindow = useSelector(selectActiveWindow);
  const initializing = useSelector(selectInitializing);
  const isThunderPlayer = useSelector(selectIsThunderPlayer);
  const dispatch = useAppDispatch();
  const windows = useSelector(selectGameWindows);
  const options = useMemo(
    () =>
      windows.map((item) => ({
        label: item.title,
        value: item.pid.toString(),
      })),
    [windows]
  );
  const [isHovered, setIsHovered] = useState<boolean>(false);
  const handleLocateWindow = () => {
    if (activeWindow) {
      api.locateWindow(parseInt(activeWindow));
    }
  };

  const setThunderPlayer = (e: any) => {
    dispatch(setIsThunderPlayer(e.target.checked));
  };

  const onRefresh = useCallback(() => {
    dispatch(getGameWindows());
  }, [dispatch]);

  useEffect(() => {
    if (windows.length > 0 && activeWindow) {
      const wnd = windows.find((item) => item.pid === parseInt(activeWindow))
      const isThunder = wnd?.title !== '塔防精灵'
      dispatch(setIsThunderPlayer(isThunder))
    }
  }, [activeWindow, windows]);

  useEffect(() => {
    if (!initializing) {
      dispatch(getGameWindows());
    }
  }, [initializing]);

  return (
    <div className={styles.container}>
      <Select
        className={styles.select}
        placeholder='Select a window'
        options={options}
        value={activeWindow}
        onChange={(value) => dispatch(setActiveWindow(value))}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        suffixIcon={isHovered ? <ReloadOutlined onClick={onRefresh} style={{color: '#4096ff'}}/> : <WindowsFilled />}
      />
      <Button
        type='primary'
        icon={<AimOutlined />}
        onClick={handleLocateWindow}
        disabled={!activeWindow}
        className={styles.locateBtn}
      >
        窗口定位
      </Button>
      <Checkbox
        onChange={setThunderPlayer}
        disabled={!activeWindow}
        className={styles.checkbox}
        checked={isThunderPlayer}
      >
        {isThunderPlayer ? '关闭雷电' : '开启雷电'}
      </Checkbox>
    </div>
  );
};

export default WindowController;
