const express = require("express");
const { dialog } = require("electron");
const { app, BrowserWindow } = require("electron");
const cors = require("cors");

const server = express();
server.use(cors());
server.use(express.json());

let mainWindow = null;

// Initialize Electron
app.whenReady().then(() => {
  mainWindow = new BrowserWindow({
    width: 1,
    height: 1,
    show: false,
    webPreferences: {
      nodeIntegration: true,
    },
  });
});

// Endpoint to select folder
server.post("/select-folder", async (req, res) => {
  try {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ["openDirectory"],
    });

    if (!result.canceled) {
      res.json({ path: result.filePaths[0] });
    } else {
      res.json({ path: null });
    }
  } catch (error) {
    console.error("Error selecting folder:", error);
    res.status(500).json({ error: "Failed to select folder" });
  }
});

// Start server
const PORT = 3000;
server.listen(PORT, () => {
  console.log(`Folder selection service running on port ${PORT}`);
});
