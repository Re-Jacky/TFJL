import React, { useState } from 'react';
import { Select, Button, Table } from 'antd';
import styles from './CollaborationContent.module.scss';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';

interface DataType {
  key: string; // row number
  text: string;
}

const CollaborationContent: React.FC = () => {
  const [selectedOption, setSelectedOption] = useState<string>('option1');

  const options = [
    { value: 'option1', label: 'Option 1' },
    { value: 'option2', label: 'Option 2' },
    { value: 'option3', label: 'Option 3' },
  ];

  const data: DataType[] = [
    { key: '1', text: 'Sample text 1' },
    { key: '2', text: 'Sample text 2' },
    { key: '3', text: 'Sample text 3' },
  ];

  const columns = [
    {
      title: 'Text',
      dataIndex: 'key',
      key: 0,
    },
    {
      title: 'Timestamp',
      dataIndex: 'text',
      key: 1,
    },
  ];

  return (
    <div className={styles.collaboration}>
      <div className={styles.header}>
        <Select
          value={selectedOption}
          onChange={setSelectedOption}
          options={options}
          style={{ width: 200 }}
        />
        <div className={styles.btnGroup}>
          <Button type='primary' icon={<PlayCircleOutlined />}>
            开始
          </Button>
          <Button icon={<PauseCircleOutlined />}>暂停</Button>
          <Button danger icon={<StopOutlined />}>结束</Button>
        </div>
      </div>
      <Table
        columns={columns}
        dataSource={data}
        pagination={{ pageSize: 10 }}
      />
    </div>
  );
};

export default CollaborationContent;
