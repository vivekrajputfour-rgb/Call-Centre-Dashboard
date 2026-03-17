import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import dir_stats, fmt_dur, pct, THRESHOLDS
from charts import dir_grouped, ans_rate_bar

st.set_page_config(page_title="Direction Analysis", page_icon="↔️", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>↔️ Direction Analysis</h2>", unsafe_allow_html=True)

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)

inc   = df[df["direction"]=="incoming"]
out   = df[df["direction"]=="outgoing"]
ds_i  = dir_stats(inc)
ds_o  = dir_stats(out)
ds_a  = dir_stats(df)

# KPIs
c = st.columns(6)
c[0].metric("Incoming Total",   f"{ds_i['total']:,}", f"Ans: {ds_i['ans_rate']}%")
c[1].metric("Outgoing Total",   f"{ds_o['total']:,}", f"Ans: {ds_o['ans_rate']}%")
c[2].metric("Inc Avg Talk",     fmt_dur(ds_i["avg_talk"]))
c[3].metric("Out Avg Talk",     fmt_dur(ds_o["avg_talk"]))
c[4].metric("Inc Blank Hangup", f"{ds_i['blank_hu']:,}", f"{ds_i['blank_hu_rate']}%")
c[5].metric("Out Blank Hangup", f"{ds_o['blank_hu']:,}", f"{ds_o['blank_hu_rate']}%")

st.divider()
col1, col2 = st.columns(2)
with col1: st.plotly_chart(dir_grouped(ds_i, ds_o), use_container_width=True)
with col2: st.plotly_chart(ans_rate_bar(ds_i["ans_rate"], ds_o["ans_rate"]), use_container_width=True)

# Full table
st.markdown("<div class='section-title'>Full Breakdown Table</div>", unsafe_allow_html=True)
rows = []
for lbl, s in [("Incoming", ds_i), ("Outgoing", ds_o), ("Total", ds_a)]:
    row = {
        "Direction": lbl,
        "Total": s["total"], "Answered": s["ans"], "Answered %": f"{s['ans_rate']}%",
        "Missed": s["miss"], "Missed %": f"{s['miss_rate']}%",
        "Abandoned": s["aban"], "Abandoned %": f"{s['aban_rate']}%",
        "Avg Talk (both conn.)": fmt_dur(s["avg_talk"]),
        "Avg Wait Time": fmt_dur(s["avg_wait"]),
        "Avg Hold Time": fmt_dur(s["avg_hold"]),
        "Avg AASA": fmt_dur(s["avg_aasa"]),
        "Hangup Blank": s["blank_hu"], "Hangup Blank %": f"{s['blank_hu_rate']}%",
    }
    for t in THRESHOLDS:
        row[f"Talk>={t}m (both conn.)"] = s.get(f"t{t}", 0)
    rows.append(row)
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
