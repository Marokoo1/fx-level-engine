from __future__ import annotations

import pandas as pd


def rank_levels(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    out["fresh_score"] = out["status"].map({"fresh": 3, "tested": 1, "crossed": 0}).fillna(0)
    out["family_score"] = out["level_family"].map({"POC": 3, "IB": 2}).fillna(1)
    out["period_score"] = out["level_period"].map({"Y": 3, "M": 2, "W": 1}).fillna(0)
    out["distance_score"] = 1 / (1 + out["distance_pips_abs"].clip(lower=0))
    out["strength_score"] = (
        out["fresh_score"] * 10
        + out["family_score"] * 5
        + out["period_score"] * 4
        + out["distance_score"] * 10
    )
    out = out.sort_values(["symbol", "table_type", "strength_score", "distance_pips_abs"], ascending=[True, True, False, True]).reset_index(drop=True)
    out["rank"] = out.groupby(["symbol", "table_type"]).cumcount() + 1
    return out
