"""Start, stop or check the legal demo server (ldm_pro on the port in odoo19_ldm.conf).

  python docs/ldm/tools/demo.py start     starts it in the background, logs to .odoo_logs_ldm/pro_server.log
  python docs/ldm/tools/demo.py stop      stops every Odoo started with odoo19_ldm.conf and holding the port
  python docs/ldm/tools/demo.py status

Only processes whose command line names odoo19_ldm.conf are touched: other
projects' Odoo servers on this machine keep running. On Windows two servers can
hold the same port at once, so stop always checks that none is left.
"""
import configparser
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CONF = os.path.join(ROOT, "odoo19_ldm.conf")
conf = configparser.ConfigParser()
conf.read(CONF)
PORT = conf["options"].get("http_port", "8110")
DB = conf["options"].get("db_name", "ldm_pro")
PYTHON = os.path.join(ROOT, ".venv_odoo19", "Scripts", "python.exe")


def listeners():
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    pids = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(f":{PORT}") and parts[3] == "LISTENING":
            pids.add(parts[4])
    return pids


def command_line(pid):
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
                         capture_output=True, text=True).stdout
    return out.strip()


def ours():
    return {pid: cmd for pid in listeners() if "odoo19_ldm.conf" in (cmd := command_line(pid))}


def status():
    mine = ours()
    others = listeners() - set(mine)
    print(f"port {PORT}: {len(mine)} legal demo server(s) {sorted(mine)}; other listeners {sorted(others)}")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/web/login", timeout=5) as response:
            print("login page:", response.status, f"http://localhost:{PORT}/web/login")
    except Exception as exc:  # noqa: BLE001
        print("login page: not answering", exc)


def stop():
    for pid in ours():
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force"])
        print("stopped", pid)
    time.sleep(1)
    left = ours()
    if left:
        sys.exit(f"still running: {sorted(left)}")


def start():
    if ours():
        sys.exit("already running; stop it first")
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    subprocess.Popen([PYTHON, os.path.join("odoo-19.0", "odoo-bin"), "-c", CONF, "-d", DB,
                      "--logfile", os.path.join(".odoo_logs_ldm", "pro_server.log")],
                     cwd=ROOT, env=env, creationflags=flags, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        time.sleep(2)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/web/login", timeout=5):
                break
        except Exception:  # noqa: BLE001
            continue
    status()


if __name__ == "__main__":
    {"start": start, "stop": stop, "status": status}[sys.argv[1] if len(sys.argv) > 1 else "status"]()
