# StoryForge

Turns real family memories into personalized illustrated children's storybooks.

## How it works

Provide a memory and a tone — StoryForge runs a LangGraph pipeline that extracts characters, plans the story, writes the pages, generates illustration prompts, and produces images via Gemini Flash.

```
extract_memory → load_characters → plan_story → generate_text → evaluate_text → generate_illustration_prompts → validate_illustration_prompts → generate_illustrations
                                                                      ↓ (fail, up to 2x)
                                                                regenerate_text
```

Images are saved to `output/{story_id}/`.

## Setup

```bash
cp .env.example .env  # add your OPENROUTER_API_KEY
docker compose up
```

Or run locally:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
OPENROUTER_API_KEY=your_key uvicorn app.main:app --reload
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/stories/generate` | Full pipeline — text + illustrations |
| GET | `/stories` | List all stories |
| GET | `/stories/{id}` | Get story with pages |
| GET | `/stories/{id}/status` | Get generation status |
| POST | `/stories/{id}/evaluate-text` | Run text register evaluation |
| POST | `/stories/{id}/generate-illustration-prompts` | Regenerate illustration prompts |
| POST | `/stories/{id}/validate-illustration-prompts` | Validate illustration prompts against rubric |
| POST | `/stories/{id}/generate-illustrations` | Generate images from existing prompts |

### Generate a story

```bash
curl -X POST http://localhost:8000/stories/generate \
  -H "Content-Type: application/json" \
  -d '{"memory_text": "We went to the beach and found a crab...", "tone": "funny"}'
```

Valid tones: `funny`, `adventurous`, `gentle`, `moral`

## Environment variables

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | Required. Used for both text and image generation. |
| `IMAGE_MODEL` | Image model override. Default: `google/gemini-2.5-flash-image` |
