import React from 'react';
import { Card, List } from 'antd';
import styles from './LogMonitor.module.scss';

interface LogEntry {
  timestamp: string;
  message: string;
  level: 'info' | 'warn' | 'error';
}

const LogMonitor: React.FC = () => {
  // Mock log data
  const logs: LogEntry[] = [
    {
      timestamp: new Date().toLocaleTimeString(),
      message: 'System initialized',
      level: 'info'
    },
    {
      timestamp: new Date().toLocaleTimeString(),
      message: 'Warning: Low memory',
      level: 'warn'
    }
  ];

  return (
    <Card className={styles.logMonitor}>
      <List
        dataSource={logs}
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