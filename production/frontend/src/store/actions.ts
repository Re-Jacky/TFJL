import sseSlice from "./slices/sseSlice";
import uiSlice from "./slices/uiSlice";

export const { setSSEConnected, setSSELastEvent } = sseSlice.actions;
export const { setActiveWindow, setLogRecords, setVehicle , clearLogRecords, updateLogRecords} = uiSlice.actions;