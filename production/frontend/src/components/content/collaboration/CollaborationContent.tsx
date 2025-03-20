import React, { useEffect, useState } from 'react';
import { Select, Button, Table } from 'antd';
import styles from './CollaborationContent.module.scss';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { api } from '../../../services/api';

interface DataType {
  key: string; // row number
  text: string;
}

interface FileOption {
  value: string;
  label: string;
  index: number;
}

const CollaborationContent: React.FC = () => {
  const [selected, setSelected] = useState<string>();
  const [loading, setIsLoading] = useState<boolean>(true);
  const [options, setOptions] = useState<Array<FileOption>>();

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

  // load file list
  useEffect(() => {
    api.getFileList()
      .then((data) => {
        const options = data.files.map((item: any, index: number) => ({
          value: item,
          label: item,
          index,
        }));
        setOptions(options);
        setSelected(options[0].value);
      })
      .catch((error) => {
        console.log(error);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  // get file content
  useEffect(() => {
    if (selected) {
      api.readFile(selected)
        .then((data) => {
          console.log(data);
        })
        .catch((error) => {
          console.log(error);
        });
    }
  }, [selected])

  return (
    <div className={styles.collaboration}>
      <div className={styles.header}>
        <Select
          showSearch={true}
          loading={loading}
          value={selected}
          onChange={setSelected}
          options={options}
          style={{ width: 200 }}
        />
        <div className={styles.btnGroup}>
          <Button
            type='primary'
            icon={<PlayCircleOutlined />}
            disabled={!selected}
          >
            开始
          </Button>
          <Button icon={<PauseCircleOutlined />}>暂停</Button>
          <Button danger icon={<StopOutlined />}>
            结束
          </Button>
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
