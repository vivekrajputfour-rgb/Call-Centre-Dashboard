import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import detect_anomalies, anomaly_summary, fmt_dur, pct
from charts import anom_hbar

st.set_page_config(page_title="Anomalies", page_icon="🚨", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>🚨 Anomaly Detection</h2>", unsafe_allow_html=True)
st.caption("14 independent anomaly checks — matching the Excel 'Anomaly Summary' sheet exactly")

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)

# Re-run anomaly detection if not already present
if "is_anomaly" not in df.columns:
    with st.spinner("Detecting anomalies…"):
        df = detect_anomalies(df)

anom = df[df["is_anomaly"]]
n    = len(df)

c = st.columns(2)
c[0].metric("Anomalous Records", f"{len(anom):,}", f"{pct(len(anom),n)}% of total")
c[1].metric("Clean Records",     f"{n-len(anom):,}", f"{pct(n-len(anom),n)}%")

st.divider()

rc, anom_df = anomaly_summary(df)

if rc.empty:
    st.success("No anomalies detected.")
else:
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(anom_hbar(rc["Anomaly Type"].tolist(), rc["Count"].tolist()), use_container_width=True)
    with col2:
        st.markdown("<div class='section-title'>Anomaly Type Summary</div>", unsafe_allow_html=True)
        st.dataframe(rc, use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("<div class='section-title'>Anomalous Records Detail</div>", unsafe_allow_html=True)
    disp = anom_df.copy()
    if "talk_sec" in disp.columns:
        disp["talk_sec"] = disp["talk_sec"].apply(fmt_dur)
        disp = disp.rename(columns={"talk_sec":"Talk Time"})
    if "dur_sec" in disp.columns:
        disp["dur_sec"] = disp["dur_sec"].apply(fmt_dur)
        disp = disp.rename(columns={"dur_sec":"Duration"})
    if "aasa_sec" in disp.columns:
        disp["aasa_sec"] = disp["aasa_sec"].apply(fmt_dur)
        disp = disp.rename(columns={"aasa_sec":"AASA"})
    if "dt" in disp.columns:
        disp["dt"] = disp["dt"].astype(str)
    st.dataframe(disp.head(500), use_container_width=True, hide_index=True)
