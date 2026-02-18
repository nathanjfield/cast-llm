"""General Utility functions for cast-llm."""

from pathlib import Path

import toml


def get_project_root() -> Path:
    """Returns project root folder."""
    return Path(__file__).resolve().parent.parent.parent


def about() -> str:
    """Standard greeter function.

    Gives the documents something to cover regarding the project. The project
    information is extracted from pyproject.toml.

    Returns:
        Information about the project and key contacts.

    Example:
        >>> about()
        "Project Name: PROJECT_NAME
        Project Summary: PROJECT_SUMMARY
        Author Name: AUTHOR_NAME
        Author Contact: AUTHOR_CONTACT
    """
    parent_folder = Path(__file__).resolve().parent.parent.parent
    config_file = Path(parent_folder / "pyproject.toml")
    config = toml.load(config_file)
    return (
        f"Project Name: {config['project']['name']}\n"
        f"Project Description: {config['project']['description']}\n"
        f"Authors: {config['project']['authors']}\n"
    )
