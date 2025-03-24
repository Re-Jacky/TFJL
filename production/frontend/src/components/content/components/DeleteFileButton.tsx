import React from 'react';
import { Popconfirm, Button } from 'antd';
import { MinusOutlined } from '@ant-design/icons';

export interface DeleteFileButtonProps {
  disabled?: boolean;
  onDelete?: () => void;
}
const DeleteFileButton: React.FC <DeleteFileButtonProps> = (props) => {
  const { disabled, onDelete } = props;
  return (
    <Popconfirm
      title={'删除文件'}
      onConfirm={onDelete}
      okText='是'
      cancelText='否'
    >
      <Button
        danger
        shape='circle'
        icon={<MinusOutlined />}
        size={'small'}
        disabled={disabled}
      />
    </Popconfirm>
  );
};

export default DeleteFileButton;
