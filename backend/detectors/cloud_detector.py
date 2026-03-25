from __future__ import annotations

import pandas as pd

from backend.models import Finding


def run(data: dict) -> list[Finding]:
    findings: list[Finding] = []
    cloud = data.get("cloud", [])
    idle = data.get("idle", [])

    if cloud:
        df = pd.DataFrame(cloud)
        month_col = next((c for c in df.columns if "month" in c.lower() or "date" in c.lower()), None)
        account_col = next((c for c in df.columns if "account" in c.lower()), None)
        service_col = next((c for c in df.columns if "service" in c.lower()), None)
        amount_cols = [c for c in df.columns if any(k in c.lower() for k in ["ec2", "s3", "rds", "lambda", "cloudfront", "cost", "amount"])]

        if month_col and account_col and amount_cols:
            df["_month"] = pd.to_datetime(df[month_col], errors="coerce")
            df = df.dropna(subset=["_month"]).sort_values("_month")
            for acc, g1 in df.groupby(account_col):
                for col in amount_cols:
                    if g1[col].dtype == object:
                        g1[col] = pd.to_numeric(g1[col], errors="coerce").fillna(0)
                    s = g1[["_month", col]].copy()
                    roll = s.set_index("_month")[col].rolling("90D", min_periods=2).mean().shift(1)
                    s["roll"] = roll.values
                    for idx, row in s.iterrows():
                        month = row["_month"]
                        val = float(row[col])
                        roll = float(row["roll"] or 0)
                        service_name = service_col and str(g1.loc[idx, service_col]).lower() or col.lower()
                        if month.month in [11, 12] and any(k in service_name for k in ["lambda", "cloudfront"]):
                            continue
                        if roll > 0 and val > 2.5 * roll and val > 50000:
                            impact = int(max(val - roll, 0))
                            severity = "critical" if impact >= 500000 else "high" if impact > 100000 else "medium"
                            findings.append(Finding(
                                category="cloud", severity=severity, title=f"Cloud spike in {col} for account {acc}",
                                inrImpact=impact, rootCause="Monthly cost exceeded 2.5x rolling 3-month baseline.",
                                recommendation="Review recent deployments and right-size workloads.", effort="2 days",
                                sourceRows=[int(idx)], detectorId="F_C1"
                            ))

    for idx, row in enumerate(idle):
        days = int(float(row.get("days idle", row.get("days_idle", 0)) or 0))
        monthly = float(row.get("monthly cost", row.get("monthly cost (inr)", row.get("monthly_cost", 0)) or 0))
        if days > 60 and monthly > 0:
            impact = int(monthly * 12)
            severity = "high" if days > 180 else "medium"
            findings.append(Finding(
                category="cloud", severity=severity, title=f"Idle resource {row.get('resource id', row.get('bucket name', idx))}",
                inrImpact=impact, rootCause="Resource idle beyond threshold; annualised waste estimated.",
                recommendation="Delete or archive idle cloud assets.", effort="1 day", sourceRows=[idx], detectorId="F_C2"
            ))
    return findings
