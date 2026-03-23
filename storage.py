"""
storage.py — Persistent storage using GitHub as the database.

How it works:
- Monthly data is saved as CSV files committed directly to your GitHub repo
- Data survives Streamlit Cloud sleep/restart/redeploy 100% of the time
- Uses GitHub API — no extra services needed, your repo is already there

Setup (one time):
1. Go to github.com → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name like "callcentre-dashboard"
4. Check the "repo" scope (full repo access)
5. Click "Generate token" — copy it immediately
6. On Streamlit Cloud → your app → Settings → Secrets → add:
   [github]
   token = "ghp_yourtoken..."
   repo  = "vivekrajputfour-rgb/Call-Centre-Dashboard"
   branch = "main"
"""

import os
import io
import base64
import json
import pandas as pd
import streamlit as st

# ── GitHub config from Streamlit secrets ─────────────────────
def _gh_config():
    try:
        token  = st.secrets["github"]["token"]
        repo   = st.secrets["github"]["repo"]
        branch = st.secrets["github"].get("branch", "main")
        return token, repo, branch
    except Exception:
        return None, None, "main"

def _headers():
    token, _, _ = _gh_config()
    if not token:
        return {}
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

def _file_url(month: str) -> str:
    _, repo, branch = _gh_config()
    return f"https://api.github.com/repos/{repo}/contents/data/{month}.csv?ref={branch}"

def _api_url(month: str) -> str:
    _, repo, _ = _gh_config()
    return f"https://api.github.com/repos/{repo}/contents/data/{month}.csv"

# ── Check if GitHub is configured ────────────────────────────
def _github_enabled() -> bool:
    token, repo, _ = _gh_config()
    return bool(token and repo)

# ── LOCAL fallback (for running locally without GitHub) ──────
_LOCAL_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(_LOCAL_DIR, exist_ok=True)

def _local_path(m): 
    return os.path.join(_LOCAL_DIR, f"{m}.parquet")

# ── SAVE ──────────────────────────────────────────────────────
def save_month(month: str, df: pd.DataFrame):
    if _github_enabled():
        _save_github(month, df)
    else:
        # Local fallback
        df.to_parquet(_local_path(month), index=False)

def _save_github(month: str, df: pd.DataFrame):
    import requests

    # Convert df to CSV string then base64
    csv_str   = df.to_csv(index=False)
    csv_bytes = csv_str.encode("utf-8")
    content_b64 = base64.b64encode(csv_bytes).decode("utf-8")

    # GitHub API has a 100MB limit per file — warn if close
    size_mb = len(csv_bytes) / (1024 * 1024)
    if size_mb > 90:
        st.error(f"File too large for GitHub ({size_mb:.1f} MB). Max is ~90 MB.")
        return

    # Get SHA if file already exists (required to update existing file)
    sha = _get_sha(month)

    payload = {
        "message": f"data: save {month} ({len(df):,} rows)",
        "content": content_b64,
        "branch":  _gh_config()[2],
    }
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(_api_url(month), headers=_headers(),
                         json=payload, timeout=60)
        if r.status_code not in (200, 201):
            msg = r.json().get("message", str(r.status_code))
            st.error(f"GitHub save failed: {msg}")
        else:
            _cached_load.clear()
            list_months.clear()
    except Exception as e:
        st.error(f"GitHub save error: {e}")

def _get_sha(month: str) -> str | None:
    """Get the SHA of an existing file (needed for GitHub updates)."""
    import requests
    r = requests.get(_file_url(month), headers=_headers())
    if r.status_code == 200:
        return r.json().get("sha")
    return None

# ── LOAD ──────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)  # cache 5 min
def _cached_load(month: str) -> pd.DataFrame | None:
    if _github_enabled():
        return _load_github(month)
    else:
        p = _local_path(month)
        if not os.path.exists(p): return None
        df = pd.read_parquet(p)
        if "dt" in df.columns:
            df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
        return df

def _load_github(month: str) -> pd.DataFrame | None:
    import requests
    try:
        r = requests.get(_file_url(month), headers=_headers(), timeout=30)
        if r.status_code != 200:
            return None

        data = r.json()
        raw_content = data.get("content", "")

        # GitHub returns base64 with newlines — strip them before decoding
        raw_content = raw_content.replace("\n", "").replace("\r", "").strip()

        if not raw_content:
            # File exists on GitHub but is empty — skip it
            return None

        csv_str = base64.b64decode(raw_content).decode("utf-8").strip()

        if not csv_str or csv_str == "":
            return None

        df = pd.read_csv(io.StringIO(csv_str), low_memory=False)

        if df.empty:
            return None

        if "dt" in df.columns:
            df["dt"] = pd.to_datetime(df["dt"], errors="coerce")

        # Restore bool columns lost during CSV round-trip
        for col in ["both_conn","cust_only","agt_only","none_conn","blank_hu",
                    "cust_conn","agt_conn","is_anomaly"]:
            if col in df.columns:
                df[col] = df[col].fillna(False).astype(bool)

        return df

    except Exception as e:
        # Log but don't crash — return None so app keeps working
        import streamlit as st
        st.warning(f"Could not load {month} from GitHub: {e}")
        return None

def load_month(month: str) -> pd.DataFrame | None:
    return _cached_load(month)

# ── LIST ──────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def list_months() -> list[str]:
    if _github_enabled():
        return _list_github()
    else:
        return sorted(
            f[:-8] for f in os.listdir(_LOCAL_DIR) if f.endswith(".parquet")
        )

def _list_github() -> list[str]:
    import requests
    _, repo, branch = _gh_config()
    url = f"https://api.github.com/repos/{repo}/contents/data?ref={branch}"
    r = requests.get(url, headers=_headers())
    if r.status_code != 200:
        return []
    files = r.json()
    if not isinstance(files, list):
        return []
    return sorted(
        f["name"].replace(".csv","")
        for f in files if f["name"].endswith(".csv")
    )

# ── DELETE ────────────────────────────────────────────────────
def delete_month(month: str):
    if _github_enabled():
        _delete_github(month)
    else:
        p = _local_path(month)
        if os.path.exists(p): os.remove(p)

def _delete_github(month: str):
    import requests
    sha = _get_sha(month)
    if not sha:
        return
    payload = {
        "message": f"data: delete {month}",
        "sha": sha,
        "branch": _gh_config()[2],
    }
    requests.delete(_api_url(month), headers=_headers(), json=payload)
    _cached_load.clear()
    list_months.clear()

# ── LOAD MULTIPLE ─────────────────────────────────────────────
def load_selected(months: list[str]) -> pd.DataFrame:
    frames = [load_month(m) for m in months]
    frames = [f for f in frames if f is not None and len(f) > 0]
    if not frames: return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    if "dt" in df.columns:
        df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
    return df
