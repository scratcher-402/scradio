# SCRadio Config

VERSION = (3, 1)
VERSION_STRING = ".".join(( str(v) for v in VERSION ))

# Paths
MEDIA_PATH = "/var/media/scradio"
PROG_PATH = "/root/scradio"

# Database
DB_HOST = "db.host.com"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = "p3ssw0rd"
DB_NAME = "scradio"

# Passwords and secrets
METADATA_SECRET = "53c1237"
ICECAST_SOURCE_USER = "source"
ICECAST_SOURCE_PASSWORD = "50u12c3"
ICECAST_ADMIN_USER = "admin"
ICECAST_ADMIN_PASSWORD = "adm1n"
ICECAST_HTTP_HOST = "icecast.host.com"
ICECAST_HTTP_PORT = 8000

# Playlist
ROTATIONS = ("Main", "Pop")

# Other
BUFSIZE = 65536
WEB_BASE_URL = "https://web.host.com/"
ICECAST_BASE_URL = "http://{{ICECAST_HTTP_HOST}}:{{ICECAST_HTTP_PORT}}/"  # you can change http to https
