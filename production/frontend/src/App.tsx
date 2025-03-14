import React from 'react';
import { Layout, Menu } from 'antd';
import { Routes, Route, Link } from 'react-router-dom';
import ImageComparison from './components/ImageComparison';
import WindowControl from './components/WindowControl';
import ActionParser from './components/ActionParser';

const { Header, Content, Sider } = Layout;

const App: React.FC = () => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#fff', padding: 0 }}>
        <div style={{ padding: '0 24px' }}>
          <h1>Task Automation Tool</h1>
        </div>
      </Header>
      <Layout>
        <Sider width={200} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            defaultSelectedKeys={['1']}
            style={{ height: '100%', borderRight: 0 }}
          >
            <Menu.Item key="1">
              <Link to="/image-comparison">Image Comparison</Link>
            </Menu.Item>
            <Menu.Item key="2">
              <Link to="/window-control">Window Control</Link>
            </Menu.Item>
            <Menu.Item key="3">
              <Link to="/action-parser">Action Parser</Link>
            </Menu.Item>
          </Menu>
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content style={{ background: '#fff', padding: 24, margin: 0, minHeight: 280 }}>
            <Routes>
              <Route path="/image-comparison" element={<ImageComparison />} />
              <Route path="/window-control" element={<WindowControl />} />
              <Route path="/action-parser" element={<ActionParser />} />
              <Route path="/" element={<ImageComparison />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default App;