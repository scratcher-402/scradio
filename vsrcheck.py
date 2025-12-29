import os
import argparse
import datetime
import subprocess
import mutagen
import datetime
from mutagen.easyid3 import EasyID3
import psycopg2
import sys
from PIL import Image, UnidentifiedImageError as BadImageError
from config import *
from progress.bar import Bar

def check_song(path):
	pr = subprocess.Popen(("ffmpeg", "-loglevel", "error", "-hide_banner", "-i", path, "-f", "wav", "-y", "/dev/null"))
	return pr.wait() == 0
def check_image(path):
	try:
		with Image.open(path) as img:
			img.load()
		return True
	except (BadImageError, OSError):
		return False
def db_get_song(cur, id):
	cur.execute("select id, title, artist, playlist, filename from songs where id = %s;", (id,))
	return cur.fetchall()
def db_update_song_path(cur, id, playlist, filename):
	cur.execute("update songs set playlist = %s, filename = %s where id = %s;", (playlist, filename, id))
def db_get_cover(cur, id):
	cur.execute("select id, name, artist, cover_filename from albums where id = %s;", (id,))
	return cur.fetchall()
def db_song_ok(cur, id, duration):
	cur.execute("update songs set loaded = true, duration = %s where id = %s returning loaded;", (duration, id))
	return cur.fetchall()
def db_song_bad(cur, id):
	cur.execute("update songs set loaded = false where id = %s returning loaded;", (id,))
	return cur.fetchall()
def db_cover_ok(cur, id):
	cur.execute("update albums set cover_loaded = true where id = %s returning cover_loaded;", (id,))
	return cur.fetchall()
def db_cover_bad(cur, id):
	cur.execute("update albums set cover_loaded = false where id = %s returning cover_loaded;", (id,))
	return cur.fetchall()
def db_get_unloaded_songs(cur):
	cur.execute("select id, filename, playlist, duration from songs where loaded = false;")
	return cur.fetchall()
def db_get_unloaded_covers(cur):
	cur.execute("select id, cover_filename from albums where cover_filename is not null and cover_loaded = false;")
	return cur.fetchall()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Проверка и восстановление целостности медиатеки SCRadio.")
	parser.add_argument("-a", "--action", choices=["unloaded", "full"], default="unloaded")
	args = parser.parse_args()
	conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME)
	cur = conn.cursor()
	if args.action == "unloaded":
		print("Поиск незагруженных песен")
		unld_songs = db_get_unloaded_songs(cur)
		print(f"{len(unld_songs)} песен не загружено")
		success_count = 0
		for song in Bar("Проверка песен").iter(unld_songs):
			# id, filename, playlist, duration
			song_path = os.path.join(MEDIA_PATH, "Music", song[2], song[1])
			print("Проверяем:", song_path)
			try:
				song_metadata = mutagen.File(song_path)
				song_id = song_metadata.get("vsr_song_id")
				if not song_id:
					print("Не найден id в метаданных")
				song_ok = check_song(song_path)
				if song_ok:
					db_song_ok(cur, song[0], int(1000*song_metadata.info.length))
					print("Песня проверена")
					success_count += 1
				else:
					print("Песня битая")
			except Exception as e:
				print("Ошибка:", e)
		print(f"Проверено {len(unld_songs)} песен, из них {success_count} - успешно.")
		conn.commit()
		print("Поиск незагруженных обложек")
		unld_covers = db_get_unloaded_covers(cur)
		print(f"{len(unld_covers)} обложек не загружено")
		success_count = 0
		for cover in Bar("Проверка обложек").iter(unld_covers):
			# id, cover_filename
			cover_path = os.path.join(MEDIA_PATH, "Covers", cover[1])
			print("Проверка:", cover_path)
			try:
				cover_ok = check_image(cover_path)
				if cover_ok:
					print("Обложка проверена")
					db_cover_ok(cur, cover[0])
					success_count += 1
				else:
					print("Обложка битая или не найдена")
			except Exception as e:
				print("Ошибка:", e)
		print(f"Проверено {len(unld_covers)} обложек, из них {success_count} - успешно.")
		conn.commit()
	else:
		print("Проверка песен в медиатеке")
		song_success = 0
		song_count = 0
		song_bad = 0
		song_not_found = 0
		song_path_updated = 0
		for playlist in os.listdir(os.path.join(MEDIA_PATH, "Music")):
			#print(playlist)
			if os.path.isdir(os.path.join(MEDIA_PATH, "Music", playlist)):
				print("Проверка поейлиста", playlist)
				playlist_files = os.listdir(os.path.join(MEDIA_PATH, "Music", playlist))
				songs = filter(lambda song: song.endswith(".opus"), playlist_files)
				for song in Bar(playlist, max=len(playlist_files)).iter(songs):
					song_filename = song
					song = os.path.join(MEDIA_PATH, "Music", playlist, song)
					print("Проверка", song)
					song_count += 1
					try:
						song_metadata = mutagen.File(song)
						id = song_metadata.get("vsr_song_id")
						if len(id) == 0:
							print("Нет id в метаданных. Пробуем получить из имени файла")
							id = song.split(" - ")[-1][:-5].strip()
						else:
							id = id[0]
						id = int(id)
						db_song = db_get_song(cur, id)
						# id, title, artist, playlist, filename
						if len(db_song) >= 1:
							db_song = db_song[0]
							if db_song[3] != playlist or db_song[4] != song_filename:
								db_update_song_path(cur, id, playlist, song_filename)
								print("Путь к песне обновлён")
								song_path_updated += 1
						else:
							print("Песня не найдена в базе данных!")
							song_not_found += 1
						song_ok = check_song(song)
						if song_ok:
							print("Песня успешно проверена")
							song_success += 1
							db_song_ok(cur, id, int(1000*song_metadata.info.length))
						else:
							print("Песня битая!")
							db_song_bad(cur, id)
							song_bad += 1
					except Exception as e:
						print("Ошибка", e)
		print("Проверка песен завершена")
		conn.commit()
		print("Проверка обложек")
		cover_success = 0
		cover_bad = 0
		cover_not_found = 0
		cover_count = 0
		covers = filter(lambda cover: cover.endswith(".jpg"), os.listdir(os.path.join(MEDIA_PATH, "Covers")))
		for cover in Bar("Проверка обложек").iter(covers):
			cover_path = os.path.join(MEDIA_PATH, "Covers", cover)
			print("Проверка:", cover_path)
			cover_count += 1
			try:
				id = int(cover[:-4])
				db_cover = db_get_cover(cur, id)
				if len(db_cover) >= 1:
					db_cover = db_cover[0]
					cover_ok = check_image(cover_path)
					if cover_ok:
						print("Обложка успешно проверена")
						cover_success += 1
						db_cover_ok(cur, id)
					else:
						print("Обложка битая")
						cover_bad += 1
						db_cover_bad(cur, id)
				else:
					print("Обложка не найдена в БД")
					cover_not_found += 1
			except Exception as e:
				print("Ошибка:", e)
		print("Обложки проверены")
		conn.commit()
		print(f"{song_count} песен проверено\n{song_success} успешно\n{song_bad} битых песен\n{song_not_found} песен не найдено\n{song_path_updated} песен с обновлённым путём")
		print(f"{cover_count} обложек проверено\n{cover_success} успешно\n{cover_bad} битых обложек\n{cover_not_found} обложек не найдено")
						
	
	
	
	
	