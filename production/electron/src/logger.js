const winston = require('winston');
const path = require('path');
const fs = require('fs');
const isDev = process.env.NODE_ENV === 'development';

// Get the directory where the executable lives
const exeDir = path.dirname(process.execPath);
// Define the log directory path
const logDir = isDev ?  path.join(__dirname, '../logs') : path.join(exeDir, 'logs');

// Create the directory (with safety checks)
function ensureLogDir() {
  if (fs.existsSync(logDir)) {
    // If it exists but is a FILE (not a directory), delete it
    const stats = fs.statSync(logDir);
    if (!stats.isDirectory()) {
      fs.rmSync(logDir, { force: true });
    }
  }

  // Create the directory (including parents if needed)
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
}

// Initialize the directory
ensureLogDir();

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.printf(({ level, message, timestamp }) => {
      return `${timestamp} ${level}: ${message}`;
    })
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ 
      filename: path.join(logDir, `app_${new Date().toISOString().split('T')[0]}.log`),
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    })
  ]
});

module.exports = logger;