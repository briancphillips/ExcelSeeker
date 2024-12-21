from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import xlrd
import tempfile
import logging
import glob

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
app.config["UPLOAD_FOLDER"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "temp"
)
ALLOWED_EXTENSIONS = {"xls"}

# Ensure temp directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def search_excel(file_path, search_text):
    results = []
    try:
        workbook = xlrd.open_workbook(file_path)
        for sheet_idx in range(workbook.nsheets):
            sheet = workbook.sheet_by_index(sheet_idx)
            for row_idx in range(sheet.nrows):
                for col_idx in range(sheet.ncols):
                    cell_value = str(sheet.cell_value(row_idx, col_idx))
                    if search_text.lower() in cell_value.lower():
                        results.append(
                            {
                                "sheet": sheet.name,
                                "row": row_idx + 1,
                                "column": col_idx + 1,
                                "value": cell_value,
                            }
                        )
        return results
    except Exception as e:
        logger.error(f"Error processing Excel file: {str(e)}")
        return {"error": str(e)}


@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return f"Error: {str(e)}", 500


@app.route("/search", methods=["POST"])
def search():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        search_text = request.form.get("search_text", "")

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return (
                jsonify({"error": "Invalid file type. Only .xls files are allowed"}),
                400,
            )

        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)

        file.save(temp_path)
        logger.debug(f"File saved to: {temp_path}")

        results = search_excel(temp_path, search_text)

        # Clean up temporary file
        try:
            os.remove(temp_path)
            logger.debug(f"Temporary file removed: {temp_path}")
        except Exception as e:
            logger.warning(f"Error removing temporary file: {str(e)}")

        return jsonify(results)
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/search_folder", methods=["POST"])
def search_folder():
    try:
        data = request.get_json()
        if not data or "folder_path" not in data or "search_text" not in data:
            return jsonify({"error": "Missing folder path or search text"}), 400

        folder_path = os.path.expanduser(data["folder_path"])
        search_text = data["search_text"]

        if not os.path.exists(folder_path):
            return jsonify({"error": "Folder path does not exist"}), 400

        if not os.path.isdir(folder_path):
            return jsonify({"error": "Path is not a directory"}), 400

        # Find all .xls files in the folder
        xls_files = glob.glob(os.path.join(folder_path, "*.xls"))

        if not xls_files:
            return (
                jsonify({"error": "No .xls files found in the specified folder"}),
                400,
            )

        all_results = []
        for file_path in xls_files:
            try:
                results = search_excel(file_path, search_text)
                if isinstance(results, list):  # Only add if search was successful
                    for result in results:
                        result["filename"] = os.path.basename(file_path)
                        all_results.append(result)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                continue

        return jsonify(all_results)
    except Exception as e:
        logger.error(f"Error in search_folder endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    try:
        # Ensure the application can find its templates and static files
        template_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "templates"
        )
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

        if not os.path.exists(template_dir):
            raise RuntimeError(f"Template directory not found: {template_dir}")
        if not os.path.exists(static_dir):
            raise RuntimeError(f"Static directory not found: {static_dir}")

        logger.info(f"Template directory: {template_dir}")
        logger.info(f"Static directory: {static_dir}")

        # Start the server
        print("\nStarting server on http://127.0.0.1:8080")
        print("You can also try: http://localhost:8080")
        print("Press Ctrl+C to quit\n")
        app.run(debug=True, port=8080, host="0.0.0.0")
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        print(f"Error: {str(e)}")
