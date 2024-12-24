import { getElement, showError, toggleVisibility } from "../utils/dom.js";

/**
 * File Manager - Handles file and folder operations
 */
export class FileManager {
  constructor(api) {
    this.api = api;
    this.setupElements();
    this.setupEventListeners();
    this.initializeState();
  }

  /**
   * Initialize required DOM elements
   */
  setupElements() {
    this.elements = {
      fileInputContainer: getElement("fileInput"),
      folderInputContainer: getElement("folderInput"),
      fileInput: getElement("file"),
      folderInput: getElement("folderPath"),
      fileNameDisplay: getElement("fileNameDisplay"),
      selectFolderBtn: getElement("selectFolderBtn"),
      searchTypeInputs: document.querySelectorAll('input[name="searchType"]'),
    };
  }

  /**
   * Initialize initial state based on default selection
   */
  initializeState() {
    const selectedType = document.querySelector(
      'input[name="searchType"]:checked'
    )?.value;
    this.updateVisibility(selectedType || "folder");
    this.restoreLastFolder();
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // File input change handler
    this.elements.fileInput.addEventListener(
      "change",
      this.handleFileChange.bind(this)
    );

    // Folder selection handler
    this.elements.selectFolderBtn.addEventListener(
      "click",
      this.handleFolderSelect.bind(this)
    );

    // Search type toggle handler
    this.elements.searchTypeInputs.forEach((radio) => {
      radio.addEventListener("change", this.handleSearchTypeChange.bind(this));
    });
  }

  /**
   * Handle file input change
   */
  handleFileChange(event) {
    const fileName = event.target.files[0]?.name || "No file chosen";
    this.elements.fileNameDisplay.textContent = fileName;
  }

  /**
   * Handle folder selection
   */
  async handleFolderSelect() {
    try {
      const path = await this.api.selectFolder();
      if (path) {
        console.log("Selected folder path:", path); // Debug log
        this.elements.folderInput.value = path;
        this.elements.folderInput.dispatchEvent(new Event("change")); // Trigger change event
        sessionStorage.setItem("lastFolderPath", path);
      }
    } catch (error) {
      console.error("Error selecting folder:", error);
      showError(
        "Failed to open folder selection dialog. Make sure the folder service is running."
      );
    }
  }

  /**
   * Handle search type change
   */
  handleSearchTypeChange(event) {
    console.log("Search type changed:", event.target.value); // Debug log
    this.updateVisibility(event.target.value);
  }

  /**
   * Update visibility of file/folder inputs
   */
  updateVisibility(searchType) {
    console.log("Updating visibility for search type:", searchType); // Debug log
    const isFileMode = searchType === "file";

    // Update container visibility
    toggleVisibility(this.elements.fileInputContainer, isFileMode);
    toggleVisibility(this.elements.folderInputContainer, !isFileMode);

    // Update required states
    this.elements.fileInput.required = isFileMode;
    this.elements.folderInput.required = !isFileMode;

    // Clear values when switching modes
    if (isFileMode) {
      this.elements.folderInput.value = "";
      sessionStorage.removeItem("lastFolderPath");
    } else {
      this.elements.fileInput.value = "";
      this.elements.fileNameDisplay.textContent = "No file chosen";
      this.restoreLastFolder();
    }
  }

  /**
   * Restore last used folder path
   */
  restoreLastFolder() {
    const lastFolderPath = sessionStorage.getItem("lastFolderPath");
    console.log("Restoring last folder path:", lastFolderPath); // Debug log
    if (lastFolderPath) {
      this.elements.folderInput.value = lastFolderPath;
      this.elements.folderInput.dispatchEvent(new Event("change")); // Trigger change event
    }
  }

  /**
   * Get current file or folder path
   */
  getCurrentPath() {
    const searchType = document.querySelector(
      'input[name="searchType"]:checked'
    )?.value;
    if (searchType === "file") {
      return this.elements.fileInput.files[0]?.path || null;
    }
    return this.elements.folderInput.value || null;
  }

  /**
   * Check if a file or folder is selected
   */
  hasSelection() {
    const searchType = document.querySelector(
      'input[name="searchType"]:checked'
    )?.value;
    if (searchType === "file") {
      return this.elements.fileInput.files.length > 0;
    }
    return Boolean(this.elements.folderInput.value);
  }

  /**
   * Reset file/folder selection
   */
  reset() {
    this.elements.fileInput.value = "";
    this.elements.fileNameDisplay.textContent = "No file chosen";
    this.elements.folderInput.value = "";
    sessionStorage.removeItem("lastFolderPath");
  }
}
