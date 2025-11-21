import logging
import json
import os
import requests
from config import KINOPOISK_API_KEY, FAVORITES_FILE, WATCHLIST_FILE

logger = logging.getLogger(__name__)

class MovieService:
    def __init__(self):
        self.api_key = KINOPOISK_API_KEY

    def _load_data(self, filename):
        """Загружает данные из файла"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return {}
                    return json.loads(content)
            return {}
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return {}

    def _save_data(self, filename, data):
        """Сохраняет данные в файл"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")

    def search_movies(self, query: str, limit: int = 50):
        """Поиск фильмов и сериалов"""
        try:
            response = requests.get(
                "https://api.kinopoisk.dev/v1.4/movie/search",
                headers={"X-API-KEY": self.api_key},
                params={"page": 1, "limit": limit, "query": query},
                timeout=15
            )
            if response.status_code == 200:
                return response.json().get('docs', [])
            return []
        except Exception as e:
            logger.error(f"Error searching movies: {e}")
            return []

    def get_movie_by_id(self, movie_id: int):
        """Получение информации о фильме по ID"""
        try:
            response = requests.get(
                f"https://api.kinopoisk.dev/v1.4/movie/{movie_id}",
                headers={"X-API-KEY": self.api_key},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting movie {movie_id}: {e}")
            return None

    def get_random_movie(self):
        """Получение случайного фильма"""
        try:
            response = requests.get(
                "https://api.kinopoisk.dev/v1.4/movie/random",
                headers={"X-API-KEY": self.api_key},
                params={
                    "type": "movie",
                    "year": "1998-2024",
                    "rating.kp": "5-10",
                    "votes.kp": "1000-10000000"
                },
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting random movie: {e}")
            return None

    def get_random_series(self):
        """Получение случайного сериала"""
        try:
            response = requests.get(
                "https://api.kinopoisk.dev/v1.4/movie/random",
                headers={"X-API-KEY": self.api_key},
                params={
                    "type": "tv-series",
                    "year": "1998-2024",
                    "rating.kp": "5-10",
                    "votes.kp": "1000-10000000"
                },
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting random series: {e}")
            return None

    def add_to_favorites(self, user_id: int, movie_data: dict) -> bool:
        """Добавление фильма в избранное"""
        data = self._load_data(FAVORITES_FILE)
        if str(user_id) not in data:
            data[str(user_id)] = []

        # Проверяем, нет ли уже этого фильма
        for movie in data[str(user_id)]:
            if movie.get('id') == movie_data.get('id'):
                return False

        data[str(user_id)].append(movie_data)
        self._save_data(FAVORITES_FILE, data)
        logger.info(f"Movie {movie_data.get('id')} added to favorites for user {user_id}")
        return True

    def remove_from_favorites(self, user_id: int, movie_id: int) -> bool:
        """Удаление фильма из избранного"""
        return self._remove_from_list(user_id, movie_id, FAVORITES_FILE, "favorites")

    def add_to_watchlist(self, user_id: int, movie_data: dict) -> bool:
        """Добавление фильма в список желаемого"""
        data = self._load_data(WATCHLIST_FILE)
        if str(user_id) not in data:
            data[str(user_id)] = []

        for movie in data[str(user_id)]:
            if movie.get('id') == movie_data.get('id'):
                return False

        data[str(user_id)].append(movie_data)
        self._save_data(WATCHLIST_FILE, data)
        logger.info(f"Movie {movie_data.get('id')} added to watchlist for user {user_id}")
        return True

    def remove_from_watchlist(self, user_id: int, movie_id: int) -> bool:
        """Удаление фильма из списка желаемого"""
        return self._remove_from_list(user_id, movie_id, WATCHLIST_FILE, "watchlist")

    def _remove_from_list(self, user_id: int, movie_id: int, filename: str, list_type: str) -> bool:
        """Общая функция удаления из списка"""
        data = self._load_data(filename)
        if str(user_id) in data:
            initial_length = len(data[str(user_id)])
            data[str(user_id)] = [
                movie for movie in data[str(user_id)]
                if str(movie.get('id')) != str(movie_id)
            ]
            if len(data[str(user_id)]) < initial_length:
                self._save_data(filename, data)
                logger.info(f"Movie {movie_id} removed from {list_type} for user {user_id}")
                return True
        return False

    def get_favorites(self, user_id: int):
        """Получение избранного пользователя"""
        data = self._load_data(FAVORITES_FILE)
        return data.get(str(user_id), [])

    def get_watchlist(self, user_id: int):
        """Получение списка желаемого пользователя"""
        data = self._load_data(WATCHLIST_FILE)
        return data.get(str(user_id), [])

    def is_in_favorites(self, user_id: int, movie_id: int) -> bool:
        """Проверка, есть ли фильм в избранном"""
        favorites = self.get_favorites(user_id)
        return any(str(movie.get('id')) == str(movie_id) for movie in favorites)

    def is_in_watchlist(self, user_id: int, movie_id: int) -> bool:
        """Проверка, есть ли фильм в списке желаемого"""
        watchlist = self.get_watchlist(user_id)
        return any(str(movie.get('id')) == str(movie_id) for movie in watchlist)