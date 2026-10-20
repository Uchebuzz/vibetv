import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Never touch the real ~/.vibetv during tests."""
    home = tmp_path / "vibetv-home"
    monkeypatch.setenv("VIBETV_HOME", str(home))
    return home
