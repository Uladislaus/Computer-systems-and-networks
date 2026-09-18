"""Автономная полноэкранная заставка «бурной разработки» (без участия пользователя)."""
from __future__ import annotations

import random
import tkinter as tk
from tkinter import ttk
from typing import Callable

# Тёмный «мощный» IDE: уголь, бирюза, контраст
BG = "#070B10"
PANEL = "#0E141B"
EDGE = "#1E2A36"
INK = "#D7E0EA"
MUTED = "#6B7C8C"
ACCENT = "#1EC8B0"
GREEN = "#3DDC97"
YELLOW = "#E6B84D"
RED = "#FF5C5C"
BLUE = "#4DA3FF"
ORANGE = "#FF9F43"
CYAN = "#5CE1E6"

FONT_MONO = ("Consolas", 11)
FONT_MONO_SM = ("Consolas", 9)
FONT_MONO_LG = ("Consolas", 12)
FONT_TITLE = ("Segoe UI Semibold", 10)

CODE_POOL = [
    '''from __future__ import annotations
import logging
from pathlib import Path
from django.db import transaction
from .models import GribModel, IngestJob
from .parsers import decode_grib2, filter_northern_sectors

log = logging.getLogger("services.grib")

class EgrrIngestService:
    def __init__(self, root: Path, *, dry_run: bool = False) -> None:
        self.root = root
        self.dry_run = dry_run
        self._queue: list[Path] = []

    def scan(self, pattern: str = "*70_90.*") -> int:
        files = sorted(self.root.glob(pattern))
        self._queue = [p for p in files if p.stat().st_size > 0]
        log.info("queued %s files", len(self._queue))
        return len(self._queue)

    @transaction.atomic
    def run_batch(self, limit: int = 128) -> IngestJob:
        job = IngestJob.objects.create(status="running", source="EGRR")
        for path in self._queue[:limit]:
            for field in filter_northern_sectors(decode_grib2(path)):
                if not self.dry_run:
                    GribModel.objects.update_or_create(
                        cccc=field.cccc, level=field.level, valid_at=field.valid_at,
                        defaults={"payload": field.to_bytes()},
                    )
        job.status = "done"
        job.save(update_fields=["status"])
        return job
''',
    '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.services.spline import CubicSplineInterpolator

app = FastAPI(title="Belhydromet Spline API", version="0.4.0")

class SeriesIn(BaseModel):
    x: list[float] = Field(..., min_length=3)
    y: list[float] = Field(..., min_length=3)
    query: list[float]

@app.post("/v1/interpolate")
def interpolate(body: SeriesIn):
    if len(body.x) != len(body.y):
        raise HTTPException(400, "x/y length mismatch")
    spline = CubicSplineInterpolator(body.x, body.y)
    return {"values": [spline.evaluate(t) for t in body.query], "knots": len(body.x)}
''',
    '''export async function refreshLayer(map, bbox) {
  const url = new URL("/api/meteo/stations", location.origin);
  url.searchParams.set("bbox", `${bbox.west},${bbox.south},${bbox.east},${bbox.north}`);
  const res = await fetch(url, { headers: { Accept: "application/geo+json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const fc = await res.json();
  map.getSource("stations").setData(fc);
  console.info(`[map] ${fc.features.length} stations @ ${performance.now().toFixed(0)}ms`);
}
''',
    '''def cubic_spline_coeffs(x, y):
    n = len(x) - 1
    h = [x[i+1] - x[i] for i in range(n)]
    alpha = [0.0] * (n + 1)
    for i in range(1, n):
        alpha[i] = (3/h[i])*(y[i+1]-y[i]) - (3/h[i-1])*(y[i]-y[i-1])
    l, mu, z = [1.0]+[0.0]*n, [0.0]*(n+1), [0.0]*(n+1)
    for i in range(1, n):
        l[i] = 2*(x[i+1]-x[i-1]) - h[i-1]*mu[i-1]
        mu[i] = h[i]/l[i]
        z[i] = (alpha[i] - h[i-1]*z[i-1]) / l[i]
    c = [0.0]*(n+1); b = [0.0]*n; d = [0.0]*n
    for j in range(n-1, -1, -1):
        c[j] = z[j] - mu[j]*c[j+1]
        b[j] = (y[j+1]-y[j])/h[j] - h[j]*(c[j+1]+2*c[j])/3
        d[j] = (c[j+1]-c[j])/(3*h[j])
    return list(zip(y[:-1], b, c[:-1], d))
''',
]

CMDS = [
    "git status -sb",
    "git diff --stat",
    "python -m pytest tests/ -q --tb=no",
    "ruff check services/ --fix",
    "mypy services/grib --pretty",
    "pip install -U django djangorestframework psycopg[binary]",
    "python manage.py migrate --plan",
    "python manage.py runserver 0.0.0.0:8000",
    "docker compose up -d --build grib-worker",
    "docker compose logs -f grib-worker --tail=30",
    "curl -sS https://mapmakers.ru/ru/News/Details/30670 | head -n 5",
    "npm run build --workspace=web",
    "pytest -k spline -vv",
    "coverage report -m --fail-under=85",
]

CMD_OUT = [
    ("## feature/grib-egrr…origin/feature/grib-egrr [ahead 2]", MUTED),
    (" M services/grib/ingest.py | 48 ++++++++++++++++++++----", YELLOW),
    ("................ [100%]  27 passed in 3.41s", GREEN),
    ("All checks passed!", GREEN),
    ("Success: no issues found in 14 source files", GREEN),
    ("Successfully installed django-5.2.17 psycopg-3.2.4", MUTED),
    ("Planned operations: 3  Apply all migrations: grib, spline, auth", BLUE),
    ("Starting development server at http://0.0.0.0:8000/", GREEN),
    ("Container belgidromet-grib-worker-1  Started", GREEN),
    ("grib-worker | INFO queued 256 files · wrote 1.4k fields", CYAN),
    ("HTTP/2 200  content-type: text/html", BLUE),
    ("✓ 184 modules transformed. built in 2.08s", GREEN),
    ("test_cubic_natural PASSED  test_extrapolate PASSED", GREEN),
    ("TOTAL  2141  187  91%", GREEN),
]

DOWNLOADS = [
    ("GribModels.txt", 1.4),
    ("egrr_sector_70_90.tar", 420.0),
    ("python-3.12.10-amd64.exe", 25.1),
    ("node-v22.14.0-x64.msi", 28.6),
    ("belgidromet-docs.zip", 96.2),
    ("cuda_runtime_cache.bin", 210.0),
]

TREE = [
    ("▼ belgidromet-services/", ACCENT),
    ("  ▼ services/", MUTED),
    ("      grib/ingest.py", INK),
    ("      grib/parsers.py", INK),
    ("      spline/cubic.py", INK),
    ("  ▼ web/src/", MUTED),
    ("      map.ts", INK),
    ("      api.ts", INK),
    ("  ▼ tests/", MUTED),
    ("      test_ingest.py", INK),
    ("  manage.py", MUTED),
    ("  docker-compose.yml", MUTED),
]


class ActivityCover(tk.Toplevel):
    """Полностью автономная заставка: код, терминал, загрузки идут сами."""

    def __init__(self, master: tk.Misc, on_close: Callable[[], None] | None = None) -> None:
        super().__init__(master)
        self._on_close = on_close
        self._alive = True
        self._jobs: list[str] = []
        self.title("belgidromet-services — building")
        self.configure(bg=BG)
        self.attributes("-topmost", True)
        try:
            self.attributes("-fullscreen", True)
        except tk.TclError:
            try:
                self.state("zoomed")
            except tk.TclError:
                self.geometry("1280x800")
        self.protocol("WM_DELETE_WINDOW", self.dismiss)
        # выход только хоткеями — без кнопок и кликов по UI
        self.bind("<Escape>", lambda e: self.dismiss())
        self.bind("<F12>", lambda e: self.dismiss())
        self.bind("<Control-Shift-H>", lambda e: self.dismiss())
        self.bind("<Button-1>", self._ignore)
        self.bind("<Button-3>", self._ignore)

        self._build()
        self.after(60, self._boot_streams)
        self.focus_force()
        self.lift()

    @staticmethod
    def _ignore(event=None):
        return "break"

    def _build(self) -> None:
        top = tk.Frame(self, bg=PANEL, height=32)
        top.pack(fill=tk.X)
        top.pack_propagate(False)
        tk.Label(
            top,
            text="  ●  ●  ●    belgidromet-services  —  ingest.py  —  Debug  —  Tasks running…",
            bg=PANEL,
            fg=MUTED,
            font=FONT_TITLE,
            anchor="w",
        ).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        # намёк только в titlebar, мелко
        tk.Label(top, text="Esc / F12  ", bg=PANEL, fg=EDGE, font=FONT_MONO_SM).pack(side=tk.RIGHT)

        body = tk.Frame(self, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(body, bg=PANEL, width=210)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)
        tk.Label(left, text=" EXPLORER", bg=PANEL, fg=MUTED, font=FONT_MONO_SM, anchor="w").pack(
            fill=tk.X, padx=8, pady=(10, 4)
        )
        self.tree_box = tk.Text(
            left, bg=PANEL, fg=INK, font=FONT_MONO_SM, relief=tk.FLAT, highlightthickness=0,
            borderwidth=0, cursor="arrow", padx=8, pady=4, height=30,
        )
        self.tree_box.pack(fill=tk.BOTH, expand=True)
        for name, color in TREE:
            self.tree_box.insert(tk.END, name + "\n")
        self._lock(self.tree_box)

        mid = tk.Frame(body, bg=BG)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tabs = tk.Frame(mid, bg=PANEL)
        tabs.pack(fill=tk.X)
        self.tab_a = tk.Label(tabs, text="  ingest.py  ", bg=BG, fg=INK, font=FONT_MONO_SM, padx=8, pady=5)
        self.tab_a.pack(side=tk.LEFT)
        self.tab_b = tk.Label(tabs, text="  cubic.py  ", bg=PANEL, fg=MUTED, font=FONT_MONO_SM, padx=8, pady=5)
        self.tab_b.pack(side=tk.LEFT)
        self.tab_c = tk.Label(tabs, text="  PROBLEMS  ", bg=PANEL, fg=YELLOW, font=FONT_MONO_SM, padx=8, pady=5)
        self.tab_c.pack(side=tk.LEFT)

        self.editor = tk.Text(
            mid, bg=BG, fg=INK, insertbackground=ACCENT, relief=tk.FLAT, font=FONT_MONO_LG,
            wrap=tk.NONE, padx=16, pady=12, highlightthickness=0, borderwidth=0, cursor="arrow",
        )
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.editor.tag_configure("kw", foreground=BLUE)
        self.editor.tag_configure("ok", foreground=GREEN)
        self.editor.tag_configure("cmt", foreground=MUTED)
        self.editor.tag_configure("hot", foreground=ACCENT)

        # нижняя зона: терминал + лог сборки рядом
        bottom = tk.Frame(mid, bg=EDGE, height=230)
        bottom.pack(fill=tk.X)
        bottom.pack_propagate(False)
        bottom.columnconfigure(0, weight=3)
        bottom.columnconfigure(1, weight=2)

        term_f = tk.Frame(bottom, bg="#05080C")
        term_f.grid(row=0, column=0, sticky="nsew")
        tk.Label(
            term_f, text=" TERMINAL  ·  pwsh  ·  parallel jobs: 4", bg="#05080C", fg=MUTED,
            font=FONT_MONO_SM, anchor="w",
        ).pack(fill=tk.X, padx=8, pady=3)
        self.term = tk.Text(
            term_f, bg="#05080C", fg=INK, relief=tk.FLAT, font=FONT_MONO_SM, height=11,
            highlightthickness=0, borderwidth=0, padx=10, pady=2, cursor="arrow",
        )
        self.term.pack(fill=tk.BOTH, expand=True)
        for tag, col in (("p", GREEN), ("c", INK), ("o", MUTED), ("ok", GREEN), ("info", BLUE), ("warn", YELLOW), ("err", RED)):
            self.term.tag_configure(tag, foreground=col)

        log_f = tk.Frame(bottom, bg="#080C12")
        log_f.grid(row=0, column=1, sticky="nsew")
        tk.Label(
            log_f, text=" OUTPUT  ·  Build / Index / Network", bg="#080C12", fg=MUTED,
            font=FONT_MONO_SM, anchor="w",
        ).pack(fill=tk.X, padx=8, pady=3)
        self.log = tk.Text(
            log_f, bg="#080C12", fg=CYAN, relief=tk.FLAT, font=FONT_MONO_SM, height=11,
            highlightthickness=0, borderwidth=0, padx=8, pady=2, cursor="arrow",
        )
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.tag_configure("info", foreground=CYAN)
        self.log.tag_configure("ok", foreground=GREEN)
        self.log.tag_configure("warn", foreground=YELLOW)

        right = tk.Frame(body, bg=PANEL, width=280)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)
        tk.Label(right, text=" DOWNLOADS / CACHE", bg=PANEL, fg=MUTED, font=FONT_MONO_SM, anchor="w").pack(
            fill=tk.X, padx=10, pady=(12, 6)
        )
        self.dl_vars: list[tk.DoubleVar] = []
        self.dl_labels: list[tk.Label] = []
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Hot.Horizontal.TProgressbar",
            troughcolor="#15202B", background=ACCENT, bordercolor=EDGE,
            lightcolor=ACCENT, darkcolor=ACCENT, thickness=10,
        )
        for name, _mb in DOWNLOADS:
            tk.Label(right, text=name, bg=PANEL, fg=INK, font=FONT_MONO_SM, anchor="w").pack(fill=tk.X, padx=12)
            var = tk.DoubleVar(value=random.uniform(0, 20))
            self.dl_vars.append(var)
            ttk.Progressbar(right, variable=var, maximum=100, length=240, style="Hot.Horizontal.TProgressbar").pack(
                padx=12, pady=(2, 0), anchor="w"
            )
            lab = tk.Label(right, text="", bg=PANEL, fg=MUTED, font=FONT_MONO_SM, anchor="w")
            lab.pack(fill=tk.X, padx=12, pady=(0, 8))
            self.dl_labels.append(lab)

        tk.Label(right, text=" LIVE METRICS", bg=PANEL, fg=MUTED, font=FONT_MONO_SM, anchor="w").pack(
            fill=tk.X, padx=10, pady=(6, 4)
        )
        self.cpu = tk.Label(right, text="CPU   ███░░░░░░  34%", bg=PANEL, fg=GREEN, font=FONT_MONO, anchor="w")
        self.cpu.pack(fill=tk.X, padx=12)
        self.ram = tk.Label(right, text="RAM   12.1 / 32 GB", bg=PANEL, fg=BLUE, font=FONT_MONO, anchor="w")
        self.ram.pack(fill=tk.X, padx=12)
        self.disk = tk.Label(right, text="DISK  ▓▓░░░░  write 180 MB/s", bg=PANEL, fg=YELLOW, font=FONT_MONO_SM, anchor="w")
        self.disk.pack(fill=tk.X, padx=12)
        self.net = tk.Label(right, text="NET   ↓ 8.4 MB/s  ↑ 220 KB/s", bg=PANEL, fg=ORANGE, font=FONT_MONO_SM, anchor="w")
        self.net.pack(fill=tk.X, padx=12, pady=(0, 8))
        self.tasks = tk.Label(
            right, text="TASKS  compile · test · sync · index", bg=PANEL, fg=ACCENT, font=FONT_MONO_SM, anchor="w"
        )
        self.tasks.pack(fill=tk.X, padx=12)

        status = tk.Frame(self, bg="#03060A", height=24)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)
        self.status = tk.Label(
            status, text="  Ln 1, Col 1  ·  Python  ·  UTF-8  ·  main*  ·  4 tasks running",
            bg="#03060A", fg=MUTED, font=FONT_MONO_SM, anchor="w",
        )
        self.status.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(status, text="0 errors  ·  2 warnings  ·  Watch  ", bg="#03060A", fg=EDGE, font=FONT_MONO_SM).pack(
            side=tk.RIGHT
        )

        for w in (self.editor, self.term, self.log, self.tree_box):
            w.bind("<Key>", self._ignore)
            w.bind("<Button-1>", self._ignore)
            w.bind("<B1-Motion>", self._ignore)

    def _lock(self, widget: tk.Text) -> None:
        widget.configure(state=tk.DISABLED)

    def _write(self, widget: tk.Text, text: str, tag: str | None = None) -> None:
        widget.configure(state=tk.NORMAL)
        if tag:
            widget.insert(tk.END, text, tag)
        else:
            widget.insert(tk.END, text)
        # ограничение длины лога
        if int(float(widget.index("end-1c").split(".")[0])) > 400:
            widget.delete("1.0", "80.0")
        widget.see(tk.END)
        widget.configure(state=tk.DISABLED)

    def _schedule(self, ms: int, fn: Callable[[], None]) -> None:
        if not self._alive:
            return
        self._jobs.append(self.after(ms, fn))

    def _boot_streams(self) -> None:
        self._code = random.choice(CODE_POOL)
        self._ci = 0
        self._cmd_i = 0
        self._typing_cmd = False
        self._type_code()
        self._run_terminal()
        self._run_downloads()
        self._run_metrics()
        self._run_build_log()
        self._pulse_tabs()

    def _type_code(self) -> None:
        if not self._alive:
            return
        if self._ci >= len(self._code):
            self._schedule(900, self._next_file)
            return
        # пачками — «быстрый набор»
        n = random.randint(2, 7)
        chunk = self._code[self._ci : self._ci + n]
        self._ci += len(chunk)
        tag = None
        stripped = chunk.lstrip()
        if stripped.startswith("#") or stripped.startswith('"""'):
            tag = "cmt"
        elif any(k in chunk for k in ("def ", "class ", "import ", "return ", "async ", "await ")):
            tag = "kw"
        elif "log." in chunk or "INFO" in chunk:
            tag = "hot"
        self._write(self.editor, chunk, tag)
        line = int(float(self.editor.index("end-1c").split(".")[0]))
        self.status.configure(
            text=f"  Ln {line}, Col {random.randint(1, 48)}  ·  Python  ·  UTF-8  ·  main*  ·  4 tasks running"
        )
        delay = random.randint(6, 22)
        if chunk.endswith("\n") and random.random() < 0.08:
            delay += random.randint(120, 280)
        self._schedule(delay, self._type_code)

    def _next_file(self) -> None:
        if not self._alive:
            return
        self.editor.configure(state=tk.NORMAL)
        self.editor.delete("1.0", tk.END)
        self.editor.configure(state=tk.DISABLED)
        self._code = random.choice(CODE_POOL)
        self._ci = 0
        name = random.choice(["ingest.py", "cubic.py", "map.ts", "api.py", "parsers.py", "test_ingest.py"])
        self.tab_a.configure(text=f"  {name}  ", bg=BG, fg=INK)
        self._type_code()

    def _run_terminal(self) -> None:
        if not self._alive or self._typing_cmd:
            return
        cmd = CMDS[self._cmd_i % len(CMDS)]
        self._cmd_i += 1
        self._typing_cmd = True
        self._write(self.term, "$ ", "p")
        self._type_cmd(cmd, 0)

    def _type_cmd(self, cmd: str, i: int) -> None:
        if not self._alive:
            return
        if i >= len(cmd):
            self._write(self.term, "\n")
            out, col = CMD_OUT[self._cmd_i % len(CMD_OUT)]
            tag = "ok" if col == GREEN else ("info" if col in (BLUE, CYAN) else ("warn" if col == YELLOW else "o"))
            self._schedule(180, lambda: self._emit_out(out, tag))
            return
        self._write(self.term, cmd[i], "c")
        self._schedule(random.randint(4, 16), lambda: self._type_cmd(cmd, i + 1))

    def _emit_out(self, out: str, tag: str) -> None:
        if not self._alive:
            return
        self._write(self.term, out + "\n", tag)
        # иногда вторая строка вывода
        if random.random() < 0.45:
            extra = random.choice(
                [
                    ("done in 0.84s", "ok"),
                    ("cache hit 92%", "info"),
                    ("watching for file changes…", "o"),
                    ("worker heartbeat ok", "ok"),
                ]
            )
            self._write(self.term, extra[0] + "\n", extra[1])
        self._typing_cmd = False
        self._schedule(random.randint(350, 900), self._run_terminal)

    def _run_downloads(self) -> None:
        if not self._alive:
            return
        for i, var in enumerate(self.dl_vars):
            bump = random.uniform(0.8, 4.5)
            val = var.get() + bump
            if val >= 100:
                val = random.uniform(0, 8)
            var.set(val)
            total = DOWNLOADS[i][1]
            speed = random.uniform(2.0, 28.0)
            self.dl_labels[i].configure(
                text=f"{val:5.1f}%  ·  {total * val / 100:6.1f}/{total:.0f} MB  ·  {speed:.1f} MB/s"
            )
        self._schedule(220, self._run_downloads)

    def _bar(self, pct: int, width: int = 10) -> str:
        filled = max(0, min(width, int(width * pct / 100)))
        return "█" * filled + "░" * (width - filled)

    def _run_metrics(self) -> None:
        if not self._alive:
            return
        cpu = random.randint(55, 97)
        ram = random.uniform(14.0, 29.5)
        disk = random.randint(40, 100)
        down = random.uniform(3.0, 22.0)
        up = random.uniform(80, 900)
        self.cpu.configure(
            text=f"CPU   {self._bar(cpu)}  {cpu}%",
            fg=RED if cpu > 88 else (YELLOW if cpu > 70 else GREEN),
        )
        self.ram.configure(text=f"RAM   {ram:.1f} / 32 GB")
        self.disk.configure(text=f"DISK  {self._bar(disk, 8)}  write {random.randint(90, 320)} MB/s")
        self.net.configure(text=f"NET   ↓ {down:.1f} MB/s  ↑ {up:.0f} KB/s")
        self.tasks.configure(
            text="TASKS  " + " · ".join(random.sample(
                ["compile", "test", "sync", "index", "lint", "docker", "fetch"], k=4
            ))
        )
        self._schedule(480, self._run_metrics)

    def _run_build_log(self) -> None:
        if not self._alive:
            return
        lines = [
            ("[index] updating symbols… 1842/2100", "info"),
            ("[webpack] compiled successfully in 1184 ms", "ok"),
            ("[django] Watching for file changes with StatReloader", "info"),
            ("[grib] decoded EGRR 0.5° · 64 fields · 850/500/200", "ok"),
            ("[pytest] session starts · platform win32", "info"),
            ("[ruff] All checks passed!", "ok"),
            ("[docker] grib-worker healthy", "ok"),
            ("[git] pushing object 12/12 (2.4 MiB/s)", "info"),
            ("[npm] cached 842 packages", "info"),
            ("[warn] disk util high on C: — still OK", "warn"),
            ("[spline] cubic coeffs n=128 · RMSE=1.2e-6", "ok"),
            ("[net] GET /api/stations 200  42ms", "info"),
        ]
        msg, tag = random.choice(lines)
        self._write(self.log, f"{msg}\n", tag)
        self._schedule(random.randint(280, 700), self._run_build_log)

    def _pulse_tabs(self) -> None:
        if not self._alive:
            return
        # имитация переключения вкладок без участия пользователя
        if random.random() < 0.35:
            active = random.choice(
                [
                    ("ingest.py", self.tab_a),
                    ("cubic.py", self.tab_b),
                    ("PROBLEMS", self.tab_c),
                ]
            )
            for lab in (self.tab_a, self.tab_b, self.tab_c):
                lab.configure(bg=PANEL, fg=MUTED)
            active[1].configure(bg=BG, fg=INK if active[0] != "PROBLEMS" else YELLOW)
        self._schedule(1600, self._pulse_tabs)

    def dismiss(self) -> None:
        if not self._alive:
            return
        self._alive = False
        for jid in self._jobs:
            try:
                self.after_cancel(jid)
            except tk.TclError:
                pass
        self._jobs.clear()
        try:
            self.destroy()
        except tk.TclError:
            pass
        if self._on_close:
            self._on_close()


def open_activity_cover(master: tk.Misc) -> ActivityCover:
    def restore() -> None:
        try:
            master.deiconify()
            master.lift()
            master.focus_force()
        except tk.TclError:
            pass

    try:
        master.withdraw()
    except tk.TclError:
        pass
    return ActivityCover(master, on_close=restore)
