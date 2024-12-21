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

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the application:

```bash
python app.py
```

5. Open your browser and navigate to `http://localhost:5000`

## Features

- Upload .xls files
- Search through Excel files for specific text
- Real-time search results
- Clean and responsive interface

## Development

- Python 3.6 or higher required
- Uses Flask web framework
- xlrd for Excel file processing

## License

MIT License
