# StoryForge — Project Plan

📖✨

**Personal Story-to-Illustrated-Book Generator**

*A tool that turns real family moments into personalised illustrated children's storybooks — so parents can read bedtime stories drawn from their own life with their toddler.*

| Field | Detail |
|---|---|
| Project Name | StoryForge |
| Status | Active development — v1 pipeline functional |
| Started | 2025 |
| Developer | Personal project |
| Primary User | Parent reading to a toddler |
| Deployment (current) | Docker Compose, local machine |
| Deployment (planned) | Docker → DigitalOcean droplet |

## 1. Motivation & Origin

The project comes from a specific personal need: a parent who wants bedtime stories rooted in real shared experiences with their toddler — not generic fiction, but "remember when we went to the beach and that seagull tried to steal your bag?"

The core insight:

- Toddlers engage more with stories about themselves and their own experiences
- Parents have dozens of small moments that would make great stories but no easy way to turn them into illustrated books
- Existing AI story generators produce generic output — they don't know your child, your family, or your real experiences
- The personalisation layer (retrieval over family memories) is the genuine differentiator

> Key differentiator: Stories grounded in real family memories, with persistent family character profiles. The personalisation and retrieval layer is the core problem, not a bolt-on.

## 2. What StoryForge Does

Given a short description of a real family experience, StoryForge:

- Extracts structured metadata from the memory (setting, characters, themes, mood)
- Plans a story arc (5–7 pages) with a chosen tone: faithful retelling, adventure, moral tale, or funny story
- Generates toddler-appropriate story text per page (picture book register, not baby talk)
- Groups pages by story arc position and generates scene-based illustrations per group (2–3 images per book)
- Serves a web-based reader with image + text per page

The result: type "we went to the beach and Vihaan was chasing a seagull that stole his toy bag," pick a tone, and get an illustrated story in a few minutes.

## 3. Architecture & Tech Stack

### 3.1 Tech Stack

| Component | Technology | Notes |
|---|---|---|
| LLM (orchestration, text) | OpenRouter API | Multiple models via single API key; OpenAI-compatible SDK |
| Image Generation | Gemini 2.5 Flash Image (via OpenRouter) | Scene-based illustrations; no separate API key needed |
| Agentic Framework | LangGraph | Stateful graph-based workflows; plan-then-execute with persistence |
| Family Data / MCP Server | Custom MCP Server (Python) | Exposes character profiles, memories, past stories as tools via MCP protocol |
| Vector Store (v2) | ChromaDB | Embedded in Python process; stores memory embeddings for semantic retrieval |
| Embeddings (v2) | OpenAI text-embedding-3-small | Cheap, effective; used to embed and query family memories |
| Backend | FastAPI + Uvicorn | Async-native; handles long-running generation as background tasks |
| Frontend | Single-file HTML/JS | Web reader served as static file from FastAPI |
| Database | SQLite + SQLAlchemy | Character profiles, memories, story metadata, page data, illustration paths |
| Deployment | Docker Compose → DigitalOcean | Single droplet; Docker Compose for services |

### 3.2 Pipeline Flow

> Memory input → Metadata extraction → Story planning (LangGraph) → Text generation (per page) → Illustration prompt generation (per arc group) → Image generation (Gemini via OpenRouter) → Reader UI

### 3.3 LangGraph Workflow Nodes

The orchestrator is implemented as a LangGraph state graph. Each node's output is persisted in graph state — if image generation fails, text and earlier nodes are not regenerated.

| Node | Input | Output | Tools Used |
|---|---|---|---|
| extract_memory | Raw memory text from user | Structured metadata: setting, characters, themes, mood arc | LLM (OpenRouter) |
| load_characters | Character names from metadata | Full character profiles with visual descriptions | MCP Server (get_characters) |
| plan_story | Metadata + characters + tone choice | Story plan: title, page count, per-page outline with arc_position, scene-based style guide | LLM (OpenRouter) |
| generate_text | Story plan + character profiles + raw memory | Full story text for all pages (structured JSON) | LLM (OpenRouter) |
| generate_illustration_prompts | Page outlines grouped by arc position + style guide | One scene illustration prompt per arc group | LLM (OpenRouter) |
| generate_illustrations | Illustration prompts | Generated images saved to disk; paths stored in DB | Gemini 2.5 Flash Image (OpenRouter) |

> Key design: illustration prompts are generated from page outlines (not page text) and grouped by arc position. Text generation and illustration generation are independent — either can be re-run without affecting the other.

## 4. Data Models

### 4.1 Family Character

| Field | Type | Example |
|---|---|---|
| name | string | Vihaan |
| role | string | son |
| age | string | 2 years old |
| visual_description | string | Black hair, big round dark eyes, often wears dinosaur shirts |
| personality_notes | string (optional) | Curious, loves dinosaurs, cautious at first then adventurous |
| created_at | datetime | 2025-06-01T00:00:00Z |

### 4.2 Memory

| Field | Type | Example |
|---|---|---|
| id | string (uuid) | mem_abc123 |
| raw_text | string | We went to the beach. A seagull swooped down and tried to grab Vihaan's toy bag. |
| setting | string | Beach |
| characters | list[string] | ["Vihaan", "Mamma", "Dada"] |
| themes | list[string] | ["adventure", "humor", "animals"] |
| mood_arc | string | Tension with seagull taking toys, resolved when bag recovered, ending in relief and joy |
| date_approximate | string (optional) | Summer 2025 |
| embedding | vector (v2) | Float array from text-embedding-3-small |
| created_at | datetime | 2025-06-15T10:30:00Z |

### 4.3 Story / Book

| Field | Type | Example |
|---|---|---|
| id | string (uuid) | story_xyz789 |
| title | string | Vihaan and the Sneaky Seagull |
| memory_id | string | mem_abc123 (source memory) |
| tone | enum | funny | adventurous | gentle | moral |
| style_guide | string | Warm sandy yellows, ocean blues, bright midday sun, lively and colorful beach setting |
| pages | list[Page] | See below |
| status | enum | planned | generating | complete | error |
| created_at | datetime | 2025-06-15T11:00:00Z |

### 4.4 Page

| Field | Type | Example |
|---|---|---|
| page_number | int | 1 |
| text | string | Vihaan, Mamma, and Dada walked on the warm sandy beach. |
| illustration_prompt | string | Soft watercolor children's book illustration... A sunny beach with colorful sand toys... |
| illustration_path | string | story_xyz789/illustration_0.png |
| mood | string | cheerful, excited |
| arc_position | string | setup | rising action | climax | resolution | ending |

### 4.5 Illustration Prompt (Graph State)

During the pipeline, illustration prompts are grouped by arc position. This model exists in graph state, not in the DB — the DB stores the resulting illustration_path on each Page.

| Field | Type | Example |
|---|---|---|
| page_numbers | list[int] | [1, 2] |
| arc_position | string | setup (grouped: setup, conflict, resolution) |
| prompt | string | Soft watercolor children's book illustration... |

## 5. Illustration Strategy

### 5.1 Current Approach (v1) — Scene-Based, No Characters

Illustrations are scene/atmosphere images — no people, no characters. This sidesteps the character consistency problem entirely while still providing engaging visuals for toddlers.

- Pages are grouped by arc position for illustration: setup, conflict, resolution (mapped from the five-stage narrative arc)
- One image generated per group — typically 2–3 images per book
- Fixed style prefix on every prompt: "Soft watercolor children's book illustration, simple shapes, warm color palette, gentle and inviting, minimal detail, white background."
- Per-story style guide generated by plan_story, focused on setting colors, lighting, and atmosphere (no character descriptions)
- Illustration prompts describe concrete visible things: objects, setting, weather, colors. No abstract atmosphere or emotions.
- Prompts are built from page outlines (from plan_story), not from the generated page text
- Images generated via Gemini 2.5 Flash Image through OpenRouter — same API key as text LLM calls
- Landscape aspect ratio (3:2) for web reader display

> Why no characters in v1: Character consistency across AI-generated images is an unsolved frontier problem. Scene illustrations avoid this entirely. Toddlers respond to colorful scenes — they don't need to see themselves in the picture to engage with the story.

### 5.2 Arc Position Grouping

The narrative arc uses five positions for story planning (setup, rising action, climax, resolution, ending) but these are mapped to three illustration groups to keep image count manageable:

| Narrative Arc Position | Illustration Group |
|---|---|
| Setup | setup |
| Rising Action | conflict |
| Climax | conflict |
| Resolution | resolution |
| Ending | resolution |

This mapping happens in Python before the illustration prompt LLM call. The five-stage arc is preserved for narrative planning — the three-group mapping only affects illustration generation.

### 5.3 Future: Character Illustrations (v2)

Character profiles already include visual_description in the data model. When illustration consistency techniques mature, characters can be added to prompts by:

- Including character visual descriptions in illustration prompts
- Using image-to-image reference for consistency across pages
- Starting with one hero image per story featuring characters, keeping scene-only for inner pages

## 6. Text Generation Strategy

### 6.1 Register: Picture Book Author, Not Baby Talk

The generate_text prompt targets the register of actual children's picture books for 2–3 year olds. Key principles:

- Narrate what happens — do not address the reader ("Look!", "See?", "What's that?")
- Short declarative sentences, mostly 4–10 words
- Characters do things: action verbs (ran, grabbed, splashed, hid, peeked)
- One sound word per page maximum (splash, whoosh, flap)
- Structural repetition — a phrase echoing across pages, not random repeated words
- Emotion through action and dialogue, not description
- No metaphors, similes, or abstract language
- No narrator commentary ("What a fun day!", "Hooray!") — though occasional use is acceptable

> The prompt uses few-shot examples showing the target register. Examples do 80% of the work — rules are guardrails against specific failure modes. Best practice: swap in your own approved outputs as examples over time.

### 6.2 Prompt Architecture

- System prompt loaded from a separate file (not inline Python string)
- Few-shot examples embedded in the system prompt showing 3 different tones
- User message provides: story plan, character profiles, raw memory text
- Output: structured JSON with per-page text, mood, and page number
- Raw memory text is passed through to generate_text alongside metadata — this prevents the LLM from ignoring real events and inventing generic scenes

## 7. Reader UI

### 7.1 Current Implementation

- Single-file HTML/JS served as a static file from FastAPI (/reader or /static/reader.html)
- Loads story data from GET /stories/{id} API endpoint
- One page displayed at a time: illustration on top, text below
- Next/previous navigation between pages
- Image stays static when advancing between pages that share the same illustration — only the text updates. Image changes when advancing to a page with a different illustration_path.
- Images served via FastAPI static files mount at /output/
- Landscape images (3:2 aspect ratio), responsive scaling

### 7.2 Future Reader Enhancements

- Auto-advance timer (pattern from MoodyBook: Off / 20s / 30s / 45s / 60s)
- Mobile/phone-friendly layout
- PDF export endpoint (GET /stories/{id}/pdf)
- Swipe navigation for touch devices

## 8. MCP Server — Family Data Layer

The family data (characters, memories, past stories) is exposed via a custom MCP server. This serves two purposes: the LangGraph agent queries it as a tool during story generation, and it's reusable from any MCP-compatible client (Claude Desktop, Claude Code, etc.).

### 8.1 MCP Tools Exposed

| Tool | Description | Used By |
|---|---|---|
| get_characters | Returns all family character profiles (or filtered by name) | load_characters node |
| add_character | Creates or updates a character profile | Setup UI / manual |
| store_memory | Saves a new memory with extracted metadata | extract_memory node |
| search_memories | Keyword search over stored memories (v1) / semantic search (v2) | Retrieval pipeline (v2) |
| list_stories | Returns all generated stories with status | Library UI |
| get_story | Returns full story with pages, text, and image paths | Reader UI |

> Why MCP here: The family data layer is the part of the stack that is most "yours" — it's not wrapping someone else's API. Building it as an MCP server gives a concrete portfolio talking point and makes the data reusable beyond this one app.

## 9. Retrieval Layer (v2)

In v1, the user types a specific memory and the system generates from it directly. No retrieval needed — the LLM has all context in the prompt.

In v2, the user has accumulated 20+ stored memories. The input can become vague: "make a story about animals" or "a story about being brave." The system must find the right memory (or combine elements from several).

### 9.1 Retrieval Flow

> Vague prompt → Embed query (text-embedding-3-small) → Semantic search against ChromaDB → Retrieve top 3 memories → LLM picks best match (or combines) → Proceed with normal pipeline

### 9.2 Technical Details

- Embedding model: OpenAI text-embedding-3-small (cheap, effective for short text)
- Vector store: ChromaDB (embedded in Python process, persists to disk, no separate server)
- Chunking strategy: Each memory is one chunk (memories are short, no splitting needed)
- Metadata filtering: Pre-filter by character, theme, or setting before semantic ranking
- Agent decides: The LangGraph orchestrator evaluates retrieved memories and chooses the best fit (or asks the user to pick)

## 10. API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| /characters | GET | List all family character profiles |
| /characters | POST | Create or update a character profile |
| /characters/{name} | DELETE | Remove a character |
| /memories | GET | List all stored memories |
| /memories | POST | Store a new memory (triggers metadata extraction) |
| /memories/search | POST | Search memories by keyword (v1) or semantically (v2) |
| /stories/generate | POST | Kick off story generation from a memory (returns job ID) |
| /stories/{id}/status | GET | Poll generation status |
| /stories | GET | List all generated stories |
| /stories/{id} | GET | Full story with pages, text, illustration paths |
| /stories/{id}/pdf | GET | Download story as PDF (planned) |
| /stories/{id}/pages/{n}/regenerate | POST | Regenerate a single page (text + illustration) |
| /reader | GET | Serve the reader HTML UI |
| /output/{path} | GET | Serve generated illustration images (static files) |

## 11. Key Decisions & Rationale

| Decision | Rationale |
|---|---|
| OpenRouter for all API calls (text + image) | Single API key for LLM and image generation; no separate OpenAI account needed; already had account |
| Gemini 2.5 Flash Image over DALL-E 3 | Available through OpenRouter (no separate key); good quality for watercolor scenes; cost-effective |
| Scene illustrations, no characters (v1) | Sidesteps character consistency problem entirely; toddlers engage with colorful scenes; characters planned for v2 |
| 3 illustration groups per book | Arc positions mapped from 5-stage to 3 groups (setup/conflict/resolution); keeps image count manageable while covering the story |
| Illustration prompts from outlines, not text | Outlines describe what happens (useful for scene selection); page text is written for toddlers (not useful for image prompting); also decouples the two generation paths |
| Picture book register, not baby talk | Few-shot examples set the target; "parent pointing at pictures" register produces commentary, not narration; real picture books narrate events |
| Prompts in separate files, not inline Python | Easier to read, edit, and diff; no escaping issues; prompt changes don't touch code |
| LangGraph over plain Python | Stateful graph with persistence; retry logic; nodes can be re-run independently |
| MCP server for family data | Reusable from any MCP client; clean tool boundary; portfolio talking point |
| SQLite + SQLAlchemy | No separate database server; sufficient scale; ORM for structured models |
| story_id generated before graph runs | Image generation node needs a save path; ID must exist in state before the graph executes |
| Style guide is scene-based only | plan_story generates setting/color/lighting descriptions; no character expressions or actions; prevents conflicts with no-character illustration approach |
| Docker Compose for deployment | Already familiar from MoodyBook; single droplet on DigitalOcean |

## 12. Known Limitations

- No character illustrations in v1 — scene-only approach means no visual representation of family members in pictures
- End-to-end generation takes several minutes (mostly image generation latency); not real-time
- Text register occasionally drifts between runs (LLM non-determinism) — a quick hand-edit pass is expected as part of the workflow
- Image consistency between illustration groups is approximate — recurring objects (e.g., a beach bag) may look different across images
- Story quality depends on the richness of the input memory — very short inputs produce generic stories
- No image input yet — all memories are text-based; photo-to-story is a future feature
- Single-user only in v1 — no auth, no multi-family support
- Style guide from plan_story can vary between runs; visual identity not yet fully locked down

## 13. Roadmap

| Version | Focus | Status |
|---|---|---|
| v0.1 | Project skeleton: FastAPI + LangGraph + basic single-memory-to-story pipeline (text only) | Complete |
| v0.5 | Image generation: Gemini via OpenRouter, scene-based illustration grouping, style guide system | Complete |
| v0.7 | Reader UI: single-file HTML, static image serving, page navigation with smart image updates | In Progress |
| v1.0 | Full pipeline: MCP server for family data, PDF export, async job system, polish | Next |
| v1.5 | Character illustrations (v2): character profiles in image prompts, consistency techniques | Planned |
| v2.0 | Retrieval: ChromaDB + embeddings, vague prompt → memory search, hybrid filtering | Future |
| v2.5 | Multi-user auth, family sharing, story library management | Future |
| v3.0 | Photo/image input for memories, OCR, richer memory types | Long term |

## 14. Portfolio & Interview Talking Points

| Skill Area | What This Project Demonstrates |
|---|---|
| Agentic Workflows | LangGraph orchestrator with plan-then-execute architecture; independent re-runnable nodes; stateful graph with persistence |
| Tool Use | Agent calls external tools (LLM, image API, MCP server) with structured inputs/outputs; tool selection is organic, not contrived |
| Retrieval (RAG) | Semantic search over personal memories using embeddings + ChromaDB; hybrid filtering (metadata + vector similarity); agent-driven query refinement |
| MCP / Protocols | Custom MCP server exposing family data as tools; reusable across clients; clean tool boundaries |
| LLM Integration | Structured output parsing; prompt engineering for register control; few-shot examples; multi-model routing via OpenRouter; prompts as external files |
| Prompt Engineering | Iterative register tuning for toddler text (baby talk → picture book voice); scene-based illustration prompts; constraint vs. example-driven approaches |
| Image Generation | Scene-based illustration strategy; arc-position grouping; style consistency via fixed prefix + per-story guide; Gemini integration through OpenRouter |
| Async Architecture | Long-running generation as background tasks; job polling; graceful failure handling |
| System Design | End-to-end pipeline from unstructured input to rendered output; separation of concerns (data layer, orchestration, generation, presentation) |

## 15. Open Questions

- Which OpenRouter model for story text? Worth A/B testing across models for register consistency
- PDF layout: simple image-above-text per page, or more designed? (Start simple)
- Should the user approve the story plan before generation, or is automatic fine? (Leaning toward showing the plan with a "Generate" button)
- How to handle memories with multiple possible stories? Let the tone selector handle this?
- When to introduce character illustrations — what consistency techniques to use (reference images, image-to-image, seed control)?
- Fixed global style prefix vs. per-story variation — should all StoryForge books look the same or have distinct visual identities?
- Temperature tuning for generate_text — lower temperature reduces register drift between runs but may reduce creative variation

*Confidential — Personal Project*
