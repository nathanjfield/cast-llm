"""Functions for adding context to the system prompt."""

import re


def add_context_to_prompt(prompt: str, context: str) -> str:
    r"""Add context to the system prompt.

    This function takes a prompt string and a context string, and inserts the
    context into the prompt at the appropriate location. The context replaces
    the placeholder comment in the "## Context" section of the prompt.

    Args:
        prompt: The original system prompt string.
        context: A short description of the context/issue being focused on
            and any important information the model should know.

    Returns:
        The updated prompt string with the context section populated.

    Example:
        >>> prompt = "# System Prompt\\n\\nYou are an expert...\\n\\n## Context\\n\\n
        <!-- Context will be dynamically inserted here -->\\n\\n## Your Task"
        >>> context = "Focusing on extractor robot failures in Cell 3"
        >>> updated = add_context_to_prompt(prompt, context)
    """
    if not context or not context.strip():
        # If context is empty, remove the context section entirely
        # Remove the "## Context" section and its placeholder comment
        pattern = r"## Context\s*\n\s*<!--.*?-->\s*\n"
        updated_prompt = re.sub(pattern, "", prompt, flags=re.DOTALL)
        return updated_prompt.strip() + "\n"

    # Replace the placeholder comment with the actual context
    placeholder_pattern = r"(## Context\s*\n\s*)<!--.*?-->\s*(\n)"
    replacement = r"\1" + context.strip() + r"\n\2"

    updated_prompt = re.sub(placeholder_pattern, replacement, prompt, flags=re.DOTALL)

    # If the placeholder wasn't found, try to insert context before "## Your Task"
    if updated_prompt == prompt:
        task_section_marker = "## Your Task"
        if task_section_marker in prompt:
            parts = prompt.split(task_section_marker, 1)
            intro = parts[0].rstrip()
            rest = parts[1] if len(parts) > 1 else ""
            context_section = f"\n\n## Context\n\n{context.strip()}\n\n"
            updated_prompt = intro + context_section + task_section_marker + rest
        else:
            # If "Your Task" section not found, append context at the end
            context_section = f"\n\n## Context\n\n{context.strip()}\n\n"
            updated_prompt = prompt.rstrip() + context_section

    return updated_prompt
