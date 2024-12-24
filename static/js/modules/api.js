/**
 * API Module - Handles all server communications
 */
export class APIService {
  constructor() {
    this.currentSearchId = null;
    this.activeEventSource = null;
  }

  /**
   * Perform a search on a single file
   */
  async searchFile(formData) {
    const response = await fetch("/search", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.error || "An error occurred while searching");
    }

    return response.json();
  }

  /**
   * Initialize folder search with server-sent events
   */
  initFolderSearch(
    folderPath,
    searchText,
    searchMode,
    onProgress,
    onComplete,
    onError
  ) {
    const searchUrl = `/search_folder?folder_path=${encodeURIComponent(
      folderPath
    )}&search_text=${encodeURIComponent(searchText)}&search_mode=${searchMode}`;

    if (this.activeEventSource) {
      this.activeEventSource.close();
    }

    const eventSource = new EventSource(searchUrl);
    this.activeEventSource = eventSource;

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.error) {
        eventSource.close();
        onError(data.error);
        return;
      }

      if (data.search_id) {
        this.currentSearchId = data.search_id;
        return;
      }

      switch (data.type) {
        case "progress":
          onProgress(data);
          break;
        case "complete":
          eventSource.close();
          this.activeEventSource = null;
          onComplete(data);
          break;
        case "cancelled":
          eventSource.close();
          this.activeEventSource = null;
          onComplete(data, true);
          break;
      }
    };

    eventSource.onerror = (error) => {
      console.error("EventSource error:", error);
      eventSource.close();
      this.activeEventSource = null;
      onError("Connection error occurred. Please try again.");
    };

    return eventSource;
  }

  /**
   * Cancel ongoing search
   */
  async cancelSearch() {
    if (!this.currentSearchId) {
      console.log("No active search to cancel");
      return;
    }

    try {
      const response = await fetch(`/cancel-search/${this.currentSearchId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Failed to cancel search");
      }

      return data;
    } catch (error) {
      console.error("Error cancelling search:", error);
      throw new Error("Failed to cancel search");
    }
  }

  /**
   * Load skipped files list
   */
  async loadSkippedFiles() {
    const response = await fetch("/skip-list");
    const data = await response.json();

    if (!response.ok) {
      throw new Error("Failed to load skipped files");
    }

    return data.skip_list || [];
  }

  /**
   * Clear skip list
   */
  async clearSkipList() {
    const response = await fetch("/clear-skip-list", {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error("Failed to clear skip list");
    }

    return response.json();
  }

  /**
   * Open a file using system default application
   */
  async openFile(filepath) {
    const response = await fetch("/open-file", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ filepath }),
    });

    const data = await response.json();
    if (!response.ok || data.error) {
      throw new Error(data.error || "Failed to open file");
    }

    return data;
  }

  /**
   * Select folder using native dialog
   */
  async selectFolder() {
    const response = await fetch("/select-folder", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();
    if (!response.ok || !data.path) {
      throw new Error("Failed to select folder");
    }

    return data.path;
  }

  /**
   * Restart services
   */
  async restartServices() {
    const response = await fetch("/restart-services", {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error("Failed to restart services");
    }

    return response.json();
  }

  /**
   * Cleanup any active connections
   */
  cleanup() {
    if (this.activeEventSource) {
      this.activeEventSource.close();
      this.activeEventSource = null;
    }
    this.currentSearchId = null;
  }
}
