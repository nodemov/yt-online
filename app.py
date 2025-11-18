from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import os
import subprocess
import re
from datetime import datetime

STORAGE = "/data"

app = Flask(__name__)

@app.template_filter('strftime')
def _jinja2_filter_datetime(timestamp, fmt='%Y-%m-%d %H:%M:%S'):
    return datetime.fromtimestamp(timestamp).strftime(fmt)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("url")
        format_type = request.form.get("format", "mp4")
        if url:
            # Format selection
            if format_type == "m4a":
                format_arg = "bestaudio[ext=m4a]/bestaudio"
            else:  # mp4
                format_arg = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best"
            
            # Run yt-dlp
            subprocess.run([
                "yt-dlp",
                "-f", format_arg,
                "-o", f"{STORAGE}/%(title)s.%(ext)s",
                url
            ])
        return redirect(url_for("index"))

    # List downloaded files with metadata
    files = []
    for filename in os.listdir(STORAGE):
        file_path = os.path.join(STORAGE, filename)
        if os.path.isfile(file_path):
            stat = os.stat(file_path)
            files.append({
                'name': filename,
                'size': stat.st_size,
                'created': stat.st_ctime
            })
    # Sort by creation time, newest first
    files.sort(key=lambda x: x['created'], reverse=True)
    return render_template("index.html", files=files)

@app.route("/download_with_progress", methods=["POST"])
def download_with_progress():
    url = request.json.get("url")
    format_type = request.json.get("format", "mp4")
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    
    def generate():
        # Format selection
        if format_type == "m4a":
            format_arg = "bestaudio[ext=m4a]/bestaudio"
        else:  # mp4
            format_arg = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best"
        
        process = subprocess.Popen([
            "yt-dlp",
            "-f", format_arg,
            "-o", f"{STORAGE}/%(title)s.%(ext)s",
            "--newline",
            url
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        for line in process.stdout:
            # Parse progress from yt-dlp output
            if "[download]" in line and "%" in line:
                # Extract percentage
                match = re.search(r'(\d+\.?\d*)%', line)
                if match:
                    percentage = match.group(1)
                    yield f"data: {percentage}\n\n"
        
        process.wait()
        yield f"data: complete\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route("/validate_url", methods=["POST"])
def validate_url():
    url = request.json.get("url")
    
    if not url:
        return jsonify({"valid": False, "error": "No URL provided"}), 400
    
    # Basic URL pattern check
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        return jsonify({"valid": False, "error": "Invalid URL format"})
    
    # Use yt-dlp to validate if the URL is supported
    try:
        result = subprocess.run([
            "yt-dlp",
            "--no-download",
            "--no-playlist",
            "--skip-download",
            "--get-title",
            url
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and result.stdout.strip():
            title = result.stdout.strip().split('\n')[0]
            return jsonify({"valid": True, "title": title})
        else:
            error_msg = result.stderr.strip() if result.stderr else "Unable to extract video info"
            return jsonify({"valid": False, "error": error_msg})
    except subprocess.TimeoutExpired:
        return jsonify({"valid": False, "error": "Validation timeout - please try again"})
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)})

@app.route("/download_file/<filename>")
def download_file(filename):
    from flask import send_file
    import mimetypes
    
    file_path = os.path.join(STORAGE, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    
    # Determine MIME type
    mime_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    
    return send_file(
        file_path,
        mimetype=mime_type,
        as_attachment=True,
        download_name=filename,
        conditional=True,
        max_age=0
    )

@app.route("/delete/<filename>")
def delete_file(filename):
    path = os.path.join(STORAGE, filename)
    if os.path.exists(path):
        os.remove(path)
    return redirect(url_for("index"))

@app.route("/clear_all", methods=["POST"])
def clear_all():
    try:
        files = os.listdir(STORAGE)
        for filename in files:
            file_path = os.path.join(STORAGE, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return jsonify({"success": True, "message": "All files deleted"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
