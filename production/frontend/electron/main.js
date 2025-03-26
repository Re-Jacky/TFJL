const { app, BrowserWindow, globalShortcut } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const logger = require('./logger');
const net = require('net');
const isDev = process.env.NODE_ENV === 'development' || !fs.existsSync(path.join(__dirname, '../dist/index.html'));

// Disable the single instance lock to allow multiple instances
app.allowRendererProcessReuse = true;
app.commandLine.appendSwitch('disable-site-isolation-trials');


let pythonServer = null;

function checkPortInUse(port) {
  return new Promise((resolve) => {
    const server = net.createServer()
      .once('error', () => resolve(true))
      .once('listening', () => {
        server.close();
        resolve(false);
      })
      .listen(port);
  });
}

async function startPythonServer() {
  try {
    const serverPath = path.join(process.resourcesPath, 'backend/tfjl_server.exe');

    if (!fs.existsSync(serverPath)) {
      throw new Error(`Python server executable not found at: ${serverPath}`);
    }

    // Check if server is already running on port 8000
    const isPortInUse = await checkPortInUse(8000);
    if (isPortInUse) {
      logger.info('Python server is already running on port 8000');
      return;
    }

    logger.info('Starting Python server...');
    pythonServer = spawn(serverPath, [], {
      shell: true,
      windowsHide: true
    });

    pythonServer.stdout.on('data', (data) => {
      logger.info(`Python Server: ${data}`);
    });

    pythonServer.stderr.on('data', (data) => {
      logger.error(`Python Server Error: ${data}`);
    });

    pythonServer.on('close', (code) => {
      logger.info(`Python server process exited with code ${code}`);
    });

    pythonServer.on('error', (error) => {
      logger.error(`Failed to start Python server: ${error.message}`);
    });
  } catch (error) {
    logger.error(`Error starting Python server: ${error.message}`);
    throw error; // Re-throw to handle it in the main process
  }
}

// Enable DevTools in production
app.commandLine.appendSwitch('remote-debugging-port', '8315');

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 800,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Register DevTools toggle shortcut
  globalShortcut.register('CommandOrControl+Shift+I', () => {
    mainWindow.webContents.toggleDevTools();
  });
}

app.whenReady().then(() => {
  if (!isDev) {
    startPythonServer();
  }
  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  // Unregister all shortcuts
  globalShortcut.unregisterAll();

  // Kill Python server process
  if (pythonServer) {
    logger.info('Shutting down Python server...');
    pythonServer.kill();
  }
});