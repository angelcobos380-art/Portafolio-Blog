#!/bin/sh
set -e

# Si la base ya existía antes de Alembic (tiene tabla 'post' pero no 'alembic_version'),
# estampa la revisión base antes de ejecutar las migraciones nuevas.
python - <<'PY'
from sqlalchemy import inspect
from app.core.database import engine
from alembic.config import Config
from alembic import command

inspector = inspect(engine)
tables = set(inspector.get_table_names())
if "post" in tables and "alembic_version" not in tables:
    cfg = Config("alembic.ini")
    command.stamp(cfg, "0001_initial_schema")
PY

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
