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
cp .env.example .env  # fill in OPENROUTER_API_KEY and ADMIN_CODE
docker compose up
```

Or run locally:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

On startup the app runs any pending Alembic migrations and seeds the admin access code from `ADMIN_CODE` automatically.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | Used for text and image generation |
| `ADMIN_CODE` | Yes | Access code for the admin account (unlimited generations) |
| `IMAGE_MODEL` | No | Image model override. Default: `google/gemini-2.5-flash-image` |

## Access codes

The app is invite-only. Users log in at `/login` with a personal access code. Non-admin codes are limited to **3 story generations per day**.

Provision a new code (run inside the container or with the venv active):

```bash
python scripts/create_code.py "Jane Smith"
# Created:  code=abc123  label=Jane Smith  admin=False

python scripts/create_code.py --list   # list all codes and usage
```

The admin code is set via `ADMIN_CODE` in `.env` and created automatically on first boot — do not use the script for this.

## Database migrations

Schema changes are managed with **Alembic**. Migrations run automatically on startup, so a `docker compose up` after a code update is all that's normally needed.

When you make a change to a model in `app/models/database.py`:

1. Generate a migration:
   ```bash
   docker compose exec app alembic revision --autogenerate -m "describe the change"
   ```
2. Review the generated file in `alembic/versions/` — Alembic's autogenerate is good but not perfect, especially for SQLite (which can't `ALTER` columns or drop constraints). Adjust if needed.
3. Apply it locally:
   ```bash
   docker compose exec app alembic upgrade head
   ```
4. Commit the migration file alongside the model change.

Other useful commands:

```bash
alembic current          # show which revision the DB is on
alembic history          # list all revisions
alembic downgrade -1     # roll back one revision
```

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/stories/generate` | Full pipeline — text + illustrations |
| GET | `/stories` | List all stories |
| GET | `/stories/{id}` | Get story with pages |
| GET | `/stories/{id}/status` | Get generation status |
| GET | `/stories/{id}/pdf` | Download story as PDF |
| POST | `/stories/{id}/evaluate-text` | Run text register evaluation |
| POST | `/stories/{id}/generate-illustration-prompts` | Regenerate illustration prompts |
| POST | `/stories/{id}/validate-illustration-prompts` | Validate prompts against rubric |
| POST | `/stories/{id}/generate-illustrations` | Generate images from existing prompts |
| GET | `/auth/status` | Current user's generation count |
