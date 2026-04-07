"""Init for cast-llm."""

from .filter_reports import filter_reports_by_config
from .mongo_reports import (
    DEFAULT_COLLECTION,
    fetch_reports_date_range,
    get_castnet_db,
    group_by_equipment,
    json_friendly,
    reports_collection,
)
from .prompt_context import add_context_to_prompt
from .settings import CastLlmSettings, get_settings
from .utils import about, get_project_root

__all__ = [
    "DEFAULT_COLLECTION",
    "CastLlmSettings",
    "about",
    "add_context_to_prompt",
    "fetch_reports_date_range",
    "filter_reports_by_config",
    "get_castnet_db",
    "get_project_root",
    "get_settings",
    "group_by_equipment",
    "json_friendly",
    "reports_collection",
]
