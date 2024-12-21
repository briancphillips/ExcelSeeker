from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename
import os
import xlrd
import tempfile
import logging
import glob
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

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
MAX_WORKERS = 4  # Number of parallel file processing threads

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


def find_excel_files(folder_path):
    """Recursively find all Excel files in the folder and its subdirectories."""
    xls_files = []
    try:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(".xls"):
                    xls_files.append(os.path.join(root, file))
    except Exception as e:
        logger.error(f"Error scanning directory {folder_path}: {str(e)}")
    return xls_files


@app.route("/search_folder", methods=["GET", "POST"])
def search_folder():
    try:
        # Handle both GET and POST requests
        if request.method == "GET":
            folder_path = request.args.get("folder_path")
            search_text = request.args.get("search_text")
        else:
            data = request.get_json()
            folder_path = data.get("folder_path")
            search_text = data.get("search_text")

        if not folder_path or not search_text:
            return jsonify({"error": "Missing folder path or search text"}), 400

        folder_path = os.path.expanduser(folder_path)

        if not os.path.exists(folder_path):
            return jsonify({"error": "Folder path does not exist"}), 400

        if not os.path.isdir(folder_path):
            return jsonify({"error": "Path is not a directory"}), 400

        # Find all .xls files recursively
        xls_files = find_excel_files(folder_path)

        if not xls_files:
            return (
                jsonify(
                    {
                        "error": "No .xls files found in the specified folder or its subdirectories"
                    }
                ),
                400,
            )

        def generate():
            total_files = len(xls_files)
            processed_files = 0
            all_results = []

            def process_file(file_path):
                try:
                    results = search_excel(file_path, search_text)
                    if isinstance(results, list):
                        for result in results:
                            # Use relative path from the selected folder
                            rel_path = os.path.relpath(file_path, folder_path)
                            result["filename"] = rel_path
                        return results
                    return []
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    return []

            # Process files in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_file = {
                    executor.submit(process_file, file_path): file_path
                    for file_path in xls_files
                }

                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        results = future.result()
                        all_results.extend(results)
                        processed_files += 1

                        # Send progress update
                        progress = {
                            "type": "progress",
                            "processed": processed_files,
                            "total": total_files,
                            "current_file": os.path.relpath(file_path, folder_path),
                            "found_results": len(all_results),
                        }
                        yield f"data: {json.dumps(progress)}\n\n"

                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {str(e)}")
                        processed_files += 1

            # Send final results
            final_data = {"type": "complete", "results": all_results}
            yield f"data: {json.dumps(final_data)}\n\n"

        # Set CORS headers for SSE
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }

        return Response(generate(), mimetype="text/event-stream", headers=headers)

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
