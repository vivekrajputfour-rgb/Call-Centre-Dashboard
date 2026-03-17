import streamlit as st

st.set_page_config(
    page_title="Call Centre Intelligence",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Premium Light Theme CSS ───────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
.stApp { background-color: #f5f3ef; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #ffffff;
    border-right: 1px solid #e8e3d8;
}
[data-testid="stSidebar"] .stMarkdown h1 {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem;
    color: #e05c3a;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #ffffff;
    border: 1px solid #e8e3d8;
    border-radius: 14px;
    padding: 14px 18px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
[data-testid="stMetricValue"] { font-size: 1.55rem !important; font-weight: 700 !important; color: #1a1714 !important; }
[data-testid="stMetricLabel"] { font-size: 0.7rem !important; text-transform: uppercase; letter-spacing: 0.7px; color: #8c8680 !important; }
[data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

/* Tab nav */
.stTabs [data-baseweb="tab-list"] {
    gap: 3px; background: #ffffff; padding: 5px;
    border-radius: 10px; border: 1px solid #e8e3d8;
    margin-bottom: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px; padding: 6px 14px;
    font-size: 13px; font-weight: 500; color: #8c8680;
}
.stTabs [aria-selected="true"] {
    background-color: #e05c3a !important; color: white !important;
}

/* Dataframes */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* Divider */
hr { border-color: #e8e3d8; }

/* Cards via st.container */
div.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

/* Buttons */
.stButton button {
    background: #e05c3a; color: white; border: none;
    border-radius: 8px; font-weight: 600; padding: 8px 20px;
}
.stButton button:hover { background: #c94e2e; }

/* Multiselect */
[data-baseweb="multi-select"] { border-radius: 8px; }

/* File uploader */
[data-testid="stFileUploader"] {
    background: #ffffff; border-radius: 12px;
    border: 2px dashed #e8e3d8;
}

/* Section headers */
.section-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem; font-weight: 700;
    color: #1a1714; margin: 0 0 12px 0;
    border-left: 4px solid #e05c3a;
    padding-left: 12px;
}
</style>
""", unsafe_allow_html=True)

# ── Home page ─────────────────────────────────────────────────
st.markdown("<h1 style='font-family:Playfair Display,serif;color:#1a1714'>📞 Call Centre Intelligence</h1>", unsafe_allow_html=True)

st.markdown("""
**Welcome.** Use the sidebar to navigate between sections.

**How it works:**
- Go to **📤 Upload Data** each month to add your Knowlarity export
- Each month is stored permanently on disk — data survives refreshes and restarts
- Select one month or combine multiple months across all analysis pages

**Date format supported:** `2/22/2026 11:24:24 AM` (M/D/YYYY H:MM:SS AM/PM)  
**Hourly charts** use 15-minute time slots from 12:00 AM through 11:45 PM
""")

from storage import list_months, load_month
months = list_months()
if months:
    st.success(f"✅ **{len(months)} month(s) stored:** {', '.join(months)}")
    cols = st.columns(min(len(months), 4))
    for i, m in enumerate(months):
        dm = load_month(m)
        r  = len(dm) if dm is not None else 0
        cols[i % 4].metric(m, f"{r:,} rows")
else:
    st.info("No data yet — go to **📤 Upload Data** to get started.")
