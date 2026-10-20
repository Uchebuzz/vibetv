import json

import pytest

from vibetv import adb, tweaks


class FakeTV:
    """In-memory stand-in for the adb calls tweaks.py makes."""

    def __init__(self, monkeypatch):
        self.settings = {("global", "window_animation_scale"): "1.0"}
        self.packages = {"com.bloat": True}
        monkeypatch.setattr(adb, "get_setting", lambda s, ns, k: self.settings.get((ns, k)))
        monkeypatch.setattr(adb, "put_setting", self._put)
        monkeypatch.setattr(adb, "is_package_enabled", lambda s, p: self.packages.get(p))
        monkeypatch.setattr(adb, "set_package_enabled", lambda s, p, e: self.packages.__setitem__(p, e))

    def _put(self, serial, ns, key, value):
        if value is None:
            self.settings.pop((ns, key), None)
        else:
            self.settings[(ns, key)] = value


@pytest.fixture
def fake(monkeypatch):
    return FakeTV(monkeypatch)


PRESET = tweaks.Preset(
    id="t", title="T", description="d",
    steps=[
        {"setting": "global", "key": "window_animation_scale", "value": "0.5"},
        {"setting": "secure", "key": "brand_new", "value": "1"},
        {"package": "com.bloat", "enabled": False},
        {"package": "com.missing", "enabled": False},
    ],
)


def test_builtin_presets_are_valid():
    presets = tweaks.load_presets()
    assert "snappy-animations" in presets
    for p in presets.values():
        assert p.risk in tweaks.RISKS


def test_apply_then_revert_restores_everything(fake):
    out = tweaks.apply("tv:5555", PRESET)
    assert fake.settings[("global", "window_animation_scale")] == "0.5"
    assert fake.settings[("secure", "brand_new")] == "1"
    assert fake.packages["com.bloat"] is False
    assert any("not installed" in line for line in out)
    assert tweaks.applied("tv:5555") == ["t"]

    tweaks.revert("tv:5555", "t")
    assert fake.settings == {("global", "window_animation_scale"): "1.0"}  # brand_new deleted again
    assert fake.packages["com.bloat"] is True
    assert tweaks.applied("tv:5555") == []


def test_reapply_keeps_original_undo_values(fake):
    tweaks.apply("tv:5555", PRESET)
    tweaks.apply("tv:5555", PRESET)
    tweaks.revert("tv:5555", "t")
    assert fake.settings[("global", "window_animation_scale")] == "1.0"


def test_revert_unknown_raises(fake):
    with pytest.raises(KeyError):
        tweaks.revert("tv:5555", "nope")


def test_user_presets_override(isolated_home):
    (isolated_home / "presets").mkdir(parents=True)
    (isolated_home / "presets" / "mine.json").write_text(json.dumps({
        "id": "snappy-animations", "title": "Mine", "description": "x",
        "steps": [{"setting": "global", "key": "k", "value": "v"}],
    }))
    assert tweaks.load_presets()["snappy-animations"].title == "Mine"


@pytest.mark.parametrize("bad", [
    {"title": "x", "description": "x", "steps": []},
    {"id": "x", "title": "x", "description": "x", "steps": [{"setting": "bogus", "key": "k", "value": "v"}]},
    {"id": "x", "title": "x", "description": "x", "steps": [{"package": "p"}]},
    {"id": "x", "title": "x", "description": "x", "risk": "yolo", "steps": []},
])
def test_validate_rejects_bad_presets(bad):
    assert tweaks.validate(bad)
