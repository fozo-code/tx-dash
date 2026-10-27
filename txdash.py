#!/usr/bin/env python3
"""tx-dash - لوحة معلومات الجهاز (Termux / Windows / Linux) بدون مكتبات خارجية"""
import ctypes
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time

VERSION = "1.1.0"
IS_WIN = os.name == "nt"
HOME = os.path.expanduser("~")
WIN_DIR = os.path.join(HOME, ".txdash")
WIN_INSTALL_URL = "https://raw.githubusercontent.com/fozo-code/tx-dash/main/install.ps1"

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


# ---------------- Windows (ctypes) ----------------
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_uint32), ("dwMemoryLoad", ctypes.c_uint32),
                ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64)]


class FILETIME(ctypes.Structure):
    _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [("ac", ctypes.c_ubyte), ("flag", ctypes.c_ubyte), ("pct", ctypes.c_ubyte),
                ("sysflag", ctypes.c_ubyte), ("life", ctypes.c_uint32), ("full", ctypes.c_uint32)]


def _win_times():
    i, k, u = FILETIME(), FILETIME(), FILETIME()
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(i), ctypes.byref(k), ctypes.byref(u))
    f = lambda t: (t.hi << 32) | t.lo
    return f(i), f(k), f(u)


def win_drives():
    k = ctypes.windll.kernel32
    mask, out = k.GetLogicalDrives(), []
    for i in range(26):
        if mask >> i & 1:
            root = f"{chr(65 + i)}:\\"
            if k.GetDriveTypeW(root) == 3:  # fixed disks only
                u = disk(root)
                if u:
                    out.append((f"{chr(65 + i)}:", u))
    return out[:4]


# ---------------- data sources (كل واحد بيرجّع None لو مش متاح) ----------------
_cache = {}


def cached(key, ttl, fn):
    now = time.time()
    if key not in _cache or now - _cache[key][0] > ttl:
        _cache[key] = (now, fn())
    return _cache[key][1]


def _battery():
    if IS_WIN:
        try:
            s = SYSTEM_POWER_STATUS()
            ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))
            if s.flag == 128 or s.pct == 255:  # no battery (desktop)
                return None
            return {"pct": s.pct, "status": "CHARGING" if s.ac == 1 else "", "temp": None}
        except Exception:
            return None
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
    if IS_WIN:
        try:
            s = MEMORYSTATUSEX()
            s.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
            return s.ullTotalPhys - s.ullAvailPhys, s.ullTotalPhys
        except Exception:
            return None
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
    if IS_WIN:
        try:
            i1, k1, u1 = _win_times()
            time.sleep(0.25)
            i2, k2, u2 = _win_times()
            total = (k2 - k1) + (u2 - u1)  # kernel time already includes idle
            return max(0, min(100, round(100 * (1 - (i2 - i1) / max(1, total)))))
        except Exception:
            return None
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
    if IS_WIN:
        try:
            k = ctypes.windll.kernel32
            k.GetTickCount64.restype = ctypes.c_uint64
            sec = int(k.GetTickCount64() // 1000)
        except Exception:
            return None
    else:
        try:
            sec = int(float(open("/proc/uptime").read().split()[0]))
        except Exception:
            return sh(["uptime", "-p"]).replace("up ", "") or None
    d, r = divmod(sec, 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    return f"{d}d {h}h" if d else f"{h}h {m}m"


def device():
    if IS_WIN:
        import platform
        try:
            build = int(platform.version().split(".")[2])
        except Exception:
            build = 0
        name = "Windows 11" if build >= 22000 else "Windows " + platform.release()
        return f"{platform.node()} · {name}"
    model = sh(["getprop", "ro.product.model"])
    ver = sh(["getprop", "ro.build.version.release"])
    if model:
        return f"{model} · Android {ver}" if ver else model
    return os.uname().nodename


# ---------------- rendering ----------------
def row(label, pct, n, detail=None):
    line = f" {R}{label:<4}{N} {bar(pct, n)} {level(pct)}{pct:>3}%{N}"
    return [line] + ([f"      {D}{detail}{N}"] if detail else [])


def render(w):
    inner = w - 2
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

    if IS_WIN:
        for label, d in win_drives():
            body += row(label, round(100 * d[0] / d[1]), n, f"{human(d[0])} / {human(d[1])}")
    else:
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
    if IS_WIN:
        drives = win_drives()
        d = drives[0][1] if drives else None
    else:
        d = disk(HOME)
    if d:
        p = round(100 * d[0] / d[1])
        parts.append(f"DISK {level(p)}{p}%{N}")
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


# ---------------- Windows maintenance commands ----------------
def win_update():
    return subprocess.call(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                            f"irm {WIN_INSTALL_URL} | iex"])


def win_uninstall():
    import winreg
    bin_dir = os.path.join(WIN_DIR, "bin")
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0,
                            winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
            cur = winreg.QueryValueEx(k, "Path")[0]
            new = ";".join(p for p in cur.split(";") if p and p.rstrip("\\").lower() != bin_dir.lower())
            winreg.SetValueEx(k, "Path", 0, winreg.REG_EXPAND_SZ, new)
    except OSError:
        pass
    shutil.rmtree(WIN_DIR, ignore_errors=True)
    print("tx-dash removed. Close and reopen your terminal.")


def main():
    if IS_WIN:
        os.system("")  # enable ANSI colors in the Windows console
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
    if IS_WIN and a and a[0] == "update":
        return sys.exit(win_update())
    if IS_WIN and a and a[0] == "uninstall":
        return win_uninstall()
    if a and a[0] in ("-h", "--help"):
        return print("txdash [-w live] [-c one line] | txdash update | txdash uninstall")
    print(render(width()))


if __name__ == "__main__":
    main()
