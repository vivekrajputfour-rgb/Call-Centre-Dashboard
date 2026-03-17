"""storage.py — persistent monthly parquet files"""
import os, pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def _p(m): return os.path.join(DATA_DIR, f"{m}.parquet")

def save_month(month: str, df: pd.DataFrame):
    df.to_parquet(_p(month), index=False)

def load_month(month: str) -> pd.DataFrame | None:
    if not os.path.exists(_p(month)): return None
    df = pd.read_parquet(_p(month))
    if "dt" in df.columns:
        df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
    return df

def list_months() -> list[str]:
    return sorted(f[:-8] for f in os.listdir(DATA_DIR) if f.endswith(".parquet"))

def delete_month(m: str):
    if os.path.exists(_p(m)): os.remove(_p(m))

def load_selected(months: list[str]) -> pd.DataFrame:
    frames = [load_month(m) for m in months]
    frames = [f for f in frames if f is not None and len(f) > 0]
    if not frames: return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    if "dt" in df.columns:
        df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
    return df
