import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import disposition_table
from charts import disp_donut

st.set_page_config(page_title="Dispositions", page_icon="🏷️", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>🏷️ Disposition Breakdown</h2>", unsafe_allow_html=True)

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)

disp = disposition_table(df)
n    = len(df)

c = st.columns(2)
c[0].metric("Unique Dispositions", len(disp))
c[1].metric("Top Disposition",     disp.iloc[0]["Disposition"] if len(disp) else "N/A",
            f"{disp.iloc[0]['Count']} calls" if len(disp) else "")

st.divider()
top10 = disp.head(10)
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(disp_donut(top10["Disposition"].tolist(), top10["Count"].tolist()), use_container_width=True)
with col2:
    st.markdown("<div class='section-title'>All Dispositions</div>", unsafe_allow_html=True)
    st.dataframe(disp, use_container_width=True, hide_index=True)
