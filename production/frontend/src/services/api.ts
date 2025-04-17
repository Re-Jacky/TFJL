import { pid } from "process";
import proxy from "./proxy";
import type { GameMode, Wnd } from "../types";
import { type ShortcutModel } from '@src/components/content/shortcut/Content';

type ScriptType = 'collab' | 'activity';
type ShortcutConfig = {
    mode?: GameMode;
    quickSell?: boolean;
};

export interface API {
    getFileList: (type: ScriptType) => Promise<{ files: string[] }>;
    readFile: (file: string, type: ScriptType) => Promise<string>;
    healthCheck: () => Promise<{ status: string }>;
    getWindows: () => Promise<{ windows: Array<Wnd>}>;
    startAction: (config: {pid: number; action: string;}) => Promise<{ status: string }>;
    saveFile: (file: string, content: string, type: ScriptType) => Promise<{ status: string }>;
    deleteFile: (file: string, type: ScriptType) => Promise<{ status: string }>;
    locateWindow: (pid: number) => Promise<{ status: string }>;
    getShortcut: () => Promise<{ shortcut: ShortcutModel }>;
    saveShortcut: (shortcut: ShortcutModel) => Promise<{ status: string }>;
    setShortcutConfig: (config: ShortcutConfig) => Promise<{ status: string }>;
    monitorShortcut: (value: boolean) => Promise<{ status: string }>;
}

export const api: API = {
    getFileList: async (type: 'collab' | 'activity') => {
        return await proxy.get(`get-file-list?type=${type}`);
    },
    readFile: async (file: string, type: ScriptType) => {
        // encode file name
        file = encodeURIComponent(file);
        return await proxy.post('read-file', { file, type });
    },
    healthCheck: async () => {
        return await proxy.get('health');
    },
    getWindows: async () => {
        return await proxy.get('windows');
    },
    startAction: async (config) => {
        return await proxy.post('start-action', config);
    },
    saveFile: async (file: string, content: string, type: ScriptType) => {
        return await proxy.post('save-file', { file, content, type });
    },
    deleteFile: async (file: string, type: ScriptType) => {
        return await proxy.post('delete-file', { file, type });
    },
    locateWindow: async (pid: number) => {
        return await proxy.post('locate-window', { pid });
    },
    getShortcut: async () => {
        return await proxy.get('shortcut');
    },
    saveShortcut: async (shortcut: ShortcutModel) => {
        return await proxy.post('shortcut', { shortcut });
    },
    setShortcutConfig: async (config: ShortcutConfig) => {
        return await proxy.post('shortcut-config', { config });
    },
    monitorShortcut: async (status: boolean) => {
        return await proxy.post('monitor-shortcut', { status });
    }
}
