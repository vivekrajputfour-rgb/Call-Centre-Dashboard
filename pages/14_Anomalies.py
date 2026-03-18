import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import detect_anomalies, anomaly_summary, fmt_dur, pct
from charts import anom_hbar

st.set_page_config(page_title="Anomalies", page_icon="🚨", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>🚨 Anomaly Detection</h2>", unsafe_allow_html=True)

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)

# Re-run anomaly detection if not already present
if "is_anomaly" not in df.columns:
    with st.spinner("Detecting anomalies…"):
        df = detect_anomalies(df)

anom = df[df["is_anomaly"]].copy()
n    = len(df)
total_anom = len(anom)

# ── KPIs ─────────────────────────────────────────────────────
c = st.columns(4)
c[0].metric("Total Anomalies",   f"{total_anom:,}",      f"{pct(total_anom,n)}% of all calls")
c[1].metric("Clean Records",     f"{n-total_anom:,}",    f"{pct(n-total_anom,n)}%")
c[2].metric("Agents Affected",   anom["agent_name"].nunique() if "agent_name" in anom.columns else "N/A")
c[3].metric("Total Calls",       f"{n:,}")

st.divider()

rc, anom_df = anomaly_summary(df)

if rc.empty:
    st.success("No anomalies detected.")
    st.stop()

# ── Charts ────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(anom_hbar(rc["Anomaly Type"].tolist(), rc["Count"].tolist()), use_container_width=True)
with col2:
    st.markdown("<div class='section-title'>Anomaly Type Summary</div>", unsafe_allow_html=True)
    st.dataframe(rc, use_container_width=True, hide_index=True)

st.divider()

# ── Anomaly Records — with filters + pagination ───────────────
st.markdown("<div class='section-title'>Anomalous Records Detail</div>", unsafe_allow_html=True)
st.caption(f"Total: **{total_anom:,} anomalous records** — use filters below to drill down, then download all filtered results")

# ── Filters row ───────────────────────────────────────────────
fc1, fc2, fc3, fc4 = st.columns(4)

# Anomaly type filter
all_types = sorted(set(
    r.strip()
    for reasons in anom_df["anomaly_reasons"].dropna()
    for r in reasons.split("|") if r.strip()
)) if "anomaly_reasons" in anom_df.columns else []
sel_type = fc1.selectbox("Filter by Anomaly Type", ["All"] + all_types)

# Agent filter
agents = ["All"] + sorted(anom_df["agent_name"].dropna().unique().tolist()) if "agent_name" in anom_df.columns else ["All"]
sel_agent = fc2.selectbox("Filter by Agent", agents)

# Direction filter
sel_dir = fc3.selectbox("Filter by Direction", ["All", "Incoming", "Outgoing"])

# Status filter
statuses = ["All"] + sorted(anom_df["status"].dropna().unique().tolist()) if "status" in anom_df.columns else ["All"]
sel_status = fc4.selectbox("Filter by Status", statuses)

# ── Apply filters ─────────────────────────────────────────────
filtered = anom_df.copy()

if sel_type != "All" and "anomaly_reasons" in filtered.columns:
    filtered = filtered[filtered["anomaly_reasons"].str.contains(sel_type, na=False)]

if sel_agent != "All" and "agent_name" in filtered.columns:
    filtered = filtered[filtered["agent_name"] == sel_agent]

if sel_dir != "All" and "direction" in filtered.columns:
    filtered = filtered[filtered["direction"] == sel_dir.lower()]

if sel_status != "All" and "status" in filtered.columns:
    filtered = filtered[filtered["status"] == sel_status.lower()]

st.info(f"Showing **{len(filtered):,}** records matching your filters (of {total_anom:,} total anomalies)")

# ── Format display columns ────────────────────────────────────
disp = filtered.copy()
if "talk_sec" in disp.columns:
    disp["talk_sec"] = disp["talk_sec"].apply(fmt_dur)
    disp = disp.rename(columns={"talk_sec": "Talk Time"})
if "dur_sec" in disp.columns:
    disp["dur_sec"] = disp["dur_sec"].apply(fmt_dur)
    disp = disp.rename(columns={"dur_sec": "Duration"})
if "aasa_sec" in disp.columns:
    disp["aasa_sec"] = disp["aasa_sec"].apply(fmt_dur)
    disp = disp.rename(columns={"aasa_sec": "AASA"})
if "dt" in disp.columns:
    disp["dt"] = disp["dt"].astype(str)

# ── Download button (ALL filtered records) ────────────────────
csv = disp.to_csv(index=False).encode("utf-8")
st.download_button(
    label=f"⬇️ Download all {len(filtered):,} filtered records as CSV",
    data=csv,
    file_name="anomalies_filtered.csv",
    mime="text/csv",
)

# ── Pagination ────────────────────────────────────────────────
PAGE_SIZE = 200
total_pages = max(1, (len(filtered) - 1) // PAGE_SIZE + 1)

if total_pages > 1:
    page = st.number_input(
        f"Page (1 to {total_pages}) — {PAGE_SIZE} records per page",
        min_value=1, max_value=total_pages, value=1, step=1
    )
else:
    page = 1

start = (page - 1) * PAGE_SIZE
end   = start + PAGE_SIZE
page_data = disp.iloc[start:end]

st.caption(f"Showing rows {start+1}–{min(end, len(filtered))} of {len(filtered):,}")
st.dataframe(page_data, use_container_width=True, hide_index=True)

if total_pages > 1:
    st.caption(f"Page {page} of {total_pages} — change page number above to see more records")
