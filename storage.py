"""
storage.py — GitHub-backed persistent storage for Streamlit Cloud.
Falls back to local parquet files when GitHub secrets are not configured.
"""
import os
import io
import base64
import pandas as pd
import streamlit as st

# ── GitHub config ─────────────────────────────────────────────
def _gh_config():
    try:
        token  = st.secrets["github"]["token"]
        repo   = st.secrets["github"]["repo"]
        branch = st.secrets["github"].get("branch", "main")
        return token, repo, branch
    except Exception:
        return None, None, "main"

def _github_enabled() -> bool:
    token, repo, _ = _gh_config()
    return bool(token and repo)

def _headers():
    token, _, _ = _gh_config()
    if not token:
        return {}
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

def _api_url(month: str) -> str:
    _, repo, branch = _gh_config()
    return f"https://api.github.com/repos/{repo}/contents/data/{month}.csv"

def _file_url(month: str) -> str:
    _, repo, branch = _gh_config()
    return f"https://api.github.com/repos/{repo}/contents/data/{month}.csv?ref={branch}"

# ── Local fallback ────────────────────────────────────────────
_LOCAL_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(_LOCAL_DIR, exist_ok=True)

def _local_path(m):
    return os.path.join(_LOCAL_DIR, f"{m}.parquet")

# ── Bool columns to restore after CSV round-trip ──────────────
_BOOL_COLS = ["both_conn","cust_only","agt_only","none_conn",
              "blank_hu","cust_conn","agt_conn","is_anomaly"]

# ── SAVE ──────────────────────────────────────────────────────
def save_month(month: str, df: pd.DataFrame):
    """Save month data. Returns True on success, False on failure."""
    if df is None or df.empty:
        st.error("No data to save.")
        return False

    if _github_enabled():
        return _save_github(month, df)
    else:
        try:
            df.to_parquet(_local_path(month), index=False)
            return True
        except Exception as e:
            st.error(f"Local save failed: {e}")
            return False

def _get_sha(month: str):
    """Get SHA of existing file on GitHub (needed for updates)."""
    import requests
    try:
        r = requests.get(_file_url(month), headers=_headers(), timeout=15)
        if r.status_code == 200:
            return r.json().get("sha")
    except Exception:
        pass
    return None

def _save_github(month: str, df: pd.DataFrame) -> bool:
    import requests

    # Serialize to CSV
    csv_str     = df.to_csv(index=False)
    csv_bytes   = csv_str.encode("utf-8")
    size_mb     = len(csv_bytes) / (1024 * 1024)

    if size_mb > 90:
        st.error(f"File too large ({size_mb:.1f} MB). GitHub limit is ~90 MB.")
        return False

    content_b64 = base64.b64encode(csv_bytes).decode("utf-8")

    # Need SHA if file already exists
    sha = _get_sha(month)

    payload = {
        "message": f"data: save {month} ({len(df):,} rows)",
        "content": content_b64,
        "branch":  _gh_config()[2],
    }
    if sha:
        payload["sha"] = sha

    try:
        r = requests.put(
            _api_url(month),
            headers=_headers(),
            json=payload,
            timeout=90,
        )
        if r.status_code in (200, 201):
            # Clear caches
            try:
                _cached_load.clear()
                _list_months_cached.clear()
            except Exception:
                pass
            return True
        else:
            msg = ""
            try:
                msg = r.json().get("message", "")
            except Exception:
                msg = r.text[:200]
            st.error(f"GitHub save failed ({r.status_code}): {msg}")
            return False
    except requests.exceptions.Timeout:
        st.error("GitHub save timed out. File may be too large. Try uploading one month at a time.")
        return False
    except Exception as e:
        st.error(f"GitHub save error: {e}")
        return False

# ── LOAD ──────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _cached_load(month: str) -> pd.DataFrame | None:
    if _github_enabled():
        return _load_github(month)
    else:
        p = _local_path(month)
        if not os.path.exists(p):
            return None
        try:
            df = pd.read_parquet(p)
            if "dt" in df.columns:
                df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
            return df
        except Exception as e:
            st.warning(f"Could not load local file {month}: {e}")
            return None

def _load_github(month: str) -> pd.DataFrame | None:
    import requests
    try:
        r = requests.get(_file_url(month), headers=_headers(), timeout=30)
        if r.status_code != 200:
            return None

        data = r.json()
        raw_b64 = data.get("content", "")

        # GitHub inserts \n every 60 chars — must strip before decode
        raw_b64 = "".join(raw_b64.split())

        if not raw_b64:
            return None

        csv_bytes = base64.b64decode(raw_b64)
        csv_str   = csv_bytes.decode("utf-8").strip()

        if not csv_str:
            return None

        df = pd.read_csv(io.StringIO(csv_str), low_memory=False)

        if df.empty or len(df.columns) == 0:
            return None

        # Restore datetime
        if "dt" in df.columns:
            df["dt"] = pd.to_datetime(df["dt"], errors="coerce")

        # Restore bool columns (CSV saves them as True/False strings or 0/1)
        for col in _BOOL_COLS:
            if col in df.columns:
                df[col] = df[col].map(
                    lambda v: str(v).strip().lower() in ("true","1","yes")
                ).astype(bool)

        # Restore numeric columns that may have been stringified
        for col in ["slot","hour","minute"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    except pd.errors.EmptyDataError:
        return None
    except Exception as e:
        st.warning(f"Could not load {month} from GitHub: {e}")
        return None

def load_month(month: str) -> pd.DataFrame | None:
    return _cached_load(month)

# ── LIST ──────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def _list_months_cached() -> list[str]:
    if _github_enabled():
        return _list_github()
    else:
        if not os.path.exists(_LOCAL_DIR):
            return []
        return sorted(
            f[:-8] for f in os.listdir(_LOCAL_DIR) if f.endswith(".parquet")
        )

def list_months() -> list[str]:
    return _list_months_cached()

def _list_github() -> list[str]:
    import requests
    _, repo, branch = _gh_config()
    url = f"https://api.github.com/repos/{repo}/contents/data?ref={branch}"
    try:
        r = requests.get(url, headers=_headers(), timeout=15)
        if r.status_code == 200:
            files = r.json()
            if isinstance(files, list):
                return sorted(
                    f["name"].replace(".csv", "")
                    for f in files
                    if isinstance(f, dict) and f.get("name","").endswith(".csv")
                    and f.get("size", 0) > 0   # skip empty files
                )
    except Exception:
        pass
    return []

# ── DELETE ────────────────────────────────────────────────────
def delete_month(month: str):
    if _github_enabled():
        _delete_github(month)
    else:
        p = _local_path(month)
        if os.path.exists(p):
            os.remove(p)

def _delete_github(month: str):
    import requests
    sha = _get_sha(month)
    if not sha:
        return
    payload = {
        "message": f"data: delete {month}",
        "sha":     sha,
        "branch":  _gh_config()[2],
    }
    try:
        requests.delete(_api_url(month), headers=_headers(), json=payload, timeout=15)
        try:
            _cached_load.clear()
            _list_months_cached.clear()
        except Exception:
            pass
    except Exception as e:
        st.warning(f"Could not delete {month}: {e}")

# ── LOAD MULTIPLE ─────────────────────────────────────────────
def load_selected(months: list[str]) -> pd.DataFrame:
    frames = []
    for m in months:
        df = load_month(m)
        if df is not None and not df.empty and len(df.columns) > 0:
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    if "dt" in result.columns:
        result["dt"] = pd.to_datetime(result["dt"], errors="coerce")
    return result
