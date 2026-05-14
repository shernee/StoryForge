# StoryForge — Project Plan

> A tool that turns real family moments into personalised illustrated children's storybooks — so parents can read bedtime stories drawn from their own life with their toddler.

| Field | Detail |
|---|---|
| Project Name | StoryForge |
| Status | Planning |
| Started | 2025 |
| Developer | Personal project |
| Primary User | Parent reading to a toddler |
| Deployment (current) | Local development |
| Deployment (planned) | Docker → DigitalOcean droplet |

---

## 1. Motivation & Origin

The project comes from a specific personal need: a parent who wants bedtime stories rooted in real shared experiences with their toddler — not generic fiction, but "remember when we went to the beach and that seagull tried to steal your bucket?"

The core insight:

- Toddlers engage more with stories about themselves and their own experiences
- Parents have dozens of small moments that would make great stories but no easy way to turn them into illustrated books
- Existing AI story generators produce generic output — they don't know your child, your family, or your real experiences
- The personalisation layer (retrieval over family memories) is the genuine differentiator

> **Key differentiator:** Stories grounded in real family memories, with persistent family character profiles for visual consistency across books. This is where retrieval becomes the core problem, not a bolt-on.

---

## 2. What StoryForge Does

Given a short description of a real family experience, StoryForge:

- Extracts structured metadata from the memory (setting, characters, themes, mood)
- Plans a story arc (3–5 pages) with a chosen tone: faithful retelling, adventure, moral tale, or funny story
- Generates toddler-appropriate story text per page (simple vocabulary, short sentences, repetition)
- Generates style-consistent illustrations per page using a global style guide and persistent character profiles
- Assembles into a swipeable phone-friendly reader and/or downloadable PDF

The result: type "we went to the park and Aiden was scared of a big dog but then pet it," pick a tone, and get an illustrated bedtime story in a few minutes.

---

## 3. Architecture & Tech Stack

### 3.1 Tech Stack

| Component | Technology | Notes |
|---|---|---|
| LLM (orchestration, text) | OpenRouter API | GPT-4o / Claude via OpenRouter; single API key for all text LLM calls |
| Image Generation | DALL-E 3 (OpenAI API) | Good prompt adherence for style consistency; upgrade path to Flux via Replicate |
| Agentic Framework | LangGraph | Stateful graph-based workflows; plan-then-execute with retry loops |
| Family Data / MCP Server | Custom MCP Server (Python) | Exposes character profiles, memories, past stories as tools via MCP protocol |
| Vector Store (v2) | ChromaDB | Embedded in Python process; stores memory embeddings for semantic retrieval |
| Embeddings (v2) | OpenAI text-embedding-3-small | Cheap, effective; used to embed and query family memories |
| Backend | FastAPI + Uvicorn | Async-native; handles long-running generation as background tasks |
| Frontend | Single-file HTML/JS (v1) | Phone-friendly reader with swipeable pages; React upgrade path for v2 |
| Storage | SQLite | Character profiles, memories, story metadata; simple, no infra |
| Deployment | Docker Compose → DigitalOcean | Single droplet; Docker Compose for services |

### 3.2 Pipeline Flow

```
Memory input → Metadata extraction → Story planning (LangGraph orchestrator) → Text generation (per page) → Illustration generation (DALL-E 3 per page) → Assembly → Reader UI / PDF
```

### 3.3 LangGraph Workflow Nodes

The orchestrator is implemented as a LangGraph state graph with the following nodes. Each node's output is persisted in graph state — if image generation fails on page 3, text and pages 1–2 are not regenerated.

| Node | Input | Output | Tools Used |
|---|---|---|---|
| extract_memory | Raw memory text from user | Structured metadata: setting, characters, themes, mood arc | LLM (OpenRouter) |
| load_characters | Character names from metadata | Full character profiles with visual descriptions | MCP Server (get_characters) |
| plan_story | Metadata + characters + user tone choice | Story plan: title, page count, per-page outline, style guide | LLM (OpenRouter) |
| generate_text | Story plan + character profiles | Full story text for all pages (structured JSON) | LLM (OpenRouter) |
| generate_illustrations | Per-page text + style guide + character descriptions | One illustration per page | DALL-E 3 API |
| evaluate_output | Generated illustrations + page text | Pass/retry decision per page | LLM (OpenRouter, optional) |
| assemble_book | All text + all images | Final book object stored to DB | Internal |

> **What makes this agentic (not just a chain):** the orchestrator plans before executing, uses tools (LLM, image API, MCP), makes decisions based on intermediate results (retry bad illustrations), and can recover from failures without re-running the full pipeline.

---

## 4. Data Models

### 4.1 Family Character

| Field | Type | Example |
|---|---|---|
| name | string | Aiden |
| role | string | son |
| age | string | 3 years old |
| visual_description | string | Short brown curly hair, big brown eyes, usually wears blue t-shirt and red shorts |
| personality_notes | string (optional) | Curious, loves dinosaurs, cautious at first then adventurous |
| created_at | datetime | 2025-06-01T00:00:00Z |

### 4.2 Memory

| Field | Type | Example |
|---|---|---|
| id | string (uuid) | mem_abc123 |
| raw_text | string | We went to the beach. A seagull swooped down and tried to grab the bucket. Aiden screamed but then laughed. |
| setting | string | Beach |
| characters | list[string] | ["Aiden", "Dad"] |
| themes | list[string] | ["courage", "humor", "animals"] |
| mood_arc | string | surprise → fear → laughter |
| date_approximate | string (optional) | Summer 2025 |
| embedding | vector (v2) | Float array from text-embedding-3-small |
| created_at | datetime | 2025-06-15T10:30:00Z |

### 4.3 Story / Book

| Field | Type | Example |
|---|---|---|
| id | string (uuid) | story_xyz789 |
| title | string | Aiden and the Sneaky Seagull |
| memory_id | string | mem_abc123 (source memory) |
| tone | enum | funny | adventurous | gentle | moral |
| style_guide | string | Soft watercolour, warm tones, simple shapes, rounded edges |
| pages | list[Page] | See below |
| status | enum | planned | generating | complete | error |
| created_at | datetime | 2025-06-15T11:00:00Z |

### 4.4 Page

| Field | Type | Example |
|---|---|---|
| page_number | int | 1 |
| text | string | One sunny morning, Aiden and Daddy went to the big blue beach. |
| illustration_prompt | string | Soft watercolour illustration of a 3-year-old boy with brown curly hair... |
| illustration_path | string | /output/story_xyz789/page_1.png |
| mood | string | cheerful, excited |
| arc_position | string | setup |

---

## 5. MCP Server — Family Data Layer

The family data (characters, memories, past stories) is exposed via a custom MCP server. This serves two purposes: the LangGraph agent queries it as a tool during story generation, and it's reusable from any MCP-compatible client (Claude Desktop, Claude Code, etc.).

### 5.1 MCP Tools Exposed

| Tool | Description | Used By |
|---|---|---|
| get_characters | Returns all family character profiles (or filtered by name) | load_characters node |
| add_character | Creates or updates a character profile | Setup UI / manual |
| store_memory | Saves a new memory with extracted metadata | extract_memory node |
| search_memories | Keyword search over stored memories (v1) / semantic search (v2) | Retrieval pipeline (v2) |
| list_stories | Returns all generated stories with status | Library UI |
| get_story | Returns full story with pages, text, and image paths | Reader UI |

> **Why MCP here:** The family data layer is the part of the stack that is most "yours" — it's not wrapping someone else's API. Building it as an MCP server gives a concrete portfolio talking point and makes the data reusable beyond this one app.

---

## 6. Retrieval Layer (v2)

In v1, the user types a specific memory and the system generates from it directly. No retrieval needed — the LLM has all context in the prompt.

In v2, the user has accumulated 20+ stored memories. The input can become vague: "make a story about animals" or "a story about being brave." The system must find the right memory (or combine elements from several).

### 6.1 Retrieval Flow

```
Vague prompt → Embed query (text-embedding-3-small) → Semantic search against ChromaDB → Retrieve top 3 memories → LLM picks best match (or combines) → Proceed with normal pipeline
```

### 6.2 Technical Details

- Embedding model: OpenAI text-embedding-3-small (cheap, effective for short text)
- Vector store: ChromaDB (embedded in Python process, persists to disk, no separate server)
- Chunking strategy: Each memory is one chunk (memories are short, no splitting needed)
- Metadata filtering: Pre-filter by character, theme, or setting before semantic ranking
- Agent decides: The LangGraph orchestrator evaluates retrieved memories and chooses the best fit (or asks the user to pick)

### 6.3 Portfolio Talking Points

- Embedding model selection and trade-offs
- Hybrid retrieval: metadata filters + semantic similarity
- Agent-driven retrieval: the model decides what to search for, evaluates results, and can refine the query
- Retrieval evaluation: how to measure if the right memories are being surfaced

---

## 7. Illustration Consistency Strategy

Style consistency across pages is the hardest practical problem in this project. Perfect character consistency across AI-generated images is still an unsolved problem at the frontier. The strategy here is to get 80% of the way with prompt engineering and accept the remaining variation.

### 7.1 Approach

- Global style directive generated once per book at plan time (e.g., "soft watercolour, warm tones, simple shapes, rounded edges, children's book illustration")
- Character visual descriptions pulled from persistent family profiles and prepended to every image prompt
- Consistent art style keywords in every prompt (same artist style reference, same medium, same colour palette)
- DALL-E 3 chosen over alternatives for stronger prompt adherence (Flux is higher quality but less controllable)

> **Expectation management:** Illustrations will be in the same style and colour palette, and characters will be recognisably similar, but not pixel-perfect consistent. For a toddler audience, this is more than acceptable.

---

## 8. API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| /characters | GET | List all family character profiles |
| /characters | POST | Create or update a character profile |
| /characters/{name} | DELETE | Remove a character |
| /memories | GET | List all stored memories |
| /memories | POST | Store a new memory (triggers metadata extraction) |
| /memories/search | POST | Search memories by keyword (v1) or semantically (v2) |
| /stories/generate | POST | Kick off story generation from a memory (returns job ID) |
| /stories/{id}/status | GET | Poll generation status (planned/generating/complete/error) |
| /stories | GET | List all generated stories |
| /stories/{id} | GET | Full story with pages, text, image URLs |
| /stories/{id}/pdf | GET | Download story as PDF |
| /stories/{id}/pages/{n}/regenerate | POST | Regenerate a single page (text + illustration) |

---

## 9. Key Decisions & Rationale

| Decision | Rationale |
|---|---|
| OpenRouter for LLM calls | Single API key for multiple models; already have an account; OpenAI-compatible SDK works with LangGraph |
| DALL-E 3 for illustrations | Best prompt adherence for style consistency; upgrade path to Flux/Replicate if quality insufficient |
| LangGraph over plain Python | Stateful graph with persistence, retry logic, and visualisation; recognised portfolio tool; plan-then-execute pattern is a natural fit |
| MCP server for family data | Reusable from any MCP client; clean tool boundary; strongest portfolio talking point |
| ChromaDB over Pinecone/Weaviate | Embedded in process, no infra; sufficient for <1000 memories; easy local development |
| SQLite over Postgres | No separate database server; sufficient scale; portable |
| Async generation with job polling | Image generation takes 10–15s per page; 5-page book = 60s+ total; must be async |
| Single LLM call for all page text | 5-page toddler book is short enough; cheaper and faster; per-page only if quality issues arise |
| Style guide per book, not per page | Consistency requires the same style directive everywhere; generated once at plan time |
| Docker Compose for deployment | Already familiar from MoodyBook; single droplet on DigitalOcean; no Kubernetes needed |

---

## 10. Known Limitations

- Character consistency across illustrations is approximate, not exact — an unsolved problem at the frontier
- End-to-end generation takes several minutes (mostly image generation latency); not real-time
- Image generation has per-call API costs (DALL-E 3: ~$0.04–$0.08 per image; 5-page book ≈ $0.20–$0.40)
- Story quality depends on the richness of the input memory — very short inputs produce generic stories
- No image input yet — all memories are text-based; photo-to-story is a future feature
- Single-user only in v1 — no auth, no multi-family support

---

## 11. Roadmap

| Version | Focus | Status |
|---|---|---|
| v0.1 | Project skeleton: FastAPI + LangGraph + basic single-memory-to-story pipeline (text only, no images) | Next |
| v0.5 | Image generation: DALL-E 3 integration, style guide system, character profiles | Planned |
| v1.0 | Full pipeline: MCP server for family data, reader UI, PDF export, async job system | Planned |
| v1.5 | Polish: regenerate individual pages, tone selector, mobile-friendly reader | Planned |
| v2.0 | Retrieval: ChromaDB + embeddings, vague prompt → memory search, hybrid filtering | Future |
| v2.5 | Multi-user auth, family sharing, story library management | Future |
| v3.0 | Photo/image input for memories, OCR, richer memory types | Long term |

---

## 12. Portfolio & Interview Talking Points

| Skill Area | What This Project Demonstrates |
|---|---|
| Agentic Workflows | LangGraph orchestrator with plan-then-execute architecture; conditional branching; retry logic; stateful graph with persistence |
| Tool Use | Agent calls external tools (LLM, image API, MCP server) with structured inputs/outputs; tool selection is organic, not contrived |
| Retrieval (RAG) | Semantic search over personal memories using embeddings + ChromaDB; hybrid filtering (metadata + vector similarity); agent-driven query refinement |
| MCP / Protocols | Custom MCP server exposing family data as tools; reusable across clients; clean tool boundaries |
| LLM Integration | Structured output parsing; prompt engineering for consistency; multi-model routing via OpenRouter; temperature and output format control |
| Async Architecture | Long-running generation as background tasks; job polling; graceful failure handling |
| System Design | End-to-end pipeline from unstructured input to rendered output; separation of concerns (data layer, orchestration, generation, presentation) |

---

## 13. Open Questions

- Which OpenRouter model for story text? GPT-4o is reliable, Claude is strong at creative writing — worth A/B testing
- PDF layout: simple image-above-text per page, or more designed? (Start simple)
- Should the user approve the story plan before generation, or is automatic fine? (Leaning toward showing the plan with a "Generate" button)
- How to handle memories with multiple possible stories? (e.g., a beach trip could be a courage story or a funny story) — let the tone selector handle this?
- Image generation cost management: cap at N books per day? Show cost estimate before generating?
