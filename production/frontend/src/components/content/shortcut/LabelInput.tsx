import { Input } from 'antd';
import React, { useState } from 'react';
import styles from './LabelInput.module.scss';

export interface LabelInputProps {
  label: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
}

const LabelInput: React.FC<LabelInputProps> = (props) => {
  const { label, defaultValue, onChange } = props;
  const [value, setValue] = useState(defaultValue ?? '');

  const handleBlur = (val: string) => {
    if (val === value) {
      return;
    }
    setValue(val);
  };

  return (
    <div className={styles.labelInput}>
      <span>{label}</span>
      <Input
        className={styles.inputField}
        value={value}
        onBlur={(e) => {
          handleBlur(e.target.value);
        }}
        onKeyDown={(e) => {
          let value = e.key;
          if (e.key === ' ') {
            value = 'Space';
          }
          handleBlur(value);
        }}
      />
    </div>
  );
};

export default LabelInput;
