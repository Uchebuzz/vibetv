import json
import struct

import pytest

from vibetv import scaffold


@pytest.mark.parametrize("template", list(scaffold.TEMPLATES))
def test_every_template_scaffolds_without_leftover_placeholders(tmp_path, template):
    dest = scaffold.create(template, "Living Room", tmp_path / "proj", app_id="com.example.living")
    project = json.loads((dest / "vibetv.json").read_text())
    assert project["template"] == template
    assert (dest / "AGENTS.md").exists()
    assert (dest / "CLAUDE.md").read_text() == "@AGENTS.md\n"
    for path in dest.rglob("*"):
        if path.is_file() and path.suffix != ".png":
            data = path.read_bytes()
            assert b"{{" not in data, f"placeholder left in {path}"
            assert b"\r\n" not in data, f"CRLF in {path}"


def test_android_layout(tmp_path):
    dest = scaffold.create("android-tv", "My Home", tmp_path / "p", app_id="com.example.home")
    kt = dest / "app/src/main/java/com/example/home/MainActivity.kt"
    assert kt.read_text().startswith("package com.example.home")
    assert (dest / ".github/workflows/build-apk.yml").exists()
    assert (dest / ".gitignore").exists()
    assert (dest / "web/index.html").exists()
    assert 'namespace = "com.example.home"' in (dest / "app/build.gradle.kts").read_text()


def test_generated_pngs_have_requested_size(tmp_path):
    dest = scaffold.create("roku", "Chan", tmp_path / "r")
    data = (dest / "images/icon_hd.png").read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert struct.unpack(">II", data[16:24]) == (336, 210)


@pytest.mark.parametrize("bad", ["MyApp", "com", "com.Example.app", "1com.app", "com..app"])
def test_rejects_bad_app_ids(tmp_path, bad):
    with pytest.raises(ValueError):
        scaffold.create("web", "x", tmp_path / "x", app_id=bad)


def test_default_app_id_is_valid():
    assert scaffold.APP_ID_RE.match(scaffold.default_app_id("123 Living-Room!"))


def test_refuses_non_empty_dir(tmp_path):
    (tmp_path / "file.txt").write_text("hi")
    with pytest.raises(FileExistsError):
        scaffold.create("web", "x", tmp_path)
