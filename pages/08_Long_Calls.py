import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import long_calls, fmt_dur, pct

st.set_page_config(page_title="Long Calls", page_icon="📞", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>📞 Long Calls (>15 min & >20 min)</h2>", unsafe_allow_html=True)
st.caption("Both-connected calls only — matching the Excel report UUID sheets exactly")

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)
bc  = df[df["both_conn"]]

t15, t20 = long_calls(df)

c = st.columns(3)
c[0].metric("Calls > 15 min", len(t15), "both connected")
c[1].metric("Calls > 20 min", len(t20), "both connected")
c[2].metric("% > 15 min",     f"{pct(len(t15),len(bc))}%", "of both-connected")

def display(d, label):
    st.markdown(f"<div class='section-title'>{label} — {len(d)} calls</div>", unsafe_allow_html=True)
    if d.empty:
        st.info("No calls in this category.")
        return
    disp = d.copy()
    if "talk_sec" in disp.columns:
        disp["talk_formatted"] = disp["talk_sec"].apply(fmt_dur)
    if "dt" in disp.columns:
        disp["datetime"] = disp["dt"].astype(str)
    cols = [c for c in ["call_uuid","datetime","direction","agent_name","customer",
                         "talk_formatted","talk_min","status","disposition"] if c in disp.columns]
    st.dataframe(disp[cols].head(200), use_container_width=True, hide_index=True)

st.divider()
display(t15, "Talk > 15 min")
st.divider()
display(t20, "Talk > 20 min")
