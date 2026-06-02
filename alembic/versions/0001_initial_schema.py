"""Initial schema with user isolation

Revision ID: 0001
Revises:
Create Date: 2026-05-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # --- access_codes ---
    if "access_codes" not in tables:
        op.create_table(
            "access_codes",
            sa.Column("code", sa.String(), primary_key=True),
            sa.Column("label", sa.String(), nullable=False),
            sa.Column("generations_today", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_generation_date", sa.Date(), nullable=True),
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="0"),
        )

    # --- characters ---
    if "characters" not in tables:
        op.create_table(
            "characters",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("code", sa.String(), sa.ForeignKey("access_codes.code"), nullable=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("age", sa.String(), nullable=False),
            sa.Column("visual_description", sa.Text(), nullable=False),
            sa.Column("personality_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    else:
        char_cols = {c["name"] for c in inspector.get_columns("characters")}
        needs_id = "id" not in char_cols
        needs_code = "code" not in char_cols
        if needs_id or needs_code:
            # Clean up any orphaned temp table from a previous failed run
            if "characters_new" in tables:
                bind.execute(sa.text("DROP TABLE characters_new"))
            # SQLite can't ALTER to add a PK column — recreate the table
            bind.execute(sa.text("""
                CREATE TABLE characters_new (
                    id TEXT PRIMARY KEY,
                    code TEXT REFERENCES access_codes(code),
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    age TEXT NOT NULL,
                    visual_description TEXT NOT NULL,
                    personality_notes TEXT,
                    created_at DATETIME
                )
            """))
            id_expr = "'char_' || lower(hex(randomblob(4)))" if needs_id else "id"
            code_expr = "NULL" if needs_code else "code"
            bind.execute(sa.text(f"""
                INSERT INTO characters_new (id, code, name, role, age, visual_description, personality_notes, created_at)
                SELECT {id_expr}, {code_expr}, name, role, age, visual_description, personality_notes, created_at
                FROM characters
            """))
            bind.execute(sa.text("DROP TABLE characters"))
            bind.execute(sa.text("ALTER TABLE characters_new RENAME TO characters"))

    # --- memories ---
    if "memories" not in tables:
        op.create_table(
            "memories",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("code", sa.String(), sa.ForeignKey("access_codes.code"), nullable=True),
            sa.Column("raw_text", sa.Text(), nullable=False),
            sa.Column("setting", sa.String(), nullable=True),
            sa.Column("characters", sa.JSON(), nullable=True),
            sa.Column("themes", sa.JSON(), nullable=True),
            sa.Column("mood_arc", sa.String(), nullable=True),
            sa.Column("date_approximate", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    else:
        mem_cols = {c["name"] for c in inspector.get_columns("memories")}
        if "code" not in mem_cols:
            bind.execute(sa.text("ALTER TABLE memories ADD COLUMN code TEXT REFERENCES access_codes(code)"))

    # --- stories ---
    if "stories" not in tables:
        op.create_table(
            "stories",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("code", sa.String(), sa.ForeignKey("access_codes.code"), nullable=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("memory_id", sa.String(), sa.ForeignKey("memories.id"), nullable=False),
            sa.Column("tone", sa.String(), nullable=False),
            sa.Column("style_guide", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), server_default="planned"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    else:
        story_cols = {c["name"] for c in inspector.get_columns("stories")}
        if "code" not in story_cols:
            bind.execute(sa.text("ALTER TABLE stories ADD COLUMN code TEXT REFERENCES access_codes(code)"))

    # --- pages (no user isolation needed — owned via story) ---
    if "pages" not in tables:
        op.create_table(
            "pages",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("story_id", sa.String(), sa.ForeignKey("stories.id"), nullable=False),
            sa.Column("page_number", sa.Integer(), nullable=False),
            sa.Column("outline", sa.Text(), nullable=True),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("illustration_prompt", sa.Text(), nullable=True),
            sa.Column("illustration_arc_group", sa.String(), nullable=True),
            sa.Column("illustration_path", sa.String(), nullable=True),
            sa.Column("mood", sa.String(), nullable=True),
            sa.Column("arc_position", sa.String(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("pages")
    op.drop_table("stories")
    op.drop_table("memories")
    op.drop_table("characters")
    op.drop_table("access_codes")
