#!/usr/bin/env node

const { exec } = require("child_process");
const path = require("path");
const process = require("process");

const frontendDir = path.join(__dirname, "../../frontend");

function buildFrontend() {
  return new Promise((resolve, reject) => {
    process.chdir(frontendDir);
    const buildProcess = exec("npm run build");

    buildProcess.stdout.on("data", (data) => {
      console.log(`stdout: ${data}`);
    });

    buildProcess.stderr.on("data", (data) => {
      console.error(`stderr: ${data}`);
    });

    buildProcess.on("close", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Build process exited with code ${code}`));
      }
    });
  });
}

buildFrontend()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
