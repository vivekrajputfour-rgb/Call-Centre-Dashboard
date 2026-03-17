"""charts.py — All Plotly figures. Light premium theme."""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from core import SLOT_LABELS, N_SLOTS, slot_range, fmt_dur

# ── Palette ───────────────────────────────────────────────────
P = dict(coral="#e05c3a", blue="#2563eb", teal="#0d9488", amber="#d97706",
         green="#16a34a", red="#dc2626", purple="#7c3aed", orange="#ea580c", pink="#db2777")

BG   = "white"
PLOT = "#f9f8f5"
GRID = "rgba(0,0,0,0.06)"
FONT = dict(family="'Plus Jakarta Sans', sans-serif", size=12, color="#1a1714")
MARG = dict(l=55, r=30, t=45, b=50)

def _layout(**kw):
    return dict(paper_bgcolor=BG, plot_bgcolor=PLOT, font=FONT, margin=MARG,
                xaxis=dict(gridcolor=GRID, linecolor="#e8e3d8", showline=True),
                yaxis=dict(gridcolor=GRID, linecolor="#e8e3d8", showline=True),
                **kw)

def _apply(fig, height=320, **kw):
    fig.update_layout(**_layout(height=height, **kw))
    return fig

# ── Slot x-axis ticks (every 4th = hourly) ───────────────────
_TV = list(range(0, N_SLOTS, 4))
_TT = [SLOT_LABELS[i] for i in _TV]

# ── Status donut ──────────────────────────────────────────────
def status_donut(counts: dict):
    items = sorted(counts.items(), key=lambda x: -x[1])
    cols  = [P["green"],P["red"],P["amber"],P["blue"],P["purple"],P["orange"]]
    fig   = go.Figure(go.Pie(
        labels=[i[0] for i in items], values=[i[1] for i in items],
        hole=0.62, sort=False,
        marker=dict(colors=cols[:len(items)], line=dict(color="white",width=2)),
        textinfo="percent+label",
    ))
    fig.update_traces(textposition="outside", textfont_size=11)
    return _apply(fig, height=320, title="Call Status Distribution", showlegend=False)

# ── Slot two-line chart ───────────────────────────────────────
def slot_two_line(inc, out, title="All Calls Traffic — 15-min Slots"):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=SLOT_LABELS, y=list(inc), name="Incoming",
        mode="lines", line=dict(color=P["teal"],width=2),
        fill="tozeroy", fillcolor="rgba(13,148,136,0.08)"))
    fig.add_trace(go.Scatter(x=SLOT_LABELS, y=list(out), name="Outgoing",
        mode="lines", line=dict(color=P["blue"],width=2),
        fill="tozeroy", fillcolor="rgba(37,99,235,0.08)"))
    fig.update_xaxes(tickvals=_TV, ticktext=_TT, tickangle=45)
    fig.update_yaxes(rangemode="tozero")
    return _apply(fig, height=300, title=title,
        legend=dict(orientation="h", y=1.08, x=0))

# ── Single slot line (answered hourly) ───────────────────────
def slot_single(data, color, title):
    arr  = list(data)
    pi   = int(np.argmax(arr))
    pv   = arr[pi]
    fig  = go.Figure()
    fig.add_trace(go.Scatter(
        x=SLOT_LABELS, y=arr, mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=[7 if i==pi else 0 for i in range(N_SLOTS)], color=color),
        fill="tozeroy", fillcolor=color+"18"))
    if pv > 0:
        fig.add_annotation(x=SLOT_LABELS[pi], y=pv,
            text=f"<b>Peak</b><br>{slot_range(pi)}<br>{pv} calls",
            showarrow=True, arrowhead=2, arrowcolor=color,
            bgcolor="#fff3cd", bordercolor="#fbbf24", borderwidth=1,
            font=dict(size=11, color="#b45309"))
    fig.update_xaxes(tickvals=_TV, ticktext=_TT, tickangle=45)
    fig.update_yaxes(rangemode="tozero")
    return _apply(fig, height=300, title=title, showlegend=False)

# ── DOW bar ───────────────────────────────────────────────────
def dow_bar(dow_counts: dict):
    from core import DOW_ORDER
    vals = [dow_counts.get(d, 0) for d in DOW_ORDER]
    fig  = go.Figure(go.Bar(x=[d[:3] for d in DOW_ORDER], y=vals,
        marker_color=P["purple"], marker_line_width=0,
        text=vals, textposition="outside"))
    return _apply(fig, height=280, title="Calls by Day of Week")

# ── Monthly bar ───────────────────────────────────────────────
def monthly_bar(mc: dict):
    ms  = sorted(mc.keys())
    fig = go.Figure(go.Bar(x=ms, y=[mc[m] for m in ms],
        marker_color=P["coral"], marker_line_width=0,
        text=[mc[m] for m in ms], textposition="outside"))
    fig.update_xaxes(tickangle=45)
    return _apply(fig, height=280, title="Calls by Month")

# ── Heatmap hour×dow ─────────────────────────────────────────
def heatmap_hour_dow(df):
    import pandas as pd
    from core import DOW_ORDER
    mask = df["hour"].notna() & df["dow"].notna()
    sub  = df[mask]
    pivot = sub.groupby(["dow","hour"]).size().unstack(fill_value=0)
    pivot = pivot.reindex([d for d in DOW_ORDER if d in pivot.index])
    pivot = pivot.reindex(columns=range(24), fill_value=0)
    fig = go.Figure(go.Heatmap(
        z=pivot.values.tolist(),
        x=[f"{h:02d}:00" for h in range(24)],
        y=pivot.index.tolist(),
        colorscale="YlOrRd", showscale=True,
        text=pivot.values.tolist(), texttemplate="%{text}",
    ))
    fig.update_layout(**_layout(height=320, title="Call Volume — Hour × Day of Week"))
    return fig

# ── Direction grouped bar ─────────────────────────────────────
def dir_grouped(inc, out):
    cats = ["Total","Answered","Missed","Abandoned"]
    fig  = go.Figure()
    fig.add_trace(go.Bar(name="Incoming",x=cats,
        y=[inc["total"],inc["ans"],inc["miss"],inc["aban"]],marker_color=P["teal"]))
    fig.add_trace(go.Bar(name="Outgoing",x=cats,
        y=[out["total"],out["ans"],out["miss"],out["aban"]],marker_color=P["blue"]))
    return _apply(fig, height=300, title="Volume by Direction", barmode="group",
        legend=dict(orientation="h",y=1.08))

def ans_rate_bar(ir, orr):
    fig = go.Figure(go.Bar(
        x=["Incoming","Outgoing"], y=[ir,orr],
        marker_color=[P["teal"],P["blue"]],
        text=[f"{ir}%",f"{orr}%"], textposition="outside"))
    fig.update_yaxes(range=[0,115])
    return _apply(fig, height=280, title="Answer Rate %", showlegend=False)

# ── Connection donut ──────────────────────────────────────────
def conn_donut(both, cust, agt, none_):
    fig = go.Figure(go.Pie(
        labels=["Both Connected","Cust Only","Agent Only","Neither"],
        values=[both,cust,agt,none_], hole=0.58,
        marker=dict(colors=[P["green"],P["amber"],P["orange"],P["red"]],
                    line=dict(color="white",width=2)),
        textinfo="percent+label",
    ))
    fig.update_traces(textposition="outside", textfont_size=11)
    return _apply(fig, height=320, title="Connection State Breakdown", showlegend=False)

# ── Agent horizontal bars ─────────────────────────────────────
def agent_hbar(agents, vals, color, title):
    h = max(300, len(agents)*28+80)
    fig = go.Figure(go.Bar(
        y=agents[::-1], x=vals[::-1], orientation="h",
        marker_color=color, marker_line_width=0,
        text=[f"{v}" for v in vals[::-1]], textposition="outside"))
    return _apply(fig, height=h, title=title)

def agent_score_hbar(agents, scores, ratings):
    cmap = {"Fully Justified":P["green"],"Mostly Justified":P["blue"],
            "Partially Justified":P["amber"],"Needs Improvement":P["red"]}
    colors = [cmap.get(r,P["purple"]) for r in ratings]
    h = max(300, len(agents)*26+100)
    fig = go.Figure(go.Bar(
        y=agents[::-1], x=scores[::-1], orientation="h",
        marker_color=colors[::-1], marker_line_width=0,
        text=[f"{s:.1f}" for s in scores[::-1]], textposition="outside"))
    for xv, col, lbl in [(80,P["green"],"≥80 Fully"),(65,P["amber"],"≥65 Mostly"),(50,P["red"],"≥50 Partial")]:
        fig.add_vline(x=xv, line_dash="dash", line_color=col, annotation_text=lbl,
                      annotation_position="top right", annotation_font_size=10)
    fig.update_xaxes(range=[0,115])
    return _apply(fig, height=h, title="Agent Performance Scores (0–100)")

# ── AASA combo (bar + cumulative line) ────────────────────────
def aasa_combo(labels, counts, cum_pct):
    fig = make_subplots(specs=[[{"secondary_y":True}]])
    fig.add_trace(go.Bar(x=labels,y=counts,name="Count",
        marker_color=P["orange"],marker_line_width=0), secondary_y=False)
    fig.add_trace(go.Scatter(x=labels,y=cum_pct,name="Cumulative %",
        mode="lines+markers",line=dict(color=P["red"],width=2),
        marker=dict(size=7,color="white",line=dict(color=P["red"],width=2))),
        secondary_y=True)
    fig.update_yaxes(title_text="Count",secondary_y=False,gridcolor=GRID)
    fig.update_yaxes(title_text="Cumulative %",secondary_y=True,range=[0,110],gridcolor=None,showgrid=False)
    fig.update_layout(**{k:v for k,v in _layout(height=320,title="AASA Distribution").items()
                        if k not in ("xaxis","yaxis")},
        legend=dict(orientation="h",y=1.08))
    return fig

def aasa_agent_bar(agents, avgs):
    fig = go.Figure(go.Bar(x=agents,y=avgs,marker_color=P["blue"],marker_line_width=0))
    fig.update_xaxes(tickangle=30)
    return _apply(fig,height=300,title="Avg AASA by Agent (seconds)")

# ── Talk buckets bar ──────────────────────────────────────────
def talk_bkt_bar(labels, vals):
    colors = [P["green"],P["green"],P["amber"],P["amber"],P["red"],P["red"],P["red"]]
    fig = go.Figure(go.Bar(x=labels,y=vals,marker_color=colors[:len(labels)],
        marker_line_width=0,text=vals,textposition="outside"))
    return _apply(fig,height=300,title="Talk Time Distribution (Both Connected)")

# ── Disposition donut ─────────────────────────────────────────
def disp_donut(labels, vals):
    cols = [P["blue"],P["green"],P["teal"],P["purple"],P["orange"],
            P["amber"],P["red"],P["pink"],P["coral"],P["coral"]]
    fig = go.Figure(go.Pie(labels=labels,values=vals,hole=0.55,
        marker=dict(colors=cols[:len(labels)],line=dict(color="white",width=2))))
    return _apply(fig,height=340,title="Disposition Breakdown (Top 10)",
        legend=dict(orientation="h",y=-0.15))

# ── Network bar ───────────────────────────────────────────────
def net_agent_bar(agents,vals):
    fig = go.Figure(go.Bar(x=agents,y=vals,marker_color=P["red"],marker_line_width=0,
        text=vals,textposition="outside"))
    fig.update_xaxes(tickangle=30)
    return _apply(fig,height=300,title="Blank Hangup By Agent")

# ── Anomaly hbar ──────────────────────────────────────────────
def anom_hbar(labels,vals):
    h = max(280,len(labels)*26+80)
    fig = go.Figure(go.Bar(y=labels[::-1],x=vals[::-1],orientation="h",
        marker_color="rgba(220,38,38,0.75)",marker_line_width=0,
        text=vals[::-1],textposition="outside"))
    return _apply(fig,height=h,title="Anomaly Type Breakdown")

# ── MoM trends ────────────────────────────────────────────────
def trend_vol(months,totals,answered,missed):
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Total",x=months,y=totals,
        marker_color="rgba(37,99,235,0.35)",marker_line_color=P["blue"],marker_line_width=2))
    fig.add_trace(go.Bar(name="Answered",x=months,y=answered,
        marker_color="rgba(22,163,74,0.35)",marker_line_color=P["green"],marker_line_width=2))
    fig.add_trace(go.Bar(name="Missed",x=months,y=missed,
        marker_color="rgba(220,38,38,0.35)",marker_line_color=P["red"],marker_line_width=2))
    return _apply(fig,height=320,title="Volume Trend",barmode="group",
        legend=dict(orientation="h",y=1.08))

def trend_line(months,vals,title,color):
    fig = go.Figure(go.Scatter(x=months,y=vals,mode="lines+markers",
        line=dict(color=color,width=2.5),
        marker=dict(size=8,color="white",line=dict(color=color,width=2.5)),
        fill="tozeroy",fillcolor=color+"18"))
    return _apply(fig,height=240,title=title,showlegend=False)
