import os
import sys
import json
import ast
import stat
import shutil
import time
import queue
import shlex
import socket
import multiprocessing
import secrets
import threading
import webbrowser
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import importlib
import importlib.metadata
from importlib.util import find_spec

APP_NAME = "CodeEditorStudio"
APP_VERSION = "V1.0.0"
AUTHOR = "@alexis_dpt"
AUTHOR_URL = "https://github.com/alexis-dpt"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".codeeditorstudio")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
BUILD_DIR = os.path.join(CONFIG_DIR, "builds")
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
CREATE_NEW_CONSOLE = 0x00000010 if os.name == "nt" else 0
IGNORED = frozenset(("__pycache__", "node_modules", "build", "dist", "venv", ".venv"))
BIN_EXT = frozenset((".exe", ".dll", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".pyc",
                     ".so", ".bin", ".pdf", ".7z", ".rar", ".mp3", ".mp4", ".woff", ".woff2", ".ttf"))
WIN_RESERVED = frozenset(["CON", "PRN", "AUX", "NUL"]
                         + ["COM%d" % i for i in range(1, 10)]
                         + ["LPT%d" % i for i in range(1, 10)])
MAX_READ = 5_000_000
MAX_SEARCH_FILE = 512_000
MAX_RESULTS = 200
MAX_ENTRIES = 3000
MAX_BODY = 64_000_000
NO_DIALOG = object()
LOCK_PORT = 47653
FROZEN = bool(getattr(sys, "frozen", False))
_PY_CACHE = []
DEFAULT_CONFIG = {"theme": "dark", "uiLang": "en", "lang": "Python", "fontSize": 13,
                  "tabSize": 4, "customThemes": [], "autoSave": False, "autoClose": True,
                  "autoIndent": True, "restore": False, "showHidden": False, "recent": []}


def _say(msg):
    try:
        print(msg, flush=True)
    except Exception:
        pass


def python_cmd():
    if _PY_CACHE:
        return _PY_CACHE[0]
    found = None
    if not FROZEN:
        exe = sys.executable
        if os.name == "nt" and os.path.basename(exe).lower() == "pythonw.exe":
            alt = os.path.join(os.path.dirname(exe), "python.exe")
            if os.path.isfile(alt):
                exe = alt
        found = [exe]
    else:
        for cand in (["python"], ["py", "-3"], ["python3"]):
            exe = shutil.which(cand[0])
            if not exe:
                continue
            try:
                r = subprocess.run([exe] + cand[1:] + ["--version"], capture_output=True,
                                   timeout=15, creationflags=CREATE_NO_WINDOW)
                if r.returncode == 0:
                    found = [exe] + cand[1:]
                    break
            except Exception:
                continue
    _PY_CACHE.append(found)
    return found


def _ext_has(py, mod):
    try:
        r = subprocess.run(py + ["-c", "import " + mod], capture_output=True, timeout=60,
                           creationflags=CREATE_NO_WINDOW)
        return r.returncode == 0
    except Exception:
        return False


def _pip_install(*pkgs):
    py = python_cmd()
    if py is None:
        return False
    base = py + ["-m", "pip", "install", "--quiet", "--no-cache-dir",
                 "--no-warn-script-location", "--disable-pip-version-check"]
    for attempt in range(2):
        try:
            subprocess.check_call(base + list(pkgs), creationflags=CREATE_NO_WINDOW)
            importlib.invalidate_caches()
            return True
        except Exception:
            if attempt == 0:
                try:
                    subprocess.check_call(py + ["-m", "ensurepip", "--upgrade"],
                                          creationflags=CREATE_NO_WINDOW)
                except Exception:
                    pass
    return False


def _has_module(mod, pkg):
    if find_spec(mod) is not None:
        return True
    try:
        importlib.metadata.version(pkg)
        return True
    except Exception:
        return False


def _ensure_module(mod, pkg):
    if _has_module(mod, pkg):
        return True
    _say("Installing " + pkg + "...")
    _pip_install(pkg)
    importlib.invalidate_caches()
    return _has_module(mod, pkg)



HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CodeEditorStudio __VER__</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-user-select:none;user-select:none}
:root{--bg:#1e1e1e;--bg-elev:#252526;--bg-elev2:#2d2d30;--bg-input:#3c3c3c;--fg:#d4d4d4;--fg-muted:#858585;--accent:#007acc;--accent-hover:#0098ff;--border:#3c3c3c;--select:#264f78;--kw:#569cd6;--str:#ce9178;--com:#6a9955;--num:#b5cea8;--fn:#dcdcaa;--err:#f44747;--err-bg:rgba(244,71,71,.15);--radius:8px;--radius-sm:6px;--radius-lg:12px}
body.theme-dark{--bg:#1e1e1e;--bg-elev:#252526;--bg-elev2:#2d2d30;--bg-input:#3c3c3c;--fg:#d4d4d4;--fg-muted:#858585;--accent:#007acc;--accent-hover:#0098ff;--border:#3c3c3c;--select:#264f78;--kw:#569cd6;--str:#ce9178;--com:#6a9955;--num:#b5cea8;--fn:#dcdcaa}
body.theme-midnight{--bg:#0d1117;--bg-elev:#161b22;--bg-elev2:#21262d;--bg-input:#30363d;--fg:#c9d1d9;--fg-muted:#8b949e;--accent:#1f6feb;--accent-hover:#388bfd;--border:#30363d;--select:#1f6feb;--kw:#ff7b72;--str:#a5d6ff;--com:#8b949e;--num:#79c0ff;--fn:#d2a8ff}
body.theme-black{--bg:#000;--bg-elev:#0a0a0a;--bg-elev2:#141414;--bg-input:#1f1f1f;--fg:#e0e0e0;--fg-muted:#666;--accent:#00acc1;--accent-hover:#00bcd4;--border:#1a1a1a;--select:#00acc1;--kw:#00e5ff;--str:#ffea00;--com:#666;--num:#ff9100;--fn:#76ff03}
body.theme-violet{--bg:#282a36;--bg-elev:#21222c;--bg-elev2:#2f3140;--bg-input:#44475a;--fg:#f8f8f2;--fg-muted:#6272a4;--accent:#bd93f9;--accent-hover:#cba6ff;--border:#44475a;--select:#44475a;--kw:#ff79c6;--str:#f1fa8c;--com:#6272a4;--num:#bd93f9;--fn:#50fa7b}
body.theme-one-dark{--bg:#282c34;--bg-elev:#21252b;--bg-elev2:#2c313a;--bg-input:#3a4049;--fg:#abb2bf;--fg-muted:#5c6370;--accent:#528bff;--accent-hover:#6ea0ff;--border:#181a1f;--select:#3e4451;--kw:#c678dd;--str:#98c379;--com:#5c6370;--num:#d19a66;--fn:#61afef}
body.theme-nord{--bg:#2e3440;--bg-elev:#3b4252;--bg-elev2:#434c5e;--bg-input:#4c566a;--fg:#d8dee9;--fg-muted:#616e88;--accent:#88c0d0;--accent-hover:#8fbcbb;--border:#4c566a;--select:#434c5e;--kw:#81a1c1;--str:#a3be8c;--com:#616e88;--num:#b48ead;--fn:#88c0d0}
body.theme-light{--bg:#fff;--bg-elev:#f3f3f3;--bg-elev2:#e8e8e8;--bg-input:#fff;--fg:#333;--fg-muted:#6a737d;--accent:#007acc;--accent-hover:#005a9e;--border:#e1e1e1;--select:#add6ff;--kw:#0000ff;--str:#a31515;--com:#008000;--num:#098658;--fn:#795e26}
body.theme-solarized{--bg:#fdf6e3;--bg-elev:#eee8d5;--bg-elev2:#e6dfc8;--bg-input:#fff;--fg:#657b83;--fg-muted:#93a1a1;--accent:#268bd2;--accent-hover:#1f6fa8;--border:#d9d2c0;--select:#b5cfd6;--kw:#859900;--str:#2aa198;--com:#93a1a1;--num:#d33682;--fn:#268bd2}
body{font-family:'Segoe UI','Cascadia Code',Consolas,sans-serif;background:#1e1e1e;background:var(--bg);color:#d4d4d4;color:var(--fg);height:100vh;overflow:hidden;font-size:13px}
#app{display:grid;grid-template-columns:240px 1fr;height:100vh}
#app.no-side{grid-template-columns:1fr}
#app.no-side .sidebar{display:none}
#app.no-out .terminal-wrap{display:none}
.sidebar{background:var(--bg-elev);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;min-height:0}
.sidebar-header{padding:14px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--border)}
.logo{color:var(--accent);font-size:16px}
.title{font-weight:600;font-size:13px;letter-spacing:.3px}
.sidebar-tabs{display:flex;border-bottom:1px solid var(--border)}
.tab{flex:1;padding:10px 12px;background:transparent;border:none;color:var(--fg-muted);cursor:pointer;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;font-family:inherit}
.tab:hover{color:var(--fg);background:var(--bg-elev2)}
.tab.active{color:var(--fg);border-bottom:2px solid var(--accent)}
.tab-content{display:none;flex:1;overflow:auto;min-height:0}
.tab-content.active{display:flex;flex-direction:column}
.explorer-header{padding:6px 8px 6px 14px;font-size:11px;font-weight:600;text-transform:uppercase;color:var(--fg-muted);letter-spacing:.5px;display:flex;align-items:center;gap:2px}
.explorer-header #workspace-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tree{padding:4px 8px;flex:1;min-height:40px}
.tree-item{padding:5px 10px;border-radius:var(--radius-sm);cursor:pointer;display:flex;align-items:center;gap:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tree-item:hover{background:var(--bg-elev2)}
.tree-item.active{background:var(--select)}
.tree-item .icon{font-size:12px;color:var(--fg-muted);width:14px;flex:none}
.tree-item.folder .icon{color:var(--accent)}
.tree-children{padding-left:14px;display:none}
.tree-children.open{display:block}
.empty{padding:20px 12px;text-align:center;color:var(--fg-muted)}
.empty .btn{margin-top:10px;border-color:var(--border)}
.srow{display:flex;align-items:center;padding-right:8px}
.srow .search-input{flex:1;width:auto}
.result{padding:6px 12px;cursor:pointer;border-bottom:1px solid var(--border);overflow:hidden}
.result:hover{background:var(--bg-elev2)}
.result .rf{font-size:11px;color:var(--accent);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.result .rt{font-size:12px;color:var(--fg-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.search-input,.input{width:calc(100% - 16px);padding:8px 12px;margin:8px;background:var(--bg-input);color:var(--fg);border:1px solid var(--border);border-radius:var(--radius-sm);font-size:12px;outline:none;font-family:inherit;-webkit-user-select:text;user-select:text}
.search-input:focus,.input:focus{border-color:var(--accent)}
.main{display:flex;flex-direction:column;overflow:hidden;background:var(--bg);min-width:0}
.menubar{height:30px;padding:0 6px;background:var(--bg-elev);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:2px}
.menubtn{padding:5px 10px;border-radius:var(--radius-sm);cursor:pointer;font-size:12px}
.menubtn:hover{background:var(--bg-elev2)}
.toolbar{height:44px;padding:0 12px;background:var(--bg-elev2);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:6px}
.btn{padding:7px 14px;background:transparent;color:var(--fg);border:1px solid transparent;border-radius:var(--radius-sm);cursor:pointer;font-size:12px;font-family:inherit}
.btn:hover{background:var(--bg-elev);border-color:var(--border)}
.btn:active{transform:scale(.97)}
.btn.primary{background:var(--accent);color:#fff}
.btn.primary:hover{background:var(--accent-hover)}
.btn.icon{padding:7px 10px;font-size:14px}
.btn.on{background:var(--select);border-color:var(--accent)}
.select{padding:6px 10px;background:var(--bg-input);color:var(--fg);border:1px solid var(--border);border-radius:var(--radius-sm);font-size:12px;font-family:inherit;cursor:pointer;outline:none}
.select:focus{border-color:var(--accent)}
.spacer{flex:1}
.tab-bar{height:36px;background:var(--bg-elev);border-bottom:1px solid var(--border);display:flex;align-items:stretch;overflow-x:auto;overflow-y:hidden}
.file-tab{padding:0 10px 0 14px;display:flex;align-items:center;gap:8px;background:var(--bg-elev);border-right:1px solid var(--border);cursor:pointer;font-size:12px;color:var(--fg-muted);white-space:nowrap}
.file-tab:hover{background:var(--bg-elev2);color:var(--fg)}
.file-tab.active{background:var(--bg);color:var(--fg);border-top:2px solid var(--accent)}
.tab-x::after{content:"✕";font-size:10px;opacity:.6;padding:2px 5px;border-radius:4px}
.tab-x.mod::after{content:"●";color:var(--accent);opacity:1}
.file-tab:hover .tab-x.mod::after{content:"✕";color:inherit}
.tab-x:hover::after{background:var(--bg-input);opacity:1}
.editor-wrap{flex:1;display:flex;flex-direction:column;min-height:0}
.editor-container{flex:1;display:flex;overflow:hidden;min-height:0;position:relative}
.line-numbers{padding:12px 10px 12px 16px;background:var(--bg);color:var(--fg-muted);font-family:'Cascadia Code',Consolas,'Courier New',monospace;font-size:13px;line-height:1.6;text-align:right;overflow:hidden;white-space:pre;min-width:50px}
.editor-highlight,.editor,.editor-find{padding:12px 16px;background:var(--bg);color:var(--fg);border:none;outline:none;resize:none;font-family:'Cascadia Code',Consolas,'Courier New',monospace;font-size:13px;line-height:1.6;tab-size:4;white-space:pre;word-wrap:normal;position:absolute;top:0;left:50px;right:0;bottom:0;width:calc(100% - 50px);height:100%}
.editor{overflow:auto}
.editor-highlight{z-index:1;pointer-events:none;overflow:hidden;padding-bottom:30px;padding-right:30px;background:transparent}
.editor-find{z-index:0;pointer-events:none;overflow:hidden;padding-bottom:30px;padding-right:30px;color:transparent}
.editor-find mark{background:rgba(255,200,0,.3);color:transparent;border-radius:2px}
.editor-find mark.cur{background:rgba(255,140,0,.65)}
.editor-highlight .kw{color:var(--kw)}
.editor-highlight .str{color:var(--str)}
.editor-highlight .com{color:var(--com);font-style:italic}
.editor-highlight .num{color:var(--num)}
.editor-highlight .fn{color:var(--fn)}
.editor{z-index:2;background:transparent;color:transparent;caret-color:var(--accent);-webkit-user-select:text;user-select:text}
.editor::selection{background:var(--select);color:transparent}
.findbar{display:none;position:absolute;top:6px;right:22px;z-index:5;background:var(--bg-elev2);border:1px solid var(--border);border-radius:var(--radius);padding:4px 6px}
.findbar .frow{display:flex;align-items:center;gap:2px}
.findbar .input{width:230px;margin:3px}
.findbar .btn{padding:5px 8px}
.fcount{min-width:70px;font-size:11px;color:var(--fg-muted);text-align:center}
.terminal-wrap{height:160px;background:var(--bg-elev);border-top:1px solid var(--border);display:flex;flex-direction:column}
.terminal-header{padding:8px 14px;font-size:11px;font-weight:600;text-transform:uppercase;color:var(--fg-muted);letter-spacing:.5px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border)}
.btn-ghost{background:transparent;border:none;color:var(--fg-muted);cursor:pointer;font-size:14px;padding:4px 8px;border-radius:var(--radius-sm);flex:none}
.btn-ghost:hover{color:var(--fg);background:var(--bg-elev2)}
.terminal{flex:1;padding:10px 14px;margin:0;overflow:auto;font-family:'Cascadia Code',Consolas,monospace;font-size:12px;line-height:1.5;color:var(--fg);white-space:pre-wrap;-webkit-user-select:text;user-select:text}
.statusbar{height:26px;padding:0 14px;background:var(--accent);color:#fff;display:flex;align-items:center;gap:10px;font-size:11px}
.statusbar .dot{opacity:.6}
.statusbar .clk{cursor:pointer}
.statusbar .clk:hover{text-decoration:underline}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.65);display:none;align-items:center;justify-content:center;z-index:100}
.modal-backdrop.open{display:flex}
.modal{background:var(--bg-elev);border:1px solid var(--border);border-radius:var(--radius-lg);padding:32px 36px;max-width:460px;width:90%;text-align:center;max-height:92vh;overflow:auto}
.modal h1,.modal h2{margin-bottom:10px;color:var(--fg)}
.modal .sub{color:var(--fg-muted);margin-bottom:20px}
.badge{display:inline-block;padding:4px 12px;background:var(--accent);color:#fff;font-size:11px;font-weight:600;border-radius:999px;margin-bottom:14px;letter-spacing:.5px}
.author{padding:16px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:20px}
.author strong{color:var(--accent)}
.author a{color:var(--accent);text-decoration:none;word-break:break-all;display:block;margin-top:6px;font-size:12px}
.author a:hover{text-decoration:underline}
.settings{text-align:left}
.settings .row{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:10px 0;border-bottom:1px solid var(--border)}
.settings .row:last-of-type{border-bottom:none}
.settings .input{margin:0;width:80px;text-align:center}
.actions{display:flex;gap:8px;justify-content:flex-end;margin-top:16px}
.dlg{text-align:left;max-width:440px}
.dlg .input{width:100%;margin:8px 0 0}
.dlg-msg{color:var(--fg-muted);white-space:pre-line;margin-bottom:4px}
.dlg-msg.err{color:var(--err)}
.dlg-msg.mono{font-family:Consolas,monospace;font-size:12px;white-space:pre;max-height:55vh;overflow:auto;-webkit-user-select:text;user-select:text}
.color-row{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border)}
.color-row label{font-size:12px;color:var(--fg-muted);min-width:100px}
.color-row input[type=color]{width:40px;height:28px;border:1px solid var(--border);border-radius:var(--radius-sm);background:transparent;cursor:pointer;padding:0}
.theme-list{max-height:200px;overflow:auto;margin:10px 0}
.theme-item{display:flex;justify-content:space-between;align-items:center;padding:8px 10px;border-radius:var(--radius-sm);cursor:pointer}
.theme-item:hover{background:var(--bg-elev2)}
.theme-item.active{background:var(--select)}
.theme-item .name{font-size:12px}
.theme-item .del{color:var(--err);cursor:pointer;font-size:14px;padding:2px 6px;border-radius:4px}
.theme-item .del:hover{background:var(--err-bg)}
.pal{align-items:flex-start;padding-top:12vh}
.palette{width:520px;max-width:92%;background:var(--bg-elev);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden}
.palette .input{width:100%;margin:0;border:none;border-bottom:1px solid var(--border);border-radius:0;padding:12px 16px;font-size:14px}
#pal-list{max-height:50vh;overflow:auto}
.pitem{display:flex;justify-content:space-between;gap:12px;padding:8px 16px;cursor:pointer;font-size:12px}
.pitem.sel{background:var(--select)}
.pitem .pg{color:var(--fg-muted);font-size:11px;margin-right:8px}
.pitem .pk{color:var(--fg-muted);font-size:11px}
#popup{position:fixed;display:none;z-index:300;min-width:220px;max-height:80vh;overflow:auto;background:var(--bg-elev2);border:1px solid var(--border);border-radius:var(--radius);padding:4px}
.mi{display:flex;justify-content:space-between;gap:24px;padding:6px 12px;border-radius:var(--radius-sm);cursor:pointer;font-size:12px;white-space:nowrap}
.mi:hover{background:var(--accent);color:#fff}
.mi.dis{opacity:.45;pointer-events:none}
.mk{color:var(--fg-muted);font-size:11px}
.mi:hover .mk{color:#fff}
.msep{height:1px;background:var(--border);margin:4px 6px}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--bg-input);border-radius:5px;border:2px solid var(--bg)}
::-webkit-scrollbar-thumb:hover{background:var(--fg-muted)}
</style>
</head>
<body class="theme-dark">
<div id="app">
  <aside class="sidebar">
    <div class="sidebar-header"><span class="logo">◆</span><span class="title">CodeEditorStudio</span></div>
    <nav class="sidebar-tabs">
      <button class="tab active" data-tab="explorer" data-i18n="explorer">Explorer</button>
      <button class="tab" data-tab="search" data-i18n="search">Search</button>
    </nav>
    <div class="tab-content active" id="tab-explorer">
      <div class="explorer-header">
        <span id="workspace-name"></span><span class="spacer"></span>
        <button class="btn-ghost" id="ex-new-file" data-i18n-title="newFile">📄</button>
        <button class="btn-ghost" id="ex-new-folder" data-i18n-title="newFolder">📁</button>
        <button class="btn-ghost" id="ex-refresh" data-i18n-title="refresh">↻</button>
        <button class="btn-ghost" id="ex-collapse" data-i18n-title="collapse">⊟</button>
      </div>
      <div class="tree" id="tree"></div>
    </div>
    <div class="tab-content" id="tab-search">
      <div class="srow">
        <input type="text" id="search-input" class="search-input" data-i18n-ph="searchPh">
        <button class="btn icon" id="search-case" data-i18n-title="caseT">Aa</button>
      </div>
      <div id="search-results"></div>
    </div>
  </aside>
  <main class="main">
    <div class="menubar" id="menubar"></div>
    <header class="toolbar">
      <button class="btn" id="btn-open-folder" data-i18n="openFolder">Open Folder</button>
      <button class="btn" id="btn-save" data-i18n="save">Save</button>
      <button class="btn" id="btn-run" data-i18n="run">Run</button>
      <button class="btn" id="btn-build" data-i18n="buildExe">Build .exe</button>
      <div class="spacer"></div>
      <select id="lang-select" class="select"></select>
      <select id="theme-select" class="select"></select>
      <select id="ui-lang-select" class="select">
        <option value="en">EN</option><option value="fr">FR</option>
      </select>
      <button class="btn icon" id="btn-settings" title="Settings">⚙</button>
      <button class="btn icon" id="btn-credits" title="Credits">✦</button>
    </header>
    <section class="editor-wrap">
      <div class="tab-bar" id="tab-bar"></div>
      <div class="editor-container">
        <div class="line-numbers" id="line-numbers">1</div>
        <pre class="editor-find" id="editor-find"></pre>
        <pre class="editor-highlight" id="editor-highlight"></pre>
        <textarea id="editor" class="editor" wrap="off" spellcheck="false" autocomplete="off" autocorrect="off" autocapitalize="off"></textarea>
        <div class="findbar" id="findbar">
          <div class="frow">
            <input type="text" id="find-input" class="input" data-i18n-ph="findPh">
            <button class="btn icon" id="find-case" data-i18n-title="caseT">Aa</button>
            <button class="btn icon" id="find-word" data-i18n-title="wordT">ab</button>
            <button class="btn icon" id="find-regex" data-i18n-title="regexT">.*</button>
            <span class="fcount" id="find-count"></span>
            <button class="btn icon" id="find-prev">↑</button>
            <button class="btn icon" id="find-next">↓</button>
            <button class="btn icon" id="find-close">✕</button>
          </div>
          <div class="frow">
            <input type="text" id="repl-input" class="input" data-i18n-ph="replPh">
            <button class="btn" id="repl-one" data-i18n="replace">Replace</button>
            <button class="btn" id="repl-all" data-i18n="replaceAll">Replace All</button>
          </div>
        </div>
      </div>
    </section>
    <section class="terminal-wrap">
      <div class="terminal-header"><span data-i18n="output">Output</span><button class="btn-ghost" id="btn-clear-terminal">✕</button></div>
      <pre id="terminal" class="terminal"></pre>
    </section>
    <footer class="statusbar">
      <span id="status-lang">Python</span><span class="dot">·</span>
      <span id="status-pos">Ln 1, Col 1</span><span class="dot">·</span>
      <span id="status-err" class="clk">0 errors</span><span class="dot">·</span>
      <span id="status-eol" class="clk">LF</span><span class="dot">·</span>
      <span id="status-theme">Dark+</span><span class="spacer"></span>
      <span id="status-msg">Ready</span>
    </footer>
  </main>
</div>
<div class="modal-backdrop" id="modal-credits">
  <div class="modal">
    <div class="badge">__VER__</div>
    <h1>CodeEditorStudio</h1>
    <p class="sub">Modern, lightweight code editor.</p>
    <div class="author">
      <p>Developed by <strong>@alexis_dpt</strong></p>
      <a href="https://github.com/alexis-dpt" target="_blank" rel="noopener">https://github.com/alexis-dpt</a>
    </div>
    <button class="btn primary" id="btn-close-credits">Close</button>
  </div>
</div>
<div class="modal-backdrop" id="modal-settings">
  <div class="modal settings">
    <h2 data-i18n="settings">Settings</h2>
    <label class="row"><span data-i18n="language">Language</span><select id="settings-lang-select" class="select"></select></label>
    <label class="row"><span data-i18n="theme">Theme</span><select id="settings-theme-select" class="select"></select></label>
    <label class="row"><span data-i18n="uiLang">UI Language</span><select id="settings-ui-lang" class="select"><option value="en">English</option><option value="fr">Français</option></select></label>
    <label class="row"><span data-i18n="fontSize">Font size</span><input type="number" id="settings-font-size" class="input" min="8" max="32"></label>
    <label class="row"><span data-i18n="tabSize">Tab size</span><input type="number" id="settings-tab-size" class="input" min="1" max="8"></label>
    <label class="row"><span data-i18n="autoSave">Auto save</span><input type="checkbox" id="settings-autosave"></label>
    <label class="row"><span data-i18n="autoClose">Auto-close brackets</span><input type="checkbox" id="settings-autoclose"></label>
    <label class="row"><span data-i18n="autoIndent">Auto indent</span><input type="checkbox" id="settings-autoindent"></label>
    <label class="row"><span data-i18n="restore">Reopen last folder</span><input type="checkbox" id="settings-restore"></label>
    <label class="row"><span data-i18n="showHidden">Show hidden files</span><input type="checkbox" id="settings-hidden"></label>
    <div class="actions">
      <button class="btn primary" id="btn-apply-settings" data-i18n="apply">Apply</button>
      <button class="btn" id="btn-close-settings" data-i18n="cancel">Cancel</button>
    </div>
  </div>
</div>
<div class="modal-backdrop" id="modal-custom-theme">
  <div class="modal settings">
    <h2>Custom Theme</h2>
    <label class="row"><span>Name</span><input type="text" id="ct-name" class="input" style="width:160px" placeholder="My Theme"></label>
    <div class="color-row"><label>Background</label><input type="color" id="ct-bg" value="#1e1e1e"></div>
    <div class="color-row"><label>Foreground</label><input type="color" id="ct-fg" value="#d4d4d4"></div>
    <div class="color-row"><label>Accent</label><input type="color" id="ct-accent" value="#007acc"></div>
    <div class="color-row"><label>Keyword</label><input type="color" id="ct-kw" value="#569cd6"></div>
    <div class="color-row"><label>String</label><input type="color" id="ct-str" value="#ce9178"></div>
    <div class="color-row"><label>Comment</label><input type="color" id="ct-com" value="#6a9955"></div>
    <div class="color-row"><label>Number</label><input type="color" id="ct-num" value="#b5cea8"></div>
    <div class="theme-list" id="ct-list"></div>
    <div class="actions">
      <button class="btn primary" id="btn-save-custom">Save</button>
      <button class="btn" id="btn-close-custom">Close</button>
    </div>
  </div>
</div>
<div class="modal-backdrop pal" id="modal-palette">
  <div class="palette">
    <input type="text" id="pal-input" class="input">
    <div id="pal-list"></div>
  </div>
</div>
<div class="modal-backdrop" id="modal-dialog">
  <div class="modal dlg">
    <h2 id="dlg-title"></h2>
    <p id="dlg-msg" class="dlg-msg"></p>
    <input type="text" id="dlg-input" class="input">
    <div class="actions" id="dlg-actions"></div>
  </div>
</div>
<div id="popup"></div>
<script>
const I18N={
en:{explorer:"Explorer",search:"Search",noFolder:"No folder opened",openFolder:"Open Folder",openFile:"Open File",save:"Save",saveAs:"Save As",saveAll:"Save All",run:"Run",buildExe:"Build .exe",output:"Output",ready:"Ready",settings:"Settings",language:"Language",theme:"Theme",uiLang:"UI Language",fontSize:"Font size",tabSize:"Tab size",apply:"Apply",cancel:"Cancel",saved:"Saved",noCode:"No code to run",compiling:"Compiling...",compiled:"Compiled",failed:"Failed",openFirst:"Save the file first",tooBig:"File too large",binary:"Binary file",newTab:"New Untitled File",newFile:"New File",newFolder:"New Folder",rename:"Rename",del:"Delete",duplicate:"Duplicate",cut:"Cut",copy:"Copy",paste:"Paste",copyPath:"Copy Path",copyRel:"Copy Relative Path",reveal:"Reveal in File Explorer",revealActive:"Reveal Active File",copyActivePath:"Copy Active File Path",refresh:"Refresh",collapse:"Collapse All",hidden:"Toggle Hidden Files",open:"Open",closeTab:"Close Tab",closeFolder:"Close Folder",recent:"Recent folders",clearRecent:"Clear recent",undo:"Undo",redo:"Redo",find:"Find",replace:"Replace",replaceAll:"Replace All",goLine:"Go to Line",searchFiles:"Search in Files",comment:"Toggle Comment",dupLine:"Duplicate Line",delLine:"Delete Line",lineUp:"Move Line Up",lineDown:"Move Line Down",sidebar:"Toggle Sidebar",toggleOut:"Toggle Output",zoomIn:"Zoom In",zoomOut:"Zoom Out",zoomReset:"Reset Zoom",palette:"Command Palette",customTheme:"Custom Theme",clearOut:"Clear Output",shortcuts:"Keyboard Shortcuts",about:"About",mFile:"File",mExplorer:"Explorer",mEdit:"Edit",mView:"View",mRun:"Run",mHelp:"Help",ok:"OK",discard:"Don't Save",unsavedT:"Unsaved changes",unsavedM:"{0} has unsaved changes.",delT:"Delete",delM:'Delete "{0}"? This cannot be undone.',exists:"Name already exists",invalid:"Invalid name or operation",notFound:"Not found",lineNo:"Line number",searchPh:"Search...",noRes:"No results",findPh:"Find",replPh:"Replace with",results:"{0} results",autoSave:"Auto save",autoClose:"Auto-close brackets",autoIndent:"Auto indent",restore:"Reopen last folder",showHidden:"Show hidden files",tabsFull:"Too many open tabs",untitled:"Untitled",cmdPh:"Type a command...",selected:"selected",emptyHint:"Open a folder to start",caseT:"Match case",copied:"Copied",wordT:"Whole word",regexT:"Regular expression",replacedN:"{0} replaced",findNextCmd:"Find Next",findPrevCmd:"Find Previous",badRx:"Invalid pattern",typePath:"Type the full path"},
fr:{explorer:"Explorateur",search:"Recherche",noFolder:"Aucun dossier ouvert",openFolder:"Ouvrir dossier",openFile:"Ouvrir fichier",save:"Enregistrer",saveAs:"Enregistrer sous",saveAll:"Tout enregistrer",run:"Exécuter",buildExe:"Compiler .exe",output:"Sortie",ready:"Prêt",settings:"Paramètres",language:"Langage",theme:"Thème",uiLang:"Langue interface",fontSize:"Taille police",tabSize:"Taille tabulation",apply:"Appliquer",cancel:"Annuler",saved:"Enregistré",noCode:"Aucun code à exécuter",compiling:"Compilation...",compiled:"Compilé",failed:"Échec",openFirst:"Enregistrez d'abord le fichier",tooBig:"Fichier trop volumineux",binary:"Fichier binaire",newTab:"Nouveau fichier vierge",newFile:"Nouveau fichier",newFolder:"Nouveau dossier",rename:"Renommer",del:"Supprimer",duplicate:"Dupliquer",cut:"Couper",copy:"Copier",paste:"Coller",copyPath:"Copier le chemin",copyRel:"Copier le chemin relatif",reveal:"Afficher dans l'explorateur",revealActive:"Afficher le fichier actif",copyActivePath:"Copier le chemin du fichier actif",refresh:"Actualiser",collapse:"Tout réduire",hidden:"Afficher/masquer fichiers cachés",open:"Ouvrir",closeTab:"Fermer l'onglet",closeFolder:"Fermer le dossier",recent:"Dossiers récents",clearRecent:"Effacer les récents",undo:"Annuler",redo:"Rétablir",find:"Rechercher",replace:"Remplacer",replaceAll:"Tout remplacer",goLine:"Aller à la ligne",searchFiles:"Rechercher dans les fichiers",comment:"Commenter/décommenter",dupLine:"Dupliquer la ligne",delLine:"Supprimer la ligne",lineUp:"Monter la ligne",lineDown:"Descendre la ligne",sidebar:"Afficher/masquer la barre latérale",toggleOut:"Afficher/masquer la sortie",zoomIn:"Zoom avant",zoomOut:"Zoom arrière",zoomReset:"Réinitialiser le zoom",palette:"Palette de commandes",customTheme:"Thème personnalisé",clearOut:"Effacer la sortie",shortcuts:"Raccourcis clavier",about:"À propos",mFile:"Fichier",mExplorer:"Explorateur",mEdit:"Édition",mView:"Affichage",mRun:"Exécution",mHelp:"Aide",ok:"OK",discard:"Ne pas enregistrer",unsavedT:"Modifications non enregistrées",unsavedM:"{0} contient des modifications non enregistrées.",delT:"Supprimer",delM:'Supprimer "{0}" ? Cette action est irréversible.',exists:"Ce nom existe déjà",invalid:"Nom ou opération invalide",notFound:"Introuvable",lineNo:"Numéro de ligne",searchPh:"Rechercher...",noRes:"Aucun résultat",findPh:"Rechercher",replPh:"Remplacer par",results:"{0} résultats",autoSave:"Enregistrement automatique",autoClose:"Fermeture auto des parenthèses",autoIndent:"Indentation automatique",restore:"Rouvrir le dernier dossier",showHidden:"Afficher les fichiers cachés",tabsFull:"Trop d'onglets ouverts",untitled:"Sans titre",cmdPh:"Tapez une commande...",selected:"sélectionnés",emptyHint:"Ouvrez un dossier pour commencer",caseT:"Respecter la casse",copied:"Copié",wordT:"Mot entier",regexT:"Expression régulière",replacedN:"{0} remplacement(s)",findNextCmd:"Occurrence suivante",findPrevCmd:"Occurrence précédente",badRx:"Motif invalide",typePath:"Saisissez le chemin complet"}
};
const THEMES=[{id:"dark",name:"Dark+ (VS Code)"},{id:"midnight",name:"Midnight Blue"},{id:"black",name:"Pure Black"},{id:"violet",name:"Violet (Dracula)"},{id:"one-dark",name:"Gris (One Dark)"},{id:"nord",name:"Nord"},{id:"light",name:"Light (VS Code)"},{id:"solarized",name:"Light (Solarized)"}];
const LANGS=["Python","JavaScript","HTML","JSON","C/C++","Markdown","Plain Text"];
const EXT_LANG={py:"Python",pyw:"Python",js:"JavaScript",mjs:"JavaScript",jsx:"JavaScript",ts:"JavaScript",html:"HTML",htm:"HTML",json:"JSON",c:"C/C++",h:"C/C++",cpp:"C/C++",hpp:"C/C++",cc:"C/C++",md:"Markdown",txt:"Plain Text"};
const COMMENT={Python:"# ",JavaScript:"// ","C/C++":"// "};
const PAIRS={"(":")","[":"]","{":"}",'"':'"',"'":"'"};
const PY_KW=new Set("def class return if elif else for while in import from as try except finally with lambda True False None and or not is pass break continue yield global nonlocal assert raise del async await match case".split(" "));
const JS_KW=new Set("const let var function return if else for while do switch case break continue new this class extends import export from default try catch finally throw typeof instanceof in of async await yield true false null undefined void delete".split(" "));
const C_KW=new Set("int char float double void long short unsigned signed struct union enum typedef static const extern return if else for while do switch case break continue sizeof class public private protected namespace using template typename new delete true false nullptr include define auto bool".split(" "));
const JSON_KW=new Set(["true","false","null"]);
const PY_RX=/(#[^\n]*)|("{3}[\s\S]*?(?:"{3}|$)|'{3}[\s\S]*?(?:'{3}|$)|"(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?)|(\b\d[\w.]*)|([A-Za-z_]\w*)(\()?/g;
const JS_RX=/(\/\/[^\n]*|\/\*[\s\S]*?(?:\*\/|$))|("(?:\\.|[^"\\\n])*"?|'(?:\\.|[^'\\\n])*'?|`(?:\\[\s\S]|[^`\\])*`?)|(\b\d[\w.]*)|([A-Za-z_$][\w$]*)(\()?/g;
const HL={Python:{rx:PY_RX,kw:PY_KW},JavaScript:{rx:JS_RX,kw:JS_KW},JSON:{rx:JS_RX,kw:JSON_KW},"C/C++":{rx:JS_RX,kw:C_KW}};
const MAX_HL=300000,MAX_SYNTAX=500000,MAX_TERM=40000,MAX_TABS=12;
const ESC={"&":"&amp;","<":"&lt;",">":"&gt;"};
const TOKEN="__TOKEN__";
const state={theme:"dark",lang:"Python",defLang:"Python",uiLang:"en",fontSize:13,tabSize:4,autoSave:false,autoClose:true,autoIndent:true,restore:false,showHidden:false,workspace:null,customThemes:[],recent:[],errors:[],tabs:[],cur:-1};
const $=s=>document.querySelector(s);
const $$=s=>document.querySelectorAll(s);
const editor=$("#editor"),highlight=$("#editor-highlight"),lineNumbers=$("#line-numbers"),terminal=$("#terminal"),tree=$("#tree"),popup=$("#popup"),findLayer=$("#editor-find");
const nodes=new Map(),expanded=new Set();
let hlFrame=0,stFrame=0,errTimer=0,cfgTimer=0,searchTimer=0,msgTimer=0,autoTimer=0,findTimer=0,lineCount=1,selected=null,fileClip=null,openMenu=null,dlgResolve=null,dlgPrimary=null,palIdx=0,palList=[];
function t(k,...a){let s=(I18N[state.uiLang]||I18N.en)[k]||I18N.en[k]||k;a.forEach((v,i)=>{s=s.replace("{"+i+"}",v)});return s}
function esc(s){return s.replace(/[&<>]/g,c=>ESC[c])}
function kd(k){return k.replace("ArrowUp","↑").replace("ArrowDown","↓")}
function sepOf(p){return p.includes("\\")?"\\":"/"}
function dirname(p){const i=Math.max(p.lastIndexOf("/"),p.lastIndexOf("\\"));return i<=0?p:p.slice(0,i)}
function basename(p){return p.slice(Math.max(p.lastIndexOf("/"),p.lastIndexOf("\\"))+1)}
function isUnder(p,base){return p===base||p.startsWith(base+sepOf(base))}
function remapPath(p,o,n){return p===o?n:n+p.slice(o.length)}
function relPath(p){return state.workspace&&isUnder(p,state.workspace)&&p!==state.workspace?p.slice(state.workspace.length+1):p}
function langFor(name){const i=name.lastIndexOf(".");return i<0?"Plain Text":(EXT_LANG[name.slice(i+1).toLowerCase()]||"Plain Text")}
function curTab(){return state.tabs[state.cur]||null}
async function api(path,body){const r=await fetch("/api",{method:"POST",headers:{"Content-Type":"application/json","X-Token":TOKEN},body:JSON.stringify({e:path,d:body||{}})});return r.json()}
function setMsg(s){const el=$("#status-msg");el.textContent=s;clearTimeout(msgTimer);msgTimer=setTimeout(()=>{el.textContent=t("ready")},2500)}
function log(msg){let s=terminal.textContent+msg+"\n";if(s.length>MAX_TERM)s=s.slice(-MAX_TERM*.75);terminal.textContent=s;terminal.scrollTop=terminal.scrollHeight}
function copyText(s){const ta=document.createElement("textarea");ta.value=s;ta.style.cssText="position:fixed;opacity:0;-webkit-user-select:text;user-select:text";document.body.appendChild(ta);ta.select();try{document.execCommand("copy")}catch(e){}ta.remove();setMsg(t("copied"))}
function applyI18n(){
  $$("[data-i18n]").forEach(el=>{el.textContent=t(el.dataset.i18n)});
  $$("[data-i18n-title]").forEach(el=>{el.title=t(el.dataset.i18nTitle)});
  $$("[data-i18n-ph]").forEach(el=>{el.placeholder=t(el.dataset.i18nPh)});
  $("#status-msg").textContent=t("ready");
  updateWorkspaceLabel();buildMenubar();if(!state.workspace)renderEmptyTree();renderTabs();
}
function injectTheme(th){if($("#theme-"+th.id))return;const s=document.createElement("style");s.id="theme-"+th.id;s.textContent="body.theme-"+th.id+"{--bg:"+th.bg+";--bg-elev:"+th.bg+";--bg-elev2:"+th.bg+";--bg-input:"+th.bg+";--fg:"+th.fg+";--accent:"+th.accent+";--accent-hover:"+th.accent+";--border:"+th.bg+";--select:"+th.accent+";--kw:"+th.kw+";--str:"+th.str+";--com:"+th.com+";--num:"+th.num+";--fn:"+th.kw+"}";document.head.appendChild(s)}
function applyTheme(id,persist=true){document.body.className="theme-"+id;state.theme=id;const th=THEMES.find(x=>x.id===id)||state.customThemes.find(x=>x.id===id);$("#status-theme").textContent=th?th.name:id;if(persist)saveConfig()}
function highlightCode(code){
  const h=HL[state.lang];
  if(!h||code.length>MAX_HL)return esc(code)+"\n";
  const rx=h.rx,kw=h.kw;let out="",last=0,m;rx.lastIndex=0;
  while((m=rx.exec(code))){
    if(m.index>last)out+=esc(code.slice(last,m.index));
    if(m[1]!==undefined)out+='<span class="com">'+esc(m[1])+'</span>';
    else if(m[2]!==undefined)out+='<span class="str">'+esc(m[2])+'</span>';
    else if(m[3]!==undefined)out+='<span class="num">'+m[3]+'</span>';
    else{const w=m[4];if(kw.has(w))out+='<span class="kw">'+w+'</span>'+(m[5]||"");else if(m[5])out+='<span class="fn">'+w+'</span>(';else out+=w}
    last=rx.lastIndex;
  }
  if(last<code.length)out+=esc(code.slice(last));
  return out+"\n";
}
function scheduleHighlight(){if(hlFrame)return;hlFrame=requestAnimationFrame(()=>{hlFrame=0;highlight.innerHTML=highlightCode(editor.value);syncLayers()})}
function countLines(v){let n=1,i=-1;while((i=v.indexOf("\n",i+1))!==-1)n++;return n}
function updateLineNumbers(force){const n=countLines(editor.value);if(n===lineCount&&!force)return;lineCount=n;const a=new Array(n);for(let i=0;i<n;i++)a[i]=i+1;lineNumbers.textContent=a.join("\n");lineNumbers.scrollTop=editor.scrollTop}
function renderStatus(){
  stFrame=0;
  const v=editor.value,pos=editor.selectionStart,end=editor.selectionEnd;
  let line=1,i=-1;while((i=v.indexOf("\n",i+1))!==-1&&i<pos)line++;
  const ls=pos?v.lastIndexOf("\n",pos-1):-1;
  $("#status-pos").textContent="Ln "+line+", Col "+(pos-ls)+(end>pos?" ("+(end-pos)+" "+t("selected")+")":"");
  $("#status-lang").textContent=state.lang;
  const tab=curTab();$("#status-eol").textContent=tab?tab.eol:"LF";
  const n=state.errors.length;$("#status-err").textContent=n+" error"+(n!==1?"s":"");
  $("#status-err").title=n?("Ln "+state.errors[0].line+": "+state.errors[0].msg):"";
}
function updateStatus(){if(!stFrame)stFrame=requestAnimationFrame(renderStatus)}
function setTitle(){
  const tab=curTab();
  document.title=(tab&&tab.modified?"● ":"")+(tab?(tab.name||t("untitled")):"")+" — CodeEditorStudio __VER__";
}
function syncLang(){$("#lang-select").value=state.lang;$("#settings-lang-select").value=state.lang;$("#status-lang").textContent=state.lang}
function syncLayers(){const st=editor.scrollTop,sl=editor.scrollLeft;highlight.scrollTop=st;highlight.scrollLeft=sl;findLayer.scrollTop=st;findLayer.scrollLeft=sl}
function applyFont(){const px=state.fontSize+"px";editor.style.fontSize=px;highlight.style.fontSize=px;findLayer.style.fontSize=px;findLayer.style.tabSize=state.tabSize;lineNumbers.style.fontSize=px;editor.style.tabSize=state.tabSize;highlight.style.tabSize=state.tabSize}
function zoom(d){state.fontSize=d===0?13:Math.min(32,Math.max(8,state.fontSize+d));applyFont();saveConfig()}
async function checkSyntax(){
  const v=editor.value;
  if(!(state.lang==="Python"||state.lang==="JSON")||!v.trim()||v.length>MAX_SYNTAX){if(state.errors.length){state.errors=[];updateStatus()}return}
  try{const r=await api("/api/check-syntax",{code:v,lang:state.lang});state.errors=r.errors||[]}catch(e){state.errors=[]}
  updateStatus();
}
function scheduleSyntaxCheck(){clearTimeout(errTimer);errTimer=setTimeout(checkSyntax,700)}
function saveConfig(now){
  clearTimeout(cfgTimer);
  const run=()=>api("/api/config",{theme:state.theme,uiLang:state.uiLang,lang:state.defLang,fontSize:state.fontSize,tabSize:state.tabSize,customThemes:state.customThemes,autoSave:state.autoSave,autoClose:state.autoClose,autoIndent:state.autoIndent,restore:state.restore,showHidden:state.showHidden,recent:state.recent});
  if(now)return run();
  cfgTimer=setTimeout(run,300);
}
async function loadConfig(){
  const cfg=await api("/api/config");
  state.uiLang=cfg.uiLang||"en";state.fontSize=cfg.fontSize||13;state.tabSize=cfg.tabSize||4;
  state.defLang=cfg.lang||"Python";state.lang=state.defLang;state.customThemes=cfg.customThemes||[];
  state.autoSave=!!cfg.autoSave;state.autoClose=cfg.autoClose!==false;state.autoIndent=cfg.autoIndent!==false;
  state.restore=!!cfg.restore;state.showHidden=!!cfg.showHidden;state.recent=cfg.recent||[];
  state.customThemes.forEach(injectTheme);
  applyTheme(cfg.theme||"dark",false);applyFont();
  $("#ui-lang-select").value=state.uiLang;$("#settings-ui-lang").value=state.uiLang;
  applyI18n();renderCustomThemeList();
}
function showTab(tab){
  editor.value=tab.content;tab.content=null;
  state.lang=tab.lang;state.errors=[];
  syncLang();updateLineNumbers(true);scheduleHighlight();renderTabs();setTitle();
  editor.scrollTop=tab.scroll||0;editor.scrollLeft=0;lineNumbers.scrollTop=editor.scrollTop;
  try{editor.setSelectionRange(tab.sel[0],tab.sel[1])}catch(e){}
  updateStatus();scheduleSyntaxCheck();scheduleFind();
}
function stashCurrent(){
  const tab=curTab();if(!tab)return;
  tab.scroll=editor.scrollTop;tab.sel=[editor.selectionStart,editor.selectionEnd];
  tab.content=(tab.modified||!tab.path)?editor.value:null;
}
async function enter(i){
  state.cur=i;const tab=state.tabs[i];
  if(tab.content===null){
    const r=await api("/api/read",{path:tab.path});
    if(r.error){log(tab.name+": "+t(r.error));tab.content=""}else{tab.content=r.content;tab.eol=r.eol}
  }
  showTab(tab);
}
async function activate(i){if(i===state.cur||i<0||i>=state.tabs.length)return;stashCurrent();await enter(i)}
function makeRoom(){
  if(state.tabs.length<MAX_TABS)return true;
  const i=state.tabs.findIndex(x=>!x.modified&&x.path);
  if(i<0){log(t("tabsFull"));return false}
  state.tabs.splice(i,1);
  if(i<state.cur)state.cur--;else if(i===state.cur)state.cur=-1;
  return true;
}
function newTab(){
  stashCurrent();if(!makeRoom())return;
  state.tabs.push({path:null,name:null,content:"",modified:false,eol:"LF",scroll:0,sel:[0,0],lang:state.defLang});
  state.cur=state.tabs.length-1;showTab(state.tabs[state.cur]);
}
async function openFile(path,name,line){
  const i=state.tabs.findIndex(x=>x.path===path);
  if(i<0){
    const r=await api("/api/read",{path});
    if(r.error){log(t(r.error==="too_big"?"tooBig":r.error==="binary"?"binary":r.error));return}
    stashCurrent();if(!makeRoom())return;
    state.tabs.push({path,name,content:r.content,modified:false,eol:r.eol,scroll:0,sel:[0,0],lang:langFor(name)});
    state.cur=state.tabs.length-1;showTab(state.tabs[state.cur]);
  }else await activate(i);
  if(line)gotoLine(line);
}
async function openFileDialog(){
  const r=await api("/api/open-file",state.workspace?{dir:state.workspace}:null);
  if(r&&r.nodialog){
    const p=await dialog({title:t("openFile"),msg:t("typePath"),input:true,value:"",buttons:OKCANCEL()});
    if(p.btn==="ok"&&p.value.trim())openFile(p.value.trim(),basename(p.value.trim()));
    return;
  }
  if(r&&r.path)openFile(r.path,r.name);
}
function renderTabs(){
  const bar=$("#tab-bar");bar.textContent="";const frag=document.createDocumentFragment();let act=null;
  state.tabs.forEach((tab,i)=>{
    const el=document.createElement("div");el.className="file-tab"+(i===state.cur?" active":"");el.title=tab.path||"";
    const n=document.createElement("span");n.textContent=tab.name||t("untitled");
    const x=document.createElement("span");x.className="tab-x"+(tab.modified?" mod":"");
    x.onclick=e=>{e.stopPropagation();closeTab(i)};
    el.append(n,x);el.onclick=()=>activate(i);el.onauxclick=e=>{if(e.button===1)closeTab(i)};
    frag.appendChild(el);if(i===state.cur)act=el;
  });
  bar.appendChild(frag);if(act)act.scrollIntoView({block:"nearest",inline:"nearest"});
}
function markModified(){
  const tab=curTab();if(!tab)return;
  if(!tab.modified){tab.modified=true;renderTabs();setTitle()}
  if(state.autoSave&&tab.path){clearTimeout(autoTimer);autoTimer=setTimeout(()=>{if(tab.modified&&tab.path&&state.tabs.includes(tab))saveTab(tab)},1200)}
}
async function saveTab(tab,as){
  if(!tab)return false;
  const content=tab===curTab()?editor.value:tab.content;
  if(!tab.path||as){
    let r=await api("/api/save-as",{content,eol:tab.eol,dir:state.workspace,name:tab.name});
    if(r&&r.nodialog){
      const p=await dialog({title:t("saveAs"),msg:t("typePath"),input:true,value:(state.workspace?state.workspace+sepOf(state.workspace):"")+(tab.name||"untitled.py"),buttons:OKCANCEL()});
      if(p.btn!=="ok"||!p.value.trim())return false;
      r=await api("/api/save-as",{content,eol:tab.eol,path:p.value.trim()});
    }
    if(!r||!r.path)return false;
    tab.path=r.path;tab.name=r.name;tab.lang=langFor(r.name);
    if(tab===curTab()){state.lang=tab.lang;syncLang();scheduleHighlight()}
    if(state.workspace&&isUnder(r.path,state.workspace))refreshDir(dirname(r.path));
  }else{
    const r=await api("/api/save",{path:tab.path,content,eol:tab.eol});
    if(r.error){log(t(r.error));return false}
  }
  tab.modified=false;if(tab!==curTab())tab.content=null;
  renderTabs();setTitle();setMsg(t("saved"));return true;
}
async function saveAll(){for(const tab of state.tabs.slice())if(tab.modified)await saveTab(tab)}
async function removeTab(i){
  const wasCur=i===state.cur;
  state.tabs.splice(i,1);
  if(!state.tabs.length){state.cur=-1;newTab();return}
  if(wasCur)await enter(Math.min(i,state.tabs.length-1));
  else{if(i<state.cur)state.cur--;renderTabs();setTitle()}
}
async function closeTab(i=state.cur){
  const tab=state.tabs[i];if(!tab)return;
  if(tab.modified){
    const r=await dialog({title:t("unsavedT"),msg:t("unsavedM",tab.name||t("untitled")),buttons:[{l:t("save"),v:"save",p:1},{l:t("discard"),v:"no"},{l:t("cancel"),v:null}]});
    if(r.btn===null)return;
    if(r.btn==="save"&&!(await saveTab(tab)))return;
  }
  await removeTab(state.tabs.indexOf(tab));
}
async function closeTabsUnder(p){for(let i=state.tabs.length-1;i>=0;i--){const x=state.tabs[i];if(x&&x.path&&isUnder(x.path,p))await removeTab(i)}}
function remapTabs(o,n){state.tabs.forEach(x=>{if(x.path&&isUnder(x.path,o)){x.path=remapPath(x.path,o,n);x.name=basename(x.path);x.lang=langFor(x.name)}});const c=curTab();if(c){state.lang=c.lang;syncLang();scheduleHighlight()}renderTabs();setTitle()}
function dialog(o){
  return new Promise(res=>{
    dlgResolve=res;
    $("#dlg-title").textContent=o.title||"";
    const m=$("#dlg-msg");m.textContent=o.msg||"";m.className="dlg-msg"+(o.err?" err":"")+(o.mono?" mono":"");m.style.display=o.msg?"block":"none";
    const inp=$("#dlg-input");inp.style.display=o.input?"block":"none";inp.value=o.value||"";
    const btns=o.buttons||OKCANCEL(),act=$("#dlg-actions");act.textContent="";
    const pr=btns.find(b=>b.p);dlgPrimary=pr?pr.v:null;
    for(const b of btns){const el=document.createElement("button");el.className="btn"+(b.p?" primary":"");el.textContent=b.l;el.onclick=()=>closeDialog(b.v);act.appendChild(el)}
    $("#modal-dialog").classList.add("open");
    if(o.input){inp.focus();inp.select()}
  });
}
function OKCANCEL(){return[{l:t("ok"),v:"ok",p:1},{l:t("cancel"),v:null}]}
function closeDialog(v){
  $("#modal-dialog").classList.remove("open");
  const r=dlgResolve;dlgResolve=null;
  if(r)r({btn:v===undefined?null:v,value:$("#dlg-input").value});
}
async function askName(title,value,action){
  let err="";
  for(;;){
    const r=await dialog({title,msg:err,err:!!err,input:true,value,buttons:OKCANCEL()});
    if(r.btn!=="ok")return null;
    value=r.value;
    const res=await action(value);
    if(res&&!res.error)return res;
    err=t((res&&res.error)||"invalid");
  }
}
function updateWorkspaceLabel(){$("#workspace-name").textContent=state.workspace?basename(state.workspace)||state.workspace:t("noFolder")}
function renderEmptyTree(){
  tree.textContent="";const d=document.createElement("div");d.className="empty";
  const p=document.createElement("div");p.textContent=t("emptyHint");
  const b=document.createElement("button");b.className="btn";b.textContent=t("openFolder");b.onclick=()=>openFolder();
  d.append(p,b);tree.appendChild(d);
}
function select(rec){if(selected&&selected.el)selected.el.classList.remove("active");selected=rec;if(rec&&rec.el)rec.el.classList.add("active")}
function selectPath(p){const rec=nodes.get(p);if(rec)select(rec)}
function targetDir(){if(selected)return selected.dir?selected.path:dirname(selected.path);return state.workspace}
async function listInto(path,container){const r=await api("/api/list-dir",{path});container.textContent="";renderNodes(r.files||[],container)}
function renderNodes(files,parent){
  const frag=document.createDocumentFragment();
  for(const n of files){
    const item=document.createElement("div");item.className="tree-item"+(n.dir?" folder":"");
    const icon=document.createElement("span");icon.className="icon";icon.textContent=n.dir?"▸":"·";
    const label=document.createElement("span");label.textContent=n.name;
    item.append(icon,label);frag.appendChild(item);
    const rec={el:item,icon,dir:n.dir,path:n.path,name:n.name};
    nodes.set(n.path,rec);
    if(selected&&selected.path===n.path){selected=rec;item.classList.add("active")}
    if(n.dir){const ch=document.createElement("div");ch.className="tree-children";frag.appendChild(ch);rec.ch=ch;if(expanded.has(n.path))setOpen(rec,true)}
    item.onclick=()=>{select(rec);if(n.dir)setOpen(rec,!rec.ch.classList.contains("open"));else openFile(n.path,n.name)};
    item.oncontextmenu=e=>{e.preventDefault();e.stopPropagation();select(rec);showPopup(ctxItems(rec),e.clientX,e.clientY)};
  }
  parent.appendChild(frag);
}
async function setOpen(rec,open){
  rec.ch.classList.toggle("open",open);rec.icon.textContent=open?"▾":"▸";
  if(open){expanded.add(rec.path);if(!rec.ch.dataset.loaded){rec.ch.dataset.loaded="1";await listInto(rec.path,rec.ch)}}
  else expanded.delete(rec.path);
}
function clearMapUnder(base){for(const k of [...nodes.keys()])if(k!==base&&isUnder(k,base))nodes.delete(k)}
async function refreshRoot(){
  if(!state.workspace)return;
  const r=await api("/api/list-dir",{path:state.workspace});
  nodes.clear();tree.textContent="";renderNodes(r.files||[],tree);
}
async function refreshDir(path,open){
  if(!state.workspace)return;
  if(path===state.workspace){await refreshRoot();return}
  const rec=nodes.get(path);if(!rec||!rec.ch)return;
  clearMapUnder(path);
  if(open){expanded.add(path);rec.ch.classList.add("open");rec.icon.textContent="▾"}
  if(rec.ch.dataset.loaded||open){rec.ch.dataset.loaded="1";await listInto(path,rec.ch)}
}
function addRecent(p){state.recent=[p].concat(state.recent.filter(x=>x!==p)).slice(0,8);saveConfig()}
async function openFolder(path){
  const res=await api("/api/open-folder",path?{path}:null);
  if(res&&res.nodialog){
    const r=await dialog({title:t("openFolder"),msg:t("typePath"),input:true,value:"",buttons:OKCANCEL()});
    if(r.btn==="ok"&&r.value.trim())return openFolder(r.value.trim());
    return;
  }
  if(!res||!res.path){if(path){state.recent=state.recent.filter(x=>x!==path);saveConfig()}return}
  state.workspace=res.path;expanded.clear();nodes.clear();selected=null;
  updateWorkspaceLabel();tree.textContent="";renderNodes(res.files||[],tree);addRecent(res.path);showSide("explorer");
}
function closeFolder(){state.workspace=null;expanded.clear();nodes.clear();selected=null;updateWorkspaceLabel();renderEmptyTree()}
async function collapseAll(){expanded.clear();await refreshRoot()}
async function toggleHidden(){state.showHidden=!state.showHidden;await saveConfig(true);refreshRoot()}
async function opNewFile(dir){
  dir=dir||targetDir();if(!dir){log(t("noFolder"));return}
  const r=await askName(t("newFile"),"",v=>api("/api/create-file",{parent:dir,name:v}));
  if(!r)return;
  await refreshDir(dir,true);selectPath(r.path);openFile(r.path,r.name);
}
async function opNewFolder(dir){
  dir=dir||targetDir();if(!dir){log(t("noFolder"));return}
  const r=await askName(t("newFolder"),"",v=>api("/api/create-folder",{parent:dir,name:v}));
  if(!r)return;
  await refreshDir(dir,true);selectPath(r.path);
}
async function opRename(rec){
  rec=rec||selected;if(!rec)return;
  const r=await askName(t("rename"),rec.name,v=>api("/api/rename",{path:rec.path,name:v}));
  if(!r||r.path===rec.path)return;
  remapTabs(rec.path,r.path);
  for(const e of [...expanded])if(isUnder(e,rec.path)){expanded.delete(e);expanded.add(remapPath(e,rec.path,r.path))}
  if(selected&&selected.path===rec.path)selected={path:r.path,dir:rec.dir,name:r.name};
  await refreshDir(dirname(rec.path));selectPath(r.path);
}
async function opDelete(rec){
  rec=rec||selected;if(!rec)return;
  const r=await dialog({title:t("delT"),msg:t("delM",rec.name),buttons:[{l:t("del"),v:"ok",p:1},{l:t("cancel"),v:null}]});
  if(r.btn!=="ok")return;
  const res=await api("/api/delete",{path:rec.path});
  if(res.error){log(t(res.error));return}
  await closeTabsUnder(rec.path);
  for(const e of [...expanded])if(isUnder(e,rec.path))expanded.delete(e);
  if(selected&&selected.path===rec.path)select(null);
  await refreshDir(dirname(rec.path));
}
async function opDuplicate(rec){
  rec=rec||selected;if(!rec)return;
  const res=await api("/api/duplicate",{path:rec.path});
  if(res.error){log(t(res.error));return}
  await refreshDir(dirname(rec.path));selectPath(res.path);
}
function opClip(rec,cut){rec=rec||selected;if(!rec)return;fileClip={path:rec.path,cut:!!cut,dir:rec.dir};setMsg(t(cut?"cut":"copy")+": "+rec.name)}
async function opPaste(rec){
  if(!fileClip)return;
  rec=rec||selected;
  const dest=rec?(rec.dir?rec.path:dirname(rec.path)):state.workspace;if(!dest)return;
  const res=await api("/api/paste",{src:fileClip.path,dest_dir:dest,cut:fileClip.cut});
  if(res.error){log(t(res.error));return}
  const src=fileClip.path;
  if(fileClip.cut&&res.path!==src){
    remapTabs(src,res.path);
    for(const e of [...expanded])if(isUnder(e,src)){expanded.delete(e);expanded.add(remapPath(e,src,res.path))}
    fileClip=null;await refreshDir(dirname(src));
  }
  await refreshDir(dest,true);selectPath(res.path);
}
function opReveal(rec){rec=rec||selected;const p=rec?rec.path:state.workspace;if(p)api("/api/reveal",{path:p})}
function ctxItems(rec){
  const items=[];
  if(rec.dir)items.push({l:t("newFile"),f:()=>opNewFile(rec.path)},{l:t("newFolder"),f:()=>opNewFolder(rec.path)},{sep:1});
  else items.push({l:t("open"),f:()=>openFile(rec.path,rec.name)},{sep:1});
  items.push(
    {l:t("rename"),k:"F2",f:()=>opRename(rec)},
    {l:t("duplicate"),f:()=>opDuplicate(rec)},
    {l:t("del"),k:"Del",f:()=>opDelete(rec)},{sep:1},
    {l:t("cut"),k:"Ctrl+X",f:()=>opClip(rec,true)},
    {l:t("copy"),k:"Ctrl+C",f:()=>opClip(rec,false)},
    {l:t("paste"),k:"Ctrl+V",dis:!fileClip,f:()=>opPaste(rec)},{sep:1},
    {l:t("copyPath"),f:()=>copyText(rec.path)},
    {l:t("copyRel"),f:()=>copyText(relPath(rec.path))},
    {l:t("reveal"),f:()=>opReveal(rec)});
  if(rec.dir)items.push({sep:1},{l:t("refresh"),f:()=>refreshDir(rec.path)});
  return items;
}
function rootItems(){
  return[
    {l:t("newFile"),f:()=>opNewFile(state.workspace)},
    {l:t("newFolder"),f:()=>opNewFolder(state.workspace)},{sep:1},
    {l:t("paste"),k:"Ctrl+V",dis:!fileClip,f:()=>opPaste(null)},{sep:1},
    {l:t("refresh"),f:()=>refreshRoot()},
    {l:t("collapse"),f:collapseAll},
    {l:t("reveal"),f:()=>opReveal(null)}
  ];
}
function showPopup(items,x,y){
  popup.textContent="";
  for(const it of items){
    if(it.sep){const s=document.createElement("div");s.className="msep";popup.appendChild(s);continue}
    const el=document.createElement("div");el.className="mi"+(it.dis?" dis":"");
    const a=document.createElement("span");a.textContent=(it.c?"✓ ":"")+it.l;
    const b=document.createElement("span");b.className="mk";b.textContent=it.k?kd(it.k):"";
    el.append(a,b);
    if(!it.dis&&it.f)el.onclick=()=>{hidePopup();it.f()};
    popup.appendChild(el);
  }
  popup.style.display="block";
  const w=popup.offsetWidth,h=popup.offsetHeight;
  popup.style.left=Math.max(0,Math.min(x,innerWidth-w-4))+"px";
  popup.style.top=Math.max(0,Math.min(y,innerHeight-h-4))+"px";
}
function hidePopup(){popup.style.display="none";openMenu=null}
const GROUPS=["File","Explorer","Edit","View","Run","Help"];
const GKEY={File:"mFile",Explorer:"mExplorer",Edit:"mEdit",View:"mView",Run:"mRun",Help:"mHelp"};
const C=[
{g:"File",l:"newTab",k:"Alt+N",f:()=>newTab()},
{g:"File",l:"openFile",k:"Alt+O",f:openFileDialog},
{g:"File",l:"openFolder",k:"Ctrl+O",f:()=>openFolder()},
{g:"File",sep:1},
{g:"File",l:"save",k:"Ctrl+S",f:()=>saveTab(curTab())},
{g:"File",l:"saveAs",k:"Ctrl+Shift+S",f:()=>saveTab(curTab(),true)},
{g:"File",l:"saveAll",k:"Alt+S",f:saveAll},
{g:"File",sep:1},
{g:"File",l:"revealActive",f:()=>{const c=curTab();if(c&&c.path)api("/api/reveal",{path:c.path})}},
{g:"File",l:"copyActivePath",f:()=>{const c=curTab();if(c&&c.path)copyText(c.path)}},
{g:"File",sep:1},
{g:"File",l:"closeTab",k:"Alt+W",f:()=>closeTab()},
{g:"File",l:"closeFolder",f:closeFolder},
{g:"Explorer",l:"newFile",k:"Alt+Shift+N",f:()=>opNewFile()},
{g:"Explorer",l:"newFolder",f:()=>opNewFolder()},
{g:"Explorer",sep:1},
{g:"Explorer",l:"rename",k:"F2",ex:1,f:()=>opRename()},
{g:"Explorer",l:"duplicate",f:()=>opDuplicate()},
{g:"Explorer",l:"del",k:"Delete",ex:1,f:()=>opDelete()},
{g:"Explorer",sep:1},
{g:"Explorer",l:"cut",k:"Ctrl+X",ex:1,f:()=>opClip(null,true)},
{g:"Explorer",l:"copy",k:"Ctrl+C",ex:1,f:()=>opClip(null,false)},
{g:"Explorer",l:"paste",k:"Ctrl+V",ex:1,f:()=>opPaste()},
{g:"Explorer",sep:1},
{g:"Explorer",l:"copyPath",f:()=>{if(selected)copyText(selected.path)}},
{g:"Explorer",l:"copyRel",f:()=>{if(selected)copyText(relPath(selected.path))}},
{g:"Explorer",l:"reveal",f:()=>opReveal()},
{g:"Explorer",sep:1},
{g:"Explorer",l:"refresh",f:()=>refreshRoot()},
{g:"Explorer",l:"collapse",f:collapseAll},
{g:"Explorer",l:"hidden",chk:()=>state.showHidden,f:toggleHidden},
{g:"Edit",l:"undo",k:"Ctrl+Z",nb:1,f:()=>{editor.focus();document.execCommand("undo")}},
{g:"Edit",l:"redo",k:"Ctrl+Y",nb:1,f:()=>{editor.focus();document.execCommand("redo")}},
{g:"Edit",sep:1},
{g:"Edit",l:"find",k:"Ctrl+F",f:()=>openFind(false)},
{g:"Edit",l:"replace",k:"Ctrl+H",f:()=>openFind(true)},
{g:"Edit",l:"findNextCmd",k:"F3",f:()=>findNext(1)},
{g:"Edit",l:"findPrevCmd",k:"Shift+F3",f:()=>findNext(-1)},
{g:"Edit",l:"goLine",k:"Ctrl+G",f:goLineDialog},
{g:"Edit",l:"searchFiles",k:"Ctrl+Shift+F",f:()=>{showSide("search");$("#search-input").focus()}},
{g:"Edit",sep:1},
{g:"Edit",l:"comment",k:"Ctrl+/",f:toggleComment},
{g:"Edit",l:"dupLine",k:"Ctrl+D",f:dupLine},
{g:"Edit",l:"delLine",k:"Ctrl+Shift+K",f:delLine},
{g:"Edit",l:"lineUp",k:"Alt+ArrowUp",f:()=>moveLine(-1)},
{g:"Edit",l:"lineDown",k:"Alt+ArrowDown",f:()=>moveLine(1)},
{g:"View",l:"sidebar",k:"Ctrl+B",f:()=>$("#app").classList.toggle("no-side")},
{g:"View",l:"toggleOut",k:"Ctrl+J",f:()=>$("#app").classList.toggle("no-out")},
{g:"View",sep:1},
{g:"View",l:"zoomIn",k:"Ctrl+=",f:()=>zoom(1)},
{g:"View",l:"zoomOut",k:"Ctrl+-",f:()=>zoom(-1)},
{g:"View",l:"zoomReset",k:"Ctrl+0",f:()=>zoom(0)},
{g:"View",sep:1},
{g:"View",l:"palette",k:"Ctrl+Shift+P",f:openPalette},
{g:"View",l:"customTheme",k:"Alt+T",f:()=>$("#modal-custom-theme").classList.add("open")},
{g:"View",l:"settings",k:"Ctrl+,",f:openSettings},
{g:"Run",l:"run",k:"F5",f:runCode},
{g:"Run",l:"buildExe",k:"F6",f:buildExe},
{g:"Run",l:"clearOut",f:()=>{terminal.textContent=""}},
{g:"Help",l:"shortcuts",f:showShortcuts},
{g:"Help",l:"about",f:()=>$("#modal-credits").classList.add("open")}
];
const KEYMAP={};
C.forEach(c=>{if(c.k&&!c.nb)KEYMAP[c.k.toLowerCase()]=c});
KEYMAP["ctrl++"]=KEYMAP["ctrl+="];
function menuItems(g){
  const out=[];
  for(const c of C){
    if(c.g!==g)continue;
    if(c.sep){out.push({sep:1});continue}
    out.push({l:t(c.l),k:c.k,c:c.chk?c.chk():false,f:c.f});
  }
  if(g==="File"){
    out.push({sep:1},{l:t("recent"),dis:1});
    state.recent.slice(0,6).forEach(p=>out.push({l:basename(p)||p,f:()=>openFolder(p)}));
    if(state.recent.length)out.push({l:t("clearRecent"),f:()=>{state.recent=[];saveConfig()}});
  }
  return out;
}
function buildMenubar(){
  const bar=$("#menubar");bar.textContent="";
  GROUPS.forEach(g=>{
    const b=document.createElement("div");b.className="menubtn";b.textContent=t(GKEY[g]);
    b.onmousedown=e=>{e.preventDefault();if(openMenu===g){hidePopup();return}openGroup(g,b)};
    b.onmouseenter=()=>{if(openMenu&&openMenu!==g)openGroup(g,b)};
    bar.appendChild(b);
  });
}
function openGroup(g,btn){const r=btn.getBoundingClientRect();showPopup(menuItems(g),r.left,r.bottom);openMenu=g}
function evKey(e){
  const k=e.key,p=[];
  if(e.ctrlKey||e.metaKey)p.push("ctrl");
  if(e.altKey)p.push("alt");
  if(e.shiftKey&&(/^[a-zA-Z]$/.test(k)||k.length>1))p.push("shift");
  p.push(k.toLowerCase());
  return p.join("+");
}
function showShortcuts(){
  const lines=C.filter(c=>c.k).map(c=>kd(c.k).padEnd(18)+t(c.l));
  lines.push("Tab / Shift+Tab".padEnd(18)+"Indent / Outdent","Ctrl+Wheel".padEnd(18)+t("zoomIn")+" / "+t("zoomOut"));
  dialog({title:t("shortcuts"),msg:lines.join("\n"),mono:true,buttons:[{l:t("ok"),v:"ok",p:1}]});
}
function openPalette(){
  const m=$("#modal-palette"),inp=$("#pal-input");
  m.classList.add("open");inp.value="";inp.placeholder=t("cmdPh");palIdx=0;renderPalette();inp.focus();
}
function renderPalette(){
  const q=$("#pal-input").value.trim().toLowerCase(),box=$("#pal-list");box.textContent="";
  palList=C.filter(c=>c.l&&(!q||t(c.l).toLowerCase().includes(q)));
  if(palIdx>=palList.length)palIdx=0;
  const frag=document.createDocumentFragment();
  palList.forEach((c,i)=>{
    const el=document.createElement("div");el.className="pitem"+(i===palIdx?" sel":"");
    const a=document.createElement("span"),g=document.createElement("span"),l=document.createElement("span");
    g.className="pg";g.textContent=t(GKEY[c.g]);l.textContent=t(c.l);a.append(g,l);
    const k=document.createElement("span");k.className="pk";k.textContent=c.k?kd(c.k):"";
    el.append(a,k);el.onclick=()=>runCmd(c);frag.appendChild(el);
  });
  box.appendChild(frag);
}
function runCmd(c){$("#modal-palette").classList.remove("open");setTimeout(()=>c.f(),0)}
function lineBlock(){
  const v=editor.value,s=editor.selectionStart,e=editor.selectionEnd;
  const bs=s?v.lastIndexOf("\n",s-1)+1:0;
  const ee=(e>s&&v[e-1]==="\n")?e-1:e;
  let be=v.indexOf("\n",ee);if(be<0)be=v.length;
  return{bs,be};
}
function editRange(s,e,text){
  editor.focus();
  if(text===""&&s===e)return;
  editor.setSelectionRange(s,e);
  const ok=text===""?document.execCommand("delete"):document.execCommand("insertText",false,text);
  if(!ok){editor.setRangeText(text,s,e,"end");onEdit()}
}
function onEdit(){updateLineNumbers();scheduleHighlight();markModified();scheduleSyntaxCheck();updateStatus();scheduleFind()}
function revealPos(i){
  const v=editor.value;let line=0,p=-1;
  while((p=v.indexOf("\n",p+1))!==-1&&p<i)line++;
  const ls=i?v.lastIndexOf("\n",i-1)+1:0,col=i-ls;
  const lh=state.fontSize*1.6,cw=state.fontSize*.6,top=line*lh+12;
  if(top<editor.scrollTop+lh||top>editor.scrollTop+editor.clientHeight-2*lh)editor.scrollTop=Math.max(0,top-editor.clientHeight/3);
  const x=col*cw;
  if(x<editor.scrollLeft||x>editor.scrollLeft+editor.clientWidth-60)editor.scrollLeft=Math.max(0,x-editor.clientWidth/3);
}
function gotoLine(n){
  const v=editor.value;let pos=0;
  for(let i=0;i<n-1;i++){const k=v.indexOf("\n",pos);if(k<0)break;pos=k+1}
  editor.focus();editor.setSelectionRange(pos,pos);revealPos(pos);updateStatus();
}
async function goLineDialog(){
  const r=await dialog({title:t("goLine"),msg:t("lineNo")+" (1-"+lineCount+")",input:true,value:"",buttons:OKCANCEL()});
  if(r.btn==="ok"){const n=parseInt(r.value);if(n>0)gotoLine(n)}
}
function toggleComment(){
  const p=COMMENT[state.lang];if(!p)return;
  const v=editor.value,{bs,be}=lineBlock(),pt=p.trimEnd();
  const lines=v.slice(bs,be).split("\n");
  const act=lines.filter(l=>l.trim());
  const un=act.length>0&&act.every(l=>l.trimStart().startsWith(pt));
  const nt=lines.map(l=>{
    if(!l.trim())return l;
    const ind=l.length-l.trimStart().length;
    if(un)return l.slice(0,ind)+l.slice(ind+pt.length).replace(/^ /,"");
    return l.slice(0,ind)+p+l.slice(ind);
  }).join("\n");
  editRange(bs,be,nt);editor.setSelectionRange(bs,bs+nt.length);
}
function dupLine(){
  const v=editor.value,{bs,be}=lineBlock(),tx=v.slice(bs,be);
  editRange(be,be,"\n"+tx);editor.setSelectionRange(be+1,be+1+tx.length);
}
function delLine(){
  const v=editor.value,{bs,be}=lineBlock();
  if(be<v.length)editRange(bs,be+1,"");else if(bs>0)editRange(bs-1,be,"");else editRange(bs,be,"");
}
function moveLine(dir){
  const v=editor.value,{bs,be}=lineBlock(),tx=v.slice(bs,be);
  if(dir<0){
    if(bs===0)return;
    const ps=v.lastIndexOf("\n",bs-2)+1,prev=v.slice(ps,bs-1);
    editRange(ps,be,tx+"\n"+prev);editor.setSelectionRange(ps,ps+tx.length);
  }else{
    if(be>=v.length)return;
    let ne=v.indexOf("\n",be+1);if(ne<0)ne=v.length;
    const next=v.slice(be+1,ne);
    editRange(bs,ne,next+"\n"+tx);editor.setSelectionRange(bs+next.length+1,bs+next.length+1+tx.length);
  }
}
function tabKey(shift){
  const v=editor.value,s=editor.selectionStart,e=editor.selectionEnd,sp=" ".repeat(state.tabSize);
  if(!shift&&!v.slice(s,e).includes("\n")){editRange(s,e,sp);return}
  const {bs,be}=lineBlock(),lines=v.slice(bs,be).split("\n");
  const rx=new RegExp("^(?:\\t| {1,"+state.tabSize+"})");
  const out=lines.map(l=>shift?l.replace(rx,""):(l?sp+l:l));
  const nt=out.join("\n");
  editRange(bs,be,nt);
  if(s===e){const p=Math.max(bs,s+out[0].length-lines[0].length);editor.setSelectionRange(p,p)}
  else editor.setSelectionRange(bs,bs+nt.length);
}
function enterKey(){
  const v=editor.value,s=editor.selectionStart,e=editor.selectionEnd;
  const ls=s?v.lastIndexOf("\n",s-1)+1:0,pre=v.slice(ls,s),ind=pre.match(/^[ \t]*/)[0],tr=pre.trimEnd();
  const opener=/[{(\[]$/.test(tr),open=opener||(state.lang==="Python"&&tr.endsWith(":"));
  const extra=open?" ".repeat(state.tabSize):"";
  const nx=v[e],closing=opener&&nx&&"})]".includes(nx);
  if(closing){editRange(s,e,"\n"+ind+extra+"\n"+ind);const p=s+1+ind.length+extra.length;editor.setSelectionRange(p,p)}
  else editRange(s,e,"\n"+ind+extra);
}
function autoPair(e){
  const k=e.key,v=editor.value,s=editor.selectionStart,en=editor.selectionEnd;
  if(s!==en&&PAIRS[k]){const sel=v.slice(s,en);editRange(s,en,k+sel+PAIRS[k]);editor.setSelectionRange(s+1,s+1+sel.length);return true}
  if(s===en&&")]}\"'".includes(k)&&v[s]===k){editor.setSelectionRange(s+1,s+1);return true}
  if(PAIRS[k]&&s===en){
    const pv=v[s-1]||"",nx=v[s]||"";
    if(k==='"'||k==="'"){if(/\w/.test(pv)||/\w/.test(nx))return false}
    else if(nx&&/\w/.test(nx))return false;
    editRange(s,s,k+PAIRS[k]);editor.setSelectionRange(s+1,s+1);return true;
  }
  return false;
}
const fb=$("#findbar"),fi=$("#find-input"),ri=$("#repl-input"),fcount=$("#find-count");
const ESCRX=/[.*+?^${}()|[\]\\]/g;
let matches=[],findFrame=0;
function flag(id){return $(id).classList.contains("on")}
function findRegex(){
  const q=fi.value;if(!q)return null;
  let src=flag("#find-regex")?q:q.replace(ESCRX,"\\$&");
  if(flag("#find-word"))src="\\b(?:"+src+")\\b";
  try{return new RegExp(src,flag("#find-case")?"g":"gi")}catch(e){return undefined}
}
function collectMatches(){
  const rx=findRegex();if(!rx)return[];
  const v=editor.value,out=[];let m;
  while((m=rx.exec(v))&&out.length<5000){if(!m[0].length){rx.lastIndex++;continue}out.push([m.index,m.index+m[0].length])}
  return out;
}
function scheduleFind(){if(fb.style.display!=="block"||findFrame)return;findFrame=requestAnimationFrame(()=>{findFrame=0;refreshFind()})}
function refreshFind(){
  if(fb.style.display!=="block"){findLayer.textContent="";return}
  const bad=findRegex()===undefined;
  matches=collectMatches();
  const s=editor.selectionStart,e=editor.selectionEnd,cur=matches.findIndex(m=>m[0]===s&&m[1]===e);
  fcount.textContent=!fi.value?"":bad?t("badRx"):matches.length?(cur>=0?(cur+1)+" / ":"")+matches.length+(matches.length>=5000?"+":""):t("noRes");
  const v=editor.value;
  if(!matches.length||v.length>MAX_HL){findLayer.textContent="";return}
  let out="",last=0;
  matches.forEach((m,i)=>{out+=esc(v.slice(last,m[0]))+"<mark"+(i===cur?' class="cur"':"")+">"+esc(v.slice(m[0],m[1]))+"</mark>";last=m[1]});
  findLayer.innerHTML=out+esc(v.slice(last))+"\n";
  syncLayers();
}
function openFind(focusRepl){
  fb.style.display="block";
  const s=editor.value.slice(editor.selectionStart,editor.selectionEnd);
  if(s&&!s.includes("\n"))fi.value=s;
  const el=focusRepl?ri:fi;el.focus();el.select();refreshFind();
}
function closeFind(){fb.style.display="none";findLayer.textContent="";editor.focus()}
function findNext(dir,fromStart){
  matches=collectMatches();
  if(!matches.length){refreshFind();return}
  const s=editor.selectionStart,e=editor.selectionEnd;let idx;
  if(fromStart)idx=matches.findIndex(m=>m[0]>=s);
  else if(dir>0)idx=matches.findIndex(m=>m[0]>=e);
  else{idx=-1;for(let i=matches.length-1;i>=0;i--)if(matches[i][1]<=s){idx=i;break}}
  if(idx<0)idx=(dir>0||fromStart)?0:matches.length-1;
  const m=matches[idx];editor.setSelectionRange(m[0],m[1]);revealPos(m[0]);refreshFind();
}
function replText(sel){
  const rx=findRegex();if(!rx)return null;
  const one=new RegExp(rx.source,rx.flags.replace("g",""));
  return flag("#find-regex")?sel.replace(one,ri.value):sel.replace(one,()=>ri.value);
}
function replaceOne(){
  const s=editor.selectionStart,e=editor.selectionEnd;
  if(s!==e&&collectMatches().some(m=>m[0]===s&&m[1]===e)){
    const r=replText(editor.value.slice(s,e));
    if(r!==null){editRange(s,e,r);editor.setSelectionRange(s+r.length,s+r.length)}
  }
  findNext(1);ri.focus();
}
function replaceAll(){
  const rx=findRegex();if(!rx)return;
  const v=editor.value,n=collectMatches().length;if(!n)return;
  const nv=flag("#find-regex")?v.replace(rx,ri.value):v.replace(rx,()=>ri.value);
  if(nv===v)return;
  const st=editor.scrollTop;
  editor.focus();editor.select();
  if(!document.execCommand("insertText",false,nv)){editor.value=nv;onEdit()}
  editor.setSelectionRange(0,0);editor.scrollTop=st;
  setMsg(t("replacedN",n));scheduleFind();ri.focus();
}
function showSide(name){
  $$(".tab").forEach(x=>x.classList.toggle("active",x.dataset.tab===name));
  $$(".tab-content").forEach(x=>x.classList.toggle("active",x.id==="tab-"+name));
  $("#app").classList.remove("no-side");
}
async function doSearch(){
  const q=$("#search-input").value.trim(),box=$("#search-results");
  box.textContent="";if(q.length<2||!state.workspace)return;
  const res=await api("/api/search",{root:state.workspace,query:q,case:$("#search-case").classList.contains("on")});
  const list=res.results||[];
  if(!list.length){const d=document.createElement("div");d.className="empty";d.textContent=t("noRes");box.appendChild(d);return}
  const frag=document.createDocumentFragment();
  for(const r of list){
    const el=document.createElement("div");el.className="result";
    const f=document.createElement("div");f.className="rf";f.textContent=relPath(r.path)+":"+r.line;
    const x=document.createElement("div");x.className="rt";x.textContent=r.text;
    el.append(f,x);el.onclick=()=>openFile(r.path,r.name,r.line);frag.appendChild(el);
  }
  box.appendChild(frag);
}
async function runCode(){
  const tab=curTab();
  if(!editor.value.trim()){log(t("noCode"));return}
  if(tab.path&&tab.modified)await saveTab(tab);
  log("$ python "+(tab.name||"untitled.py"));
  const r=await api("/api/run",{content:editor.value});
  if(r&&r.error)log(r.error);
}
async function buildExe(){
  const tab=curTab();
  if(!tab||!tab.path){log(t("openFirst"));return}
  if(tab.modified)await saveTab(tab);
  log(t("compiling"));
  const res=await api("/api/build",{path:tab.path});
  if(res.ok)log(t("compiled")+": "+res.output);else log(t("failed")+": "+(res.error||""));
}
function setupThemes(){
  const sel=$("#theme-select"),selS=$("#settings-theme-select");
  THEMES.concat(state.customThemes).forEach(th=>{sel.appendChild(new Option(th.name,th.id));selS.appendChild(new Option(th.name,th.id))});
  sel.value=state.theme;selS.value=state.theme;
  sel.onchange=e=>{applyTheme(e.target.value);selS.value=e.target.value};
  selS.onchange=e=>{applyTheme(e.target.value);sel.value=e.target.value};
}
function changeLang(l){
  state.lang=l;state.defLang=l;const tab=curTab();if(tab)tab.lang=l;
  syncLang();scheduleHighlight();scheduleSyntaxCheck();updateStatus();saveConfig();
}
function setupLangs(){
  const sel=$("#lang-select"),selS=$("#settings-lang-select");
  LANGS.forEach(l=>{sel.appendChild(new Option(l,l));selS.appendChild(new Option(l,l))});
  sel.value=state.lang;selS.value=state.lang;sel.onchange=e=>changeLang(e.target.value);
}
function openSettings(){
  $("#settings-font-size").value=state.fontSize;$("#settings-tab-size").value=state.tabSize;
  $("#settings-theme-select").value=state.theme;$("#settings-lang-select").value=state.lang;$("#settings-ui-lang").value=state.uiLang;
  $("#settings-autosave").checked=state.autoSave;$("#settings-autoclose").checked=state.autoClose;
  $("#settings-autoindent").checked=state.autoIndent;$("#settings-restore").checked=state.restore;$("#settings-hidden").checked=state.showHidden;
  $("#modal-settings").classList.add("open");
}
function setupSettings(){
  $("#btn-settings").onclick=openSettings;
  $("#btn-close-settings").onclick=()=>$("#modal-settings").classList.remove("open");
  $("#btn-apply-settings").onclick=async()=>{
    state.fontSize=Math.min(32,Math.max(8,parseInt($("#settings-font-size").value)||13));
    state.tabSize=Math.min(8,Math.max(1,parseInt($("#settings-tab-size").value)||4));
    state.uiLang=$("#settings-ui-lang").value;
    state.autoSave=$("#settings-autosave").checked;state.autoClose=$("#settings-autoclose").checked;
    state.autoIndent=$("#settings-autoindent").checked;state.restore=$("#settings-restore").checked;
    const hid=$("#settings-hidden").checked,hidChanged=hid!==state.showHidden;state.showHidden=hid;
    applyFont();applyTheme($("#settings-theme-select").value,false);
    $("#theme-select").value=state.theme;$("#ui-lang-select").value=state.uiLang;
    applyI18n();changeLang($("#settings-lang-select").value);
    $("#modal-settings").classList.remove("open");
    await saveConfig(true);
    if(hidChanged)refreshRoot();
  };
}
function renderCustomThemeList(){
  const list=$("#ct-list");list.textContent="";
  state.customThemes.forEach(th=>{
    const item=document.createElement("div");item.className="theme-item"+(state.theme===th.id?" active":"");
    const n=document.createElement("span");n.className="name";n.textContent=th.name;
    const d=document.createElement("span");d.className="del";d.textContent="✕";
    n.onclick=()=>{applyTheme(th.id);$("#theme-select").value=th.id;renderCustomThemeList()};
    d.onclick=e=>{
      e.stopPropagation();
      state.customThemes=state.customThemes.filter(x=>x.id!==th.id);
      $$("option").forEach(o=>{if(o.value===th.id)o.remove()});
      const st=$("#theme-"+th.id);if(st)st.remove();
      if(state.theme===th.id){applyTheme("dark");$("#theme-select").value="dark"}
      saveConfig();renderCustomThemeList();
    };
    item.append(n,d);list.appendChild(item);
  });
}
function setupCustomTheme(){
  $("#btn-close-custom").onclick=()=>$("#modal-custom-theme").classList.remove("open");
  $("#btn-save-custom").onclick=()=>{
    const name=$("#ct-name").value.trim()||"Custom",id="custom-"+Date.now();
    const th={id,name,bg:$("#ct-bg").value,fg:$("#ct-fg").value,accent:$("#ct-accent").value,kw:$("#ct-kw").value,str:$("#ct-str").value,com:$("#ct-com").value,num:$("#ct-num").value};
    state.customThemes.push(th);injectTheme(th);applyTheme(id);
    $("#theme-select").appendChild(new Option(name,id));$("#settings-theme-select").appendChild(new Option(name,id));
    $("#theme-select").value=id;renderCustomThemeList();$("#modal-custom-theme").classList.remove("open");
  };
}
function setupEvents(){
  editor.addEventListener("input",onEdit);
  let sc=false;
  editor.addEventListener("scroll",()=>{if(sc)return;sc=true;requestAnimationFrame(()=>{sc=false;lineNumbers.scrollTop=editor.scrollTop;syncLayers()})},{passive:true});
  editor.addEventListener("keyup",updateStatus);
  editor.addEventListener("click",updateStatus);
  editor.addEventListener("wheel",e=>{if(e.ctrlKey){e.preventDefault();zoom(e.deltaY<0?1:-1)}},{passive:false});
  editor.addEventListener("keydown",e=>{
    if(e.isComposing)return;
    if(e.key==="Tab"){e.preventDefault();tabKey(e.shiftKey);return}
    if(e.key==="Enter"&&state.autoIndent&&!e.ctrlKey&&!e.altKey&&!e.shiftKey&&!e.metaKey){e.preventDefault();enterKey();return}
    if(e.key==="Backspace"&&state.autoClose&&!e.ctrlKey&&!e.altKey){
      const s=editor.selectionStart;
      if(s>0&&s===editor.selectionEnd){const v=editor.value,o=PAIRS[v[s-1]];if(o&&o===v[s]){e.preventDefault();editRange(s-1,s+1,"")}}
      return;
    }
    if(state.autoClose&&e.key.length===1){
      const ag=e.ctrlKey&&e.altKey;
      if(!ag&&(e.ctrlKey||e.altKey||e.metaKey))return;
      if(autoPair(e))e.preventDefault();
    }
  });
  $("#btn-open-folder").onclick=()=>openFolder();
  $("#btn-save").onclick=()=>saveTab(curTab());
  $("#btn-run").onclick=runCode;
  $("#btn-build").onclick=buildExe;
  $("#btn-credits").onclick=()=>$("#modal-credits").classList.add("open");
  $("#btn-close-credits").onclick=()=>$("#modal-credits").classList.remove("open");
  $("#btn-clear-terminal").onclick=()=>{terminal.textContent=""};
  $("#ui-lang-select").onchange=e=>{state.uiLang=e.target.value;$("#settings-ui-lang").value=state.uiLang;applyI18n();saveConfig()};
  $("#ex-new-file").onclick=()=>opNewFile();
  $("#ex-new-folder").onclick=()=>opNewFolder();
  $("#ex-refresh").onclick=()=>refreshRoot();
  $("#ex-collapse").onclick=collapseAll;
  tree.addEventListener("click",e=>{if(e.target===tree)select(null)});
  tree.addEventListener("contextmenu",e=>{e.preventDefault();if(!state.workspace)return;select(null);showPopup(rootItems(),e.clientX,e.clientY)});
  $("#search-input").addEventListener("input",()=>{clearTimeout(searchTimer);searchTimer=setTimeout(doSearch,400)});
  $("#search-case").onclick=e=>{e.currentTarget.classList.toggle("on");doSearch()};
  $$(".tab").forEach(tab=>{tab.onclick=()=>showSide(tab.dataset.tab)});
  fi.addEventListener("input",()=>{clearTimeout(findTimer);findTimer=setTimeout(()=>findNext(1,true),120)});
  fi.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();findNext(e.shiftKey?-1:1)}});
  ri.addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();replaceOne()}});
  $("#find-next").onclick=()=>findNext(1);
  $("#find-prev").onclick=()=>findNext(-1);
  $("#find-close").onclick=closeFind;
  ["#find-case","#find-word","#find-regex"].forEach(id=>{$(id).onclick=e=>{e.currentTarget.classList.toggle("on");findNext(1,true)}});
  $("#repl-one").onclick=replaceOne;
  $("#repl-all").onclick=replaceAll;
  $("#status-err").onclick=()=>{if(state.errors.length)gotoLine(state.errors[0].line)};
  $("#status-eol").onclick=()=>{const tab=curTab();if(!tab)return;tab.eol=tab.eol==="LF"?"CRLF":"LF";tab.modified=true;renderTabs();setTitle();updateStatus()};
  $("#dlg-input").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();closeDialog(dlgPrimary)}});
  const pin=$("#pal-input");
  pin.addEventListener("input",()=>{palIdx=0;renderPalette()});
  pin.addEventListener("keydown",e=>{
    if(e.key==="ArrowDown"||e.key==="ArrowUp"){
      e.preventDefault();if(!palList.length)return;
      palIdx=(palIdx+(e.key==="ArrowDown"?1:-1)+palList.length)%palList.length;renderPalette();
      const el=$("#pal-list").children[palIdx];if(el)el.scrollIntoView({block:"nearest"});
    }else if(e.key==="Enter"){e.preventDefault();if(palList[palIdx])runCmd(palList[palIdx])}
  });
  $("#modal-palette").addEventListener("mousedown",e=>{if(e.target.id==="modal-palette")e.currentTarget.classList.remove("open")});
  document.addEventListener("mousedown",e=>{if(!popup.contains(e.target)&&!e.target.closest(".menubtn"))hidePopup()});
  document.addEventListener("contextmenu",e=>{if(!e.target.closest("textarea,input"))e.preventDefault()});
  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"){
      const m=$(".modal-backdrop.open");
      if(m){if(m.id==="modal-dialog")closeDialog(null);else m.classList.remove("open");return}
      hidePopup();if(fb.style.display==="block")closeFind();return;
    }
    if(e.key==="Enter"&&$("#modal-dialog").classList.contains("open")&&document.activeElement.tagName!=="BUTTON"&&document.activeElement.id!=="dlg-input"){e.preventDefault();closeDialog(dlgPrimary);return}
    if(e.ctrlKey&&!e.altKey&&!e.shiftKey&&["r","p","u"].includes(e.key.toLowerCase())){e.preventDefault();return}
    if($(".modal-backdrop.open"))return;
    if(e.ctrlKey&&e.altKey)return;
    const c=KEYMAP[evKey(e)];if(!c)return;
    if(c.ex){
      const a=document.activeElement;
      if(a&&(a.tagName==="TEXTAREA"||a.tagName==="INPUT"||a.tagName==="SELECT"))return;
      if(!selected||String(window.getSelection()))return;
    }
    e.preventDefault();c.f();
  },true);
}
async function boot(){
  await api("/api/ping");
  await loadConfig();
  setupThemes();setupLangs();setupSettings();setupCustomTheme();setupEvents();
  newTab();
  updateStatus();renderEmptyTree();
  if(state.restore&&state.recent[0])openFolder(state.recent[0]);
}
window.addEventListener("beforeunload",e=>{if(state.tabs.some(x=>x.modified)){e.preventDefault();e.returnValue=""}});
window.addEventListener("pagehide",()=>{navigator.sendBeacon("/bye?t="+TOKEN)});
setInterval(async()=>{try{const r=await api("/api/ping");(r.msgs||[]).forEach(log)}catch(e){}},3000);
boot();
</script>
</body>
</html>
""".replace("__VER__", APP_VERSION)


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {**DEFAULT_CONFIG, **data}
    except Exception:
        pass
    return dict(DEFAULT_CONFIG)


def save_config(data):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))
    except Exception:
        pass


def valid_name(name):
    name = (name or "").strip()
    if not name or name in (".", ".."):
        return None
    if any(c in name for c in '<>:"/\\|?*') or any(ord(c) < 32 for c in name):
        return None
    if os.name == "nt" and (name.endswith(".") or name.split(".")[0].upper() in WIN_RESERVED):
        return None
    return name


def join_path(parent, name):
    if os.name == "nt" and len(parent) == 2 and parent[1] == ":":
        parent += os.sep
    return os.path.join(parent, name)


def unique_path(path, is_dir):
    if not os.path.lexists(path):
        return path
    base, ext = (path, "") if is_dir else os.path.splitext(path)
    n = 1
    while True:
        cand = "%s copy%s%s" % (base, "" if n == 1 else " %d" % n, ext)
        if not os.path.lexists(cand):
            return cand
        n += 1


def copy_item(src, dst):
    if os.path.isdir(src):
        shutil.copytree(src, dst, symlinks=True)
    else:
        shutil.copy2(src, dst)


def _rm_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_item(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path, onerror=_rm_readonly)
    else:
        try:
            os.remove(path)
        except PermissionError:
            os.chmod(path, stat.S_IWRITE)
            os.remove(path)


def write_text(path, content, eol):
    if eol == "CRLF":
        content = content.replace("\n", "\r\n")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)


def list_dir(path, hidden=False):
    items = []
    try:
        with os.scandir(path) as it:
            for e in it:
                if e.name in IGNORED or (e.name.startswith(".") and not hidden):
                    continue
                try:
                    is_dir = e.is_dir()
                except OSError:
                    continue
                items.append({"name": e.name, "dir": is_dir, "path": e.path})
    except OSError:
        return []
    items.sort(key=lambda x: (not x["dir"], x["name"].lower()))
    return items[:MAX_ENTRIES]


def check_syntax(code, lang):
    if lang == "JSON":
        try:
            json.loads(code)
        except json.JSONDecodeError as e:
            return [{"type": "syntax", "line": e.lineno, "col": e.colno, "msg": e.msg}]
        except Exception as e:
            return [{"type": "syntax", "line": 1, "col": 0, "msg": str(e)}]
        return []
    try:
        ast.parse(code)
    except SyntaxError as e:
        return [{"type": "syntax", "line": e.lineno or 1, "col": e.offset or 0,
                 "msg": e.msg or "Syntax error"}]
    except Exception as e:
        return [{"type": "syntax", "line": 1, "col": 0, "msg": str(e)}]
    return []


def search_workspace(root, query, case, hidden):
    q = query if case else query.lower()
    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED and (hidden or not d.startswith("."))]
        for name in filenames:
            if (name.startswith(".") and not hidden) or os.path.splitext(name)[1].lower() in BIN_EXT:
                continue
            path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(path) > MAX_SEARCH_FILE:
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for n, line in enumerate(f, 1):
                        if q in (line if case else line.lower()):
                            results.append({"path": path, "name": name, "line": n,
                                            "text": line.strip()[:120]})
                            if len(results) >= MAX_RESULTS:
                                return results
            except OSError:
                continue
    return results


class API:
    def __init__(self, ui):
        self._ui = ui
        self._last_ping = None
        self._bye = None
        self._msgs = []
        self._config = load_config()
        self._routes = {
            "/api/config": self._h_config,
            "/api/ping": self._h_ping,
            "/api/open-folder": self._h_open_folder,
            "/api/open-file": self._h_open_file,
            "/api/list-dir": self._h_list_dir,
            "/api/read": self._h_read,
            "/api/save": self._h_save,
            "/api/save-as": self._h_save_as,
            "/api/create-file": self._h_create_file,
            "/api/create-folder": self._h_create_folder,
            "/api/rename": self._h_rename,
            "/api/delete": self._h_delete,
            "/api/duplicate": self._h_duplicate,
            "/api/paste": self._h_paste,
            "/api/reveal": self._h_reveal,
            "/api/check-syntax": self._h_check_syntax,
            "/api/search": self._h_search,
            "/api/run": self._h_run,
            "/api/build": self._h_build,
        }

    def call(self, endpoint, payload=None):
        if isinstance(payload, dict):
            data = payload
        else:
            try:
                data = json.loads(payload) if payload else {}
            except Exception:
                data = {}
        handler = self._routes.get(endpoint)
        if handler is None:
            return {"error": "unknown endpoint"}
        try:
            return handler(data)
        except Exception as e:
            return {"error": str(e)}

    def _dialog(self, kind, **kw):
        return self._ui.dialog(kind, **kw)

    def push(self, text):
        self._msgs.append(text)

    def _hidden(self):
        return bool(self._config.get("showHidden"))

    def _h_config(self, d):
        if d:
            if any(self._config.get(k) != v for k, v in d.items()):
                self._config.update(d)
                save_config(self._config)
            return {"ok": True}
        return self._config

    def _h_ping(self, d):
        self._last_ping = time.time()
        self._bye = None
        msgs, self._msgs = self._msgs, []
        return {"msgs": msgs}

    def _h_open_folder(self, d):
        path = d.get("path")
        if path:
            path = os.path.normpath(path)
            if not os.path.isdir(path):
                return {"path": None}
        else:
            r = self._dialog("FOLDER")
            if r is NO_DIALOG:
                return {"nodialog": True}
            if not r:
                return {"path": None}
            path = os.path.normpath(r)
        return {"path": path, "name": os.path.basename(path) or path,
                "files": list_dir(path, self._hidden())}

    def _h_open_file(self, d):
        r = self._dialog("OPEN", directory=d.get("dir") or "")
        if r is NO_DIALOG:
            return {"nodialog": True}
        if not r:
            return {"path": None}
        path = os.path.normpath(r)
        return {"path": path, "name": os.path.basename(path)}

    def _h_list_dir(self, d):
        return {"files": list_dir(d["path"], self._hidden())}

    def _h_read(self, d):
        path = d["path"]
        if not os.path.isfile(path):
            return {"error": "notFound"}
        if os.path.getsize(path) > MAX_READ:
            return {"error": "too_big"}
        with open(path, "rb") as f:
            raw = f.read()
        if b"\0" in raw[:8192]:
            return {"error": "binary"}
        text = raw.decode("utf-8", errors="replace")
        del raw
        crlf = "\r\n" in text
        if crlf:
            text = text.replace("\r\n", "\n")
        return {"content": text, "eol": "CRLF" if crlf else "LF"}

    def _h_save(self, d):
        write_text(d["path"], d.get("content", ""), d.get("eol"))
        return {"ok": True}

    def _h_save_as(self, d):
        path = d.get("path")
        if not path:
            r = self._dialog("SAVE", directory=d.get("dir") or "",
                             save_filename=d.get("name") or "untitled.py")
            if r is NO_DIALOG:
                return {"nodialog": True}
            if not r:
                return {"path": None}
            path = r
        path = os.path.normpath(path)
        write_text(path, d.get("content", ""), d.get("eol"))
        return {"path": path, "name": os.path.basename(path)}

    def _h_create_file(self, d):
        name = valid_name(d.get("name"))
        if not name:
            return {"error": "invalid"}
        path = join_path(d["parent"], name)
        if os.path.lexists(path):
            return {"error": "exists"}
        with open(path, "x", encoding="utf-8"):
            pass
        return {"path": path, "name": name}

    def _h_create_folder(self, d):
        name = valid_name(d.get("name"))
        if not name:
            return {"error": "invalid"}
        path = join_path(d["parent"], name)
        if os.path.lexists(path):
            return {"error": "exists"}
        os.mkdir(path)
        return {"path": path, "name": name}

    def _h_rename(self, d):
        src = d["path"]
        name = valid_name(d.get("name"))
        if not name:
            return {"error": "invalid"}
        if not os.path.lexists(src):
            return {"error": "notFound"}
        dst = join_path(os.path.dirname(src), name)
        if os.path.normcase(dst) != os.path.normcase(src) and os.path.lexists(dst):
            return {"error": "exists"}
        if dst != src:
            os.rename(src, dst)
        return {"path": dst, "name": name}

    def _h_delete(self, d):
        path = d["path"]
        if not os.path.lexists(path):
            return {"error": "notFound"}
        if os.path.dirname(os.path.abspath(path)) == os.path.abspath(path):
            return {"error": "invalid"}
        remove_item(path)
        return {"ok": True}

    def _h_duplicate(self, d):
        src = d["path"]
        if not os.path.lexists(src):
            return {"error": "notFound"}
        is_dir = os.path.isdir(src)
        dst = unique_path(src, is_dir)
        copy_item(src, dst)
        return {"path": dst}

    def _h_paste(self, d):
        src, dest_dir, cut = d["src"], d["dest_dir"], d.get("cut")
        if not os.path.lexists(src):
            return {"error": "notFound"}
        is_dir = os.path.isdir(src)
        s_abs = os.path.normcase(os.path.abspath(src))
        t_abs = os.path.normcase(os.path.abspath(dest_dir))
        if is_dir and (t_abs == s_abs or t_abs.startswith(s_abs + os.sep)):
            return {"error": "invalid"}
        dst = join_path(dest_dir, os.path.basename(src))
        if cut:
            if os.path.normcase(os.path.abspath(dst)) == s_abs:
                return {"path": src}
            if os.path.lexists(dst):
                return {"error": "exists"}
            shutil.move(src, dst)
        else:
            dst = unique_path(dst, is_dir)
            copy_item(src, dst)
        return {"path": dst}

    def _h_reveal(self, d):
        path = d["path"]
        if not os.path.exists(path):
            return {"error": "notFound"}
        if os.name == "nt":
            if os.path.isdir(path):
                os.startfile(path)
            else:
                subprocess.Popen('explorer /select,"%s"' % os.path.normpath(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", path if os.path.isdir(path) else os.path.dirname(path)])
        return {"ok": True}

    def _h_check_syntax(self, d):
        return {"errors": check_syntax(d.get("code", ""), d.get("lang"))}

    def _h_search(self, d):
        root = d.get("root")
        query = d.get("query", "")
        if not root or len(query) < 2:
            return {"results": []}
        return {"results": search_workspace(root, query, bool(d.get("case")), self._hidden())}

    def _h_run(self, d):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        temp = os.path.join(CONFIG_DIR, "_run_temp.py")
        with open(temp, "w", encoding="utf-8") as f:
            f.write(d.get("content", ""))
        py = python_cmd()
        if py is None:
            return {"error": "Python not found"}
        if os.name == "nt":
            subprocess.Popen(["cmd", "/k"] + py + [temp], creationflags=CREATE_NEW_CONSOLE)
        else:
            cmd = " ".join(shlex.quote(x) for x in py + [temp]) + '; echo; read -p "Press Enter..." _'
            for term, args in (("x-terminal-emulator", ["-e"]), ("gnome-terminal", ["--"]),
                               ("konsole", ["-e"]), ("xterm", ["-e"])):
                if shutil.which(term):
                    subprocess.Popen([term, *args, "bash", "-c", cmd])
                    break
            else:
                subprocess.Popen(py + [temp])
        return {"ok": True}

    def _h_build(self, d):
        py = python_cmd()
        if py is None:
            return {"ok": False, "error": "Python not found"}
        if not _ext_has(py, "PyInstaller"):
            _pip_install("pyinstaller")
            if not _ext_has(py, "PyInstaller"):
                return {"ok": False, "error": "PyInstaller unavailable"}
        src = d["path"]
        base = os.path.splitext(os.path.basename(src))[0]
        work = os.path.join(BUILD_DIR, "build")
        spec = os.path.join(BUILD_DIR, "spec")
        os.makedirs(BUILD_DIR, exist_ok=True)
        icon_path = os.path.join(CONFIG_DIR, "icon.ico")
        args = py + ["-m", "PyInstaller", "--onefile", "--noconfirm", "--clean",
                "--windowed", "--distpath", BUILD_DIR, "--workpath", work,
                "--specpath", spec, "--name", base]
        if os.path.isfile(icon_path):
            args += ["--icon", icon_path]
        args.append(src)
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=300,
                                    creationflags=CREATE_NO_WINDOW)
        finally:
            shutil.rmtree(work, ignore_errors=True)
            shutil.rmtree(spec, ignore_errors=True)
        if result.returncode == 0:
            return {"ok": True,
                    "output": os.path.join(BUILD_DIR, base + (".exe" if os.name == "nt" else ""))}
        return {"ok": False, "error": (result.stderr or "")[-500:]}


class UI:
    def __init__(self):
        self.q = queue.Queue()
        self.ok = True
        try:
            import tkinter
        except Exception:
            self.ok = False

    def dialog(self, kind, **kw):
        if not self.ok:
            return NO_DIALOG
        done = threading.Event()
        box = {}
        self.q.put((kind, kw, done, box))
        done.wait()
        return box.get("r", NO_DIALOG)

    def _run(self, root, kind, kw):
        from tkinter import filedialog
        init = kw.get("directory") or os.path.expanduser("~")
        root.attributes("-topmost", True)
        root.update()
        if kind == "FOLDER":
            r = filedialog.askdirectory(parent=root, initialdir=init, mustexist=True)
        elif kind == "OPEN":
            r = filedialog.askopenfilename(parent=root, initialdir=init)
        else:
            r = filedialog.asksaveasfilename(parent=root, initialdir=init,
                                             initialfile=kw.get("save_filename") or "untitled.py")
        root.attributes("-topmost", False)
        return r or None

    def _drain(self):
        try:
            while True:
                _, _, done, box = self.q.get_nowait()
                box["r"] = NO_DIALOG
                done.set()
        except queue.Empty:
            pass

    def loop(self):
        if self.ok:
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
            except Exception:
                self.ok = False
        if not self.ok:
            while True:
                self._drain()
                time.sleep(0.2)

        def poll():
            try:
                while True:
                    kind, kw, done, box = self.q.get_nowait()
                    try:
                        box["r"] = self._run(root, kind, kw)
                    except Exception:
                        box["r"] = NO_DIALOG
                    done.set()
            except queue.Empty:
                pass
            root.after(50, poll)

        poll()
        root.mainloop()


def find_browser():
    cands = []
    if os.name == "nt":
        for var in ("ProgramFiles(x86)", "ProgramFiles", "LocalAppData"):
            base = os.environ.get(var)
            if base:
                cands += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                          os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                          os.path.join(base, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                          os.path.join(base, "Chromium", "Application", "chrome.exe")]
    elif sys.platform == "darwin":
        cands = ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    else:
        for name in ("microsoft-edge", "microsoft-edge-stable", "google-chrome",
                     "google-chrome-stable", "chromium", "chromium-browser", "brave-browser"):
            found = shutil.which(name)
            if found:
                cands.append(found)
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def launch_browser(url):
    exe = find_browser()
    if exe:
        args = [exe, "--app=" + url,
                "--user-data-dir=" + os.path.join(CONFIG_DIR, "profile"),
                "--window-size=1280,800", "--no-first-run", "--no-default-browser-check",
                "--disable-extensions", "--disable-background-networking",
                "--disable-component-update", "--disable-sync", "--disable-breakpad",
                "--disable-features=Translate,MediaRouter", "--renderer-process-limit=1",
                "--disk-cache-size=1048576", "--js-flags=--max-old-space-size=384"]
        try:
            subprocess.Popen(args)
            return
        except OSError:
            pass
    webbrowser.open(url)


def make_handler(api, token, page, hosts):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            if ctype.startswith("text/html"):
                self.send_header("Content-Security-Policy",
                                 "default-src 'self' 'unsafe-inline'; connect-src 'self'; "
                                 "img-src 'self' data:; frame-ancestors 'none'")
            if code >= 400:
                self.close_connection = True
            self.end_headers()
            self.wfile.write(body)

        def _host_ok(self):
            return self.headers.get("Host") in hosts

        def do_GET(self):
            if self._host_ok() and urlparse(self.path).path in ("/", "/index.html"):
                self._send(200, page, "text/html; charset=utf-8")
            else:
                self._send(404, b"", "text/plain")

        def do_POST(self):
            if not self._host_ok():
                self._send(403, b"", "text/plain")
                return
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if n > MAX_BODY:
                self._send(413, b"", "text/plain")
                return
            raw = self.rfile.read(n) if n > 0 else b""
            url = urlparse(self.path)
            if url.path == "/bye":
                if parse_qs(url.query).get("t", [""])[0] == token:
                    api._bye = time.time() + 3
                self._send(200, b"{}", "application/json")
                return
            if url.path != "/api" or self.headers.get("X-Token") != token:
                self._send(403, b"", "text/plain")
                return
            try:
                msg = json.loads(raw.decode("utf-8"))
                res = api.call(msg.get("e"), msg.get("d") or {})
            except Exception as e:
                res = {"error": str(e)}
            self._send(200, json.dumps(res).encode("utf-8"), "application/json; charset=utf-8")

    return Handler


def monitor(api, started):
    while True:
        time.sleep(1)
        now = time.time()
        if api._last_ping is None:
            if now - started > 90:
                os._exit(0)
            continue
        if api._bye is not None and now > api._bye:
            os._exit(0)
        if now - api._last_ping > 150:
            os._exit(0)


def background_install(api):
    if FROZEN or _has_module("PyInstaller", "pyinstaller"):
        return
    api.push("Installing PyInstaller...")
    ok = _ensure_module("PyInstaller", "pyinstaller")
    api.push("PyInstaller " + ("ready" if ok else "unavailable"))


def acquire_lock():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", LOCK_PORT))
        sock.listen(1)
    except OSError:
        sock.close()
        return None
    return sock


def main():
    lock = acquire_lock()
    if lock is None:
        return
    ui = UI()
    api = API(ui)
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    port = server.server_address[1]
    hosts = {"127.0.0.1:%d" % port, "localhost:%d" % port}
    page = HTML.replace("__TOKEN__", token).encode("utf-8")
    server.RequestHandlerClass = make_handler(api, token, page, hosts)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=monitor, args=(api, time.time()), daemon=True).start()
    threading.Thread(target=background_install, args=(api,), daemon=True).start()
    launch_browser("http://127.0.0.1:%d/" % port)
    ui.loop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
