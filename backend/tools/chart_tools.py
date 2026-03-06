from langchain_core.tools import tool
from pydantic import BaseModel, Field
import plotly.graph_objects as go
import plotly.express as px
import json

# Thème sombre commun à tous les graphiques
LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#7a9ab0", "family": "DM Mono, monospace"},
    "title_font": {"color": "#dce8f0", "size": 14},
    "margin": {"l":50,"r":30,"t":50,"b":50},
    "xaxis": {"gridcolor":"#1e2d3d","linecolor":"#1e2d3d","tickfont":{"size":10}},
    "yaxis": {"gridcolor":"#1e2d3d","linecolor":"#1e2d3d","tickfont":{"size":10}},
}

class LineInput(BaseModel):
    data: list[dict] = Field(description="Liste de {x_key, y_key, ...}")
    title: str = Field(description="Titre du graphique")
    x_key: str = Field(description="Clé pour l'axe X")
    y_key: str = Field(description="Clé pour l'axe Y")
    color_key: str = Field(None, description="Clé pour différencier plusieurs lignes")

@tool(args_schema=LineInput)
def create_line_chart(data, title, x_key, y_key, color_key=None) -> dict:
    """Crée un graphique en ligne. Supporte plusieurs séries si color_key est fourni."""
    import plotly.express as px
    if color_key:
        fig = px.line(data, x=x_key, y=y_key, color=color_key, title=title,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    else:
        fig = px.line(data, x=x_key, y=y_key, title=title)
        fig.update_traces(line_color="#00d4ff", line_width=2, fill="tozeroy", fillcolor="rgba(0,212,255,0.06)")

    fig.update_layout(**LAYOUT)
    parsed = json.loads(fig.to_json())
    return {"type":"chart","chart_type":"line","plotly_json":json.dumps(parsed)}

class BarInput(BaseModel):
    data: list[dict]; title: str; x_key: str; y_key: str
    color: str = Field("#a78bfa", description="Couleur hex des barres")

@tool(args_schema=BarInput)
def create_bar_chart(data, title, x_key, y_key, color="#a78bfa") -> dict:
    """Crée un bar chart horizontal. Idéal pour les classements (top produits)."""
    x = [d[y_key] for d in data]
    y = [d[x_key] for d in data]
    fig = go.Figure(go.Bar(x=x, y=y, orientation="h", marker_color=color))
    fig.update_layout(**{**LAYOUT, "title":title})
    parsed = json.loads(fig.to_json())
    return {"type":"chart","chart_type":"bar","plotly_json":json.dumps(parsed)}

class HeatmapInput(BaseModel):
    matrix: dict = Field(description="Dict {M+0: {cohort: val}, M+1: ...}")
    title: str

@tool(args_schema=HeatmapInput)
def create_heatmap(matrix, title) -> dict:
    """Crée une heatmap de cohortes. Reçoit la matrix du get_cohort_retention."""
    import pandas as pd
    df = pd.DataFrame(matrix)
    fig = go.Figure(go.Heatmap(
        z=df.values.tolist(), x=df.columns.tolist(), y=df.index.tolist(),
        colorscale=[[0,"#001824"],[0.5,"#003d57"],[1,"#00d4ff"]],
        hoverongaps=False,
        colorbar={"tickfont":{"color":"#7a9ab0"}},
    ))
    fig.update_layout(**{**LAYOUT, "title":title})
    parsed = json.loads(fig.to_json())
    return {"type":"chart","chart_type":"heatmap","plotly_json":json.dumps(parsed)}