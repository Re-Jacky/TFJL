import React from 'react';
import { Select, Button, Space } from 'antd';
import styles from './CropLabeler.module.scss';

interface CropLabelerProps {
  crops: string[]; // Base64 image URLs
  labels: string[]; // Card names for each crop
  cardNames: string[]; // Available card names
  onLabelsChange: (labels: string[]) => void; // eslint-disable-line no-unused-vars
  onSave: () => void;
  onCancel: () => void;
  saving?: boolean;
}

const CropLabeler: React.FC<CropLabelerProps> = ({
  crops,
  labels,
  cardNames,
  onLabelsChange,
  onSave,
  onCancel,
  saving = false,
}) => {
  const handleLabelChange = (index: number, value: string) => {
    const newLabels = [...labels];
    newLabels[index] = value;
    onLabelsChange(newLabels);
  };

  const allLabeled = labels.every((label) => label.trim() !== '');

  return (
    <div className={styles.cropLabeler}>
      <div className={styles.header}>
        <h4>批量标注 ({crops.length} 张卡牌)</h4>
        <p className={styles.hint}>为每张卡牌选择名称后保存</p>
      </div>

      <div className={styles.cropsGrid}>
        {crops.map((cropUrl, index) => (
          <div key={index} className={styles.cropItem}>
            <div className={styles.cropImageContainer}>
              <img
                src={cropUrl}
                alt={`Crop ${index + 1}`}
                className={styles.cropImage}
              />
              <div className={styles.cropNumber}>{index + 1}</div>
            </div>
            <Select
              value={labels[index] || undefined}
              onChange={(value) => handleLabelChange(index, value)}
              style={{ width: '100%' }}
              placeholder='选择卡牌'
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '')
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
              options={cardNames.map((name) => ({ label: name, value: name }))}
              status={labels[index] ? undefined : 'warning'}
            />
          </div>
        ))}
      </div>

      <div className={styles.actions}>
        <Space>
          <Button onClick={onCancel} disabled={saving}>
            取消
          </Button>
          <Button
            type='primary'
            onClick={onSave}
            disabled={!allLabeled || saving}
            loading={saving}
          >
            保存标注
          </Button>
        </Space>
        {!allLabeled && (
          <span className={styles.warning}>请为所有卡牌选择标签</span>
        )}
      </div>
    </div>
  );
};

export default CropLabeler;
