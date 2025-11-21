import logging
import json
import os
from config import COLLECTIONS_FILE

logger = logging.getLogger(__name__)

class CollectionService:
    def __init__(self):
        pass

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

    def create_collection(self, user_id: int, collection_name: str) -> str:
        """Создание новой коллекции"""
        data = self._load_data(COLLECTIONS_FILE)
        if str(user_id) not in data:
            data[str(user_id)] = {}

        collection_id = str(len(data[str(user_id)]) + 1)
        data[str(user_id)][collection_id] = {
            'name': collection_name,
            'movies': []
        }

        self._save_data(COLLECTIONS_FILE, data)
        logger.info(f"Collection '{collection_name}' created for user {user_id}")
        return collection_id

    def get_user_collections(self, user_id: int):
        """Получение всех коллекций пользователя"""
        data = self._load_data(COLLECTIONS_FILE)
        return data.get(str(user_id), {})

    def add_to_collection(self, user_id: int, collection_id: str, movie_data: dict) -> bool:
        """Добавление фильма в коллекцию"""
        data = self._load_data(COLLECTIONS_FILE)
        if str(user_id) in data and collection_id in data[str(user_id)]:
            # Проверяем, нет ли уже этого фильма в коллекции
            for movie in data[str(user_id)][collection_id]['movies']:
                if movie.get('id') == movie_data.get('id'):
                    return False

            data[str(user_id)][collection_id]['movies'].append(movie_data)
            self._save_data(COLLECTIONS_FILE, data)
            logger.info(f"Movie {movie_data.get('id')} added to collection {collection_id} for user {user_id}")
            return True
        return False

    def remove_from_collection(self, user_id: int, collection_id: str, movie_id: int) -> bool:
        """Удаление фильма из коллекции"""
        data = self._load_data(COLLECTIONS_FILE)
        if str(user_id) in data and collection_id in data[str(user_id)]:
            initial_length = len(data[str(user_id)][collection_id]['movies'])
            data[str(user_id)][collection_id]['movies'] = [
                movie for movie in data[str(user_id)][collection_id]['movies']
                if str(movie.get('id')) != str(movie_id)
            ]
            if len(data[str(user_id)][collection_id]['movies']) < initial_length:
                self._save_data(COLLECTIONS_FILE, data)
                logger.info(f"Movie {movie_id} removed from collection {collection_id} for user {user_id}")
                return True
        return False