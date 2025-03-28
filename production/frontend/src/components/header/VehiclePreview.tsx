import React, { useState } from 'react';
import { Input, Grid } from 'antd';
import styles from './VehiclePreview.module.scss';

const { useBreakpoint } = Grid;

const VehiclePreview: React.FC = () => {
  
  const screens = useBreakpoint();
  const [activeCell, setActiveCell] = useState<number | null>(null);
  const [cellValues, setCellValues] = useState<string[]>(
    Array(7).fill('Cell Content')
  );

  const handleDoubleClick = (index: number) => {
    setActiveCell(index);
  };

  const handleBlur = (index: number, value: string) => {
    const newValues = [...cellValues];
    newValues[index] = value;
    setCellValues(newValues);
    setActiveCell(null);
  };

  return (
    <div className={styles.chariotContainer}>
      <div
        className={`${styles.gridContainer} ${screens.xs ? styles.xs : styles.lg}`}
      >
        {[...cellValues].reverse().map((value, index) => (
          <div
            key={index}
            onDoubleClick={() => handleDoubleClick(cellValues.length - 1 - index)}
            className={styles.cell}
            style={{ gridArea: `cell${cellValues.length - 1 - index}` }}
          >
            {activeCell === cellValues.length - 1 - index ? (
              <Input
                className={styles.cellInput}
                autoFocus
                defaultValue={value}
                onBlur={(e) => handleBlur(cellValues.length - 1 - index, e.target.value)}
                onPressEnter={(e) =>
                  handleBlur(cellValues.length - 1 - index, (e.target as HTMLInputElement).value)
                }
              />
            ) : (
              <div>{value}</div>
            )}
          </div>
        ))}
      </div>
      <div className={styles.footer}>
        <span>装备: <b className={styles.footerText}>强袭</b></span>
        <span>第<a className={styles.footerText}>123</a>关</span>
      </div>
    </div>
  );
};

export default VehiclePreview;
