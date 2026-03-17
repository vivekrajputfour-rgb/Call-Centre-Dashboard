import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import network_table, pct
from charts import net_agent_bar

st.set_page_config(page_title="Network Issues", page_icon="⚠️", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>⚠️ Network Issues — Blank Hangup By</h2>", unsafe_allow_html=True)
st.caption("Calls where the 'Hangup By' field is blank — potential network drops")

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)

bl = df[df["blank_hu"]]
n  = len(df)

c = st.columns(5)
c[0].metric("Total Blank Hangup",  f"{len(bl):,}",                                    f"{pct(len(bl),n)}%")
c[1].metric("Blank + Answered",    int((bl["status"]=="answered").sum()),              "Network drop?")
c[2].metric("Blank + Missed",      int(bl["status"].isin(["missed","unanswered"]).sum()))
c[3].metric("Blank Incoming",      int((bl["direction"]=="incoming").sum()))
c[4].metric("Blank Outgoing",      int((bl["direction"]=="outgoing").sum()))

st.divider()
net = network_table(df)
st.markdown("<div class='section-title'>Network Issues Table</div>", unsafe_allow_html=True)
st.dataframe(net, use_container_width=True, hide_index=True)

st.divider()
st.markdown("<div class='section-title'>Blank Hangup by Agent</div>", unsafe_allow_html=True)
ag_bl = bl.groupby("agent_name").size().sort_values(ascending=False).head(15).reset_index()
ag_bl.columns = ["Agent","Count"]
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(net_agent_bar(ag_bl["Agent"].tolist(), ag_bl["Count"].tolist()), use_container_width=True)
with col2:
    st.dataframe(ag_bl, use_container_width=True, hide_index=True)
