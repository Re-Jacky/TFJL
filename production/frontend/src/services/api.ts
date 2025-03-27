import { pid } from "process";
import proxy from "./proxy";

export type Wnd = {
    title: string;
    pid: number;
}
export interface API {
    getFileList: () => Promise<{ files: string[] }>;
    readFile: (file: string) => Promise<string>;
    healthCheck: () => Promise<{ status: string }>;
    getWindows: () => Promise<{ windows: Array<Wnd>}>;
    startAction: (config: {pid: number; action: string;}) => Promise<{ status: string }>;
    saveFile: (file: string, content: string) => Promise<{ status: string }>;
    deleteFile: (file: string) => Promise<{ status: string }>;
}

export const api: API = {
    getFileList: async () => {
        return await proxy.get('get-file-list');
    },
    readFile: async (file: string) => {
        // encode file name
        file = encodeURIComponent(file);
        return await proxy.post('read-file', { file });
    },
    healthCheck: async () => {
        return await proxy.get('health');
    },
    getWindows: async () => {
        // return await proxy.get('windows');
        return {windows: [{title: 'test', pid: 1}, {title: 'test2', pid: 2}]}
    },
    startAction: async (config) => {
        return await proxy.post('start-action', config);
    },
    saveFile: async (file: string, content: string) => {
        return await proxy.post('save-file', { file, content });
    },
    deleteFile: async (file: string) => {
        return await proxy.post('delete-file', { file });
    },
}