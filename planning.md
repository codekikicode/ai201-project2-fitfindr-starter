# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset (`data/listings.json`) for items matching the user's description, size, and maximum price. Matches against `title`, `description`, `style_tags`, and `category`. Returns results sorted by relevance (exact title match > style tag match > description keyword match). Prices are filtered with `price <= max_price`.

**Input parameters:**
- `description` (str): Keywords describing the desired item (e.g., "vintage graphic tee"). Searched against `title`, `description`, and `style_tags`.
- `size` (str): Desired size (e.g., "M", "W30", "US 8"). Matched against the `size` field. Partial matches accepted (e.g., "S" matches "S/M").
- `max_price` (float): Maximum price the user is willing to pay. Items with `price > max_price` are excluded.

**What it returns:**
A list of matching listing dictionaries, sorted by relevance score (highest first). Each dict contains: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Returns an empty list `[]` if no matches are found.

**What happens if it fails or returns nothing:**
The agent detects the empty result, sets `session["error"] = "No listings found matching your criteria. Try broadening your search (different keywords, larger size range, or higher budget)."`, and returns this message to the user immediately. The planning loop terminates early -- `suggest_outfit` and `create_fit_card` are not called.

---

### Tool 2: suggest_outfit

**What it does:**
 Suggests one or more complete outfit combinations once given a specific new item (a listing dict from `search_listings`) and the user's current wardrobe. Matches the new item with existing wardrobe pieces by checking for complementary `category` coverage (e.g., if new item is a top, it pairs with bottoms, shoes, and optionally outerwear/accessories from the wardrobe) and overlapping or complementary `style_tags` and `colors`. Uses the Groq API to generate a natural language styling suggestion.

**Input parameters:**
- `new_item` (dict): A single listing dictionary from `search_listings` (contains `title`, `category`, `style_tags`, `colors`, etc.).
- `wardrobe` (dict): A wardrobe dictionary with an `items` key containing a list of wardrobe item dicts (each with `id`, `name`, `category`, `colors`, `style_tags`, `notes`).

**What it returns:**
A string containing a natural language outfit suggestion. Example: "Pair this with your wide-leg jeans and platform Docs for a classic 90s grunge look. Roll the sleeves once and tuck the front corner slightly for shape." If the wardrobe is empty, returns a standalone styling suggestion based on the item's style tags.

**What happens if it fails or returns nothing:**
If the wardrobe is empty or has fewer than 2 items, the tool returns a generic styling suggestion based on the new item's `style_tags` and `category` (e.g., "This piece works great with high-waisted denim and chunky sneakers for a streetwear vibe"). The agent stores this in `session["outfit_suggestion"]` and continues to `create_fit_card`. If the Groq API call fails, the agent falls back to a rule-based suggestion using color/style matching and logs the API error.

---

### Tool 3: create_fit_card

**What it does:**
Generates a short, shareable description of a complete outfit: the kind of caption someone would use for an Instagram post. Takes the outfit suggestion and the new item details, then uses the Groq API to produce a casual, concise caption that mentions the new item, the price, the platform, and the styling vibe. The output must be different for different inputs.

**Input parameters:**
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit`.
- `new_item` (dict): The listing dictionary for the purchased/found item (contains `title`, `price`, `platform`, `style_tags`).

**What it returns:**
A string -- a short caption fit for social media usage. Example: "thrifted this faded band tee off depop for $22 and honestly it was made for my wide-legs 🖤 full look in my IG Stories!"

**What happens if it fails or returns nothing:**
If the outfit input is missing or empty, the agent should generate a minimal fit card using only the new item's metadata: "Found a [title] for $[price] on [platform]. Can't wait to style this!" If the Groq API call fails, the agent uses a template-based fallback that randomizes phrasing to ensure different outputs for different inputs.

---

### Tool 4: parse_user_query

**What it does:**
Extracts structured parameters from the user's natural language query before the planning loop begins. Uses keyword matching (not LLM) to identify size, max_price, and item description.

**Input parameters:**
- `query` (str): The user's raw input string.

**What it returns:**
A dict with keys: `description` (str), `size` (str or None), `max_price` (float or None). If a parameter is missing, the value is `None`.

**What happens if it fails or returns nothing:**
If no parameters can be extracted, returns `{"description": query, "size": None, "max_price": None}` and the planning loop proceeds with broad search parameters.

---

## Planning Loop

**How does your agent decide which tool to call next?**
The planning loop is a sequential state machine with conditional branches, not a fixed pipeline. It maintains a `session` dict and checks the state after each tool call.

1. **Initialization**: Parse the user query with `parse_user_query` to populate `session["query_params"]`. Load the user's wardrobe into `session["wardrobe"]`.

2. **First decision**: Check if `session["query_params"]["description"]` exists. If yes, call `search_listings(description, size, max_price)`. If no description was extracted, ask the user for clarification and return early.

3. **After search_listings**: 
   - If `results == []`: Set `session["status"] = "error"`, `session["error_message"] = "No listings found..."`, and return the error message to the user. 
   
   **Stop here.**
   
   - If `results` is non-empty: Set `session["selected_item"] = results[0]` (the top match). Proceed to next step.

4. **Second decision**: Check if `session["selected_item"]` exists. If yes, call `suggest_outfit(new_item=session["selected_item"], wardrobe=session["wardrobe"])`. Store the result in `session["outfit_suggestion"]`.

5. **After suggest_outfit**:
   - If the wardrobe was empty, the tool still returns a generic suggestion. The agent notes this in `session["wardrobe_empty"] = True` but continues.
   - If the suggestion is empty (API failure), use the fallback rule-based suggestion. Store in `session["outfit_suggestion"]`.

6. **Third decision**: Check if `session["outfit_suggestion"]` exists. If yes, call `create_fit_card(outfit=session["outfit_suggestion"], new_item=session["selected_item"])`. Store result in `session["fit_card"]`.

7. **Termination**: Return `session["fit_card"]` to the user. The loop is done when `fit_card` is populated or an error state was set earlier.

---

## State Management

**How does information from one tool get passed to the next?**
The agent uses a single `session` dictionary (a Python dict) that persists for the entire user interaction. It is initialized at the start of the loop and passed implicitly by the agent class.

**Session structure:**
python session = {
    "user_query": str,  # Original user input
    "query_params": {   # Output of  parse_user_query
    
        "description": str,
        "size": str | None,
        "max_price": float | None
    
    },

    "wardrobe": dict,  # User's wardrobe (items list)
    "search_results": list[dict],   
    "selected_item": dict | None,   
    "outfit_suggestion": str | None,# Output of suggest_outfit
    "fit_card": str | None,         
    "status": "in_progress" | "error" | "complete",
    "error_message": str | None,
    "wardrobe_empty": bool

}

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|--------------|----------------|
| search_listings | No results match the query | Set session["status"] = "error", set session["error_message"] to a helpful message suggesting broader search terms, and return the message to the user immediately. Do not call subsequent tools. |
| suggest_outfit | Wardrobe is empty | Return a generic styling suggestion based on the new item's style_tags and category. Set session["wardrobe_empty"] = True and include a note: "You don't have any wardrobe items saved yet -- here's a general styling idea!" Continue to create_fit_card. |
| create_fit_card | Outfit input is missing or incomplete | Generate a minimal template-based fit card using only the new item's title, price, and platform. Store in session["fit_card"] and complete the session. |
| parse_user_query | No parameters extracted (query is too vague or empty) | Returns `{"description": query, "size": None, "max_price": None}` and the planning loop proceeds with a broad search using the full query string as the description. If the query is empty, the agent asks the user: "What are you looking for today?" and returns early. |
---

## Architecture

User query
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│  Planning Loop (Agent)                                            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 1. parse_user_query(query)                                  │   │
│  │    → session["query_params"] = {description, size, max_price}│   │
│  │                                                             │   │
│  │    ├─ query is empty / None                                │   │
│  │    │   → [ERROR] "What are you looking for today?"         │   │
│  │    │   → RETURN to user                                   │   │
│  │    │                                                      │   │
│  │    └─ params extracted                                     │   │
│  │        → continue                                         │   │
│  │                                                             │   │
│  │ 2. IF description is None:                               │   │
│  │      → [ERROR] "What kind of item are you looking for?     │   │
│  │         Try something like 'vintage jeans under $40'."    │   │
│  │      → RETURN to user                                     │   │
│  │                                                             │   │
│  │ 3. search_listings(description, size, max_price)            │   │
│  │    → reads listings.json via load_listings()                │   │
│  │    → session["search_results"]                              │   │
│  │    → session["selected_item"] = results[0]                  │   │
│  │                                                             │   │
│  │    ├─ results == []                                        │   │
│  │    │   → [ERROR] "No listings found matching your         │   │
│  │    │      criteria. Try broadening your search..."        │   │
│  │    │   → session["status"] = "error"                        │   │
│  │    │   → RETURN to user (loop terminates)                 │   │
│  │    │                                                      │   │
│  │    └─ results = [item, ...]                              │   │
│  │        → continue                                         │   │
│  │                                                             │   │
│  │ 4. suggest_outfit(new_item=selected_item, wardrobe)         │   │
│  │    → reads session["wardrobe"]                              │   │
│  │    → calls Groq API for styling suggestion                  │   │
│  │    → session["outfit_suggestion"]                           │   │
│  │                                                             │   │
│  │    ├─ wardrobe is empty / < 2 items                        │   │
│  │    │   → fallback: generic suggestion from style_tags       │   │
│  │    │   → session["wardrobe_empty"] = True                   │   │
│  │    │   → note: "You don't have any wardrobe items yet..."  │   │
│  │    │   → continue (still creates fit_card)                  │   │
│  │    │                                                      │   │
│  │    ├─ Groq API fails                                       │   │
│  │    │   → fallback: rule-based color/category matching       │   │
│  │    │   → log error, continue                               │   │
│  │    │                                                      │   │
│  │    └─ success                                            │   │
│  │        → continue                                         │   │
│  │                                                             │   │
│  │ 5. create_fit_card(outfit_suggestion, selected_item)        │   │
│  │    → calls Groq API for social-media caption                │   │
│  │    → session["fit_card"]                                    │   │
│  │                                                             │   │
│  │    ├─ outfit missing / incomplete                          │   │
│  │    │   → fallback: template using title, price, platform    │   │
│  │    │   → continue                                          │   │
│  │    │                                                      │   │
│  │    ├─ Groq API fails                                       │   │
│  │    │   → fallback: rotating template (3-4 variants)       │   │
│  │    │   → continue                                          │   │
│  │    │                                                      │   │
│  │    └─ success                                            │   │
│  │        → continue                                         │   │
│  │                                                             │   │
│  │ 6. RETURN session["fit_card"] to user                      │   │
│  │    → session["status"] = "complete"                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Session State (dict) — shared across all tool calls        │   │
│  │                                                             │   │
│  │  • user_query          (str)  — original input              │   │
│  │  • query_params        (dict) — {description, size, max_price}│  │
│  │  • wardrobe            (dict) — {items: [...]}               │   │
│  │  • search_results      (list) — [listing, ...]              │   │
│  │  • selected_item       (dict) — top listing                 │   │
│  │  • outfit_suggestion   (str)  — styling text               │   │
│  │  • fit_card            (str)  — final caption               │   │
│  │  • status              (str)  — "in_progress" | "error" |   │   │
│  │                                 "complete"                   │   │
│  │  • error_message       (str)  — user-facing error text      │   │
│  │  • wardrobe_empty      (bool) — flag for empty wardrobe   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Error paths (steps 1, 2, 3) terminate here ──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

**Tool**: `parse_user_query`  
 AI tool: Kimi 2.6
 
**Input:** 
  The Tool 4 spec from this planning.md (input: `query` string, returns: dict with `description`, `size`, `max_price`). Also provide 5 example user queries showing varied phrasing.

**Expected output:**
  A Python function using regex and string parsing to extract price patterns (e.g., "under $30", "$30", "max 30"), size patterns (e.g., "size M", "M", "US 8"), and description (remaining keywords). No LLM call -- pure string logic.  

  **Verification:** 
  Test with 5 queries: (1) "vintage graphic tee under $30 size M" → `{description: "vintage graphic tee", size: "M", max_price: 30.0}`, (2) "baggy jeans" → `{description: "baggy jeans", size: None, max_price: None}`, (3) "platform sneakers size 8 under 50" → `{description: "platform sneakers", size: "8", max_price: 50.0}`, (4) "" (empty) → `{description: "", size: None, max_price: None}`, (5) "looking for something cute" → `{description: "something cute", size: None, max_price: None}`. Verify all fields match expected values before trusting the implementation.

**Tool:** `search_listings`  
AI tool: Kimi 2.6  

**Input:** 
The Tool 1 spec from this planning.md (inputs, return value, failure mode), plus the `listings.json` schema (fields: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`). Also provide the `load_listings()` function signature from `utils/data_loader.py`.  

**Expected output:** 
A Python function `search_listings(description, size, max_price)` that loads listings via `load_listings()`, filters by `price <= max_price`, matches size with partial string matching, scores keyword matches across `title`/`description`/`style_tags`, and returns a sorted list of dicts.  

**Verification:** 
Test with 3 queries before trusting: (1) exact match — `search_listings("vintage graphic tee", "L", 30)` should return `lst_006` as the top result, (2) no match — `search_listings("diamond ring", "M", 10)` should return `[]`, (3) partial match — `search_listings("baggy jeans", "W32", 40)` should return `lst_031`. Verify non-empty results are sorted by relevance score and empty results return `[]`.

**Tool: `suggest_outfit`**  
AI tool: Kimi 2.6  

**Input:** 
The Tool 2 spec from this planning.md, the wardrobe schema (`id`, `name`, `category`, `colors`, `style_tags`, `notes`), plus a concrete sample: `new_item = lst_006` (Graphic Tee — 2003 Tour Bootleg Style) and the example wardrobe from `wardrobe_schema.json`. Also provide the Groq API key setup from `.env`.  

**Expected output:** 
A function that constructs a structured prompt for the Groq API (model: `llama-3.1-8b-instant` or similar fast model), sends the new item and wardrobe items, and returns a natural language styling suggestion. Includes a rule-based fallback if the wardrobe is empty or the API fails.  

**Verification:** 
Test with 3 scenarios before trusting: (1) full wardrobe -- output should mention specific wardrobe pieces by name (e.g., "baggy straight-leg jeans"), (2) empty wardrobe -- output should be a generic suggestion based on `style_tags` and include the note about no saved items, (3) API failure (simulate by passing invalid key) -- should catch exception and return fallback rule-based suggestion using color/category matching. Verify output is always a non-empty string.

**Tool:** `create_fit_card`  
AI tool:* Kimi 2.6

**Input:** 
The Tool 3 spec from this planning.md, plus 2-3 concrete example inputs showing different outfit suggestions and new items (e.g., `lst_006` with a streetwear suggestion, `lst_009` with a y2k suggestion). Include the requirement that outputs must differ for different inputs.  

**Expected output:**
A function that calls the Groq API with a prompt asking for a short, casual Instagram-style caption. Includes 3-4 template fallbacks with randomized phrasing for when the API fails. Templates should rotate so the same input never produces identical output twice.  

**Verification:** 
Test with 2 identical inputs and verify outputs differ (either via LLM randomness or template rotation). Verify each output includes the new item's `price` and `platform`. Test fallback mode by simulating API failure and confirm it uses a template, not an empty string.

**Milestone 4 — Planning loop and state management:**
AI tool: Kimi 2.6
(`parse_user_query`, `search_listings`, `suggest_outfit`, `create_fit_card`).  

**Expected output:** 
A single `Agent` class with a `run(query, wardrobe)` method that: initializes the `session` dict, executes the conditional loop in the exact order specified (parse → check description → search → check results → suggest → check fallback → fit card → return), handles all error branches by setting `session["status"] = "error"` and returning early, and returns the final `fit_card` string or error message.  

**Verification:** 
Run 4 end-to-end tests and verify `session` state at each step:  
  
  1. **Happy path:** All 3 tools succeed → `session["status"] == "complete"`, `session["fit_card"]` is a non-empty string, `session["selected_item"]` is populated.  
  
  2. **Search returns nothing:** `search_listings` returns `[]` → `session["status"] == "error"`, `session["error_message"]` is set, `session["fit_card"]` is `None`, loop terminates after step 3.  
  
  3. **Empty wardrobe:** `wardrobe["items"] == []` → `session["wardrobe_empty"] == True`, `session["outfit_suggestion"]` is a generic string, `session["fit_card"]` is still generated.  
  
  4. **Missing query params:** `query = "help me"` → Agent asks for clarification and returns early, `session["status"]` remains `"in_progress"` or error.  
  Only proceed to stretch features after all 4 tests pass.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** 
"I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1: Parse the query**
The agent calls `parse_user_query("I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?")`. 

Returns: `{"description": "vintage graphic tee", "size": None, "max_price": 30.0}`.  
The agent stores this in `session["query_params"]`. 

Since `description` is present and non-empty, the agent proceeds. The user's wardrobe (already loaded from `wardrobe_schema.json` -- contains baggy jeans and chunky white sneakers) is stored in `session["wardrobe"]`.

**Step 2: Search listings**
The agent calls `search_listings(description="vintage graphic tee", size=None, max_price=30.0)`.  

The tool loads `listings.json` via `load_listings()` and scans all 40 listings. It finds 3 matches:
- `lst_006` — "Graphic Tee — 2003 Tour Bootleg Style", $24, size L, style_tags: `["graphic tee", "vintage", "grunge", "streetwear", "band tee"]`
- `lst_033` — "Vintage Band Tee — Faded Grey", $19, size L, style_tags: `["vintage", "grunge", "band tee", "graphic tee", "streetwear"]`
- `lst_002` — "Y2K Baby Tee — Butterfly Print", $18, size S/M, style_tags: `["y2k", "vintage", "graphic tee", "cottagecore"]`

Sorted by relevance (exact "graphic tee" in title + "vintage" in style_tags), `lst_006` is ranked first.  
The agent stores `session["search_results"] = [lst_006, lst_033, lst_002]` and `session["selected_item"] = lst_006`.

**Step 3: Suggest outfit**
The agent calls `suggest_outfit(new_item=lst_006, wardrobe=session["wardrobe"])`.  
The tool examines the new item: category = `tops`, style_tags = `["graphic tee", "vintage", "grunge", "streetwear", "band tee"]`, colors = `["black"]`.  

Scans the wardrobe for complementary pieces:
- `w_001` -- baggy straight-leg jeans (bottoms, streetwear, dark blue) -- matches `streetwear` tag
- `w_007` -- chunky white sneakers (shoes, streetwear, white) -- matches `streetwear` tag

Using the Groq API, the tool generates:  
"Pair this with your baggy straight-leg jeans and chunky white sneakers for a laid-back streetwear vibe. The dark wash balances the faded graphic perfectly. Tuck just the front hem to show the high waist."

The agent stores this in `session["outfit_suggestion"]`.

**Step 4: Create fit card**
The agent calls `create_fit_card(outfit=session["outfit_suggestion"], new_item=lst_006)`.  
The tool constructs a prompt for the Groq API combining the outfit suggestion and the listing metadata (`title`, `price`, `platform`, `style_tags`). 
It generates:  "thrifted this 2003 tour bootleg tee off depop for $24 and it literally goes with my baggy jeans like they were made for each other 🖤 full fit check in my stories"

The agent stores this in `session["fit_card"]` and sets `session["status"] = "complete"`.

**Final output to user:**
The agent returns a formatted summary to the user:

**Found:** **Graphic Tee — 2003 Tour Bootleg Style** -- $24 on Depop (Good condition, Size L)

**How to style it:** Pair this with your baggy straight-leg jeans and chunky white sneakers for a laid-back streetwear vibe. The dark wash balances the faded graphic perfectly. Tuck just the front hem to show the high waist.

**Your fit card:** 
"thrifted this 2003 tour bootleg tee off depop for $24 and it literally goes with my baggy jeans like they were made for each other 🖤 full fit check in my IG stories"

**Error path example:**
If the user stated "I'm looking for a diamond ring under $10," Step 2 would return `[]`. The agent would immediately set `session["status"] = "error"` and `session["error_message"] = "No listings found matching your criteria. Try broadening your search (different keywords, larger size range, or higher budget)."`. 

The agent returns this message to the user immediately. Steps 3 and 4 are never executed.

---