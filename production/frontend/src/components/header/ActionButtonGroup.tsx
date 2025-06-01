import React from 'react';
import { Button } from 'antd';
import styles from './ActionButtonGroup.module.scss';
import { api } from '@src/services/api';


const ActionButtonGroup: React.FC = () => {
  const handleStart = () => {
    window.nodeAPI?.restartServer();
    location.reload();
  };

  const handleTest = () => {
    api.test();
  }

  return (
    <div className={styles.actionBtnGroup}>
      <Button type="primary" onClick={handleStart}>
        刷新
      </Button>
      {/* <Button type="primary" onClick={handleTest}>
        test
      </Button> */}
    </div>
  );
};

export default ActionButtonGroup;