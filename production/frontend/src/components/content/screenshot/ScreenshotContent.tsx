import React, { useState } from 'react';
import { Button, Image, Spin, message, Empty } from 'antd';
import { useAppSelector } from '@src/store/store';
import { selectActiveWindow } from '@src/store/selectors';
import { api } from '@src/services/api';
import styles from './ScreenshotContent.module.scss';

const ScreenshotContent: React.FC = () => {
  const activeWindow = useAppSelector(selectActiveWindow);
  const [loading, setLoading] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  const handleCapture = async () => {
    if (!activeWindow) {
      message.error('请先选择一个游戏窗口');
      return;
    }

    setLoading(true);
    try {
    const pid = parseInt(activeWindow, 10);
    const result = await api.captureScreenshot(pid);
      if (result.success && result.image) {
        setImageUrl(result.image);
        message.success('截图成功');
      } else {
        message.error(result.message || '截图失败');
      }
    } catch (error) {
      console.error('Screenshot error:', error);
      message.error('截图发生错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.screenshot}>
      <div className={styles.header}>
        <Button 
          type="primary" 
          onClick={handleCapture} 
          loading={loading}
          disabled={!activeWindow}
        >
          捕获截图
        </Button>
      </div>

      <div className={styles.content}>
        <div className={styles.imagePreview}>
          {loading ? (
            <Spin tip="正在捕获..." />
          ) : imageUrl ? (
            <Image
              src={imageUrl}
              alt="Window Screenshot"
              style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
            />
          ) : (
            <Empty description="暂无截图" />
          )}
        </div>
      </div>
    </div>
  );
};

export default ScreenshotContent;
