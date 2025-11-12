import psycopg2
from config import *
from dataclasses import dataclass, asdict
import os
import sys
from datetime import datetime
import subprocess
import traceback
import requests
import threading

@dataclass
class Song:
	id: int
	title: str
	artist: str
	album: str
	artist_solo: str
	lyrics: str
	album_id: str
	filename: str
	playlist: str
	duration: int
	cover_filename: str
	
	def sep_artist(self):
		return self.artist.split(", ")
	
	def smalldict(self):
		return { "id": self.id, "title": self.title, "artist": self.artist, "album_id": self.album_id }
	
	def fulldict(self):
		d = asdict(self)
		d["cover_url"] = f"{WEB_BASE_URL}static/media/Covers/{self.cover_filename}"
		d.pop("cover_filename")
		return d
	
	def get_path(self):
		return os.path.join(MEDIA_PATH, "Music", self.playlist, self.filename)

	

class SmartPlaylist:
	pl_prev = []
	now_playing = None
	pl_next = []
	artists_prev = set() # set of artists of last 5 songs
	songs_prev = set() # set of last 20 ids
	unpr_pl = []
	
	def __init__(self, adder_func):
		self.adder_func = adder_func
	
	def _is_addable(self, song):
		id_ok = song.id not in self.songs_prev
		artist_ok = not any(( artist in self.artists_prev for artist in song.sep_artist() ))
		return id_ok and artist_ok
	
	def _add_to_pl(self, song):
		if self._is_addable(song):
			if len(self.pl_next) >= 5:
				for artist in self.pl_next[-5].sep_artist():
					self.artists_prev.discard(artist) # deleting artists of the 6th song from set
			if len(self.pl_next) >= 20:
				self.songs_prev.discard(self.pl_next[-20].id) # deleting 20th song from set
			self.artists_prev.update(song.sep_artist())
			self.songs_prev.add(song.id)
			self.pl_next.append(song)
			return True
		else:
			return False
	
	def _fetch_new_songs(self):
		self.unpr_pl += self.adder_func()
	
	def _add_songs_to_pl(self, count=30):
		songs_added = 0
		index = 0
		while True:
			if index >= len(self.unpr_pl):
				self._fetch_new_songs()
			if self._add_to_pl(self.unpr_pl[index]):
				songs_added += 1
				self.unpr_pl.pop(index)
				index = 0
			else:
				index += 1
			if songs_added == count:
				break
	
	def next_song(self):
		if self.now_playing:
			self.pl_prev.append(self.now_playing)
			if len(self.pl_prev) > 5:
				self.pl_prev.pop(0)
		if len(self.pl_next) < 21:
			self._add_songs_to_pl()
		self.now_playing = self.pl_next.pop(0)
		return self.now_playing
	
	def metadata_dict(self):
		d = {}
		d["prev_songs"] = [ song.smalldict() for song in self.pl_prev ]
		if len(self.pl_next) >= 5:
			d["next_songs"] = [ song.smalldict() for song in self.pl_next[:5] ]
		else:
			d["next_songs"] = [ song.smalldict() for song in self.pl_next ]
		d["now_playing"] = self.now_playing.fulldict()
		return d
	

def fetch_songs_from_db():
	conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME)
	cur = conn.cursor()
	cur.execute("select s.id, s.title, s.artist, s.album, s.artist_solo, s.lyrics, s.album_id, s.filename, s.playlist, s.duration, a.cover_filename from songs s, albums a where s.loaded = true and s.allowed = true and a.id = s.album_id order by random();")
	songs = [ Song(*row) for row in cur.fetchall() ]
	cur.close()
	conn.close()
	return songs

def test_pl():
	return SmartPlaylist(fetch_songs_from_db)

def update_metadata(pl): 
	try:
		r1 = requests.post(f"{WEB_BASE_URL}api/metadata", json=pl.metadata_dict(), headers={"X-Metadata-Secret": METADATA_SECRET})
		np_string = f"{pl.now_playing.artist} - {pl.now_playing.title}"
		r2 = requests.get(f"http://{ICECAST_HTTP_HOST}:{ICECAST_HTTP_PORT}/admin/metadata", auth=requests.auth.HTTPBasicAuth(ICECAST_ADMIN_USER, ICECAST_ADMIN_PASSWORD), params={"mount": "/scradio", "mode": "updinfo", "song": np_string})
		print(r1, r2)
	except Exception as e:
		print("metadata error:", e)


cmd = ("bash", os.path.join(PROG_PATH, "ffmpeg.sh"), VERSION_STRING, f"{ICECAST_SOURCE_USER}:{ICECAST_SOURCE_PASSWORD}@{ICECAST_HTTP_HOST}:{ICECAST_HTTP_PORT}")

if __name__ == "__main__":
	try:
		playlist = SmartPlaylist(adder_func=fetch_songs_from_db)
		ffmpeg_pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE, bufsize=BUFSIZE)
		while True:
			now_playing = playlist.next_song()
			print(f"({now_playing.id}) {now_playing.artist} - {now_playing.title}")
			thr = threading.Thread(target=update_metadata, args=(playlist,))
			thr.start()
			with open(now_playing.get_path(), "rb") as song_file:
				block = song_file.read(16384)
				while len(block) != 0:
					if ffmpeg_pipe.poll() != None:
						raise Exception("ffmpeg stopped")
					ffmpeg_pipe.stdin.write(block)
					block = song_file.read(16384)
	except Exception as e:
		traceback.print_exc()
		with open("errors.txt", "a") as ef:
			ef.write(f"\n---- [{datetime.now()}] ----\n")
			traceback.print_exc(file=ef)
