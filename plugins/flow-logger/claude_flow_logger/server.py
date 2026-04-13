"""
FastAPI web server — reads native Claude Code JSONL sessions and serves a
live browser dashboard via SSE.  Supports two UI themes: Classic (Alpine.js)
and Cyber (Vue 3).
"""

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from . import parser as _parser
from .diagram import build_diagram_mermaid_only
from .parser import CLAUDE_PROJECTS_DIR

PORT = int(os.environ.get("FLOW_SERVER_PORT", "7842"))
STATIC_DIR = Path(__file__).parent / "static"

# ---------------------------------------------------------------------------
# Session state — wraps a ParsedSession + SSE subscribers
# ---------------------------------------------------------------------------
@dataclass
class SessionState:
    parsed: _parser.ParsedSession
    subscribers: list = field(default_factory=list)
    _seen: set = field(default_factory=set)   # (id, event) tuples already broadcast

    @property
    def session_id(self) -> str:
        return self.parsed.session_id

    @property
    def is_active(self) -> bool:
        return self.parsed.is_active

    def refresh(self) -> list[dict]:
        """Re-parse the session dir and return newly appeared events."""
        new_ps = _parser.parse_session_dir(self.parsed.session_dir)
        if new_ps is None:
            return []
        new_events: list[dict] = []
        for e in new_ps.events:
            key = (e.get("id", ""), e.get("event", ""))
            if key not in self._seen:
                self._seen.add(key)
                new_events.append(e)
        self.parsed = new_ps
        return new_events


# ---------------------------------------------------------------------------
# Global shared state (initialised in lifespan)
# ---------------------------------------------------------------------------
_sessions: dict[str, SessionState] = {}
_sessions_lock: asyncio.Lock = None  # type: ignore[assignment]
_global_subscribers: list[asyncio.Queue] = []
_app_loop: asyncio.AbstractEventLoop = None  # type: ignore[assignment]
_last_change: dict[str, float] = {}


def _session_dir_from_path(path: Path) -> Path | None:
    """
    Map a changed .jsonl file back to the session aux directory
    ({project_dir}/{session_uuid}/).

    Native layout:
      {project_dir}/{session_uuid}.jsonl            — main file
      {project_dir}/{session_uuid}/subagents/…      — sub-agents
    """
    parent = path.parent
    if parent.name == "subagents":
        # {project_dir}/{session_uuid}/subagents/agent-*.jsonl
        return parent.parent    # {project_dir}/{session_uuid}/
    # Main session file: {project_dir}/{session_uuid}.jsonl
    if path.suffix == ".jsonl":
        return parent / path.stem   # {project_dir}/{session_uuid}/
    return None


# ---------------------------------------------------------------------------
# Async file change processor (called from watchdog thread)
# ---------------------------------------------------------------------------
async def _process_file_change(path: Path) -> None:
    session_dir = _session_dir_from_path(path)
    if session_dir is None:
        return

    session_id = session_dir.name
    is_new = session_id not in _sessions

    async with _sessions_lock:
        if session_id not in _sessions:
            ps = _parser.parse_session_dir(session_dir)
            if ps is None:
                return
            state = SessionState(parsed=ps)
            # Mark all events already on disk as seen so we don't replay history
            for e in ps.events:
                state._seen.add((e.get("id", ""), e.get("event", "")))
            _sessions[session_id] = state
        else:
            state = _sessions[session_id]
            new_events = state.refresh()
            for e in new_events:
                for q in list(state.subscribers):
                    try:
                        q.put_nowait(e)
                    except asyncio.QueueFull:
                        pass

    if is_new:
        msg = {"type": "session_new", "session_id": session_id}
        for q in list(_global_subscribers):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass


# ---------------------------------------------------------------------------
# Watchdog handler
# ---------------------------------------------------------------------------
class _LogFileHandler(FileSystemEventHandler):
    DEBOUNCE = 0.05

    def _handle(self, path_str: str) -> None:
        if not path_str.endswith(".jsonl"):
            return
        now = time.monotonic()
        if now - _last_change.get(path_str, 0) < self.DEBOUNCE:
            return
        _last_change[path_str] = now
        asyncio.run_coroutine_threadsafe(
            _process_file_change(Path(path_str)), _app_loop
        )

    def on_created(self, event):
        if not event.is_directory:
            self._handle(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._handle(event.src_path)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app(log_dir: Path | None = None) -> FastAPI:
    # log_dir is accepted for backward-compat but ignored;
    # sessions are always read from CLAUDE_PROJECTS_DIR.

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global _sessions_lock, _app_loop

        _sessions_lock = asyncio.Lock()
        _app_loop = asyncio.get_running_loop()

        for ps in _parser.discover_sessions():
            state = SessionState(parsed=ps)
            for e in ps.events:
                state._seen.add((e.get("id", ""), e.get("event", "")))
            _sessions[ps.session_id] = state

        watch_dir = CLAUDE_PROJECTS_DIR
        watch_dir.mkdir(parents=True, exist_ok=True)
        observer = Observer()
        observer.schedule(_LogFileHandler(), str(watch_dir), recursive=True)
        observer.start()

        n = len(_sessions)
        hint = " — no Claude Code sessions found" if n == 0 else ""
        print(f"\nFlow Dashboard")
        print(f"  Sessions dir : {watch_dir}")
        print(f"  Sessions     : {n}{hint}")
        print(f"  URL          : http://localhost:{PORT}")
        print(f"  Stop         : Ctrl+C\n")

        yield

        observer.stop()
        observer.join()

    app = FastAPI(lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # ── REST ──────────────────────────────────────────────────────────────

    @app.get("/api/sessions")
    async def list_sessions():
        async with _sessions_lock:
            result = [
                {
                    "session_id":     s.session_id,
                    "project":        s.parsed.project,
                    "cwd":            s.parsed.cwd,
                    "git_branch":     s.parsed.git_branch,
                    "version":        s.parsed.version,
                    "event_count":    len(s.parsed.events),
                    "first_ts":       s.parsed.first_ts(),
                    "last_ts":        s.parsed.last_ts(),
                    "is_active":      s.is_active,
                    "initial_prompt": s.parsed.initial_prompt(),
                }
                for s in _sessions.values()
            ]
        result.sort(key=lambda x: x["last_ts"], reverse=True)
        return JSONResponse(result)

    @app.get("/api/sessions/{session_id:path}/diagram")
    async def get_diagram(session_id: str):
        async with _sessions_lock:
            if session_id not in _sessions:
                return JSONResponse({"error": "not found"}, status_code=404)
            events = list(_sessions[session_id].parsed.events)
        mermaid_src, truncated = build_diagram_mermaid_only(events, session_id, max_entries=200)
        return JSONResponse({
            "mermaid":   mermaid_src,
            "truncated": truncated,
            "total":     len(events),
            "shown":     min(len(events), 200),
        })

    @app.get("/api/sessions/{session_id:path}/stats")
    async def get_session_stats(session_id: str):
        async with _sessions_lock:
            if session_id not in _sessions:
                return JSONResponse({"error": "not found"}, status_code=404)
            ps = _sessions[session_id].parsed
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(None, _parser.compute_stats, ps)
        return JSONResponse(stats)

    # ── SSE ───────────────────────────────────────────────────────────────

    @app.get("/api/sessions/{session_id:path}/stream")
    async def session_stream(session_id: str):
        async with _sessions_lock:
            if session_id not in _sessions:
                async def _not_found():
                    yield {"event": "error", "data": json.dumps({"message": "session not found"})}
                return EventSourceResponse(_not_found())

            state = _sessions[session_id]
            q: asyncio.Queue = asyncio.Queue(maxsize=500)
            state.subscribers.append(q)
            existing_count = len(state.parsed.events)

        async def _generator():
            try:
                yield {
                    "event": "connected",
                    "data": json.dumps({"session_id": session_id, "existing_count": existing_count}),
                }
                while True:
                    try:
                        entry = await asyncio.wait_for(q.get(), timeout=25.0)
                        yield {"event": "entry", "data": json.dumps(entry)}
                    except asyncio.TimeoutError:
                        yield {"event": "ping", "data": ""}
            except asyncio.CancelledError:
                pass
            finally:
                async with _sessions_lock:
                    try:
                        state.subscribers.remove(q)
                    except ValueError:
                        pass

        return EventSourceResponse(_generator())

    @app.get("/api/stream/global")
    async def global_stream():
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        _global_subscribers.append(q)

        async def _generator():
            try:
                while True:
                    try:
                        msg = await asyncio.wait_for(q.get(), timeout=25.0)
                        yield {"event": msg["type"], "data": json.dumps(msg)}
                    except asyncio.TimeoutError:
                        yield {"event": "ping", "data": ""}
            except asyncio.CancelledError:
                pass
            finally:
                try:
                    _global_subscribers.remove(q)
                except ValueError:
                    pass

        return EventSourceResponse(_generator())

    # NOTE: this catch-all :path route MUST be after /diagram, /stats, /stream
    @app.get("/api/sessions/{session_id:path}")
    async def get_session(session_id: str):
        async with _sessions_lock:
            if session_id not in _sessions:
                return JSONResponse({"error": "not found"}, status_code=404)
            data = list(_sessions[session_id].parsed.events)
        return JSONResponse({"session_id": session_id, "entries": data})

    # ── Dashboard HTML ────────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return HTMLResponse(_HTML_PAGE)

    @app.get("/cyber", response_class=HTMLResponse)
    async def cyber_dashboard():
        return HTMLResponse(_CYBER_HTML)

    return app


# ---------------------------------------------------------------------------
# Classic Dashboard HTML (Alpine.js + Tailwind)
# ---------------------------------------------------------------------------
_HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Claude Code Flow Monitor</title>
  <script src="/static/tailwind.play.js"></script>
  <script defer src="/static/alpine.min.js"></script>
  <script src="/static/mermaid.min.js"></script>
  <style>
    [x-cloak] { display: none !important; }

    /* Tree connector lines */
    .tree-children {
      padding-left: 1.5rem;
      margin-left: 1.1rem;
      border-left: 2px solid #64748b;
      position: relative;
    }
    .tree-node {
      position: relative;
      padding-top: 10px;
      margin-bottom: 2px;
    }
    /* Horizontal connector from spine to card */
    .tree-node::before {
      content: '';
      position: absolute;
      left: -1.5rem;
      top: 1.45rem;
      width: 1.5rem;
      height: 2px;
      background: #64748b;
    }
    /* Colored junction dot — sits where horizontal meets vertical */
    .node-dot {
      position: absolute;
      left: calc(-1.5rem - 4px);
      top: calc(1.45rem - 4px);
      width: 10px;
      height: 10px;
      border-radius: 50%;
      border: 2px solid #f8fafc;
      box-shadow: 0 0 0 1px rgba(0,0,0,.18);
      z-index: 2;
    }
    /* live pulse on agent status dot */
    .status-pulse {
      animation: spulse 1.4s ease-in-out infinite;
    }
    @keyframes spulse {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.25; }
    }
  </style>
</head>
<body class="bg-gray-100 h-screen flex flex-col overflow-hidden"
      x-data="flowDashboard()" x-init="init()" x-cloak>

  <!-- Top bar -->
  <header class="bg-white border-b px-4 py-2 flex items-center gap-3 shrink-0 shadow-sm">
    <span class="font-bold text-gray-800 text-sm tracking-tight">Claude Code Flow Monitor</span>
    <a href="/cyber" style="font-size:11px;font-family:monospace;background:#0a0a14;color:#00ff9f;
                             border:1px solid #00ff9f44;border-radius:4px;padding:2px 8px;
                             text-decoration:none;letter-spacing:.05em;opacity:.8"
       title="Open Cyber UI">⬡ CYBER</a>
    <div class="ml-auto flex items-center gap-2">
      <span class="relative flex h-2.5 w-2.5">
        <span x-show="liveConnected"
              class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
        <span :class="liveConnected ? 'bg-green-500' : 'bg-gray-300'"
              class="relative inline-flex rounded-full h-2.5 w-2.5"></span>
      </span>
      <span class="text-xs text-gray-400" x-text="liveConnected ? 'LIVE' : 'disconnected'"></span>
    </div>
  </header>

  <!-- Body -->
  <div class="flex flex-1 overflow-hidden">

    <!-- Sidebar -->
    <aside class="w-64 bg-white border-r flex flex-col shrink-0">
      <div class="px-3 py-2.5 border-b bg-gray-50">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Sessions</p>
      </div>
      <div class="flex-1 overflow-y-auto">
        <template x-for="grp in projectGroups()" :key="grp.project">
          <div>
            <!-- Project header -->
            <div class="px-3 py-1.5 bg-gray-100 border-b border-gray-200 sticky top-0 z-10
                        flex items-center gap-1.5 cursor-pointer select-none"
                 @click="toggleProject(grp.project)">
              <span class="text-[10px] font-mono"
                    x-text="collapsedProjects[grp.project] ? '▶' : '▼'"></span>
              <span class="text-[10px] font-bold text-gray-600 uppercase tracking-wider truncate"
                    x-text="grp.project || '(no project)'"></span>
              <span class="text-[10px] text-gray-400 ml-auto shrink-0"
                    x-text="grp.sessions.length"></span>
            </div>
            <!-- Sessions in this project -->
            <ul x-show="!collapsedProjects[grp.project]" class="divide-y divide-gray-100">
              <template x-for="s in grp.sessions" :key="s.session_id">
                <li @click="selectSession(s.session_id)"
                    :class="s.session_id === activeSessionId
                      ? 'bg-blue-50 border-l-2 border-blue-500'
                      : 'hover:bg-gray-50 border-l-2 border-transparent cursor-pointer'"
                    class="px-3 py-2 transition-colors">
                  <div class="flex items-center gap-1.5">
                    <span class="font-mono text-xs text-gray-700 truncate flex-1"
                          x-text="s.first_ts ? s.first_ts.slice(0,10) : s.session_id.slice(0,8) + '…'"></span>
                    <span x-show="s.is_active"
                          class="text-xs font-bold text-green-600 animate-pulse shrink-0">LIVE</span>
                  </div>
                  <div class="flex items-center gap-2 mt-0.5">
                    <span class="text-xs text-gray-500 font-mono"
                          x-text="s.first_ts ? s.first_ts.slice(11,19) : ''"></span>
                    <span class="text-xs text-gray-300">→</span>
                    <span class="text-xs text-gray-400 font-mono"
                          x-text="s.last_ts ? s.last_ts.slice(11,19) : ''"></span>
                    <span class="text-xs text-gray-300 ml-auto"
                          x-text="s.event_count + ' ev'"></span>
                  </div>
                  <div x-show="s.git_branch || s.initial_prompt" class="mt-0.5">
                    <span x-show="s.git_branch"
                          class="text-[10px] text-purple-500 font-mono truncate"
                          x-text="'⎇ ' + s.git_branch"></span>
                    <p x-show="s.initial_prompt"
                       class="text-[10px] text-gray-400 truncate mt-0.5"
                       x-text="s.initial_prompt"></p>
                  </div>
                </li>
              </template>
            </ul>
          </div>
        </template>
        <div x-show="sessions.length === 0"
            class="px-3 py-4 text-xs text-gray-400 italic">
          No sessions yet.
        </div>
      </div>
    </aside>

    <!-- Main -->
    <main class="flex-1 flex flex-col overflow-hidden">

      <!-- Tabs -->
      <nav class="bg-white border-b px-4 flex gap-0 shrink-0">
        <button @click="switchTab('tree')"
                :class="tab==='tree'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'"
                class="px-4 py-2.5 text-sm font-medium transition-colors">
          Flow Tree
        </button>
        <button @click="switchTab('events')"
                :class="tab==='events'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'"
                class="px-4 py-2.5 text-sm font-medium transition-colors">
          Events
          <span class="ml-1 text-xs text-gray-400" x-text="'(' + entries.length + ')'"></span>
        </button>
        <button @click="switchTab('diagram')"
                :class="tab==='diagram'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'"
                class="px-4 py-2.5 text-sm font-medium transition-colors">
          Diagram
        </button>
      </nav>

      <!-- Flow Tree tab -->
      <div x-show="tab === 'tree'" class="flex-1 overflow-auto p-5 bg-gray-50">
        <div x-show="!activeSessionId" class="text-sm text-gray-400 italic">
          Select a session from the sidebar.
        </div>
        <div x-show="activeSessionId && entries.length === 0" class="text-sm text-gray-400 italic">
          No events yet — waiting for Claude Code hook events.
        </div>
        <div id="prompt-panel" style="margin-bottom:8px"></div>
        <div id="stats-panel" style="margin-bottom:12px"></div>
        <div id="tree-container"></div>
      </div>

      <!-- Events tab -->
      <div x-show="tab === 'events'" class="flex-1 overflow-auto bg-white">
        <table class="w-full text-xs border-collapse">
          <thead class="bg-gray-50 sticky top-0 shadow-sm">
            <tr>
              <th class="px-3 py-2 text-left font-medium text-gray-500 border-b w-28">Time (UTC)</th>
              <th class="px-3 py-2 text-left font-medium text-gray-500 border-b w-8">Dir</th>
              <th class="px-3 py-2 text-left font-medium text-gray-500 border-b w-28">Tool</th>
              <th class="px-3 py-2 text-left font-medium text-gray-500 border-b">Summary</th>
              <th class="px-3 py-2 text-left font-medium text-gray-500 border-b w-16">Tokens</th>
            </tr>
          </thead>
          <template x-for="(e, i) in entries" :key="i">
            <tbody>
              <!-- Main row -->
              <tr :class="rowClass(e)" class="border-b transition-colors cursor-pointer"
                  @click="e.response != null && e.response !== '' && toggleEvtResp(i)">
                <td class="px-3 py-1.5 font-mono whitespace-nowrap"
                    x-text="e.ts ? e.ts.slice(11,23) : ''"></td>
                <td class="px-3 py-1.5 text-gray-400"
                    x-text="e.event === 'pre' ? '→' : e.event === 'command' ? '⚡' : '←'"></td>
                <td class="px-3 py-1.5 font-semibold" x-text="e.tool"></td>
                <td class="px-3 py-1.5">
                  <div class="flex items-center gap-2">
                    <span class="truncate flex-1" style="max-width:420px" x-text="e.cmd || summarise(e)"></span>
                    <span x-show="e.response != null && e.response !== ''"
                          class="shrink-0 px-1 py-0.5 rounded text-gray-400 font-mono text-[10px]"
                          x-text="openResps[i] ? '▼ resp' : '▶ resp'">
                    </span>
                  </div>
                </td>
                <td class="px-3 py-1.5 font-mono text-gray-400 whitespace-nowrap">
                  <template x-if="e.tokens">
                    <span>
                      <span x-show="e.tokens?.input" class="text-blue-500" x-text="'↑'+fmtKi(e.tokens?.input||0)"></span>
                      <span x-show="e.tokens?.output" class="text-green-500" x-text="' ↓'+fmtKi(e.tokens?.output||0)"></span>
                    </span>
                  </template>
                </td>
              </tr>
              <!-- Response detail row (hidden by default) -->
              <tr x-show="openResps[i]" class="bg-gray-50 border-b">
                <td colspan="5" class="px-3 py-2">
                  <pre class="text-xs font-mono whitespace-pre-wrap break-all max-h-52 overflow-y-auto
                              bg-white border border-gray-200 rounded p-2 text-gray-600 shadow-inner"
                       x-text="fmtResp(e.response)"></pre>
                </td>
              </tr>
            </tbody>
          </template>
          <tbody x-show="entries.length === 0">
            <tr>
              <td colspan="5" class="px-3 py-4 text-gray-400 italic">No events yet.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Diagram tab -->
      <div x-show="tab === 'diagram'" class="flex-1 overflow-auto p-5 bg-gray-50">
        <div x-show="!activeSessionId" class="text-sm text-gray-400 italic">
          Select a session from the sidebar.
        </div>
        <template x-if="activeSessionId">
          <div>
            <div class="flex items-center gap-2 mb-4">
              <button @click="loadDiagram()"
                      :disabled="diagramLoading"
                      class="px-3 py-1.5 text-xs font-medium rounded bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50 transition-colors">
                <span x-text="diagramLoading ? 'Generating…' : 'Refresh'"></span>
              </button>
              <button x-show="diagramSvg" @click="downloadSvg()"
                      class="px-3 py-1.5 text-xs font-medium rounded border border-gray-300 bg-white hover:bg-gray-100 transition-colors">
                ↓ SVG
              </button>
              <button x-show="diagramMd" @click="downloadMd()"
                      class="px-3 py-1.5 text-xs font-medium rounded border border-gray-300 bg-white hover:bg-gray-100 transition-colors">
                ↓ Markdown
              </button>
              <span x-show="diagramTruncated" class="text-xs text-amber-500">
                ⚠ Last 200 events shown
              </span>
            </div>
            <div x-show="!diagramSvg && !diagramLoading" class="text-sm text-gray-400 italic">
              Click Refresh to generate the sequence diagram.
            </div>
            <div id="diagram-container" class="bg-white border border-gray-200 rounded p-4 overflow-auto"></div>
          </div>
        </template>
      </div>

    </main>
  </div>

<script>
// ─── Tool display config ───────────────────────────────────────────────────
const TOOL_CFG = {
  Agent: {
    icon: '🤖',
    hdrBg:'#2563eb', hdrFg:'#fff',
    bodyBg:'#eff6ff', bodyFg:'#1e3a8a', border:'#bfdbfe',
    label: n => n.input.subagent_type || n.input.agent || 'general-purpose',
    details: n => {
      const d = [];
      if (n.input.description) d.push(['description', n.input.description]);
      if (n.response != null && n.response !== '') d.push(['response', fmtResponse(n.response)]);
      return d;
    },
  },
  Skill: {
    icon: '⚡',
    hdrBg:'#7c3aed', hdrFg:'#fff',
    bodyBg:'#f5f3ff', bodyFg:'#4c1d95', border:'#ddd6fe',
    label: n => n.cmd || n.input.skill || '',
    details: n => n.input.args ? [['args', n.input.args]] : [],
  },
  SendMessage: {
    icon: '💬',
    hdrBg:'#d97706', hdrFg:'#fff',
    bodyBg:'#fffbeb', bodyFg:'#78350f', border:'#fde68a',
    label: n => n.cmd || `→ ${n.input.to || ''}`,
    details: n => n.input.message ? [['msg', String(n.input.message).slice(0, 160)]] : [],
  },
  TaskCreate: {
    icon: '✅',
    hdrBg:'#059669', hdrFg:'#fff',
    bodyBg:'#ecfdf5', bodyFg:'#064e3b', border:'#a7f3d0',
    label: n => n.cmd || n.input.title || '',
    details: n => [],
  },
  TaskUpdate: {
    icon: '🔄',
    hdrBg:'#047857', hdrFg:'#fff',
    bodyBg:'#ecfdf5', bodyFg:'#064e3b', border:'#a7f3d0',
    label: n => n.cmd || `${n.input.taskId||n.input.id||''} → ${n.input.status||''}`,
    details: n => [],
  },
  Read: {
    icon: '📄',
    hdrBg:'#94a3b8', hdrFg:'#fff',
    bodyBg:'#f8fafc', bodyFg:'#475569', border:'#e2e8f0',
    label: n => n.cmd || (n.input.file_path || n.input.path || '').split('/').slice(-2).join('/'),
    details: n => [],
  },
  Glob: {
    icon: '🔍',
    hdrBg:'#94a3b8', hdrFg:'#fff',
    bodyBg:'#f8fafc', bodyFg:'#475569', border:'#e2e8f0',
    label: n => n.cmd || n.input.pattern || n.input.path || '',
    details: n => [],
  },
  Grep: {
    icon: '🔎',
    hdrBg:'#94a3b8', hdrFg:'#fff',
    bodyBg:'#f8fafc', bodyFg:'#475569', border:'#e2e8f0',
    label: n => n.cmd || n.input.pattern || '',
    details: n => [],
  },
  Bash: {
    icon: '💻',
    hdrBg:'#1e293b', hdrFg:'#fff',
    bodyBg:'#f8fafc', bodyFg:'#334155', border:'#cbd5e1',
    label: n => n.cmd || n.input.description || (n.input.command || '').slice(0, 60) || '',
    details: n => {
      const d = [];
      if (n.input.command) d.push(['command', String(n.input.command).slice(0, 200)]);
      return d;
    },
  },
  Edit: {
    icon: '✏️',
    hdrBg:'#ca8a04', hdrFg:'#fff',
    bodyBg:'#fefce8', bodyFg:'#713f12', border:'#fde68a',
    label: n => n.cmd || (n.input.file_path || '').split('/').slice(-2).join('/'),
    details: n => [],
  },
  Write: {
    icon: '📝',
    hdrBg:'#b45309', hdrFg:'#fff',
    bodyBg:'#fffbeb', bodyFg:'#78350f', border:'#fde68a',
    label: n => n.cmd || (n.input.file_path || '').split('/').slice(-2).join('/'),
    details: n => [],
  },
  Command: {
    icon: '🎯',
    hdrBg:'#6366f1', hdrFg:'#fff',
    bodyBg:'#eef2ff', bodyFg:'#3730a3', border:'#c7d2fe',
    label: n => n.cmd || `${n.input.command||''} ${n.input.args||''}`.trim(),
    details: n => n.input.args ? [['args', n.input.args]] : [],
  },
  User: {
    icon: '👤',
    hdrBg:'#e11d48', hdrFg:'#fff',
    bodyBg:'#fff1f2', bodyFg:'#881337', border:'#fecdd3',
    label: n => n.cmd || (n.input.message || '').slice(0, 100),
    details: n => n.input.message ? [['message', String(n.input.message)]] : [],
  },
};
const MCP_CFG = {
  icon:'🔌', hdrBg:'#0891b2', hdrFg:'#fff',
  bodyBg:'#ecfeff', bodyFg:'#155e75', border:'#a5f3fc',
  label: n => n.cmd || n.tool.replace(/^mcp__[^_]+__/, ''),
  details: n => [],
};
const DEFAULT_CFG = {
  icon:'⚙️', hdrBg:'#6b7280', hdrFg:'#fff',
  bodyBg:'#f9fafb', bodyFg:'#374151', border:'#e5e7eb',
  label: n => n.cmd || '', details: n => [],
};
const tc = t => TOOL_CFG[t] || (t.startsWith('mcp__') ? MCP_CFG : DEFAULT_CFG);

function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
const fmtT = ts => ts ? ts.slice(11,19) : '';

function fmtK(n) {
  if (!n) return '0';
  if (n >= 1000) return (Math.round(n / 100) / 10) + 'k';
  return String(n);
}

function buildTokenIndex(entries, timeline) {
  const idx = new Map();
  if (!timeline || !timeline.length) return idx;
  const tl = [...timeline].filter(m => m.ts).sort(
    (a, b) => new Date(a.ts) - new Date(b.ts)
  );
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    if (e.event !== 'pre' || !e.ts) continue;
    const nodeMs = new Date(e.ts).getTime();
    let best = null, bestDiff = 10001;
    for (const m of tl) {
      const diff = Math.abs(new Date(m.ts).getTime() - nodeMs);
      if (diff < bestDiff && m.tools && m.tools.includes(e.tool)) {
        bestDiff = diff; best = m;
      }
    }
    if (!best) {
      bestDiff = 5001;
      for (const m of tl) {
        const diff = Math.abs(new Date(m.ts).getTime() - nodeMs);
        if (diff < bestDiff) { bestDiff = diff; best = m; }
      }
    }
    if (best) idx.set(i, best);
  }
  return idx;
}

function fmtResponse(v) {
  if (v == null || v === '') return { text: '', isMultiLine: false };
  if (typeof v === 'object') {
    const s = JSON.stringify(v, null, 2);
    return { text: s, isMultiLine: true };
  }
  const s = String(v);
  try {
    const parsed = JSON.parse(s);
    if (typeof parsed === 'object' && parsed !== null) {
      const pretty = JSON.stringify(parsed, null, 2);
      return { text: pretty, isMultiLine: true };
    }
  } catch (_) {}
  const truncated = s.length > 400 ? s.slice(0, 400) + `…[+${s.length - 400}]` : s;
  return { text: truncated, isMultiLine: truncated.includes('\n') };
}

// ─── Tree builder ──────────────────────────────────────────────────────────
const CONTAINER_TOOLS = new Set(['Agent', 'Skill', 'Bash']);

function buildTree(entries) {
  const root = {
    id:'root', tool:'Claude', children:[], status:'root',
    input:{}, ts: entries[0]?.ts || '', response:null, postTs:null,
    cmd:'', tokens:null,
  };
  const hasActionIds = entries.some(e => e.action_id);
  if (hasActionIds) return _buildTreeById(entries, root);
  return _buildTreeHeuristic(entries, root);
}

function _buildTreeById(entries, root) {
  const nodeMap = new Map();
  nodeMap.set(null, root); nodeMap.set(undefined, root);
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    if (e.event !== 'pre' && e.event !== 'command' && e.event !== 'prompt') continue;
    const node = {
      id: e.action_id || i, tool: e.tool, input: e.input || {}, ts: e.ts,
      cmd: e.cmd || '', tokens: e.tokens || null,
      status: CONTAINER_TOOLS.has(e.tool) ? 'active' : 'done',
      children: [], response: null, postTs: null,
      parallel: false, parentId: e.parent_id || null,
    };
    nodeMap.set(e.action_id, node);
    // User prompts always attach to root
    const par = e.event === 'prompt' ? root : (nodeMap.get(e.parent_id) || root);
    node.parentId = par.id;
    if (e.tool === 'Agent') {
      const activeSib = par.children.find(c => c.tool === 'Agent' && c.status === 'active');
      if (activeSib) {
        node.parallel = true;
        par.children
          .filter(c => c.tool === 'Agent' && (c.status === 'active' || c.parallel))
          .forEach(c => c.parallel = true);
      }
    }
    par.children.push(node);
  }
  for (const e of entries) {
    if (e.event !== 'post') continue;
    const node = nodeMap.get(e.action_id);
    if (!node) continue;
    node.status   = 'done';
    node.response = e.response ?? '';
    node.postTs   = e.ts;
    if (e.tokens) node.tokens = e.tokens;
    if (e.child_ids?.length) node.childIds = e.child_ids;
  }
  return root;
}

function _buildTreeHeuristic(entries, root) {
  const stack      = [root];
  const openAgents = [];
  // Use subagent_type (native) with fallback to agent (hook-based)
  const agentKey = inp => inp?.subagent_type || inp?.agent || '';
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    if (e.event === 'post') {
      if (e.tool === 'Agent') {
        const key = agentKey(e.input);
        let mi = -1;
        for (let j = openAgents.length - 1; j >= 0; j--) {
          if (agentKey(openAgents[j].input) === key) { mi = j; break; }
        }
        if (mi === -1 && openAgents.length) mi = openAgents.length - 1;
        if (mi !== -1) {
          const node = openAgents[mi];
          node.status   = 'done';
          node.response = e.response ?? '';
          node.postTs   = e.ts;
          if (e.tokens) node.tokens = e.tokens;
          // Agent cost metrics from native JSONL
          if (e.agent_total_tokens) node.agentTotalTokens = e.agent_total_tokens;
          if (e.agent_duration_ms)  node.agentDurationMs  = e.agent_duration_ms;
          if (e.agent_tool_count)   node.agentToolCount   = e.agent_tool_count;
          if (e.agent_type)         node.agentType        = e.agent_type;
          openAgents.splice(mi, 1);
          const si = stack.indexOf(node);
          if (si !== -1) stack.splice(si, 1);
        }
      } else {
        let found = false;
        for (let j = stack.length - 1; j >= 0 && !found; j--) {
          for (let k = stack[j].children.length - 1; k >= 0; k--) {
            const c = stack[j].children[k];
            if (c.tool === e.tool && c.status === 'pending') {
              c.status = 'done'; c.response = e.response ?? ''; c.postTs = e.ts;
              if (e.tokens) c.tokens = e.tokens;
              found = true; break;
            }
          }
        }
      }
      continue;
    }
    if (e.event === 'command' || e.event === 'prompt') {
      root.children.push({
        id: i, tool: e.tool || (e.event === 'prompt' ? 'User' : 'Command'),
        input: e.input || {}, ts: e.ts,
        cmd: e.cmd || '', tokens: e.tokens || null,
        model: e.model || null, thinking: e.thinking || null,
        status: 'done', children: [], response: null, postTs: null,
        parallel: false, parentId: root.id,
      });
      continue;
    }
    if (e.tool === 'Agent') {
      let parIdx = stack.length - 1;
      while (
        parIdx > 0 &&
        stack[parIdx].tool === 'Agent' &&
        stack[parIdx].status === 'active' &&
        !stack[parIdx].children.some(c => c.tool !== 'Agent')
      ) { parIdx--; }
      const par = stack[parIdx];
      const node = {
        id: i, tool: 'Agent', input: e.input || {}, ts: e.ts,
        cmd: e.cmd || '', tokens: e.tokens || null,
        model: e.model || null, thinking: e.thinking || null,
        status: 'active', children: [], response: null, postTs: null,
        parallel: false, parentId: par.id,
      };
      const activeSib = par.children.find(c => c.tool === 'Agent' && c.status === 'active');
      if (activeSib) {
        node.parallel = true;
        par.children
          .filter(c => c.tool === 'Agent' && (c.status === 'active' || c.parallel))
          .forEach(c => c.parallel = true);
      }
      par.children.push(node);
      openAgents.push(node);
      stack.push(node);
    } else {
      const par = stack[stack.length - 1];
      const needsPost = e.tool === 'Skill' || e.tool === 'SendMessage';
      par.children.push({
        id: i, tool: e.tool, input: e.input || {}, ts: e.ts,
        cmd: e.cmd || '', tokens: e.tokens || null,
        model: e.model || null, thinking: e.thinking || null,
        status: needsPost ? 'pending' : 'done',
        children: [], response: null, postTs: null,
        parallel: false, parentId: par.id,
      });
    }
  }
  return root;
}

// ─── Renderer ─────────────────────────────────────────────────────────────
function nodeCard(node) {
  const c    = tc(node.tool);
  const lbl  = esc(c.label(node));
  const rows = c.details(node);
  let badge = '';
  if (node.status === 'active') {
    badge = `<span style="display:inline-flex;align-items:center;gap:4px;font-size:10px;color:#86efac">
               <span class="status-pulse" style="width:6px;height:6px;border-radius:50%;
                     background:#4ade80;display:inline-block;flex-shrink:0"></span>live
             </span>`;
  } else if (node.status === 'pending') {
    badge = `<span style="font-size:10px;opacity:.55">⏳</span>`;
  }
  const t1  = fmtT(node.ts), t2 = fmtT(node.postTs);
  const tStr = t2 ? `${t1}→${t2}` : t1;
  const inlineTok = node.tokens;
  const idxTok    = window._tokenIndex ? window._tokenIndex.get(node.id) : null;
  const tok       = inlineTok || idxTok;
  const totalIn  = tok ? (tok.input || 0) + (tok.cache_read || 0) + (tok.cache_write || 0) + (tok.cache_create || 0) : 0;
  const totalOut = tok ? (tok.output || 0) : 0;
  const hasTokens = tok && (totalIn || totalOut);
  const tokBadge = hasTokens
    ? `<span title="in:${(tok.input||0).toLocaleString()} out:${(tok.output||0).toLocaleString()} cache_r:${(tok.cache_read||0).toLocaleString()} cache_c:${(tok.cache_create||tok.cache_write||0).toLocaleString()}${tok.duration_ms ? ' '+tok.duration_ms+'ms' : ''}"
             style="display:inline-flex;align-items:center;gap:3px;font-size:9px;
                    background:rgba(0,0,0,.18);border-radius:4px;padding:1px 5px;
                    font-family:monospace;color:inherit;opacity:.85;flex-shrink:0;white-space:nowrap">
         ↑${fmtK(totalIn)} ↓${fmtK(totalOut)}
       </span>`
    : '';
  const mainRows     = rows.filter(([k]) => k !== 'response');
  const responseRow  = rows.find(([k])   => k === 'response');
  function renderDetailRow([k, v]) {
    const isFmt     = v && typeof v === 'object' && 'text' in v;
    const text      = isFmt ? v.text : String(v);
    const multiLine = isFmt ? v.isMultiLine : text.includes('\n');
    const valueHtml = multiLine
      ? `<pre style="margin:0;padding:4px 6px;background:rgba(0,0,0,.04);border-radius:4px;
                     font-size:10px;line-height:1.5;white-space:pre-wrap;word-break:break-all;
                     max-height:160px;overflow-y:auto;font-family:monospace">${esc(text)}</pre>`
      : `<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(text)}</span>`;
    return `<div style="display:flex;gap:6px;font-size:11px;line-height:1.4;overflow:hidden;
                        ${multiLine ? 'flex-direction:column' : 'align-items:baseline'}">
              <span style="opacity:.4;flex-shrink:0;min-width:52px">${esc(k)}:</span>
              ${valueHtml}
            </div>`;
  }
  const mainHtml = mainRows.map(renderDetailRow).join('');
  let tokenRowHtml = '';
  if (hasTokens) {
    function pill2(label, val, bg, fg) {
      if (!val) return '';
      return `<span style="display:inline-flex;align-items:center;gap:2px;font-size:10px;
                            background:${bg};color:${fg};border-radius:999px;
                            padding:0px 6px;font-weight:600;white-space:nowrap;font-family:monospace">
                ${label}<span style="font-weight:400">${fmtK(val)}</span>
              </span>`;
    }
    tokenRowHtml = `
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:3px;
                  padding:3px 0;border-top:1px dashed ${c.border}">
        <span style="font-size:10px;opacity:.4;min-width:52px;flex-shrink:0">tokens:</span>
        ${pill2('↑ ', tok.input,        '#dbeafe','#1e40af')}
        ${pill2('↓ ', tok.output,       '#dcfce7','#166534')}
        ${tok.cache_read   ? pill2('↩ ', tok.cache_read,  '#fef9c3','#713f12') : ''}
        ${(tok.cache_create || tok.cache_write) ? pill2('☁ ', tok.cache_create || tok.cache_write,'#f3e8ff','#6b21a8') : ''}
        ${tok.duration_ms  ? `<span style="font-size:9px;opacity:.5;font-family:monospace">${tok.duration_ms}ms</span>` : ''}
      </div>`;
  }
  // ── Model chip ────────────────────────────────────────────────────────────
  const modelChip = node.model
    ? `<span title="${esc(node.model)}"
             style="display:inline-flex;align-items:center;font-size:9px;
                    background:rgba(255,255,255,.18);border-radius:999px;
                    padding:1px 6px;font-family:monospace;color:inherit;
                    opacity:.8;flex-shrink:0;white-space:nowrap;max-width:120px;
                    overflow:hidden;text-overflow:ellipsis">
         ${esc(node.model.replace('claude-', '').replace(/-\d{8}$/, ''))}
       </span>`
    : '';

  // ── Agent cost badges ─────────────────────────────────────────────────────
  let agentCostHtml = '';
  if (node.tool === 'Agent' && node.status === 'done' && (node.agentTotalTokens || node.agentDurationMs)) {
    const toks = node.agentTotalTokens ? fmtK(node.agentTotalTokens) + ' tok' : '';
    const dur  = node.agentDurationMs  ? (node.agentDurationMs / 1000).toFixed(1) + 's' : '';
    const cnt  = node.agentToolCount   ? node.agentToolCount + ' calls' : '';
    agentCostHtml = `
      <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:3px;
                  padding:3px 0;border-top:1px dashed ${c.border}">
        <span style="font-size:10px;opacity:.4;min-width:52px;flex-shrink:0">agent:</span>
        ${toks ? `<span style="font-size:10px;background:#dbeafe;color:#1e40af;border-radius:999px;padding:0px 6px;font-family:monospace;font-weight:600">${esc(toks)}</span>` : ''}
        ${dur  ? `<span style="font-size:10px;background:#dcfce7;color:#166534;border-radius:999px;padding:0px 6px;font-family:monospace;font-weight:600">${esc(dur)}</span>` : ''}
        ${cnt  ? `<span style="font-size:10px;background:#f3e8ff;color:#6b21a8;border-radius:999px;padding:0px 6px;font-family:monospace;font-weight:600">${esc(cnt)}</span>` : ''}
      </div>`;
  }

  // ── Thinking toggle ───────────────────────────────────────────────────────
  let thinkingHtml = '';
  if (node.thinking) {
    const tuid = `think-${node.id}`;
    thinkingHtml = `
      <div style="margin-top:4px;border-top:1px dashed ${c.border};padding-top:4px">
        <button onclick="(function(btn){
                   var d=document.getElementById('${tuid}');
                   var open=d.style.display!=='none';
                   d.style.display=open?'none':'block';
                   btn.textContent=open?'▶ thinking':'▼ thinking';
                 })(this)"
                style="background:none;border:none;cursor:pointer;font-size:10px;
                       color:${c.bodyFg};opacity:.5;padding:0;font-family:inherit">
          ▶ thinking
        </button>
        <div id="${tuid}" style="display:none">
          <pre style="margin:4px 0 0;padding:4px 6px;background:rgba(0,0,0,.04);border-radius:4px;
                     font-size:10px;line-height:1.5;white-space:pre-wrap;word-break:break-all;
                     max-height:200px;overflow-y:auto;font-family:monospace;font-style:italic;
                     color:${c.bodyFg}">${esc(String(node.thinking).slice(0, 1000))}</pre>
        </div>
      </div>`;
  }

  const uid = `resp-${node.id}`;
  let responseHtml = '';
  if (responseRow) {
    const [, v]     = responseRow;
    const isFmt     = v && typeof v === 'object' && 'text' in v;
    const text      = isFmt ? v.text : String(v);
    const multiLine = isFmt ? v.isMultiLine : text.includes('\n');
    const valueHtml = multiLine
      ? `<pre style="margin:4px 0 0;padding:4px 6px;background:rgba(0,0,0,.04);border-radius:4px;
                     font-size:10px;line-height:1.5;white-space:pre-wrap;word-break:break-all;
                     max-height:200px;overflow-y:auto;font-family:monospace">${esc(text)}</pre>`
      : `<span style="font-size:11px;overflow:hidden;text-overflow:ellipsis;
                      white-space:nowrap">${esc(text)}</span>`;
    responseHtml = `
      <div style="margin-top:4px;border-top:1px dashed ${c.border};padding-top:4px">
        <button onclick="(function(btn){
                   var d=document.getElementById('${uid}');
                   var open=d.style.display!=='none';
                   d.style.display=open?'none':'block';
                   btn.textContent=open?'▶ response':'▼ response';
                 })(this)"
                style="background:none;border:none;cursor:pointer;font-size:10px;
                       color:${c.bodyFg};opacity:.5;padding:0;font-family:inherit">
          ▶ response
        </button>
        <div id="${uid}" style="display:none">${valueHtml}</div>
      </div>`;
  }
  if (!responseHtml && node.response != null && node.response !== '') {
    let respText = '';
    if (typeof node.response === 'object') {
      const r = node.response;
      if (r.stdout || r.stderr) {
        const parts = [];
        if (r.exit_code != null && r.exit_code !== 0) parts.push(`exit: ${r.exit_code}`);
        if (r.stdout) parts.push(String(r.stdout).slice(0, 500));
        if (r.stderr) parts.push(`stderr: ${String(r.stderr).slice(0, 200)}`);
        respText = parts.join('\n');
      } else {
        respText = JSON.stringify(r, null, 2);
      }
    } else {
      respText = String(node.response).slice(0, 600);
    }
    if (respText) {
      const ruid = `nresp-${node.id}`;
      responseHtml = `
        <div style="margin-top:4px;border-top:1px dashed ${c.border};padding-top:4px">
          <button onclick="(function(btn){
                     var d=document.getElementById('${ruid}');
                     var open=d.style.display!=='none';
                     d.style.display=open?'none':'block';
                     btn.textContent=open?'▶ response':'▼ response';
                   })(this)"
                  style="background:none;border:none;cursor:pointer;font-size:10px;
                         color:${c.bodyFg};opacity:.5;padding:0;font-family:inherit">
            ▶ response
          </button>
          <div id="${ruid}" style="display:none">
            <pre style="margin:4px 0 0;padding:4px 6px;background:rgba(0,0,0,.04);border-radius:4px;
                       font-size:10px;line-height:1.5;white-space:pre-wrap;word-break:break-all;
                       max-height:200px;overflow-y:auto;font-family:monospace">${esc(respText)}</pre>
          </div>
        </div>`;
    }
  }
  const hasBody = mainHtml || tokenRowHtml || agentCostHtml || thinkingHtml || responseHtml;
  return `
    <div style="border:1px solid ${c.border};border-radius:8px;overflow:hidden;
                box-shadow:0 1px 3px rgba(0,0,0,.08);min-width:220px;max-width:480px">
      <!-- header -->
      <div style="background:${c.hdrBg};color:${c.hdrFg};padding:6px 10px;
                  display:flex;align-items:center;gap:6px;font-size:12px;font-weight:600">
        <span style="flex-shrink:0">${c.icon}</span>
        <span style="flex-shrink:0">${esc(node.tool)}</span>
        ${lbl
          ? `<span style="font-weight:400;opacity:.8;overflow:hidden;text-overflow:ellipsis;
                          white-space:nowrap;max-width:200px" title="${lbl}">· ${lbl}</span>`
          : ''}
        <div style="margin-left:auto;display:flex;align-items:center;gap:8px;flex-shrink:0">
          ${badge}
          ${modelChip}
          ${tokBadge}
          <span style="font-size:10px;opacity:.6;font-family:monospace">${esc(tStr)}</span>
          ${node.parentId != null
            ? `<button title="Go to parent"
                       onclick="event.stopPropagation();var el=document.getElementById('node-${node.parentId}');if(el){el.scrollIntoView({behavior:'smooth',block:'nearest'});el.style.outline='2px solid rgba(255,255,255,.8)';setTimeout(()=>el.style.outline='',1200);}"
                       style="background:rgba(255,255,255,.15);border:none;cursor:pointer;
                              border-radius:3px;padding:1px 4px;font-size:10px;color:inherit;
                              line-height:1.2;flex-shrink:0">⬆</button>`
            : ''}
          ${node.children.length
            ? (() => {
                const isExp = window._expanded && window._expanded.has(node.id);
                const cnt   = node.children.length;
                return `<button id="toggle-${node.id}"
                           data-count="${cnt}"
                           title="${isExp ? 'Collapse' : 'Expand'} ${cnt} child${cnt>1?'ren':''}"
                           onclick="event.stopPropagation();toggleNode('${node.id}','ch-${node.id}')"
                           style="background:rgba(255,255,255,.15);border:none;cursor:pointer;
                                  border-radius:3px;padding:1px 6px;font-size:10px;color:inherit;
                                  line-height:1.4;flex-shrink:0;font-family:inherit">
                         ${isExp ? '▼' : '▶'} ${cnt}
                       </button>`;
              })()
            : ''}
        </div>
      </div>
      ${hasBody
        ? `<div style="background:${c.bodyBg};color:${c.bodyFg};
                       padding:6px 10px 8px;border-top:1px solid ${c.border}">
             ${mainHtml}${tokenRowHtml}${agentCostHtml}${thinkingHtml}${responseHtml}
           </div>`
        : ''}
    </div>`;
}

function renderGroup(children) {
  if (!children.length) return '';
  const step1 = [];
  let pbatch = [];
  for (const ch of children) {
    if (ch.parallel) {
      pbatch.push(ch);
    } else {
      if (pbatch.length) { step1.push({type:'parallel', nodes:pbatch}); pbatch = []; }
      step1.push({type:'single', node:ch});
    }
  }
  if (pbatch.length) step1.push({type:'parallel', nodes:pbatch});
  const groups = [];
  let cmdBatch = [];
  function flushCmd() {
    if (!cmdBatch.length) return;
    if (cmdBatch.length === 1) {
      groups.push({type:'single', node:cmdBatch[0]});
    } else {
      groups.push({type:'cmdgroup', nodes:[...cmdBatch]});
    }
    cmdBatch = [];
  }
  for (const item of step1) {
    if (item.type === 'single' && item.node.tool !== 'Agent') {
      cmdBatch.push(item.node);
    } else {
      flushCmd();
      groups.push(item);
    }
  }
  flushCmd();
  return groups.map(g => {
    if (g.type === 'parallel') {
      const cols = g.nodes.map(n => {
        const cc = tc(n.tool);
        let kids = '';
        if (n.children.length) {
          const isExp = window._expanded && window._expanded.has(n.id);
          kids = `<div id="ch-${n.id}" style="display:${isExp?'block':'none'}">
            <div class="tree-children" style="margin-top:10px">${renderGroup(n.children)}</div>
          </div>`;
        }
        return `
          <div style="flex:1;min-width:220px;display:flex;flex-direction:column">
            <div style="display:flex;align-items:center;margin-bottom:6px">
              <div style="width:10px;height:10px;border-radius:50%;background:${cc.hdrBg};
                          border:2px solid #f1f5f9;box-shadow:0 0 0 1px rgba(0,0,0,.15);flex-shrink:0"></div>
              <div style="flex:1;height:2px;background:${cc.hdrBg};opacity:.35"></div>
            </div>
            ${nodeCard(n)}${kids}
          </div>`;
      }).join('');
      return `
        <div class="tree-node">
          <span class="node-dot" style="background:#64748b"></span>
          <div style="border:1.5px dashed #94a3b8;border-radius:10px;padding:10px 10px 10px;
                      background:rgba(241,245,249,.55)">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
              <span style="font-size:10px;font-weight:600;color:#475569;letter-spacing:.03em;
                           background:#e2e8f0;border-radius:999px;padding:1px 8px;flex-shrink:0">
                ∥ ${g.nodes.length} parallel
              </span>
              <div style="flex:1;height:1px;background:#cbd5e1"></div>
            </div>
            <div style="display:flex;flex-direction:row;gap:12px;align-items:flex-start;
                        flex-wrap:wrap;overflow-x:auto">${cols}</div>
          </div>
        </div>`;
    }
    if (g.type === 'cmdgroup') {
      const gid = 'cg-' + g.nodes[0].id;
      const isExp = window._expanded && window._expanded.has(gid);
      const toolCounts = {};
      for (const n of g.nodes) {
        const key = n.tool;
        toolCounts[key] = (toolCounts[key] || 0) + 1;
      }
      const summary = Object.entries(toolCounts)
        .map(([t, c]) => `${tc(t).icon} ${t}` + (c > 1 ? ` ×${c}` : ''))
        .join('  ');
      const cnt = g.nodes.length;
      const inner = g.nodes.map(n => renderNode(n)).join('');
      return `
        <div class="tree-node">
          <span class="node-dot" style="background:#6b7280"></span>
          <div style="border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;
                      box-shadow:0 1px 3px rgba(0,0,0,.06);min-width:220px;max-width:480px">
            <div onclick="toggleCmdGroup('${gid}')"
                 style="background:#f1f5f9;color:#475569;padding:6px 10px;
                        display:flex;align-items:center;gap:8px;font-size:11px;
                        cursor:pointer;user-select:none">
              <span style="font-size:10px;font-weight:700;flex-shrink:0"
                    id="cg-chev-${gid}">${isExp ? '▼' : '▶'}</span>
              <span style="font-weight:600">${cnt} commands</span>
              <span style="opacity:.6;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${summary}</span>
            </div>
          </div>
          <div id="${gid}" style="display:${isExp ? 'block' : 'none'}">
            <div class="tree-children" style="margin-top:6px">${inner}</div>
          </div>
        </div>`;
    }
    return renderNode(g.node);
  }).join('');
}

function renderNode(node) {
  const c = tc(node.tool);
  let kids = '';
  if (node.children.length) {
    const isExp = window._expanded && window._expanded.has(node.id);
    kids = `<div id="ch-${node.id}" style="display:${isExp?'block':'none'}">
      <div class="tree-children" style="margin-top:10px">${renderGroup(node.children)}</div>
    </div>`;
  }
  return `<div class="tree-node" id="node-${node.id}">
    <span class="node-dot" style="background:${c.hdrBg}"></span>
    ${nodeCard(node)}${kids}
  </div>`;
}

function renderTree(root) {
  if (!root || !root.children.length) return '';
  return `
    <div>
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:0">
        <div style="display:flex;flex-direction:column;align-items:center;flex-shrink:0">
          <div style="width:34px;height:34px;border-radius:50%;background:#1e293b;
                      display:flex;align-items:center;justify-content:center;
                      color:#fff;font-size:14px;font-weight:700;box-shadow:0 2px 6px rgba(0,0,0,.25)">C</div>
          <div style="width:2px;height:10px;background:#64748b"></div>
        </div>
        <div>
          <span style="font-size:13px;font-weight:700;color:#1e293b">Claude</span>
          <span style="font-size:11px;color:#9ca3af;margin-left:6px;font-family:monospace">${esc(fmtT(root.ts))} UTC</span>
        </div>
      </div>
      <div class="tree-children">${renderGroup(root.children)}</div>
    </div>`;
}

// ─── Stats panel renderer ─────────────────────────────────────────────────
function renderPromptPanel(prompt) {
  if (!prompt) return '';
  const escaped = esc(prompt);
  const id = 'prompt-toggle-' + Date.now();
  return `
    <div style="background:white;border:1px solid #e2e8f0;border-radius:10px;
                box-shadow:0 1px 3px rgba(0,0,0,.06);overflow:hidden">
      <div onclick="(function(){
             var c=document.getElementById('${id}');
             var a=c.parentElement.querySelector('[data-arrow]');
             if(c.style.display==='none'){c.style.display='block';a.textContent='▼'}
             else{c.style.display='none';a.textContent='▶'}
           })()"
           style="padding:8px 12px;cursor:pointer;display:flex;align-items:center;gap:6px;
                  user-select:none">
        <span data-arrow style="font-size:10px;color:#64748b;flex-shrink:0">▶</span>
        <span style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;
                     letter-spacing:.06em">Initial prompt</span>
        <span style="font-size:10px;color:#94a3b8;margin-left:4px;overflow:hidden;
                     text-overflow:ellipsis;white-space:nowrap;flex:1">${escaped.slice(0, 80)}${escaped.length > 80 ? '…' : ''}</span>
      </div>
      <div id="${id}" style="display:none;padding:0 12px 10px 28px">
        <pre style="font-size:11px;color:#334155;white-space:pre-wrap;word-break:break-word;
                    line-height:1.5;margin:0;font-family:ui-monospace,SFMono-Regular,Menlo,monospace">${escaped}</pre>
      </div>
    </div>`;
}

function renderStatsPanel(s) {
  if (!s || s.error) return '';
  const tok  = s.tokens  || {};
  const tools = s.tools  || {};
  const kids  = s.child_sessions || [];
  const totalIn  = (tok.input  || 0) + (tok.cache_read || 0) + (tok.cache_create || 0);
  const totalOut = tok.output || 0;
  function pill(label, val, bg, fg) {
    if (!val) return '';
    return `<span style="display:inline-flex;align-items:center;gap:3px;font-size:10px;
                          background:${bg};color:${fg};border-radius:999px;padding:1px 7px;
                          font-weight:600;white-space:nowrap">
              ${label} <span style="font-weight:400">${val.toLocaleString()}</span>
            </span>`;
  }
  const sortedTools = Object.entries(tools).sort((a,b) => b[1]-a[1]).slice(0, 8);
  const maxCount = sortedTools[0]?.[1] || 1;
  const toolRows = sortedTools.map(([name, cnt]) => {
    const pct = Math.round((cnt / maxCount) * 100);
    const c = tc(name);
    return `<div style="display:flex;align-items:center;gap:6px;font-size:10px">
      <span style="width:80px;text-align:right;opacity:.7;flex-shrink:0">${esc(name)}</span>
      <div style="flex:1;height:6px;background:#f1f5f9;border-radius:3px;overflow:hidden">
        <div style="width:${pct}%;height:100%;background:${c.hdrBg};border-radius:3px"></div>
      </div>
      <span style="width:24px;font-weight:600;color:#475569">${cnt}</span>
    </div>`;
  }).join('');
  const childRows = kids.map(k =>
    `<div style="display:flex;align-items:center;gap:6px;font-size:10px;padding:2px 0">
       <span style="font-size:12px">🤖</span>
       <span style="font-weight:600;color:#3b82f6">${esc(k.agent_type || k.agent_id)}</span>
       <span style="opacity:.55;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(k.description)}</span>
     </div>`
  ).join('');
  return `
    <div style="background:white;border:1px solid #e2e8f0;border-radius:10px;
                padding:10px 12px;display:flex;flex-wrap:wrap;gap:12px;
                box-shadow:0 1px 3px rgba(0,0,0,.06)">
      <div style="flex:1;min-width:180px">
        <div style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;
                    letter-spacing:.06em;margin-bottom:6px">Tokens</div>
        <div style="display:flex;flex-wrap:wrap;gap:4px">
          ${pill('in',  tok.input,        '#dbeafe','#1e40af')}
          ${pill('out', tok.output,       '#dcfce7','#166534')}
          ${pill('↩cache', tok.cache_read,  '#fef9c3','#713f12')}
          ${pill('☁cache', tok.cache_create,'#f3e8ff','#6b21a8')}
        </div>
      </div>
      ${sortedTools.length ? `
      <div style="flex:1;min-width:200px">
        <div style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;
                    letter-spacing:.06em;margin-bottom:6px">Tools used</div>
        <div style="display:flex;flex-direction:column;gap:3px">${toolRows}</div>
      </div>` : ''}
      ${kids.length ? `
      <div style="flex:1;min-width:180px">
        <div style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;
                    letter-spacing:.06em;margin-bottom:6px">Spawned agents (${kids.length})</div>
        ${childRows}
      </div>` : ''}
    </div>`;
}

// ─── Mermaid ───────────────────────────────────────────────────────────────
mermaid.initialize({ startOnLoad: false, theme: 'neutral' });

// ─── Alpine component ──────────────────────────────────────────────────────
window._timeline   = [];
window._tokenIndex = new Map();
window._expanded   = new Set();

function toggleNode(nodeId, childrenId) {
  const exp = window._expanded;
  const kids = document.getElementById(childrenId);
  const btn  = document.getElementById('toggle-' + nodeId);
  if (!kids) return;
  if (exp.has(nodeId)) {
    exp.delete(nodeId);
    kids.style.display = 'none';
    if (btn) btn.setAttribute('data-open', '');
  } else {
    exp.add(nodeId);
    kids.style.display = 'block';
    if (btn) btn.setAttribute('data-open', '1');
  }
  if (btn) {
    const cnt = btn.getAttribute('data-count') || '';
    btn.textContent = (exp.has(nodeId) ? '▼' : '▶') + (cnt ? ' ' + cnt : '');
  }
}

function toggleCmdGroup(gid) {
  const exp = window._expanded;
  const el  = document.getElementById(gid);
  const chev = document.getElementById('cg-chev-' + gid);
  if (!el) return;
  if (exp.has(gid)) {
    exp.delete(gid);
    el.style.display = 'none';
    if (chev) chev.textContent = '▶';
  } else {
    exp.add(gid);
    el.style.display = 'block';
    if (chev) chev.textContent = '▼';
  }
}

function flowDashboard() {
  return {
    sessions: [], activeSessionId: null, entries: [],
    tab: 'tree', liveConnected: false,
    openResps: {},
    collapsedProjects: {},
    diagramMd: null, diagramSvg: null, diagramLoading: false, diagramTruncated: false,
    _entryES: null, _globalES: null, _treeTimer: null,

    async init() {
      await this.loadSessions();
      this.connectGlobalStream();
      if (this.sessions.length > 0) await this.selectSession(this.sessions[0].session_id);
    },

    async loadSessions() {
      try { this.sessions = await fetch('/api/sessions').then(r => r.json()); }
      catch(e) { console.error('loadSessions', e); }
    },

    async selectSession(id) {
      if (id === this.activeSessionId) return;
      this.closeEntryStream();
      this.activeSessionId = id;
      this.entries = [];
      this.openResps = {};
      this.diagramMd = null;
      this.diagramSvg = null;
      this.diagramTruncated = false;
      window._timeline   = [];
      window._tokenIndex = new Map();
      window._expanded   = new Set();
      document.getElementById('tree-container').innerHTML = '';
      const dc = document.getElementById('diagram-container');
      if (dc) dc.innerHTML = '';
      try {
        const d = await fetch(`/api/sessions/${id}`).then(r => r.json());
        this.entries = d.entries || [];
      } catch(e) { console.error('selectSession', e); }
      this.scheduleTree();
      this.loadStats();
      this.connectEntryStream(id);
    },

    switchTab(t) {
      this.tab = t;
      if (t === 'tree') { this.scheduleTree(); this.loadStats(); }
      if (t === 'diagram' && !this.diagramSvg) this.loadDiagram();
    },

    scheduleTree() {
      clearTimeout(this._treeTimer);
      this._treeTimer = setTimeout(() => {
        const el = document.getElementById('tree-container');
        if (!el) return;
        const wrap = el.parentElement;
        const top  = wrap ? wrap.scrollTop : 0;
        el.innerHTML = renderTree(buildTree(this.entries));
        if (wrap) wrap.scrollTop = top;
      }, 80);
    },

    async loadStats() {
      const panel = document.getElementById('stats-panel');
      const promptPanel = document.getElementById('prompt-panel');
      if (!panel || !this.activeSessionId) return;
      const loadingFor = this.activeSessionId;
      panel.innerHTML = `<div style="font-size:11px;color:#94a3b8;padding:4px 0">Loading stats…</div>`;
      if (promptPanel) promptPanel.innerHTML = '';
      try {
        const s = await fetch(`/api/sessions/${loadingFor}/stats`).then(r => r.json());
        if (loadingFor !== this.activeSessionId) return;
        window._timeline   = s.timeline || [];
        window._tokenIndex = buildTokenIndex(this.entries, window._timeline);
        panel.innerHTML = renderStatsPanel(s);
        if (promptPanel) promptPanel.innerHTML = renderPromptPanel(s.initial_prompt);
        this.scheduleTree();
      } catch(e) {
        if (loadingFor !== this.activeSessionId) return;
        window._timeline   = [];
        window._tokenIndex = new Map();
        panel.innerHTML = '';
        if (promptPanel) promptPanel.innerHTML = '';
      }
    },

    connectEntryStream(id) {
      this._entryES = new EventSource(`/api/sessions/${id}/stream`);
      this._entryES.addEventListener('connected', () => { this.liveConnected = true; });
      this._entryES.addEventListener('entry', ev => {
        this.entries.push(JSON.parse(ev.data));
        this.scheduleTree();
        if (this.tab === 'events') {
          this.$nextTick(() => {
            const el = document.querySelector('tbody tr:last-child');
            if (el) el.scrollIntoView({behavior:'smooth', block:'nearest'});
          });
        }
      });
      this._entryES.addEventListener('ping', () => {});
      this._entryES.onerror = () => {
        this.liveConnected = false;
        this.closeEntryStream();
        setTimeout(() => { if (this.activeSessionId === id) this.connectEntryStream(id); }, 3000);
      };
    },

    async loadDiagram() {
      if (!this.activeSessionId || this.diagramLoading) return;
      this.diagramLoading = true;
      try {
        const d = await fetch(`/api/sessions/${this.activeSessionId}/diagram`).then(r => r.json());
        this.diagramMd = d.mermaid;
        this.diagramTruncated = d.truncated || false;
        const container = document.getElementById('diagram-container');
        if (this.diagramMd && container) {
          const { svg } = await mermaid.render('mg-' + Date.now(), this.diagramMd);
          this.diagramSvg = svg;
          container.innerHTML = svg;
        }
      } catch(e) {
        console.error('loadDiagram', e);
      } finally {
        this.diagramLoading = false;
      }
    },

    downloadSvg() {
      if (!this.diagramSvg) return;
      const a = Object.assign(document.createElement('a'), {
        href: URL.createObjectURL(new Blob([this.diagramSvg], { type: 'image/svg+xml' })),
        download: `flow-${this.activeSessionId}.svg`,
      });
      a.click(); URL.revokeObjectURL(a.href);
    },

    downloadMd() {
      if (!this.diagramMd) return;
      const content = '```mermaid\n' + this.diagramMd + '\n```';
      const a = Object.assign(document.createElement('a'), {
        href: URL.createObjectURL(new Blob([content], { type: 'text/markdown' })),
        download: `flow-${this.activeSessionId}.md`,
      });
      a.click(); URL.revokeObjectURL(a.href);
    },

    closeEntryStream() {
      if (this._entryES) { this._entryES.close(); this._entryES = null; this.liveConnected = false; }
    },

    connectGlobalStream() {
      this._globalES = new EventSource('/api/stream/global');
      this._globalES.addEventListener('session_new', () => this.loadSessions());
      this._globalES.addEventListener('ping', () => {});
    },

    rowClass(e) {
      if (e.tool === 'Agent' && e.event === 'pre')  return 'bg-blue-50 text-blue-900 font-semibold';
      if (e.tool === 'Agent' && e.event === 'post') return 'bg-blue-100 text-blue-700';
      if (e.tool === 'Skill')                        return 'bg-purple-50 text-purple-800';
      if (e.tool === 'SendMessage')                  return 'bg-amber-50 text-amber-800';
      if (e.tool === 'TaskCreate' || e.tool === 'TaskUpdate') return 'bg-green-50 text-green-800';
      if (e.tool === 'Bash')                         return e.event === 'post' ? 'bg-slate-100 text-slate-600' : 'bg-slate-50 text-slate-700';
      if (e.tool === 'Edit' || e.tool === 'Write')   return 'bg-yellow-50 text-yellow-800';
      if (e.tool === 'Command')                      return 'bg-indigo-50 text-indigo-800 font-semibold';
      if (['Read','Glob','Grep'].includes(e.tool))   return 'bg-gray-50 text-gray-500';
      if (e.tool?.startsWith('mcp__'))               return 'bg-cyan-50 text-cyan-800';
      return 'bg-white text-gray-700';
    },

    summarise(e) {
      if (e.cmd) return e.cmd;
      const i = e.input || {};
      switch (e.tool) {
        case 'Agent':       return `[${i.agent||'?'}] ${i.description||''}`;
        case 'Skill':       return `${i.skill||''}${i.args ? ' '+i.args : ''}`;
        case 'SendMessage': return `→ ${i.to||''}: ${(i.message||'').slice(0,80)}`;
        case 'TaskCreate':  return i.title || JSON.stringify(i).slice(0,80);
        case 'TaskUpdate':  return `${i.id||''} → ${i.status||''}`;
        case 'Bash':        return i.description || (i.command||'').slice(0,80);
        case 'Read': case 'Glob': case 'Grep':
          return (i.path||i.file_path||i.pattern||'').split('/').slice(-3).join('/');
        case 'Edit': case 'Write':
          return (i.file_path||'').split('/').slice(-3).join('/');
        case 'Command':     return `${i.command||''} ${i.args||''}`.trim();
        default: return JSON.stringify(i).slice(0,100);
      }
    },

    projectGroups() {
      const map = {};
      for (const s of this.sessions) {
        const p = s.project || '';
        if (!map[p]) map[p] = [];
        map[p].push(s);
      }
      const activeProject = this.sessions.find(s => s.session_id === this.activeSessionId)?.project || '';
      return Object.entries(map)
        .sort(([a], [b]) => {
          if (a === activeProject) return -1;
          if (b === activeProject) return 1;
          return a.localeCompare(b);
        })
        .map(([project, sessions]) => ({ project, sessions }));
    },

    toggleProject(name) {
      if (this.collapsedProjects[name]) delete this.collapsedProjects[name];
      else this.collapsedProjects[name] = true;
    },

    toggleEvtResp(i) {
      if (this.openResps[i]) delete this.openResps[i];
      else this.openResps[i] = true;
    },

    fmtKi(n) {
      if (!n) return '0';
      if (n >= 1000) return (Math.round(n / 100) / 10) + 'k';
      return String(n);
    },

    fmtResp(r) {
      if (r == null || r === '') return '';
      if (typeof r === 'object') {
        if (r.stdout != null || r.stderr != null) {
          const parts = [];
          if (r.exit_code != null && r.exit_code !== 0) parts.push('exit: ' + r.exit_code);
          if (r.stdout) parts.push(String(r.stdout));
          if (r.stderr) parts.push('stderr: ' + String(r.stderr));
          if (r.interrupted) parts.push('[interrupted]');
          return parts.join('\n') || '(empty)';
        }
        if (r.files) return `${r.count||0} files: ${r.files.join(', ')}`;
        if (r.matches) return `${r.num_files||0} files matched\n${r.matches}`;
        if (r.content) return r.content;
        return JSON.stringify(r, null, 2);
      }
      return String(r);
    },
  };
}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Cyber Dashboard HTML (Vue 3 + JetBrains Mono)
# ---------------------------------------------------------------------------
_CYBER_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CLAUDE FLOW // CYBER</title>
<script src="/static/vue.global.prod.js"></script>
<script src="/static/mermaid.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:       #06060f;
    --bg2:      #0c0c1a;
    --bg3:      #12122a;
    --cyan:     #00d4ff;
    --green:    #00ff9f;
    --purple:   #b44cff;
    --orange:   #ff8c35;
    --red:      #ff0055;
    --dim:      rgba(0,212,255,.18);
    --border:   rgba(0,212,255,.22);
    --text:     #c8e6ff;
    --muted:    rgba(200,230,255,.38);
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; background: var(--bg); color: var(--text);
               font-family: 'JetBrains Mono', 'Fira Code', monospace; overflow: hidden; }
  body::after {
    content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 9999;
    background: repeating-linear-gradient(0deg, transparent, transparent 2px,
                rgba(0,0,0,.03) 2px, rgba(0,0,0,.03) 4px);
  }
  body::before {
    content: ''; position: fixed; inset: 0; pointer-events: none; z-index: 9998;
    background: radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,.6) 100%);
  }
  #app { height: 100vh; display: flex; flex-direction: column; }
  .topbar {
    display: flex; align-items: center; gap: 12px;
    padding: 8px 16px; border-bottom: 1px solid var(--border);
    background: rgba(0,212,255,.04); flex-shrink: 0; z-index: 10;
  }
  .topbar__logo {
    font-size: 13px; font-weight: 700; letter-spacing: .12em;
    color: var(--cyan); text-shadow: 0 0 12px var(--cyan);
  }
  .topbar__sep { color: var(--border); }
  .topbar__session { font-size: 11px; color: var(--muted); }
  .topbar__live {
    display: flex; align-items: center; gap: 5px; font-size: 10px;
    color: var(--green); margin-left: auto;
  }
  .topbar__live-dot {
    width: 7px; height: 7px; border-radius: 50%; background: var(--green);
    box-shadow: 0 0 8px var(--green);
    animation: pulse 1.4s ease-in-out infinite;
  }
  .topbar__link {
    font-size: 10px; letter-spacing: .06em; color: var(--muted);
    text-decoration: none; border: 1px solid var(--border);
    border-radius: 3px; padding: 2px 8px;
    transition: color .2s, border-color .2s;
  }
  .topbar__link:hover { color: var(--cyan); border-color: var(--cyan); }
  .main { display: flex; flex: 1; overflow: hidden; }
  .sessions {
    width: 220px; flex-shrink: 0; border-right: 1px solid var(--border);
    background: var(--bg2); display: flex; flex-direction: column; overflow: hidden;
  }
  .sessions__hdr {
    padding: 8px 12px; font-size: 9px; font-weight: 700; letter-spacing: .14em;
    color: var(--cyan); border-bottom: 1px solid var(--border);
    text-transform: uppercase;
  }
  .sessions__list { overflow-y: auto; flex: 1; padding: 4px 0; }
  .session-item {
    padding: 7px 12px; cursor: pointer; border-left: 2px solid transparent;
    transition: background .15s, border-color .15s;
    display: flex; flex-direction: column; gap: 2px;
  }
  .session-item:hover { background: rgba(0,212,255,.06); }
  .session-item.active {
    border-left-color: var(--cyan); background: rgba(0,212,255,.08);
  }
  .session-item__id { font-size: 11px; color: var(--text); }
  .session-item__meta { font-size: 9px; color: var(--muted); display: flex; gap: 6px; }
  .session-item__dot {
    width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
    align-self: center; margin-left: auto;
  }
  .session-item__dot--live { background: var(--green); box-shadow: 0 0 6px var(--green);
    animation: pulse 1.4s ease-in-out infinite; }
  .session-item__dot--done { background: var(--muted); }
  .right { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  .hud {
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    padding: 6px 14px; border-bottom: 1px solid var(--border);
    background: rgba(0,212,255,.03); flex-shrink: 0;
  }
  .hud__label { font-size: 9px; color: var(--muted); text-transform: uppercase;
                letter-spacing: .1em; }
  .hud__pill {
    font-size: 10px; border-radius: 3px; padding: 1px 7px; font-weight: 700;
    letter-spacing: .04em; border: 1px solid;
  }
  .hud__pill--in     { color: #60a5fa; border-color: rgba(96,165,250,.35); background: rgba(96,165,250,.08); }
  .hud__pill--out    { color: #4ade80; border-color: rgba(74,222,128,.35); background: rgba(74,222,128,.08); }
  .hud__pill--cr     { color: #fbbf24; border-color: rgba(251,191,36,.3);  background: rgba(251,191,36,.06); }
  .hud__pill--cc     { color: #c084fc; border-color: rgba(192,132,252,.3); background: rgba(192,132,252,.06); }
  .hud__tools { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .hud__tool-badge {
    font-size: 9px; color: var(--muted); border: 1px solid var(--border);
    border-radius: 3px; padding: 1px 5px;
  }
  .hud__sep { width: 1px; height: 14px; background: var(--border); }
  .tree-wrap { flex: 1; overflow: auto; padding: 16px 20px; }
  .tree-wrap::-webkit-scrollbar { width: 6px; }
  .tree-wrap::-webkit-scrollbar-track { background: var(--bg2); }
  .tree-wrap::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  .cn { position: relative; margin-bottom: 4px; }
  .cn__children {
    padding-left: 28px; border-left: 1px solid var(--border);
    margin-left: 14px; margin-top: 4px;
  }
  .cn__children > .cn { position: relative; }
  .cn__children > .cn::before {
    content: ''; position: absolute; left: -28px; top: 18px;
    width: 22px; height: 1px; background: var(--border);
  }
  .cn__card {
    display: flex; flex-direction: column;
    border: 1px solid var(--border); border-radius: 4px;
    background: var(--bg2);
    transition: border-color .2s, box-shadow .2s;
    overflow: hidden; max-width: 560px;
  }
  .cn__card:hover { border-color: rgba(0,212,255,.5); }
  .cn--active > .cn__card {
    border-color: var(--green);
    box-shadow: 0 0 14px rgba(0,255,159,.18), inset 0 0 20px rgba(0,255,159,.04);
    animation: glow-pulse 2s ease-in-out infinite;
  }
  .cn__header {
    display: flex; align-items: center; gap: 7px;
    padding: 5px 9px; cursor: pointer; user-select: none;
  }
  .cn__tag {
    font-size: 9px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
    border-radius: 2px; padding: 1px 5px; flex-shrink: 0;
  }
  .cn__tag--agent       { background: rgba(0,212,255,.15); color: var(--cyan); border: 1px solid rgba(0,212,255,.4); }
  .cn__tag--skill       { background: rgba(180,76,255,.15); color: var(--purple); border: 1px solid rgba(180,76,255,.4); }
  .cn__tag--sendmessage { background: rgba(255,140,53,.15); color: var(--orange); border: 1px solid rgba(255,140,53,.4); }
  .cn__tag--taskcreate  { background: rgba(0,255,159,.12); color: var(--green); border: 1px solid rgba(0,255,159,.35); }
  .cn__tag--read,.cn__tag--glob,.cn__tag--grep {
    background: rgba(100,116,139,.15); color: #94a3b8; border: 1px solid rgba(100,116,139,.35); }
  .cn__tag--claude      { background: rgba(255,255,255,.08); color: #fff; border: 1px solid rgba(255,255,255,.25); }
  .cn__tag--cmdgroup    { background: rgba(100,116,139,.2); color: #94a3b8; border: 1px solid rgba(100,116,139,.4); }
  .cn__card--cmdgroup   { cursor: pointer; }
  .cn__card--cmdgroup:hover { border-color: rgba(100,116,139,.6); }
  .cn__tag--bash        { background: rgba(30,41,59,.4); color: #cbd5e1; border: 1px solid rgba(100,116,139,.5); }
  .cn__tag--edit        { background: rgba(202,138,4,.15); color: #fbbf24; border: 1px solid rgba(202,138,4,.4); }
  .cn__tag--write       { background: rgba(180,83,9,.15); color: #f59e0b; border: 1px solid rgba(180,83,9,.4); }
  .cn__tag--command     { background: rgba(99,102,241,.15); color: #818cf8; border: 1px solid rgba(99,102,241,.4); }
  .cn__tag--taskupdate  { background: rgba(4,120,87,.15); color: var(--green); border: 1px solid rgba(4,120,87,.4); }
  .cn__tag--mcp         { background: rgba(8,145,178,.15); color: #22d3ee; border: 1px solid rgba(8,145,178,.4); }
  .cn__tag--user        { background: rgba(225,29,72,.18); color: #fb7185; border: 1px solid rgba(225,29,72,.45); }
  .cn__label { font-size: 11px; color: var(--muted); overflow: hidden;
               text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0; }
  .cn__label--bright { color: var(--text); }
  .cn__tokens { font-size: 9px; color: var(--muted); flex-shrink: 0; letter-spacing: .03em; }
  .cn__tokens span { color: var(--cyan); }
  .cn__status {
    font-size: 9px; flex-shrink: 0; padding: 1px 5px;
    border-radius: 2px; letter-spacing: .06em;
  }
  .cn__status--active  { color: var(--green); background: rgba(0,255,159,.1); animation: blink-text 1.2s step-end infinite; }
  .cn__status--pending { color: var(--orange); background: rgba(255,140,53,.1); }
  .cn__toggle { font-size: 10px; color: var(--muted); flex-shrink: 0; cursor: pointer;
                transition: color .15s; padding: 0 2px; }
  .cn__toggle:hover { color: var(--cyan); }
  .cn__body {
    padding: 5px 9px 6px;
    border-top: 1px solid rgba(0,212,255,.1);
    background: rgba(0,0,0,.2);
    display: flex; flex-direction: column; gap: 3px;
  }
  .cn__row { display: flex; gap: 6px; font-size: 10px; line-height: 1.5;
             overflow: hidden; align-items: baseline; }
  .cn__key { color: var(--muted); flex-shrink: 0; min-width: 52px; }
  .cn__val { color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cn__val--pre { white-space: pre-wrap; word-break: break-all; font-size: 9px;
                  max-height: 120px; overflow-y: auto; color: #94a3b8; }
  .cn__tok-row {
    display: flex; align-items: center; gap: 5px; flex-wrap: wrap;
    padding-top: 3px; border-top: 1px solid rgba(0,212,255,.08); margin-top: 1px;
  }
  .cn__tok-row .lbl { font-size: 9px; color: var(--muted); min-width: 40px; }
  .tok-pill {
    font-size: 9px; border-radius: 2px; padding: 0 5px; font-family: inherit;
    border: 1px solid;
  }
  .tok-pill--in  { color: #60a5fa; border-color: rgba(96,165,250,.4);  background: rgba(96,165,250,.1); }
  .tok-pill--out { color: #4ade80; border-color: rgba(74,222,128,.4);  background: rgba(74,222,128,.1); }
  .tok-pill--cr  { color: #fbbf24; border-color: rgba(251,191,36,.4);  background: rgba(251,191,36,.08); }
  .tok-pill--cc  { color: #c084fc; border-color: rgba(192,132,252,.4); background: rgba(192,132,252,.08); }
  .cn__resp-toggle {
    font-size: 9px; color: var(--muted); cursor: pointer; background: none; border: none;
    font-family: inherit; text-align: left; padding: 0; letter-spacing: .04em;
    transition: color .15s;
  }
  .cn__resp-toggle:hover { color: var(--cyan); }
  .cn__resp {
    font-size: 9px; white-space: pre-wrap; word-break: break-all;
    max-height: 160px; overflow-y: auto; color: #64748b;
    border-left: 2px solid rgba(0,212,255,.2); padding-left: 6px; margin-top: 3px;
  }
  .cn__parallel {
    border: 1px dashed rgba(0,212,255,.25); border-radius: 4px;
    background: rgba(0,212,255,.025); padding: 8px;
    max-width: 100%;
  }
  .cn__parallel-hdr {
    font-size: 9px; color: var(--cyan); letter-spacing: .1em; margin-bottom: 8px;
    text-transform: uppercase;
  }
  .cn__parallel-cols { display: flex; gap: 10px; overflow-x: auto; align-items: flex-start; }
  .cn__parallel-col  { flex: 1; min-width: 220px; }
  .cn--root > .cn__card {
    background: rgba(255,255,255,.04); border-color: rgba(255,255,255,.2);
    max-width: 280px;
  }
  .slide-enter-active { transition: all .28s cubic-bezier(.25,.46,.45,.94); }
  .slide-leave-active { transition: all .2s cubic-bezier(.55,.06,.68,.19); }
  .slide-enter-from   { opacity: 0; transform: translateY(-8px); }
  .slide-leave-to     { opacity: 0; transform: translateY(-4px); }
  .fade-enter-active { transition: opacity .25s; }
  .fade-leave-active { transition: opacity .15s; }
  .fade-enter-from, .fade-leave-to { opacity: 0; }
  @keyframes scanIn {
    from { opacity: 0; clip-path: inset(0 100% 0 0); }
    to   { opacity: 1; clip-path: inset(0 0% 0 0); }
  }
  .cn__card { animation: scanIn .22s ease-out both; }
  @keyframes glow-pulse {
    0%,100% { box-shadow: 0 0 10px rgba(0,255,159,.15), inset 0 0 20px rgba(0,255,159,.03); }
    50%      { box-shadow: 0 0 22px rgba(0,255,159,.35), inset 0 0 30px rgba(0,255,159,.07); }
  }
  @keyframes pulse {
    0%,100% { opacity: 1; transform: scale(1); }
    50%      { opacity: .5; transform: scale(.85); }
  }
  @keyframes blink-text {
    0%,100% { opacity: 1; } 50% { opacity: .3; }
  }
  .empty { display: flex; flex-direction: column; align-items: center;
           justify-content: center; height: 100%; gap: 10px;
           color: var(--muted); font-size: 12px; letter-spacing: .08em; }
  .empty__glyph { font-size: 36px; opacity: .3; }
  .kb-hint { position: fixed; bottom: 10px; right: 14px; font-size: 9px;
             color: var(--muted); letter-spacing: .06em; opacity: .6; pointer-events: none; }
  .diagram-panel {
    border-top: 1px solid var(--border); background: var(--bg2);
    flex-shrink: 0; display: flex; flex-direction: column;
    max-height: 45vh; overflow: hidden;
  }
  .diagram-panel__bar {
    display: flex; align-items: center; gap: 8px; flex-shrink: 0;
    padding: 6px 14px; border-bottom: 1px solid var(--border);
  }
  .diagram-panel__title {
    font-size: 9px; font-weight: 700; letter-spacing: .14em;
    color: var(--cyan); text-transform: uppercase;
  }
  .diagram-panel__btn {
    font-size: 9px; padding: 2px 8px; border-radius: 3px; cursor: pointer;
    border: 1px solid var(--border); background: none; font-family: inherit;
    color: var(--muted); letter-spacing: .06em; transition: color .15s, border-color .15s;
  }
  .diagram-panel__btn:hover { color: var(--cyan); border-color: var(--cyan); }
  .diagram-panel__btn:disabled { opacity: .4; cursor: default; }
  .diagram-panel__warn { font-size: 9px; color: #fbbf24; margin-left: 4px; }
  .diagram-panel__body { flex: 1; overflow: auto; padding: 12px 16px; }
  .diagram-panel__body svg { max-width: 100%; height: auto; }
  .diagram-panel__hint { font-size: 10px; color: var(--muted); letter-spacing: .04em; }
</style>
</head>
<body>
<div id="app">
  <div class="topbar">
    <span class="topbar__logo">CLAUDE FLOW</span>
    <span class="topbar__sep">//</span>
    <span class="topbar__session">{{ activeSession ? activeSession.slice(0,16) + '…' : 'no session' }}</span>
    <div v-if="liveConnected" class="topbar__live">
      <div class="topbar__live-dot"></div>LIVE
    </div>
    <a href="/" class="topbar__link" style="margin-left:auto">← CLASSIC</a>
    <button @click="toggleDiagram()"
            class="topbar__link"
            :style="diagramOpen ? 'color:var(--cyan);border-color:var(--cyan)' : ''">
      {{ diagramOpen ? '✕ DIAGRAM' : '⬡ DIAGRAM' }}
    </button>
  </div>

  <div class="main">
    <aside class="sessions">
      <div class="sessions__hdr">// sessions</div>
      <div class="sessions__list">
        <div v-for="grp in projectGroups" :key="grp.project">
          <div @click="toggleProject(grp.project)"
               style="padding:4px 12px;font-size:9px;font-weight:700;letter-spacing:.1em;
                      color:var(--cyan);background:rgba(0,212,255,.04);border-bottom:1px solid var(--border);
                      cursor:pointer;display:flex;align-items:center;gap:6px;
                      text-transform:uppercase;user-select:none">
            <span style="font-size:8px">{{ collapsedProjects[grp.project] ? '▶' : '▼' }}</span>
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
              {{ grp.project || '(no project)' }}
            </span>
            <span style="opacity:.5;font-weight:400">{{ grp.sessions.length }}</span>
          </div>
          <template v-if="!collapsedProjects[grp.project]">
            <div v-for="s in grp.sessions" :key="s.session_id"
                 class="session-item" :class="{ active: s.session_id === activeSession }"
                 @click="selectSession(s.session_id)">
              <div style="display:flex;align-items:center;gap:6px">
                <span class="session-item__id">{{ s.first_ts ? s.first_ts.slice(0,10) : s.session_id.slice(0,12) }}</span>
                <span class="session-item__dot"
                      :class="s.is_active ? 'session-item__dot--live' : 'session-item__dot--done'"></span>
              </div>
              <div class="session-item__meta">
                <span>{{ s.first_ts ? s.first_ts.slice(11,19) : '' }}</span>
                <span>→</span>
                <span>{{ s.last_ts ? s.last_ts.slice(11,19) : '' }}</span>
                <span style="margin-left:auto">{{ s.event_count }}ev</span>
              </div>
            </div>
          </template>
        </div>
        <div v-if="!sessions.length" style="padding:16px 12px;font-size:10px;color:var(--muted)">
          // no sessions yet
        </div>
      </div>
    </aside>

    <div class="right">
      <!-- Initial prompt (collapsed by default) -->
      <div v-if="stats && stats.initial_prompt" class="cyber-prompt"
           style="margin:6px 8px 0;border:1px solid var(--border);border-radius:6px;
                  background:rgba(0,212,255,.03);overflow:hidden;flex-shrink:0">
        <div @click="promptOpen = !promptOpen"
             style="padding:6px 10px;cursor:pointer;display:flex;align-items:center;gap:6px;
                    user-select:none">
          <span style="font-size:8px;color:var(--cyan);flex-shrink:0">{{ promptOpen ? '▼' : '▶' }}</span>
          <span style="font-size:9px;font-weight:700;color:var(--cyan);text-transform:uppercase;
                       letter-spacing:.08em">initial prompt</span>
          <span v-if="!promptOpen"
                style="font-size:9px;color:var(--muted);margin-left:4px;overflow:hidden;
                       text-overflow:ellipsis;white-space:nowrap;flex:1">
            {{ stats.initial_prompt.slice(0, 80) }}{{ stats.initial_prompt.length > 80 ? '…' : '' }}
          </span>
        </div>
        <div v-show="promptOpen"
             style="padding:0 10px 8px 24px">
          <pre style="font-size:10px;color:var(--text);white-space:pre-wrap;word-break:break-word;
                      line-height:1.5;margin:0;font-family:inherit;opacity:.85">{{ stats.initial_prompt }}</pre>
        </div>
      </div>

      <div class="hud" v-if="stats && stats.tokens">
        <span class="hud__label">tokens</span>
        <span class="hud__pill hud__pill--in"  v-if="stats.tokens.input">↑ {{ fmtK(stats.tokens.input) }}</span>
        <span class="hud__pill hud__pill--out" v-if="stats.tokens.output">↓ {{ fmtK(stats.tokens.output) }}</span>
        <span class="hud__pill hud__pill--cr"  v-if="stats.tokens.cache_read">↩ {{ fmtK(stats.tokens.cache_read) }}</span>
        <span class="hud__pill hud__pill--cc"  v-if="stats.tokens.cache_create">☁ {{ fmtK(stats.tokens.cache_create) }}</span>
        <div class="hud__sep"></div>
        <span class="hud__label">tools</span>
        <div class="hud__tools">
          <span class="hud__tool-badge" v-for="[t,c] in topTools" :key="t">{{ t }} ×{{ c }}</span>
        </div>
      </div>

      <div class="tree-wrap" ref="treeWrap">
        <div v-if="!activeSession" class="empty">
          <div class="empty__glyph">⬡</div>
          <span>// select a session</span>
        </div>
        <div v-else-if="!tree" class="empty">
          <span>// loading…</span>
        </div>
        <template v-else>
          <div class="cn cn--root" style="margin-bottom:8px">
            <div class="cn__card">
              <div class="cn__header">
                <span class="cn__tag cn__tag--claude">CLAUDE</span>
                <span class="cn__label cn__label--bright" style="font-size:12px">root</span>
                <span style="font-size:9px;color:var(--muted);margin-left:auto">{{ fmtT(tree.ts) }}</span>
              </div>
            </div>
            <div class="cn__children" v-if="tree.children.length">
              <cyber-node v-for="child in tree.children" :key="child.id"
                          :node="child" :token-index="tokenIndex" :depth="0" />
            </div>
          </div>
        </template>
      </div>
    </div>

      <!-- Diagram panel (slides in at bottom of right column) -->
      <transition name="slide">
        <div v-if="diagramOpen" class="diagram-panel">
          <div class="diagram-panel__bar">
            <span class="diagram-panel__title">// sequence diagram</span>
            <button class="diagram-panel__btn" @click="loadDiagram()" :disabled="diagramLoading">
              {{ diagramLoading ? 'generating…' : 'refresh' }}
            </button>
            <button v-if="diagramSvg" class="diagram-panel__btn" @click="downloadSvg()">↓ svg</button>
            <button v-if="diagramMd"  class="diagram-panel__btn" @click="downloadMd()">↓ markdown</button>
            <span v-if="diagramTruncated" class="diagram-panel__warn">⚠ last 200 events</span>
          </div>
          <div class="diagram-panel__body">
            <span v-if="!diagramSvg && !diagramLoading" class="diagram-panel__hint">
              click refresh to generate diagram
            </span>
            <div v-html="diagramSvg"></div>
          </div>
        </div>
      </transition>
    </div>
  </div>

  <div class="kb-hint">j/k navigate · space expand · esc collapse all</div>
</div>

<script>
const { createApp, ref, computed, onMounted, onUnmounted, watch, nextTick } = Vue;

mermaid.initialize({ startOnLoad: false, theme: 'dark' });

function fmtK(n) {
  if (!n) return '0';
  return n >= 1000 ? (Math.round(n / 100) / 10) + 'k' : String(n);
}
function fmtT(ts) {
  if (!ts) return '';
  return ts.slice(11, 19);
}
function fmtDate(ts) {
  if (!ts) return '';
  return ts.slice(0, 16).replace('T', ' ');
}
function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

const CONTAINER_TOOLS = new Set(['Agent', 'Skill', 'Bash']);

function buildTree(entries) {
  const root = {
    id:'root', tool:'Claude', children:[], status:'root',
    input:{}, ts: entries[0]?.ts || '', response:null, postTs:null,
    cmd:'', tokens:null,
  };
  const hasActionIds = entries.some(e => e.action_id);
  if (hasActionIds) return _buildTreeById(entries, root);
  return _buildTreeHeuristic(entries, root);
}

function _buildTreeById(entries, root) {
  const nodeMap = new Map();
  nodeMap.set(null, root); nodeMap.set(undefined, root);
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    if (e.event !== 'pre' && e.event !== 'command' && e.event !== 'prompt') continue;
    const node = {
      id: e.action_id || i, tool: e.tool, input: e.input || {}, ts: e.ts,
      cmd: e.cmd || '', tokens: e.tokens || null,
      status: CONTAINER_TOOLS.has(e.tool) ? 'active' : 'done',
      children: [], response: null, postTs: null,
      parallel: false, parentId: e.parent_id || null,
    };
    nodeMap.set(e.action_id, node);
    // User prompts always attach to root
    const par = e.event === 'prompt' ? root : (nodeMap.get(e.parent_id) || root);
    node.parentId = par.id;
    if (e.tool === 'Agent') {
      const activeSib = par.children.find(c => c.tool === 'Agent' && c.status === 'active');
      if (activeSib) {
        node.parallel = true;
        par.children.filter(c => c.tool === 'Agent' && (c.status === 'active' || c.parallel))
                    .forEach(c => c.parallel = true);
      }
    }
    par.children.push(node);
  }
  for (const e of entries) {
    if (e.event !== 'post') continue;
    const node = nodeMap.get(e.action_id);
    if (!node) continue;
    node.status = 'done'; node.response = e.response ?? ''; node.postTs = e.ts;
    if (e.tokens) node.tokens = e.tokens;
  }
  return root;
}

function _buildTreeHeuristic(entries, root) {
  const stack = [root];
  const openAgents = [];
  const agentKey = inp => inp?.subagent_type || inp?.agent || '';
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    if (e.event === 'post') {
      if (e.tool === 'Agent') {
        const key = agentKey(e.input);
        let mi = -1;
        for (let j = openAgents.length - 1; j >= 0; j--) {
          if (agentKey(openAgents[j].input) === key) { mi = j; break; }
        }
        if (mi === -1 && openAgents.length) mi = openAgents.length - 1;
        if (mi !== -1) {
          const node = openAgents[mi];
          node.status = 'done'; node.response = e.response ?? ''; node.postTs = e.ts;
          if (e.tokens) node.tokens = e.tokens;
          if (e.agent_total_tokens) node.agentTotalTokens = e.agent_total_tokens;
          if (e.agent_duration_ms)  node.agentDurationMs  = e.agent_duration_ms;
          if (e.agent_tool_count)   node.agentToolCount   = e.agent_tool_count;
          openAgents.splice(mi, 1);
          const si = stack.indexOf(node);
          if (si !== -1) stack.splice(si, 1);
        }
      } else {
        let found = false;
        for (let j = stack.length - 1; j >= 0 && !found; j--) {
          for (let k = stack[j].children.length - 1; k >= 0; k--) {
            const c = stack[j].children[k];
            if (c.tool === e.tool && c.status === 'pending') {
              c.status = 'done'; c.response = e.response ?? ''; c.postTs = e.ts;
              if (e.tokens) c.tokens = e.tokens;
              found = true; break;
            }
          }
        }
      }
      continue;
    }
    if (e.event === 'command' || e.event === 'prompt') {
      root.children.push({
        id: i, tool: e.tool || (e.event === 'prompt' ? 'User' : 'Command'),
        input: e.input || {}, ts: e.ts,
        cmd: e.cmd || '', tokens: e.tokens || null,
        model: e.model || null, thinking: e.thinking || null,
        status: 'done', children: [], response: null, postTs: null,
        parallel: false, parentId: root.id,
      });
      continue;
    }
    if (e.tool === 'Agent') {
      let parIdx = stack.length - 1;
      while (parIdx > 0 && stack[parIdx].tool === 'Agent' && stack[parIdx].status === 'active'
             && !stack[parIdx].children.some(c => c.tool !== 'Agent')) { parIdx--; }
      const par = stack[parIdx];
      const node = { id: i, tool: 'Agent', input: e.input || {}, ts: e.ts,
                     cmd: e.cmd || '', tokens: e.tokens || null,
                     model: e.model || null, thinking: e.thinking || null,
                     status: 'active', children: [], response: null, postTs: null,
                     parallel: false, parentId: par.id };
      const activeSib = par.children.find(c => c.tool === 'Agent' && c.status === 'active');
      if (activeSib) {
        node.parallel = true;
        par.children.filter(c => c.tool === 'Agent' && (c.status === 'active' || c.parallel))
                    .forEach(c => c.parallel = true);
      }
      par.children.push(node); openAgents.push(node); stack.push(node);
    } else {
      const par = stack[stack.length - 1];
      par.children.push({ id: i, tool: e.tool, input: e.input || {}, ts: e.ts,
                          cmd: e.cmd || '', tokens: e.tokens || null,
                          model: e.model || null, thinking: e.thinking || null,
                          status: (e.tool==='Skill'||e.tool==='SendMessage') ? 'pending' : 'done',
                          children: [], response: null, postTs: null, parallel: false, parentId: par.id });
    }
  }
  return root;
}

function buildTokenIndex(entries, timeline) {
  const idx = new Map();
  if (!timeline?.length) return idx;
  const tl = [...timeline].filter(m => m.ts).sort((a,b) => new Date(a.ts)-new Date(b.ts));
  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    if (e.event !== 'pre' || !e.ts) continue;
    const nodeMs = new Date(e.ts).getTime();
    let best = null, bestDiff = 10001;
    for (const m of tl) {
      const diff = Math.abs(new Date(m.ts).getTime() - nodeMs);
      if (diff < bestDiff && m.tools?.includes(e.tool)) { bestDiff = diff; best = m; }
    }
    if (!best) { bestDiff = 5001; for (const m of tl) { const diff = Math.abs(new Date(m.ts).getTime()-nodeMs); if (diff<bestDiff){bestDiff=diff;best=m;} } }
    if (best) idx.set(i, best);
  }
  return idx;
}

const CyberNode = {
  name: 'CyberNode',
  props: { node: Object, tokenIndex: Map, depth: { type: Number, default: 0 } },
  setup(props) {
    const expanded   = ref(false);
    const respOpen   = ref(false);
    const thinkOpen  = ref(false);
    const hasKids    = computed(() => props.node.children?.length > 0);
    const isParallel = computed(() => props.node.children?.some(c => c.parallel));
    const inlineTok = computed(() => props.node.tokens || null);
    const idxTok    = computed(() => props.tokenIndex?.get(props.node.id) || null);
    const tok       = computed(() => inlineTok.value || idxTok.value);
    const totalIn  = computed(() => tok.value ? (tok.value.input||0)+(tok.value.cache_read||0)+(tok.value.cache_write||0)+(tok.value.cache_create||0) : 0);
    const totalOut = computed(() => tok.value?.output || 0);
    const hasTok   = computed(() => tok.value && (totalIn.value || totalOut.value));
    const toolLower = computed(() => {
      const t = props.node.tool || '';
      return t.startsWith('mcp__') ? 'mcp' : t.toLowerCase();
    });
    const label = computed(() => {
      if (props.node.cmd) return props.node.cmd;
      const i = props.node.input || {};
      switch (props.node.tool) {
        case 'Agent':       return `${i.subagent_type||i.agent||'?'}`.trim();
        case 'Skill':       return `${i.skill||''}${i.args?' '+i.args:''}`;
        case 'SendMessage': return `→${i.to||''}: ${(i.message||'').slice(0,60)}`;
        case 'TaskCreate':  return i.subject || i.title || '';
        case 'TaskUpdate':  return `${i.taskId||i.id||''} → ${i.status||''}`;
        case 'Read': case 'Glob': case 'Grep':
          return (i.file_path||i.path||i.pattern||'').split('/').slice(-2).join('/');
        case 'Bash':
          return i.description || (i.command||'').slice(0,60) || '';
        case 'Edit': case 'Write':
          return (i.file_path||'').split('/').slice(-2).join('/');
        case 'Command':
          return `${i.command||''} ${i.args||''}`.trim();
        case 'User':
          return (i.message||'').slice(0, 100);
        default:
          if (props.node.tool?.startsWith('mcp__'))
            return props.node.tool.replace(/^mcp__[^_]+__/, '');
          return '';
      }
    });
    const bodyRows = computed(() => {
      const i = props.node.input || {};
      const rows = [];
      if (props.node.tool === 'Agent') {
        if (i.description) rows.push(['desc', i.description]);
      } else if (props.node.tool === 'SendMessage') {
        if (i.message) rows.push(['msg', i.message.slice(0, 200)]);
      } else if (props.node.tool === 'Bash') {
        if (i.command) rows.push(['cmd', String(i.command).slice(0, 200)]);
      } else if (props.node.tool === 'Command') {
        if (i.args) rows.push(['args', i.args]);
      } else if (props.node.tool === 'User') {
        if (i.message) rows.push(['message', String(i.message)]);
      }
      return rows;
    });
    const formattedResp = computed(() => {
      const r = props.node.response;
      if (!r || r === '') return '';
      if (typeof r === 'object') {
        if (r.stdout || r.stderr) {
          const parts = [];
          if (r.exit_code != null && r.exit_code !== 0) parts.push('exit: ' + r.exit_code);
          if (r.stdout) parts.push(String(r.stdout).slice(0, 500));
          if (r.stderr) parts.push('stderr: ' + String(r.stderr).slice(0, 200));
          return parts.join('\n');
        }
        return JSON.stringify(r, null, 2).slice(0, 600);
      }
      return String(r).slice(0, 600);
    });
    const hasAgentCost = computed(() =>
      props.node.tool === 'Agent' && props.node.status === 'done' &&
      !!(props.node.agentTotalTokens || props.node.agentDurationMs));
    const hasThinking = computed(() => !!props.node.thinking);
    const shortModel = computed(() => {
      const m = props.node.model;
      return m ? m.replace('claude-', '').replace(/-\d{8}$/, '') : '';
    });
    const hasBody = computed(() =>
      bodyRows.value.length > 0 || hasTok.value || !!formattedResp.value ||
      hasAgentCost.value || hasThinking.value);
    const hasResp = computed(() => !!formattedResp.value);
    function toggle() {
      if (hasKids.value) expanded.value = !expanded.value;
    }
    const childGroups = computed(() => {
      const kids = props.node.children || [];
      if (!kids.length) return [];
      const step1 = [];
      let pbatch = [];
      for (const ch of kids) {
        if (ch.parallel) { pbatch.push(ch); }
        else {
          if (pbatch.length) { step1.push({type:'parallel', nodes:pbatch}); pbatch = []; }
          step1.push({type:'single', node:ch});
        }
      }
      if (pbatch.length) step1.push({type:'parallel', nodes:pbatch});
      const groups = [];
      let cmdBatch = [];
      function flush() {
        if (!cmdBatch.length) return;
        if (cmdBatch.length === 1) groups.push({type:'single', nodes:[cmdBatch[0]]});
        else groups.push({type:'cmdgroup', nodes:[...cmdBatch]});
        cmdBatch = [];
      }
      for (const item of step1) {
        if (item.type === 'single' && item.node.tool !== 'Agent') {
          cmdBatch.push(item.node);
        } else {
          flush();
          groups.push(item);
        }
      }
      flush();
      return groups;
    });
    const expandedGroups = ref(new Set());
    function toggleGroup(gid) {
      if (expandedGroups.value.has(gid)) expandedGroups.value.delete(gid);
      else expandedGroups.value.add(gid);
    }
    function cmdGroupSummary(nodes) {
      const counts = {};
      for (const n of nodes) counts[n.tool] = (counts[n.tool]||0) + 1;
      return Object.entries(counts).map(([t,c]) => t + (c>1?' ×'+c:'')).join(', ');
    }
    return { expanded, respOpen, thinkOpen, hasKids, isParallel, tok, totalIn, totalOut, hasTok,
             toolLower, label, bodyRows, hasBody, hasResp, formattedResp, toggle, fmtK, fmtT,
             childGroups, expandedGroups, toggleGroup, cmdGroupSummary,
             hasAgentCost, hasThinking, shortModel };
  },
  template: `
    <div class="cn" :class="['cn--'+toolLower, 'cn--'+node.status]">
      <div class="cn__card">
        <div class="cn__header" @click="toggle">
          <span class="cn__tag" :class="'cn__tag--'+toolLower">{{ node.tool }}</span>
          <span class="cn__label" :class="label ? 'cn__label--bright' : ''" :title="label">{{ label || '—' }}</span>
          <span v-if="shortModel"
                style="font-size:8px;background:rgba(255,255,255,.12);border-radius:999px;
                       padding:1px 6px;font-family:monospace;opacity:.75;white-space:nowrap;
                       overflow:hidden;text-overflow:ellipsis;max-width:100px">{{ shortModel }}</span>
          <span v-if="hasTok" class="cn__tokens">
            [<span>↑{{ fmtK(totalIn) }}</span>|<span style="color:#4ade80">↓{{ fmtK(totalOut) }}</span>]
          </span>
          <span v-if="node.status==='active'"  class="cn__status cn__status--active">⬤ RUN</span>
          <span v-if="node.status==='pending'" class="cn__status cn__status--pending">⏳</span>
          <span v-if="hasKids" class="cn__toggle" @click.stop="toggle">{{ expanded ? '[-]' : '[+]' }}</span>
        </div>
        <div class="cn__body" v-if="hasBody">
          <div class="cn__row" v-for="[k,v] in bodyRows" :key="k">
            <span class="cn__key">{{ k }}:</span>
            <span class="cn__val">{{ v }}</span>
          </div>
          <div class="cn__tok-row" v-if="hasTok">
            <span class="lbl">tok:</span>
            <span class="tok-pill tok-pill--in"  v-if="tok.input">↑ {{ fmtK(tok.input) }}</span>
            <span class="tok-pill tok-pill--out" v-if="tok.output">↓ {{ fmtK(tok.output) }}</span>
            <span class="tok-pill tok-pill--cr"  v-if="tok.cache_read">↩ {{ fmtK(tok.cache_read) }}</span>
            <span class="tok-pill tok-pill--cc"  v-if="tok.cache_create || tok.cache_write">☁ {{ fmtK(tok.cache_create || tok.cache_write) }}</span>
            <span v-if="tok.duration_ms" style="font-size:8px;opacity:.5;font-family:monospace">{{ tok.duration_ms }}ms</span>
          </div>
          <div class="cn__tok-row" v-if="hasAgentCost">
            <span class="lbl">agent:</span>
            <span class="tok-pill tok-pill--in"  v-if="node.agentTotalTokens">{{ fmtK(node.agentTotalTokens) }} tok</span>
            <span class="tok-pill tok-pill--out" v-if="node.agentDurationMs">{{ (node.agentDurationMs/1000).toFixed(1) }}s</span>
            <span class="tok-pill tok-pill--cc"  v-if="node.agentToolCount">{{ node.agentToolCount }} calls</span>
          </div>
          <div v-if="hasThinking" style="margin-top:2px">
            <button class="cn__resp-toggle" @click="thinkOpen=!thinkOpen">
              {{ thinkOpen ? '▼ thinking' : '▶ thinking' }}
            </button>
            <pre v-if="thinkOpen" class="cn__resp" style="font-style:italic;opacity:.75">{{ String(node.thinking).slice(0, 1000) }}</pre>
          </div>
          <div v-if="hasResp" style="margin-top:2px">
            <button class="cn__resp-toggle" @click="respOpen=!respOpen">
              {{ respOpen ? '▼ response' : '▶ response' }}
            </button>
            <pre v-if="respOpen" class="cn__resp">{{ formattedResp }}</pre>
          </div>
        </div>
      </div>
      <transition name="slide">
        <div class="cn__children" v-if="expanded && hasKids">
          <template v-for="(g, gi) in childGroups" :key="gi">
            <div v-if="g.type==='parallel'" class="cn">
              <div class="cn__parallel">
                <div class="cn__parallel-hdr">∥ {{ g.nodes.length }} parallel</div>
                <div class="cn__parallel-cols">
                  <div class="cn__parallel-col" v-for="child in g.nodes" :key="child.id">
                    <cyber-node :node="child" :token-index="tokenIndex" :depth="depth+1" />
                  </div>
                </div>
              </div>
            </div>
            <div v-else-if="g.type==='cmdgroup'" class="cn cn--cmdgroup">
              <div class="cn__card cn__card--cmdgroup" @click="toggleGroup(g.nodes[0].id)">
                <div class="cn__header">
                  <span class="cn__tag cn__tag--cmdgroup">⚙ {{ g.nodes.length }} cmds</span>
                  <span class="cn__label" style="opacity:.6">{{ cmdGroupSummary(g.nodes) }}</span>
                  <span class="cn__toggle">{{ expandedGroups.has(g.nodes[0].id) ? '[-]' : '[+]' }}</span>
                </div>
              </div>
              <div class="cn__children" v-if="expandedGroups.has(g.nodes[0].id)">
                <cyber-node v-for="child in g.nodes" :key="child.id"
                            :node="child" :token-index="tokenIndex" :depth="depth+1" />
              </div>
            </div>
            <cyber-node v-else v-for="child in g.nodes" :key="child.id"
                        :node="child" :token-index="tokenIndex" :depth="depth+1" />
          </template>
        </div>
      </transition>
    </div>
  `
};
CyberNode.components = { 'cyber-node': CyberNode };

const app = createApp({
  components: { 'cyber-node': CyberNode },
  setup() {
    const sessions     = ref([]);
    const activeSession = ref(null);
    const entries      = ref([]);
    const stats        = ref(null);
    const liveConnected = ref(false);
    const treeWrap     = ref(null);
    const tree       = computed(() => entries.value.length ? buildTree(entries.value) : null);
    const tokenIndex = computed(() => buildTokenIndex(entries.value, stats.value?.timeline || []));
    const topTools   = computed(() => Object.entries(stats.value?.tools||{}).sort((a,b)=>b[1]-a[1]).slice(0,6));
    const collapsedProjects = ref({});
    const promptOpen = ref(false);
    const diagramOpen      = ref(false);
    const diagramMd        = ref(null);
    const diagramSvg       = ref(null);
    const diagramLoading   = ref(false);
    const diagramTruncated = ref(false);
    const projectGroups = computed(() => {
      const map = {};
      for (const s of sessions.value) {
        const p = s.project || '';
        if (!map[p]) map[p] = [];
        map[p].push(s);
      }
      const ap = sessions.value.find(s => s.session_id === activeSession.value)?.project || '';
      return Object.entries(map)
        .sort(([a],[b]) => { if (a===ap) return -1; if (b===ap) return 1; return a.localeCompare(b); })
        .map(([project, sessions]) => ({project, sessions}));
    });
    function toggleProject(name) {
      const c = {...collapsedProjects.value};
      if (c[name]) delete c[name]; else c[name] = true;
      collapsedProjects.value = c;
    }
    let globalES = null, entryES = null;
    async function loadSessions() {
      try { sessions.value = await fetch('/api/sessions').then(r=>r.json()); }
      catch(e) { console.error(e); }
    }
    async function selectSession(id) {
      if (id === activeSession.value) return;
      entryES?.close();
      activeSession.value = id;
      entries.value = [];
      stats.value = null;
      promptOpen.value = false;
      diagramMd.value = null;
      diagramSvg.value = null;
      diagramTruncated.value = false;
      try {
        const d = await fetch(`/api/sessions/${id}`).then(r=>r.json());
        entries.value = d.entries || [];
      } catch(e) { console.error(e); }
      loadStats(id);
      connectEntryStream(id);
    }
    async function loadStats(id) {
      try {
        const s = await fetch(`/api/sessions/${id}/stats`).then(r=>r.json());
        if (id === activeSession.value) stats.value = s;
      } catch(e) {}
    }
    async function toggleDiagram() {
      diagramOpen.value = !diagramOpen.value;
      if (diagramOpen.value && !diagramSvg.value) await loadDiagram();
    }
    async function loadDiagram() {
      if (!activeSession.value || diagramLoading.value) return;
      diagramLoading.value = true;
      try {
        const d = await fetch(`/api/sessions/${activeSession.value}/diagram`).then(r=>r.json());
        diagramMd.value = d.mermaid;
        diagramTruncated.value = d.truncated || false;
        if (d.mermaid) {
          const { svg } = await mermaid.render('mg-' + Date.now(), d.mermaid);
          diagramSvg.value = svg;
        }
      } catch(e) { console.error('loadDiagram', e); }
      finally { diagramLoading.value = false; }
    }
    function downloadSvg() {
      if (!diagramSvg.value) return;
      const a = Object.assign(document.createElement('a'), {
        href: URL.createObjectURL(new Blob([diagramSvg.value], { type: 'image/svg+xml' })),
        download: `flow-${activeSession.value}.svg`,
      });
      a.click(); URL.revokeObjectURL(a.href);
    }
    function downloadMd() {
      if (!diagramMd.value) return;
      const content = '```mermaid\n' + diagramMd.value + '\n```';
      const a = Object.assign(document.createElement('a'), {
        href: URL.createObjectURL(new Blob([content], { type: 'text/markdown' })),
        download: `flow-${activeSession.value}.md`,
      });
      a.click(); URL.revokeObjectURL(a.href);
    }

    function connectEntryStream(id) {
      entryES = new EventSource(`/api/sessions/${id}/stream`);
      entryES.addEventListener('connected', () => { liveConnected.value = true; });
      entryES.addEventListener('entry', ev => {
        try { entries.value = [...entries.value, JSON.parse(ev.data)]; }
        catch(e) {}
      });
      entryES.addEventListener('ping', () => {});
      entryES.onerror = () => {
        liveConnected.value = false;
        entryES?.close();
        setTimeout(() => { if (activeSession.value === id) connectEntryStream(id); }, 3000);
      };
    }
    function connectGlobalStream() {
      globalES = new EventSource('/api/stream/global');
      globalES.onopen = () => { liveConnected.value = true; };
      globalES.onerror = () => { liveConnected.value = false; };
      globalES.addEventListener('session_new', () => loadSessions());
    }
    function onKey(e) {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'ArrowDown' || e.key === 'j') {
        const items = document.querySelectorAll('.session-item');
        const cur = [...items].findIndex(el => el.classList.contains('active'));
        const next = items[cur + 1];
        if (next) next.click();
      } else if (e.key === 'ArrowUp' || e.key === 'k') {
        const items = document.querySelectorAll('.session-item');
        const cur = [...items].findIndex(el => el.classList.contains('active'));
        const prev = items[cur - 1];
        if (prev) prev.click();
      } else if (e.key === 'Escape') {
        const es = entries.value;
        entries.value = [];
        nextTick(() => { entries.value = es; });
      }
    }
    onMounted(async () => {
      await loadSessions();
      connectGlobalStream();
      if (sessions.value.length) selectSession(sessions.value[0].session_id);
      document.addEventListener('keydown', onKey);
    });
    onUnmounted(() => {
      globalES?.close();
      entryES?.close();
      document.removeEventListener('keydown', onKey);
    });
    return { sessions, activeSession, entries, stats, liveConnected, treeWrap,
             tree, tokenIndex, topTools, projectGroups, collapsedProjects, toggleProject,
             selectSession, promptOpen, fmtK, fmtT,
             diagramOpen, diagramMd, diagramSvg, diagramLoading, diagramTruncated,
             toggleDiagram, loadDiagram, downloadSvg, downloadMd };
  }
});
app.mount('#app');
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def run(log_dir: Path) -> None:
    app = create_app(log_dir)
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["loggers"]["uvicorn.access"]["level"] = "WARNING"

    try:
        uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning", log_config=log_config)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\nERROR: Port {PORT} is already in use.")
            print(f"Set FLOW_SERVER_PORT=<other> to use a different port.\n")
            sys.exit(1)
        raise
