from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px


def make_figure(rows: List[Dict[str, Any]], question: str = ""):
    """
    Choisit intelligemment le type de graphique selon les données et la question.
    - Série temporelle → line
    - 2 colonnes catégorie + numérique → bar
    - 1 colonne catégorie (répartition) → pie
    - 2 colonnes numériques → scatter
    """
    if not rows:
        return None
    df = pd.DataFrame(rows)
    if df.shape[1] < 2:
        return None

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    other_cols = [c for c in df.columns if c not in numeric_cols]

    q_lower = question.lower()

    # Série temporelle
    if datetime_cols and numeric_cols:
        return px.line(
            df,
            x=datetime_cols[0],
            y=numeric_cols[0],
            title=f"Évolution de {numeric_cols[0]}",
            template="plotly_white",
        )

    # Répartition / proportion → pie
    if other_cols and numeric_cols and len(df) <= 10:
        mots_pie = ["répartition", "proportion", "part", "pourcentage", "%", "distribution"]
        if any(m in q_lower for m in mots_pie):
            return px.pie(
                df,
                names=other_cols[0],
                values=numeric_cols[0],
                title=f"Répartition par {other_cols[0]}",
                template="plotly_white",
            )

    # Scatter si 2 colonnes numériques
    if len(numeric_cols) >= 2 and not other_cols:
        return px.scatter(
            df,
            x=numeric_cols[0],
            y=numeric_cols[1],
            title=f"{numeric_cols[1]} vs {numeric_cols[0]}",
            template="plotly_white",
        )

    # Bar chart (défaut)
    if other_cols and numeric_cols:
        fig = px.bar(
            df,
            x=other_cols[0],
            y=numeric_cols[0],
            title=f"{numeric_cols[0]} par {other_cols[0]}",
            template="plotly_white",
            color=numeric_cols[0],
            color_continuous_scale="Blues",
        )
        fig.update_layout(showlegend=False)
        return fig

    return None
