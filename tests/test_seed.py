import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent import seed


def test_yatras_has_both():
    y = seed.load("yatras")
    assert set(y.keys()) == {"pandharpur", "kumbh"}
    assert y["pandharpur"]["name"]["mr"]
    assert y["kumbh"]["control_room"]


def test_logistics_rates_per_yatra():
    r = seed.load("logistics_rates")
    assert r["pandharpur"] and r["kumbh"]
    first = r["pandharpur"][0]
    assert "service" in first and "rate" in first


def test_missing_file_raises():
    import pytest
    with pytest.raises(FileNotFoundError):
        seed.load("does-not-exist")


def test_t_resolves_language():
    assert seed.t({"mr": "अ", "hi": "ब", "en": "c"}, "mr") == "अ"
    assert seed.t({"en": "only"}, "mr") == "only"   # falls back to en
    assert seed.t("plain", "hi") == "plain"
