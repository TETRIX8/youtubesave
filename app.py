from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, after_this_request, jsonify, render_template, request, send_file
from flask_cors import CORS
from yt_dlp import YoutubeDL

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


def _extract_info(video_url: str) -> Dict[str, Any]:
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "noplaylist": True,
        "no_warnings": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return info


def _format_list(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    formats: List[Dict[str, Any]] = []
    for f in info.get("formats", []):
        if not f.get("url"):
            continue
        # Build a friendly label
        height = f.get("height")
        fps = f.get("fps")
        abr = f.get("abr")
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        ext = f.get("ext")
        tbr = f.get("tbr")  # total bitrate
        is_audio = (vcodec == "none") and acodec and acodec != "none"
        is_video = (acodec == "none") and vcodec and vcodec != "none"
        is_muxed = (vcodec and vcodec != "none") and (acodec and acodec != "none")

        quality = None
        if height:
            quality = f"{height}p"
            if fps and fps > 30:
                quality += f"{int(fps)}"
        elif is_audio:
            quality = f"audio {int(abr)}kbps" if abr else "audio"
        else:
            quality = ext or "format"

        size_hint = None
        if tbr:
            size_hint = f"~{int(tbr)}kbps"

        kind = "video+audio" if is_muxed else ("video" if is_video else "audio")

        formats.append(
            {
                "format_id": f.get("format_id"),
                "ext": ext,
                "quality": quality,
                "filesize": f.get("filesize") or f.get("filesize_approx"),
                "size_hint": size_hint,
                "container": f.get("container"),
                "vcodec": vcodec,
                "acodec": acodec,
                "fps": fps,
                "kind": kind,
                "note": f.get("format_note"),
            }
        )

    # Sort: prefer muxed first, then by height desc, then audio
    def sort_key(x: Dict[str, Any]):
        kind_order = {"video+audio": 0, "video": 1, "audio": 2}
        height = 0
        if x.get("quality") and isinstance(x.get("quality"), str) and x["quality"].endswith("p"):
            try:
                height = int(x["quality"].rstrip("p0123456789").rstrip())
            except Exception:
                pass
        return (kind_order.get(x["kind"], 3), -height, -(x.get("fps") or 0))

    formats.sort(key=sort_key)
    return formats


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.post("/api/info")
def api_info():
    data = request.get_json(silent=True) or {}
    video_url = data.get("url")
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        info = _extract_info(video_url)
        thumb = None
        if isinstance(info.get("thumbnails"), list) and info["thumbnails"]:
            thumb = sorted(info["thumbnails"], key=lambda t: t.get("height") or 0)[-1].get("url")
        result = {
            "id": info.get("id"),
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "thumbnail": thumb or info.get("thumbnail"),
            "formats": _format_list(info),
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/download")
def download():
    video_url = request.args.get("url")
    format_id = request.args.get("format_id")
    if not video_url or not format_id:
        return jsonify({"error": "Missing url or format_id"}), 400

    temp_dir = tempfile.mkdtemp(prefix="ytdl_")

    @after_this_request
    def cleanup(response):
        try:
            # Remove temp directory after request is handled
            for p in Path(temp_dir).glob("*"):
                try:
                    p.unlink()
                except Exception:
                    pass
            Path(temp_dir).rmdir()
        except Exception:
            pass
        return response

    # Prepare download
    outtmpl = str(Path(temp_dir) / "%(title).200B-%(id)s.%(ext)s")
    ydl_opts = {
        "format": format_id,
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            # Find downloaded file path
            if "requested_downloads" in info and info["requested_downloads"]:
                file_path = info["requested_downloads"][0].get("filepath")
            else:
                # fallback pattern
                file_path = ydl.prepare_filename(info)

        file_path = Path(file_path)
        if not file_path.exists():
            return jsonify({"error": "File not found after download"}), 500

        return send_file(
            str(file_path),
            as_attachment=True,
            download_name=file_path.name,
            mimetype="application/octet-stream",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False) 