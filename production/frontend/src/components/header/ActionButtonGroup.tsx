import React from 'react';
import { Button } from 'antd';
import styles from './ActionButtonGroup.module.scss';
import { api } from '@src/services/api';
import { useAppSelector } from '@src/store/store';
import { selectActiveWindow } from '@src/store/selectors';


const ActionButtonGroup: React.FC = () => {
  const activeWindow = useAppSelector(selectActiveWindow);
  const handleStart = () => {
    window.nodeAPI?.restartServer();
    location.reload();
  };

  const handleTest = () => {
    if (activeWindow) {
      api.test(activeWindow || '');
    }
  }

  return (
    <div className={styles.actionBtnGroup}>
      <Button type="primary" onClick={handleStart}>
        刷新
      </Button>
      <Button type="primary" onClick={handleTest}>
        test
      </Button>
    </div>
  );
};

export default ActionButtonGroup;