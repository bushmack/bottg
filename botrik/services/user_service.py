import logging
from repository.user_repository import UserRepository
from models.user import User

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        self.user_repo = UserRepository()

    def register_user(self, user_id: int, username: str, first_name: str, last_name: str) -> bool:
        """Регистрация пользователя"""
        logger.info(f"Registering user {user_id}")
        return self.user_repo.add_user(user_id, username, first_name, last_name)

    def get_user_info(self, user_id: int):
        """Получение информации о пользователе"""
        return self.user_repo.get_user(user_id)