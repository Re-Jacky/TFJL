import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { Wnd } from '@src/types';

export interface LogRecord {
  timestamp: string;
  message: string;
  level: 'info' | 'warn' | 'error';
}

export interface VehicleCell {
  card: string | undefined;
  level: number | undefined;
}
export interface Vehicle {
  side: 'left' | 'right' | undefined;
  equipment: string | undefined;
  level: number | undefined; // current level of a game
  seat: number | undefined; // 1-6, opened seats for cards
  info: {
    [key: number]: VehicleCell;
  };
}

export interface UIState {
  isInitializing: boolean;
  activeWindow: string | null;
  windows: Array<Wnd>;
  logRecords: Array<LogRecord>;
  vehicle: Vehicle;
}

const generateVehicleInfo = () => {
  const info: Vehicle['info'] = {};
  for (let i = 0; i <= 6; i++) {
    info[i] = {
      card: undefined,
      level: undefined,
    };
  }
  return info;
};

const initialState: UIState = {
  isInitializing: true,
  activeWindow: null,
  windows: [],
  logRecords: [],
  vehicle: {
    side: undefined,
    level: undefined,
    seat: undefined,
    equipment: undefined,
    info: generateVehicleInfo(),
  },
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  selectors: {
    selectActiveWindow: (state) => state.activeWindow,
    selectLogRecords: (state) => state.logRecords,
    selectVehicle: (state) => state.vehicle,
    selectWindows: (state) => state.windows,
    selectInitializing: (state) => state.isInitializing,
  },
  reducers: {
    setInitializing: (state, action: PayloadAction<boolean>) => {
      state.isInitializing = action.payload;
    },
    setActiveWindow: (state, action: PayloadAction<string | null>) => {
      state.activeWindow = action.payload;
    },
    setLogRecords: (state, action: PayloadAction<Array<LogRecord>>) => {
      state.logRecords = action.payload;
    },
    clearLogRecords: (state) => {
      state.logRecords = [];
    },
    updateLogRecords: (state, action: PayloadAction<LogRecord>) => {
      state.logRecords.push(action.payload);
    },
    setVehicle: (state, action: PayloadAction<Vehicle>) => {
      state.vehicle = action.payload;
    },
    setWindows: (state, action: PayloadAction<Array<Wnd>>) => {
      state.windows = action.payload;
    },
  },
});

export default uiSlice;
