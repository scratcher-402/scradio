from flask import Flask, Blueprint, request, render_template, jsonify, redirect, url_for, abort, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import psycopg2
from psycopg2 import OperationalError, InterfaceError
import time
import copy
from config import *
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from db import AutoReconnectDB
import os

app = Flask(__name__)
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=[])

db = AutoReconnectDB(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME, max_retries=2)

def set_like(ip, song_id, rating=1):
	db.execute("INSERT INTO likes (ip, song_id, rating) VALUES (%s, %s, %s) ON CONFLICT (ip, song_id) DO UPDATE SET rating = EXCLUDED.rating RETURNING rating;", (ip, song_id, rating), commit=True)

def remove_like(ip, song):
	db.execute("DELETE FROM likes WHERE ip = %s AND song_id = %s;", (ip, song), commit=True)

def add_feedback(ip, name, email, message):
	db.execute("INSERT INTO feedback (ip, name, email, text) VALUES (%s, %s, %s, %s)", (ip, name, email, message), commit=True)

@dataclass
class Song:
	id: int
	title: str
	artist: str
	album: str
	artist_solo: str
	lyrics: str
	album_id: str
	playlist: str
	duration: int
	cover_url: str
	rating: int
	likes: int
	dislikes: int
	
def get_song(id, ip=None):
	if ip:
		raw_songs = db.execute("SELECT s.id, s.title, s.artist, s.album, s.artist_solo, s.lyrics, s.album_id, s.playlist, s.duration, %s || a.cover_filename AS cover_url, (SELECT rating FROM likes where ip = %s and song_id = s.id ), song_likes(s.id, 1), song_likes(s.id, -1) FROM songs s, albums a WHERE s.loaded AND s.allowed AND s.album_id = a.id AND s.id = %s;", (f"{WEB_BASE_URL}static/media/Covers/", ip, id))
		if len(raw_songs) == 0:
			return None
		else:
			return Song(*raw_songs[0])
	else:
		raw_songs = db.execute("SELECT s.id, s.title, s.artist, s.album, s.artist_solo, s.lyrics, s.album_id, s.playlist, s.duration, %s || a.cover_filename AS cover_url FROM songs s, albums a WHERE s.loaded AND s.allowed AND s.album_id = a.id AND s.id = %s;", (f"{WEB_BASE_URL}static/media/Covers/", id))
		if len(raw_songs) == 0:
			return None
		else:
			return Song(*raw_songs[0], None, None, None)
	
def get_likes(ip, *song_ids):
	flat = []
	for lst in song_ids:
		flat += lst
	index_array = list(range(len(flat)))
	
	resp = db.execute("WITH query_data AS ( SELECT unnest(%s) as query_array_id, unnest(%s) as query_song_id ) SELECT (SELECT rating FROM likes WHERE song_id = qd.query_song_id AND ip = %s), song_likes(query_song_id, 1), song_likes(query_song_id, -1), qd.query_array_id FROM query_data qd ORDER BY qd.query_array_id;", (index_array, flat, ip))
	
	packed_likes = [ like[0:3] for like in resp ]
	print(flat, index_array, resp, packed_likes)
	output = []
	last_index = 0
	for lst in song_ids:
		output.append(packed_likes[last_index:last_index+len(lst)])
		last_index += len(lst)
	
	return output

# API

api = Blueprint('api', __name__)
limiter.limit("10 per second")(api)

@api.route("/api/songs/<int:id>/")
def api_song_get(id):
	song = get_song(id, request.remote_addr)
	if song:
		return jsonify( asdict(song) )
	else:
		return jsonify({ "error": "song not found" }), 404
	
@api.route("/api/songs/<int:id>/like", methods=["GET", "POST", "DELETE"])
def api_song_like(id):
    if request.method == "DELETE":
        remove_like(request.remote_addr, id)
        return jsonify({ "rating": None })
    else:
	    like = set_like(request.remote_addr, id, 1)
	    return jsonify({ "rating": 1 })

@api.route("/api/songs/<int:id>/dislike", methods=["GET", "POST", "DELETE"])
def api_song_dislike(id):
    if request.method == "DELETE":
        remove_like(request.remote_addr, id)
        return jsonify({ "rating": None })
    else:
	    like = set_like(request.remote_addr, id, -1)
	    return jsonify({ "rating": -1 })



metadata = {"prev_songs": [], "now_playing": {}, "next_songs": [], "received": None}

@api.route("/api/metadata", methods=["GET", "POST"])
def api_metadata():
	global metadata
	if request.method == "GET":
		f = request.args.get("format")
		if not f: f = "full"
		if f == "full":
			if request.args.get("likes"):
				copied_meta = copy.deepcopy(metadata)
				prev_id = [ s["id"] for s in copied_meta["prev_songs"] ]
				next_id = [ s["id"] for s in copied_meta["next_songs"] ]
				now_id = [ copied_meta["now_playing"]["id"] ]
				prev_likes, now_likes, next_likes = get_likes(request.remote_addr, prev_id, now_id, next_id)
				for i in range(len(copied_meta["prev_songs"])): 
					copied_meta["prev_songs"][i]["rating"] = prev_likes[i][0]
					copied_meta["prev_songs"][i]["likes"] = prev_likes[i][1]
					copied_meta["prev_songs"][i]["dislikes"] = prev_likes[i][2]
				for i in range(len(copied_meta["next_songs"])): 
					copied_meta["next_songs"][i]["rating"] = next_likes[i][0]
					copied_meta["next_songs"][i]["likes"] = next_likes[i][1]
					copied_meta["next_songs"][i]["dislikes"] = next_likes[i][2]
				copied_meta["now_playing"]["rating"] = now_likes[0][0]
				copied_meta["now_playing"]["likes"] = now_likes[0][1]
				copied_meta["now_playing"]["dislikes"] = now_likes[0][2]
				return jsonify(copied_meta)
			else:
				return jsonify(metadata)
		if f == "legacy":
			return jsonify({ "artist": metadata["now_playing"].get("artist"), "title": metadata["now_playing"].get("title") })
		if f == "small":
			return jsonify({ "id": metadata["now_playing"].get("id"), "title": metadata["now_playing"].get("title"), "artist": metadata["now_playing"].get("artist"), "album": metadata["now_playing"].get("album"), "cover_url": metadata["now_playing"].get("cover_url") })
		return jsonify({ "error": "invalid format" }), 400
	else:
		if request.headers.get("X-Metadata-Secret") == METADATA_SECRET:
			j = request.json
			if not j:
				return jsonify({ "error": "invalid json" }), 400
			prev_ok = isinstance(j.get("prev_songs"), list)
			next_ok = isinstance(j.get("next_songs"), list)
			now_ok = isinstance(j.get("now_playing"), dict)
			if prev_ok and next_ok and now_ok:
				if j["now_playing"].get("filename"): j["now_playing"].pop("filename")
				metadata["prev_songs"] = j["prev_songs"]
				metadata["next_songs"] = j["next_songs"]
				metadata["now_playing"] = j["now_playing"]
				metadata["received"] = datetime.now().timestamp()
				return jsonify(metadata)
			else:
				return jsonify({ "error": "invalid format" }), 400
		else:
			return jsonify({ "error": "invalid secret" })

app.register_blueprint(api)

@app.context_processor
def global_variables():
	return {"version_string": VERSION_STRING, "web_base_url": WEB_BASE_URL, "icecast_base_url": ICECAST_BASE_URL}

# Страницы

@app.route("/")
def root():
 return render_template("index.html", metadata=metadata)


@app.route("/feedback")
def feedback_page():
	return render_template("feedback.html", message=None)

@app.route("/info")
def info_page():
	return render_template("info.html")

# Обработчики форм

@app.route("/forms/feedback", methods=["POST"])
@limiter.limit("1 per 10 seconds")
def feedback_form():
	ip = request.remote_addr
	name = request.form.get("name")
	email = request.form.get("email")
	message = request.form.get("message")
	add_feedback(ip, name, email, message)
	return render_template("feedback.html", message={"status": 1})


def is_safe_path(parent_path, child_path):
    try:
        parent_real = os.path.realpath(parent_path)
        target_real = os.path.realpath(os.path.join(parent_real, child_path))
        return os.path.commonpath([parent_real]) == os.path.commonpath([parent_real, target_real])
    except (ValueError, OSError):
        return False

@app.route("/static/media/<path:filename>")
def send_media_file(filename):
    file_path = os.path.join(MEDIA_PATH, filename)
    if is_safe_path(MEDIA_PATH, file_path):
        return send_from_directory(MEDIA_PATH, filename)
    else:
        abort(403)


if __name__ == "__main__":
	app.run("0.0.0.0", 8999, debug=True)
