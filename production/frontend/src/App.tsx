import React, { useState, useEffect } from 'react';
import { Layout } from 'antd';
import Header from './components/header/Header';
import TaskTabs from './components/tabs/TaskTabs';
import LoadingMask from './components/loading/LoadingMask';
import { api } from '@src/services/api';
import { useSSE } from './hooks/useSSE';
import { selectActiveWindow } from './store/selectors';
import { useAppSelector,useAppDispatch } from './store/store';

const App: React.FC = () => {
  const [initializing, setInitializing] = useState(true);
  const activeWindow = useAppSelector(selectActiveWindow)
  const { connect, disconnect } = useSSE();

  useEffect(() => {
    // Check if the API is healthy every 1 second until it is healthy
    const intervalId = setInterval(() => {
      api.healthCheck().then(() => {
        setInitializing(false);
        clearInterval(intervalId);
      }).catch(() => {
        setInitializing(true);
      });
    }, 1000);
    // Clean up the interval when the component unmounts
    return () => clearInterval(intervalId);
  }, []);

  /**
   * Set up SSE connection when the active window changes
   * and disconnect when the component unmounts.
   *
   * @param {string} activeWindow - The active window from the men
   */
  useEffect(() => {
    if (!initializing) {
      // if there's no active window, use the current timestamp as a default id, when the window is actived, the id will be updated
      connect(activeWindow ?? Date.now().toString());
    }
    return () => {
      disconnect();
    };
  }, [initializing, activeWindow]);


  /**
   * Set the active window to localStorage when the active window changes
   */
  useEffect(() => {
    if (activeWindow) {
      window.localStorage.setItem('pid', activeWindow);
    }
    return () => {
      // Clean up the localStorage when the component unmounts
      window.localStorage.removeItem('pid');
    };
  }, [activeWindow]);
  

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
