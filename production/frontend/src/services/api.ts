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
        return await proxy.get('windows');
    },
    startAction: async (config) => {
        return await proxy.post('start-action', config);
    },
}