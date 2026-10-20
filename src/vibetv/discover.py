"""Find TVs on the local network.

Uses SSDP (the same multicast discovery casting apps use) to find Roku, DIAL
(Android/Google/Fire TV, LG, Samsung) and UPnP renderers, then probes well-known
ports to work out how vibetv can talk to each one.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from xml.etree import ElementTree

SSDP_ADDR = ("239.255.255.250", 1900)
SEARCH_TARGETS = (
    "roku:ecp",
    "urn:dial-multiscreen-org:service:dial:1",
    "urn:schemas-upnp-org:device:MediaRenderer:1",
    "urn:lge-com:service:webos-second-screen:1",
)

# port -> (platform hint, description)
PORTS = {
    5555: ("android", "ADB over network"),
    8060: ("roku", "Roku ECP"),
    3000: ("webos", "webOS SSAP"),
    3001: ("webos", "webOS SSAP (TLS)"),
    8001: ("tizen", "Samsung Tizen remote"),
    8002: ("tizen", "Samsung Tizen remote (TLS)"),
}


@dataclass
class FoundTV:
    host: str
    name: str = ""
    manufacturer: str = ""
    model: str = ""
    open_ports: list[int] = field(default_factory=list)
    services: set[str] = field(default_factory=set)

    @property
    def platform(self) -> str:
        """Best guess at which vibetv backend can drive this device."""
        maker = self.manufacturer.lower()
        if 8060 in self.open_ports or "roku" in maker:
            return "roku"
        if 5555 in self.open_ports:
            return "android"
        if {3000, 3001} & set(self.open_ports) or "lg electronics" in maker:
            return "webos"
        if {8001, 8002} & set(self.open_ports) or "samsung" in maker:
            return "tizen"
        if "amazon" in maker or "google" in maker or "nvidia" in maker:
            return "android"
        return "unknown"

    @property
    def ready(self) -> bool:
        """Whether vibetv can control the device right now without extra setup."""
        return {"roku": 8060, "android": 5555}.get(self.platform) in self.open_ports or self.platform == "webos"


def parse_ssdp_response(data: bytes) -> dict[str, str]:
    headers = {}
    for line in data.decode(errors="replace").split("\r\n")[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    return headers


def parse_device_description(xml_text: str) -> dict[str, str]:
    """Pull friendlyName/manufacturer/modelName out of a UPnP device description."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return {}
    out = {}
    for tag in ("friendlyName", "manufacturer", "modelName"):
        el = root.find(f".//{{*}}{tag}")
        if el is None:
            el = root.find(f".//{tag}")
        if el is not None and el.text:
            out[tag] = el.text.strip()
    return out


def ssdp_search(timeout: float = 3.0) -> dict[str, list[dict[str, str]]]:
    """Return {host: [ssdp response headers...]}."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(timeout)
    for st in SEARCH_TARGETS:
        msg = (
            "M-SEARCH * HTTP/1.1\r\n"
            f"HOST: {SSDP_ADDR[0]}:{SSDP_ADDR[1]}\r\n"
            'MAN: "ssdp:discover"\r\n'
            "MX: 2\r\n"
            f"ST: {st}\r\n\r\n"
        )
        try:
            sock.sendto(msg.encode(), SSDP_ADDR)
        except OSError:
            pass
    found: dict[str, list[dict[str, str]]] = {}
    try:
        while True:
            data, (host, _) = sock.recvfrom(65507)
            found.setdefault(host, []).append(parse_ssdp_response(data))
    except (socket.timeout, OSError):
        pass
    finally:
        sock.close()
    return found


def port_open(host: str, port: int, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def local_ip() -> str | None:
    """This machine's LAN address, found by routing a UDP socket (no packets are sent)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


def local_subnet() -> ipaddress.IPv4Network | None:
    """Guess the LAN /24 so --scan can sweep it."""
    ip = local_ip()
    return ipaddress.ip_network(f"{ip}/24", strict=False) if ip else None


def _describe(tv: FoundTV, location: str) -> None:
    try:
        with urllib.request.urlopen(location, timeout=2) as resp:
            info = parse_device_description(resp.read().decode(errors="replace"))
    except Exception:
        return
    tv.name = tv.name or info.get("friendlyName", "")
    tv.manufacturer = tv.manufacturer or info.get("manufacturer", "")
    tv.model = tv.model or info.get("modelName", "")


def discover(timeout: float = 3.0, scan_subnet: bool = False) -> list[FoundTV]:
    tvs: dict[str, FoundTV] = {}
    locations: dict[str, str] = {}
    for host, responses in ssdp_search(timeout).items():
        tv = tvs.setdefault(host, FoundTV(host=host))
        for headers in responses:
            if st := headers.get("st"):
                tv.services.add(st)
            if loc := headers.get("location"):
                locations.setdefault(host, loc)
            server = headers.get("server", "")
            if "roku" in server.lower():
                tv.manufacturer = tv.manufacturer or "Roku"

    hosts = set(tvs)
    if scan_subnet and (net := local_subnet()):
        hosts |= {str(h) for h in net.hosts()}

    def probe(host: str) -> tuple[str, list[int]]:
        return host, [p for p in PORTS if port_open(host, p)]

    with ThreadPoolExecutor(max_workers=64) as pool:
        for host, ports in pool.map(probe, sorted(hosts)):
            if ports:
                tvs.setdefault(host, FoundTV(host=host)).open_ports = ports
        list(pool.map(lambda h: _describe(tvs[h], locations[h]), locations))

    # Drop SSDP chatter from routers/NAS boxes that expose nothing TV-like.
    result = [
        tv for tv in tvs.values()
        if tv.open_ports or any(re.search(r"roku|dial|webos", s, re.I) for s in tv.services)
    ]
    return sorted(result, key=lambda t: tuple(int(x) for x in t.host.split(".")))
