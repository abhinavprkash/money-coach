"""Evidence-based roast lines. Every line is built from the user's own numbers; nothing names a person.

tone: gentle | honest | savage      priority (from onboarding): protect | normal | cut
Protected categories always get the gentle voice: you told us they matter.
"""


def _m(x):
    return f"${x:,.0f}"


def _voice(priority, tone):
    if priority == "protect":
        return "gentle"
    if priority == "cut" and tone != "gentle":
        return "savage"
    return tone


def category_line(c, priority="normal", tone="honest"):
    """c: category summary dict from analyze.summary (recent_avg, prior_avg, recent_count, total, count)."""
    v = _voice(priority, tone)
    ra, pa, n = c["recent_avg"], c["prior_avg"], c["recent_count"]
    trend = ra - pa
    name = c["name"].lower()
    if v == "gentle":
        if priority == "protect":
            return f"You said {name} matters. {_m(ra)}/mo lately; keep it intentional."
        return f"{_m(ra)}/mo on {name} lately. Small trims add up."
    if v == "honest":
        if pa and trend > 0:
            return f"{name.capitalize()} went from {_m(pa)} to {_m(ra)}/mo ({n} charges in 3 months)."
        return f"{_m(ra)}/mo on {name} ({n} charges in 3 months)."
    # savage
    if pa and trend > 0:
        return f"{name.capitalize()} jumped {_m(trend)}/mo. {n} charges in 3 months. Who approved this? Not your goal."
    yearly = ra * 12
    return f"{_m(yearly)}/yr on {name}. That's a vacation you're eating one swipe at a time."


def action_for(name, tone):
    n = name.lower()
    base = {
        "food delivery": "Delete the delivery apps until your goal date.",
        "dining": "Pick two restaurant nights a week; cook the rest.",
        "online shopping": "48-hour cart rule. Remove the saved card.",
        "groceries": "Plan meals before the store; split shared groceries the same day.",
        "rideshare": "Rideshare only after 10pm or in the rain.",
        "coffee": "Brew at home Mon–Thu.",
        "entertainment": "One paid outing a week.",
        "clothing": "No new clothes for 60 days.",
    }.get(n, f"Set a cap for {n} and check it weekly.")
    return base if tone != "savage" else base + " No exceptions."


def cadence_line(m, tone):
    per_week = m["recent_count"] / 13
    if tone == "gentle":
        return f"{m['merchant']} about {per_week:.1f}×/week lately. Batch your orders."
    if tone == "honest":
        return f"{m['recent_count']} {m['merchant']} charges in 3 months. Batch orders and use a 48-hour rule."
    return f"{m['recent_count']} {m['merchant']} charges in 3 months, one every {13*7/max(1, m['recent_count']):.1f} days. The cart is not a hobby."


def delivery_line(c, tone):
    if tone == "gentle":
        return "Try a no-delivery week and see how it feels."
    if tone == "honest":
        return f"{_m(c['total'])} on delivery over {c['count']} orders. Make the default 'cook or pick up'."
    return f"{_m(c['total'])} on {c['count']} delivery orders. Budget is $0 now. Delete the apps."


# Lines the dashboard uses for live status (mirrored in app/site/template.html: varRoast/netRoast).
def over_budget(over, tone):
    return {"gentle": f"{_m(over)} over. Tomorrow's a new day.",
            "honest": f"Over by {_m(over)}. Pause this category.",
            "savage": f"OVER by {_m(over)}. Card goes in the drawer."}[tone]
