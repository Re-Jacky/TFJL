import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Select, Button, Checkbox } from 'antd';
import { WindowsFilled, AimOutlined, ReloadOutlined } from '@ant-design/icons';
import styles from './WindowController.module.scss';
import { useSelector } from 'react-redux';
import { selectActiveWindow, selectInitializing, selectGameWindows } from '@src/store/selectors';
import { setActiveWindow } from '@src/store/actions';
import { useAppDispatch } from '@src/store/store';
import { getGameWindows } from '@src/store/thunks';
import { api } from '@src/services/api';

const WindowController: React.FC = () => {
  const activeWindow = useSelector(selectActiveWindow);
  const initializing = useSelector(selectInitializing);
  const dispatch = useAppDispatch();
  const [isWindowLocked, setIsWindowLocked] = useState<boolean>(false);
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

  const handleCheckWindow = (e: any) => {
    if (activeWindow) {
      api.lockWindow({ lock: e.target.checked }).then(() => {
        setIsWindowLocked(!isWindowLocked);
      });
    }
  };

  const onRefresh = useCallback(() => {
    dispatch(getGameWindows());
  }, [dispatch]);

  useEffect(() => {
    if (!initializing) {
      dispatch(getGameWindows());
    }
  }, [initializing]);

  return (
    <div className={styles.container}>
      <Select
        disabled={isWindowLocked}
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
        onChange={handleCheckWindow}
        disabled={!activeWindow}
        className={styles.checkbox}
      >
        {isWindowLocked ? '解锁窗口' : '锁定窗口'}
      </Checkbox>
    </div>
  );
};

export default WindowController;
