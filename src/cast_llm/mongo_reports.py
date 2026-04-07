"""Load shift reports from CastNet MongoDB for LLM pipelines."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from .settings import get_settings

_s0 = get_settings()
DEFAULT_MONGO_URI = _s0.mongodb_uri
DEFAULT_DB_NAME = _s0.mongodb_db
DEFAULT_COLLECTION = _s0.reports_collection

DEFAULT_PROJECTION: dict[str, int] = {
    "_id": 0,
    "report": 1,
    "die": 1,
    "equipment": 1,
    "shift": 1,
    "department": 1,
    "cavity": 1,
    "name": 1,
    "date_iso": 1,
    "createdAt": 1,
}


def get_castnet_db(
    uri: str | None = None,
    db_name: str | None = None,
) -> Database[Any]:
    """Return the CastNet database handle (pooled client)."""
    s = get_settings()
    resolved_uri = uri if uri is not None else s.mongodb_uri
    resolved_db = db_name if db_name is not None else s.mongodb_db
    client: MongoClient[Any] = MongoClient(resolved_uri)
    return client[resolved_db]


def reports_collection(
    db: Database[Any] | None = None,
    *,
    uri: str | None = None,
    db_name: str | None = None,
    collection_name: str | None = None,
) -> Collection[Any]:
    """Return the shift reports collection, opening a client if db is omitted."""
    s = get_settings()
    resolved_uri = uri if uri is not None else s.mongodb_uri
    resolved_db = db_name if db_name is not None else s.mongodb_db
    resolved_coll = collection_name if collection_name is not None else s.reports_collection
    database = db if db is not None else get_castnet_db(resolved_uri, resolved_db)
    return database[resolved_coll]


def json_friendly(value: Any) -> Any:
    """Recursively convert BSON types for JSON serialization to the LLM."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: json_friendly(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_friendly(v) for v in value]
    return value


def fetch_reports_date_range(
    start: datetime,
    end: datetime,
    *,
    db: Database[Any] | None = None,
    uri: str | None = None,
    db_name: str | None = None,
    collection_name: str | None = None,
    projection: dict[str, int] | None = None,
    date_field: str = "date_iso",
) -> list[dict[str, Any]]:
    """Fetch shift reports whose shift date falls in [start, end] (inclusive).

    Args:
        start: Range start (timezone-aware recommended; stored values are UTC).
        end: Range end (inclusive on the field; use end of day if needed).
        db: Optional existing PyMongo database. If None, opens a new client.
        uri: MongoDB connection string (default from ``CAST_LLM_MONGODB_URI``).
        db_name: Database name (default ``castnet`` / env).
        collection_name: Reports collection (default ``reports`` / env).
        projection: Fields to return; default matches castnet-database-context.md.
        date_field: Field used for filtering (default ``date_iso``).

    Returns:
        List of documents with BSON types converted for JSON encoding.
    """
    coll = reports_collection(
        db, uri=uri, db_name=db_name, collection_name=collection_name
    )
    proj = projection if projection is not None else DEFAULT_PROJECTION
    cursor = coll.find({date_field: {"$gte": start, "$lte": end}}, proj).sort(
        [(date_field, 1), ("equipment", 1), ("shift", 1)]
    )
    return [json_friendly(doc) for doc in cursor]


def group_by_equipment(reports: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group reports by ``equipment`` (e.g. \"DCM 1\"). Unknown/missing -> \"\"."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in reports:
        key = str(row.get("equipment") or "").strip()
        grouped[key].append(row)
    return dict(grouped)
