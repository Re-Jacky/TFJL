import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { build } from 'vite';


interface SSEEvent {
  type: 'log' | 'error' | 'action' | 'vehicle';
  payload: unknown;
}
export interface SSEState {
  connected: boolean;
  lastEvent: SSEEvent | null;
}

const initialState: SSEState = {
  connected: false,
  lastEvent: null,
};

const sseSlice = createSlice({
  name: 'sse',
  initialState,
  selectors: {
    selectSSEConnected: (state: SSEState) => state.connected,
    selectSSELastEvent: (state: SSEState) => state.lastEvent,
  },
  reducers: {
    setSSEConnected: (state, action: PayloadAction<boolean>) => {
      state.connected = action.payload;
    },
    setSSELastEvent: (state, action: PayloadAction<SSEEvent>) => {
      state.lastEvent = action.payload;
    },
  },
});

export default sseSlice;