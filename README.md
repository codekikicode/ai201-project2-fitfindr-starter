# FitFindr — Starter Kit

FitFindr is a multi-tool AI agent that helps users find secondhand clothing and figure out how to wear it. Given a natural language query like "vintage graphic tee under $30, size M," the agent parses the request, searches a mock listings dataset, suggests an outfit using the user's existing wardrobe, and generates a shareable social-media caption.

## Tool Inventory

| Tool | Inputs | Output | Purpose |
|------|--------|--------|---------|
| `parse_user_query(query: str)` | Raw user query string | `dict` with `description` (str), `size` (str or None), `max_price` (float or None) | Extracts structured search parameters from free-text input using regex. |
| `search_listings(description: str, size: str \| None, max_price: float \| None)` | Parsed keywords, optional size filter, optional price ceiling | `list[dict]` of matching listings sorted by relevance score | Filters the mock dataset by price and size, then scores keyword matches across title, description, style_tags, and category. |
| `suggest_outfit(new_item: dict, wardrobe: dict)` | A single listing dict + the user's wardrobe dict | `str` — natural language outfit suggestion | Calls the Groq LLM to generate styling advice. Falls back to rule-based matching if the wardrobe is empty or the API fails. |
| `create_fit_card(outfit: str, new_item: dict)` | Outfit suggestion string + the selected listing dict | `str` — Instagram-style caption | Generates a casual social-media caption. Uses template rotation if the outfit string is empty or the API fails. |

## Planning Loop

The agent does **not** run all three tools in a fixed sequence. It uses a conditional planning loop that checks the result of each step before deciding what to do next:

1. **Parse** — `parse_user_query` extracts description, size, and max_price from the user's raw text. If no description is found, the agent returns a clarification message immediately.
2. **Search** — `search_listings` runs with the parsed parameters. If it returns an empty list, the agent sets `session["error"]` and returns early. `suggest_outfit` and `create_fit_card` are **never called** in this branch.
3. **Select** — If results exist, the top result (`results[0]`) is stored in `session["selected_item"]`.
4. **Suggest** — `suggest_outfit` receives the selected item and the wardrobe. If the wardrobe is empty, it returns generic advice and the loop continues.
5. **Caption** — `create_fit_card` receives the outfit suggestion and the selected item. If the outfit string is empty, it returns a fallback message instead of crashing.
6. **Return** — The completed session dict is returned to the UI.

This branching design is the core of the agent's behavior: it responds to what it receives rather than blindly executing a pipeline.

## State Management

State is stored in a single `session` dictionary that lives for the entire interaction. It is initialized by `_new_session()` and passed through the planning loop in `agent.py`.

Key fields:
- `session["parsed"]` — output of `parse_user_query`
- `session["search_results"]` — output of `search_listings`
- `session["selected_item"]` — the top result, fed into `suggest_outfit`
- `session["outfit_suggestion"]` — output of `suggest_outfit`, fed into `create_fit_card`
- `session["fit_card"]` — final output
- `session["error"]` — set if the loop terminates early

No tool calls another tool directly. The planning loop reads from and writes to the session dict, so data flows explicitly from one step to the next without re-entry or hardcoded values.

## Error Handling

Every tool handles its own failure mode and communicates it to the agent:

| Tool | Failure Mode | Agent Response |
|------|-------------|----------------|
| `search_listings` | No results match | Sets `session["error"]` to: "No listings found matching your criteria. Try broadening your search (different keywords, larger size range, or higher budget)." Returns early. |
| `suggest_outfit` | Empty wardrobe (`wardrobe["items"] == []`) | Returns generic styling advice based on the item's category and style_tags. The agent continues to `create_fit_card`. |
| `create_fit_card` | Empty outfit string | Returns a fallback message using only the item's title, price, and platform: "Found a [title] for $[price] on [platform]. Can't wait to style this!" |

**Concrete example from testing:**  
Running `python -c "from agent import run_agent; ... run_agent('designer ballgown size XXS under $5', ...)"` returned `session["error"]` with the broadening-search message, while `session["fit_card"]` remained `None`. Screenshots of this terminal output are included in the demo video.

## AI Usage

I used Kimi (Kimi 2.6) as my AI coding assistant for two major parts of the implementation:

**1. Tool implementations (`tools.py`)**
- **Input:** I pasted the Tool 1–4 specs from `planning.md` (what each tool does, exact inputs/outputs, failure modes) plus the `listings.json` schema and `wardrobe_schema.json` structure.
- **Output:** Kimi generated complete implementations for `search_listings`, `suggest_outfit`, `create_fit_card`, and `parse_user_query`, including Groq API calls, rule-based fallbacks, and rotating template captions.
- **Changes:** I fixed a 3-space indentation error in `create_fit_card` that would have caused an `IndentationError`. I also removed stray `""` string literals that appeared between functions. Finally, I adjusted the test expectations in `tests/test_tools.py` when I realized my `parse_user_query` correctly strips filler words like "help me," so the assertion needed to expect `"find something cool"` instead of `"help me find something cool"`.

**2. Planning loop (`agent.py`)**
- **Input:** I shared the Planning Loop section, the Architecture ASCII diagram, and the State Management section from `planning.md`.
- **Output:** Kimi generated the `run_agent()` function with the conditional branching logic (parse → guard → search → branch → suggest → fit card).
- **Changes:** I adapted the generated code to match the starter repo's existing `_new_session()` structure. The starter used `session["parsed"]` and `session["error"]`, while my planning.md used `session["query_params"]` and `session["error_message"]`. I aligned the implementation with the starter's keys rather than the planning.md's keys to ensure compatibility with the pre-built `app.py` and CLI tests.

## Setup & Run

```bash
pip install -r requirements.txt
