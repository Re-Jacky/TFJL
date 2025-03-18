import React, { useState } from 'react';
import { Input, Grid } from 'antd';
import styles from './ChariotPreview.module.scss';

const { useBreakpoint } = Grid;

const ChariotPreview: React.FC = () => {
  const screens = useBreakpoint();
  const [activeCell, setActiveCell] = useState<number | null>(null);
  const [cellValues, setCellValues] = useState<string[]>(
    Array(8).fill('Cell Content')
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
        {cellValues.map((value, index) => (
          <div
            key={index}
            onDoubleClick={() => handleDoubleClick(index)}
            className={styles.cell}
          >
            {activeCell === index ? (
              <Input
                className={styles.cellInput}
                autoFocus
                defaultValue={value}
                onBlur={(e) => handleBlur(index, e.target.value)}
                onPressEnter={(e) =>
                  handleBlur(index, (e.target as HTMLInputElement).value)
                }
              />
            ) : (
              <div>{value}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ChariotPreview;
