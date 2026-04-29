"""
Bybit Learn Content Writer — Streamlit Web App
Generates publication-ready articles using Claude API with the Bybit editorial style guide.
"""

import os
import streamlit as st
from utils.image_utils import process_uploaded_file
from utils.claude_api import (
    build_user_message,
    generate_article,
    revise_article,
    test_connection,
    DEFAULT_MODEL,
    MODEL_OPTIONS,
    PROXY_BASE_URL,
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


def count_words(text: str) -> int:
    return len(text.split())


def reset_article():
    st.session_state.conversation_history = None
    st.session_state.article_text = ""
    st.session_state.article_generated = False
    st.session_state.screenshots_processed = []
    st.session_state.brief = {}
    st.session_state.revision_count = 0


# --- Sidebar ---
with st.sidebar:
    st.title("✍️ Content Writer")
    st.caption("Bybit Learn Article Generator")

    st.divider()

    api_key = st.text_input(
        "API Key",
        type="password",
        value=os.environ.get("ANTHROPIC_AUTH_TOKEN", os.environ.get("LITELLM_API_KEY", "")),
        help="LiteLLM proxy API key (starts with sk-).",
    )

    model_label = st.selectbox(
        "Model",
        options=list(MODEL_OPTIONS.keys()),
        index=0,
    )
    model = MODEL_OPTIONS[model_label]

    if st.button("Test connection", use_container_width=True):
        with st.spinner("Testing..."):
            result = test_connection(api_key)
        if result.startswith("Connected"):
            st.success(result)
        else:
            st.error(result)

    st.divider()

    if st.session_state.article_generated:
        st.markdown("### Current article")
        article_type_display = st.session_state.brief.get("article_type", "Unknown")
        st.markdown(f"**Type:** {article_type_display}")
        st.markdown(f"**Word count:** {count_words(st.session_state.article_text):,}")
        st.markdown(f"**Revisions:** {st.session_state.revision_count}")
        st.markdown(f"**Screenshots:** {len(st.session_state.screenshots_processed)}")

        st.divider()

        if st.button("🔄 New article", use_container_width=True):
            reset_article()
            st.rerun()

    with st.expander("Debug info"):
        st.text(f"Proxy: {PROXY_BASE_URL}")
        st.text(f"Key: {api_key[:8]}..." if api_key else "Key: (empty)")
        st.text(f"Model: {model}")


# --- Main content ---
if not api_key:
    st.warning("Please enter your API key in the sidebar to get started.")
    st.stop()

# === BRIEF INPUT FORM ===
if not st.session_state.article_generated:
    st.header("Create a new article")

    article_type = st.radio(
        "Article type",
        options=["Product Explainer", "Campaign Article"],
        horizontal=True,
        help="Product Explainer: tutorial/how-to with screenshots. Campaign: marketing campaign mechanics.",
    )

    type_key = "product_explainer" if article_type == "Product Explainer" else "campaign"

    default_wc = 1750 if type_key == "product_explainer" else 1000

    # Screenshot upload (outside form to avoid Streamlit file_uploader bug)
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

    screenshot_captions = {}
    if uploaded_files:
        st.markdown("**Screenshot captions** (optional — helps with placement)")
        for i, f in enumerate(uploaded_files):
            screenshot_captions[i] = st.text_input(
                f"Caption for {f.name}",
                key=f"caption_{i}",
                placeholder=f"e.g., Step {i+1}: Navigate to the trading page",
            )

    st.markdown("---")

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

        submitted = st.form_submit_button(
            "✨ Generate article",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if not name:
            st.error("Please enter a product/campaign name.")
            st.stop()
        if not description:
            st.error("Please enter a description or brief.")
            st.stop()
        if type_key == "product_explainer" and not uploaded_files:
            st.warning("No screenshots uploaded. The article will include generic screenshot placeholders.")

        processed_screenshots = []
        if uploaded_files:
            with st.spinner("Processing screenshots..."):
                for i, f in enumerate(uploaded_files):
                    processed = process_uploaded_file(f)
                    processed["caption"] = screenshot_captions.get(i, "")
                    processed_screenshots.append(processed)

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

        with st.status("Generating article...", expanded=True) as status:
            st.write("Sending brief to Claude...")
            try:
                article_text, history = generate_article(
                    brief=brief,
                    screenshots=processed_screenshots,
                    article_type=type_key,
                    model=model,
                    api_key=api_key,
                )
                st.session_state.article_text = article_text
                st.session_state.conversation_history = history
                st.session_state.article_generated = True
                status.update(label="Article generated!", state="complete")

            except Exception as e:
                status.update(label="Generation failed", state="error")
                st.error(f"Error generating article: {e}")
                st.stop()

        st.rerun()


# === ARTICLE PREVIEW + REVISION ===
else:
    st.header(st.session_state.brief.get("name", "Article"))

    st.markdown(st.session_state.article_text)

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📋 Copy markdown", use_container_width=True):
            st.code(st.session_state.article_text, language="markdown")

    with col2:
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
            type_key = (
                "product_explainer"
                if st.session_state.brief.get("article_type") == "Product Explainer"
                else "campaign"
            )

            with st.status("Revising article...", expanded=True) as status:
                st.write("Applying feedback...")
                try:
                    revised_text, history = revise_article(
                        revision_request=revision_input,
                        conversation_history=st.session_state.conversation_history,
                        article_type=type_key,
                        model=model,
                        api_key=api_key,
                    )
                    st.session_state.article_text = revised_text
                    st.session_state.conversation_history = history
                    st.session_state.revision_count += 1
                    status.update(label="Revision complete!", state="complete")

                except Exception as e:
                    status.update(label="Revision failed", state="error")
                    st.error(f"Error during revision: {e}")

            st.rerun()
