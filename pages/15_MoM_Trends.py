import streamlit as st
import pandas as pd
from storage import list_months, load_month
from core import summary_kpis, fmt_dur, pct
from charts import trend_vol, trend_line, P

st.set_page_config(page_title="MoM Trends", page_icon="📈", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>📈 Month-over-Month Trends</h2>", unsafe_allow_html=True)

months = list_months()
if len(months) < 1:
    st.warning("Need at least one month of data."); st.stop()

# Build stats per month
rows = []
for m in months:
    dm = load_month(m)
    if dm is None or dm.empty: continue
    k = summary_kpis(dm)
    rows.append({
        "Month":        m,
        "Total":        k["total"],
        "Answered":     k["ans"],
        "Ans%":         k["ans_rate"],
        "Missed":       k["miss"],
        "Miss%":        pct(k["miss"],k["total"]),
        "Abandoned":    k["aban"],
        "Incoming":     k["inc"],
        "Outgoing":     k["out"],
        "Both Conn":    k["bc"],
        "BC%":          pct(k["bc"],k["total"]),
        "Avg Talk":     fmt_dur(k["avg_talk"]),
        "Avg Talk Inc": fmt_dur(k["avg_talk_inc"]),
        "Avg Talk Out": fmt_dur(k["avg_talk_out"]),
        "Avg Duration": fmt_dur(k["avg_dur"]),
        "Avg Hold":     fmt_dur(k["avg_hold"]),
        "Avg Wait":     fmt_dur(k["avg_wait"]),
        "Avg AASA":     fmt_dur(k["avg_aasa"]),
        "Talk>=10m":    k["t10"],
        "Talk>=15m":    k["t15"],
        "Talk>=20m":    k["t20"],
        "Anomalies":    k["anomalies"],
        "Anom%":        pct(k["anomalies"],k["total"]),
        # raw for charts
        "_avg_talk_s":  k["avg_talk"],
        "_ans_rate":    k["ans_rate"],
        "_anom_rate":   pct(k["anomalies"],k["total"]),
    })

if not rows:
    st.info("No month data available."); st.stop()

mom = pd.DataFrame(rows)

# ── Delta KPIs vs previous month ─────────────────────────────
if len(mom) >= 2:
    last = mom.iloc[-1]; prev = mom.iloc[-2]
    st.markdown("<div class='section-title'>Latest Month vs Previous</div>", unsafe_allow_html=True)
    c = st.columns(5)
    def delta(a, b, label, good_up=True):
        d = a - b
        sign = "+" if d >= 0 else ""
        color = "normal" if (d >= 0) == good_up else "inverse"
        return f"{sign}{d:.1f}" if isinstance(d, float) else f"{sign}{d:,}"

    c[0].metric("Total Calls",   f"{int(last['Total']):,}",   delta(last['Total'],prev['Total'],'')+f" vs {prev['Month']}")
    c[1].metric("Answer Rate",   f"{last['Ans%']}%",           f"{last['Ans%']-prev['Ans%']:+.1f}pp")
    c[2].metric("Missed",        f"{int(last['Missed']):,}",   f"{int(last['Missed']-prev['Missed']):+,}")
    c[3].metric("Avg Talk",      last["Avg Talk"])
    c[4].metric("Anomalies",     f"{int(last['Anomalies']):,}",f"{int(last['Anomalies']-prev['Anomalies']):+,}")

    st.divider()

# ── Trend charts ──────────────────────────────────────────────
ms = mom["Month"].tolist()

st.plotly_chart(
    trend_vol(ms, mom["Total"].tolist(), mom["Answered"].tolist(), mom["Missed"].tolist()),
    use_container_width=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.plotly_chart(trend_line(ms, mom["_ans_rate"].tolist(), "Answer Rate %", P["green"]), use_container_width=True)
with col2:
    talk_mins = [(s/60 if s else None) for s in mom["_avg_talk_s"].tolist()]
    st.plotly_chart(trend_line(ms, talk_mins, "Avg Talk Time (min)", P["amber"]), use_container_width=True)
with col3:
    st.plotly_chart(trend_line(ms, mom["_anom_rate"].tolist(), "Anomaly Rate %", P["red"]), use_container_width=True)

# ── Full summary table ────────────────────────────────────────
st.divider()
st.markdown("<div class='section-title'>Month-over-Month Summary Table</div>", unsafe_allow_html=True)
show_cols = [c for c in mom.columns if not c.startswith("_")]
st.dataframe(mom[show_cols], use_container_width=True, hide_index=True)
