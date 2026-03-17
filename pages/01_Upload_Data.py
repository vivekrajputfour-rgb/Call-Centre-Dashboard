import streamlit as st
import pandas as pd
from core import parse_dataframe, detect_anomalies
from storage import save_month, list_months, delete_month, load_month

st.set_page_config(page_title="Upload Data", page_icon="📤", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>📤 Upload Monthly Data</h2>", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("""
    Upload your **Knowlarity** monthly export (Excel `.xlsx` or `.csv`).  
    The app reads the `Date and Time` column, detects the month automatically, and stores each month separately.
    """)

    uploaded = st.file_uploader(
        "Drop your Knowlarity file here",
        type=["xlsx", "xls", "csv"],
        help="Supports M/D/YYYY H:MM:SS AM/PM date format"
    )

    if uploaded:
        with st.spinner("Parsing file… this may take a moment for large files."):
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

                st.success(f"✅ **{len(df):,} rows parsed** — {ok:,} dates OK, {fail} date failures")

                if months_found:
                    st.info(f"📅 Months detected: **{', '.join(months_found)}**")
                else:
                    st.error("Could not detect any valid months. Check that 'Date and Time' column exists.")
                    st.stop()

                # Debug sample
                dt_col = None
                for cn in raw.columns:
                    if cn.strip().lower() in ("date and time","datetime","date time"):
                        dt_col = cn; break
                if dt_col and len(raw) > 0:
                    sample_raw = str(raw[dt_col].iloc[0])
                    sp = df.iloc[0]
                    st.caption(
                        f"📌 Sample parse: `{sample_raw}` → "
                        f"month=**{sp.get('month','?')}**, "
                        f"hour=**{sp.get('hour','?')}**, "
                        f"slot=**{sp.get('slot','?')}**, "
                        f"dow=**{sp.get('dow','?')}**"
                    )

                with st.expander("Preview raw data (first 5 rows)"):
                    st.dataframe(raw.head(5), use_container_width=True)

                st.divider()
                existing = list_months()
                for m in months_found:
                    mdf = df[df["month"] == m].copy()
                    if m in existing:
                        col_a, col_b = st.columns([3,1])
                        col_a.warning(f"Month **{m}** already exists ({len(load_month(m)):,} rows)")
                        if col_b.button(f"Replace {m}", key=f"rep_{m}"):
                            save_month(m, mdf)
                            st.success(f"Replaced {m} with {len(mdf):,} rows")
                            st.rerun()
                    else:
                        save_month(m, mdf)
                        st.success(f"✅ Saved **{m}** — {len(mdf):,} rows")

            except Exception as e:
                st.error(f"Parse error: {e}")
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
            ca, cb = st.columns([3, 1])
            ca.metric(m, f"{r:,} rows")
            if cb.button("🗑️", key=f"del_{m}", help=f"Delete {m}"):
                delete_month(m)
                st.rerun()

    st.divider()
    st.caption("Each month is stored as a `.parquet` file in the `data/` folder next to the app. Data persists between restarts.")
