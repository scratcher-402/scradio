# coding: utf-8
import os
import datetime
import subprocess
import mutagen
import datetime
from mutagen.easyid3 import EasyID3
import psycopg2
import sys
from config import *

# Config
DIR_PATH = MEDIA_PATH
DB_CONNECT = {"host": DB_HOST, "user": DB_USER, "password": DB_PASSWORD, "dbname": DB_NAME, "port": DB_PORT}
EDITOR = os.environ.get("EDITOR", DEFAULT_EDITOR)


class Metadata:
	def __init__(self, title, artist, album, lyrics, year):
		self.title = title
		self.artist = artist
		self.album = album
		self.lyrics = lyrics
		self.year = year

def read_metadata(fn):
	if fn.endswith(".mp3"):
		mm = EasyID3(fn)
		title = mm.get("title")
		artist = mm.get("artist")
		album = mm.get("album")
		year = mm.get("date")
		if title: title = title[0]
		if artist: artist = artist[0]
		if album: album = album[0]
		if year: year = year[0]
		return Metadata(title, artist, album, None, year)
	else:
		mm = mutagen.File(fn)
		title = mm.get("title")
		artist = mm.get("artist")
		album = mm.get("album")
		lyrics = mm.get("lyrics")
		year = mm.get("date")
		if title: title = title[0]
		if artist: artist = artist[0]
		if album: album = album[0]
		if year: year = year[0]
		if lyrics: lyrics = lyrics[0]
		return Metadata(title, artist, album, lyrics, year)

def tempfn(format=""):
	return os.path.join(DIR_PATH, "Temp", f"{datetime.datetime.now().timestamp()}{format}")

def edit_lyrics(lyrics):
	if not lyrics: lyrics = ""
	tfn = tempfn()
	with open(tfn, "w") as fp:
		fp.write(lyrics)
	p = subprocess.Popen((EDITOR, tfn))
	p.wait()
	with open(tfn, "r") as fp:
		lyrics = fp.read()
	os.remove(tfn)
	return lyrics

def get_cover(song):
	tfn = tempfn(format=".jpg")
	p = subprocess.Popen(("ffmpeg", "-i", song, "-an", "-q:v", "10", tfn))
	code = p.wait()
	if code == 0:
		return tfn
	else:
		return False

def init_db():
	conn = psycopg2.connect(**DB_CONNECT)
	cur = conn.cursor()
	return conn, cur

def db_insert_album(cur, params):
	cur.execute("insert into albums (name, artist, artist_solo, year) values (%s, %s, %s, %s) returning id;", params)
	id = cur.fetchone()[0]
	cur.execute("update albums set cover_filename = %s where id = %s;", (f"{id}.jpg", id))
	return id

def db_insert_song(cur, params):
	cur.execute("insert into songs (title, artist, album, playlist, album_id, artist_solo, lyrics) values (%s, %s, %s, %s, %s, %s,%s) returning id;", params)
	id = cur.fetchone()[0]
	fn = f"{params[1]} - {params[0]} - {id}.opus"
	cur.execute("update songs set filename = %s where id = %s", (fn, id))
	return (id, fn)

def db_get_album(cur, id):
	cur.execute("select name, artist, artist_solo from albums where id = %s;", (id,))
	return cur.fetchone()

def convert_song(fn, title, artist, album, lyrics, album_id, artist_solo, cover, playlist, id):
	wtfn = tempfn(format=".wav")
	wp = subprocess.Popen(("ffmpeg", "-i", fn, "-f", "wav", wtfn))
	if wp.wait() != 0: raise Exception("ffmpeg error")
	ofn = os.path.join(DIR_PATH, "Music", playlist, f"{artist} - {title} - {id}.opus")
	oparams = ["opusenc", "--bitrate", "128", "--title", title, "--artist", artist, "--album", album, "--comment", f"vsr_song_id={id}", "--comment", f"vsr_album_id={album_id}", "--comment", f"artist_solo={artist_solo}", "--comment", f"vsr_playlist={playlist}"]
	if lyrics:
		oparams.append("--comment")
		oparams.append(f"lyrics={lyrics}")
	if cover:
		oparams.append("--picture")
		oparams.append(cover)
	oparams.append(wtfn)
	oparams.append(ofn)
	op = subprocess.Popen(oparams)
	if op.wait() != 0: raise Exception("opusenc error")
	os.remove(wtfn)
	return fn

def conv_add_song(fn=sys.argv[1]):
	print("Конвертируем", fn)
	conn, cur = init_db()
	meta = read_metadata(fn)
	title = meta.title
	artist = meta.artist
	album = meta.album
	lyrics = meta.lyrics
	year = meta.year
	album_id = None
	artist_solo = None
	playlist = "Main"
	cover = False
	correct = False
	while not correct:
		_title = input(f"Название[{title}]: ")
		if _title: title = _title
		choice = input("(1): Новый альбом\n(2):Указать существующий альбом\nВаш выбор[1]: ")
		if not choice or choice == "1":
			_artist = input(f"Исполнитель[{artist}]: ")
			if _artist: artist = _artist
			_album = input(f"Альбом[{album}]: ")
			if _album: album = _album
			_artist_solo = input(f"Солист[{artist_solo}]: ")
			if _artist_solo: artist_solo = _artist_solo
			_year = input(f"Год[{year}]: ")
			if _year: year = _year
		else:
			album_id = int(input("ID альбома: "))
			album, artist, artist_solo = db_get_album(cur, album_id)
		print("Текст песни: ", lyrics)
		choice = input("Редактировать текст? [Д/н/Y/n]: ")
		if choice not in ("н", "Н", "n", "N"):
			lyrics = edit_lyrics(lyrics)
		_playlist = input(f"Плейлист[{playlist}]: ")
		if _playlist: playlist = _playlist
		if not cover:
			choice = input("Получить обложку из файла? [Д/н/Y/n]: ")
			if choice not in ("н", "Н", "n", "N"):
				cover = get_cover(fn)
				if cover:
					print("Обложка получена")
				else:
					print("Не удалось получить обложку!")
		choice = input("Введенные данные корректны? [Д/н/Y/n]: ")
		if choice not in ("н", "Н", "n", "N"): correct = True
		else: correct = False
	rewrite_cover = True
	if album_id:
		cover = os.path.join(DIR_PATH, "Covers", f"{album_id}.jpg")
		rewrite_cover = False
	if not album_id:
		album_id = db_insert_album(cur, (album, artist, artist_solo, year))
		print("Альбом добавлен, ID:", album_id)
	id, ffn = db_insert_song(cur, (title, artist, album, playlist, album_id, artist_solo, lyrics))
	print("Песня добавлена! ID:", id)
	convert_song(fn, title, artist, album, lyrics, album_id, artist_solo, cover, playlist, id)
	if cover:
		real_cover_fn = os.path.join(DIR_PATH, "Covers", f"{album_id}.jpg")
		if not os.path.exists(real_cover_fn): os.rename(cover, real_cover_fn)
	conn.commit()
	cur.close()
	conn.close()

if __name__ == "__main__":
    for dir in ("Covers", "Music", "Temp"):
        if not os.path.exists(os.path.join(MEDIA_PATH, dir)):
            os.makedirs(os.path.join(MEDIA_PATH, dir))
    conv_add_song()
	
			
