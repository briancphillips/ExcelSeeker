import { getElement, createElement } from "../utils/dom.js";

/**
 * Skipped Files Manager - Handles skipped files display and operations
 */
export class SkippedFilesManager {
  constructor(api) {
    this.api = api;
    this.setupElements();
    this.setupEventListeners();
    this.loadSkippedFiles();
  }

  /**
   * Initialize required DOM elements
   */
  setupElements() {
    this.elements = {
      skippedFilesList: getElement("skippedFilesList"),
      skipFilterInput: getElement("skipFilterInput"),
      skipFilterColumn: getElement("skipFilterColumn"),
      clearButton: getElement("clearSkipListBtn"),
      exportButton: getElement("exportSkipListBtn"),
    };
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    this.elements.skipFilterInput.addEventListener("input", () =>
      this.filterSkippedFiles()
    );
    this.elements.skipFilterColumn.addEventListener("change", () =>
      this.filterSkippedFiles()
    );
    this.elements.clearButton.addEventListener("click", () =>
      this.clearSkipList()
    );
    this.elements.exportButton.addEventListener("click", () =>
      this.exportSkipList()
    );

    // Sort handlers
    document
      .querySelectorAll(".skipped-table .sortable")
      .forEach((header, index) => {
        header.addEventListener("click", () => this.sortSkippedFiles(index));
      });
  }

  /**
   * Load and display skipped files
   */
  async loadSkippedFiles() {
    try {
      const skipList = await this.api.loadSkippedFiles();
      this.displaySkippedFiles(skipList);
    } catch (error) {
      console.error("Error loading skipped files:", error);
    }
  }

  /**
   * Display skipped files
   */
  displaySkippedFiles(skippedFiles) {
    this.elements.skippedFilesList.innerHTML = "";

    if (!skippedFiles || skippedFiles.length === 0) {
      this.elements.skippedFilesList.innerHTML = `
                <tr class="no-skipped-files">
                    <td colspan="2">No skipped files to display</td>
                </tr>`;
      return;
    }

    // Group by directory
    const groupedSkipped = this.groupByDirectory(skippedFiles);
    this.renderGroupedSkippedFiles(groupedSkipped);
  }

  /**
   * Group files by directory
   */
  groupByDirectory(files) {
    return files.reduce((groups, item) => {
      if (!item || !item.directory) return groups;

      if (!groups[item.directory]) {
        groups[item.directory] = [];
      }

      groups[item.directory].push({
        filename: item.file,
        path: item.path,
        reason: item.reason?.reason || "Unknown error",
      });

      return groups;
    }, {});
  }

  /**
   * Render grouped skipped files
   */
  renderGroupedSkippedFiles(groupedSkipped) {
    Object.entries(groupedSkipped).forEach(
      ([dirPath, fileErrors], groupIndex) => {
        // Add group header
        const headerRow = createElement("tr", { class: "group-header" });
        headerRow.innerHTML = `
                <td colspan="2">
                    <div class="file-group-header">
                        <div class="path-info">
                            <span class="directory-path" title="${dirPath}">📁 ${dirPath}</span>
                            <span class="match-count">${
                              fileErrors.length
                            } file${
          fileErrors.length > 1 ? "s" : ""
        } skipped</span>
                        </div>
                    </div>
                </td>
            `;
        this.elements.skippedFilesList.appendChild(headerRow);

        // Add errors for this directory
        fileErrors.forEach((error) => {
          const row = createElement("tr", { class: "group-item" });
          row.innerHTML = `
                    <td class="file-name">${error.filename}</td>
                    <td class="file-reason">${error.reason}</td>
                `;
          this.elements.skippedFilesList.appendChild(row);
        });

        // Add separator
        if (groupIndex < Object.keys(groupedSkipped).length - 1) {
          const separatorRow = createElement("tr", {
            class: "group-separator",
          });
          separatorRow.innerHTML = '<td colspan="2"></td>';
          this.elements.skippedFilesList.appendChild(separatorRow);
        }
      }
    );
  }

  /**
   * Filter skipped files
   */
  filterSkippedFiles() {
    const filterText = this.elements.skipFilterInput.value.toLowerCase();
    const filterColumn = this.elements.skipFilterColumn.value;
    const groups = Array.from(
      this.elements.skippedFilesList.getElementsByClassName("group-header")
    );

    groups.forEach((header) => {
      let groupVisible = false;
      let currentGroup = header;
      const items = [];

      const dirPath = header
        .querySelector(".directory-path")
        .textContent.toLowerCase();

      // Collect items in this group
      while (
        currentGroup.nextElementSibling &&
        !currentGroup.nextElementSibling.classList.contains("group-header")
      ) {
        if (currentGroup.nextElementSibling.classList.contains("group-item")) {
          items.push(currentGroup.nextElementSibling);
        }
        currentGroup = currentGroup.nextElementSibling;
      }

      if (!filterText) {
        header.style.display = "";
        items.forEach((item) => (item.style.display = ""));
        if (header.nextElementSibling?.classList.contains("group-separator")) {
          header.nextElementSibling.style.display = "";
        }
        return;
      }

      items.forEach((item) => {
        let text = "";
        if (filterColumn === "all") {
          text =
            dirPath +
            " " +
            item.querySelector(".file-name").textContent.toLowerCase() +
            " " +
            item.querySelector(".file-reason").textContent.toLowerCase();
        } else if (filterColumn === "filename") {
          text =
            dirPath +
            "/" +
            item.querySelector(".file-name").textContent.toLowerCase();
        } else if (filterColumn === "reason") {
          text = item.querySelector(".file-reason").textContent.toLowerCase();
        }

        const matches = text.includes(filterText);
        item.style.display = matches ? "" : "none";
        if (matches) groupVisible = true;
      });

      header.style.display = groupVisible ? "" : "none";
      if (header.nextElementSibling?.classList.contains("group-separator")) {
        header.nextElementSibling.style.display = groupVisible ? "" : "none";
      }
    });
  }

  /**
   * Sort skipped files
   */
  sortSkippedFiles(columnIndex) {
    const tbody = this.elements.skippedFilesList;
    const rows = Array.from(tbody.getElementsByTagName("tr"));

    // Sort rows
    rows.sort((a, b) => {
      if (
        a.classList.contains("group-header") ||
        b.classList.contains("group-header") ||
        a.classList.contains("group-separator") ||
        b.classList.contains("group-separator")
      ) {
        return 0;
      }

      const aValue = a.cells[columnIndex].textContent.trim().toLowerCase();
      const bValue = b.cells[columnIndex].textContent.trim().toLowerCase();
      return aValue.localeCompare(bValue);
    });

    // Reapply rows
    tbody.innerHTML = "";
    rows.forEach((row) => tbody.appendChild(row));
  }

  /**
   * Clear skip list
   */
  async clearSkipList() {
    try {
      await this.api.clearSkipList();
      this.loadSkippedFiles();
    } catch (error) {
      console.error("Error clearing skip list:", error);
    }
  }

  /**
   * Export skip list as CSV
   */
  exportSkipList() {
    const rows = Array.from(this.elements.skippedFilesList.rows);
    if (!rows.length) {
      showMessage("No skipped files to export");
      return;
    }

    let csvContent = "Path,File Name,Error Reason\n";
    let currentPath = "";

    rows.forEach((row) => {
      if (row.classList.contains("group-header")) {
        currentPath = row.querySelector(".directory-path").textContent;
      } else if (row.classList.contains("group-item")) {
        const fileName = row.querySelector(".file-name").textContent;
        const reason = row.querySelector(".file-reason").textContent;

        // Escape fields that might contain commas
        const escapedPath = `"${currentPath.replace(/"/g, '""')}"`;
        const escapedFileName = `"${fileName.replace(/"/g, '""')}"`;
        const escapedReason = `"${reason.replace(/"/g, '""')}"`;

        csvContent += `${escapedPath},${escapedFileName},${escapedReason}\n`;
      }
    });

    // Create and trigger download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = createElement("a", {
      href: URL.createObjectURL(blob),
      download: "skipped_files.csv",
    });
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }
}
