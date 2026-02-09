"""Tests for wizard_to_values in app.services.helm_runner."""
from app.services.helm_runner import wizard_to_values


def test_wizard_to_values_flat_and_nested():
    result = wizard_to_values({"a.b": 1, "a.c": 2, "d": 3})
    assert result == {"a": {"b": 1, "c": 2}, "d": 3}


def test_wizard_to_values_empty():
    result = wizard_to_values({})
    assert result == {}


def test_wizard_to_values_deeply_nested():
    result = wizard_to_values({"a.b.c": "deep"})
    assert result == {"a": {"b": {"c": "deep"}}}
