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
            value = 'space';
          } else if (e.key === 'Escape') {
            value = 'esc';
          } else if (e.key === 'Enter') {
            value = 'enter';
          } else if (e.key === 'Tab') {
            value = 'tab';
          } else if (e.key === 'Backspace') {
            value = 'backspace';
          } else if (e.key === 'ArrowUp') {
            value = 'up';
          } else if (e.key === 'ArrowDown') {
            value = 'down';
          } else if (e.key === 'ArrowLeft') {
            value = 'left';
          } else if (e.key === 'ArrowRight') {
            value = 'right';
          }
          handleBlur(value);
        }}
      />
    </div>
  );
};

export default LabelInput;
