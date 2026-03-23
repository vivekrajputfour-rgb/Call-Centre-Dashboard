import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import summary_kpis, build_slot_arrays, fmt_dur, fmt_hm, pct
from charts import status_donut, slot_two_line, dow_bar, monthly_bar, heatmap_hour_dow

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>📊 Overview</h2>", unsafe_allow_html=True)

months = list_months()
if not months:
    st.warning("No data loaded. Go to **📤 Upload Data** first."); st.stop()

sel = st.multiselect("Select months", months, default=months)
if not sel: st.info("Select at least one month."); st.stop()

df = load_selected(sel)

k  = summary_kpis(df)

# ── KPI Row 1: Volume ─────────────────────────────────────────
st.markdown("<div class='section-title'>Volume</div>", unsafe_allow_html=True)
c = st.columns(8)
c[0].metric("Total Calls",    f"{k['total']:,}")
c[1].metric("Answer Rate",    f"{k['ans_rate']}%")
c[2].metric("Answered",       f"{k['ans']:,}")
c[3].metric("Missed",         f"{k['miss']:,}", f"{pct(k['miss'],k['total'])}%")
c[4].metric("Abandoned",      f"{k['aban']:,}", f"{pct(k['aban'],k['total'])}%")
c[5].metric("Outgoing",       f"{k['out']:,}")
c[6].metric("Incoming",       f"{k['inc']:,}")
c[7].metric("Both Connected", f"{k['bc']:,}", f"{pct(k['bc'],k['total'])}%")

# ── KPI Row 2: Talk time ──────────────────────────────────────
st.markdown("<div class='section-title' style='margin-top:12px'>Talk Time (Both Connected)</div>", unsafe_allow_html=True)
c2 = st.columns(7)
c2[0].metric("Avg Talk — All",      fmt_dur(k["avg_talk"]))
c2[1].metric("Avg Talk — Incoming", fmt_dur(k["avg_talk_inc"]))
c2[2].metric("Avg Talk — Outgoing", fmt_dur(k["avg_talk_out"]))
c2[3].metric("Avg Duration",        fmt_dur(k["avg_dur"]))
c2[4].metric("Avg Hold",            fmt_dur(k["avg_hold"]))
c2[5].metric("Avg Wait (Queue)",    fmt_dur(k["avg_wait"]))
c2[6].metric("Avg AASA",            fmt_dur(k["avg_aasa"]))

# ── KPI Row 3: Long calls + quality ──────────────────────────
st.markdown("<div class='section-title' style='margin-top:12px'>Long Calls & Quality</div>", unsafe_allow_html=True)
c3 = st.columns(5)
c3[0].metric("Talk ≥ 10 min",  f"{k['t10']:,}", "both connected")
c3[1].metric("Talk ≥ 15 min",  f"{k['t15']:,}", "both connected")
c3[2].metric("Talk ≥ 20 min",  f"{k['t20']:,}", "both connected")
c3[3].metric("Follow-Up Calls",f"{k['follow_up']:,}")
c3[4].metric("Anomalies",      f"{k['anomalies']:,}", f"{pct(k['anomalies'],k['total'])}%")

st.divider()

# ── Charts ────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(status_donut(df["status"].value_counts().to_dict()), use_container_width=True)
with col2:
    si, so, _, _ = build_slot_arrays(df)
    st.plotly_chart(slot_two_line(si, so), use_container_width=True)

col3, col4 = st.columns(2)
with col3:
    st.plotly_chart(dow_bar(df["dow"].dropna().value_counts().to_dict()), use_container_width=True)
with col4:
    st.plotly_chart(monthly_bar(df["month"].dropna().value_counts().to_dict()), use_container_width=True)

# ── Heatmap ───────────────────────────────────────────────────
st.plotly_chart(heatmap_hour_dow(df), use_container_width=True)

# ── Month summary table ───────────────────────────────────────
st.markdown("<div class='section-title' style='margin-top:4px'>Month Summary</div>", unsafe_allow_html=True)
rows = []
for m in sorted(sel):
    dm = df[df["month"] == m]
    if dm.empty: continue
    kk = summary_kpis(dm)
    rows.append({
        "Month": m, "Total": f"{kk['total']:,}",
        "Answered": f"{kk['ans']:,}", "Ans%": f"{kk['ans_rate']}%",
        "Missed": f"{kk['miss']:,}", "Abandoned": f"{kk['aban']:,}",
        "Incoming": f"{kk['inc']:,}", "Outgoing": f"{kk['out']:,}",
        "Both Conn": f"{kk['bc']:,}",
        "Avg Talk": fmt_dur(kk["avg_talk"]),
        "Avg Talk Inc": fmt_dur(kk["avg_talk_inc"]),
        "Avg Talk Out": fmt_dur(kk["avg_talk_out"]),
        "Avg Duration": fmt_dur(kk["avg_dur"]),
        "Avg Hold": fmt_dur(kk["avg_hold"]),
        "Avg Wait": fmt_dur(kk["avg_wait"]),
        "Avg AASA": fmt_dur(kk["avg_aasa"]),
        "Talk≥10m": kk["t10"], "Talk≥15m": kk["t15"], "Talk≥20m": kk["t20"],
        "Follow-Up": kk["follow_up"], "Anomalies": kk["anomalies"],
    })
if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
