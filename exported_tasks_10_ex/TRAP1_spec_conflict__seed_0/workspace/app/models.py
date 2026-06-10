"""Data models for marketplace_api."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    name: str
    email: str
    id: Optional[int] = None


@dataclass
class Item:
    name: str
    price: float
    id: Optional[int] = None


@dataclass
class Order:
    user_id: int
    item_id: int
    quantity: int
    id: Optional[int] = None


@dataclass
class Report:
    report_type: str
    id: Optional[int] = None
