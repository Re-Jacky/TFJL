import React from 'react';
import { Button } from 'antd';
import styles from './ActionButtonGroup.module.scss';

const ActionButtonGroup: React.FC = () => {
  const handleStart = () => {
    location.reload();
  };

  return (
    <div className={styles.actionBtnGroup}>
      <Button type="primary" onClick={handleStart}>
        刷新
      </Button>
    </div>
  );
};

export default ActionButtonGroup;