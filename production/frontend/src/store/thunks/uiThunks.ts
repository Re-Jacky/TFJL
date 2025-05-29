import { createAsyncThunk } from '@reduxjs/toolkit';
import { api } from '@src/services/api';
import { setGameWindows, setActiveWindow, setToolWindows } from '../actions';

export const getGameWindows = createAsyncThunk(
  'ui/getGameWindows',
  async (_, thunkAPI) => {
    const { dispatch } = thunkAPI;
    const {windows} = await api.getGameWindows();
    dispatch(setGameWindows(windows))
    if (windows.length > 0) {
      dispatch(setActiveWindow(windows[0].pid.toString()))
    }

    return windows;
  }
)

export const getToolWindows = createAsyncThunk(
  'ui/getToolWindows',
  async (_, thunkAPI) => {
    const { dispatch } = thunkAPI;
    const {windows} = await api.getToolWindows();
    dispatch(setToolWindows(windows))
    return windows;
  }
)