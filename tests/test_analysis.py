from conftest import load


def titles(ws, agent):
    return " | ".join(f["title"] for f in load(ws / "findings" / f"{agent}.json")["findings"])


def test_summary(demo_ws):
    a = load(demo_ws / "analysis.json")
    assert len(a["full_months"]) == 12 and a["paycheck"]["frequency_guess"] == "semimonthly"
    assert a["windows"]["recent"] == a["full_months"][-3:]          # equal windows


def test_recurring_finds_price_hike_and_zombie_sub(demo_ws):
    t = titles(demo_ws, "recurring")
    assert "Hulu went up" in t and "marked cancelled but charged" in t


def test_spending_flags_trends_and_delivery(demo_ws):
    t = titles(demo_ws, "spending")
    assert "Online Shopping up" in t and "Food delivery" in t
    roasts = load(demo_ws / "findings" / "spending.json")["roasts"]
    assert any("$" in v for v in roasts.values())


def test_audit_p2p_and_savings_sweep(demo_ws):
    t = titles(demo_ws, "audit")
    assert "P2P" in t and "moved back OUT of savings" in t


def test_roast_voices():
    import roast as R
    c = {"name": "Dining", "recent_avg": 400, "prior_avg": 300, "recent_count": 30, "total": 4000, "count": 120}
    assert "matters" in R.category_line(c, "protect", "savage")      # protected never roasted
    assert "Who approved" in R.category_line(c, "cut", "savage")
    assert "went from" in R.category_line(c, "normal", "honest")
