import streamlit as st
import pandas as pd
import numpy as np
from storage import list_months, load_selected
from core import answered_hourly, hourly_volume, slot_range, N_SLOTS
from charts import slot_single, slot_two_line, P

st.set_page_config(page_title="Answered Hourly", page_icon="🕐", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>🕐 Answered Calls — 15-min Time Slots</h2>", unsafe_allow_html=True)

st.info("""
Each call's time is extracted from the **Date and Time** column and mapped to a 15-minute slot.  
Slot 0 = 12:00 AM–12:15 AM · Slot 95 = 11:45 PM–12:00 AM  
Only **answered** calls are counted in these charts.
""")

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)

inc_df, out_df, sai, sao = answered_hourly(df)

# Peak metrics
pi = int(np.argmax(sai)); pv = int(sai[pi])
po = int(np.argmax(sao)); pov= int(sao[po])

c = st.columns(2)
c[0].metric("Peak Incoming Slot", slot_range(pi) if pv>0 else "N/A", f"{pv} answered calls")
c[1].metric("Peak Outgoing Slot", slot_range(po) if pov>0 else "N/A", f"{pov} answered calls")

st.divider()

# Answered Incoming
st.markdown("<div class='section-title'>Answered Incoming Calls — 15-min Slots</div>", unsafe_allow_html=True)
st.plotly_chart(slot_single(sai, P["teal"], "Answered Incoming Calls by 15-min Slot"), use_container_width=True)
inc_show = inc_df[inc_df["Answered Incoming"] > 0][["Time Slot","Answered Incoming"]].copy()
inc_show["% of Day"] = (inc_show["Answered Incoming"]/max(inc_show["Answered Incoming"].sum(),1)*100).round(1)
with st.expander(f"Incoming slot table ({len(inc_show)} active slots)"):
    st.dataframe(inc_show, use_container_width=True, hide_index=True)

st.divider()

# Answered Outgoing
st.markdown("<div class='section-title'>Answered Outgoing Calls — 15-min Slots</div>", unsafe_allow_html=True)
st.plotly_chart(slot_single(sao, P["blue"], "Answered Outgoing Calls by 15-min Slot"), use_container_width=True)
out_show = out_df[out_df["Answered Outgoing"] > 0][["Time Slot","Answered Outgoing"]].copy()
out_show["% of Day"] = (out_show["Answered Outgoing"]/max(out_show["Answered Outgoing"].sum(),1)*100).round(1)
with st.expander(f"Outgoing slot table ({len(out_show)} active slots)"):
    st.dataframe(out_show, use_container_width=True, hide_index=True)

st.divider()

# Hourly Volume (raw 24h table matching Excel)
st.markdown("<div class='section-title'>Hourly Volume Table (24h) — All Calls</div>", unsafe_allow_html=True)
hv = hourly_volume(df)
st.dataframe(hv, use_container_width=True, hide_index=True)
