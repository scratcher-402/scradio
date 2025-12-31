function autoUpdatePlaylist() {
	playlistContainer = document.getElementById("playlist-modal");
	renderPlaylist(playlistContainer);
	}
function checkTextOverflow() {
    document.querySelectorAll(".scroll").forEach((e) => {
    if (e.scrollWidth > e.clientWidth) {
        e.classList.add('scroll-animation');
        const scrollDistance = e.offsetWidth - e.scrollWidth - 60;
        e.style.setProperty("--scroll-distance", `${scrollDistance}px`);
        const scrollSpeed = 0.04;
        const scrollTime = scrollSpeed*(-scrollDistance);
        e.style.animation = `scroll-horizontal ${scrollTime}s linear infinite`;
    } else {
        e.classList.remove('scroll-animation');
        e.style.animation = null;
    }
    })
}

// Запускаем при загрузке
document.addEventListener('DOMContentLoaded', checkTextOverflow);

// И при изменении размера окна
window.addEventListener('resize', checkTextOverflow);

// Вещательные константы
const metadataUrl = '/api/metadata?likes=1';

// дефолт конфиг
const defaultConfig = {
	format: window.playerStreams[0],
	metadataInTitle: true,
	coverInFavicon: true
	}

let config = defaultConfig;

function saveConfig() {
	localStorage.setItem('config', JSON.stringify(config));
	}

function loadConfig() {
	config = localStorage.getItem('config');
	if (config) {
		config = JSON.parse(config);
	} else {
		config = defaultConfig;
		saveConfig();
	}
}

// Состояния плеера
let playing = false;
let metadata = {};
let metadataInterval = null;
let audio = null;

function changeFavicon(href) {
	const oldFavicon = document.querySelector('link[rel=icon]');
	if (oldFavicon) oldFavicon.remove();
	
	const favicon = document.createElement('link');
	favicon.rel = 'icon';
	favicon.href = href;
	document.head.appendChild(favicon);
}


function updateMetadata(songObj) {
	fetch(metadataUrl)
	.then(response => {
		const status = response.status;
		switch (true) {
			case status === 200:
				return response.json();
			case status === 404:
				throw new Error("404 - no metadata")
			case status === 429:
				throw new Error("429 - rate limited")
			default:
				throw new Error("metadata getting error")
		}
	})
	.then(data => {
		songObj.errorMessage.style.display = "none";
		metadata = data;
		let nowPlaying = data["now_playing"];
		songObj.title.innerText = nowPlaying["title"];
		songObj.artist.innerText = nowPlaying["artist"];
		songObj.album.innerText = nowPlaying["album"];
		songObj.cover.src = nowPlaying["cover_url"];
		songObj.lyrics.innerText = nowPlaying["lyrics"];
		songObj.likesCount.innerText = nowPlaying["likes"];
		songObj.dislikesCount.innerText = nowPlaying["dislikes"];
		if (nowPlaying.likes == 0) {
			songObj.likesCount.style.display = "none";
		} else {
			songObj.likesCount.style.display = "inline-block";
			}
		if (nowPlaying.dislikes == 0) {
			songObj.dislikesCount.style.display = "none";
		} else {
			songObj.dislikesCount.style.display = "inline-block";
			}
		if (nowPlaying.rating == 1) {
			songObj.likeBtn.classList = "fa-solid fa-thumbs-up";
			songObj.dislikeBtn.classList = "fa-regular fa-thumbs-down";
		} else if (nowPlaying.rating == -1) {
			songObj.likeBtn.classList = "fa-regular fa-thumbs-up";
			songObj.dislikeBtn.classList = "fa-solid fa-thumbs-down";
		} else {
			songObj.likeBtn.classList = "fa-regular fa-thumbs-up";
			songObj.dislikeBtn.classList = "fa-regular fa-thumbs-down";
			}
		if (playing && config.metadataInTitle) {
			document.title = `${nowPlaying.artist} - ${nowPlaying.title} на SCRadio`;
		}
		if (playing && config.coverInFavicon && nowPlaying.cover_url) {
			changeFavicon(nowPlaying.cover_url);
			}
		checkTextOverflow();
		autoUpdatePlaylist();
	})
	.catch(error => {
		if (error.message.includes("404")) {
			console.log("metadata not found")
			songObj.errorMessage.style.display = "block";
			songObj.errorMessageText.innerText = "Метаданные не найдены";
		} else if (error.message.includes("429")) {
			setInterval(() => updateMetadata(songObj), 1500);
		} else {
			songObj.errorMessage.style.display = "block";
			songObj.errorMessageText.innerText = "Ошибка получения метаданных";
			console.log(error);
		}
	});
	}

function autoUpdateMetadata(songObj) {
	if (metadataInterval == null) {
		metadataInterval = setInterval(() => {updateMetadata(songObj);}, 15000);
		}
	}

function togglePlay(playBtn, songObj) {
	if (playing) {
		playing = false;
		audio.pause();
		audio.removeAttribute('src');
		audio = null
		clearInterval(metadataInterval);
		playBtn.classList = "fa-solid fa-play";
		document.title = "SCRadio";
		changeFavicon("/static/scradio.png");
	} else {
		if (audio) {
            playing = true;
            togglePlay(playBtn, songObj);
            return;
        }
        audio = new Audio();
        playBtn.classList = "fa-solid fa-spinner fa-spin";
        
        let streamUrl = config.format.url;
        
        audio.src = streamUrl;
        playing = true;
        
        audio.addEventListener('play', () => {
        	playBtn.classList = "fa-solid fa-stop";
        	updateMetadata(songObj, false);
        	autoUpdateMetadata(songObj)
        });
        audio.addEventListener('pause', () => {
        	if (playing) togglePlay(playBtn, songObj);
		});
		audio.addEventListener('error', (e) => {
			console.log("playback error", e);
			togglePlay(playBtn, songObj);
			alert("Ошибка воспроизведения: ", e);
		});
		
		audio.play();
	};
};



function likeSong(likeBtn, song_id, rating, again, oppositeBtn) {
	if ('fa-spinner' in likeBtn.classList) return;
	if (rating === 1) {
	    let fetchUrl = `/api/songs/${song_id}/like`;
	    let doDelete = likeBtn.classList.contains("fa-solid");
	    likeBtn.classList = "fa-solid fa-spinner fa-spin";
	    if (doDelete) {
	        fetch(fetchUrl, {method: "DELETE"})
	        .then(response => {
	            if (response.ok) {
	                likeBtn.classList = "fa-regular fa-thumbs-up";
	            } else if (response.status === 429 && (!again)) {
	                console.log("rate-limited, retrying in 2s", response);
	                likeBtn.classList = "fa-solid fa-thumbs-up";
                    setTimeout(() => {likeSong(likeBtn, song_id, rating, true, oppositeBtn);}, 2000);
	            } else {
	                throw new Error("like error - unknown status code");
	            }
	        })
	        .catch(error => {
	            console.log(error);
	            likeBtn.classList = "fa-solid fa-thumbs-up";
	            alert("Не удалось убрать лайк");
	        });
	    } else {
	        fetch(fetchUrl)
	        .then(response => {
	            if (response.ok) {
	                likeBtn.classList = "fa-solid fa-thumbs-up";
	                oppositeBtn.classList = "fa-regular fa-thumbs-down";
	            } else if (response.status === 429 && (!again)) {
	                console.log("rate-limited, retrying in 2s", response);
	                likeBtn.classList = "fa-regular fa-thumbs-up";
	                setTimeout(() => {likeSong(likeBtn, song_id, rating, true, oppositeBtn);}, 2000);
	            } else {
	                throw new Error("like error - unknown status code")
	            }
	        })
	        .catch(error => {
	            console.log(error);
	            likeBtn.classList = "fa-regular fa-thumbs-up";
	            alert("Не удалось поставить лайк")
	        });
	    }
	} else {
	    let fetchUrl = `/api/songs/${song_id}/dislike`;
	    let doDelete = likeBtn.classList.contains("fa-solid");
	    likeBtn.classList = "fa-solid fa-spinner fa-spin";
	    if (doDelete) {
	    	fetch(fetchUrl, {method: "DELETE"})
	    	.then(response => {
	    	    if (response.ok) {
	    	        likeBtn.classList = "fa-regular fa-thumbs-down";
	    	    } else if (response.status === 429 && (!again)) {
	    	        console.log("rate-limited, retrying in 2s", response);
	    	        likeBtn.classList = "fa-solid fa-thumbs-down";
	                setTimeout(() => {likeSong(likeBtn, song_id, rating, false, oppositeBtn);}, 2000);
	    	    } else {
	    	        throw new Error("like error - unknown status code");
	    	        }
	    	    })
	            .catch(error => {
	                console.log(error);
	   	            likeBtn.classList = "fa-solid fa-thumbs-down";
	   	            alert("Не удалось убрать дизлайк");
	   	        });
   	    } else {
	        fetch(fetchUrl)
 	        .then(response => {
	    	     if (response.ok) {
	                 likeBtn.classList = "fa-solid fa-thumbs-down";
	                 oppositeBtn.classList = "fa-regular fa-thumbs-up";
	    	     } else if (response.status === 429 && (!again)) {
	                 console.log("rate-limited, retrying in 2s", response);
	    	         likeBtn.classList = "fa-regular fa-thumbs-down";
	    	         setTimeout(() => {likeSong(likeBtn, song_id, rating, false, oppositeBtn);}, 2000);
	    	     } else {
	    	         throw new Error("like error - unknown status code")
	    	     }
	    	 })
	    	 .catch(error => {
	    	     console.log(error);
	    	     likeBtn.classList = "fa-regular fa-thumbs-down";
	    	     alert("Не удалось поставить дизлайк")
	    	 });
	    }
	}
};


function createPlaylistEntry(song, playlistContainer) {
	// создаем говно
	const songContainer = document.createElement("div");
	const songCover = document.createElement("img");
	const songInfo = document.createElement("div");
	const songTitle = document.createElement("div");
	const songArtist = document.createElement("div");
	const songLike = document.createElement("i");
	const songLikesCount = document.createElement("span");
	const songDislike = document.createElement("i");
	const songDislikesCount = document.createElement("span");

	
	// вставляем значения
	songCover.src = `/static/media/Covers/${song.album_id}.jpg`; // почему я просто не вставил туда ссылку? двойные стандарты api!
	songTitle.innerText = song.title;
	songArtist.innerText = song.artist;
	if (song.likes != 0) songLikesCount.innerText = song.likes;
	if (song.dislikes != 0) songDislikesCount.innerText = song.dislikes;
	
	// добро пожаловать на канал хренового программирования `говнокод тв`!
	songContainer.classList = "track";
	songInfo.classList = "track-info";
	songTitle.classList = "scroll track-title";
	songArtist.classList = "scroll track-artist";
	songLikesCount.classList = "likes_count";
	songDislikesCount.classList = "likes_count";
	if (song.rating === 1) {
		songLike.classList = "fa-solid fa-thumbs-up";
		songDislike.classList = "fa-regular fa-thumbs-down";
	} else if (song.rating === -1) {
		songLike.classList = "fa-regular fa-thumbs-up";
		songDislike.classList = "fa-solid fa-thumbs-down";
	} else {
		songLike.classList = "fa-regular fa-thumbs-up";
		songDislike.classList = "fa-regular fa-thumbs-down";
		};
	
	// обработчики
	songLike.addEventListener('click', () => {
		likeSong(songLike, song.id, 1, false, songDislike);
	});
	songDislike.addEventListener('click', () => {
		likeSong(songDislike, song.id, -1, false, songLike);
	});
	// улучшаем демографическую ситуацию
	songContainer.appendChild(songCover);
	songContainer.appendChild(songInfo);
	songInfo.appendChild(songTitle);
	songInfo.appendChild(songArtist);
	songContainer.appendChild(songLike);
	songContainer.appendChild(songLikesCount);
	songContainer.appendChild(songDislike);
	songContainer.appendChild(songDislikesCount);

	return songContainer;
}
	

// ой блять это пиздец
function renderPlaylist(playlistContainer) {
	if (playlistContainer.style.display === 'block') { //ну а нахуя грузить обложки в фоне???
		const playlistContent = playlistContainer.querySelector('.modal-text');
		playlistContent.innerHTML = "";
		for (const playlistEntry in metadata.prev_songs) {
			const songContainer = createPlaylistEntry(metadata.prev_songs[playlistEntry], playlistContainer);
			playlistContent.appendChild(songContainer);
			}
		const nowSongContainer = createPlaylistEntry(metadata.now_playing, playlistContainer);
		nowSongContainer.style.backgroundColor = getComputedStyle(document.documentElement).getPropertyValue("--light").trim();
		playlistContent.appendChild(nowSongContainer);
		for (const playlistEntry in metadata.next_songs) {
			const songContainer = createPlaylistEntry(metadata.next_songs[playlistEntry], playlistContainer);
			playlistContent.appendChild(songContainer);
			}
		checkTextOverflow();
	}
};

function renderSettings(settingsContainer) {
	const settingsContent = settingsContainer.querySelector(".modal-text");
	settingsContent.innerHTML = "";
	
	// выбор формата
	const formatSelect = document.createElement("select");
	formatSelect.id = "settings-format";
	for (const i in window.playerStreams) {
		if (config.format.url == window.playerStreams[i].url) {
			const opt = new Option(window.playerStreams[i].name, i, false, true);
			formatSelect.appendChild(opt);
		} else {
			const opt = new Option(window.playerStreams[i].name, i);
			formatSelect.appendChild(opt);
		}
	}
	settingsContent.innerHTML += "Формат: ";
	settingsContent.appendChild(formatSelect);
	
	const brBrPatapim = document.createElement("br");
	settingsContent.appendChild(brBrPatapim);
	
	// кнопочки про метаданные
	const pizdaSelect = document.createElement("input");
	const pizdaSelectLabel = document.createElement("label");
	pizdaSelect.type = "checkbox";
	pizdaSelect.name = "metadata-in-title";
	pizdaSelect.id = "metadata-in-title";
	if (config.metadataInTitle) pizdaSelect.checked = true;
	pizdaSelectLabel.for = "metadata-in-title";
	pizdaSelectLabel.innerText = " Метаданные в названии сайта";
	settingsContent.appendChild(pizdaSelect);
	settingsContent.appendChild(pizdaSelectLabel);
	
	const brBrPatapimb = document.createElement("br");
	settingsContent.appendChild(brBrPatapimb);
	
	const xyiSelect = document.createElement("input");
	const xyiSelectLabel = document.createElement("label");
	xyiSelect.type = "checkbox";
	xyiSelect.name = "cover-in-favicon";
	xyiSelect.id = "cover-in-favicon";
	if (config.coverInFavicon) xyiSelect.checked = true;
	xyiSelectLabel.for = "cover-in-favicon";
	xyiSelectLabel.innerText = " Обложка песни в Favicon";
	settingsContent.appendChild(xyiSelect);
	settingsContent.appendChild(xyiSelectLabel);
	}

function saveSettings(settingsContainer) {
	const settingsContent = settingsContainer.querySelector(".modal-text");
	
	// выбор формата
	const formatSelect = settingsContent.querySelector("#settings-format");
	const formatSelectIndex = +(formatSelect.value);
	config.format = window.playerStreams[formatSelectIndex];
	
	// метаданная хуйня
	const pizdaSelect = document.querySelector("#metadata-in-title");
	const xyiSelect = document.querySelector("#cover-in-favicon");
	config.metadataInTitle = pizdaSelect.checked;
	config.coverInFavicon = xyiSelect.checked;
	
	saveConfig();
	location.reload();
	}
	

document.addEventListener('DOMContentLoaded', () => {
	// Элементы плеера
	const songTitle = document.getElementById("song-info-title");
	const songArtist = document.getElementById("song-info-artist");
	const songAlbum = document.getElementById("song-info-album");
	const songCover = document.getElementById("song-info-cover");
	const songLyricsContainer = document.getElementById("lyrics-modal");
	const songLyrics = document.getElementById("lyrics-text");
	const playBtn = document.getElementById("song-play");
	const likeBtn = document.getElementById("song-like");
	const likesCount = document.getElementById("song-likes");
	const dislikeBtn = document.getElementById("song-dislike");
	const dislikesCount = document.getElementById("song-dislikes");
	const settingsBtn = document.getElementById("song-settings");
	const lyricsBtn = document.getElementById("song-lyrics");
	const lyricsCloseBtn = document.getElementById("lyrics-close");
	const playlistBtn = document.getElementById("song-playlist");
	const playlistContainer = document.getElementById("playlist-modal");
	const playlistContent = document.getElementById("playlist-content");
	const playlistCloseBtn = document.getElementById("playlist-close");
	const settingsContainer = document.getElementById("settings-modal");
	const settingsCancelBtn = document.getElementById("settings-cancel");
	const settingsSaveBtn = document.getElementById("settings-save");
	const errorMessage = document.querySelector(".player .error-message")
	const errorMessageText = document.querySelector(".player .error-message-text")
	const songObj = {title: songTitle, artist: songArtist, album: songAlbum, cover: songCover, likeBtn: likeBtn, dislikeBtn: dislikeBtn, lyrics: songLyrics, likesCount: likesCount, dislikesCount: dislikesCount, errorMessage: errorMessage, errorMessageText: errorMessageText};
	window.songObj = songObj
	loadConfig();
	updateMetadata(songObj);
	
	// Вешаем обработчики
	playBtn.addEventListener('click', () => {
		togglePlay(playBtn, songObj);
		});
	
	likeBtn.addEventListener('click', () => {
		let song_id = metadata["now_playing"]["id"];
		likeSong(likeBtn, song_id, 1, false, dislikeBtn);
	});
	
	dislikeBtn.addEventListener('click', () => {
		let song_id = metadata["now_playing"]["id"];
		likeSong(dislikeBtn, song_id, -1, false, likeBtn);
	});
	
	lyricsBtn.addEventListener('click', () => {
		songLyricsContainer.style.display = "block";
		});
	
	lyricsCloseBtn.addEventListener('click', () => {
		songLyricsContainer.style.display = "none";
		});
		
	
	playlistBtn.addEventListener('click', () => {
		playlistContainer.style.display = "block";
		renderPlaylist(playlistContainer);
		});
	
	playlistCloseBtn.addEventListener('click', () => {
		playlistContainer.style.display = "none";
		});
	
	settingsBtn.addEventListener('click', () => {
		renderSettings(settingsContainer);
		settingsContainer.style.display = 'block';
		});
	
	settingsCancelBtn.addEventListener('click', () => {
		settingsContainer.style.display = 'none';
		});
	
	settingsSaveBtn.addEventListener('click', () => {
		saveSettings(settingsContainer);
		settingsContainer.style.display = 'none';
		});

});
