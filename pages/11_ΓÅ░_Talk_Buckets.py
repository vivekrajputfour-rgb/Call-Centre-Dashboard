import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import talk_buckets, dow_table, pct
from charts import talk_bkt_bar, dow_bar

st.set_page_config(page_title="Talk Buckets", page_icon="⏰", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>⏰ Talk Time Buckets</h2>", unsafe_allow_html=True)
st.caption("Both-connected calls only — matching the Excel 'Talk Time Buckets' sheet")

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)
bc  = df[df["both_conn"]]

t10 = int((bc["talk_sec"]>=600).sum())
t15 = int((bc["talk_sec"]>=900).sum())
t20 = int((bc["talk_sec"]>=1200).sum())
n   = len(bc)

c = st.columns(4)
c[0].metric("Both Connected",  f"{n:,}")
c[1].metric("Talk ≥ 10 min",   f"{t10:,}", f"{pct(t10,n)}%")
c[2].metric("Talk ≥ 15 min",   f"{t15:,}", f"{pct(t15,n)}%")
c[3].metric("Talk ≥ 20 min",   f"{t20:,}", f"{pct(t20,n)}%")

st.divider()
bkt = talk_buckets(df)
st.plotly_chart(talk_bkt_bar(bkt["Talk Time Bucket"].tolist(), bkt["Count"].tolist()), use_container_width=True)

st.markdown("<div class='section-title'>Talk Time Buckets Table</div>", unsafe_allow_html=True)
st.dataframe(bkt, use_container_width=True, hide_index=True)

st.divider()
st.markdown("<div class='section-title'>Day of Week</div>", unsafe_allow_html=True)
dow = dow_table(df)
col1, col2 = st.columns(2)
with col1: st.plotly_chart(dow_bar(df["dow"].dropna().value_counts().to_dict()), use_container_width=True)
with col2: st.dataframe(dow, use_container_width=True, hide_index=True)
