from vibetv import mcp


def call(method, params=None, id=1):
    return mcp.handle({"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}})


def test_initialize_echoes_protocol_version():
    r = call("initialize", {"protocolVersion": "2025-03-26"})["result"]
    assert r["protocolVersion"] == "2025-03-26"
    assert r["serverInfo"]["name"] == "vibetv"


def test_notifications_get_no_reply():
    assert mcp.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_tools_have_schemas():
    tools = call("tools/list")["result"]["tools"]
    names = {t["name"] for t in tools}
    assert {"tv_screenshot", "tv_key", "tv_logs", "tv_deploy"} <= names
    for t in tools:
        assert t["inputSchema"]["type"] == "object"


def test_tool_errors_are_reported_not_raised():
    r = call("tools/call", {"name": "tv_screenshot", "arguments": {}})["result"]
    assert r["isError"] is True
    assert "No default device" in r["content"][0]["text"]


def test_unknown_method():
    assert call("bogus")["error"]["code"] == -32601
