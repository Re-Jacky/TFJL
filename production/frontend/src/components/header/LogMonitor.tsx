import React, { useEffect, useRef } from 'react';
import { Card, List } from 'antd';
import styles from './LogMonitor.module.scss';
import { useAppSelector } from '@src/store/store';
import { selectLogRecords } from '@src/store/selectors';

const LogMonitor: React.FC = () => {
  const logRecords = useAppSelector(selectLogRecords)
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [logRecords]);

  return (
    <Card className={styles.logMonitor}>
      <List
        ref={listRef}
        dataSource={logRecords}
        renderItem={(log) => (
          <List.Item className={styles.listItem}>
            <div className={styles.logItem}>
              <span className={styles.timestamp}>
                {log.timestamp}
              </span>
              <span className={styles[`logLevel--${log.level}`]}>
                {log.message}
              </span>
            </div>
          </List.Item>
        )}
      />
    </Card>
  );
};

export default LogMonitor;