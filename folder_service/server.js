const express = require("express");
const { app, dialog, BrowserWindow } = require("electron");
const cors = require("cors");
const path = require("path");

const server = express();
server.use(cors());
server.use(express.json());

let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 0,
    height: 0,
    show: false,
    type: "toolbar",
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  // Keep window always on top
  mainWindow.setVisibleOnAllWorkspaces(true);
  mainWindow.setAlwaysOnTop(true, "pop-up-menu");

  // Hide dock icon on macOS
  if (process.platform === "darwin") {
    app.dock.hide();
  }
}

app.on("ready", () => {
  createWindow();
  console.log("Electron app is ready");
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});

server.get("/health", (req, res) => {
  res.json({ status: "ok" });
});

server.post("/select-folder", async (req, res) => {
  try {
    if (!mainWindow) {
      createWindow();
    }

    // Force focus and top-most state
    mainWindow.setAlwaysOnTop(true, "pop-up-menu", 1);
    mainWindow.moveTop();

    const options = {
      properties: ["openDirectory"],
      title: "Select Folder",
      defaultPath: app.getPath("documents"),
      buttonLabel: "Select Folder",
      modal: true,
    };

    const result = await dialog.showOpenDialog(mainWindow, options);

    if (!result.canceled) {
      res.json({ path: result.filePaths[0] });
    } else {
      res.json({ path: null });
    }
  } catch (error) {
    console.error("Error selecting folder:", error);
    res.status(500).json({ error: "Failed to open folder dialog" });
  }
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Folder selection service running on port ${PORT}`);
});
