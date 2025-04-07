import React, { useEffect, useMemo, useState } from 'react';
import { Input } from 'antd';
import styles from './Vehicle.module.scss';

type CellValues = {
  [idx: number]: string;
};
interface VehicleProps {
  defaultCellValues?: CellValues;
  active?: boolean;
  onChange?: (cellValues: CellValues) => void;
  label?: string;
}

const emptyCellValues: CellValues = Array.from({ length: 7 }).reduce((acc: CellValues, _, index) => {
  acc[index] = '';
  return acc;
}, {});

const Vehicle: React.FC<VehicleProps> = (props) => {
  const { defaultCellValues, active, onChange, label } = props;
  const [cellValues, setCellValues] = useState<CellValues>(defaultCellValues ?? emptyCellValues);
  const errorCellIdxs: string[] = useMemo(() => {
   const temp: Record<string, any> = {};
   Object.entries(cellValues).forEach(([index, value]) => {
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
  }, [cellValues])

  const handleBlur = (index: number, value: string) => {
    if (cellValues[index] === value) {
      return;
    }
    const newCellValues = { ...cellValues };
    newCellValues[index] = value;
    setCellValues(newCellValues);
  };

  useEffect(() => {
    onChange?.(cellValues);
  }, [cellValues])

  return (
    <div className={styles.vehicle}>
     <div className={`${styles.gridContainer} ${active ? styles.active : ''}`}>
      {Object.keys(cellValues).sort().map((key: string) => {
        const displayIdx = Object.keys(cellValues).length - 1 - parseInt(key);
        return (
          <div
            key={displayIdx}
            className={styles.cell}
            style={{ gridArea: `cell${key}` }}
          >
            <Input
              className={styles.cellInput}
              status={errorCellIdxs.includes(key) ? 'error' : undefined}
              autoFocus
              value={cellValues[parseInt(key)]}
              onBlur={(e) => handleBlur(parseInt(key), e.target.value)}
              onKeyDown={(e) => {
                let value = e.key;
                if (e.key === ' ') {
                    value = 'Space'
                }
                handleBlur(parseInt(key), value);
              }}
            />
          </div>
        );
      })}
      </div>
      {label && <div className={`${styles.label} ${active ? styles.labelActive : ''}`}>{label}</div>}
    </div>
  );
};

export default Vehicle;
