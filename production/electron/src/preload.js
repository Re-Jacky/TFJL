const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('nodeAPI', {
    restartServer: () => {
        ipcRenderer.send('restart-server');
    }
})