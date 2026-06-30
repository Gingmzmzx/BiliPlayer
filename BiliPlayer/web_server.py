"""Flask web server providing REST API and control panel for BiliPlayer."""

import os
import threading
from flask import Flask, request, jsonify, send_from_directory

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def create_app(shared_state, config):
    app = Flask(__name__, template_folder=_TEMPLATES_DIR)
    app.config["SHARED_STATE"] = shared_state
    app.config["BILI_CONFIG"] = config

    @app.route("/")
    def index():
        return send_from_directory(_TEMPLATES_DIR, "index.html")

    @app.route("/api/status", methods=["GET"])
    def api_status():
        ss = app.config["SHARED_STATE"]
        cfg = app.config["BILI_CONFIG"]
        snap = ss.snapshot()
        snap["sep_page"] = cfg.get("Player.sepPage")
        snap["default_volume"] = cfg.get("Player.defaultVolume")
        snap["web_port"] = cfg.get("Player.webPort")
        return jsonify(snap)

    @app.route("/api/user/load", methods=["POST"])
    def api_user_load():
        data = request.get_json(silent=True) or {}
        uid = data.get("uid")
        fav_name = data.get("fav_name")
        if not uid or not fav_name:
            return jsonify({"ok": False, "error": "uid and fav_name are required"}), 400
        ss = app.config["SHARED_STATE"]
        ss.uid = int(uid)
        ss.fav_name = fav_name
        ss.mark_reload()
        return jsonify({"ok": True})

    @app.route("/api/playlist", methods=["GET"])
    def api_playlist():
        ss = app.config["SHARED_STATE"]
        return jsonify({
            "playlist": ss.get_playlist(),
            "titles": ss.playlist_titles,
            "current_index": ss.get_current_index(),
        })

    @app.route("/api/playlist/add", methods=["POST"])
    def api_playlist_add():
        data = request.get_json(silent=True) or {}
        bvid = (data.get("bvid") or "").strip()
        if not bvid:
            return jsonify({"ok": False, "error": "bvid is required"}), 400
        app.config["SHARED_STATE"].add_to_playlist(bvid)
        return jsonify({"ok": True})

    @app.route("/api/playlist/remove", methods=["POST"])
    def api_playlist_remove():
        data = request.get_json(silent=True) or {}
        index = data.get("index")
        if index is None:
            return jsonify({"ok": False, "error": "index is required"}), 400
        ok = app.config["SHARED_STATE"].remove_from_playlist(int(index))
        return jsonify({"ok": ok})

    @app.route("/api/playlist/move", methods=["POST"])
    def api_playlist_move():
        data = request.get_json(silent=True) or {}
        from_idx = data.get("from_index")
        to_idx = data.get("to_index")
        if from_idx is None or to_idx is None:
            return jsonify({"ok": False, "error": "from_index and to_index are required"}), 400
        ok = app.config["SHARED_STATE"].reorder_playlist(int(from_idx), int(to_idx))
        return jsonify({"ok": ok})

    @app.route("/api/playlist/refresh", methods=["POST"])
    def api_playlist_refresh():
        ss = app.config["SHARED_STATE"]
        if not ss.uid or not ss.fav_name:
            return jsonify({"ok": False, "error": "No UID/fav_name set. Use /api/user/load first."}), 400
        ss.mark_reload()
        return jsonify({"ok": True})

    @app.route("/api/playback/next", methods=["POST"])
    def api_playback_next():
        app.config["SHARED_STATE"].set_command("next")
        return jsonify({"ok": True})

    @app.route("/api/playback/pause", methods=["POST"])
    def api_playback_pause():
        app.config["SHARED_STATE"].set_command("pause")
        return jsonify({"ok": True})

    @app.route("/api/playback/seek", methods=["POST"])
    def api_playback_seek():
        data = request.get_json(silent=True) or {}
        position = data.get("position")
        if position is None:
            return jsonify({"ok": False, "error": "position (0-100) is required"}), 400
        app.config["SHARED_STATE"].set_command("seek", float(position))
        return jsonify({"ok": True})

    @app.route("/api/playback/volume", methods=["POST"])
    def api_playback_volume():
        data = request.get_json(silent=True) or {}
        volume = data.get("volume")
        if volume is None:
            return jsonify({"ok": False, "error": "volume (0-100) is required"}), 400
        vol = max(0, min(100, int(volume)))
        app.config["SHARED_STATE"].set_command("volume", vol)
        return jsonify({"ok": True})

    @app.route("/api/playback/play_index", methods=["POST"])
    def api_playback_play_index():
        data = request.get_json(silent=True) or {}
        index = data.get("index")
        if index is None:
            return jsonify({"ok": False, "error": "index is required"}), 400
        app.config["SHARED_STATE"].set_command("play_index", int(index))
        return jsonify({"ok": True})

    @app.route("/api/config", methods=["POST"])
    def api_config():
        data = request.get_json(silent=True) or {}
        cfg = app.config["BILI_CONFIG"]
        ss = app.config["SHARED_STATE"]
        if "play_mode" in data:
            mode = data["play_mode"]
            if mode in ("sequential", "shuffle", "repeat_one"):
                ss.play_mode = mode
                cfg.set("Player.playMode", mode)
            else:
                return jsonify({"ok": False, "error": f"Invalid play_mode: {mode}"}), 400
        if "sep_page" in data:
            cfg.set("Player.sepPage", bool(data["sep_page"]))
        if "default_volume" in data:
            vol = max(0, min(100, int(data["default_volume"])))
            cfg.set("Player.defaultVolume", vol)
        cfg.save()
        return jsonify({"ok": True, "play_mode": ss.play_mode})

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    @app.route("/api/preferences", methods=["GET"])
    def api_preferences():
        """Return all per-video preferences."""
        cfg = app.config["BILI_CONFIG"]
        return jsonify(cfg.get("Player.preference", {}))

    @app.route("/api/preference/set", methods=["POST"])
    def api_preference_set():
        """Set preference for a BV. Body: {bvid, p?, beginTime?, endTime?}"""
        data = request.get_json(silent=True) or {}
        bvid = (data.get("bvid") or "").strip()
        if not bvid:
            return jsonify({"ok": False, "error": "bvid is required"}), 400
        cfg = app.config["BILI_CONFIG"]
        pref = cfg.get("Player.preference", {})
        entry = {}
        if "p" in data and data["p"] is not None:
            entry["p"] = int(data["p"])
        if "beginTime" in data and data["beginTime"] is not None:
            entry["beginTime"] = int(data["beginTime"])
        if "endTime" in data and data["endTime"] is not None:
            entry["endTime"] = int(data["endTime"])
        if entry:
            pref[bvid] = entry
        else:
            pref.pop(bvid, None)
        cfg.set("Player.preference", pref)
        cfg.save()
        return jsonify({"ok": True, "preference": pref.get(bvid, {})})

    @app.route("/api/preference/delete", methods=["POST"])
    def api_preference_delete():
        """Delete preference for a BV. Body: {bvid}"""
        data = request.get_json(silent=True) or {}
        bvid = (data.get("bvid") or "").strip()
        if not bvid:
            return jsonify({"ok": False, "error": "bvid is required"}), 400
        cfg = app.config["BILI_CONFIG"]
        pref = cfg.get("Player.preference", {})
        pref.pop(bvid, None)
        cfg.set("Player.preference", pref)
        cfg.save()
        return jsonify({"ok": True})

    @app.route("/api/quit", methods=["POST"])
    def api_quit():
        app.config["SHARED_STATE"].set_command("quit")
        return jsonify({"ok": True})

    return app


def start_web_server(shared_state, config, port: int = 58000):
    app = create_app(shared_state, config)
    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False),
        daemon=True,
        name="biliplayer-web",
    )
    thread.start()
    return thread
