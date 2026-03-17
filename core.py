"""
core.py — Data engine for Call Centre Intelligence Dashboard
Matches every sheet/column in the Excel report exactly.
Date format: M/D/YYYY H:MM:SS AM/PM  e.g. "2/22/2026 11:24:24 AM"
"""
import re, math
from datetime import datetime
import numpy as np
import pandas as pd

# ── Constants ─────────────────────────────────────────────────
SALARY_BASE  = 35_000
N_SLOTS      = 96  # 96 × 15-min slots
CONN_VALS    = {"connected","yes","true","1","answered","active"}
DIR_MAP      = {"outbound":"outgoing","inbound":"incoming"}
BLANK_HU     = {"nan","","na","n/a","none","undefined","null","-"}
THRESHOLDS   = [10, 15, 20]   # minutes
DOW_ORDER    = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# ── 15-min slot helpers ───────────────────────────────────────
def slot_idx(h: int, m: int) -> int:
    return h * 4 + m // 15

def _fmt12(h, m):
    ap = "AM" if h < 12 else "PM"
    h12 = 12 if h == 0 else (h - 12 if h > 12 else h)
    return f"{h12}:{m:02d} {ap}"

def slot_label(i: int) -> str:
    """'10:30 AM'"""
    h, q = divmod(i, 4)
    return _fmt12(h, q * 15)

def slot_range(i: int) -> str:
    """'10:30 AM – 10:45 AM'"""
    h, q = divmod(i, 4)
    s = _fmt12(h, q * 15)
    em = h * 60 + q * 15 + 15
    eh, emm = divmod(em % (24 * 60), 60)
    e = _fmt12(eh, emm)
    return f"{s} – {e}"

SLOT_LABELS = [slot_label(i) for i in range(N_SLOTS)]

# ── Duration formatting ───────────────────────────────────────
def fmt_dur(sec) -> str:
    if sec is None or (isinstance(sec, float) and math.isnan(sec)):
        return "N/A"
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def fmt_hm(sec) -> str:
    """For display: '1h 4m' or '45s'"""
    if sec is None or (isinstance(sec, float) and math.isnan(sec)):
        return "N/A"
    sec = int(sec)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    if h: return f"{h}h {m}m"
    if m: return f"{m}m {s}s"
    return f"{s}s"

def pct(n, d): return round(100 * n / d, 1) if d else 0.0

# ── Date parser ───────────────────────────────────────────────
_R1 = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s*(AM|PM)$', re.I)
_R2 = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})$')
_R3 = re.compile(r'^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2}):(\d{2})')

def parse_dt(raw) -> datetime | None:
    if raw is None: return None
    if isinstance(raw, (datetime, pd.Timestamp)):
        d = raw.to_pydatetime() if hasattr(raw, 'to_pydatetime') else raw
        return d if 2000 <= d.year <= 2100 else None
    s = str(raw).strip()
    if not s or s.lower() in ("nan", "none", "null", ""): return None
    mo = dy = yr = hh = mm = ss = None
    m = _R1.match(s)
    if m:
        mo,dy,yr,hh,mm,ss = (int(x) for x in m.groups()[:6])
        mer = m.group(7).upper()
        if mer == "PM" and hh != 12: hh += 12
        if mer == "AM" and hh == 12: hh = 0
    if mo is None:
        m = _R2.match(s)
        if m: mo,dy,yr,hh,mm,ss = (int(x) for x in m.groups())
    if mo is None:
        m = _R3.match(s)
        if m: yr,mo,dy,hh,mm,ss = (int(x) for x in m.groups())
    if mo is None or not (2000 <= yr <= 2100): return None
    try:
        return datetime(yr, mo, dy, hh or 0, mm or 0, ss or 0)
    except ValueError:
        return None

# ── Duration parser ───────────────────────────────────────────
def parse_dur(val) -> float | None:
    if val is None: return None
    if isinstance(val, (int, float)):
        if math.isnan(float(val)): return None
        n = float(val)
        return round(n * 86400) if 0 < n < 1 else n
    if isinstance(val, pd.Timedelta):
        return val.total_seconds()
    s = str(val).strip()
    if not s or s.lower() in ("nan","none",""): return None
    p = s.split(":")
    try:
        if len(p) == 3: return int(p[0])*3600 + int(p[1])*60 + float(p[2])
        if len(p) == 2: return int(p[0])*60 + float(p[1])
        n = float(s)
        return round(n*86400) if 0 < n < 1 else n
    except: return None

# ── Column lookup ─────────────────────────────────────────────
_COLS = {
    "raw_dt":    ["Date and Time","datetime","Date Time","DATE AND TIME"],
    "direction": ["Call Direction","direction","CALL DIRECTION"],
    "status":    ["Call Status","status","CALL STATUS"],
    "cust_st":   ["Customer Status","cust_status","CUSTOMER STATUS"],
    "agt_st":    ["Agent Status","agent_status","AGENT STATUS"],
    "agent":     ["Agent Name","agent_name","AGENT NAME"],
    "customer":  ["Customer","customer","CUSTOMER"],
    "uuid":      ["Call UUID","call_uuid","CALL UUID"],
    "talk":      ["Talk Time (hh:mm:ss)","talk_raw","Talk Time"],
    "dur":       ["Total Call Duration (hh:mm:ss)","dur_raw","Total Duration"],
    "wait":      ["Wait time in Queue","wait_raw","Wait Time"],
    "hold":      ["Hold Time (hh:mm:ss)","hold_raw","Hold Time"],
    "aasa":      ["AASA(Transfer Time)","aasa_raw","AASA"],
    "hangup":    ["Hangup By","hangup_by","HANGUP BY"],
    "disp":      ["Disposition","disposition","DISPOSITION"],
    "sub_disp":  ["Sub Disposition","sub_disposition"],
    "sr":        ["Sr Number","sr_number"],
    "solution":  ["Solution","solution"],
    "device":    ["Device","device"],
    "credits":   ["Credits Deducted","credits"],
    "follow_up": ["Follow Up Date","follow_up"],
    "queue":     ["Queue","queue"],
    "campaign":  ["Campaign ID","campaign_id"],
    "ivr":       ["IVR ID","ivr_id"],
    "notes":     ["Notes","notes"],
    "agt_num":   ["Agent Number","agent_number"],
}

def _gcol(df: pd.DataFrame, key: str) -> pd.Series:
    cl = {c.strip().lower(): c for c in df.columns}
    for alias in _COLS.get(key, []):
        if alias.strip().lower() in cl:
            return df[cl[alias.strip().lower()]]
    return pd.Series([""] * len(df), index=df.index)

# ── Main parser ───────────────────────────────────────────────
def parse_dataframe(raw: pd.DataFrame) -> pd.DataFrame:
    raw = raw.copy()
    raw.columns = raw.columns.str.strip()

    # Parse datetimes
    dt_s = _gcol(raw, "raw_dt").apply(parse_dt)
    hour   = dt_s.apply(lambda d: d.hour   if d else None)
    minute = dt_s.apply(lambda d: d.minute if d else None)
    slot   = hour.combine(minute, lambda h, m: slot_idx(int(h), int(m)) if h is not None else None)
    dow    = dt_s.apply(lambda d: d.strftime("%A") if d else None)
    month  = dt_s.apply(lambda d: d.strftime("%Y-%m") if d else None)

    # Direction
    dir_raw   = _gcol(raw, "direction").astype(str).str.strip().str.lower()
    direction = dir_raw.map(lambda x: DIR_MAP.get(x, x))

    # Status
    status = _gcol(raw, "status").astype(str).str.strip().str.lower()

    # Connection
    cust_s = _gcol(raw, "cust_st").astype(str).str.strip().str.lower()
    agt_s  = _gcol(raw, "agt_st").astype(str).str.strip().str.lower()
    cC = cust_s.isin(CONN_VALS)
    aC = agt_s.isin(CONN_VALS)

    # Hangup
    hu      = _gcol(raw, "hangup").astype(str).str.strip().str.lower()
    blankhu = hu.isin(BLANK_HU)

    # Disposition
    disp = _gcol(raw, "disp").astype(str).str.strip().str.lower().replace("", "nan")

    df = pd.DataFrame({
        "dt":          dt_s,
        "hour":        hour,
        "minute":      minute,
        "slot":        slot,
        "dow":         dow,
        "month":       month,
        "direction":   direction,
        "status":      status,
        "agent_name":  _gcol(raw,"agent").astype(str).str.strip().replace("","Unknown"),
        "customer":    _gcol(raw,"customer").astype(str).str.strip(),
        "call_uuid":   _gcol(raw,"uuid").astype(str).str.strip(),
        "talk_sec":    _gcol(raw,"talk").apply(parse_dur),
        "dur_sec":     _gcol(raw,"dur").apply(parse_dur),
        "wait_sec":    _gcol(raw,"wait").apply(parse_dur),
        "hold_sec":    _gcol(raw,"hold").apply(parse_dur),
        "aasa_sec":    _gcol(raw,"aasa").apply(parse_dur),
        "cust_conn":   cC,
        "agt_conn":    aC,
        "both_conn":   cC & aC,
        "cust_only":   cC & ~aC,
        "agt_only":    ~cC & aC,
        "none_conn":   ~cC & ~aC,
        "hangup_by":   hu,
        "blank_hu":    blankhu,
        "disposition": disp,
        "sub_disp":    _gcol(raw,"sub_disp").astype(str).str.strip(),
        "sr_number":   _gcol(raw,"sr").astype(str).str.strip(),
        "solution":    _gcol(raw,"solution").astype(str).str.strip(),
        "device":      _gcol(raw,"device").astype(str).str.strip(),
        "credits":     pd.to_numeric(_gcol(raw,"credits"), errors="coerce"),
        "notes":       _gcol(raw,"notes").astype(str).str.strip(),
        "queue":       _gcol(raw,"queue").astype(str).str.strip(),
        "follow_up":   _gcol(raw,"follow_up").astype(str).str.strip(),
        "agt_number":  _gcol(raw,"agt_num").astype(str).str.strip(),
    })
    return df

# ── Anomaly detection (matching code exactly) ─────────────────
def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    reasons = [[] for _ in range(len(df))]
    idx = list(range(len(df)))

    def flag(mask_arr, msg):
        for i, v in enumerate(mask_arr):
            if v: reasons[i].append(msg)

    tk = df["talk_sec"].fillna(0)
    dr = df["dur_sec"].fillna(0)
    hd = df["hold_sec"].fillna(0)
    st = df["status"]

    flag((df["talk_sec"].notna() & df["dur_sec"].notna() & (df["talk_sec"] > df["dur_sec"] + 5)).tolist(),
         "DURATION: Talk time exceeds total call duration")
    flag(((hd + tk) > dr + 30).tolist(),
         "DURATION: Talk + Hold > Total duration (>30s slack)")
    flag((df["hold_sec"].notna() & df["dur_sec"].notna() & (df["hold_sec"] > df["dur_sec"] + 5)).tolist(),
         "DURATION: Hold time exceeds total call duration")
    flag((df["dur_sec"].notna() & (df["dur_sec"] > 10800)).tolist(),
         "DURATION: Extremely long call (>3 hours)")
    flag((df["dur_sec"].notna() & (df["dur_sec"] > 0) & (df["dur_sec"] < 3) & st.eq("answered")).tolist(),
         "DURATION: Answered call with <3s total duration (phantom answer)")
    # Removed: phantom answer <5s (valid calls for this call centre)
    flag((st.isin(["missed","unanswered","abandoned"]) & (tk > 5)).tolist(),
         "TALK: Missed/Unanswered call but has talk time recorded")
    flag((st.eq("answered") & (tk == 0) & (dr > 30)).tolist(),
         "TALK: Answered, zero talk time but duration >30s (silent call?)")
    flag((~df["both_conn"] & (tk > 30)).tolist(),
         "CONNECTION: Talk time >30s but customer/agent not both connected")
    flag((df["cust_conn"] & ~df["agt_conn"] & st.eq("answered")).tolist(),
         "CONNECTION: Customer connected but agent not connected on answered call")
    flag((st.eq("answered") & df["blank_hu"]).tolist(),
         "HANGUP: Answered call with blank Hangup By (possible network drop)")
    flag((df["wait_sec"].notna() & (df["wait_sec"] > 60)).tolist(),
         "WAIT: Customer waited >1 minute in queue")
    flag((df["aasa_sec"].notna() & (df["aasa_sec"] > 60)).tolist(),
         "AASA: Agent answer time >1 minute")
    now = pd.Timestamp.now()
    flag((df["dt"].notna() & df["dt"].apply(lambda d: pd.Timestamp(d) > now if d else False)).tolist(),
         "DATETIME: Call timestamp is in the future")
    flag(df["dt"].isna().tolist(),
         "DATETIME: Missing/unparseable timestamp")
    # Removed: weekend check (call centre operates Sat/Sun)

    df["anomaly_reasons"] = [" | ".join(r) if r else "" for r in reasons]
    df["is_anomaly"] = [bool(r) for r in reasons]
    return df

# ── Slot arrays ───────────────────────────────────────────────
def build_slot_arrays(df: pd.DataFrame):
    si  = np.zeros(N_SLOTS, int)
    so  = np.zeros(N_SLOTS, int)
    sai = np.zeros(N_SLOTS, int)
    sao = np.zeros(N_SLOTS, int)
    mask = df["slot"].notna() & (df["slot"] >= 0) & (df["slot"] < N_SLOTS)
    sub = df[mask]
    for _, r in sub.iterrows():
        s = int(r["slot"])
        if r["direction"] == "incoming":
            si[s] += 1
            if r["status"] == "answered": sai[s] += 1
        elif r["direction"] == "outgoing":
            so[s] += 1
            if r["status"] == "answered": sao[s] += 1
    return si, so, sai, sao

# ── Summary KPIs ──────────────────────────────────────────────
def summary_kpis(df: pd.DataFrame) -> dict:
    bc   = df[df["both_conn"]]
    n    = len(df)
    ans  = int(df["status"].eq("answered").sum())
    miss = int(df["status"].isin(["missed","unanswered"]).sum())
    aban = int(df["status"].eq("abandoned").sum())
    inc  = int(df["direction"].eq("incoming").sum())
    out  = int(df["direction"].eq("outgoing").sum())
    inc_bc = bc[bc["direction"]=="incoming"]
    out_bc = bc[bc["direction"]=="outgoing"]
    at   = bc["talk_sec"].dropna().mean()
    at_i = inc_bc["talk_sec"].dropna().mean()
    at_o = out_bc["talk_sec"].dropna().mean()
    anom = int(df["is_anomaly"].sum()) if "is_anomaly" in df.columns else 0
    fu   = int(df["follow_up"].notna().sum()) if "follow_up" in df.columns else 0
    return dict(
        total=n, ans=ans, miss=miss, aban=aban,
        ans_rate=pct(ans,n), inc=inc, out=out, bc=len(bc),
        avg_talk=float(at) if not math.isnan(float(at or 0)) else None,
        avg_talk_inc=float(at_i) if not math.isnan(float(at_i or 0)) else None,
        avg_talk_out=float(at_o) if not math.isnan(float(at_o or 0)) else None,
        avg_dur=float(df["dur_sec"].dropna().mean()) if df["dur_sec"].notna().any() else None,
        avg_hold=float(df["hold_sec"].dropna().mean()) if df["hold_sec"].notna().any() else None,
        avg_wait=float(df["wait_sec"].dropna().mean()) if df["wait_sec"].notna().any() else None,
        avg_aasa=float(df["aasa_sec"].dropna().mean()) if df["aasa_sec"].notna().any() else None,
        t10=int((bc["talk_sec"]>=600).sum()),
        t15=int((bc["talk_sec"]>=900).sum()),
        t20=int((bc["talk_sec"]>=1200).sum()),
        follow_up=fu, anomalies=anom,
        long15=int((bc["talk_sec"]>=900).sum()),
        long20=int((bc["talk_sec"]>=1200).sum()),
    )

# ── Direction stats ───────────────────────────────────────────
def dir_stats(sub: pd.DataFrame) -> dict:
    bc  = sub[sub["both_conn"]]
    bl  = sub[sub["blank_hu"]]
    n   = len(sub)
    ans = int(sub["status"].eq("answered").sum())
    ms  = int(sub["status"].isin(["missed","unanswered"]).sum())
    ab  = int(sub["status"].eq("abandoned").sum())
    sm  = lambda s: float(s.dropna().mean()) if s.notna().any() else None
    d = dict(
        total=n, ans=ans, miss=ms, aban=ab,
        ans_rate=pct(ans,n), miss_rate=pct(ms,n), aban_rate=pct(ab,n),
        avg_talk=sm(bc["talk_sec"]), avg_wait=sm(sub["wait_sec"]),
        avg_hold=sm(sub["hold_sec"]), avg_aasa=sm(sub["aasa_sec"]),
        blank_hu=len(bl), blank_hu_rate=pct(len(bl),n),
    )
    for t in THRESHOLDS:
        d[f"t{t}"] = int((bc["talk_sec"] >= t*60).sum())
    return d

# ── Connection status table ───────────────────────────────────
def connection_table(df: pd.DataFrame):
    n = len(df)
    cats = [
        ("Both Connected",                "both_conn"),
        ("Customer Connected, Agent Not", "cust_only"),
        ("Agent Connected, Customer Not", "agt_only"),
        ("Neither Connected",             "none_conn"),
    ]
    rows = []
    for lbl, col in cats:
        if col not in df.columns: continue
        cnt = int(df[col].sum())
        sub = df[df[col]]
        at  = sub["talk_sec"].dropna().mean()
        ad  = sub["dur_sec"].dropna().mean()
        rows.append({"Connection State":lbl,"Call Count":cnt,"% of Total":pct(cnt,n),
                     "Avg Talk":fmt_dur(at),"Avg Duration":fmt_dur(ad)})
    # Detail by direction
    detail = []
    for lbl, col in cats:
        if col not in df.columns: continue
        sub = df[df[col]]
        for d in ["incoming","outgoing"]:
            g = sub[sub["direction"]==d]
            dt = int(df["direction"].eq(d).sum())
            at = g["talk_sec"].dropna().mean()
            detail.append({"Connection State":lbl,"Direction":d.title(),
                           "Count":len(g),"% of Direction":pct(len(g),dt),
                           "Avg Talk":fmt_dur(at)})
    return pd.DataFrame(rows), pd.DataFrame(detail)

# ── Agent stats ───────────────────────────────────────────────
def agent_stats(df: pd.DataFrame) -> tuple:
    """Returns (all_df, inc_df, out_df) matching Excel report exactly."""
    def _build(sub, label):
        bc  = sub[sub["both_conn"]]
        n   = len(sub)
        ans = int(sub["status"].eq("answered").sum())
        at  = bc["talk_sec"].dropna().mean()
        tt  = float(bc["talk_sec"].dropna().sum())
        return {
            "Agent Name":       label,
            "Total Calls":      n,
            "Answered":         ans,
            "Answer Rate %":    pct(ans,n),
            "Avg Talk (both conn.)": fmt_dur(at),
            "Total Talk Time":  fmt_dur(tt),
            "Total Talk (hrs)": round(tt/3600,2),
            "Avg Hold":         fmt_dur(sub["hold_sec"].dropna().mean()),
            "Avg Wait":         fmt_dur(sub["wait_sec"].dropna().mean()),
            "Avg AASA":         fmt_dur(sub["aasa_sec"].dropna().mean()),
            "Both Connected":   len(bc),
            "Both Connected %": pct(len(bc),n),
            "Talk>=10m":        int((bc["talk_sec"]>=600).sum()),
            "Talk>=15m":        int((bc["talk_sec"]>=900).sum()),
            "Talk>=20m":        int((bc["talk_sec"]>=1200).sum()),
            "Hangup Blank":     int(sub["blank_hu"].sum()),
            # raw for scoring
            "_ans":      ans,
            "_ans_rate": pct(ans,n),
            "_conn_pct": pct(len(bc),n),
            "_t15":      int((bc["talk_sec"]>=900).sum()),
            "_avg_talk_sec": float(bc["talk_sec"].dropna().mean()) if bc["talk_sec"].notna().any() else 0,
        }

    all_rows, inc_rows, out_rows = [], [], []
    for agent, g in df.groupby("agent_name"):
        all_rows.append(_build(g, agent))
        gi = g[g["direction"]=="incoming"]
        if len(gi): inc_rows.append(_build(gi, agent))
        go = g[g["direction"]=="outgoing"]
        if len(go): out_rows.append(_build(go, agent))

    def to_df(rows):
        if not rows: return pd.DataFrame()
        return pd.DataFrame(rows).sort_values("Total Calls",ascending=False).reset_index(drop=True)

    return to_df(all_rows), to_df(inc_rows), to_df(out_rows)

# ── Agent scoring ─────────────────────────────────────────────
def score_agents(agt_all: pd.DataFrame) -> pd.DataFrame:
    """
    Score each agent 0-100. Justified salary is DIRECTLY proportional
    to the score — every point difference produces a different salary.

    Formula: Justified Salary = Score/100 * SALARY_BASE
    So score 80 → ₹28,000 | score 50 → ₹17,500 | score 20 → ₹7,000

    Components (all relative to top performer so spread is maximised):
      35% — Volume: answered / max_answered * 100
      25% — Answer rate % (absolute)
      20% — Both-connected % (absolute)
      15% — Avg talk time (closeness to 15 min ideal)
      5%  — Long calls >=15m (answered, normalised)
    """
    if agt_all.empty: return pd.DataFrame()
    df = agt_all.copy()

    max_ans  = max(df["_ans"].max(), 1)
    max_t15  = max(df["_t15"].max(), 1)

    # 1. Volume score — relative to best agent (0-100)
    vol_score = (df["_ans"] / max_ans * 100).clip(0, 100)

    # 2. Answer rate % — absolute (0-100)
    ans_score = df["_ans_rate"].clip(0, 100)

    # 3. Both-connected % — absolute (0-100)
    conn_score = df["_conn_pct"].clip(0, 100)

    # 4. Talk time — closeness to 15 min ideal (0-100)
    ideal = 15 * 60
    talk_score = df["_avg_talk_sec"].apply(
        lambda s: max(0, 100 - abs(s - ideal) / ideal * 100) if s and s > 0 else 0)

    # 5. Long calls rate — relative (0-100)
    long_score = (df["_t15"] / max_t15 * 100).clip(0, 100)

    # ── Weighted Score 0-100 ──────────────────────────────────────
    df["Score"] = (
        vol_score  * 0.35 +
        ans_score  * 0.25 +
        conn_score * 0.20 +
        talk_score * 0.15 +
        long_score * 0.05
    ).round(1)

    # ── Justified salary = Score% of base salary (fully proportional) ──
    # Every agent gets a UNIQUE salary based on their exact score
    # Score 100 → ₹35,000 | Score 50 → ₹17,500 | Score 10 → ₹3,500
    df["Justified Salary (₹)"] = (df["Score"] / 100 * SALARY_BASE).round(0).astype(int)
    df["Salary Gap (₹)"]       = SALARY_BASE - df["Justified Salary (₹)"]
    df["Salary Multiplier"]    = (df["Score"] / 100).round(2)

    def rating(s):
        if s >= 80: return "Fully Justified"
        if s >= 65: return "Mostly Justified"
        if s >= 50: return "Partially Justified"
        return "Needs Improvement"

    df["Rating"] = df["Score"].apply(rating)
    df["Rank"]   = df["Score"].rank(ascending=False, method="min").astype(int)

    cols = ["Rank","Agent Name","Score","Rating","Answered","Answer Rate %",
            "Avg Talk (both conn.)","Total Talk Time","Total Talk (hrs)",
            "Talk>=15m","Both Connected %","Justified Salary (₹)","Salary Gap (₹)","Salary Multiplier"]
    cols = [c for c in cols if c in df.columns]
    return df[cols].sort_values("Rank").reset_index(drop=True)

# ── AASA analysis ─────────────────────────────────────────────
def aasa_analysis(df: pd.DataFrame):
    n    = len(df)
    bins = [0,5,10,20,30,60,120,300,99999]
    lbls = ["<5s","5-10s","10-20s","20-30s","30-60s","1-2min","2-5min",">5min"]
    df2  = df.copy()
    df2["aasa_bucket"] = pd.cut(df2["aasa_sec"],bins=bins,labels=lbls,right=False)
    bkt  = df2["aasa_bucket"].value_counts().reindex(lbls,fill_value=0).reset_index()
    bkt.columns = ["AASA Bucket","Count"]
    bkt["% of Total"]   = bkt["Count"].apply(lambda x: pct(x,n))
    bkt["Cumulative %"] = bkt["% of Total"].cumsum().round(1)

    agt = df.groupby("agent_name")["aasa_sec"].agg(
        Count="count", Mean="mean", Median="median", Min="min", Max="max"
    ).reset_index()
    agt.columns = ["Agent","AASA Count","Avg AASA (s)","Median AASA (s)","Min AASA (s)","Max AASA (s)"]
    for c in ["Avg AASA (s)","Median AASA (s)","Min AASA (s)","Max AASA (s)"]:
        agt[c] = agt[c].round(1)
    agt = agt.sort_values("Avg AASA (s)").reset_index(drop=True)
    return bkt, agt

# ── Long calls (UUID level) ───────────────────────────────────
def long_calls(df: pd.DataFrame):
    bc   = df[df["both_conn"]].copy()
    cols = [c for c in ["call_uuid","dt","direction","agent_name","customer",
                        "talk_sec","status","disposition","talk_min"] if c in bc.columns or c=="talk_min"]
    bc["talk_min"] = (bc["talk_sec"]/60).round(2)
    t15  = bc[bc["talk_sec"]>=900].sort_values("talk_sec",ascending=False)
    t20  = bc[bc["talk_sec"]>=1200].sort_values("talk_sec",ascending=False)
    show = [c for c in ["call_uuid","dt","direction","agent_name","customer",
                        "talk_sec","talk_min","status","disposition"] if c in bc.columns]
    return t15[show].reset_index(drop=True), t20[show].reset_index(drop=True)

# ── Phone frequency ───────────────────────────────────────────
def phone_frequency(df: pd.DataFrame):
    rows = []
    for ph, g in df.groupby("customer"):
        if not ph or ph in ("nan","None",""): continue
        rows.append({
            "Phone Number":      ph,
            "Total Contacts":    len(g),
            "Incoming Calls":    int((g["direction"]=="incoming").sum()),
            "Incoming Answered": int(((g["direction"]=="incoming")&(g["status"]=="answered")).sum()),
            "Outgoing Calls":    int((g["direction"]=="outgoing").sum()),
            "Outgoing Answered": int(((g["direction"]=="outgoing")&(g["status"]=="answered")).sum()),
            "Avg Talk (s)":      round(float(g["talk_sec"].dropna().mean()),1) if g["talk_sec"].notna().any() else "N/A",
        })
    all_df  = pd.DataFrame(rows).sort_values("Total Contacts",ascending=False).reset_index(drop=True)
    high_df = all_df[all_df["Total Contacts"]>10].reset_index(drop=True)
    return all_df, high_df

# ── Hourly volume table ───────────────────────────────────────
def hourly_volume(df: pd.DataFrame) -> pd.DataFrame:
    hours = list(range(24))
    inc = df[df["direction"]=="incoming"].groupby("hour").size()
    out = df[df["direction"]=="outgoing"].groupby("hour").size()
    res = pd.DataFrame({"Hour (24h)":hours,
                        "Incoming":[int(inc.get(h,0)) for h in hours],
                        "Outgoing":[int(out.get(h,0)) for h in hours]})
    res["Total"] = res["Incoming"] + res["Outgoing"]
    return res

# ── Answered hourly (15-min slot arrays) ─────────────────────
def answered_hourly(df: pd.DataFrame):
    _, _, sai, sao = build_slot_arrays(df)
    inc_rows = [{"Time Slot":slot_range(i),"Slot Label":slot_label(i),
                 "Answered Incoming":int(sai[i])} for i in range(N_SLOTS)]
    out_rows = [{"Time Slot":slot_range(i),"Slot Label":slot_label(i),
                 "Answered Outgoing":int(sao[i])} for i in range(N_SLOTS)]
    return pd.DataFrame(inc_rows), pd.DataFrame(out_rows), sai, sao

# ── DOW table ─────────────────────────────────────────────────
def dow_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("dow").size().reindex(DOW_ORDER, fill_value=0).reset_index()
    g.columns = ["Day","Total Calls"]
    return g

# ── Talk buckets ──────────────────────────────────────────────
def talk_buckets(df: pd.DataFrame) -> pd.DataFrame:
    bc   = df[df["both_conn"]]
    bins = [0,60,300,600,900,1200,3600,99999]
    lbls = ["<1 min","1-5 min","5-10 min","10-15 min","15-20 min","20-60 min",">60 min"]
    bc2  = bc.copy()
    bc2["bucket"] = pd.cut(bc2["talk_sec"],bins=bins,labels=lbls,right=False)
    g = bc2["bucket"].value_counts().reindex(lbls,fill_value=0).reset_index()
    g.columns = ["Talk Time Bucket","Count"]
    g["% of Both-Connected"] = g["Count"].apply(lambda x: pct(x,len(bc)))
    return g

# ── Disposition breakdown ─────────────────────────────────────
def disposition_table(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("disposition").size().sort_values(ascending=False).reset_index()
    g.columns = ["Disposition","Count"]
    g["% of Total"] = g["Count"].apply(lambda x: pct(x,len(df)))
    return g

# ── Network issues ────────────────────────────────────────────
def network_table(df: pd.DataFrame) -> pd.DataFrame:
    n    = len(df)
    bl   = df[df["blank_hu"]]
    rows = [
        {"Metric":"Total blank Hangup By",    "Value":len(bl),              "% of Total":pct(len(bl),n)},
        {"Metric":"  Answered + blank Hangup","Value":int((bl["status"]=="answered").sum()),   "% of Total":pct(int((bl["status"]=="answered").sum()),n)},
        {"Metric":"  Missed + blank Hangup",  "Value":int(bl["status"].isin(["missed","unanswered"]).sum()), "% of Total":pct(int(bl["status"].isin(["missed","unanswered"]).sum()),n)},
        {"Metric":"  Unanswered + blank Hangup","Value":int((bl["status"]=="unanswered").sum()),"% of Total":pct(int((bl["status"]=="unanswered").sum()),n)},
        {"Metric":"  Abandoned + blank Hangup","Value":int((bl["status"]=="abandoned").sum()),  "% of Total":pct(int((bl["status"]=="abandoned").sum()),n)},
        {"Metric":"  Incoming + blank Hangup", "Value":int((bl["direction"]=="incoming").sum()),"% of Total":pct(int((bl["direction"]=="incoming").sum()),n)},
        {"Metric":"  Outgoing + blank Hangup", "Value":int((bl["direction"]=="outgoing").sum()),"% of Total":pct(int((bl["direction"]=="outgoing").sum()),n)},
    ]
    return pd.DataFrame(rows)

# ── Anomaly summary ───────────────────────────────────────────
def anomaly_summary(df: pd.DataFrame):
    if "is_anomaly" not in df.columns: return pd.DataFrame(), pd.DataFrame()
    all_r = []
    for rs in df["anomaly_reasons"]:
        if rs:
            all_r.extend([r.strip() for r in rs.split("|") if r.strip()])
    rc = pd.Series(all_r).value_counts().reset_index()
    rc.columns = ["Anomaly Type","Count"]
    rc["% of All Calls"] = rc["Count"].apply(lambda x: pct(x,len(df)))

    anom_cols = [c for c in ["call_uuid","dt","direction","status","agent_name","customer",
                              "talk_sec","dur_sec","aasa_sec","hangup_by",
                              "cust_conn","agt_conn","anomaly_reasons"] if c in df.columns]
    anom_df = df[df["is_anomaly"]][anom_cols].copy().reset_index(drop=True)
    return rc, anom_df
