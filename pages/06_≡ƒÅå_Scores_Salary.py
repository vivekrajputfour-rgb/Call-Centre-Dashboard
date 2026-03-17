import streamlit as st
import pandas as pd
from storage import list_months, load_selected
from core import agent_stats, score_agents, SALARY_BASE, pct
from charts import agent_score_hbar

st.set_page_config(page_title="Scores & Salary", page_icon="🏆", layout="wide")
st.markdown("<h2 style='font-family:Playfair Display,serif'>🏆 Agent Scores & Salary Justification</h2>", unsafe_allow_html=True)

st.info(f"""
**Scoring weights:** Volume 30% · Talk Time (ideal 15min) 25% · Answer Rate 20% · Long Calls ≥15m 15% · Connection % 10%

**Base salary ₹{SALARY_BASE:,}/month** → Score ≥80 → 100% (Fully Justified) · ≥65 → 85% · ≥50 → 70% · <50 → 55% (Needs Improvement)
""")

months = list_months()
if not months: st.warning("No data."); st.stop()
sel = st.multiselect("Months", months, default=months)
if not sel: st.stop()
df  = load_selected(sel)

with st.spinner("Computing scores…"):
    ag_all, _, _ = agent_stats(df)
    sc = score_agents(ag_all)

if sc.empty: st.info("No agent data."); st.stop()

cats = {"Fully Justified":0,"Mostly Justified":0,"Partially Justified":0,"Needs Improvement":0}
for r in sc["Rating"]: cats[r] = cats.get(r,0)+1

c = st.columns(6)
c[0].metric("Fully Justified",     cats["Fully Justified"],     "Score ≥ 80")
c[1].metric("Mostly Justified",    cats["Mostly Justified"],    "Score 65–79")
c[2].metric("Partially Justified", cats["Partially Justified"], "Score 50–64")
c[3].metric("Needs Improvement",   cats["Needs Improvement"],  "Score < 50")
c[4].metric("Total Salary Gap",    f"₹{sc['Salary Gap (₹)'].sum():,}")
c[5].metric("Justified Payroll",   f"₹{sc['Justified Salary (₹)'].sum():,}")

st.divider()
st.markdown("<div class='section-title'>Scores Table</div>", unsafe_allow_html=True)
st.dataframe(sc, use_container_width=True, hide_index=True)

st.divider()
st.plotly_chart(
    agent_score_hbar(sc["Agent Name"].tolist(), sc["Score"].tolist(), sc["Rating"].tolist()),
    use_container_width=True)
