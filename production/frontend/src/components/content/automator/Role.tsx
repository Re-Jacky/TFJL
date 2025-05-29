import React, {
  useMemo,
  useState,
  forwardRef,
  useImperativeHandle,
  useEffect,
} from 'react';
import { Select } from 'antd';
import { useSelector } from 'react-redux';
import { selectGameWindows, selectToolWIndows } from '@src/store/selectors';
import styles from './Role.module.scss';

export interface RoleProps {
  role: string;
  onValidChange?: (valid: boolean) => void;
  defaultSelectedIndex?: number;
}

export interface RoleHandler {
  getSelectedWindow: () => {
    game: number;
    tool: number;
  };
}

const Role: React.ForwardRefRenderFunction<RoleHandler, RoleProps> = (
  props,
  ref
) => {
  const { role, onValidChange, defaultSelectedIndex } = props;
  const gameWindows = useSelector(selectGameWindows);
  const toolWindows = useSelector(selectToolWIndows);
  const [selectedWindow, setSelectedWindow] = useState<{
    game: string;
    tool: string;
  }>({ game: '', tool: '' });
  const gameOptions = useMemo(
    () =>
      gameWindows.map((item, index) => ({
        label: `游戏-${index}`,
        value: item.pid.toString(),
      })),
    [gameWindows]
  );
  const toolOptions = useMemo(
    () =>
      toolWindows.map((item, index) => ({
        label: `老马-${index}`,
        value: item.pid.toString(),
      })),
    [toolWindows]
  );

  const onSelectedChange = (key: 'tool' | 'game') => (value: string) => {
    const newSelectedWindow = {
      ...selectedWindow,
      [key]: value,
    };
    setSelectedWindow(newSelectedWindow);
    onValidChange?.(
      newSelectedWindow.game !== '' && newSelectedWindow.tool !== ''
    );
  };

  useImperativeHandle(ref, () => ({
    getSelectedWindow: () => ({ game: parseInt(selectedWindow.game), tool: parseInt(selectedWindow.tool) }),
  }));

  useEffect(() => {
    if (gameWindows.length > 1 && toolWindows.length > 1 && defaultSelectedIndex !== undefined) {
      setSelectedWindow({
        game: gameWindows[defaultSelectedIndex].pid.toString(),
        tool: toolWindows[defaultSelectedIndex].pid.toString(),
      })
    }
  }, [defaultSelectedIndex, gameWindows, toolWindows])

  return (
    <div className={styles.automatorRole}>
      <span>{role}</span>
      <Select
        className={styles.select}
        placeholder='游戏窗口'
        options={gameOptions}
        onChange={onSelectedChange('game')}
        value={selectedWindow.game}
      />
      <Select
        className={styles.select}
        placeholder='老马窗口'
        options={toolOptions}
        onChange={onSelectedChange('tool')}
        value={selectedWindow.tool}
      />
    </div>
  );
};

export default forwardRef(Role);
