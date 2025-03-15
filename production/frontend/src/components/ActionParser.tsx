import React, { useState } from 'react';
import { Upload, Button, Card, List, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import axios from 'axios';

interface Action {
  action: string;
}

const ActionParser: React.FC = () => {
  const [actions, setActions] = useState<Action[]>([]);

  const handleFileUpload = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://localhost:8000/parse-actions', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setActions(response.data.actions);
      message.success('File parsed successfully');
    } catch (error) {
      message.error('Error parsing file');
      console.error(error);
    }
  };

  return (
    <Card title="Action Parser">
      <Upload
        beforeUpload={(file) => {
          handleFileUpload(file);
          return false;
        }}
        maxCount={1}
      >
        <Button icon={<UploadOutlined />}>Upload Text File</Button>
      </Upload>

      {actions.length > 0 && (
        <List
          style={{ marginTop: '20px' }}
          header={<div>Parsed Actions</div>}
          bordered
          dataSource={actions}
          renderItem={(item) => (
            <List.Item>
              {item.action}
            </List.Item>
          )}
        />
      )}
    </Card>
  );
};

export default ActionParser;