"""Полноэкранная «живая» заставка активной разработки (быстрое сокрытие)."""
from __future__ import annotations

import random
import tkinter as tk
from typing import Callable

# Тёмный IDE-стиль (уголь + бирюза DocFactory, без purple)
BG = "#0D1117"
PANEL = "#161B22"
EDGE = "#30363D"
INK = "#E6EDF3"
MUTED = "#8B949E"
ACCENT = "#2DD4BF"
GREEN = "#3FB950"
YELLOW = "#D29922"
RED = "#F85149"
BLUE = "#58A6FF"
ORANGE = "#DB6D28"
PURPLE_OK = "#A5D6FF"  # холодный, не «AI purple»

FONT_UI = ("Segoe UI", 10)
FONT_MONO = ("Consolas", 11)
FONT_MONO_SM = ("Consolas", 9)
FONT_TITLE = ("Segoe UI Semibold", 11)

CODE_SNIPPETS = [
    '''"""Синхронизация GRIB-потока EGRR → Grib.cdb."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from django.db import transaction

from .models import GribModel, IngestJob
from .parsers import decode_grib2, filter_northern_sectors

log = logging.getLogger("services.grib")


class EgrrIngestService:
    """Приём и запись полей Met Office (0.5°) с фильтрами секторов."""

    def __init__(self, root: Path, *, dry_run: bool = False) -> None:
        self.root = root
        self.dry_run = dry_run
        self._queue: list[Path] = []

    def scan(self, pattern: str = "*70_90.*") -> int:
        files = sorted(self.root.glob(pattern))
        self._queue = [p for p in files if p.stat().st_size > 0]
        log.info("queued %s files from %s", len(self._queue), self.root)
        return len(self._queue)

    @transaction.atomic
    def run_batch(self, limit: int = 64) -> IngestJob:
        job = IngestJob.objects.create(status="running", source="EGRR")
        processed = 0
        for path in self._queue[:limit]:
            fields = decode_grib2(path)
            for field in filter_northern_sectors(fields):
                if self.dry_run:
                    continue
                GribModel.objects.update_or_create(
                    cccc=field.cccc,
                    level=field.level,
                    valid_at=field.valid_at,
                    defaults={"payload": field.to_bytes()},
                )
            processed += 1
            log.debug("ok %s (%s fields)", path.name, len(fields))
        job.status = "done"
        job.processed = processed
        job.save(update_fields=["status", "processed"])
        return job


def bootstrap(paths: Iterable[Path]) -> None:
    for p in paths:
        svc = EgrrIngestService(p)
        if svc.scan():
            svc.run_batch()
''',
    '''from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.services.spline import CubicSplineInterpolator

app = FastAPI(title="Belhydromet Spline API", version="0.3.1")


class SeriesIn(BaseModel):
    x: list[float] = Field(..., min_length=3)
    y: list[float] = Field(..., min_length=3)
    query: list[float]


@app.post("/v1/interpolate")
def interpolate(body: SeriesIn, db: Session = Depends(get_session)):
    if len(body.x) != len(body.y):
        raise HTTPException(400, "x/y length mismatch")
    spline = CubicSplineInterpolator(body.x, body.y)
    values = [spline.evaluate(t) for t in body.query]
    db.add(spline.to_audit_row())
    db.commit()
    return {"values": values, "knots": len(body.x)}
''',
    '''async function loadStations(bbox) {
  const url = new URL("/api/meteo/stations", window.location.origin);
  url.searchParams.set("west", bbox.west);
  url.searchParams.set("east", bbox.east);
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.features.map((f) => ({
    id: f.properties.id,
    name: f.properties.name,
    lat: f.geometry.coordinates[1],
    lon: f.geometry.coordinates[0],
  }));
}

export async function refreshMap(layer, bbox) {
  const stations = await loadStations(bbox);
  layer.clearLayers();
  for (const s of stations) {
    L.circleMarker([s.lat, s.lon], { radius: 4, color: "#2DD4BF" })
      .bindPopup(s.name)
      .addTo(layer);
  }
  console.log(`[map] rendered ${stations.length} stations`);
}
''',
]

TERMINAL_LINES = [
    ("$ ", "git status -sb", GREEN),
    ("", "## feature/grib-egrr-0.5...origin/feature/grib-egrr-0.5", MUTED),
    ("", " M services/grib/ingest.py", YELLOW),
    ("", "?? notebooks/spline_qc.ipynb", MUTED),
    ("$ ", "python -m pytest tests/test_ingest.py -q", GREEN),
    ("", "................ [100%]", MUTED),
    ("", "14 passed in 2.83s", GREEN),
    ("$ ", "pip install -U django djangorestframework --quiet", GREEN),
    ("", "Successfully installed django-5.2.17 djangorestframework-3.15.2", MUTED),
    ("$ ", "python manage.py migrate --check", GREEN),
    ("", "System check identified no issues (0 silenced).", MUTED),
    ("$ ", "curl -I https://mapmakers.ru/ru/News/Details/30670", GREEN),
    ("", "HTTP/1.1 200 OK", BLUE),
    ("$ ", "docker compose logs -f grib-worker --tail=20", GREEN),
    ("", "grib-worker-1  | INFO queued 128 files from /data/egrr", MUTED),
    ("$ ", "ruff check services/ --fix", GREEN),
    ("", "Found 0 errors (2 fixed, 0 remaining).", GREEN),
    ("$ ", "npm run build --workspace=web", GREEN),
    ("", "vite v5.4.2 building for production...", MUTED),
    ("", "✓ built in 1.92s", GREEN),
]

DOWNLOADS = [
    ("GribModels.txt", 1.2),
    ("python-3.12.10-amd64.exe", 24.8),
    ("node-v22.14.0-x64.msi", 28.1),
    ("belgidromet-docs.zip", 86.4),
    ("pgadmin4-9.1-x64.exe", 142.0),
]

FILES_TREE = [
    ("▼ services/", ACCENT),
    ("    grib/", MUTED),
    ("      ingest.py", INK),
    ("      parsers.py", INK),
    ("    spline/", MUTED),
    ("      cubic.py", INK),
    ("▼ web/", ACCENT),
    ("    src/map.ts", INK),
    ("▼ tests/", ACCENT),
    ("    test_ingest.py", INK),
    ("  manage.py", MUTED),
    ("  pyproject.toml", MUTED),
]


class ActivityCover(tk.Toplevel):
    """Полноэкранный интерактивный экран «идёт разработка»."""

    def __init__(self, master: tk.Misc, on_close: Callable[[], None] | None = None) -> None:
        super().__init__(master)
        self._on_close = on_close
        self._alive = True
        self._jobs: list[str] = []
        self.title("Code — belgidromet-services")
        self.configure(bg=BG)
        self.attributes("-topmost", True)
        try:
            self.state("zoomed")
        except tk.TclError:
            self.attributes("-fullscreen", True)
        self.protocol("WM_DELETE_WINDOW", self.dismiss)
        self.bind("<Escape>", lambda e: self.dismiss())
        self.bind("<F12>", lambda e: self.dismiss())
        self.bind("<Control-Shift-H>", lambda e: self.dismiss())

        self._build()
        self.after(80, self._start_animations)
        self.focus_force()
        self.lift()

    def _build(self) -> None:
        # title bar
        top = tk.Frame(self, bg=PANEL, height=36)
        top.pack(fill=tk.X)
        top.pack_propagate(False)
        tk.Label(
            top,
            text="  ● ● ●   belgidromet-services — ingest.py — Visual Studio Code",
            bg=PANEL,
            fg=MUTED,
            font=FONT_TITLE,
            anchor="w",
        ).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        tk.Label(top, text="F12 / Esc — вернуться  ", bg=PANEL, fg=EDGE, font=FONT_MONO_SM).pack(
            side=tk.RIGHT
        )

        body = tk.Frame(self, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        # left tree
        left = tk.Frame(body, bg=PANEL, width=200)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)
        tk.Label(left, text=" EXPLORER", bg=PANEL, fg=MUTED, font=FONT_MONO_SM, anchor="w").pack(
            fill=tk.X, padx=8, pady=(10, 4)
        )
        for name, color in FILES_TREE:
            tk.Label(left, text=name, bg=PANEL, fg=color, font=FONT_MONO_SM, anchor="w").pack(
                fill=tk.X, padx=10
            )

        mid = tk.Frame(body, bg=BG)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # editor
        ed_head = tk.Frame(mid, bg=PANEL)
        ed_head.pack(fill=tk.X)
        self.tab_label = tk.Label(
            ed_head, text="  ingest.py  ×", bg=BG, fg=INK, font=FONT_MONO_SM, padx=10, pady=6
        )
        self.tab_label.pack(side=tk.LEFT)
        tk.Label(ed_head, text="  map.ts", bg=PANEL, fg=MUTED, font=FONT_MONO_SM, padx=10).pack(
            side=tk.LEFT
        )

        self.editor = tk.Text(
            mid,
            bg=BG,
            fg=INK,
            insertbackground=ACCENT,
            relief=tk.FLAT,
            font=FONT_MONO,
            wrap=tk.NONE,
            padx=14,
            pady=10,
            highlightthickness=0,
            borderwidth=0,
        )
        self.editor.pack(fill=tk.BOTH, expand=True)
        self.editor.tag_configure("kw", foreground=BLUE)
        self.editor.tag_configure("str", foreground=ORANGE)
        self.editor.tag_configure("cmt", foreground=MUTED)
        self.editor.tag_configure("fn", foreground=YELLOW)
        self.editor.tag_configure("ok", foreground=GREEN)

        # terminal
        term_wrap = tk.Frame(mid, bg=PANEL, height=200)
        term_wrap.pack(fill=tk.X)
        term_wrap.pack_propagate(False)
        tk.Label(
            term_wrap, text=" TERMINAL  ·  powershell  ·  belgidromet-services", bg=PANEL, fg=MUTED, font=FONT_MONO_SM, anchor="w"
        ).pack(fill=tk.X, padx=8, pady=4)
        self.term = tk.Text(
            term_wrap,
            bg="#010409",
            fg=INK,
            relief=tk.FLAT,
            font=FONT_MONO_SM,
            height=9,
            highlightthickness=0,
            borderwidth=0,
            padx=10,
            pady=4,
        )
        self.term.pack(fill=tk.BOTH, expand=True)
        self.term.tag_configure("prompt", foreground=GREEN)
        self.term.tag_configure("cmd", foreground=INK)
        self.term.tag_configure("out", foreground=MUTED)
        self.term.tag_configure("ok", foreground=GREEN)
        self.term.tag_configure("info", foreground=BLUE)
        self.term.tag_configure("warn", foreground=YELLOW)

        # right: downloads + metrics
        right = tk.Frame(body, bg=PANEL, width=260)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)
        tk.Label(right, text=" DOWNLOADS", bg=PANEL, fg=MUTED, font=FONT_MONO_SM, anchor="w").pack(
            fill=tk.X, padx=10, pady=(12, 6)
        )
        self.dl_vars: list[tk.DoubleVar] = []
        self.dl_labels: list[tk.Label] = []
        for name, _mb in DOWNLOADS:
            tk.Label(right, text=name, bg=PANEL, fg=INK, font=FONT_MONO_SM, anchor="w").pack(
                fill=tk.X, padx=12
            )
            var = tk.DoubleVar(value=0.0)
            self.dl_vars.append(var)
            bar = ttk.Progressbar(right, variable=var, maximum=100, length=220)
            bar.pack(padx=12, pady=(2, 2), anchor="w")
            lab = tk.Label(right, text="0%", bg=PANEL, fg=MUTED, font=FONT_MONO_SM, anchor="w")
            lab.pack(fill=tk.X, padx=12, pady=(0, 8))
            self.dl_labels.append(lab)

        tk.Label(right, text=" SYSTEM", bg=PANEL, fg=MUTED, font=FONT_MONO_SM, anchor="w").pack(
            fill=tk.X, padx=10, pady=(8, 4)
        )
        self.cpu_lbl = tk.Label(right, text="CPU  42%", bg=PANEL, fg=GREEN, font=FONT_MONO, anchor="w")
        self.cpu_lbl.pack(fill=tk.X, padx=12)
        self.ram_lbl = tk.Label(right, text="RAM  11.4 / 32 GB", bg=PANEL, fg=BLUE, font=FONT_MONO, anchor="w")
        self.ram_lbl.pack(fill=tk.X, padx=12)
        self.net_lbl = tk.Label(right, text="NET  ↓ 4.2 MB/s  ↑ 180 KB/s", bg=PANEL, fg=YELLOW, font=FONT_MONO_SM, anchor="w")
        self.net_lbl.pack(fill=tk.X, padx=12, pady=(0, 8))
        self.git_lbl = tk.Label(
            right, text="git · 3 files · ahead 1", bg=PANEL, fg=ACCENT, font=FONT_MONO_SM, anchor="w"
        )
        self.git_lbl.pack(fill=tk.X, padx=12)

        # status bar
        status = tk.Frame(self, bg="#010409", height=26)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)
        self.status_lbl = tk.Label(
            status,
            text="  Ln 1, Col 1  ·  Python  ·  UTF-8  ·  main*  ·  indexing…",
            bg="#010409",
            fg=MUTED,
            font=FONT_MONO_SM,
            anchor="w",
        )
        self.status_lbl.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(status, text="Problems 0  ·  Output  ·  Debug Console  ", bg="#010409", fg=EDGE, font=FONT_MONO_SM).pack(
            side=tk.RIGHT
        )

        # style progressbars
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "TProgressbar",
            troughcolor="#21262D",
            background=ACCENT,
            bordercolor=EDGE,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
            thickness=8,
        )

    def _start_animations(self) -> None:
        self._code_i = 0
        self._snippet = random.choice(CODE_SNIPPETS)
        self._term_i = 0
        self._dl_progress = [random.uniform(5, 35) for _ in DOWNLOADS]
        self._type_code()
        self._tick_terminal()
        self._tick_downloads()
        self._tick_metrics()
        self._blink_cursor()

    def _schedule(self, ms: int, fn: Callable[[], None]) -> None:
        if not self._alive:
            return
        jid = self.after(ms, fn)
        self._jobs.append(jid)

    def _type_code(self) -> None:
        if not self._alive:
            return
        if self._code_i >= len(self._snippet):
            # пауза и новый сниппет
            self._schedule(1800, self._reset_code)
            return
        chunk = self._snippet[self._code_i : self._code_i + random.randint(1, 4)]
        self._code_i += len(chunk)
        self.editor.insert(tk.END, chunk)
        self.editor.see(tk.END)
        # лёгкая «подсветка» строк-комментариев
        if chunk.strip().startswith("#") or '"""' in chunk:
            pass
        line = int(float(self.editor.index("insert").split(".")[0]))
        col = int(self.editor.index("insert").split(".")[1])
        self.status_lbl.configure(
            text=f"  Ln {line}, Col {col}  ·  Python  ·  UTF-8  ·  main*  ·  indexing…"
        )
        delay = random.randint(12, 48) if chunk != "\n" else random.randint(40, 120)
        if random.random() < 0.04:
            delay += random.randint(200, 500)  # пауза «подумал»
        self._schedule(delay, self._type_code)

    def _reset_code(self) -> None:
        if not self._alive:
            return
        self.editor.delete("1.0", tk.END)
        self._snippet = random.choice(CODE_SNIPPETS)
        self._code_i = 0
        names = ["ingest.py", "cubic.py", "map.ts", "api.py", "test_ingest.py"]
        self.tab_label.configure(text=f"  {random.choice(names)}  ×")
        self._type_code()

    def _tick_terminal(self) -> None:
        if not self._alive:
            return
        prompt, text, color = TERMINAL_LINES[self._term_i % len(TERMINAL_LINES)]
        self._term_i += 1
        if prompt:
            self.term.insert(tk.END, prompt, "prompt")
            # печатаем команду по символам быстро
            self._type_term_cmd(text, 0)
            return
        tag = "ok" if color == GREEN else ("info" if color == BLUE else ("warn" if color == YELLOW else "out"))
        self.term.insert(tk.END, text + "\n", tag)
        self.term.see(tk.END)
        self._schedule(random.randint(400, 1100), self._tick_terminal)

    def _type_term_cmd(self, text: str, i: int) -> None:
        if not self._alive:
            return
        if i >= len(text):
            self.term.insert(tk.END, "\n")
            self.term.see(tk.END)
            self._schedule(random.randint(300, 900), self._tick_terminal)
            return
        self.term.insert(tk.END, text[i], "cmd")
        self.term.see(tk.END)
        self._schedule(random.randint(8, 28), lambda: self._type_term_cmd(text, i + 1))

    def _tick_downloads(self) -> None:
        if not self._alive:
            return
        for i, var in enumerate(self.dl_vars):
            step = random.uniform(0.3, 2.8)
            val = min(100.0, var.get() + step)
            if val >= 100 and random.random() < 0.15:
                val = random.uniform(0, 12)  # «новый» файл / повтор
            var.set(val)
            mb = DOWNLOADS[i][1] * val / 100
            self.dl_labels[i].configure(
                text=f"{val:4.0f}%  ·  {mb:5.1f} / {DOWNLOADS[i][1]} MB  ·  {random.uniform(1.2, 9.5):.1f} MB/s"
            )
        self._schedule(280, self._tick_downloads)

    def _tick_metrics(self) -> None:
        if not self._alive:
            return
        cpu = random.randint(38, 92)
        ram = random.uniform(9.8, 27.4)
        down = random.uniform(0.8, 12.5)
        up = random.uniform(40, 420)
        color = RED if cpu > 85 else (YELLOW if cpu > 65 else GREEN)
        self.cpu_lbl.configure(text=f"CPU  {cpu}%", fg=color)
        self.ram_lbl.configure(text=f"RAM  {ram:.1f} / 32 GB")
        self.net_lbl.configure(text=f"NET  ↓ {down:.1f} MB/s  ↑ {up:.0f} KB/s")
        self._schedule(700, self._tick_metrics)

    def _blink_cursor(self) -> None:
        # tk Text уже мигает; обновляем «indexing»
        if not self._alive:
            return
        dots = "." * ((self._term_i % 3) + 1)
        base = self.status_lbl.cget("text").split("· indexing")[0]
        if "indexing" in self.status_lbl.cget("text") or True:
            parts = self.status_lbl.cget("text").rsplit("·", 1)
            if len(parts) == 2:
                self.status_lbl.configure(text=parts[0] + f"·  indexing{dots}")
        self._schedule(450, self._blink_cursor)

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
    """Скрыть главное окно и показать заставку; по Esc/F12 вернуть."""

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
