import React from 'react';
import { Layout, Menu } from 'antd';
import Header from './components/header/Header';


const App: React.FC = () => {
  return (
    <Layout style={{width: '800px', height: '600px'}}>
      <Layout>
        <Header />
        <div>tabs</div>
        <div>content</div>
      </Layout>
    </Layout>
  );
};

export default App;
