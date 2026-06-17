"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re
import random

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    if not listings:
        return []

    results = []
    keywords = [
        k.strip(".,;:- ")
        for k in (description or "").lower().split()
        if k.strip(".,;:- ")
    ]

    for item in listings:
        # Price filter
        if max_price is not None and item["price"] > max_price:
            continue

        # Size filter (partial match, case-insensitive)
        if size is not None and size.strip():
            item_size = str(item.get("size", "")).lower()
            search_size = size.strip().lower()
            if search_size not in item_size and item_size not in search_size:
                continue

        # Relevance scoring
        score = 0
        for keyword in keywords:
            if keyword in item.get("title", "").lower():
                score += 3
            for tag in item.get("style_tags", []):
                if keyword in tag.lower():
                    score += 2
            if keyword in item.get("description", "").lower():
                score += 1
            if keyword in item.get("category", "").lower():
                score += 1

        if score > 0 or not keywords:
            item_copy = dict(item)
            item_copy["_score"] = score
            results.append(item_copy)

    # Sort by score descending
    results.sort(key=lambda x: x["_score"], reverse=True)

    # Remove internal score field before returning
    for item in results:
        del item["_score"]

    return results

# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    wardrobe_items = wardrobe.get("items", [])

    # 1. Handle empty or minimal wardrobe — agent must not crash
    if not wardrobe_items or len(wardrobe_items) < 2:
        style_tags = new_item.get("style_tags", [])
        category = new_item.get("category", "item")
        tag_str = ", ".join(style_tags[:2]) if style_tags else "versatile"

        fallbacks = {
            "tops": f"This {new_item.get('title', 'piece')} works great with high-waisted denim and chunky sneakers for a {tag_str} vibe.",
            "bottoms": f"Style these {new_item.get('title', 'pants')} with an oversized tee and your favorite sneakers for a {tag_str} look.",
            "outerwear": f"Layer this {new_item.get('title', 'jacket')} over a simple tee and jeans for a {tag_str} outfit.",
            "shoes": f"These {new_item.get('title', 'shoes')} anchor any outfit — try them with baggy jeans and a vintage tee for a {tag_str} feel.",
            "accessories": f"Add this {new_item.get('title', 'accessory')} to a simple outfit for a {tag_str} touch.",
        }
        return fallbacks.get(
            category,
            f"This {new_item.get('title', 'piece')} is a great find — pair it with pieces that match a {tag_str} aesthetic.",
        )

    # 2. Build wardrobe context for LLM
    wardrobe_context = "\n".join(
        [
            f"- {item['name']} ({item['category']}, colors: {', '.join(item.get('colors', []))}, tags: {', '.join(item.get('style_tags', []))})"
            for item in wardrobe_items
        ]
    )

    prompt = f"""You are a fashion stylist. Given a new thrifted item and a user's existing wardrobe, suggest how to style the new item into a complete outfit.

New item: {new_item.get('title', 'Unknown')}
Category: {new_item.get('category', 'unknown')}
Style tags: {', '.join(new_item.get('style_tags', []))}
Colors: {', '.join(new_item.get('colors', []))}
Description: {new_item.get('description', '')}

User's wardrobe:
{wardrobe_context}

Suggest a complete outfit using the new item and pieces from the wardrobe. Be specific about which wardrobe items to use. Give styling tips (tucking, rolling, layering). Keep it to 2-3 sentences."""

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=150,
        )

        suggestion = response.choices[0].message.content.strip()
        if suggestion:
            return suggestion
        raise ValueError("Empty response from LLM")

    except Exception:
        # Rule-based fallback if LLM fails
        category = new_item.get("category", "")
        colors = set(new_item.get("colors", []))
        style_tags = set(new_item.get("style_tags", []))

        matches = []
        for item in wardrobe_items:
            if item.get("category") == category:
                continue
            item_colors = set(item.get("colors", []))
            item_tags = set(item.get("style_tags", []))
            if (colors & item_colors) or (style_tags & item_tags):
                matches.append(item["name"])

        if matches:
            return f"Pair this {new_item.get('title', 'piece')} with your {', '.join(matches[:3])} for a cohesive look. The shared colors and style tags tie the outfit together."
        return f"This {new_item.get('title', 'piece')} is versatile — try it with your {wardrobe_items[0]['name']} and {wardrobe_items[1]['name']} for a balanced outfit."

# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
   # 1. Guard against empty outfit string
    if not outfit or not outfit.strip():
        return f"Found a {new_item.get('title', 'great piece')} for ${new_item.get('price', '??')} on {new_item.get('platform', 'thrift store')}. Can't wait to style this!"

    prompt = f"""Write a short, casual Instagram-style caption for a thrifted outfit. The caption should feel authentic and social-media-ready.

New item: {new_item.get('title', 'Unknown')} — ${new_item.get('price', '??')} from {new_item.get('platform', 'thrift store')}
Outfit: {outfit}

Write 1-2 sentences. Use casual language, maybe an emoji. Mention the price and platform. Make it feel like a real person's post, not an ad."""

    try:
        client = _get_groq_client()
        # Higher temperature ensures outputs vary between runs
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=100,
        )

        caption = response.choices[0].message.content.strip()
        if caption:
            return caption
        raise ValueError("Empty response from LLM")

    except Exception:
        # Rotating template fallback — produces different output each time
        templates = [
            "thrifted this {title} off {platform} for ${price} and honestly it's the perfect find 🖤 {snippet}",
            "found a {title} on {platform} for ${price} — {snippet} ✨",
            "just copped this {title} for ${price} on {platform}. {snippet} 🖤",
            "this {title} from {platform} (${price}) was meant for my closet. {snippet} ✨",
        ]

        title = new_item.get("title", "piece").lower()
        platform = new_item.get("platform", "depop")
        price = new_item.get("price", "??")

        snippet = outfit.split(".")[0] if "." in outfit else outfit[:60]
        snippet = snippet.replace("Pair this", "goes with").replace("Style these", "perfect with")

        return random.choice(templates).format(
            title=title, platform=platform, price=price, snippet=snippet
        )
    
# ── Tool 4: parse_user_query ───────────────────────────────────────────────────

def parse_user_query(query: str) -> dict:
    """
    Extract structured parameters from the user's natural language query.
    Uses keyword matching (not LLM) to identify size, max_price, and description.

    Args:
        query: The user's raw input string.

    Returns:
        A dict with keys: description (str), size (str or None), max_price (float or None).
        If a parameter is missing, the value is None.

    TODO:
        1. Check for empty/whitespace-only query.
        2. Use regex to extract price patterns (e.g., "under $30", "$30").
        3. Use regex to extract size patterns (e.g., "size M", "US 8").
        4. Clean remaining text into the description field.
        5. Return the structured dict.

    Before writing code, fill in the Tool 4 section of planning.md.
    """
    if not query or not query.strip():
        return {"description": "", "size": None, "max_price": None}

    original = query.strip()

    # Extract price: "under $30", "max $30", "$30", "less than 30"
    price_match = re.search(
        r'(?:under|max|maximum|less than)\s*\$?(\d+)|\$\s*(\d+)(?:\s|$)',
        original,
        re.IGNORECASE,
    )
    max_price = None
    working = original
    if price_match:
        max_price = float(price_match.group(1) or price_match.group(2))
        working = working[: price_match.start()] + working[price_match.end() :]
        working = re.sub(r"\s+", " ", working).strip()

    # Extract size: "size M", "size US 8", "M", "W30", "US 8"
    size_patterns = [
        (r"size\s+(US\s+\d+\.?\d*)", 1),
        (r"size\s+([XSMLxl]+\/?[XSMLxl]*)", 1),
        (r"size\s+([Ww]\d+)", 1),
        (r"\b(US\s+\d+\.?\d*)\b", 1),
        (r"\b([Ww]\d+)\b", 1),
        (r"\b([XSMLxl]+\/?[XSMLxl]*)\b", 1),
    ]
    size = None
    for pattern, group in size_patterns:
        match = re.search(pattern, working, re.IGNORECASE)
        if match:
            size = match.group(group).strip()
            working = working[: match.start()] + working[match.end() :]
            working = re.sub(r"\s+", " ", working).strip()
            break

    # Clean up description
    description = working.strip(".,;:- ")
    fillers = [
        "looking for",
        "i want",
        "i need",
        "find me",
        "search for",
        "i am",
        "i'm",
        "show me",
        "what's out there",
        "how would i style it",
        "i mostly wear",
        "help me",
    ]
    for filler in fillers:
        description = re.sub(re.escape(filler), "", description, flags=re.IGNORECASE).strip()

    description = re.sub(r"\s+", " ", description).strip(".,;:- ")

    if not description:
        description = original.strip()

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }
