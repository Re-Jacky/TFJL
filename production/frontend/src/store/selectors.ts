import sseSlice from './slices/sseSlice';
import uiSlice from './slices/uiSlice';

export const { selectSSEConnected, selectSSELastEvent } = sseSlice.selectors;
export const { selectActiveWindow, selectLogRecords, selectVehicle, selectWindows, selectInitializing } = uiSlice.selectors;
