# ExcelSeeker

A web-based application for searching through Excel (.xls) files.

## Features

- Upload .xls files
- Search through Excel files for specific text
- Real-time search results
- Clean and responsive interface
- Native folder selection dialog
- Dark mode support
- Multi-file search support

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
2. Choose between:
   - Single file upload: Select an .xls file directly
   - Folder search: Use the native folder selection dialog
3. Enter your search text
4. View results in real-time

## Architecture

The application consists of two main components:

1. **Flask Backend (Port 8080)**

   - Handles file processing and search
   - Serves the web interface
   - Manages file operations

2. **Folder Selection Service (Port 3000)**
   - Node.js + Electron service
   - Provides native folder selection dialog
   - Cross-platform compatibility

## Development

- The application uses Flask for the backend
- Frontend is built with vanilla JavaScript
- Excel file processing uses xlrd library
- Native folder selection uses Electron

## License

MIT License
