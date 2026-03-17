import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import agent_stats
from charts import agent_hbar, P

st.set_page_config(page_title="Agent Performance", page_icon="👤", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>👤 Agent Performance</h2>", unsafe_allow_html=True)

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)

with st.spinner("Computing agent stats…"):
    ag_all, ag_inc, ag_out = agent_stats(df)

# Drop internal scoring columns for display
def clean(d):
    return d.drop(columns=[c for c in d.columns if c.startswith("_")], errors="ignore")

tab_all, tab_inc, tab_out = st.tabs(["All Calls", "Incoming Only", "Outgoing Only"])

with tab_all:
    st.caption(f"**{len(ag_all)} agents** · Avg talk = both-connected calls only")
    st.dataframe(clean(ag_all), use_container_width=True, hide_index=True)
    if not ag_all.empty:
        col1, col2 = st.columns(2)
        top = ag_all.head(15)
        with col1:
            st.plotly_chart(
                agent_hbar(top["Agent Name"].tolist(), top["Answered"].tolist(), P["blue"], "Top 15 Agents by Answered Calls"),
                use_container_width=True)
        with col2:
            st.plotly_chart(
                agent_hbar(top["Agent Name"].tolist(), top["Total Talk (hrs)"].tolist(), P["orange"], "Total Talk Hours"),
                use_container_width=True)

with tab_inc:
    st.caption("Incoming calls only")
    st.dataframe(clean(ag_inc), use_container_width=True, hide_index=True)

with tab_out:
    st.caption("Outgoing calls only")
    st.dataframe(clean(ag_out), use_container_width=True, hide_index=True)
