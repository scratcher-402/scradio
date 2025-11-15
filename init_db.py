from db import *
from config import *


def init_db(db):
    db.execute(
"""
CREATE TABLE albums (
    id serial PRIMARY KEY,
    name text NOT NULL,
    artist text NOT NULL,
    cover_filename text,
    cover_loaded boolean DEFAULT false NOT NULL,
    artist_solo text,
    year integer,
    meta jsonb
);
"""
, commit=True)
    db.execute(
"""
CREATE TABLE feedback (
    id serial PRIMARY KEY,
    ip inet,
    name character varying(100) NOT NULL,
    email character varying(100),
    text character varying(4096) NOT NULL
);
"""
, commit=True)
    db.execute(
"""
CREATE TABLE songs (
    id serial PRIMARY KEY,
    title text NOT NULL,
    artist text NOT NULL,
    album text NOT NULL,
    playlist text NOT NULL,
    album_id integer NOT NULL,
    artist_solo text,
    filename text,
    lyrics text,
    flags integer DEFAULT 0 NOT NULL,
    loaded boolean DEFAULT false NOT NULL,
    allowed boolean DEFAULT true NOT NULL,
    meta jsonb,
    duration bigint
);
"""
, commit=True)
    db.execute(
"""
CREATE TABLE likes (
    ip inet,
    song_id integer,
    rating smallint,
    constraint unique_like unique (ip, song_id)
);
"""
, commit=True)
    db.execute(
"""
CREATE FUNCTION inthash(n integer) RETURNS integer
    LANGUAGE sql
    AS $$
select (n * 785 + 29) % 515
$$;
"""
, commit=True)
    db.execute(
"""
CREATE FUNCTION song_likes(id integer, r integer) RETURNS integer
    LANGUAGE sql
    AS $$
    select count(*) from likes where song_id = id and rating = r;
$$;
"""
, commit=True)


if __name__ == "__main__":
    db = AutoReconnectDB(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME, max_retries=2)
    init_db(db)
