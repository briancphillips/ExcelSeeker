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
import platform
import hashlib
import pickle
from datetime import datetime
import socket
from nlp.search_integration import SearchIntegration
import re
import fnmatch

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
SKIP_LIST_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "skip_list.json"
)
CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "search_cache.pkl"
)
CACHE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds

# Global variables
folder_service_process = None
search_integration = SearchIntegration()

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
                        data = json.load(f)
                        # Handle both old format (list of strings) and new format (dict)
                        if isinstance(data, list):
                            return {path: "Unknown reason" for path in data}
                        return data
                except json.JSONDecodeError:
                    logger.error("Skip list file is corrupted. Creating new one.")
                    save_skip_list({})  # Reset the file if corrupted
                    return {}
            else:
                logger.info("Skip list file is empty")
                return {}
        else:
            logger.info("Skip list file does not exist. Creating new one.")
            save_skip_list({})  # Create the file if it doesn't exist
            return {}
    except Exception as e:
        logger.error(f"Error loading skip list: {e}")
        return {}


def save_skip_list(skip_list):
    """Save the skip list to JSON file."""
    try:
        # Ensure all values are JSON serializable
        serializable_skip_list = {}
        for path, info in skip_list.items():
            if isinstance(info, str):
                # Convert old format to new format
                info = {
                    "reason": info,
                    "timestamp": datetime.now().isoformat(),
                    "file_exists": os.path.exists(path),
                    "file_size": (
                        os.path.getsize(path) if os.path.exists(path) else None
                    ),
                    "is_readable": (
                        os.access(path, os.R_OK) if os.path.exists(path) else False
                    ),
                }
            serializable_skip_list[str(path)] = info

        with open(SKIP_LIST_FILE, "w") as f:
            json.dump(serializable_skip_list, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving skip list: {e}")


def add_to_skip_list(file_path, reason="Unknown error"):
    """Add a file to the skip list with a reason."""
    try:
        skip_list = load_skip_list()
        abs_path = str(os.path.abspath(file_path))
        error_info = {
            "reason": str(reason),
            "timestamp": datetime.now().isoformat(),
            "file_exists": os.path.exists(abs_path),
            "file_size": (
                os.path.getsize(abs_path) if os.path.exists(abs_path) else None
            ),
            "is_readable": (
                os.access(abs_path, os.R_OK) if os.path.exists(abs_path) else False
            ),
        }
        skip_list[abs_path] = error_info
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
                                    "filepath": str(os.path.abspath(file_path)),
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


def calculate_directory_hash(folder_path, skip_list):
    """Calculate a hash of the directory state including file contents and skip list."""
    hasher = hashlib.sha256()

    # Get all Excel files
    xls_files = find_excel_files(folder_path)

    # Sort files for consistent hashing
    xls_files.sort()

    for file_path in xls_files:
        abs_path = str(os.path.abspath(file_path))
        if abs_path in skip_list:
            continue

        try:
            # Add file path, size, and modification time to hash
            stats = os.stat(file_path)
            file_info = f"{abs_path}|{stats.st_size}|{stats.st_mtime}"
            hasher.update(file_info.encode())
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {str(e)}")
            continue

    # Add skip list to hash
    hasher.update(json.dumps(skip_list, sort_keys=True).encode())

    return hasher.hexdigest()


def cleanup_old_cache_entries():
    """Remove cache entries older than CACHE_MAX_AGE."""
    try:
        cache = load_search_cache()
        current_time = datetime.now()
        updated_cache = {}

        for key, data in cache.items():
            try:
                cache_time = datetime.fromisoformat(data["timestamp"])
                if (current_time - cache_time).total_seconds() < CACHE_MAX_AGE:
                    updated_cache[key] = data
            except (ValueError, KeyError):
                # Skip invalid entries
                continue

        if len(updated_cache) != len(cache):
            save_search_cache(updated_cache)
            logger.info(
                f"Cleaned up {len(cache) - len(updated_cache)} old cache entries"
            )
    except Exception as e:
        logger.error(f"Error cleaning up cache: {str(e)}")


def save_search_cache(cache_data):
    """Save search results cache to file."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(cache_data, f)
    except Exception as e:
        logger.error(f"Error saving cache: {str(e)}")


def load_search_cache():
    """Load search results cache from file."""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "rb") as f:
                return pickle.load(f)
    except Exception as e:
        logger.error(f"Error loading cache: {str(e)}")
    return {}


def get_cache_key(folder_path, search_text, search_mode):
    """Generate a cache key for the search parameters."""
    # Include skip list in cache key to invalidate when skip list changes
    skip_list = load_skip_list()
    skip_list_hash = hashlib.sha256(
        json.dumps(skip_list, sort_keys=True).encode()
    ).hexdigest()
    return f"{folder_path}|{search_text}|{search_mode}|{skip_list_hash}"


def search_filenames(
    folder_path,
    search_text,
    use_wildcard=False,
    use_regex=False,
    extension_filter=None,
    path_filter=None,
):
    """Search for files by filename only."""
    results = []

    # Process extension filter
    allowed_extensions = None
    if extension_filter:
        allowed_extensions = set(
            ext.strip().lower() for ext in extension_filter.split(",")
        )

    # Compile regex pattern if using regex
    regex_pattern = None
    if use_regex:
        try:
            regex_pattern = re.compile(search_text, re.IGNORECASE)
        except re.error:
            raise ValueError("Invalid regular expression pattern")

    for root, _, files in os.walk(folder_path):
        # Check path filter if specified
        if path_filter:
            rel_path = os.path.relpath(root, folder_path)
            if not fnmatch.fnmatch(rel_path.lower(), path_filter.lower()):
                continue

        for filename in files:
            # Check file extension if filter is specified
            if allowed_extensions:
                ext = os.path.splitext(filename)[1][1:].lower()
                if ext not in allowed_extensions:
                    continue

            # Get relative path for display
            rel_path = os.path.relpath(os.path.join(root, filename), folder_path)

            # Perform filename matching based on search mode
            match = False
            if use_regex and regex_pattern:
                match = bool(regex_pattern.search(filename))
            elif use_wildcard:
                match = fnmatch.fnmatch(filename.lower(), search_text.lower())
            else:
                match = search_text.lower() in filename.lower()

            if match:
                results.append(
                    {
                        "filename": filename,
                        "filepath": str(os.path.abspath(os.path.join(root, filename))),
                        "relative_path": rel_path,
                        "directory": root,
                        "sheet": "N/A",  # Add these fields to match the expected format
                        "cell": "N/A",  # for the results table
                        "value": filename,  # Use filename as the value
                    }
                )

    return results


@app.route("/search_folder")
def search_folder():
    """Handle folder search request with natural language query support."""
    # Capture all request parameters outside the generator
    folder_path = request.args.get("folder_path")
    search_text = request.args.get("search_text")
    search_mode = request.args.get("search_mode", "exact")

    # Capture filename search parameters if needed
    filename_params = None
    if search_mode == "filename":
        filename_params = {
            "use_wildcard": request.args.get("use_wildcard") == "true",
            "use_regex": request.args.get("use_regex") == "true",
            "extension_filter": request.args.get("extension_filter"),
            "path_filter": request.args.get("path_filter"),
        }

    if not folder_path or not search_text:
        return jsonify({"error": "Missing folder path or search text"}), 400

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

            # Handle filename search mode
            if search_mode == "filename":
                try:
                    # Perform filename search using captured parameters
                    results = search_filenames(
                        folder_path,
                        search_text,
                        filename_params["use_wildcard"],
                        filename_params["use_regex"],
                        filename_params["extension_filter"],
                        filename_params["path_filter"],
                    )

                    # Send progress update
                    progress_data = {
                        "type": "progress",
                        "current_file": "Searching filenames...",
                        "processed": 1,
                        "total": 1,
                        "results_found": len(results),
                    }
                    yield f"data: {json.dumps(progress_data)}\n\n"

                    # Send completion data
                    completion_data = {
                        "type": "complete",
                        "results": results,
                        "total_processed": 1,
                        "total_skipped": 0,
                        "skipped_files": [],
                        "total_results": len(results),
                        "from_cache": False,
                    }
                    yield f"data: {json.dumps(completion_data)}\n\n"
                    return
                except Exception as e:
                    logger.error(f"Error in filename search: {str(e)}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    return

            # Process natural language query for non-filename searches
            search_params = search_integration.process_query(search_text)
            logger.info(f"Processed search parameters: {search_params}")

            # Load skip list
            skip_list = load_skip_list()

            # Calculate directory hash and check cache
            dir_hash = calculate_directory_hash(folder_path, skip_list)
            cache = load_search_cache()
            cache_key = get_cache_key(
                folder_path, json.dumps(search_params), search_mode
            )

            if cache_key in cache and cache[cache_key]["hash"] == dir_hash:
                logger.info("Using cached results")
                cached_data = cache[cache_key]
                cached_response = {
                    "type": "complete",
                    "results": cached_data["results"],
                    "total_processed": cached_data["total_processed"],
                    "total_skipped": cached_data["total_skipped"],
                    "skipped_files": cached_data["skipped_files"],
                    "total_results": len(cached_data["results"]),
                    "from_cache": True,
                }
                yield f"data: {json.dumps(cached_response)}\n\n"
                return

            # Get all XLS files
            xls_files = find_excel_files(folder_path)
            if not xls_files:
                yield f"data: {json.dumps({'error': 'No .xls files found in folder'})}\n\n"
                return

            # Prepare skipped files info
            skipped_files = []

            # Check for previously skipped files in this folder
            for file_path in xls_files:
                abs_path = str(os.path.abspath(file_path))
                if abs_path in skip_list:
                    skipped_files.append(
                        {
                            "file": os.path.basename(file_path),
                            "path": abs_path,
                            "reason": skip_list[abs_path],
                        }
                    )

            # Filter out skipped files from processing list
            xls_files = [
                f for f in xls_files if str(os.path.abspath(f)) not in skip_list
            ]
            total_files = len(xls_files)
            processed = 0

            # If there are previously skipped files, send initial skipped files update
            if skipped_files:
                progress_data = {
                    "type": "progress",
                    "current_file": "Starting search...",
                    "processed": 0,
                    "total": total_files,
                    "skipped_files": len(skipped_files),
                    "results_found": 0,
                }
                yield f"data: {json.dumps(progress_data)}\n\n"

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                for file_path in xls_files:
                    # Check for cancellation
                    if cancel_event.is_set():
                        logger.info(f"Search {search_id} cancelled")
                        # Send partial results if any were found
                        completion_data = {
                            "type": "cancelled",
                            "results": all_results,
                            "total_processed": processed,
                            "total_skipped": len(skipped_files),
                            "skipped_files": skipped_files,
                            "total_results": total_results,
                            "partial": True,
                        }
                        yield f"data: {json.dumps(completion_data)}\n\n"
                        return

                    processed += 1
                    try:
                        # Use search parameters from NLP processing
                        result = process_excel_file(
                            file_path,
                            search_params["search_text"],
                            search_params.get("search_mode", search_mode),
                        )

                        if "results" in result:
                            # Apply NLP-based filters to results
                            filtered_results = search_integration.apply_filters(
                                result["results"], search_params.get("filters", {})
                            )
                            all_results.extend(filtered_results)
                            total_results += len(filtered_results)
                        elif result.get("skipped"):
                            error_msg = result.get("error", "Unknown error")
                            skipped_files.append(
                                {
                                    "file": os.path.basename(file_path),
                                    "reason": error_msg,
                                }
                            )
                            # Add to persistent skip list
                            add_to_skip_list(file_path, error_msg)
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"Error processing {file_path}: {error_msg}")
                        skipped_files.append(
                            {"file": os.path.basename(file_path), "reason": error_msg}
                        )
                        # Add to persistent skip list
                        add_to_skip_list(file_path, error_msg)
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
                        logger.info(
                            f"Search {search_id} cancelled after progress update"
                        )
                        # Send partial results if any were found
                        completion_data = {
                            "type": "cancelled",
                            "results": all_results,
                            "total_processed": processed,
                            "total_skipped": len(skipped_files),
                            "skipped_files": skipped_files,
                            "total_results": total_results,
                            "partial": True,
                        }
                        yield f"data: {json.dumps(completion_data)}\n\n"
                        return

            # Store results in cache
            cache_data = {
                "hash": dir_hash,
                "timestamp": datetime.now().isoformat(),
                "results": all_results,
                "total_processed": processed,
                "total_skipped": len(skipped_files),
                "skipped_files": skipped_files,
            }
            cache[cache_key] = cache_data
            save_search_cache(cache)

            # Send completion data
            completion_data = {
                "type": "complete",
                "results": all_results,
                "total_processed": processed,
                "total_skipped": len(skipped_files),
                "skipped_files": skipped_files,
                "total_results": total_results,
                "from_cache": False,
            }
            logger.info(f"Search completed. Sending completion data: {completion_data}")
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
        # Use the full path to npm and node
        npm_path = "/opt/homebrew/bin/npm"
        node_path = "/opt/homebrew/bin/node"

        # Verify port is available before starting
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.bind(("127.0.0.1", 3000))
                s.close()
        except socket.error as e:
            logger.error(f"Port 3000 is not available for service startup: {e}")
            return None

        # Set up environment with proper PATH
        env = dict(os.environ)
        env["PATH"] = f"/opt/homebrew/bin:{env.get('PATH', '')}"

        # Start the folder selection service
        process = subprocess.Popen(
            [npm_path, "start"],
            cwd="folder_service",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            env=env,
            preexec_fn=os.setsid if platform.system() != "Windows" else None,
        )

        # Wait for service to start (max 10 seconds)
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                response = requests.get("http://localhost:3000/health", timeout=1)
                if response.status_code == 200:
                    logger.info("Folder selection service started successfully")
                    return process
            except requests.exceptions.RequestException:
                time.sleep(0.5)
                continue

        # If we get here, service didn't start
        logger.error("Folder service failed to start within timeout period")
        try:
            if platform.system() != "Windows":
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.terminate()
            process.wait(timeout=5)
        except Exception as e:
            logger.warning(f"Error terminating failed service startup: {e}")

        return None
    except Exception as e:
        logger.error(f"Error starting folder service: {str(e)}")
        return None


def cleanup_services(folder_service_process):
    """Clean up services and ensure ports are released."""
    if folder_service_process:
        try:
            logger.info("Shutting down folder selection service...")

            if platform.system().lower() == "darwin":  # macOS
                try:
                    # First, try to get all PIDs using port 3000
                    try:
                        # Direct command to get PIDs, avoiding shell=True
                        port_pids = subprocess.check_output(
                            ["lsof", "-t", "-i", ":3000"]
                        )
                        pids = port_pids.decode().strip().split("\n")

                        # Kill each process individually
                        for pid in pids:
                            if pid:  # Ensure PID is not empty
                                try:
                                    pid = int(pid)
                                    os.kill(pid, signal.SIGKILL)
                                    logger.info(f"Killed process {pid}")
                                except (ValueError, ProcessLookupError) as e:
                                    logger.warning(f"Failed to kill process {pid}: {e}")
                    except subprocess.CalledProcessError:
                        logger.info("No processes found on port 3000")

                    # Kill specific processes
                    process_patterns = [
                        "node.*folder_service",
                        "electron.*folder_service",
                        "Electron",
                    ]

                    for pattern in process_patterns:
                        try:
                            pids = subprocess.check_output(["pgrep", "-f", pattern])
                            for pid in pids.decode().strip().split("\n"):
                                if pid:  # Ensure PID is not empty
                                    try:
                                        pid = int(pid)
                                        os.kill(pid, signal.SIGKILL)
                                        logger.info(
                                            f"Killed process {pid} matching {pattern}"
                                        )
                                    except (ValueError, ProcessLookupError) as e:
                                        logger.warning(
                                            f"Failed to kill process {pid}: {e}"
                                        )
                        except subprocess.CalledProcessError:
                            logger.info(f"No processes found matching {pattern}")

                except Exception as e:
                    logger.warning(f"Error during macOS cleanup: {str(e)}")

            elif platform.system().lower() == "windows":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(folder_service_process.pid)],
                    check=False,
                )
            else:  # Linux
                try:
                    os.killpg(os.getpgid(folder_service_process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    logger.warning("Process group already terminated")

            # Wait for processes to terminate
            time.sleep(2)

            # Verify port is released
            max_attempts = 5
            attempt = 0
            while attempt < max_attempts:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        s.bind(("127.0.0.1", 3000))
                        s.close()
                        logger.info("Port 3000 successfully released")
                        return True
                except socket.error:
                    logger.warning(
                        f"Port 3000 still in use, attempt {attempt + 1}/{max_attempts}"
                    )
                    if platform.system().lower() == "darwin":
                        try:
                            # Try one more time to find and kill processes on port 3000
                            port_pids = subprocess.check_output(
                                ["lsof", "-t", "-i", ":3000"]
                            )
                            for pid in port_pids.decode().strip().split("\n"):
                                if pid:
                                    try:
                                        pid = int(pid)
                                        os.kill(pid, signal.SIGKILL)
                                    except (ValueError, ProcessLookupError):
                                        pass
                        except subprocess.CalledProcessError:
                            pass
                    time.sleep(2)
                    attempt += 1

            if attempt == max_attempts:
                logger.error("Failed to release port 3000 after multiple attempts")
                return False

            logger.info("Service cleanup completed")
            return True
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return False


@app.route("/skip-list", methods=["GET", "DELETE"])
def manage_skip_list():
    if request.method == "GET":
        skip_list = load_skip_list()
        # Convert to list of objects with full path information
        skip_list_array = [
            {
                "file": os.path.basename(path),
                "directory": os.path.dirname(path),
                "path": path,
                "reason": reason,
                "timestamp": os.path.getmtime(path) if os.path.exists(path) else None,
            }
            for path, reason in skip_list.items()
        ]
        return jsonify({"skip_list": skip_list_array})
    elif request.method == "DELETE":
        try:
            # Clear the skip list
            save_skip_list({})
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


@app.route("/open-file", methods=["POST"])
def open_file():
    """Open a file using the system's default application."""
    try:
        data = request.get_json()
        if not data or "filepath" not in data:
            return jsonify({"error": "No file path provided"}), 400

        filepath = data["filepath"]
        if not os.path.exists(filepath):
            return jsonify({"error": "File not found"}), 404

        # Use the appropriate command based on the operating system
        system = platform.system().lower()
        try:
            if system == "darwin":  # macOS
                subprocess.run(["open", filepath])
            elif system == "windows":
                subprocess.run(["start", filepath], shell=True)
            elif system == "linux":
                subprocess.run(["xdg-open", filepath])
            else:
                return jsonify({"error": "Unsupported operating system"}), 400

            return jsonify({"message": "File opened successfully"})
        except subprocess.SubprocessError as e:
            return jsonify({"error": f"Failed to open file: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/restart-services", methods=["POST"])
def restart_services():
    """Restart both the Flask app and folder service."""
    global folder_service_process
    try:
        # Stop the folder service if it's running
        if folder_service_process:
            logger.info("Stopping existing folder service...")
            if not cleanup_services(folder_service_process):
                raise Exception("Failed to clean up existing services")
            folder_service_process = None

        # Additional cleanup for macOS
        if platform.system().lower() == "darwin":
            try:
                # Try to find and kill any remaining processes
                try:
                    port_pids = subprocess.check_output(["lsof", "-t", "-i", ":3000"])
                    for pid in port_pids.decode().strip().split("\n"):
                        if pid:
                            try:
                                pid = int(pid)
                                os.kill(pid, signal.SIGKILL)
                                logger.info(f"Killed remaining process {pid}")
                            except (ValueError, ProcessLookupError) as e:
                                logger.warning(f"Failed to kill process {pid}: {e}")
                except subprocess.CalledProcessError:
                    logger.info("No remaining processes found on port 3000")
            except Exception as e:
                logger.warning(f"Error during additional macOS cleanup: {str(e)}")

        # Give the system time to fully release resources
        time.sleep(3)

        # Final port check before starting new service
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.bind(("127.0.0.1", 3000))
                s.close()
        except socket.error as e:
            logger.error(f"Port 3000 still in use after all cleanup attempts: {e}")
            raise Exception("Port 3000 still in use after cleanup")

        # Start the folder service again
        logger.info("Starting new folder service...")
        new_folder_service = start_folder_service()
        if not new_folder_service:
            raise Exception("Failed to restart folder service")

        # Verify the service is responding
        start_time = time.time()
        while time.time() - start_time < 10:
            if is_folder_service_running():
                folder_service_process = new_folder_service
                logger.info("Services restarted successfully")
                return jsonify({"message": "Services restarted successfully"})
            time.sleep(0.5)

        raise Exception("Folder service not responding after restart")
    except Exception as e:
        logger.error(f"Error restarting services: {str(e)}")
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
