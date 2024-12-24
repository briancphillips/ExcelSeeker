/**
 * Theme Manager - Handles theme switching and persistence
 */
export class ThemeManager {
  constructor() {
    this.setupElements();
    this.loadSavedTheme();
    this.setupEventListeners();
  }

  /**
   * Initialize required DOM elements
   */
  setupElements() {
    this.elements = {
      html: document.documentElement,
      themeToggle: document.getElementById("themeToggle"),
      sunIcon: document.querySelector(".sun-icon"),
      moonIcon: document.querySelector(".moon-icon"),
    };
  }

  /**
   * Load saved theme preference
   */
  loadSavedTheme() {
    const savedTheme = localStorage.getItem("theme") || "light";
    this.setTheme(savedTheme);
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    this.elements.themeToggle.addEventListener("click", () => {
      const currentTheme = this.elements.html.getAttribute("data-theme");
      const newTheme = currentTheme === "light" ? "dark" : "light";
      this.setTheme(newTheme);
    });
  }

  /**
   * Set theme and update UI
   */
  setTheme(theme) {
    this.elements.html.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
    this.updateThemeIcon(theme === "dark");
  }

  /**
   * Update theme icon visibility
   */
  updateThemeIcon(isDark) {
    if (isDark) {
      this.elements.sunIcon.style.display = "none";
      this.elements.moonIcon.style.display = "block";
    } else {
      this.elements.sunIcon.style.display = "block";
      this.elements.moonIcon.style.display = "none";
    }
  }
}
