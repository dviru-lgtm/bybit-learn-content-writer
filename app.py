"""
Bybit Learn Content Writer — Streamlit Web App
Generates publication-ready articles using Claude API with the Bybit editorial style guide.
"""

import os
import streamlit as st
from utils.image_utils import process_uploaded_file
from utils.claude_api import (
    build_user_message,
    stream_generate_article,
    stream_revise_article,
    DEFAULT_MODEL,
    MODEL_OPTIONS,
    PROXY_BASE_URL as PROXY_BASE_URL,
)

# --- Page config ---
st.set_page_config(
    page_title="Bybit Learn Content Writer",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Session state init ---
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = None
if "article_text" not in st.session_state:
    st.session_state.article_text = ""
if "article_generated" not in st.session_state:
    st.session_state.article_generated = False
if "screenshots_processed" not in st.session_state:
    st.session_state.screenshots_processed = []
if "brief" not in st.session_state:
    st.session_state.brief = {}
if "revision_count" not in st.session_state:
    st.session_state.revision_count = 0
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False


def count_words(text: str) -> int:
    return len(text.split())


def reset_article():
    st.session_state.conversation_history = None
    st.session_state.article_text = ""
    st.session_state.article_generated = False
    st.session_state.screenshots_processed = []
    st.session_state.brief = {}
    st.session_state.revision_count = 0
    st.session_state.is_generating = False


# --- Sidebar ---
with st.sidebar:
    st.title("✍️ Content Writer")
    st.caption("Bybit Learn Article Generator")

    st.divider()

    # Proxy API key
    api_key = st.text_input(
        "API Key",
        type="password",
        value=os.environ.get("ANTHROPIC_AUTH_TOKEN", os.environ.get("LITELLM_API_KEY", "")),
        help="LiteLLM proxy API key (starts with sk-).",
    )

    # Model selection
    model_label = st.selectbox(
        "Model",
        options=list(MODEL_OPTIONS.keys()),
        index=0,
    )
    model = MODEL_OPTIONS[model_label]

    st.divider()

    # Session info
    if st.session_state.article_generated:
        st.markdown("### Current article")
        article_type = st.session_state.brief.get("article_type", "Unknown")
        st.markdown(f"**Type:** {article_type}")
        st.markdown(f"**Word count:** {count_words(st.session_state.article_text):,}")
        st.markdown(f"**Revisions:** {st.session_state.revision_count}")
        st.markdown(f"**Screenshots:** {len(st.session_state.screenshots_processed)}")

        st.divider()

        if st.button("🔄 New article", use_container_width=True):
            reset_article()
            st.rerun()


# --- Main content ---
if not api_key:
    st.warning("Please enter your API key in the sidebar to get started.")
    st.stop()

# === BRIEF INPUT FORM ===
if not st.session_state.article_generated:
    st.header("Create a new article")

    # Article type
    article_type = st.radio(
        "Article type",
        options=["Product Explainer", "Campaign Article"],
        horizontal=True,
        help="Product Explainer: tutorial/how-to with screenshots. Campaign: marketing campaign mechanics.",
    )

    type_key = "product_explainer" if article_type == "Product Explainer" else "campaign"

    # Default word counts
    default_wc = 1750 if type_key == "product_explainer" else 1000
    wc_range = (1500, 2000) if type_key == "product_explainer" else (800, 1200)

    with st.form("brief_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "Product/Campaign name *",
                placeholder="e.g., Bybit Copy Trading, WSOT 2026",
            )

            audience = st.selectbox(
                "Target audience",
                options=["New users", "Early traders", "Experienced traders", "All users"],
                index=3,
            )

            cta = st.text_input(
                "CTA / Primary action",
                placeholder="e.g., Start copy trading on Bybit",
            )

            keyword = st.text_input(
                "SEO target keyword (optional)",
                placeholder="e.g., how to copy trade on Bybit",
            )

        with col2:
            description = st.text_area(
                "Brief / Description *",
                placeholder="Describe what the article should cover. Paste the full brief or summarize in 2-3 sentences.",
                height=120,
            )

            key_points = st.text_area(
                "Key points to cover",
                placeholder="- Point 1\n- Point 2\n- Point 3",
                height=120,
            )

        word_count = st.slider(
            "Target word count",
            min_value=500,
            max_value=3000,
            value=default_wc,
            step=100,
        )

        # Screenshot upload
        st.markdown("---")
        screenshots_label = (
            "Upload screenshots *" if type_key == "product_explainer"
            else "Upload campaign creatives (optional)"
        )
        uploaded_files = st.file_uploader(
            screenshots_label,
            type=["png", "jpg", "jpeg", "gif", "webp"],
            accept_multiple_files=True,
            help="Drag and drop or browse. For Product Explainers, upload screenshots in the order they appear in the tutorial.",
        )

        # Screenshot captions
        screenshot_captions = {}
        if uploaded_files:
            st.markdown("**Screenshot captions** (optional — helps with placement)")
            for i, f in enumerate(uploaded_files):
                screenshot_captions[i] = st.text_input(
                    f"Caption for {f.name}",
                    key=f"caption_{i}",
                    placeholder=f"e.g., Step {i+1}: Navigate to the trading page",
                )

        submitted = st.form_submit_button(
            "✨ Generate article",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        # Validate required fields
        if not name:
            st.error("Please enter a product/campaign name.")
            st.stop()
        if not description:
            st.error("Please enter a description or brief.")
            st.stop()
        if type_key == "product_explainer" and not uploaded_files:
            st.warning("No screenshots uploaded. The article will include generic screenshot placeholders.")

        # Process screenshots
        processed_screenshots = []
        if uploaded_files:
            with st.spinner("Processing screenshots..."):
                for i, f in enumerate(uploaded_files):
                    processed = process_uploaded_file(f)
                    processed["caption"] = screenshot_captions.get(i, "")
                    processed_screenshots.append(processed)

        # Build brief
        brief = {
            "article_type": article_type,
            "name": name,
            "description": description,
            "audience": audience,
            "key_points": key_points,
            "cta": cta,
            "keyword": keyword,
            "word_count": word_count,
        }

        st.session_state.brief = brief
        st.session_state.screenshots_processed = processed_screenshots

        # Generate article with streaming
        with st.spinner(""):
            article_placeholder = st.empty()
            full_text = ""

            try:
                for chunk, is_done, current_text, history in stream_generate_article(
                    brief=brief,
                    screenshots=processed_screenshots,
                    article_type=type_key,
                    model=model,
                    api_key=api_key,
                ):
                    if not is_done:
                        full_text = current_text
                        article_placeholder.markdown(full_text)
                    else:
                        st.session_state.article_text = current_text
                        st.session_state.conversation_history = history
                        st.session_state.article_generated = True

            except Exception as e:
                if full_text:
                    st.warning(f"Connection error: {e}\n\nShowing partial output — you can revise or retry.")
                    st.session_state.article_text = full_text
                    st.session_state.conversation_history = [
                        {"role": "user", "content": build_user_message(brief, processed_screenshots)},
                        {"role": "assistant", "content": full_text},
                    ]
                    st.session_state.article_generated = True
                else:
                    st.error(f"Error generating article: {e}")
                    st.stop()

        st.rerun()


# === ARTICLE PREVIEW + REVISION ===
else:
    st.header(st.session_state.brief.get("name", "Article"))

    # Article display
    st.markdown(st.session_state.article_text)

    st.divider()

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        # Copy to clipboard (via st.code workaround)
        if st.button("📋 Copy markdown", use_container_width=True):
            st.code(st.session_state.article_text, language="markdown")

    with col2:
        # Download as .md file
        article_name = st.session_state.brief.get("name", "article").lower().replace(" ", "-")
        st.download_button(
            "⬇️ Download .md",
            data=st.session_state.article_text,
            file_name=f"{article_name}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with col3:
        if st.button("🔄 Start over", use_container_width=True):
            reset_article()
            st.rerun()

    # Revision interface
    st.divider()
    st.subheader("Revisions")

    revision_input = st.text_area(
        "Feedback / revision request",
        placeholder="e.g., Make the intro more engaging, add more detail to Step 3, the prize pool is 50,000 USDT not 5,000",
        height=100,
        key="revision_input",
    )

    if st.button("✏️ Revise article", use_container_width=True, type="primary"):
        if not revision_input:
            st.warning("Please enter your revision request.")
        else:
            article_placeholder = st.empty()
            full_text = ""

            type_key = (
                "product_explainer"
                if st.session_state.brief.get("article_type") == "Product Explainer"
                else "campaign"
            )

            try:
                for chunk, is_done, current_text, history in stream_revise_article(
                    revision_request=revision_input,
                    conversation_history=st.session_state.conversation_history,
                    article_type=type_key,
                    model=model,
                    api_key=api_key,
                ):
                    if not is_done:
                        full_text = current_text
                        article_placeholder.markdown(full_text)
                    else:
                        st.session_state.article_text = current_text
                        st.session_state.conversation_history = history
                        st.session_state.revision_count += 1

            except Exception as e:
                st.error(f"Error during revision: {e}")

            st.rerun()
