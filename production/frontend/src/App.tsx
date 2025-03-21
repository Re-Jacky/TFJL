import React, { useState, useEffect } from 'react';
import { Layout } from 'antd';
import Header from './components/header/Header';
import TaskTabs from './components/tabs/TaskTabs';
import LoadingMask from './components/loading/LoadingMask';
import { api } from '@src/services/api';

const App: React.FC = () => {
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    api.healthCheck().then(() => {
      setInitializing(false);
    }).catch(() => {
      setInitializing(true);
    });
  }, []);

  return (
    <Layout
      style={{
        width: '800px',
        height: '600px',
        fontSize: '12px',
        position: 'relative',
      }}
    >
      <LoadingMask visible={initializing} />
      <Header />
      <TaskTabs />
    </Layout>
  );
};

export default App;
