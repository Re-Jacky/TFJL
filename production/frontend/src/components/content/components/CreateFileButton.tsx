import React, { ChangeEvent, ChangeEventHandler, useState } from 'react';
import { Popover, Button, Input } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { b } from 'vite/dist/node/types.d-aGj9QkWt';

export interface CreateFileButtonProps {
  validator?: (value: string) => boolean;
  onSave?: (fileName: string) => void;
}

const CreateFileButton: React.FC<CreateFileButtonProps> = (props) => {
  const { validator, onSave } = props;
  const [open, setOpen] = useState(false);
  const [fileName, setFileName] = useState('');
  const [disableSave, setDisableSave] = useState<boolean>(true);

  const handleOpenChange = (open: boolean) => {
    setOpen(open);
  };

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFileName(e.target.value);
    if (validator) {
        setDisableSave(!validator(e.target.value));
    }
  };

  const getContent = () => {
    return (
      <>
        <Input
          placeholder='输入文件名'
          suffix={'.txt'}
          onChange={onChange}
        ></Input>
        <Button onClick={() => onSave?.(fileName)} disabled={disableSave}>确认</Button>
      </>
    );
  };

  return (
    <Popover
      content={getContent()}
      title='新建文件'
      trigger='click'
      open={open}
      onOpenChange={handleOpenChange}
    >
      <Button
        shape='circle'
        color='primary'
        icon={<PlusOutlined />}
        size={'small'}
        variant='outlined'
      />
    </Popover>
  );
};

export default CreateFileButton;
