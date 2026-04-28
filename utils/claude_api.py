"""
Anthropic SDK wrapper (Bedrock via LiteLLM proxy) with prompt caching and vision support.
Handles article generation, revision, and compliance checking.
"""

import os
import time
import httpx
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import anthropic

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"

try:
    import streamlit as st
    PROXY_BASE_URL = st.secrets.get("PROXY_BASE_URL", "")
except Exception:
    PROXY_BASE_URL = ""
if not PROXY_BASE_URL:
    PROXY_BASE_URL = os.environ.get("CONTENT_WRITER_BASE_URL", "https://litellm-de.yijin.io")
DEFAULT_MODEL = "claude-sonnet-4-6"
MODEL_OPTIONS = {
    "Sonnet 4.6 (faster, cheaper)": "claude-sonnet-4-6",
    "Opus 4.6 (highest quality)": "claude-opus-4-6",
}
MAX_TOKENS = 8192
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # seconds


def _make_client(api_key: str = "") -> anthropic.Anthropic:
    return anthropic.Anthropic(
        base_url=PROXY_BASE_URL,
        api_key=api_key or "unused",
        timeout=httpx.Timeout(600.0, connect=30.0),
        max_retries=2,
    )


def load_prompt_file(filename: str) -> str:
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return ""


def load_example_file(filename: str) -> str:
    filepath = EXAMPLES_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return ""


def build_system_prompt(article_type: str) -> List[dict]:
    """
    Build the system prompt with prompt caching.
    Returns a list of content blocks for the system parameter.
    The style guide block is marked for caching since it's large and static.
    """
    core_instructions = load_prompt_file("system_prompt.md")
    style_guide = load_prompt_file("style_guide.md")
    writing_patterns = load_prompt_file("writing_patterns.md")
    compliance = load_prompt_file("compliance_checklist.md")

    if article_type == "product_explainer":
        template = load_prompt_file("product_explainer_template.md")
        example = load_example_file("product_explainer_example.md")
    else:
        template = load_prompt_file("campaign_article_template.md")
        example = load_example_file("campaign_article_example.md")

    cached_block = (
        f"{core_instructions}\n\n"
        f"# STYLE GUIDE\n\n{style_guide}\n\n"
        f"# WRITING PATTERNS FROM EXISTING ARTICLES\n\n{writing_patterns}\n\n"
        f"# COMPLIANCE CHECKLIST\n\n{compliance}"
    )

    type_block = (
        f"# ARTICLE TEMPLATE\n\n{template}\n\n"
        f"# EXAMPLE ARTICLE\n\n{example}"
    )

    return [
        {
            "type": "text",
            "text": cached_block,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": type_block,
        },
    ]


def build_user_message(brief: dict, screenshots: List[dict]) -> List[dict]:
    """
    Build the user message content with text brief and optional screenshots.
    """
    content = []

    for i, screenshot in enumerate(screenshots, 1):
        if screenshot.get("caption"):
            content.append({
                "type": "text",
                "text": f"Screenshot {i}: {screenshot['caption']}",
            })

        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": screenshot["media_type"],
                "data": screenshot["data"],
            },
        })

    brief_parts = []
    brief_parts.append("## Article Brief\n")
    brief_parts.append(f"**Article Type:** {brief.get('article_type', 'Product Explainer')}")
    brief_parts.append(f"**Product/Campaign Name:** {brief.get('name', 'TBD')}")
    brief_parts.append(f"**Description:** {brief.get('description', 'TBD')}")
    brief_parts.append(f"**Target Audience:** {brief.get('audience', 'All')}")
    brief_parts.append(f"**Key Points to Cover:**\n{brief.get('key_points', 'TBD')}")
    brief_parts.append(f"**CTA / Primary Action:** {brief.get('cta', 'TBD')}")

    if brief.get("keyword"):
        brief_parts.append(f"**SEO Target Keyword:** {brief['keyword']}")

    brief_parts.append(f"**Target Word Count:** {brief.get('word_count', 1500)}")

    if screenshots:
        brief_parts.append(f"\n**Screenshots provided:** {len(screenshots)}")
        brief_parts.append(
            "Please analyze each screenshot and place [Screenshot: description] "
            "placeholders at the appropriate points in the article."
        )

    brief_parts.append(
        "\nPlease generate the full article following the template structure, "
        "style guide rules, and compliance checklist. "
        "After the article, provide a brief compliance summary."
    )

    content.append({
        "type": "text",
        "text": "\n".join(brief_parts),
    })

    return content


def generate_article(
    brief: dict,
    screenshots: List[dict],
    article_type: str,
    conversation_history: Optional[List[dict]] = None,
    model: str = DEFAULT_MODEL,
    api_key: str = "",
) -> Tuple[str, List[dict]]:
    client = _make_client(api_key)
    system = build_system_prompt(article_type)

    if conversation_history is None:
        messages = [
            {"role": "user", "content": build_user_message(brief, screenshots)},
        ]
    else:
        messages = conversation_history

    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=messages,
    )

    assistant_text = ""
    for block in response.content:
        if block.type == "text":
            assistant_text += block.text

    updated_history = messages + [
        {"role": "assistant", "content": assistant_text},
    ]

    return assistant_text, updated_history


def revise_article(
    revision_request: str,
    conversation_history: List[dict],
    article_type: str,
    model: str = DEFAULT_MODEL,
    api_key: str = "",
) -> Tuple[str, List[dict]]:
    messages = conversation_history + [
        {
            "role": "user",
            "content": (
                f"{revision_request}\n\n"
                "Please revise the article based on this feedback. "
                "Only change the affected sections. "
                "Re-run the compliance checklist and provide an updated summary."
            ),
        },
    ]

    client = _make_client(api_key)
    system = build_system_prompt(article_type)

    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=messages,
    )

    assistant_text = ""
    for block in response.content:
        if block.type == "text":
            assistant_text += block.text

    updated_history = messages + [
        {"role": "assistant", "content": assistant_text},
    ]

    return assistant_text, updated_history


def stream_generate_article(
    brief: dict,
    screenshots: List[dict],
    article_type: str,
    conversation_history: Optional[List[dict]] = None,
    model: str = DEFAULT_MODEL,
    api_key: str = "",
):
    """
    Stream article generation with retry on connection drops.
    Yields (chunk, is_done, full_text, updated_history) tuples.
    """
    system = build_system_prompt(article_type)

    if conversation_history is None:
        messages = [
            {"role": "user", "content": build_user_message(brief, screenshots)},
        ]
    else:
        messages = conversation_history

    full_text = ""
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            client = _make_client(api_key)

            if attempt > 0 and full_text:
                retry_messages = messages + [
                    {"role": "assistant", "content": full_text},
                    {"role": "user", "content": "Your previous response was cut off. Please continue exactly where you left off. Do not repeat what you already wrote."},
                ]
                current_messages = retry_messages
            else:
                current_messages = messages

            with client.messages.stream(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=current_messages,
            ) as stream:
                for text in stream.text_stream:
                    full_text += text
                    yield text, False, full_text, None

            updated_history = messages + [
                {"role": "assistant", "content": full_text},
            ]
            yield "", True, full_text, updated_history
            return

        except (
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
        ) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                yield f"\n\n---\n*Connection interrupted. Retrying in {delay}s (attempt {attempt + 2}/{MAX_RETRIES})...*\n\n", False, full_text, None
                time.sleep(delay)
            else:
                # Final attempt failed — return what we have
                if full_text:
                    full_text += f"\n\n---\n*Generation was interrupted after {MAX_RETRIES} attempts. The article above may be incomplete.*"
                    updated_history = messages + [
                        {"role": "assistant", "content": full_text},
                    ]
                    yield "", True, full_text, updated_history
                    return
                else:
                    raise last_error


def stream_revise_article(
    revision_request: str,
    conversation_history: List[dict],
    article_type: str,
    model: str = DEFAULT_MODEL,
    api_key: str = "",
):
    """
    Stream article revision with retry on connection drops.
    Yields (chunk, is_done, full_text, updated_history) tuples.
    """
    messages = conversation_history + [
        {
            "role": "user",
            "content": (
                f"{revision_request}\n\n"
                "Please revise the article based on this feedback. "
                "Only change the affected sections. "
                "Re-run the compliance checklist and provide an updated summary."
            ),
        },
    ]

    system = build_system_prompt(article_type)

    full_text = ""
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            client = _make_client(api_key)

            if attempt > 0 and full_text:
                retry_messages = messages + [
                    {"role": "assistant", "content": full_text},
                    {"role": "user", "content": "Your previous response was cut off. Please continue exactly where you left off."},
                ]
                current_messages = retry_messages
            else:
                current_messages = messages

            with client.messages.stream(
                model=model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=current_messages,
            ) as stream:
                for text in stream.text_stream:
                    full_text += text
                    yield text, False, full_text, None

            updated_history = messages + [
                {"role": "assistant", "content": full_text},
            ]
            yield "", True, full_text, updated_history
            return

        except (
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
        ) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                yield f"\n\n---\n*Connection interrupted. Retrying in {delay}s (attempt {attempt + 2}/{MAX_RETRIES})...*\n\n", False, full_text, None
                time.sleep(delay)
            else:
                if full_text:
                    full_text += f"\n\n---\n*Revision was interrupted after {MAX_RETRIES} attempts. The output above may be incomplete.*"
                    updated_history = messages + [
                        {"role": "assistant", "content": full_text},
                    ]
                    yield "", True, full_text, updated_history
                    return
                else:
                    raise last_error
