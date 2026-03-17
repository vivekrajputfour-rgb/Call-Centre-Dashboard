# Call Centre Intelligence — Streamlit Dashboard

Complete analytics dashboard matching every sheet in the Excel report.
Built for Knowlarity call centre data. Persistent month-over-month storage.

---

## 📁 Project Structure

```
cc_app/
├── app.py                    ← Home page
├── core.py                   ← All data parsing + analytics engine
├── storage.py                ← Parquet file storage per month
├── charts.py                 ← All Plotly figures
├── requirements.txt
├── data/                     ← Auto-created, stores monthly .parquet files
└── pages/
    ├── 01_📤_Upload_Data.py
    ├── 02_📊_Overview.py
    ├── 03_↔️_Direction.py
    ├── 04_🔗_Connection.py
    ├── 05_👤_Agents.py
    ├── 06_🏆_Scores_Salary.py
    ├── 07_⏱️_AASA.py
    ├── 08_📞_Long_Calls.py
    ├── 09_📱_Phone_Frequency.py
    ├── 10_🕐_Answered_Hourly.py
    ├── 11_⏰_Talk_Buckets.py
    ├── 12_🏷️_Dispositions.py
    ├── 13_⚠️_Network_Issues.py
    ├── 14_🚨_Anomalies.py
    └── 15_📈_MoM_Trends.py
```

---

## 🚀 Deploy on Streamlit Community Cloud (FREE — 5 min setup)

### Step 1: Put the project on GitHub

1. Create a free account at https://github.com
2. Create a new **public** repository (e.g. `callcentre-dashboard`)
3. Upload ALL files from `cc_app/` into the repository root
   - `app.py`, `core.py`, `storage.py`, `charts.py`, `requirements.txt`
   - The entire `pages/` folder with all 15 page files
   - Do NOT upload the `data/` folder (it gets created automatically)

### Step 2: Deploy on Streamlit Cloud

1. Go to https://share.streamlit.io and sign in with GitHub
2. Click **"New app"**
3. Select your repository → Branch: `main` → Main file: `app.py`
4. Click **"Deploy"** — done in ~2 minutes

Your dashboard will be live at:
`https://<your-username>-callcentre-dashboard-app-xxxx.streamlit.app`

---

## 💾 Data Persistence

- Each month is stored as a `.parquet` file in the `data/` folder
- On **Streamlit Cloud**, the `data/` folder is ephemeral (resets on redeployment)
- **Recommended for permanent storage:** Use a free **Supabase** or **PlanetScale** database,
  or simply re-upload your monthly files after deployment

For truly persistent storage on Streamlit Cloud, add this to `storage.py`:
```python
# Option: Use st.session_state as cache so data survives navigation
# Option: Connect to Supabase (free tier) for cloud storage
```

---

## 🖥️ Run Locally

```bash
# 1. Install Python 3.11+
# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py

# Opens at http://localhost:8501
```

---

## 📊 Dashboard Pages

| Page | Matches Excel Sheet |
|------|---------------------|
| Overview | Overview (all KPIs) |
| Direction Analysis | Direction Analysis |
| Connection Status | Connection Status |
| Agents (All/Inc/Out) | Agent — All / Incoming / Outgoing |
| Scores & Salary | Agent Scores |
| AASA | AASA Analysis |
| Long Calls | UUID > 15 min, UUID > 20 min |
| Phone Frequency | Phone Frequency, High Frequency Numbers |
| Answered Hourly | Answered Hourly — Inc / Out (15-min slots) |
| Talk Buckets | Talk Time Buckets |
| Dispositions | Dispositions |
| Network Issues | Network Issues |
| Anomalies | Anomaly Summary |
| MoM Trends | All months combined |

---

## 📅 Date Format

Handles Knowlarity format: `2/22/2026 11:24:24 AM` (M/D/YYYY H:MM:SS AM/PM)

The parser also handles:
- `2/22/2026 13:24:24` (24-hour, no AM/PM)
- `2026-02-22 11:24:24` (ISO format)
- Excel datetime objects

---

## 💰 Salary Scoring

Base salary: ₹35,000/month (edit `SALARY_BASE` in `core.py`)

Weights:
- 30% — Call volume (answered calls)
- 25% — Avg talk time (ideal = 15 min)
- 20% — Answer rate %
- 15% — Long calls ≥ 15 min
- 10% — Both-connected %

Score → Salary:
- ≥ 80 → Fully Justified → 100%
- ≥ 65 → Mostly Justified → 85%
- ≥ 50 → Partially Justified → 70%
- < 50 → Needs Improvement → 55%
