import proxy from "./proxy";

export interface API {
    getFileList: () => Promise<{ files: string[] }>;
    readFile: (file: string) => Promise<string>;
    healthCheck: () => Promise<{ status: string }>;
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
}