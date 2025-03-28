import React from 'react';
import { Button } from 'antd';
import styles from './ActionButtonGroup.module.scss';

const ActionButtonGroup: React.FC = () => {
  const handleStart = () => {

  };

  const handleEnd = () => {
    console.log('结束操作');
  };

  return (
    <div className={styles.actionBtnGroup}>
      <Button type="primary" onClick={handleStart}>
        开始
      </Button>
      <Button type="default" onClick={handleEnd}>
        结束
      </Button>
    </div>
  );
};

export default ActionButtonGroup;