import { pid } from "process";
import proxy from "./proxy";
import type { Wnd } from "../types";

type ScriptType = 'collab' | 'activity';

export interface API {
    getFileList: (type: ScriptType) => Promise<{ files: string[] }>;
    readFile: (file: string, type: ScriptType) => Promise<string>;
    healthCheck: () => Promise<{ status: string }>;
    getWindows: () => Promise<{ windows: Array<Wnd>}>;
    startAction: (config: {pid: number; action: string;}) => Promise<{ status: string }>;
    saveFile: (file: string, content: string, type: ScriptType) => Promise<{ status: string }>;
    deleteFile: (file: string, type: ScriptType) => Promise<{ status: string }>;
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
}