import React, { useEffect, useRef, useState } from 'react';
import { Select, Button } from 'antd';
import styles from './CollaborationContent.module.scss';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { api } from '@src/services/api';
import CodeEditor, {
  type EditorHandler,
} from '@src/components/editor/CodeEditor';

interface FileOption {
  value: string;
  label: string;
  index: number;
}

const CollaborationContent: React.FC = () => {
  const [selected, setSelected] = useState<string>();
  const [loading, setIsLoading] = useState<boolean>(true);
  const [options, setOptions] = useState<Array<FileOption>>();
  const [initContent, setInitContent] = useState('');
  const ref = useRef<EditorHandler | null>(null);

  const onStart = () => {
    if (!selected) return;
    api.startAction({pid:198586, action: '合作助战'})
  };

  // load file list
  useEffect(() => {
    api
      .getFileList()
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
      api
        .readFile(selected)
        .then((data) => {
          setInitContent(data);
        })
        .catch((error) => {
          console.log(error);
        });
    }
  }, [selected]);

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
            onClick={onStart}
          >
            开始
          </Button>
          <Button icon={<PauseCircleOutlined />}>暂停</Button>
          <Button danger icon={<StopOutlined />}>
            结束
          </Button>
        </div>
      </div>
      <div className={styles.scriptSection}>
        <CodeEditor ref={ref} value={initContent} height={290}/>
        <Button type='primary' icon={<SaveOutlined />}>
          保存
        </Button>
      </div>
    </div>
  );
};

export default CollaborationContent;
