import io
import zipfile

import pytest

from vibetv import roku, scaffold


def test_zip_channel_puts_manifest_at_root_and_skips_docs(tmp_path):
    dest = scaffold.create("roku", "Chan", tmp_path / "chan")
    names = zipfile.ZipFile(io.BytesIO(roku.zip_channel(dest))).namelist()
    assert "manifest" in names
    assert "source/main.brs" in names
    assert "components/MainScene.xml" in names
    assert not any(n.endswith(".md") or n == "vibetv.json" for n in names)


def test_zip_channel_requires_manifest(tmp_path):
    with pytest.raises(roku.RokuError):
        roku.zip_channel(tmp_path)


def test_multipart_encoding():
    body, ctype = roku._multipart({"mysubmit": "Install"}, {"archive": ("dev.zip", b"PK\x03\x04")})
    boundary = ctype.split("boundary=")[1]
    assert body.startswith(f"--{boundary}\r\n".encode())
    assert b'name="mysubmit"\r\n\r\nInstall' in body
    assert b'filename="dev.zip"' in body
    assert body.endswith(f"--{boundary}--\r\n".encode())
