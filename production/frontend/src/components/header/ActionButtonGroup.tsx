import React from 'react';
import { Button } from 'antd';
import styles from './ActionButtonGroup.module.scss';
import { api } from '@src/services/api';
import { useSelector } from 'react-redux';
import { selectActiveWindow } from '@src/store/selectors';

const ActionButtonGroup: React.FC = () => {
  const activeWindow = useSelector(selectActiveWindow)
  const handleStart = () => {
    if (activeWindow) {
      api.startAction({
        pid: parseInt(activeWindow),
        action: '合作助战',
      })
    }
    
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