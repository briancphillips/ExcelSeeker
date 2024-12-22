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
from threading import Event
from collections import defaultdict
import uuid
import threading

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
SKIP_LIST_FILE = "skip_list.json"

# Track active searches
active_searches = {}
search_events = defaultdict(Event)

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


def load_skip_list():
    """Load the list of files to skip from JSON file."""
    try:
        if os.path.exists(SKIP_LIST_FILE):
            if (
                os.path.getsize(SKIP_LIST_FILE) > 0
            ):  # Only try to load if file is not empty
                try:
                    with open(SKIP_LIST_FILE, "r") as f:
                        return set(json.load(f))
                except json.JSONDecodeError:
                    logger.error("Skip list file is corrupted. Creating new one.")
                    save_skip_list(set())  # Reset the file if corrupted
                    return set()
            else:
                logger.info("Skip list file is empty")
                return set()
        else:
            logger.info("Skip list file does not exist. Creating new one.")
            save_skip_list(set())  # Create the file if it doesn't exist
            return set()
    except Exception as e:
        logger.error(f"Error loading skip list: {e}")
        return set()


def save_skip_list(skip_list):
    """Save the skip list to JSON file."""
    try:
        # Ensure the skip list is a set of strings
        skip_list = set(str(path) for path in skip_list)
        # Convert to list for JSON serialization
        with open(SKIP_LIST_FILE, "w") as f:
            json.dump(list(skip_list), f, indent=2)
    except Exception as e:
        logger.error(f"Error saving skip list: {e}")


def add_to_skip_list(file_path):
    """Add a file to the skip list."""
    try:
        skip_list = load_skip_list()
        skip_list.add(str(os.path.abspath(file_path)))  # Ensure path is string
        save_skip_list(skip_list)
    except Exception as e:
        logger.error(f"Error adding to skip list: {e}")


def process_excel_file(file_path, search_text, search_mode="exact"):
    """Process an Excel file and search for text."""
    try:
        workbook = xlrd.open_workbook(file_path)
        results = []

        # Split search text into keywords for ANY/ALL modes
        search_text = search_text.lower()
        if search_mode in ("any", "all"):
            keywords = list(set(filter(None, search_text.split())))
        else:
            keywords = [search_text]

        for sheet_index in range(workbook.nsheets):
            sheet = workbook.sheet_by_index(sheet_index)
            for row_idx in range(sheet.nrows):
                for col_idx in range(sheet.ncols):
                    try:
                        cell_value = str(sheet.cell_value(row_idx, col_idx)).lower()
                        if not cell_value:
                            continue

                        match = False
                        if search_mode == "exact":
                            match = keywords[0] in cell_value
                        elif search_mode == "any":
                            match = any(keyword in cell_value for keyword in keywords)
                        elif search_mode == "all":
                            match = all(keyword in cell_value for keyword in keywords)

                        if match:
                            results.append(
                                {
                                    "filename": os.path.basename(file_path),
                                    "sheet": sheet.name,
                                    "cell": format_cell_address(
                                        row_idx + 1, col_idx + 1
                                    ),
                                    "value": str(sheet.cell_value(row_idx, col_idx)),
                                }
                            )
                    except Exception as e:
                        logger.error(f"Error processing cell in {file_path}: {str(e)}")
                        continue

        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        return {"error": str(e), "skipped": True}


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
    search_mode = request.form.get("search_mode", "exact")

    if not search_text:
        return jsonify({"error": "No search text provided"}), 400

    if search_mode not in ("exact", "any", "all"):
        return jsonify({"error": "Invalid search mode"}), 400

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
                file_results = process_excel_file(file_path, search_text, search_mode)
                if isinstance(file_results, list):
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

            results = process_excel_file(temp_path, search_text, search_mode)
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


@app.route("/search_folder")
def search_folder():
    search_text = request.args.get("search_text")
    folder_path = request.args.get("folder_path")
    search_mode = request.args.get("search_mode", "exact")

    if not search_text or not folder_path:
        return jsonify({"error": "Missing required parameters"}), 400

    def generate():
        search_id = str(uuid.uuid4())
        cancel_event = threading.Event()
        active_searches[search_id] = cancel_event
        total_results = 0
        all_results = []

        try:
            # Send search ID first
            yield f"data: {json.dumps({'search_id': search_id})}\n\n"

            if not os.path.exists(folder_path):
                yield f"data: {json.dumps({'error': 'Folder not found'})}\n\n"
                return

            xls_files = [
                f
                for f in glob.glob(
                    os.path.join(folder_path, "**/*.xls"), recursive=True
                )
            ]
            if not xls_files:
                yield f"data: {json.dumps({'error': 'No .xls files found in folder'})}\n\n"
                return

            total_files = len(xls_files)
            processed = 0
            skipped_files = []

            for file_path in xls_files:
                # Check for cancellation
                if cancel_event.is_set():
                    logger.info(f"Search {search_id} cancelled")
                    yield f"data: {json.dumps({'type': 'cancelled'})}\n\n"
                    return

                processed += 1
                try:
                    result = process_excel_file(file_path, search_text, search_mode)
                    if "results" in result:
                        all_results.extend(result["results"])
                        total_results += result["count"]
                    elif result.get("skipped"):
                        skipped_files.append(
                            {
                                "file": os.path.basename(file_path),
                                "reason": result.get("error", "Unknown error"),
                            }
                        )
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    skipped_files.append(
                        {"file": os.path.basename(file_path), "reason": str(e)}
                    )
                    continue

                # Send progress update
                progress_data = {
                    "type": "progress",
                    "current_file": os.path.basename(file_path),
                    "processed": processed,
                    "total": total_files,
                    "skipped_files": len(skipped_files),
                    "results_found": total_results,
                }
                yield f"data: {json.dumps(progress_data)}\n\n"

                # Check for cancellation again after progress update
                if cancel_event.is_set():
                    logger.info(f"Search {search_id} cancelled after progress update")
                    yield f"data: {json.dumps({'type': 'cancelled'})}\n\n"
                    return

            # Send completion data
            completion_data = {
                "type": "complete",
                "results": all_results,
                "total_processed": processed,
                "total_skipped": len(skipped_files),
                "skipped_files": skipped_files,
                "total_results": total_results,
            }
            yield f"data: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            logger.error(f"Error in search {search_id}: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        finally:
            logger.info(f"Cleaning up search {search_id}")
            if search_id in active_searches:
                del active_searches[search_id]

    return Response(generate(), mimetype="text/event-stream")


def is_folder_service_running():
    try:
        response = requests.get("http://localhost:3000/health", timeout=1)
        return response.status_code == 200
    except:
        return False


def start_folder_service():
    try:
        # Use the full path to npm
        npm_path = "/opt/homebrew/bin/npm"
        node_path = "/opt/homebrew/bin/node"

        # Start the folder selection service
        process = subprocess.Popen(
            [npm_path, "start"],
            cwd="folder_service",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=dict(
                os.environ, PATH=f"/opt/homebrew/bin:{os.environ.get('PATH', '')}"
            ),
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


@app.route("/skip-list", methods=["GET", "DELETE"])
def manage_skip_list():
    if request.method == "GET":
        skip_list = load_skip_list()
        return jsonify({"skip_list": list(skip_list)})
    elif request.method == "DELETE":
        try:
            # Clear the skip list
            save_skip_list(set())
            return jsonify({"message": "Skip list cleared successfully"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/cancel-search/<search_id>", methods=["POST"])
def cancel_search(search_id):
    """Cancel an active search operation."""
    try:
        if search_id in active_searches:
            logger.info(f"Cancelling search {search_id}")
            active_searches[search_id].set()  # Signal cancellation
            # Wait a moment to ensure the search thread sees the cancellation
            time.sleep(0.1)
            return jsonify({"status": "cancelled", "search_id": search_id})
        logger.warning(f"Search {search_id} not found for cancellation")
        return jsonify({"error": "Search not found"}), 404
    except Exception as e:
        logger.error(f"Error cancelling search {search_id}: {e}")
        return jsonify({"error": str(e)}), 500


def cleanup_search(search_id):
    """Clean up search resources."""
    try:
        if search_id in search_events:
            del search_events[search_id]
        if search_id in active_searches:
            del active_searches[search_id]
    except Exception as e:
        logger.error(f"Error cleaning up search {search_id}: {e}")


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
