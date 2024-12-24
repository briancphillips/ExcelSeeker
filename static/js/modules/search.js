import { APIService } from "./api.js";
import {
  showError,
  showMessage,
  toggleVisibility,
  getElement,
  updateProgress,
  setFormElementsState,
} from "../utils/dom.js";

/**
 * Search Manager - Handles all search-related functionality
 */
export class SearchManager {
  constructor() {
    this.api = new APIService();
    this.setupElements();
    this.setupEventListeners();
  }

  /**
   * Initialize required DOM elements
   */
  setupElements() {
    this.elements = {
      form: getElement("searchForm"),
      searchInput: getElement("searchText"),
      fileInput: getElement("file"),
      folderInput: getElement("folderPath"),
      loading: getElement("loading"),
      resultsSection: getElement("resultsSection"),
      progressBar: getElement("progress"),
      cancelButton: getElement("cancelSearch"),
      searchTypeInputs: document.querySelectorAll('input[name="searchType"]'),
      searchModeInputs: document.querySelectorAll('input[name="search_mode"]'),
      regularModes: getElement("regularSearchModes"),
      nlpInfo: getElement("nlpSearchInfo"),
      progressText: document.querySelector(".progress-text"),
      progressBarElement: document.querySelector(".progress-bar"),
    };
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Form submission
    this.elements.form.addEventListener("submit", this.handleSubmit.bind(this));

    // Cancel button
    this.elements.cancelButton.addEventListener(
      "click",
      this.handleCancel.bind(this)
    );

    // Search type changes
    this.setupSearchTypeListeners();

    // Initialize search type state
    const currentSearchType =
      document.querySelector('input[name="search_type"]:checked')?.value ||
      "regular";
    this.updateSearchTypeState(currentSearchType === "regular");
  }

  /**
   * Setup search type toggle listeners
   */
  setupSearchTypeListeners() {
    this.elements.searchTypeInputs.forEach((radio) => {
      radio.addEventListener("change", (e) => {
        const isRegular = e.target.value === "regular";
        this.updateSearchTypeState(isRegular);
      });
    });
  }

  /**
   * Update search type state
   */
  updateSearchTypeState(isRegular) {
    // Update visibility
    toggleVisibility(this.elements.regularModes, isRegular);
    toggleVisibility(this.elements.nlpInfo, !isRegular);

    // Update placeholder
    this.elements.searchInput.placeholder = isRegular
      ? "Enter search text"
      : "Enter natural language query (e.g., 'find travel expenses over $5000 from last quarter')";

    // Enable/disable search mode inputs
    this.elements.searchModeInputs.forEach((input) => {
      input.disabled = !isRegular;
      const radioOption = input.closest(".radio-option");
      if (radioOption) {
        radioOption.classList.toggle("disabled", !isRegular);
      }
    });

    // If switching to NLP, select the first mode
    if (!isRegular && this.elements.searchModeInputs.length > 0) {
      this.elements.searchModeInputs[0].checked = true;
    }
  }

  /**
   * Handle form submission
   */
  async handleSubmit(event) {
    event.preventDefault();

    const searchText = this.elements.searchInput.value.trim();
    const searchTypeMode = document.querySelector(
      'input[name="searchType"]:checked'
    )?.value;
    const searchType = document.querySelector(
      'input[name="search_type"]:checked'
    )?.value;
    const searchMode = document.querySelector(
      'input[name="search_mode"]:checked'
    )?.value;
    const folderPath = this.elements.folderInput.value.trim();
    const fileSelected =
      this.elements.fileInput.files && this.elements.fileInput.files.length > 0;

    // Validation
    if (!searchText) {
      showError("Please enter search text");
      return;
    }

    if (!searchTypeMode) {
      showError("Please select a search type (file or folder)");
      return;
    }

    if (!searchType) {
      showError("Please select a search type (regular or NLP)");
      return;
    }

    if (searchType === "regular" && !searchMode) {
      showError("Please select a search mode");
      return;
    }

    // Show loading state
    toggleVisibility(this.elements.loading, true);
    toggleVisibility(this.elements.resultsSection, false);
    setFormElementsState(this.elements.form, true);

    try {
      if (searchTypeMode === "folder") {
        if (!folderPath) {
          throw new Error("Please select a folder to search");
        }
        await this.handleFolderSearch(
          folderPath,
          searchText,
          searchType,
          searchMode
        );
      } else {
        if (!fileSelected) {
          throw new Error("Please select a file to search");
        }
        await this.handleFileSearch(searchText, searchType, searchMode);
      }
    } catch (error) {
      showError(error.message || "An error occurred while searching");
      console.error("Search error:", error);
    } finally {
      toggleVisibility(this.elements.loading, false);
      setFormElementsState(this.elements.form, false);
    }
  }

  /**
   * Handle folder search
   */
  async handleFolderSearch(folderPath, searchText, searchType, searchMode) {
    const finalSearchMode = searchType === "nlp" ? "nlp" : searchMode;

    // Show loading section and cancel button
    toggleVisibility(this.elements.loading, true);
    toggleVisibility(this.elements.cancelButton, true);

    // Reset progress bar
    if (this.elements.progressBarElement && this.elements.progressText) {
      this.elements.progressBarElement.style.width = "0%";
      this.elements.progressText.textContent = "0%";
    }
    if (this.elements.progressBar) {
      this.elements.progressBar.textContent = "Starting search...";
    }

    this.api.initFolderSearch(
      folderPath,
      searchText,
      finalSearchMode,
      this.handleSearchProgress.bind(this),
      this.handleSearchComplete.bind(this),
      this.handleSearchError.bind(this)
    );
  }

  /**
   * Handle file search
   */
  async handleFileSearch(searchText, searchType, searchMode) {
    // Show loading section but hide cancel button (not needed for single file)
    toggleVisibility(this.elements.loading, true);
    toggleVisibility(this.elements.cancelButton, false);

    // Set progress bar to indeterminate state
    if (this.elements.progressBarElement && this.elements.progressText) {
      this.elements.progressBarElement.style.width = "100%";
      this.elements.progressText.textContent = "Processing...";
    }
    if (this.elements.progressBar) {
      this.elements.progressBar.textContent = "Searching file...";
    }

    const formData = new FormData();
    formData.append("search_text", searchText);
    formData.append("search_type", searchType);
    formData.append("search_mode", searchType === "nlp" ? "nlp" : searchMode);
    formData.append("file", this.elements.fileInput.files[0]);

    const data = await this.api.searchFile(formData);
    this.handleSearchComplete(data);
  }

  /**
   * Handle search progress updates
   */
  handleSearchProgress(data) {
    // Ensure loading section is visible
    toggleVisibility(this.elements.loading, true);

    const percentage = Math.round((data.processed / data.total) * 100);
    if (this.elements.progressBarElement && this.elements.progressText) {
      this.elements.progressBarElement.style.width = `${percentage}%`;
      this.elements.progressText.textContent = `${percentage}%`;
    }
    if (this.elements.progressBar) {
      this.elements.progressBar.textContent = `Processing: ${data.current_file} (${data.processed}/${data.total} files, ${data.results_found} results found)`;
    }
  }

  /**
   * Handle search completion
   */
  handleSearchComplete(data, wasCancelled = false) {
    // Hide loading section
    toggleVisibility(this.elements.loading, false);
    toggleVisibility(this.elements.cancelButton, false);

    if (wasCancelled) {
      showMessage("Search cancelled. Showing partial results.");
    }

    if (data.results && data.results.length > 0) {
      // Emit event for results display
      window.dispatchEvent(
        new CustomEvent("searchComplete", { detail: data.results })
      );
      toggleVisibility(this.elements.resultsSection, true);
    } else {
      showMessage("No results found.");
      toggleVisibility(this.elements.resultsSection, false);
    }
  }

  /**
   * Handle search errors
   */
  handleSearchError(error) {
    // Hide loading section and cancel button
    toggleVisibility(this.elements.loading, false);
    toggleVisibility(this.elements.cancelButton, false);
    toggleVisibility(this.elements.resultsSection, false);

    showError(error);
    setFormElementsState(this.elements.form, false);
  }

  /**
   * Handle search cancellation
   */
  async handleCancel() {
    try {
      if (this.elements.progressBar) {
        this.elements.progressBar.textContent = "Cancelling search...";
      }
      await this.api.cancelSearch();
    } catch (error) {
      showError("Failed to cancel search");
      console.error("Cancel error:", error);
    }
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    this.api.cleanup();
  }
}
