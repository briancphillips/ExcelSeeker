# ExcelSeeker

A web-based application for searching through Excel (.xls) files with real-time progress tracking and advanced features.

## Features

- Upload and search through .xls files
- Folder-based search with recursive scanning
- Real-time search progress tracking
- Search cancellation support
- Skipped files tracking and management
- Dark mode support
- Native folder selection dialog
- Result filtering and sorting
- Clean and responsive interface
- Automatic service management
- Corrupted file handling
- Progress indicators
- Result caching for better performance

## Prerequisites

- Python 3.6 or higher
- Node.js and npm (for native folder selection)

## Quick Start (macOS/Linux)

1. Clone the repository:

```bash
git clone <repository-url>
cd ExcelSeeker
```

2. Make the run script executable:

```bash
chmod +x run.sh
```

3. Start the application:

```bash
./run.sh
```

The script will automatically:

- Create and activate a Python virtual environment
- Install Python dependencies
- Install Node.js dependencies
- Start both the Flask application and folder selection service
- Clean up processes on exit

## Manual Setup

If you prefer to set up the services manually:

1. Create and activate a Python virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
.\venv\Scripts\activate  # On Windows
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install and start the folder selection service:

```bash
cd folder_service
npm install
npm start
```

4. In a new terminal, start the main application:

```bash
cd ..  # Back to root directory
python app.py
```

## Usage

1. Open your browser and navigate to `http://localhost:8080`

2. Choose your search mode:

   - **Single File**: Upload and search within a single .xls file
   - **Folder**: Search through all .xls files in a selected folder and subfolders

3. Select your search options:

   - **Exact phrase**: Match the exact search text
   - **Any keywords**: Match any of the words in the search text
   - **All keywords**: Match all words in the search text

4. Enter your search text and start the search

5. During folder searches:

   - View real-time progress updates
   - Cancel the search at any time
   - See which files were skipped and why
   - Clear the skip list if needed

6. Working with results:
   - Filter results by any column
   - Sort results by clicking column headers
   - Toggle between light and dark mode
   - View detailed file information

## Architecture

The application consists of two main components:

1. **Flask Backend (Port 8080)**

   - Handles file processing and search
   - Manages search cancellation
   - Provides real-time progress updates
   - Handles skip list management
   - Serves the web interface

2. **Folder Selection Service (Port 3000)**
   - Node.js + Electron service
   - Provides native folder selection dialog
   - Cross-platform compatibility

## Development

- The application uses Flask for the backend
- Frontend is built with vanilla JavaScript
- Excel file processing uses xlrd library
- Native folder selection uses Electron
- Real-time updates via Server-Sent Events (SSE)
- Progress tracking with event-based architecture

## License

MIT License
