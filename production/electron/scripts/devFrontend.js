const { spawn } = require('child_process');
const path = require('path');

const frontendPath = path.join(__dirname, '../../frontend');

const devProcess = spawn('npm', ['run', 'dev'], {
  cwd: frontendPath,
  stdio: 'inherit',
  shell: true
});

devProcess.on('error', (err) => {
  console.error('Failed to start subprocess:', err);
});

devProcess.on('close', (code) => {
  console.log(`Frontend dev process exited with code ${code}`);
});