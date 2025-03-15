import React, { useState } from 'react';
import { Select, Button, Checkbox } from 'antd';
import { WindowsFilled, AimOutlined } from '@ant-design/icons';
import styles from './WindowController.module.scss';

const WindowController: React.FC = () => {
  const [selectedWindow, setSelectedWindow] = useState<string | null>(null);
  const [isWindowLocked, setIsWindowLocked] = useState<boolean>(false);

  // Mock window data
  const windows = [
    { label: 'Window 1', value: 'window1' },
    { label: 'Window 2', value: 'window2' },
    { label: 'Window 3', value: 'window3' },
  ];

  const handleLocateWindow = () => {
    if (selectedWindow) {
      // Add your window location logic here
      console.log(`Locating window: ${selectedWindow}`);
    }
  };

  const handleCheckWindow = (e: any) => {
    if (selectedWindow) {
      setIsWindowLocked(!isWindowLocked)
    }
  };

  return (
    <div className={styles.container}>
      <Select
        className={styles.select}
        placeholder="Select a window"
        options={windows}
        value={selectedWindow}
        onChange={(value) => setSelectedWindow(value)}
        suffixIcon={<WindowsFilled />}
      />
      <Button
        type="primary"
        icon={<AimOutlined />}
        onClick={handleLocateWindow}
        disabled={!selectedWindow}
        className={styles.locateBtn}
      >
        窗口定位
      </Button>
      <Checkbox
        onChange={handleCheckWindow}
        disabled={!selectedWindow}
        className={styles.checkbox}
      >
        {isWindowLocked ? '解锁窗口' :'锁定窗口' }
      </Checkbox>
    </div>
  );
};

export default WindowController;