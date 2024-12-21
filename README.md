# ExcelSeeker

A web-based application for searching through Excel (.xls) files.

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

3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

4. Install and start the folder selection service:

```bash
cd folder_service
npm install
npm start
```

5. In a new terminal, start the main application:

```bash
cd ..  # Back to root directory
python app.py
```

6. Open your browser and navigate to `http://localhost:8080`

## Features

- Upload .xls files
- Search through Excel files for specific text
- Real-time search results
- Clean and responsive interface
- Native folder selection dialog
- Dark mode support

## Development

- Python 3.6 or higher required
- Node.js and npm for folder selection service
- Uses Flask web framework
- xlrd for Excel file processing
- Electron for native dialogs

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

## License

MIT License
