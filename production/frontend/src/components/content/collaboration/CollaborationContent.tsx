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
import CreateFileButton from '../components/CreateFileButton';
import DeleteFileButton from '../components/DeleteFileButton';
import { useSelector } from 'react-redux';
import { selectActiveWindow } from '@src/store/selectors';

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
  const [disableSaveBtn, setDisableSaveBtn] = useState<boolean>(true);
  const editorRef = useRef<EditorHandler | null>(null);
  const activeWindow = useSelector(selectActiveWindow);

  const onStart = () => {
    if (!selected || !activeWindow) return;
    api.startAction({ pid: parseInt(activeWindow), action: '合作助战' });
  };

  const onSave = () => {
    const content = editorRef?.current?.getContent();
    if (selected) {
      api.saveFile(selected, content || '', 'collab').then(() => {
        setInitContent(content || '');
        setDisableSaveBtn(true);
      });
    }
  };

  const onDelete = () => {
    if (selected) {
      // api.deleteFile(selected).then(() => {
      //   setSelected(options?.[0].value);
      // });
    }
  };

  const loadFiles = async () => {
    return api
      .getFileList('collab')
      .then((data) => {
        const options = data.files.map((item: any, index: number) => ({
          value: item,
          label: item,
          index,
        }));
        return options;
      })
      .catch((error) => {
        console.log(error);
      })
      .finally(() => {
        setIsLoading(false);
      });
  };

  const onCreateNewFile = async (fileName: string) => {
    const file = `${fileName}.txt`;
    await api.saveFile(file, '', 'collab');
    const options = await loadFiles();
    setOptions(options || []);
    setSelected(file);
  };

  const onDeleteFile = async () => {
    if (selected) {
      await api.deleteFile(selected, 'collab');
      const options = await loadFiles();
      setOptions(options || []);
      setSelected(options?.[0].value);
    }
  };

  const validateDuplicateFiles = (name: string) => {
    const file = `${name}.txt`;
    if (options) {
      const index = options.findIndex((item) => item.value === file);
      return index === -1;
    }
    return true;
  };

  // load file list
  useEffect(() => {
    loadFiles().then((options) => {
      if (options) {
        setOptions(options || []);
        setSelected(options[0].value);
      }
    });
  }, []);

  // get file content
  useEffect(() => {
    if (selected) {
      api
        .readFile(selected, 'collab')
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
        <div className={styles.select}>
          <Select
            showSearch={true}
            loading={loading}
            value={selected}
            onChange={setSelected}
            options={options}
            style={{ width: 200 }}
          />
          <CreateFileButton onSave={onCreateNewFile} validator={validateDuplicateFiles}/>
          <DeleteFileButton onDelete={onDeleteFile}/>
        </div>
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
        <CodeEditor
          ref={editorRef}
          value={initContent}
          height={290}
          onChange={(value) => {
            setDisableSaveBtn(value === initContent);
          }}
        />
        <Button
          type='primary'
          icon={<SaveOutlined />}
          onClick={onSave}
          disabled={disableSaveBtn}
        >
          保存
        </Button>
      </div>
    </div>
  );
};

export default CollaborationContent;
