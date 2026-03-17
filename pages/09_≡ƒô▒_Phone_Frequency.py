import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import phone_frequency

st.set_page_config(page_title="Phone Frequency", page_icon="📱", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>📱 Phone Number Frequency</h2>", unsafe_allow_html=True)

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)

with st.spinner("Computing phone frequency…"):
    all_df, high_df = phone_frequency(df)

c = st.columns(3)
c[0].metric("Unique Numbers",  f"{len(all_df):,}")
c[1].metric("High Frequency",  f"{len(high_df):,}", "> 10 contacts")
c[2].metric("Max Contacts",    int(all_df["Total Contacts"].max()) if len(all_df) else 0)

st.divider()
st.markdown(f"<div class='section-title'>High Frequency Numbers (>10 contacts) — {len(high_df)} flagged</div>", unsafe_allow_html=True)
st.dataframe(high_df, use_container_width=True, hide_index=True)

st.markdown("<div class='section-title'>All Phone Numbers</div>", unsafe_allow_html=True)
q = st.text_input("Search phone number", "")
filt = all_df[all_df["Phone Number"].str.contains(q, na=False)] if q else all_df
st.dataframe(filt.head(500), use_container_width=True, hide_index=True)
