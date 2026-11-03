import copy

import pytest
from conftest import load
from mc_common import ConfigError, load_config, month_budget, validate_config
import plan_budget
import goal


def test_month_budget_matches_hand_math(demo_ws):
    cfg = load_config(demo_ws)
    b = month_budget(cfg, "2026-11")
    assert b["income"] == pytest.approx(5700)
    assert b["savings"] == pytest.approx(800)
    assert b["sinking"] == pytest.approx(2800 - (1650 + 420 + 390 + 85 + 142))
    assert b["buffer"] == pytest.approx(b["income"] - b["total_out"])
    mar = month_budget(cfg, "2027-03")
    assert mar["savings"] == pytest.approx(800 + 3900)                  # windfalls route to savings


def test_split_too_big_is_critical(demo_ws):
    cfg = copy.deepcopy(load_config(demo_ws))
    cfg["split"]["accounts"][0]["per_paycheck"] = 1500
    _, f = plan_budget.check(cfg)
    assert f and f[0]["severity"] == "critical" and "savings split" in f[0]["title"]


def test_caps_respect_user_values(demo_ws):
    cfg = copy.deepcopy(load(demo_ws / "config.json"))
    cfg["categories"][0]["cap"] = 123
    cfg["categories"][1]["cap"] = None
    changed = plan_budget.fill_caps(cfg, load(demo_ws / "analysis.json"))
    assert cfg["categories"][0]["cap"] == 123 and [c["category"] for c in changed] == [cfg["categories"][1]["name"]]


def test_caps_need_confirmed_multipliers(demo_ws):
    cfg = copy.deepcopy(load(demo_ws / "config.json"))
    cfg.pop("cap_multipliers")
    cfg["categories"][0]["cap"] = None
    with pytest.raises(SystemExit):
        plan_budget.fill_caps(cfg, load(demo_ws / "analysis.json"))


def test_goal_projection(demo_ws):
    g = goal.project(load_config(demo_ws))
    assert g["start"] == pytest.approx(2100 + 900 + 6400 - 1100)
    assert len(g["checkpoints"]) == 6 and g["projected"] > g["start"]
    assert any("Unconfirmed windfall" in e for e in g["findings"][0]["evidence"])


def test_missing_field_fails_loudly(demo_ws):
    cfg = copy.deepcopy(load(demo_ws / "config.json"))
    del cfg["income"]["take_home_per_paycheck"]
    with pytest.raises(ConfigError, match="income.take_home_per_paycheck"):
        validate_config(cfg)
