import React from 'react';
import { Select, Button, Space } from 'antd';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import styles from './ImageBrowser.module.scss';

interface ImageBrowserProps {
  files: string[];
  selectedIndex: number;
  // eslint-disable-next-line no-unused-vars
  onSelectFile: (index: number) => void;
  onPrevious: () => void;
  onNext: () => void;
  disabled?: boolean;
}

const ImageBrowser: React.FC<ImageBrowserProps> = ({
  files,
  selectedIndex,
  onSelectFile,
  onPrevious,
  onNext,
  disabled = false,
}) => {
  const handleDropdownChange = (value: string) => {
    const index = files.indexOf(value);
    if (index !== -1) {
      onSelectFile(index);
    }
  };

  return (
    <div className={styles.imageBrowser}>
      <div className={styles.selectWrapper}>
        <Select
          value={files[selectedIndex]}
          onChange={handleDropdownChange}
          style={{ width: '100%' }}
          placeholder='选择截图'
          disabled={disabled || files.length === 0}
          showSearch
          filterOption={(input, option) =>
            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
          }
          options={files.map((file) => ({ label: file, value: file }))}
        />
      </div>
      <div className={styles.navigationWrapper}>
        <Button
          icon={<LeftOutlined />}
          onClick={onPrevious}
          disabled={disabled || selectedIndex === 0}
          size='small'
        >
          上一张
        </Button>
        <span className={styles.counter}>
          {files.length > 0
            ? `${selectedIndex + 1} / ${files.length}`
            : '0 / 0'}
        </span>
        <Button
          icon={<RightOutlined />}
          onClick={onNext}
          disabled={disabled || selectedIndex >= files.length - 1}
          size='small'
        >
          下一张
        </Button>
      </div>
    </div>
  );
};

export default ImageBrowser;
