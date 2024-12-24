import {
  escapeHtml,
  getElement,
  createElement,
  addEventListenerWithCleanup,
  debounce,
} from "../utils/dom.js";

/**
 * Results Manager - Handles display and manipulation of search results
 */
export class ResultsManager {
  constructor(api) {
    this.api = api;
    this.currentSort = { column: -1, direction: 1 };
    this.currentFilter = { text: "", column: "all" };
    this.setupElements();
    this.setupEventListeners();
  }

  /**
   * Initialize required DOM elements
   */
  setupElements() {
    this.elements = {
      resultsSection: getElement("resultsSection"),
      resultsBody: getElement("resultsBody"),
      filterInput: getElement("filterInput"),
      filterColumn: getElement("filterColumn"),
      sortHeaders: document.querySelectorAll(".sortable"),
      skippedFilesList: getElement("skippedFilesList"),
    };
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Filter event listeners with debouncing
    const debouncedFilter = debounce(() => this.filterResults(), 300);
    this.elements.filterInput.addEventListener("input", debouncedFilter);
    this.elements.filterColumn.addEventListener("change", debouncedFilter);

    // Sort event listeners
    this.elements.sortHeaders.forEach((header, index) => {
      header.addEventListener("click", () => this.sortTable(index));
    });

    // Listen for search completion
    window.addEventListener("searchComplete", (event) => {
      this.displayResults(event.detail);
    });
  }

  /**
   * Display search results
   */
  displayResults(results) {
    this.elements.resultsBody.innerHTML = "";

    if (!results || results.length === 0) {
      this.elements.resultsSection.classList.add("hidden");
      return;
    }

    this.elements.resultsSection.classList.remove("hidden");

    // Group results by filename
    const groupedResults = this.groupResultsByFile(results);
    this.renderGroupedResults(groupedResults);

    // Store results for sorting/filtering
    this.currentResults = results;
  }

  /**
   * Group results by filename
   */
  groupResultsByFile(results) {
    return results.reduce((groups, result) => {
      if (!groups[result.filename]) {
        groups[result.filename] = [];
      }
      groups[result.filename].push(result);
      return groups;
    }, {});
  }

  /**
   * Render grouped results
   */
  renderGroupedResults(groupedResults) {
    Object.entries(groupedResults).forEach(
      ([filename, fileResults], groupIndex) => {
        // Add group header
        const headerRow = createElement("tr", { class: "group-header" });
        headerRow.innerHTML = this.createGroupHeaderHTML(filename, fileResults);
        this.elements.resultsBody.appendChild(headerRow);

        // Add results for this file
        fileResults.forEach((result) => {
          const row = createElement("tr", { class: "group-item" });
          row.innerHTML = this.createResultRowHTML(result);
          this.elements.resultsBody.appendChild(row);
        });

        // Add separator after each group except the last one
        if (groupIndex < Object.keys(groupedResults).length - 1) {
          const separatorRow = createElement("tr", {
            class: "group-separator",
          });
          separatorRow.innerHTML = '<td colspan="4"></td>';
          this.elements.resultsBody.appendChild(separatorRow);
        }
      }
    );
  }

  /**
   * Create HTML for group header
   */
  createGroupHeaderHTML(filename, fileResults) {
    return `
            <td colspan="4">
                <div class="file-group-header">
                    <a href="#" 
                       onclick="window.resultsManager.openFile('${escapeHtml(
                         fileResults[0].filepath
                       )}'); return false;" 
                       class="file-link" 
                       title="Click to open file">
                        ${escapeHtml(filename)}
                    </a>
                    <span class="match-count">${fileResults.length} match${
      fileResults.length > 1 ? "es" : ""
    }</span>
                </div>
            </td>
        `;
  }

  /**
   * Create HTML for result row
   */
  createResultRowHTML(result) {
    let formattedValue = result.value;
    if (result.type === "date") {
      formattedValue = `📅 ${result.value}`;
    } else if (result.type === "monetary") {
      formattedValue = `💰 ${result.value}`;
    } else if (result.type === "budget_code") {
      formattedValue = `🏷️ ${result.value}`;
    }

    return `
            <td></td>
            <td>${escapeHtml(result.sheet)}</td>
            <td>${escapeHtml(result.cell)}</td>
            <td>${escapeHtml(formattedValue)}</td>
        `;
  }

  /**
   * Sort table by column
   */
  sortTable(columnIndex) {
    const tbody = this.elements.resultsBody;
    const rows = Array.from(tbody.getElementsByTagName("tr"));

    // Update sort direction
    if (this.currentSort.column === columnIndex) {
      this.currentSort.direction *= -1;
    } else {
      this.currentSort.direction = 1;
    }
    this.currentSort.column = columnIndex;

    // Update sort icons
    this.updateSortIcons(columnIndex);

    // Sort rows
    rows.sort((a, b) => {
      // Skip group headers and separators
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
      return aValue.localeCompare(bValue) * this.currentSort.direction;
    });

    // Clear and re-append sorted rows
    tbody.innerHTML = "";
    rows.forEach((row) => tbody.appendChild(row));

    // Reapply current filter if exists
    if (this.currentFilter.text) {
      this.filterResults();
    }
  }

  /**
   * Update sort icons
   */
  updateSortIcons(columnIndex) {
    document.querySelectorAll(".sort-icon").forEach((icon) => {
      icon.textContent = "↕";
    });
    const currentIcon = document.querySelectorAll(".sort-icon")[columnIndex];
    currentIcon.textContent = this.currentSort.direction === 1 ? "↓" : "↑";
  }

  /**
   * Filter results
   */
  filterResults() {
    const filterText = this.elements.filterInput.value.toLowerCase();
    const filterColumn = this.elements.filterColumn.value;
    const rows = Array.from(
      this.elements.resultsBody.getElementsByTagName("tr")
    );

    // Store current filter state
    this.currentFilter.text = filterText;
    this.currentFilter.column = filterColumn;

    // Show all rows if filter is empty
    if (!filterText) {
      rows.forEach((row) => (row.style.display = ""));
      return;
    }

    let lastHeader = null;
    let hasVisibleItems = false;

    rows.forEach((row) => {
      if (row.classList.contains("group-header")) {
        lastHeader = row;
        hasVisibleItems = false;
      } else if (row.classList.contains("group-separator")) {
        if (lastHeader) {
          lastHeader.style.display = hasVisibleItems ? "" : "none";
        }
        row.style.display = hasVisibleItems ? "" : "none";
        lastHeader = null;
        hasVisibleItems = false;
      } else {
        const visible = this.shouldShowRow(row, filterText, filterColumn);
        row.style.display = visible ? "" : "none";
        hasVisibleItems = hasVisibleItems || visible;
      }
    });

    // Handle the last group
    if (lastHeader) {
      lastHeader.style.display = hasVisibleItems ? "" : "none";
    }

    this.updateNoResultsMessage(rows);
  }

  /**
   * Determine if row should be shown based on filter
   */
  shouldShowRow(row, filterText, filterColumn) {
    let text = "";
    if (filterColumn === "all") {
      text = row.textContent.toLowerCase();
    } else {
      const columnIndex = {
        filename: 0,
        sheet: 1,
        cell: 2,
        value: 3,
      }[filterColumn];
      text = row.cells[columnIndex].textContent.toLowerCase();
    }
    return text.includes(filterText);
  }

  /**
   * Update no results message
   */
  updateNoResultsMessage(rows) {
    const visibleRows = rows.filter((row) => row.style.display !== "none");
    const noResults = this.elements.resultsSection.querySelector(".no-results");

    if (visibleRows.length === 0) {
      if (!noResults) {
        const noResultsDiv = createElement("div", {
          class: "no-results",
          textContent: "No matching results found",
        });
        this.elements.resultsSection.appendChild(noResultsDiv);
      }
    } else if (noResults) {
      noResults.remove();
    }
  }

  /**
   * Open file using system default application
   */
  async openFile(filepath) {
    try {
      await this.api.openFile(filepath);
    } catch (error) {
      console.error("Error opening file:", error);
      showError("Failed to open file");
    }
  }
}
