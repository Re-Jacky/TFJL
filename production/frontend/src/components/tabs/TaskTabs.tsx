import React from 'react';
import { Tabs, type TabsProps } from 'antd';
import styles from './TaskTabs.module.scss';
import {
  BattleContent,
  CollaborationContent,
  EventContent,
  MainContent,
} from '../content';

const items: TabsProps['items'] = [
  {
    key: 'main',
    label: '主页',
    children: <MainContent />,
  },
  {
    key: 'collaboration',
    label: '合作',
    children: <CollaborationContent />,
  },
  {
    key: 'battle',
    label: '对战',
    children: <BattleContent />,
  },
  {
    key: 'event',
    label: '活动',
    children: <EventContent />,
  },
];
const TaskTabs: React.FC = () => {
  return (
    <Tabs defaultActiveKey='main' items={items} className={styles.taskTabs} />
  );
};

export default TaskTabs;
