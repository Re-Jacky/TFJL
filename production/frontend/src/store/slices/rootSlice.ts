import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface rootState {
  activeWindow: null | string;
}

const initialState: rootState = {
  activeWindow: null,
};

export const rootSlice = createSlice({
  name: 'root',
  initialState,
  reducers: {
    setActiveWindow: (state, action: PayloadAction<string>) => {
      state.activeWindow = action.payload;
    },
  },
});

export const { setActiveWindow } = rootSlice.actions;
export default rootSlice.reducer;