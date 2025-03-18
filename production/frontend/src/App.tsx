import React from 'react';
import { Layout } from 'antd';
import Header from './components/header/Header';
import TaskTabs from './components/tabs/TaskTabs';

const App: React.FC = () => {
  return (
    <Layout style={{ width: '800px', height: '600px', fontSize: '12px' }}>
      <Header />
      <TaskTabs />
    </Layout>
  );
};

export default App;
