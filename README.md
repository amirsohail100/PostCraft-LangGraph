# PostCraft-LangGraph

Writer → Reviewer iterative loop: an LLM (Mistral) drafts a LinkedIn post — searching the web with Tavily if it needs current info — and a second LLM (Groq) reviews it. If rejected, the writer gets the feedback and retries, up to 3 attempts total.

## Structure

```
PostCraft-LangGraph/
├── main.py            # FastAPI app: /api/generate, /api/health, serves the UI
├── agent.py            # Graph wiring: writer <-> tools loop, then -> reviewer -> loop/end
├── schema/
│   └── payload.py       # GenerateRequest / GenerateResponse
├── state/
│   └── WriterState.py    # WriterState TypedDict
├── tools/
│   └── nodes.py           # writer/reviewer/tool nodes + routing functions
├── static/
│   ├── index.html
│   ├── style.css
│   └── script.js           # topic input -> verdict badge + post preview card
├── requirements.txt
└── .env                     # GROQ_API_KEY, MISTRAL_API_KEY, TAVILY_API_KEY
```

## Bugs found in the uploaded code and fixed here

1. **`TavilySearch(max_result=3)`** — wrong keyword, the actual param is `max_results` (plural). Fixed.
2. **The tool loop never went back to the writer.** `graph.add_edge("tools", "reviewer")` sent search results straight to the reviewer, skipping post generation entirely — `reviewer_node` would then crash with `KeyError: 'draft'` because `draft` was never set on that path. Fixed by routing `tools -> writer` so the writer actually uses the search results to finish the post, then a "have we finished, or do we need to search again?" check (`should_use_tool`) decides whether to loop back to `tools` again or move on to `extract_draft`.
3. **`REVIEWER_SYSTEM_PROMPT = { ... }` and the `prompt` inside `reviewer_node`** were wrapped in `{ }`. Since there's no comma between the string lines, Python's implicit string concatenation still applies — but the outer `{ }` turns the whole thing into a **set containing one string**, not a string itself. Passing a set as message content would break the LLM call. Fixed by removing the braces (plain string / parentheses for line-continuation).
4. **Key name mismatch:** `reviewer_node` returned `{"review_feedback": feedback, ...}`, but `WriterState` defines the field as `reviewer_feedback`, and `writer_node` reads `state["reviewer_feedback"]`. Because the key never matched, the writer never actually saw the reviewer's real feedback on a retry. Fixed to use `reviewer_feedback` consistently.
5. **`previous_feedback = state["reviewer_feedback"]`** was read unconditionally, even on attempt 1 before any review happens — this raises `KeyError` on the very first call unless the caller pre-seeds that key. Fixed with `state.get("reviewer_feedback", "")`, and `run_writer()` also seeds all fields explicitly on the initial invoke.
6. **Added a safety cap** (`MAX_TOOL_ROUNDS = 2`) on total search round-trips across the whole run — without one, a model that keeps deciding to search again has no hard stop, which is a real cost/availability risk once this is public.

Everything else (the 3-attempt cap, the approve/reject wording, the writer/reviewer prompts) is unchanged from what you wrote.

## Endpoints

- `GET  /api/health` → `{"status": "ok"}`
- `POST /api/generate` → body `{"topic": "..."}`, returns:
  ```json
  {
    "draft": "...",
    "is_approved": true,
    "attempt": 2,
    "reviewer_feedback": "..."
  }
  ```
  Rate limited to **3 requests/minute per IP** — this endpoint can chain up to 8+ LLM/tool calls, so it's both slow and the most expensive one in this project family.
- `GET  /` → the UI (`static/index.html`)

## Run locally

```bash
pip install -r requirements.txt
# .env me teeno keys daalo: GROQ_API_KEY, MISTRAL_API_KEY, TAVILY_API_KEY
uvicorn main:app --reload --port 8000
```

Browser me `http://localhost:8000` kholo. Ek generation me 10-60 seconds lag sakte hain (multiple LLM calls + possible web searches + up to 3 attempts) — UI "Writing & reviewing..." dikhata rehta hai isi beech.

## Before going to production

- CORS abhi `allow_origins=["*"]` par hai — apne actual frontend domain tak restrict kar dena.
- Ye endpoint synchronous hai (request khatam hone tak connection khula rehta hai). Agar deploy platform ka request timeout kam hai (jaise 30s), to lambi generations timeout ho sakti hain — us case me background job + polling/websocket pattern me move karna better rahega.
- `reviewer_feedback` sirf latest attempt ka feedback carry karta hai; agar tumhe har attempt ka pura history UI me dikhana ho, `agent.py` me ek `feedback_history: list` field add kar sakte ho.
