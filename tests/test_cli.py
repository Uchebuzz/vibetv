import pytest

from vibetv import cli, config


def test_new_and_templates(tmp_path, capsys):
    cli.main(["new", "web", "Hello TV", "--dir", str(tmp_path / "hello")])
    assert (tmp_path / "hello" / "index.html").exists()
    cli.main(["templates"])
    assert "android-tv" in capsys.readouterr().out


def test_device_commands_without_device_fail_cleanly(capsys):
    with pytest.raises(SystemExit):
        cli.main(["screenshot"])
    assert "No default device" in capsys.readouterr().err


def test_devices_and_default(capsys):
    config.save_device(config.Device(name="lounge", host="10.0.0.5", platform="roku"))
    config.save_device(config.Device(name="bedroom", host="10.0.0.6", platform="android"), make_default=False)
    cli.main(["devices"])
    out = capsys.readouterr().out
    assert "* lounge" in out and "  bedroom" in out
    assert config.get_device("10.0.0.6").name == "bedroom"
    cli.main(["use", "bedroom"])
    assert config.get_device().name == "bedroom"
