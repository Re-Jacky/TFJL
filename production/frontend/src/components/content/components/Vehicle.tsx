import React, { useEffect, useMemo, useState } from 'react';
import { Input } from 'antd';
import styles from './Vehicle.module.scss';
import {CloseCircleFilled} from '@ant-design/icons';

export type CellValues = {
  [idx: number]: string;
};
interface VehicleProps {
  defaultCellValues?: CellValues;
  value?: CellValues;
  active?: boolean;
  onChange?: (cellValues: CellValues) => void;
  label?: string;
  onClick?: () => void;
}

export const produceEmptyCellValues = () => Array.from({ length: 7 }).reduce(
  (acc: CellValues, _, index) => {
    acc[index] = '';
    return acc;
  },
  {}
);

const Vehicle: React.FC<VehicleProps> = (props) => {
  const { defaultCellValues, active, onChange, label, onClick, value } = props;
  const [cellValues, setCellValues] = useState<CellValues>(
    defaultCellValues ?? produceEmptyCellValues()
  );
  const displayValues = value ?? cellValues;
  const errorCellIdxs: string[] = useMemo(() => {
    const temp: Record<string, any> = {};
    Object.entries(displayValues).forEach(([index, value]) => {
      if (!!value && !temp[value]) {
        temp[value] = [];
      }
      !!value && temp[value].push(index);
    });
    return Object.values(temp).reduce((acc: string[], curr: string[]) => {
      if (curr.length > 1) {
        acc.push(...curr);
      }
      return acc;
    }, []);
  }, [displayValues]);

  const handleBlur = (index: number, value: string) => {
    if (displayValues[index] === value) {
      return;
    }
    const newCellValues = { ...displayValues };
    newCellValues[index] = value;
    setCellValues(newCellValues);
  };

  const handleClear = (index: number) => {
    // only handle the clear event
    const newCellValues = {...displayValues };
    newCellValues[index] = '';
    setCellValues(newCellValues);
  }

  useEffect(() => {
    onChange?.(cellValues);
  }, [cellValues]);

  return (
    <div className={styles.vehicle} onClick={onClick}>
      <div className={`${styles.gridContainer} ${active ? styles.active : ''}`}>
        {Object.keys(displayValues)
          .sort()
          .map((key: string) => {
            const displayIdx =
              Object.keys(displayValues).length - 1 - parseInt(key);
            
            return (
              <div
                key={displayIdx}
                className={styles.cell}
                style={{ gridArea: `cell${key}` }}
              >
                <Input
                  className={styles.cellInput}
                  status={errorCellIdxs.includes(key) ? 'error' : undefined}
                  value={displayValues[parseInt(key)]}
                  onBlur={(e) => handleBlur(parseInt(key), e.target.value)}
                  allowClear={{clearIcon: <CloseCircleFilled className={styles.inputClearIcon}/>}}
                  onClear={() => {
                    handleClear(parseInt(key));
                  }}
                  onKeyDown={(e) => {
                    let value = e.key;
                    if (e.key === ' ') {
                      value = 'Space';
                    }
                    handleBlur(parseInt(key), value);
                  }}
                />
              </div>
            );
          })}
      </div>
      {label && (
        <div className={`${styles.label} ${active ? styles.labelActive : ''}`}>
          {label}
        </div>
      )}
    </div>
  );
};

export default Vehicle;
