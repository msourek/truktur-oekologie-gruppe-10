"""
Vibe Coding Studio - Setup-Check

Ausfuehren im Kursordner, im Terminal von VS Code:      Run it in the course folder, in the VS Code terminal:
    python check_setup.py        (Mac: python3 ...)        python check_setup.py en      (English output)

Prueft, ob alles installiert ist, und ob dein API-Key funktioniert. Dein Key wird NIE angezeigt.
Checks that everything is installed and that your API key works. Your key is NEVER shown.
"""
import importlib, shutil, subprocess, sys
from pathlib import Path

EN = len(sys.argv) > 1 and sys.argv[1].lower().startswith("en")
T = (lambda de, en: en) if EN else (lambda de, en: de)
HERE = Path(__file__).resolve().parent
results = []


def report(status, what, detail="", fix=""):
    results.append(status)
    mark = {"ok": "[ OK ]", "warn": "[ !! ]", "fail": "[" + T("FEHL", "FAIL") + "]"}[status]
    print(f"{mark} {what}" + (f"  -  {detail}" if detail else ""))
    if fix and status != "ok":
        print(f"        -> {fix}")


print("\nVibe Coding Studio - " + T("Setup-Check", "setup check") + "\n" + "-" * 40)

# 1 Python
v = sys.version_info
if v >= (3, 10):
    report("ok", "Python", f"{v.major}.{v.minor}.{v.micro}")
else:
    report("fail", "Python", f"{v.major}.{v.minor} " + T("ist zu alt", "is too old"),
           T("Python 3.14 von python.org installieren (Schritt 1)", "Install Python 3.14 from python.org (step 1)"))

# 1b macOS: rhino3dm (reads the .3dm models) ships Mac packages only for macOS 14 and newer
if sys.platform == "darwin":
    import platform
    mac = platform.mac_ver()[0] or "0"
    major = int(mac.split(".")[0] or 0)
    report("ok" if major >= 14 else "fail", T("macOS-Version", "macOS version"), mac,
           T("rhino3dm braucht macOS 14 (Sonoma) oder neuer. Bitte vor dem Kurs melden.",
             "rhino3dm needs macOS 14 (Sonoma) or newer. Please let us know before the course."))

# 2 virtual environment
in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
report("ok" if in_venv else "warn", T("Virtuelle Umgebung (.venv)", "Virtual environment (.venv)"),
       T("aktiv", "active") if in_venv else T("nicht aktiv", "not active"),
       T("In VS Code: Strg/Cmd+Shift+P -> 'Python: Select Interpreter' -> den Eintrag mit .venv waehlen, Terminal neu oeffnen (Schritt 7)",
         "In VS Code: Ctrl/Cmd+Shift+P -> 'Python: Select Interpreter' -> pick the entry with .venv, open a new terminal (step 7)"))

# 3 packages
PACKAGES = {"rhino3dm": "rhino3dm", "pymupdf": "pymupdf", "plotly": "plotly", "fastapi": "fastapi",
            "uvicorn": "uvicorn", "python-multipart": "multipart", "httpx": "httpx"}
missing = []
for pip_name, module in PACKAGES.items():
    try:
        importlib.import_module(module)
    except Exception:
        missing.append(pip_name)
if missing:
    report("fail", T("Python-Pakete", "Python packages"), T("fehlen: ", "missing: ") + ", ".join(missing),
           T("Im Terminal: pip install -r requirements.txt", "In the terminal: pip install -r requirements.txt"))
else:
    report("ok", T("Python-Pakete", "Python packages"), T(f"alle {len(PACKAGES)} da", f"all {len(PACKAGES)} present"))

# 4 git
git = shutil.which("git")
if git:
    out = subprocess.run([git, "--version"], capture_output=True, text=True).stdout.strip()
    report("ok", "Git", out)
else:
    report("fail", "Git", T("nicht gefunden", "not found"),
           T("Git installieren (Schritt 4), danach VS Code neu starten", "Install Git (step 4), then restart VS Code"))

# 5 VS Code command line (nice to have)
report("ok" if shutil.which("code") else "warn", T("VS Code im Terminal ('code')", "VS Code in the terminal ('code')"),
       T("gefunden", "found") if shutil.which("code") else T("nicht gefunden", "not found"),
       T("Nicht schlimm. Mac: in VS Code Cmd+Shift+P -> 'Shell Command: Install code command in PATH'",
         "Not a problem. Mac: in VS Code Cmd+Shift+P -> 'Shell Command: Install code command in PATH'"))

# 6 .env and .gitignore
env_file = HERE / ".env"
env = {}
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, val = line.split("=", 1)
            env[k.strip()] = val.strip().strip('"').strip("'")
key = env.get("LLM_API_KEY", "")
if not env_file.exists():
    report("fail", T(".env-Datei", ".env file"), T("fehlt im Kursordner", "missing in the course folder"),
           T("Datei .env anlegen (Schritt 8)", "Create the .env file (step 8)"))
elif not key or key.startswith("hier-") or key.startswith("paste-"):
    report("fail", T(".env-Datei", ".env file"), T("LLM_API_KEY ist leer", "LLM_API_KEY is empty"),
           T("Key in die Zeile LLM_API_KEY= eintragen (Schritt 8)", "Put your key into the line LLM_API_KEY= (step 8)"))
else:
    report("ok", T(".env-Datei", ".env file"),
           T(f"Key eingetragen ({len(key)} Zeichen, wird nicht angezeigt)", f"key present ({len(key)} characters, not shown)"))

gi = HERE / ".gitignore"
if gi.exists() and any(l.strip() in (".env", "/.env", "*.env") for l in gi.read_text(encoding="utf-8").splitlines()):
    report("ok", ".gitignore", T(".env ist geschuetzt", ".env is protected"))
else:
    report("fail", ".gitignore", T(".env steht nicht drin", ".env is not listed"),
           T("Datei .gitignore anlegen mit der Zeile .env  - sonst landet dein Key auf GitHub (Schritt 8)",
             "Create .gitignore with the line .env  - otherwise your key ends up on GitHub (step 8)"))

# 7 API key works (costs nothing: only lists models / reads the key's limit)
if key and not key.startswith(("hier-", "paste-")):
    try:
        import httpx
        provider = env.get("LLM_PROVIDER", "openai").lower()
        base = env.get("LLM_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        if provider == "anthropic":
            r = httpx.get(f"{base}/models", headers={"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=20)
        elif "openrouter.ai" in base:
            r = httpx.get(f"{base}/key", headers={"Authorization": f"Bearer {key}"}, timeout=20)
        else:
            r = httpx.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=20)
        if r.status_code == 200:
            if "openrouter.ai" in base:
                lim = r.json().get("data", {}).get("limit")
                if lim is None:
                    report("warn", "API-Key", T("funktioniert, aber KEIN Ausgabelimit gesetzt", "works, but NO credit limit set"),
                           T("Auf openrouter.ai beim Key ein Limit setzen, z. B. 10 $ (Schritt 5)",
                             "Set a limit on the key at openrouter.ai, e.g. $10 (step 5)"))
                else:
                    report("ok", "API-Key", T(f"funktioniert  (Ausgabelimit: {lim} $)", f"works  (credit limit: ${lim})"))
            else:
                report("ok", "API-Key", T("funktioniert", "works") + f" ({base})")
        elif r.status_code in (401, 403):
            report("fail", "API-Key", T(f"wird abgelehnt (HTTP {r.status_code})", f"rejected (HTTP {r.status_code})"),
                   T("Key nochmal kopieren, ohne Leerzeichen; passt LLM_BASE_URL zum Anbieter?",
                     "Copy the key again, without spaces; does LLM_BASE_URL match your provider?"))
        else:
            try:
                msg = r.json().get("error", {}).get("message", "")
            except Exception:
                msg = r.text[:120]
            report("fail", "API-Key", f"HTTP {r.status_code} {msg}",
                   T("Guthaben/Abrechnung beim Anbieter pruefen", "Check credit/billing at your provider"))
    except Exception as e:
        report("fail", "API-Key", T(f"keine Verbindung ({type(e).__name__})", f"no connection ({type(e).__name__})"),
               T("Internet? Uni-WLAN mit Proxy? Nochmal im eigenen Netz versuchen",
                 "Internet? University Wi-Fi with a proxy? Try again on your own network"))

print("-" * 40)
fails, warns = results.count("fail"), results.count("warn")
if not fails and not warns:
    print(T("ALLES GRUEN. Du bist startklar fuer den 19.10.\n", "ALL GREEN. You are ready for 19 October.\n"))
elif not fails:
    print(T(f"Startklar, {warns} Hinweis(e) oben ansehen.\n", f"Ready, have a look at {warns} note(s) above.\n"))
else:
    print(T(f"{fails} Punkt(e) fehlen noch. Die Zeilen mit -> sagen, was zu tun ist.\n",
            f"{fails} item(s) still missing. The lines with -> say what to do.\n"))
