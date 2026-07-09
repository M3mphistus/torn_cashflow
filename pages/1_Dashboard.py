import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import auth
import calculations
import db
import theme

st.set_page_config(page_title="Dashboard - Torn Cashflow", page_icon="\U0001F4B0", layout="wide")
theme.inject_theme()
db.init_db()
st.title("Dashboard")

player = auth.get_current_player()
if player is None:
    st.warning("Paste your Torn Full Access API key in Settings first.")
    st.stop()


def apply_chart_theme(fig):
    fig.update_layout(
        paper_bgcolor="#181209", plot_bgcolor="#181209",
        font=dict(color="#cdbf9c", family="Oswald"),
        colorway=["#c9a227", "#e4c258", "#8a6d1a", "#a33a2e", "#7f9a5b"],
        xaxis=dict(gridcolor="#2c2216", zerolinecolor="#3a2e1e"),
        yaxis=dict(gridcolor="#2c2216", zerolinecolor="#3a2e1e"),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig

all_snapshots = db.get_snapshots(player.player_id)

if len(all_snapshots) < 2:
    st.info("Need at least two synced snapshots to compute deltas. Go to **Sync** and sync at least twice.")
    st.stop()

min_ts = all_snapshots[0]["synced_at"]
max_ts = all_snapshots[-1]["synced_at"]
min_date = datetime.datetime.utcfromtimestamp(min_ts).date()
max_date = datetime.datetime.utcfromtimestamp(max_ts).date()

preset = st.radio("Time range", ["Last 7 days", "Last 30 days", "Last 90 days", "Custom", "All time"], horizontal=True)

if preset == "Custom":
    start_date, end_date = st.date_input(
        "Custom range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
else:
    end_date = max_date
    if preset == "Last 7 days":
        start_date = max(min_date, end_date - datetime.timedelta(days=7))
    elif preset == "Last 30 days":
        start_date = max(min_date, end_date - datetime.timedelta(days=30))
    elif preset == "Last 90 days":
        start_date = max(min_date, end_date - datetime.timedelta(days=90))
    else:
        start_date = min_date

start_ts = int(datetime.datetime.combine(start_date, datetime.time.min).timestamp())
end_ts = int(datetime.datetime.combine(end_date, datetime.time.max).timestamp())

snapshots = [s for s in all_snapshots if start_ts <= s["synced_at"] <= end_ts]

if len(snapshots) < 2:
    st.warning("Not enough snapshots in this range. Widen the time range.")
    st.stop()

cashflow_total = calculations.total_cashflow(snapshots)
cashflow_day = calculations.cashflow_per_day(snapshots)

col1, col2 = st.columns(2)
col1.metric("Total Cashflow", f"${cashflow_total:,}")
col2.metric("Cashflow / Day", f"${cashflow_day:,.0f}")

st.divider()
st.subheader("Cashflow by Category")

log_entries = db.get_log_entries(player.player_id, start_ts, end_ts)
breakdown = calculations.category_breakdown(log_entries, cashflow_total, db.list_categories(player.player_id))
if breakdown.empty:
    st.info("No categorized log data in this range yet.")
else:
    breakdown = breakdown.sort_values("amount")
    breakdown["sign"] = breakdown["amount"].apply(lambda v: "Positive" if v >= 0 else "Negative")
    fig = px.bar(
        breakdown, x="amount", y="category", orientation="h", color="sign",
        color_discrete_map={"Positive": "#c9a227", "Negative": "#a33a2e"},
    )
    fig.update_layout(showlegend=False, xaxis_title="Cashflow ($)", yaxis_title="")
    apply_chart_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Networth Breakdown")
st.caption("As of the latest sync in the selected time range. 'Trade' isn't exposed by the Torn API and is shown as n/a.")

latest_in_range = snapshots[-1]
nw_df = calculations.networth_breakdown(latest_in_range)
nw_df["formatted"] = nw_df["amount"].apply(lambda v: f"${v:,.0f}" if pd.notna(v) else "n/a")
st.dataframe(
    nw_df[["component", "formatted"]].rename(columns={"component": "Component", "formatted": "Amount"}),
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("Time Series")

daily = calculations.daily_series(snapshots)
if daily.empty:
    st.info("No daily data to chart yet.")
else:
    tab1, tab2 = st.tabs(["Cashflow / Day", "Networth"])
    with tab1:
        fig = px.bar(daily, x="to_date", y="cashflow_delta")
        apply_chart_theme(fig)
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        fig = px.line(daily, x="to_date", y="networth")
        apply_chart_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Raw Snapshots")

rows = [dict(s) for s in snapshots]
df = pd.DataFrame(rows)
if not df.empty:
    df["synced_at"] = pd.to_datetime(df["synced_at"], unit="s")
st.dataframe(df, use_container_width=True)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Export CSV", data=csv, file_name="torn_snapshots.csv", mime="text/csv")
