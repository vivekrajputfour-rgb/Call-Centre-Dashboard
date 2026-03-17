import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import connection_table, fmt_dur, pct
from charts import conn_donut

st.set_page_config(page_title="Connection Status", page_icon="🔗", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>🔗 Connection Status</h2>", unsafe_allow_html=True)

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)
n   = len(df)

both  = int(df["both_conn"].sum())
cust  = int(df["cust_only"].sum())
agt   = int(df["agt_only"].sum())
none_ = int(df["none_conn"].sum())

c = st.columns(4)
c[0].metric("Both Connected",  f"{both:,}",  f"{pct(both,n)}%")
c[1].metric("Cust Only",       f"{cust:,}",  f"{pct(cust,n)}%")
c[2].metric("Agent Only",      f"{agt:,}",   f"{pct(agt,n)}%")
c[3].metric("Neither",         f"{none_:,}", f"{pct(none_,n)}%")

st.divider()
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(conn_donut(both,cust,agt,none_), use_container_width=True)
with col2:
    conn_df, detail_df = connection_table(df)
    st.markdown("<div class='section-title'>Connection State Summary</div>", unsafe_allow_html=True)
    st.dataframe(conn_df, use_container_width=True, hide_index=True)

st.markdown("<div class='section-title'>Connection Breakdown by Direction</div>", unsafe_allow_html=True)
st.dataframe(detail_df, use_container_width=True, hide_index=True)
