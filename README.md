# scradio
Здесь представлен исходный код проекта SCRadio (https://radio.k0nus.ru/) - онлайн-радиостанции с автоматическим диджеем и веб-сайтом
## Зависимости
- ОС Linux
- Python 3.10 или новее
- FFmpeg
- opus-tools
- Python библиотеки (см. `requirements.txt`)
## Структура для развёртывания
- Стример (`main.py`)
- Веб-приложение (`app.py`, не обязательно для работы стримера)
- База данных PostgreSQL
- Медиасервер Icecast
## Инструкция по развёртыванию
### Подготовка
Перед развертыванием проверьте, что все необходимые зависимости установлены. В Debian/Ubuntu их можно установить следующей командой:
```bash
sudo apt install python3 python3-pip ffmpeg opus-tools
```
Для установки Python библиотек выполните:
```bash
pip install -r requirements.txt
```
Для запуска нужно будет записать настройки в конфигурационный файл `config.py`. Рекомендуется взять `config.py.example` как основу:
```bash
mv config.py.example config.py # переименовать config.py.example в config.py
```
### Настройка базы данных
Для работы SCRadio нужна база данных PostgreSQL.
Рекомендую создать отдельного пользователя и базу данных для него:
```sql
CREATE USER scradio WITH PASSWORD '53c1237';
CREATE DATABASE scradio OWNER scradio;
```
Запишите настройки для подключения к БД в конфигурационный файл, затем выполните скрипт `init_db.py`. Структура базы данных будет настроена автоматически.
### Настройка Icecast
Нужно будет настроить маунты Icecast для вещания:
- `/scradio`, формат MP3, битрейт 256 Кбит/с
- `/scradio.opus`, формат Opus, битрейт 128 Кбит/с

Не забудьте внести настройки для подключения к Icecast в конфиг.
### Настройка путей
Создайте папку для медиафайлов и пропишите её в конфиг. В ней будут храниться песни и обложки.

**Важно.** Если вы используете сторонний HTTP сервер, настройте его так, чтобы медиапапка была доступна из веба по адресу `/static/media/`.
### Подготовка плейлиста
Чтобы добавить песни, используйте интерактивный скрипт `vsrconv.py`:
```bash
python3 vsrconv.py /path/to/song.mp3
```
**Важно.** SCRadio использует "умный" плейлист, который упорядочивает песни так, чтобы одна и та же песня не включалась слишком часто. Если в плейлисте мало песен (20 и менее), стример может не запуститься.

Чтобы сделать новые песни видимыми для стримера, запустите скрипт проверки медиа:
```bash
python3 vsrcheck.py
```
### Запуск
Для запуска стримера выполните `main.py`, для запуска веб-интерфейса - `app.py`.
## Рекомендации
Для использования в продакшене лучше настроить отдельный веб-сервер (Gunicorn или nginx+uwsgi).
Также следует использовать сложные пароли.
## API
Веб-приложение имеет API для просмотра и редактирования информации о проигрываемых песнях.
### /api/metadata
Эндпоинт для получения и обновления метаданных.

#### Методы
- GET (для получения)
- POST (для обновления, требуется заголовок X-Metadata-Secret (METADATA_SECRET из конфига))

#### Параметры
- `likes`: добавлять или нет информацию о лайках. Передайте любое значение для активации параметра
- `format`: устанавливает формат (подробность) возвращаемого объекта метаданных. Принимает значения `full` (по умолчанию), `small`, `legacy`. (примеры объектов приведены ниже)

Пример объекта с likes=1
```json
{
  "next_songs": [
    {
      "album_id": 63,
      "artist": "Ace of Base",
      "dislikes": 0,
      "id": 90,
      "likes": 0,
      "rating": null,
      "title": "Beautiful Life"
    },
    {
      "album_id": 131,
      "artist": "Roxette",
      "dislikes": 0,
      "id": 303,
      "likes": 0,
      "rating": null,
      "title": "Sleeping In My Car"
    },
    {
      "album_id": 199,
      "artist": "Metallica",
      "dislikes": 0,
      "id": 261,
      "likes": 1,
      "rating": null,
      "title": "Nothing Else Matters"
    },
    {
      "album_id": 21,
      "artist": "Константин Никольский",
      "dislikes": 0,
      "id": 104,
      "likes": 1,
      "rating": null,
      "title": "Один взгляд назад"
    },
    {
      "album_id": 37,
      "artist": "Brainstorm",
      "dislikes": 0,
      "id": 60,
      "likes": 0,
      "rating": null,
      "title": "Ветер"
    }
  ],
  "now_playing": {
    "album": "...But Seriously",
    "album_id": 75,
    "artist": "Phil Collins",
    "artist_solo": null,
    "cover_url": "https://radio.k0nus.ru/static/media/Covers/75.jpg",
    "dislikes": 0,
    "duration": 323053,
    "id": 107,
    "likes": 0,
    "lyrics": "..."
    "playlist": "Main",
    "rating": null,
    "title": "Another Day In Paradise"
  },
  "prev_songs": [
    {
      "album_id": 183,
      "artist": "Queen",
      "dislikes": 0,
      "id": 240,
      "likes": 2,
      "rating": null,
      "title": "Bohemian Rhapsody"
    },
    {
      "album_id": 11,
      "artist": "Танцы минус",
      "dislikes": 0,
      "id": 24,
      "likes": 0,
      "rating": null,
      "title": "10 капель"
    },
    {
      "album_id": 225,
      "artist": "The Jimi Hendrix Experience",
      "dislikes": 0,
      "id": 294,
      "likes": 1,
      "rating": null,
      "title": "All Along the Watchtower"
    },
    {
      "album_id": 137,
      "artist": "Максим Леонидов",
      "dislikes": 0,
      "id": 186,
      "likes": 1,
      "rating": null,
      "title": "Видение"
    },
    {
      "album_id": 109,
      "artist": "Bee Gees",
      "dislikes": 2,
      "id": 153,
      "likes": 4,
      "rating": null,
      "title": "Stayin' Alive"
    }
  ],
  "received": 1763300622.6947
}
```

При отсутствии параметра `likes` возвращается аналогичный объект без полей `likes`, `dislikes`, `rating`.

Пример формата `small`:
```json
{
  "album": "Metallica",
  "artist": "Metallica",
  "cover_url": "https://radio.k0nus.ru/static/media/Covers/199.jpg",
  "id": 261,
  "title": "Nothing Else Matters"
}
```

Пример формата `legacy`:
```json
{
  "artist": "Metallica",
  "title": "Nothing Else Matters"
}
```
