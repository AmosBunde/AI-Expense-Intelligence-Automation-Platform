"""Test configuration — SQLite compatibility for PostgreSQL-specific types."""
import importlib
import json
import sys
import types
from pathlib import Path

# ---------------------------------------------------------------------------
# Make shared_types importable without installing the package
# ---------------------------------------------------------------------------
_shared_src = Path(__file__).resolve().parent.parent.parent / "shared-types" / "src"

shared_types = types.ModuleType("shared_types")
shared_types.__path__ = [str(_shared_src)]
sys.modules["shared_types"] = shared_types

spec = importlib.util.spec_from_file_location(
    "shared_types.models", _shared_src / "models.py"
)
models = importlib.util.module_from_spec(spec)
sys.modules["shared_types.models"] = models
spec.loader.exec_module(models)

# ---------------------------------------------------------------------------
# Register SQLite compilation + bind/result rules for PostgreSQL-only types
# ---------------------------------------------------------------------------
from sqlalchemy import JSON, String, TypeDecorator, event
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles

# pgvector
try:
    from pgvector.sqlalchemy import Vector

    @compiles(Vector, "sqlite")
    def _compile_vector_sqlite(type_, compiler, **kw):
        return "TEXT"
except ImportError:
    pass


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return compiler.visit_JSON(JSON(), **kw)


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw):
    return "JSON"


# Patch ARRAY to JSON-serialize lists for SQLite
_orig_array_bind = ARRAY.bind_processor

def _array_bind_processor(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            return json.dumps(value, default=str)
        return process
    return _orig_array_bind(self, dialect)

ARRAY.bind_processor = _array_bind_processor

_orig_array_result = ARRAY.result_processor

def _array_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is None:
                return None
            if isinstance(value, str):
                return json.loads(value)
            return value
        return process
    return _orig_array_result(self, dialect, coltype)

ARRAY.result_processor = _array_result_processor
