from __future__ import annotations
import json
import plotly.graph_objects as go
import pandas as pd


def plot_yield_curve(yield_curve: pd.DataFrame) -> str:
    fig = go.Figure(data=go.Scatter(x=yield_curve.index.tolist(), y=yield_curve["Rate"].tolist(), mode="lines+markers"))
    fig.update_layout(title="Yield Curve", xaxis_title="Date", yaxis_title="Rate")
    # Return a single-encoded JSON string (fix double-encoding)
    return fig.to_json()
