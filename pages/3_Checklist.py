import time

import streamlit as st

import auth
import calculations
import db
import licensing
import theme

st.set_page_config(page_title="Checklist - Torn Cashflow", page_icon="\U00002705", layout="wide")
theme.inject_theme()
db.init_db()
st.title("Checklist")

player = auth.get_current_player()
if player is None:
    st.warning("Paste your Torn Full Access API key in Settings first.")
    st.stop()

war_mode_active = db.get_setting(player.player_id, "war_mode_active", "0") == "1"
war_mode_started_at = db.get_setting(player.player_id, "war_mode_started_at")
war_mode_started_at = int(war_mode_started_at) if war_mode_started_at else None

now_ts = int(time.time())

tasks = db.list_checklist_tasks(player.player_id)
premium_status = licensing.get_premium_status(player)
if premium_status.is_premium:
    for task in tasks:
        if calculations.task_needs_reset(task, now_ts, war_mode_started_at):
            db.reset_task_cycle(player.player_id, task["id"])
    tasks = db.list_checklist_tasks(player.player_id)
else:
    st.caption(
        "Recurring tasks reset automatically with Premium. On the free tier, check tasks off and "
        "un-check them yourself when a new cycle starts."
    )

st.subheader("Add a task")
with st.form("new_task_form", clear_on_submit=True):
    title = st.text_input("Title")
    description = st.text_area("Description (optional)")
    repeat_type = st.selectbox(
        "Repeat type",
        list(calculations.REPEAT_TYPE_LABELS.keys()),
        format_func=lambda key: calculations.REPEAT_TYPE_LABELS[key],
    )
    interval_days = None
    if repeat_type == "every_x_days":
        interval_days = st.number_input("Every X days", min_value=1, value=2, step=1)
    submitted = st.form_submit_button("Add task")
    if submitted:
        if not title.strip():
            st.error("Title is required.")
        else:
            db.create_checklist_task(player.player_id, title.strip(), description.strip(), repeat_type, interval_days)
            st.rerun()

st.divider()

visible_tasks = [t for t in tasks if t["repeat_type"] != "war_day" or war_mode_active]
open_tasks = [t for t in visible_tasks if not t["is_done_current_cycle"]]
done_tasks = [t for t in visible_tasks if t["is_done_current_cycle"]]

st.subheader("Open Tasks")
if not open_tasks:
    st.info("Nothing open right now.")
else:
    grouped: dict[str, list] = {}
    for task in open_tasks:
        grouped.setdefault(task["repeat_type"], []).append(task)

    for repeat_type, group in grouped.items():
        st.markdown(f"**{calculations.REPEAT_TYPE_LABELS[repeat_type]}**")
        for task in group:
            with st.container(border=True):
                cols = st.columns([1, 5, 2, 2])
                with cols[0]:
                    if st.checkbox("Done", key=f"done_{task['id']}"):
                        db.set_task_done(player.player_id, task["id"], True, int(time.time()))
                        st.rerun()
                with cols[1]:
                    st.write(f"**{task['title']}**")
                    if task["description"]:
                        st.caption(task["description"])
                with cols[2]:
                    if st.button("Edit", key=f"edit_{task['id']}"):
                        st.session_state[f"editing_{task['id']}"] = True
                with cols[3]:
                    if st.button("Delete", key=f"delete_{task['id']}"):
                        db.delete_checklist_task(player.player_id, task["id"])
                        st.rerun()

                if st.session_state.get(f"editing_{task['id']}"):
                    with st.form(f"edit_form_{task['id']}"):
                        new_title = st.text_input("Title", value=task["title"])
                        new_description = st.text_area("Description", value=task["description"] or "")
                        new_repeat_type = st.selectbox(
                            "Repeat type",
                            list(calculations.REPEAT_TYPE_LABELS.keys()),
                            index=list(calculations.REPEAT_TYPE_LABELS.keys()).index(task["repeat_type"]),
                            format_func=lambda key: calculations.REPEAT_TYPE_LABELS[key],
                            key=f"edit_repeat_{task['id']}",
                        )
                        new_interval = task["repeat_interval_days"] or 2
                        if new_repeat_type == "every_x_days":
                            new_interval = st.number_input(
                                "Every X days", min_value=1, value=int(new_interval), step=1, key=f"edit_interval_{task['id']}"
                            )
                        save = st.form_submit_button("Save changes")
                        if save:
                            db.update_checklist_task(
                                player.player_id,
                                task["id"],
                                new_title.strip(),
                                new_description.strip(),
                                new_repeat_type,
                                new_interval if new_repeat_type == "every_x_days" else None,
                            )
                            st.session_state[f"editing_{task['id']}"] = False
                            st.rerun()

st.divider()
st.subheader("Completed")
if not done_tasks:
    st.caption("Nothing completed for the current cycle.")
else:
    with st.expander(f"{len(done_tasks)} completed task(s)"):
        for task in done_tasks:
            cols = st.columns([1, 6])
            with cols[0]:
                if st.checkbox("Done", value=True, key=f"undo_{task['id']}"):
                    pass
                else:
                    db.set_task_done(player.player_id, task["id"], False, task["last_completed_at"])
                    st.rerun()
            with cols[1]:
                st.markdown(f"~~{task['title']}~~")
