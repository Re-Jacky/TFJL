import React, { useState } from 'react';
import { Input, Button, Card, Space, message } from 'antd';
import axios from 'axios';

const WindowControl: React.FC = () => {
  const [windowTitle, setWindowTitle] = useState('');

  const handleWindowAction = async (action: string) => {
    if (!windowTitle) {
      message.error('Please enter a window title');
      return;
    }

    try {
      const response = await axios.post('http://localhost:8000/window-control', {
        window_title: windowTitle,
        action: action
      });

      if (response.data.success) {
        message.success(`Window ${action} successful`);
      } else {
        message.error(response.data.error);
      }
    } catch (error) {
      message.error('Error controlling window');
      console.error(error);
    }
  };

  return (
    <Card title="Window Control">
      <Space direction="vertical" style={{ width: '100%' }}>
        <Input
          placeholder="Enter window title"
          value={windowTitle}
          onChange={(e) => setWindowTitle(e.target.value)}
        />
        <Space>
          <Button onClick={() => handleWindowAction('minimize')}>
            Minimize Window
          </Button>
          <Button onClick={() => handleWindowAction('maximize')}>
            Maximize Window
          </Button>
          <Button onClick={() => handleWindowAction('restore')}>
            Restore Window
          </Button>
        </Space>
      </Space>
    </Card>
  );
};

export default WindowControl;