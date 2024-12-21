from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import xlrd
import tempfile
from pathlib import Path

app = Flask(__name__)

# Configuration
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
app.config["UPLOAD_FOLDER"] = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {"xls"}


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
                                "file": os.path.basename(file_path),
                                "sheet": sheet.name,
                                "row": row_idx + 1,
                                "column": col_idx + 1,
                                "value": cell_value,
                            }
                        )
        return results
    except Exception as e:
        return {"error": f"Error in file {os.path.basename(file_path)}: {str(e)}"}


def search_folder(folder_path, search_text):
    all_results = []
    errors = []

    try:
        # Convert folder path to absolute path
        folder_path = os.path.abspath(folder_path)

        # Scan for all .xls files in the folder
        for file_path in Path(folder_path).rglob("*.xls"):
            try:
                results = search_excel(str(file_path), search_text)
                if isinstance(results, list):
                    all_results.extend(results)
                elif isinstance(results, dict) and "error" in results:
                    errors.append(results["error"])
            except Exception as e:
                errors.append(f"Error processing {file_path.name}: {str(e)}")

        return {
            "results": all_results,
            "errors": errors if errors else None,
            "total_files": len(list(Path(folder_path).rglob("*.xls"))),
        }
    except Exception as e:
        return {"error": f"Error accessing folder: {str(e)}"}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    search_text = request.form.get("search_text", "")
    search_type = request.form.get("search_type", "file")  # 'file' or 'folder'

    if search_type == "file":
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return (
                jsonify({"error": "Invalid file type. Only .xls files are allowed"}),
                400,
            )

        try:
            filename = secure_filename(file.filename)
            temp_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(temp_path)

            results = search_excel(temp_path, search_text)

            # Clean up temporary file
            os.remove(temp_path)

            return jsonify(
                {
                    "results": results if isinstance(results, list) else [],
                    "errors": (
                        [results["error"]]
                        if isinstance(results, dict) and "error" in results
                        else None
                    ),
                    "total_files": 1,
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif search_type == "folder":
        folder_path = request.form.get("folder_path", "")
        if not folder_path:
            return jsonify({"error": "No folder path provided"}), 400

        if not os.path.isdir(folder_path):
            return jsonify({"error": "Invalid folder path"}), 400

        results = search_folder(folder_path, search_text)
        if "error" in results:
            return jsonify({"error": results["error"]}), 500

        return jsonify(results)

    return jsonify({"error": "Invalid search type"}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5001)
