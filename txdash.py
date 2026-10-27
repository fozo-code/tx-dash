#!/usr/bin/env python3
"""tx-dash - لوحة معلومات الجهاز لتيرمكس (بدون مكتبات خارجية)"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

VERSION = "1.0.0"
HOME = os.path.expanduser("~")

R = "\033[38;5;196m"; D = "\033[38;5;240m"; W = "\033[38;5;252m"
G = "\033[38;5;78m"; Y = "\033[38;5;220m"; N = "\033[0m"
ANSI = re.compile(r"\033\[[0-9;?]*[A-Za-z]")


def sh(cmd, timeout=3):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=timeout, text=True).strip()
    except Exception:
        return ""


def vlen(s):
    return len(ANSI.sub("", s))


def level(p):
    return G if p < 60 else Y if p < 85 else R


def bar(p, n):
    f = max(0, min(n, round(n * p / 100)))
    return level(p) + "█" * f + D + "░" * (n - f) + N


def human(b):
    for u in ("B", "K", "M", "G", "T"):
        if b < 1024 or u == "T":
            return f"{b:.0f}{u}" if u in "BK" else f"{b:.1f}{u}"
        b /= 1024


# ---------------- data sources (كل واحد بيرجّع None لو مش متاح) ----------------
_cache = {}


def cached(key, ttl, fn):
    now = time.time()
    if key not in _cache or now - _cache[key][0] > ttl:
        _cache[key] = (now, fn())
    return _cache[key][1]


def _battery():
    try:
        j = json.loads(sh(["termux-battery-status"]))
        return {"pct": int(j["percentage"]), "status": j.get("status", ""), "temp": j.get("temperature")}
    except Exception:
        pass
    try:
        base = "/sys/class/power_supply/battery/"
        pct = int(open(base + "capacity").read())
        st = open(base + "status").read().strip().upper()
        return {"pct": pct, "status": st, "temp": None}
    except Exception:
        return None


def battery():
    return cached("bat", 10, _battery)


def mem():
    try:
        d = {}
        for line in open("/proc/meminfo"):
            k, v = line.split(":")
            d[k] = int(v.split()[0]) * 1024
        total = d["MemTotal"]
        used = total - d.get("MemAvailable", d.get("MemFree", 0))
        return used, total
    except Exception:
        return None


def _stat():
    v = list(map(int, open("/proc/stat").readline().split()[1:8]))
    return sum(v), v[3] + v[4]


def cpu():
    try:
        t1, i1 = _stat()
        time.sleep(0.25)
        t2, i2 = _stat()
        return round(100 * (1 - (i2 - i1) / max(1, t2 - t1)))
    except Exception:
        try:
            return min(100, round(100 * os.getloadavg()[0] / (os.cpu_count() or 1)))
        except Exception:
            return None


def disk(path):
    try:
        u = shutil.disk_usage(path)
        return u.used, u.total
    except Exception:
        return None


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def uptime():
    try:
        sec = int(float(open("/proc/uptime").read().split()[0]))
    except Exception:
        return sh(["uptime", "-p"]).replace("up ", "") or None
    d, r = divmod(sec, 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    return f"{d}d {h}h" if d else f"{h}h {m}m"


def device():
    model = sh(["getprop", "ro.product.model"])
    ver = sh(["getprop", "ro.build.version.release"])
    if model:
        return f"{model} · Android {ver}" if ver else model
    return os.uname().nodename


# ---------------- rendering ----------------
def row(label, pct, n, detail=None):
    line = f" {R}{label:<4}{N} {bar(pct, n)} {level(pct)}{pct:>3}%{N}"
    return [line] + ([f"      {D}{detail}{N}"] if detail else [])


def render(width):
    inner = width - 2
    n = inner - 14
    body = [f" {W}{device()[: inner - 2]}{N}", ""]

    b = battery()
    if b:
        extra = []
        if "CHARG" in b["status"].upper():
            extra.append("charging")
        if b["temp"] is not None:
            extra.append(f"{b['temp']:.1f}°C")
        body += row("BAT", b["pct"], n, " · ".join(extra) or None)
    m = mem()
    if m:
        body += row("RAM", round(100 * m[0] / m[1]), n, f"{human(m[0])} / {human(m[1])}")
    c = cpu()
    if c is not None:
        body += row("CPU", c, n, f"{os.cpu_count()} core(s)")
    d = disk(HOME)
    if d:
        body += row("DATA", round(100 * d[0] / d[1]), n, f"{human(d[0])} / {human(d[1])}")
    p = disk("/storage/emulated/0")
    if p and p != d:
        body += row("SD", round(100 * p[0] / p[1]), n, f"{human(p[0])} / {human(p[1])}")

    body.append("")
    ip = cached("ip", 30, local_ip)
    body.append(f" {R}NET{N}  {W}{ip or 'offline'}{N}")
    up = uptime()
    if up:
        body.append(f" {R}UP{N}   {W}{up}{N}")

    top = D + "╭─ " + R + "TX-DASH" + D + " " + "─" * (inner - 10) + "╮" + N
    out = [top]
    for line in body:
        out.append(D + "│" + N + line + " " * max(0, inner - vlen(line)) + D + "│" + N)
    out.append(D + "╰" + "─" * inner + "╯" + N)
    return "\n".join(out)


def compact():
    parts = []
    b = battery()
    if b:
        parts.append(f"BAT {level(100 - b['pct'])}{b['pct']}%{N}")
    m = mem()
    if m:
        p = round(100 * m[0] / m[1])
        parts.append(f"RAM {level(p)}{p}%{N}")
    d = disk(HOME)
    if d:
        p = round(100 * d[0] / d[1])
        parts.append(f"DATA {level(p)}{p}%{N}")
    print(f" {R}▌{N}" + f" {D}·{N} ".join(parts))


def width():
    return max(36, min(52, shutil.get_terminal_size((44, 24)).columns))


def watch():
    sys.stdout.write("\033[?25l")
    try:
        while True:
            sys.stdout.write("\033[H\033[J" + render(width()) + f"\n {D}Ctrl+C to exit{N}\n")
            sys.stdout.flush()
            time.sleep(1.5)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h\n")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    a = sys.argv[1:]
    if a and a[0] in ("-w", "--watch"):
        return watch()
    if a and a[0] in ("-c", "--compact"):
        return compact()
    if a and a[0] in ("-v", "--version"):
        return print("tx-dash", VERSION)
    if a and a[0] in ("-h", "--help"):
        return print("txdash [-w live] [-c one line] | txdash startup on|off | txdash update | txdash uninstall")
    print(render(width()))


if __name__ == "__main__":
    main()
