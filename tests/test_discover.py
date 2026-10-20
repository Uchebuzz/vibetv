from vibetv.discover import FoundTV, parse_device_description, parse_ssdp_response


def test_parse_ssdp_response():
    raw = (
        b"HTTP/1.1 200 OK\r\nCache-Control: max-age=3600\r\nST: roku:ecp\r\n"
        b"LOCATION: http://192.168.1.50:8060/\r\nServer: Roku/12.0 UPnP/1.0\r\n\r\n"
    )
    h = parse_ssdp_response(raw)
    assert h["st"] == "roku:ecp"
    assert h["location"] == "http://192.168.1.50:8060/"


def test_parse_device_description_with_namespace():
    xml = """<?xml version="1.0"?>
    <root xmlns="urn:schemas-upnp-org:device-1-0"><device>
      <friendlyName>Living Room TV</friendlyName><manufacturer>LG Electronics</manufacturer>
      <modelName>OLED55</modelName></device></root>"""
    info = parse_device_description(xml)
    assert info == {"friendlyName": "Living Room TV", "manufacturer": "LG Electronics", "modelName": "OLED55"}


def test_parse_device_description_garbage():
    assert parse_device_description("not xml") == {}


def test_platform_guessing():
    assert FoundTV("1.1.1.1", open_ports=[8060]).platform == "roku"
    assert FoundTV("1.1.1.1", open_ports=[5555]).platform == "android"
    assert FoundTV("1.1.1.1", open_ports=[3000]).platform == "webos"
    assert FoundTV("1.1.1.1", manufacturer="Samsung Electronics").platform == "tizen"
    assert FoundTV("1.1.1.1", manufacturer="Amazon").platform == "android"
    assert FoundTV("1.1.1.1").platform == "unknown"
