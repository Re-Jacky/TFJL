import React from 'react';
import { Tabs, type TabsProps } from 'antd';
import styles from './TaskTabs.module.scss';
import {
  Automator,
  ShortcutContent,
} from '../content';

const items: TabsProps['items'] = [
  {
    key: 'shortcut',
    label: '快捷键',
    children: <ShortcutContent />,
  },
  {
    key: 'automator',
    label: '自动连打',
    children: <Automator />,
  },
];
const TaskTabs: React.FC = () => {
  return (
    <Tabs defaultActiveKey='main' items={items} className={styles.taskTabs} />
  );
};

export default TaskTabs;
