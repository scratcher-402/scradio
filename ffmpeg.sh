

echo -e "\n\n\n---- RESTART ffmpeg ----\n\n\n" >> fflog.txt



ffmpeg -loglevel error -f ogg -i - \
 -vn -ab 256k -map_metadata -1 -content_type audio/mpeg -f mp3 -ar 44100 -hide_banner -ice_public 1 -ice_name "SCRadio_$1" -af arealtime icecast://${2}/scradio \
 -content_type audio/ogg -vn -acodec libopus -f ogg -ice_public 1 -ice_name "SCRadio_$1" -af arealtime -ab 128k -map_metadata -1 -metadata "title=Use https://scradio.30x.ru/api/metadata to get metadata" -metadata "artist=SCRadio_$1" icecast://${2}/scradio.opus 2>> fflog.txt
