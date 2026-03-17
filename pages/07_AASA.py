import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import aasa_analysis, fmt_dur, pct
from charts import aasa_combo, aasa_agent_bar

st.set_page_config(page_title="AASA Analysis", page_icon="⏱️", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>⏱️ AASA — Agent Answer Speed</h2>", unsafe_allow_html=True)

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)

vals = df["aasa_sec"].dropna()
if vals.empty: st.info("No AASA data found."); st.stop()

n = len(df)
c = st.columns(3)
c[0].metric("Avg AASA",      fmt_dur(float(vals.mean())))
c[1].metric("< 10s Answer",  int((vals<10).sum()), f"{pct(int((vals<10).sum()),n)}%")
c[2].metric("> 1 min AASA",  int((vals>=60).sum()), "Slow")

st.divider()
bkt, agt = aasa_analysis(df)

col1, col2 = st.columns(2)
with col1:
    counts   = bkt["Count"].tolist()
    cum_pct  = bkt["Cumulative %"].tolist()
    labels   = bkt["AASA Bucket"].tolist()
    st.plotly_chart(aasa_combo(labels, counts, cum_pct), use_container_width=True)
with col2:
    top10 = agt.head(10)
    st.plotly_chart(aasa_agent_bar(top10["Agent"].tolist(), top10["Avg AASA (s)"].tolist()), use_container_width=True)

st.markdown("<div class='section-title'>AASA Bucket Distribution</div>", unsafe_allow_html=True)
st.dataframe(bkt, use_container_width=True, hide_index=True)

st.markdown("<div class='section-title'>Per-Agent AASA Detail</div>", unsafe_allow_html=True)
st.dataframe(agt, use_container_width=True, hide_index=True)
