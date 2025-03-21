import React from 'react';
import { Spin } from 'antd';
import styles from './LoadingMask.module.css';

interface LoadingMaskProps {
  visible: boolean;
  tip?: string;
}

const LoadingMask: React.FC<LoadingMaskProps> = ({ visible, tip = ' 初始化...' }) => {
  if (!visible) return null;

  return (
    <div className={styles.container}>
      <Spin size="large" tip={tip} />
    </div>
  );
};

export default LoadingMask;