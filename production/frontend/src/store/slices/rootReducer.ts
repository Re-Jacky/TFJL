import { combineReducers, createSlice, PayloadAction } from '@reduxjs/toolkit';
import uiSlice, { UIState } from './uiSlice';
import sseSlice, { SSEState } from './sseSlice';

export interface RootState {
  [uiSlice.name]: UIState;
  [sseSlice.name]: SSEState;
}

const rootReducer = combineReducers({
  [uiSlice.name]: uiSlice.reducer,
  [sseSlice.name]: sseSlice.reducer,
})

export default rootReducer;
