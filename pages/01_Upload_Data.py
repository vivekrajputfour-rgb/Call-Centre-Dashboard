import streamlit as st
import pandas as pd
from core import parse_dataframe, detect_anomalies
from storage import save_month, list_months, delete_month, load_month

st.set_page_config(page_title="Upload Data", page_icon="📤", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>📤 Upload Monthly Data</h2>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("Upload your **Knowlarity** monthly export (Excel `.xlsx` or `.csv`).")
    uploaded = st.file_uploader("Drop your file here", type=["xlsx","xls","csv"])

    if uploaded:
        with st.spinner("Parsing…"):
            try:
                if uploaded.name.lower().endswith(".csv"):
                    raw = pd.read_csv(uploaded, encoding="latin-1", low_memory=False)
                else:
                    raw = pd.read_excel(uploaded, engine="openpyxl")
                raw.columns = raw.columns.str.strip()

                df  = parse_dataframe(raw)
                df  = detect_anomalies(df)

                months_found = sorted(df["month"].dropna().unique().tolist())
                ok   = int(df["dt"].notna().sum())
                fail = int(df["dt"].isna().sum())

                st.success(f"✅ **{len(df):,} rows parsed** — {ok:,} dates OK, {fail} failures")
                if months_found:
                    st.info(f"📅 Months detected: **{', '.join(months_found)}**")
                else:
                    st.error("No valid months found. Check the 'Date and Time' column.")
                    st.stop()

                with st.expander("Preview (first 5 rows)"):
                    st.dataframe(raw.head(5), use_container_width=True)

                existing = list_months()
                for m in months_found:
                    mdf = df[df["month"] == m].copy()
                    if m in existing:
                        ca, cb = st.columns([3,1])
                        ca.warning(f"Month **{m}** already exists")
                        if cb.button(f"Replace {m}", key=f"rep_{m}"):
                            save_month(m, mdf)
                            st.success(f"✅ Replaced **{m}** — {len(mdf):,} rows")
                            st.rerun()
                    else:
                        save_month(m, mdf)
                        st.success(f"✅ Saved **{m}** — {len(mdf):,} rows")

            except Exception as e:
                st.error(f"Error: {e}")
                st.exception(e)

with col2:
    st.markdown("<div class='section-title'>Stored Months</div>", unsafe_allow_html=True)
    months = list_months()
    if not months:
        st.info("No data stored yet.")
    else:
        for m in months:
            dm = load_month(m)
            r  = len(dm) if dm is not None else 0
            ca, cb = st.columns([3,1])
            ca.metric(m, f"{r:,} rows")
            if cb.button("🗑️", key=f"del_{m}"):
                delete_month(m)
                st.rerun()
