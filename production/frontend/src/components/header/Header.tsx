import React from 'react';
import ChariotPreview from './ChariotPreview';
import LogMonitor from './LogMonitor';
import WindowController from './WindowController';
import ActionButtonGroup from './ActionButtonGroup';
import styles from './Header.module.scss'

const Header: React.FC = () => {
  return (
    <div className={styles.container}>
      <ChariotPreview />
      <LogMonitor />
      <WindowController />
      <ActionButtonGroup />
    </div>
  );
};
export default Header;
