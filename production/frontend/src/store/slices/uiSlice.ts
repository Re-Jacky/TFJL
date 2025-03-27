import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface LogRecord {
  timestamp: string;
  message: string;
  level: 'info' | 'warn' | 'error';
}

export interface Vehicle {
  side: 'left' | 'right' | undefined;
  info: {
    [key: number] : {
      card: string | undefined;
      level: number | undefined;
    }
  };
}

export interface UIState {
    activeWindow: string | null;
    logRecords: Array<LogRecord>;
    vehicle: Vehicle;
}

const generateVehicleInfo = () => {
  const info: Vehicle['info'] = {};
  for (let i = 1; i <= 7; i++) {
    info[i] = {
      card: undefined,
      level: undefined,
    };
  }
  return info;
};

const initialState: UIState = {
  activeWindow: null,
  logRecords: [],
  vehicle: {
    side: undefined,
    info: generateVehicleInfo()
  }
}

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  selectors: {
    selectActiveWindow: (state) => state.activeWindow,
    selectLogRecords: (state) => state.logRecords,
    selectVehicle: (state) => state.vehicle,
  },
  reducers: {
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
  },
});

export default uiSlice;