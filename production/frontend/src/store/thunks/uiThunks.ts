import { createAsyncThunk } from '@reduxjs/toolkit';
import { api } from '@src/services/api';
import { setWindows, setActiveWindow } from '../actions';

export const getWindows = createAsyncThunk(
  'ui/getWindows',
  async (_, thunkAPI) => {
    const { dispatch } = thunkAPI;
    const {windows} = await api.getWindows();
    dispatch(setWindows(windows))
    if (windows.length > 0) {
      dispatch(setActiveWindow(windows[0].pid.toString()))
    }

    return windows;
  }
)