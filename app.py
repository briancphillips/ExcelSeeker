from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename
import os
import xlrd
import tempfile
import logging
import glob
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import requests
import time
import signal
import atexit

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


def format_cell_address(row, col):
    """Convert row and column numbers to Excel cell reference."""
    col_str = ""
    while col:
        col, remainder = divmod(col - 1, 26)
        col_str = chr(65 + remainder) + col_str
    return f"{col_str}{row}"


def process_excel_file(file_path, search_text):
    try:
        workbook = xlrd.open_workbook(file_path)
        results = []

        for sheet_index in range(workbook.nsheets):
            sheet = workbook.sheet_by_index(sheet_index)
            for row_idx in range(sheet.nrows):
                for col_idx in range(sheet.ncols):
                    cell_value = str(sheet.cell_value(row_idx, col_idx))
                    if search_text.lower() in cell_value.lower():
                        results.append(
                            {
                                "filename": os.path.basename(file_path),
                                "sheet": sheet.name,
                                "cell": xlrd.colname(col_idx) + str(row_idx + 1),
                                "value": cell_value,
                            }
                        )
        return results
    except xlrd.XLRDError as e:
        # Handle specific Excel file errors
        error_msg = str(e)
        if "Unsupported format" in error_msg:
            app.logger.error(f"File format not supported: {file_path}")
            return {
                "error": "This Excel file format is not supported. Please ensure it is a valid .xls file."
            }
        elif "Password protected" in error_msg:
            app.logger.error(f"Password protected file: {file_path}")
            return {
                "error": "This Excel file is password protected and cannot be read."
            }
        else:
            app.logger.error(f"Error processing file {file_path}: {e}")
            return {
                "error": "Unable to read this Excel file. Please ensure it is not corrupted."
            }
    except Exception as e:
        app.logger.error(f"Unexpected error processing file {file_path}: {e}")
        return {"error": "An unexpected error occurred while reading this file."}


@app.route("/")
def index():
    try:
        return render_template("index.html")
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return f"Error: {str(e)}", 500


@app.route("/search", methods=["POST"])
def search():
    """Handle search request and return results."""
    if "file" not in request.files and "folder_path" not in request.form:
        return jsonify({"error": "No file or folder path provided"}), 400

    search_text = request.form.get("search_text", "").strip()
    if not search_text:
        return jsonify({"error": "No search text provided"}), 400

    results = []
    total_files = 0
    processed_files = 0

    try:
        if "folder_path" in request.form:
            folder_path = request.form["folder_path"]
            if not os.path.isdir(folder_path):
                return jsonify({"error": "Invalid folder path"}), 400

            excel_files = []
            for root, _, files in os.walk(folder_path):
                excel_files.extend(
                    [os.path.join(root, f) for f in files if f.endswith(".xls")]
                )

            total_files = len(excel_files)

            for file_path in excel_files:
                file_results = process_excel_file(file_path, search_text)
                results.extend(file_results)
                processed_files += 1

                # Send progress update
                progress = int((processed_files / total_files) * 100)
                sse.publish(
                    {"progress": progress, "file": os.path.basename(file_path)},
                    type="progress",
                )

        else:
            file = request.files["file"]
            if not file or not file.filename.endswith(".xls"):
                return jsonify({"error": "Invalid file type"}), 400

            temp_path = os.path.join(
                app.config["UPLOAD_FOLDER"], secure_filename(file.filename)
            )
            file.save(temp_path)

            results = process_excel_file(temp_path, search_text)
            os.remove(temp_path)  # Clean up temporary file

        return jsonify(results)

    except Exception as e:
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
                    results = process_excel_file(file_path, search_text)
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


def is_folder_service_running():
    try:
        response = requests.get("http://localhost:3000/health", timeout=1)
        return response.status_code == 200
    except:
        return False


def start_folder_service():
    try:
        # Start the folder selection service
        process = subprocess.Popen(
            ["npm", "start"],
            cwd="folder_service",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        # Wait for service to start (max 10 seconds)
        start_time = time.time()
        while time.time() - start_time < 10:
            if is_folder_service_running():
                logger.info("Folder selection service started successfully")
                return process
            time.sleep(0.5)

        # If we get here, service didn't start
        process.terminate()
        raise Exception("Folder selection service failed to start")
    except Exception as e:
        logger.error(f"Error starting folder service: {str(e)}")
        return None


def cleanup_services(folder_service_process):
    if folder_service_process:
        logger.info("Shutting down folder selection service...")
        folder_service_process.terminate()
        try:
            folder_service_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            folder_service_process.kill()


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

        # Start folder selection service if not running
        folder_service_process = None
        if not is_folder_service_running():
            logger.info("Starting folder selection service...")
            folder_service_process = start_folder_service()
            if not folder_service_process:
                logger.warning(
                    "Failed to start folder selection service. Folder selection will not be available."
                )
        else:
            logger.info("Folder selection service is already running")

        # Register cleanup function
        atexit.register(cleanup_services, folder_service_process)

        # Start the server
        print("\nStarting server on http://127.0.0.1:8080")
        print("You can also try: http://localhost:8080")
        print("Press Ctrl+C to quit\n")
        app.run(debug=True, port=8080, host="0.0.0.0")
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        print(f"Error: {str(e)}")
        if folder_service_process:
            cleanup_services(folder_service_process)
