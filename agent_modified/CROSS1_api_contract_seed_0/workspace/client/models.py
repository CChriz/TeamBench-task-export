from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    userId: int    # FIXED: server sends "userId" (camelCase)
    name: str
    email: str

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        return cls(
            userId=data.get("userId"),  # FIXED: matches server camelCase
            name=data.get("name", ""),
            email=data.get("email", ""),
        )
