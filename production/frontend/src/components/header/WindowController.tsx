import React, { useCallback, useEffect, useState } from 'react';
import { Select, Button, Checkbox } from 'antd';
import { WindowsFilled, AimOutlined } from '@ant-design/icons';
import styles from './WindowController.module.scss';
import { api } from '@src/services/api';
import { useSelector } from 'react-redux';
import { selectActiveWindow } from '@src/store/selectors';
import { setActiveWindow } from '@src/store/actions';
import { useAppDispatch } from '@src/store/store';

const WindowController: React.FC = () => {
  const activeWindow = useSelector(selectActiveWindow);
  const dispatch = useAppDispatch();
  const [isWindowLocked, setIsWindowLocked] = useState<boolean>(false);
  const [windows, setWindows] = useState<
    Array<{ label: string; value: string }>
  >([]);

  const handleLocateWindow = () => {
    if (activeWindow) {
      // Add your window location logic here
      console.log(`Locating window: ${activeWindow}`);
    }
  };

  const handleCheckWindow = (e: any) => {
    if (activeWindow) {
      setIsWindowLocked(!isWindowLocked);
    }
  };

  useEffect(() => {
    api
      .getWindows()
      .then((res) => {
        const wnds = res.windows.map((item) => ({
          label: item.title,
          value: item.pid.toString(),
        }));
        setWindows(wnds);
        dispatch(setActiveWindow(wnds[0]?.value));
      })
      .catch((err) => console.log(err));
  }, []);

  return (
    <div className={styles.container}>
      <Select
        disabled={isWindowLocked}
        className={styles.select}
        placeholder='Select a window'
        options={windows}
        value={activeWindow}
        onChange={(value) => dispatch(setActiveWindow(value))}
        suffixIcon={<WindowsFilled />}
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
