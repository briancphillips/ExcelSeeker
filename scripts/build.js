const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

// Create build directory if it doesn't exist
const buildDir = path.join(__dirname, "..", "build");
if (!fs.existsSync(buildDir)) {
  fs.mkdirSync(buildDir);
}

// Create entitlements file for macOS
if (os.platform() === "darwin") {
  const entitlements = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
  </dict>
</plist>`;

  fs.writeFileSync(path.join(buildDir, "entitlements.mac.plist"), entitlements);
}

// Clean up previous builds
console.log("Cleaning up previous builds...");
try {
  if (fs.existsSync("dist")) {
    fs.rmSync("dist", { recursive: true });
  }
  if (fs.existsSync("folder_service/dist")) {
    fs.rmSync("folder_service/dist", { recursive: true });
  }
} catch (error) {
  console.warn("Warning during cleanup:", error);
}

console.log("Building Python application...");
try {
  execSync("npm run build:python", { stdio: "inherit" });
} catch (error) {
  console.error("Failed to build Python application:", error);
  process.exit(1);
}

console.log("Building Electron application...");
try {
  // Ensure electron is installed in folder_service
  execSync("cd folder_service && npm install", { stdio: "inherit" });
  execSync("npm run build:electron", { stdio: "inherit" });
} catch (error) {
  console.error("Failed to build Electron application:", error);
  process.exit(1);
}

console.log("Build completed successfully!");
