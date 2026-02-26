"""Unit tests for InventoryService."""
import pytest
from service import InventoryService


def test_process_valid():
    svc = InventoryService()
    result = svc.process({"id": 1, "name": "test"})
    assert result["id"] == 1


def test_process_missing_id():
    svc = InventoryService()
    with pytest.raises((ValueError, KeyError)):
        svc.process({"name": "no_id"})


def test_list_all_empty():
    svc = InventoryService()
    assert svc.list_all() == []


def test_delete():
    svc = InventoryService()
    svc.process({"id": 42, "name": "to_delete"})
    result = svc.delete(42)
    assert result is True
