import logging
from typing import Dict, Any, List
from repository import UserRepository
from config import *

class BotService:
    def __init__(self):
        self.repository = UserRepository()
        self.logger = logging.getLogger(__name__)

    def handle_start(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка команды /start"""
        try:
            user_id = user_data['id']
            username = user_data.get('username', '')
            first_name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')

            # Сохраняем пользователя в БД
            success = self.repository.add_user(user_id, username, first_name, last_name)
            
            return {
                'success': True,
                'message': START_MESSAGE,
                'keyboard': MAIN_KEYBOARD,
                'user_saved': success
            }
        except Exception as e:
            self.logger.error(f"Error in handle_start: {e}")
            return {
                'success': False,
                'message': ERROR_MESSAGE
            }

    def handle_help(self) -> Dict[str, Any]:
        """Обработка команды /help"""
        try:
            return {
                'success': True,
                'message': HELP_MESSAGE,
                'keyboard': MAIN_KEYBOARD
            }
        except Exception as e:
            self.logger.error(f"Error in handle_help: {e}")
            return {
                'success': False,
                'message': ERROR_MESSAGE
            }

    def handle_profile(self, user_id: int) -> Dict[str, Any]:
        """Обработка команды /profile"""
        try:
            user = self.repository.get_user(user_id)
            if user:
                message = PROFILE_MESSAGE.format(user[0], user[1] or 'Не указан', 
                                               user[2] or 'Не указано', user[3] or 'Не указана')
            else:
                message = NO_PROFILE_MESSAGE
                
            return {
                'success': True,
                'message': message,
                'keyboard': MAIN_KEYBOARD
            }
        except Exception as e:
            self.logger.error(f"Error in handle_profile for user {user_id}: {e}")
            return {
                'success': False,
                'message': ERROR_MESSAGE
            }

    def handle_all_users(self) -> Dict[str, Any]:
        """Обработка команды /all_users"""
        try:
            users = self.repository.get_all_users()
            if users:
                message = ALL_USERS_HEADER.format(len(users))
                for user in users:
                    message += USER_INFO.format(user[0], user[1] or 'Не указан', 
                                              user[2] or 'Не указано', user[3] or 'Не указана') + "\n"
            else:
                message = NO_USERS_MESSAGE
                
            return {
                'success': True,
                'message': message,
                'keyboard': MAIN_KEYBOARD
            }
        except Exception as e:
            self.logger.error(f"Error in handle_all_users: {e}")
            return {
                'success': False,
                'message': ERROR_MESSAGE
            }