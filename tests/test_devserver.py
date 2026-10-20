import json
import threading
import urllib.request

from vibetv import devserver


def test_inject_before_body_close():
    out = devserver.inject(b"<html><body><p>x</p></BODY></html>")
    assert out.index(devserver.TAG) < out.lower().index(b"</body>")


def test_inject_without_body():
    assert devserver.inject(b"<p>x</p>").endswith(devserver.TAG)


def test_version_changes_when_files_change(tmp_path):
    (tmp_path / "a.js").write_text("1")
    v1 = devserver.tree_version(tmp_path)
    (tmp_path / "b.js").write_text("2")
    assert devserver.tree_version(tmp_path) != v1


def test_server_round_trip(tmp_path):
    (tmp_path / "index.html").write_text("<html><body>hi</body></html>")
    server = devserver.make_server(tmp_path, host="127.0.0.1", port=0, quiet=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        html = urllib.request.urlopen(base + "/").read()
        assert devserver.TAG in html
        req = urllib.request.Request(base + "/__vibetv/log", data=json.dumps({"level": "error", "msg": "boom"}).encode())
        urllib.request.urlopen(req).read()
        logs = json.loads(urllib.request.urlopen(base + "/__vibetv/logs").read())
        assert logs[-1].endswith("[error] boom")
    finally:
        server.shutdown()
        server.server_close()
