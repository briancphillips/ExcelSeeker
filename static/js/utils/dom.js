/**
 * DOM Utilities Module
 */

/**
 * Show error message
 */
export function showError(message, duration = 5000) {
  const errorDiv = document.createElement("div");
  errorDiv.className = "error";
  errorDiv.textContent = message;

  const resultsSection = document.getElementById("resultsSection");
  resultsSection.insertAdjacentElement("beforebegin", errorDiv);

  setTimeout(() => {
    errorDiv.remove();
  }, duration);
}

/**
 * Show success/info message
 */
export function showMessage(message, duration = 5000) {
  const messageDiv = document.createElement("div");
  messageDiv.className = "message";
  messageDiv.textContent = message;

  const resultsSection = document.getElementById("resultsSection");
  resultsSection.insertAdjacentElement("beforebegin", messageDiv);

  setTimeout(() => {
    messageDiv.remove();
  }, duration);
}

/**
 * Toggle element visibility
 */
export function toggleVisibility(element, show) {
  if (show) {
    element.classList.remove("hidden");
  } else {
    element.classList.add("hidden");
  }
}

/**
 * Safely get element by ID with type checking
 */
export function getElement(id) {
  const element = document.getElementById(id);
  if (!element) {
    throw new Error(`Element with id "${id}" not found`);
  }
  return element;
}

/**
 * Update progress bar
 */
export function updateProgress(progressBar, progressText, percentage) {
  progressBar.style.width = `${percentage}%`;
  progressText.textContent = `${Math.round(percentage)}%`;
}

/**
 * Escape HTML to prevent XSS
 */
export function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Create element with attributes and properties
 */
export function createElement(tag, attributes = {}, properties = {}) {
  const element = document.createElement(tag);

  Object.entries(attributes).forEach(([key, value]) => {
    element.setAttribute(key, value);
  });

  Object.entries(properties).forEach(([key, value]) => {
    element[key] = value;
  });

  return element;
}

/**
 * Add event listener with automatic cleanup
 */
export function addEventListenerWithCleanup(
  element,
  eventType,
  handler,
  options = {}
) {
  element.addEventListener(eventType, handler, options);
  return () => element.removeEventListener(eventType, handler, options);
}

/**
 * Debounce function for performance optimization
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Create a loading spinner
 */
export function createSpinner() {
  const spinner = createElement("div", { class: "spinner" });
  return spinner;
}

/**
 * Disable/enable form elements
 */
export function setFormElementsState(form, disabled) {
  const elements = form.querySelectorAll("input, button, select, textarea");
  elements.forEach((element) => {
    element.disabled = disabled;
  });
}

/**
 * Format file size
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

/**
 * Add tooltip to element
 */
export function addTooltip(element, text) {
  element.setAttribute("title", text);
  element.setAttribute("data-tooltip", text);
  return element;
}
