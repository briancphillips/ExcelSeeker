# ExcelSeeker

A powerful web-based application for searching through Excel (.xls) files. ExcelSeeker allows you to search through single files or entire folders of Excel files with ease.

## Quick Start

### Windows

1. Download the repository
2. Double-click `install.bat`
3. Once installation is complete, double-click `start.bat`
4. Open `http://localhost:5001` in your browser

### macOS/Linux

1. Download the repository
2. Open Terminal in the repository folder
3. Run:

```bash
chmod +x install.sh start.sh  # Make scripts executable
./install.sh                  # Install dependencies
./start.sh                   # Start the application
```

4. Open `http://localhost:5001` in your browser

## Features

- 🔍 **Smart Search**

  - Search through single Excel files or entire folders
  - Case-insensitive text search across all cells
  - Real-time search results
  - Detailed results showing file, sheet, row, and column information

- 📊 **File Support**

  - Support for .xls files
  - Multiple file search capability
  - File size limit of 16MB per file
  - Automatic file cleanup after processing

- 🎨 **User Interface**

  - Clean, modern design
  - Responsive layout for all devices
  - Real-time loading indicators
  - Clear error messaging
  - Detailed search results display

- 🛡️ **Security**
  - File type validation
  - Secure file handling
  - Input sanitization
  - Temporary file cleanup

## Setup Instructions

1. Clone the repository:

```bash
git clone <repository-url>
cd ExcelSeeker
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the application:

```bash
python app.py
```

5. Open your browser and navigate to `http://localhost:5001`

## Usage

1. **Single File Search**:

   - Select "Single File" search type
   - Click "Choose Excel File" to select a .xls file
   - Enter your search text
   - Click "Search"

2. **Folder Search**:

   - Select "Folder" search type
   - Enter the full path to your folder
   - Enter your search text
   - Click "Search"

3. **Understanding Results**:
   - Results show file name, sheet name, row, column, and matching value
   - Stats display total matches and files searched
   - Any errors during search are clearly displayed

## Requirements

- Python 3.6 or higher
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Operating System: Windows, macOS, or Linux

## Development

The application is built with:

- Backend: Flask (Python)
- Frontend: HTML, CSS, JavaScript (vanilla)
- Excel Processing: xlrd library

## Project Structure

```
excel_seeker/
├── app.py              # Main Flask application
├── templates/          # HTML templates
│   └── index.html     # Main interface
├── static/            # Static assets
│   └── style.css     # Styling
├── requirements.txt   # Python dependencies
└── README.md         # Documentation
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

MIT License

## Acknowledgments

- Flask web framework
- xlrd Excel processing library
- Modern web development best practices
