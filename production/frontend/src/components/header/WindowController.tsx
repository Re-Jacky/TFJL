import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Select, Button, Checkbox } from 'antd';
import { WindowsFilled, AimOutlined, ReloadOutlined } from '@ant-design/icons';
import styles from './WindowController.module.scss';
import { useSelector } from 'react-redux';
import { selectActiveWindow, selectWindows } from '@src/store/selectors';
import { setActiveWindow } from '@src/store/actions';
import { useAppDispatch } from '@src/store/store';
import { getWindows } from '@src/store/thunks';
import { api } from '@src/services/api';

const WindowController: React.FC = () => {
  const activeWindow = useSelector(selectActiveWindow);
  const dispatch = useAppDispatch();
  const [isWindowLocked, setIsWindowLocked] = useState<boolean>(false);
  const windows = useSelector(selectWindows);
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
      setIsWindowLocked(!isWindowLocked);
    }
  };

  const onRefresh = useCallback(() => {
    dispatch(getWindows());
  }, [dispatch]);

  useEffect(() => {
    dispatch(getWindows());
  }, []);

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
