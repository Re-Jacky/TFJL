import React, { useState, useMemo } from 'react';
import { Input, Grid } from 'antd';
import styles from './VehiclePreview.module.scss';
import { selectVehicle } from '@src/store/selectors';
import { useAppDispatch, useAppSelector } from '@src/store/store';
import { VehicleCell } from '@src/store/slices/uiSlice';
import { setVehicle } from '@src/store/actions';

const { useBreakpoint } = Grid;

const VehiclePreview: React.FC = () => {
  const screens = useBreakpoint();
  const [activeCell, setActiveCell] = useState<number | null>(null);
  const dispatch = useAppDispatch();
  const vehicleInfo = useAppSelector(selectVehicle);
  const cellValues = useMemo(() => {
    return Object.entries(vehicleInfo.info)
      .sort((a, b) => {
        return parseInt(a[0]) - parseInt(b[0]);
      })
      .map((item) => item[1]);
  }, [vehicleInfo]);

  const handleDoubleClick = (index: number) => {
    setActiveCell(index);
  };

  const handleBlur = (index: number, value: string) => {
    const match = value.match(/(.+?)\s*(\d+)/);
    dispatch(setVehicle({
      ...vehicleInfo,
      info: {
        ...vehicleInfo.info,
        [index]: {
          card: match? match[1] : '',
          level: match? parseInt(match[2]) : 0,
        },
      },
    }));
    setActiveCell(null);
  };
  const getCellDisplayName = (cell: VehicleCell) => {
    return cell.card ? `${cell.card} ${cell.level}` : '';
  };
  return (
    <div className={styles.chariotContainer}>
      <div
        className={`${styles.gridContainer} ${screens.xs ? styles.xs : styles.lg}`}
      >
        {[...cellValues].reverse().map((cell, index) => (
          <div
            key={index}
            onDoubleClick={() =>
              handleDoubleClick(cellValues.length - 1 - index)
            }
            className={styles.cell}
            style={{ gridArea: `cell${cellValues.length - 1 - index}` }}
          >
            {activeCell === cellValues.length - 1 - index ? (
              <Input
                className={styles.cellInput}
                autoFocus
                defaultValue={getCellDisplayName(cell)}
                onBlur={(e) =>
                  handleBlur(cellValues.length - 1 - index, e.target.value)
                }
                onPressEnter={(e) =>
                  handleBlur(
                    cellValues.length - 1 - index,
                    (e.target as HTMLInputElement).value
                  )
                }
              />
            ) : (
              <div>{getCellDisplayName(cell) || '(空)'}</div>
            )}
          </div>
        ))}
      </div>
      <div className={styles.footer}>
        <span>
          装备:{' '}
          <b className={styles.footerText}>{vehicleInfo.equipment || ''}</b>
        </span>
        <span>
          第<a className={styles.footerText}>{vehicleInfo.level || 0}</a>关
        </span>
      </div>
    </div>
  );
};

export default VehiclePreview;
