#!/usr/bin/python
import os
import time
import threading
import webbrowser
import shutil
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_file
from AbbyyOnlineSdk import AbbyyOnlineSdk, ProcessingSettings

UPLOAD_FOLDER = Path("uploads")
RESULT_FOLDER = Path("results")
UPLOAD_FOLDER.mkdir(exist_ok=True)
RESULT_FOLDER.mkdir(exist_ok=True)

DEFAULT_APP_ID   = os.environ.get("ABBYY_APP_ID", "")
DEFAULT_PASSWORD = os.environ.get("ABBYY_PASSWORD", "")
DEFAULT_REGION   = os.environ.get("ABBYY_REGION", "https://cloud-westus.ocrsdk.com")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024


@app.route("/")
def index():
    return render_template("index.html",
        default_app_id=DEFAULT_APP_ID,
        default_password=DEFAULT_PASSWORD,
        default_region=DEFAULT_REGION,
        use_env=bool(DEFAULT_APP_ID and DEFAULT_PASSWORD)
    )


@app.route("/ocr", methods=["POST"])
def ocr():
    app_id   = request.form.get("appId", "").strip() or DEFAULT_APP_ID
    password = request.form.get("password", "").strip() or DEFAULT_PASSWORD
    language = request.form.get("language", "Indonesian")
    fmt      = request.form.get("exportFormat", "txt")
    region   = request.form.get("region", DEFAULT_REGION)

    if not app_id or not password:
        return jsonify({"error": "Kredensial tidak ditemukan. Set env var ABBYY_APP_ID dan ABBYY_PASSWORD."}), 400

    if "file" not in request.files or request.files["file"].filename == "":
        return jsonify({"error": "Pilih file terlebih dahulu."}), 400

    f = request.files["file"]
    filename = f.filename
    save_path = UPLOAD_FOLDER / filename
    f.save(str(save_path))

    sdk = AbbyyOnlineSdk()
    sdk.ApplicationId = app_id
    sdk.Password = password
    sdk.ServerUrl = region.rstrip("/") + "/"

    settings = ProcessingSettings()
    settings.Language = language
    settings.OutputFormat = fmt

    try:
        task = sdk.process_image(str(save_path), settings)
        if task.Status == "NotEnoughCredits":
            return jsonify({"error": "Kredit ABBYY tidak mencukupi."}), 402

        waited = 0
        while task.is_active() and waited < 180:
            time.sleep(3)
            waited += 3
            task = sdk.get_task_status(task)

        if task.is_active():
            return jsonify({"error": "Timeout: OCR terlalu lama, coba lagi."}), 504
        if task.Status != "Completed":
            return jsonify({"error": f"OCR gagal: {task.Status}"}), 500

        if fmt == "txt":
            result_text = sdk.download_result_text(task)
            return jsonify({
                "success": True, "format": fmt, "filename": filename,
                "text": result_text,
                "words": len(result_text.split()),
                "chars": len(result_text),
                "lines": result_text.count("\n") + 1,
            })
        else:
            ext_map = {"docx":".docx","xlsx":".xlsx","pdfSearchable":".pdf","pdfTextAndImages":".pdf","rtf":".rtf","xml":".xml"}
            out_name = Path(filename).stem + "_hasil" + ext_map.get(fmt, ".bin")
            out_path = RESULT_FOLDER / out_name
            sdk.download_result(task, str(out_path))
            return jsonify({"success": True, "format": fmt, "filename": filename, "download_name": out_name})

    except Exception as e:
        msg = str(e)
        if "401" in msg: msg = "Autentikasi gagal. Periksa Application ID dan Password."
        elif "403" in msg: msg = "Akses ditolak (403). Periksa Application ID, Password, dan Region server."
        elif "400" in msg: msg = "Request tidak valid. Periksa format file."
        return jsonify({"error": msg}), 500
    finally:
        try: save_path.unlink()
        except: pass


@app.route("/download/<filename>")
def download(filename):
    path = RESULT_FOLDER / filename
    if not path.exists():
        return "File tidak ditemukan", 404
    return send_file(str(path), as_attachment=True, download_name=filename)


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 3131))
    IS_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT"))

    print("\n" + "="*48)
    print("  Dokumen Ekstraksi AI — ABBYY OCR")
    print("="*48)
    print(f"\n  ✅  http://localhost:{PORT}")
    if not IS_RAILWAY:
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    print("  Ctrl+C untuk berhenti.\n")
    app.run(host="0.0.0.0", port=PORT, debug=False)
