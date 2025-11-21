import logging
import requests
from config import SERVER_URL

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, base_url: str = SERVER_URL):
        self.base_url = base_url
        self.session = requests.Session()

    def add_user(self, user_id: int, username: str, first_name: str, last_name: str) -> bool:
        """Добавление пользователя через API"""
        try:
            response = self.session.post(
                f"{self.base_url}/users/",
                json={
                    "user_id": user_id,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name
                },
                timeout=10
            )
            logger.info(f"User {user_id} added via API: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error adding user {user_id} via API: {e}")
            return False

    def get_user(self, user_id: int):
        """Получение пользователя по ID"""
        try:
            response = self.session.get(f"{self.base_url}/users/{user_id}", timeout=10)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None