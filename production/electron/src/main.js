const { app, BrowserWindow, globalShortcut, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const logger = require('./logger');
const net = require('net');
const isDev = process.env.NODE_ENV === 'development' || !fs.existsSync(path.join(__dirname, '../dist/index.html'));

// Disable the single instance lock to allow multiple instances
app.allowRendererProcessReuse = true;
app.commandLine.appendSwitch('disable-site-isolation-trials');
app.commandLine.appendSwitch('no-sandbox');


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
    const serverPath = path.join(process.resourcesPath, 'backend', 'tfjl_server.exe');
    const normalizedPath = path.normalize(serverPath);

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
    pythonServer = spawn(`"${normalizedPath}"`, [], {
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

function registerHandler() {
  ipcMain.on('restart-server', () => {
    if (isDev) {
      console.log('Dev mode, not restarting server');
      return;
    }
    if (pythonServer) {
      logger.info('Restarting Python server...');
      pythonServer.kill('SIGKILL');
      pythonServer = null;
    }
    startPythonServer();
  });
}

// Enable DevTools in production
app.commandLine.appendSwitch('remote-debugging-port', '8315');

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 850,
    height: 700,
    webPreferences: {
      nodeIntegration: true,
      preload: path.join(__dirname, 'preload.js'),
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
  registerHandler();
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
    try {
      pythonServer.kill('SIGKILL');
    } catch (err) {
      logger.error(`Failed to kill Python server process: ${err.message}`);
    }
  }

  // Kill TFJL server process
  try {
    logger.info('Terminating TFJL server process...');
    const { spawnSync } = require('child_process');
    const result = spawnSync('taskkill', ['/F', '/IM', 'tfjl_server.exe']);
    if (result.error) {
      throw result.error;
    }
  } catch (err) {
    logger.error(`Failed to terminate TFJL server process: ${err.message}`);
  }
});

// Handle unexpected exits
process.on('uncaughtException', (err) => {
  logger.error(`Uncaught Exception: ${err.message}`);
  
  // Cleanup before exiting
  if (pythonServer) {
    try {
      pythonServer.kill('SIGKILL');
    } catch (killErr) {
      logger.error(`Failed to kill Python server during crash: ${killErr.message}`);
    }
  }
  
  // Kill TFJL Auto process
  try {
    spawn('taskkill', ['/F', '/IM', 'tfjl_server.exe']);
  } catch (err) {
    logger.error(`Failed to terminate TFJL server process: ${err.message}`);
  }
  
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  logger.error(`Unhandled Rejection at: ${promise}, reason: ${reason}`);
  
  // Cleanup before exiting
  if (pythonServer) {
    try {
      pythonServer.kill('SIGKILL');
    } catch (killErr) {
      logger.error(`Failed to kill Python server during crash: ${killErr.message}`);
    }
  }
  
  // Kill TFJL Auto process
  try {
    spawn('taskkill', ['/F', '/IM', 'tfjl_server.exe']);
  } catch (err) {
    logger.error(`Failed to terminate TFJL server process: ${err.message}`);
  }
  
  process.exit(1);
});