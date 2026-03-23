import streamlit as st
import pandas as pd
from core import parse_dataframe, detect_anomalies
from storage import save_month, list_months, delete_month, load_month, _github_enabled

st.set_page_config(page_title="Upload Data", page_icon="📤", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>📤 Upload Monthly Data</h2>", unsafe_allow_html=True)

# ── GitHub status banner ──────────────────────────────────────
if _github_enabled():
    st.success("✅ **GitHub storage active** — your data is saved permanently to GitHub and will never be lost on sleep/restart.")
else:
    st.warning("""
⚠️ **GitHub storage not configured** — data is stored locally and will be lost when Streamlit Cloud sleeps.

**To fix this (5 min setup):**
1. Go to **github.com → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **Generate new token** → name it anything → check **repo** scope → Generate → Copy the token
3. Go to **share.streamlit.io → your app → Settings → Secrets** and paste:
```toml
[github]
token = "ghp_paste_your_token_here"
repo  = "vivekrajputfour-rgb/Call-Centre-Dashboard"
branch = "main"
```
4. Save → app restarts → data is now permanent ✅
""")

st.divider()
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("Upload your **Knowlarity** monthly export (Excel `.xlsx` or `.csv`). The app detects the month from the `Date and Time` column automatically.")

    uploaded = st.file_uploader("Drop your file here", type=["xlsx","xls","csv"])

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
                        f"slot=**{sp.get('slot','?')}**, "
                        f"dow=**{sp.get('dow','?')}**"
                    )

                with st.expander("Preview raw data (first 5 rows)"):
                    st.dataframe(raw.head(5), use_container_width=True)

                st.divider()
                existing = list_months()
                for m in months_found:
                    mdf = df[df["month"] == m].copy()
                    st.info(f"Preparing to save **{m}** — {len(mdf):,} rows…")

                    do_save = False
                    if m in existing:
                        col_a, col_b = st.columns([3,1])
                        col_a.warning(f"Month **{m}** already exists — click Replace to overwrite")
                        if col_b.button(f"Replace {m}", key=f"rep_{m}"):
                            do_save = True
                    else:
                        do_save = True

                    if do_save:
                        with st.spinner(f"Saving {m} to GitHub ({len(mdf):,} rows)… this may take 10–30 seconds for large files"):
                            success = save_month(m, mdf)
                        if success:
                            st.success(f"✅ **{m}** saved — {len(mdf):,} rows permanently stored in GitHub")
                            st.cache_data.clear()
                        else:
                            st.error(f"❌ Save failed for {m}. Check the error above and try again.")

            except Exception as e:
                st.error(f"Parse error: {e}")
                st.exception(e)

with col2:
    st.markdown("<div class='section-title'>Stored Months</div>", unsafe_allow_html=True)

    if _github_enabled():
        st.caption("📁 Stored in your GitHub repo — permanent")
    else:
        st.caption("📁 Stored locally — configure GitHub to make permanent")

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
                with st.spinner(f"Deleting {m}…"):
                    delete_month(m)
                st.cache_data.clear()
                st.rerun()

    st.divider()
    if st.button("🔄 Refresh month list"):
        st.cache_data.clear()
        st.rerun()
