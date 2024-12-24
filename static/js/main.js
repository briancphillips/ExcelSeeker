import { APIService } from "./modules/api.js";
import { SearchManager } from "./modules/search.js";
import { ResultsManager } from "./modules/results.js";
import { ThemeManager } from "./modules/theme.js";
import { FileManager } from "./modules/fileManager.js";
import { SkippedFilesManager } from "./modules/skippedFiles.js";
import { showMessage, showError } from "./utils/dom.js";

/**
 * Main Application Class
 */
class App {
  constructor() {
    this.initializeModules();
    this.setupGlobalEventListeners();
    this.handleInitialState();
  }

  /**
   * Initialize all modules
   */
  initializeModules() {
    try {
      console.log("Initializing modules..."); // Debug log

      // Create shared API service
      this.api = new APIService();

      // Initialize all managers in specific order
      this.themeManager = new ThemeManager();
      this.fileManager = new FileManager(this.api);
      this.searchManager = new SearchManager(this.api);
      this.resultsManager = new ResultsManager(this.api);
      this.skippedFilesManager = new SkippedFilesManager(this.api);

      // Make managers globally accessible where needed
      window.resultsManager = this.resultsManager;
      window.skippedFilesManager = this.skippedFilesManager;

      console.log("Modules initialized successfully"); // Debug log
    } catch (error) {
      console.error("Error initializing modules:", error);
      showError("Failed to initialize application. Please refresh the page.");
    }
  }

  /**
   * Setup global event listeners
   */
  setupGlobalEventListeners() {
    try {
      console.log("Setting up global event listeners..."); // Debug log

      // Handle restart button
      const restartButton = document.getElementById("restartButton");
      if (restartButton) {
        restartButton.addEventListener("click", this.handleRestart.bind(this));
      }

      // Handle window unload
      window.addEventListener("beforeunload", () => {
        this.cleanup();
      });

      console.log("Global event listeners set up successfully"); // Debug log
    } catch (error) {
      console.error("Error setting up event listeners:", error);
    }
  }

  /**
   * Handle initial application state
   */
  handleInitialState() {
    try {
      console.log("Setting up initial state..."); // Debug log

      // Restore last search type
      const lastSearchType = sessionStorage.getItem("lastSearchType");
      if (lastSearchType) {
        const radio = document.querySelector(
          `input[name="searchType"][value="${lastSearchType}"]`
        );
        if (radio) {
          radio.checked = true;
          radio.dispatchEvent(new Event("change"));
        }
      }

      console.log("Initial state set up successfully"); // Debug log
    } catch (error) {
      console.error("Error setting up initial state:", error);
    }
  }

  /**
   * Handle service restart
   */
  async handleRestart() {
    try {
      const restartButton = document.getElementById("restartButton");
      restartButton.disabled = true;

      showMessage("Stopping services...");

      // Clean up any existing search
      this.searchManager.cleanup();

      // Restart services
      await this.api.restartServices();

      showMessage("Starting services...");

      // Reload the page after a delay
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    } catch (error) {
      console.error("Error restarting services:", error);
      showError("Failed to restart services: " + error.message);
      document.getElementById("restartButton").disabled = false;
    }
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    try {
      console.log("Cleaning up resources..."); // Debug log
      this.searchManager.cleanup();
      console.log("Cleanup completed successfully"); // Debug log
    } catch (error) {
      console.error("Error during cleanup:", error);
    }
  }
}

// Initialize the application when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM loaded, initializing application..."); // Debug log
  window.app = new App();
});
