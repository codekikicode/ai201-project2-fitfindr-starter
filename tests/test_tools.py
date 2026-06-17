import pytest
from tools import search_listings, suggest_outfit, create_fit_card, parse_user_query
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# --- parse_user_query tests ---

def test_parse_basic_query():
    result = parse_user_query("vintage graphic tee under $30 size M")
    assert result["description"] == "vintage graphic tee"
    assert result["size"] == "M"
    assert result["max_price"] == 30.0


def test_parse_no_params():
    result = parse_user_query("help me find something cool")
    assert result["description"] == "find something cool"  # "help me" stripped as filler
    assert result["size"] is None
    assert result["max_price"] is None


def test_parse_empty():
    result = parse_user_query("")
    assert result["description"] == ""
    assert result["size"] is None
    assert result["max_price"] is None


# --- search_listings tests (at least one test per failure mode) ---

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0
    assert all("price" in item for item in results)


def test_search_empty_results():
    """Failure mode: no listings match the query"""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []  # empty list, no exception


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("jeans", size="W32", max_price=100)
    assert len(results) > 0
    assert any(
        "W32" in str(item.get("size", "")) or "32" in str(item.get("size", ""))
        for item in results
    )


# --- suggest_outfit tests (at least one test per failure mode) ---

def test_suggest_with_full_wardrobe():
    wardrobe = get_example_wardrobe()
    new_item = {
        "title": "Graphic Tee — 2003 Tour Bootleg Style",
        "category": "tops",
        "style_tags": ["graphic tee", "vintage", "grunge", "streetwear"],
        "colors": ["black"],
        "description": "Vintage-style bootleg tee with faded graphic.",
    }
    result = suggest_outfit(new_item, wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_empty_wardrobe():
    """Failure mode: wardrobe is empty — agent should not crash"""
    wardrobe = get_empty_wardrobe()
    new_item = {
        "title": "Vintage Band Tee",
        "category": "tops",
        "style_tags": ["vintage", "grunge"],
        "colors": ["black"],
        "description": "Faded band tee.",
    }
    result = suggest_outfit(new_item, wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_minimal_wardrobe():
    """Failure mode: wardrobe has fewer than 2 items"""
    wardrobe = {
        "items": [
            {
                "name": "One Item",
                "category": "bottoms",
                "colors": ["blue"],
                "style_tags": ["denim"],
            }
        ]
    }
    new_item = {
        "title": "Tee",
        "category": "tops",
        "style_tags": ["basic"],
        "colors": ["white"],
        "description": "A tee",
    }
    result = suggest_outfit(new_item, wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


# --- create_fit_card tests (at least one test per failure mode) ---

def test_fit_card_with_outfit():
    outfit = "Pair this with baggy jeans and chunky sneakers."
    new_item = {
        "title": "Graphic Tee",
        "price": 24.0,
        "platform": "depop",
        "style_tags": ["graphic tee", "vintage"],
        "colors": ["black"],
    }
    result = create_fit_card(outfit, new_item)
    assert isinstance(result, str)
    assert len(result) > 0


def test_fit_card_empty_outfit():
    """Failure mode: outfit input is missing or empty — return message, don't crash"""
    new_item = {
        "title": "Vintage Jacket",
        "price": 45.0,
        "platform": "poshmark",
        "style_tags": ["vintage"],
        "colors": ["navy"],
    }
    result = create_fit_card("", new_item)
    assert isinstance(result, str)
    assert "45" in result or "Vintage Jacket" in result
    assert len(result) > 0


def test_fit_card_variety():
    """Run twice with same input — verify outputs differ or are both valid"""
    outfit = "Pair with jeans and sneakers."
    new_item = {
        "title": "Band Tee",
        "price": 20.0,
        "platform": "depop",
        "style_tags": ["band tee"],
        "colors": ["black"],
    }
    result1 = create_fit_card(outfit, new_item)
    result2 = create_fit_card(outfit, new_item)
    assert isinstance(result1, str) and len(result1) > 0
    assert isinstance(result2, str) and len(result2) > 0