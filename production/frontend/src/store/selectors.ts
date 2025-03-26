import { RootState } from './index';

export const selectActiveWindow = (state: RootState): string | null => state.root.activeWindow;