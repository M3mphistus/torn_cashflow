import pandas as pd
import streamlit as st

import auth
import calculations
import db
import licensing
import theme

st.set_page_config(page_title="Categories - Torn Cashflow", page_icon="\U0001F3F7", layout="wide")
theme.inject_theme()
db.init_db()
licensing.render_heading_with_badge("#", "Categories")

player = auth.get_current_player()
if player is None:
    st.warning("Paste your Torn API key in Settings first.")
    st.stop()

if not licensing.require_premium("Categories", player):
    st.stop()

RESERVED_NAMES = {"Uncategorized", calculations.IGNORED_CATEGORY}

st.subheader("Manage Categories")
st.caption(
    "Categories used across Sync, Dashboard, and auto-categorization. "
    "A category can only be removed once no log entries use it."
)

categories = db.list_categories(player.player_id)
counts = db.get_category_counts(player.player_id)

with st.form("add_category_form", clear_on_submit=True):
    new_category_name = st.text_input("New category name")
    if st.form_submit_button("Add category"):
        name = new_category_name.strip()
        if not name:
            st.error("Enter a name.")
        elif name in RESERVED_NAMES:
            st.error(f"'{name}' is reserved and can't be used as a custom category.")
        elif db.add_category(player.player_id, name):
            st.success(f"Added '{name}'.")
            st.rerun()
        else:
            st.warning(f"'{name}' already exists.")

for category in categories:
    count = counts.get(category, 0)
    cols = st.columns([4, 2, 2])
    cols[0].write(category)
    cols[1].write(f"{count} entr{'y' if count == 1 else 'ies'}")
    with cols[2]:
        if st.button("Delete", key=f"delcat_{category}", disabled=count > 0):
            db.delete_category(player.player_id, category)
            st.rerun()

st.divider()


@st.fragment
def render_review_and_recategorize(player_id: int, categories: list[str]) -> None:
    st.subheader("Review & Recategorize")
    st.caption(
        "Every log title seen so far, grouped by its current category. Edit the Category column and click "
        "Apply to reassign all matching entries — the choice is also remembered for future syncs."
    )

    filter_options = ["All", *categories, "Uncategorized", calculations.IGNORED_CATEGORY]
    filter_choice = st.selectbox("Filter by category", filter_options)

    summary_rows = db.get_title_category_summary(player_id, None if filter_choice == "All" else filter_choice)
    if not summary_rows:
        st.info("No log entries yet.")
        return

    summary_df = pd.DataFrame([dict(r) for r in summary_rows]).rename(
        columns={"title": "Title", "app_category": "Category", "c": "Entries"}
    )
    all_category_options = [*categories, "Uncategorized", calculations.IGNORED_CATEGORY]

    edited_df = st.data_editor(
        summary_df,
        column_config={
            "Title": st.column_config.TextColumn(disabled=True),
            "Entries": st.column_config.NumberColumn(disabled=True),
            "Category": st.column_config.SelectboxColumn(options=all_category_options),
        },
        hide_index=True,
        use_container_width=True,
        key="category_review_editor",
    )

    if st.button("Apply changes", type="primary"):
        changes = 0
        for original, edited in zip(summary_df.itertuples(), edited_df.itertuples()):
            if original.Category != edited.Category:
                db.reassign_category(player_id, original.Title, original.Category, edited.Category)
                if original.Title:
                    db.upsert_category_rule(player_id, original.Title, edited.Category)
                changes += 1
        if changes:
            st.success(f"Reassigned {changes} title group(s).")
            st.rerun(scope="fragment")
        else:
            st.info("No changes to apply.")


render_review_and_recategorize(player.player_id, categories)
