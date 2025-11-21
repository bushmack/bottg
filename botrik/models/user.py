from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None