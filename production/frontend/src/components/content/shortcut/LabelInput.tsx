import { Input } from 'antd';
import React, { useState } from 'react';
import { CloseCircleFilled } from '@ant-design/icons';
import styles from './LabelInput.module.scss';

export interface LabelInputProps {
  className?: string;
  label: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
  value?: string;
}

const LabelInput: React.FC<LabelInputProps> = (props) => {
  const { label, defaultValue, onChange, className, value } = props;
  const [internalValue, setInternalValue] = useState(defaultValue ?? '');

  const displayValue = value ?? internalValue;

  const handleBlur = (val: string) => {
    if (val === displayValue) {
      return;
    }
    setInternalValue(val);
    onChange && onChange(val);
  };

  const onClear = () => {
    setInternalValue('');
    onChange && onChange('');
  };

  return (
    <div className={`${styles.labelInput} ${className || ''}`}>
      <span>{label}</span>
      <Input
        className={styles.inputField}
        value={displayValue}
        allowClear={{
          clearIcon: <CloseCircleFilled className={styles.inputClearIcon} />,
        }}
        onBlur={(e) => {
          handleBlur(e.target.value);
        }}
        onClear={onClear}
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
