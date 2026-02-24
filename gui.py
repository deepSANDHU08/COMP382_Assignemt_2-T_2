"""
GUI for COMP382 city stack visualization.

Repo files reused:
- City_implementation.py: CityParams, generate_city
- Temp_CFG.py: CFG helpers where available
- city_output.json: sample dataset loader
- testscreenshot 1.png: sample preview image

Wrappers added here:
- dynamic generator adapter (to locate equivalent generator symbols if names differ)
- per-stack derivation trace fallback when generator does not provide traces
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import random
import sys
import traceback
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6 import QtCore, QtGui, QtWidgets

import matplotlib

# QtAgg backend for embedding matplotlib in PySide6.
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np


ROOT = Path(__file__).resolve().parent
SAMPLE_JSON = ROOT / "city_output.json"
SAMPLE_IMG = ROOT / "testscreenshot 1.png"

COLOR_MAP: Dict[str, QtGui.QColor] = {
    "R": QtGui.QColor(226, 62, 62),
    "G": QtGui.QColor(46, 168, 80),
    "B": QtGui.QColor(58, 107, 223),
}


@dataclass
class CellData:
    x: int
    z: int
    colors: List[str]
    dominant_color: str
    trace: List[str]

    @property
    def height(self) -> int:
        return len(self.colors)


@dataclass
class CityResult:
    width: int
    height: int
    grid: List[List[List[str]]]  # grid[z][x] = ["R", "G", ...]
    cells: Dict[Tuple[int, int], CellData]


class GeneratorAdapter:
    """Find and call project generator symbols while tolerating naming differences."""

    def __init__(self) -> None:
        self.city_params_cls: Optional[type] = None
        self.generate_city_fn: Optional[Callable[..., Any]] = None
        self.cfg_module: Optional[Any] = None
        self.debug_source: str = ""
        self._bootstrap()

    def _bootstrap(self) -> None:
        # First preference: canonical module names from this repo.
        canonical = self._try_import_module("City_implementation")
        if canonical:
            self.city_params_cls = getattr(canonical, "CityParams", None)
            self.generate_city_fn = getattr(canonical, "generate_city", None)
            if self.city_params_cls and callable(self.generate_city_fn):
                self.debug_source = "City_implementation.py"

        self.cfg_module = self._try_import_module("Temp_CFG")

        if self.city_params_cls and self.generate_city_fn:
            return

        # Fallback: scan top-level python files for equivalent symbols.
        for py_file in ROOT.glob("*.py"):
            if py_file.name in {"gui.py", "main.py"}:
                continue
            module = self._import_from_file(py_file)
            if module is None:
                continue

            if self.city_params_cls is None:
                self.city_params_cls = self._find_params_class(module)
            if self.generate_city_fn is None:
                self.generate_city_fn = self._find_generate_fn(module)

            if self.city_params_cls and self.generate_city_fn:
                self.debug_source = py_file.name
                break

    def _try_import_module(self, name: str) -> Optional[Any]:
        try:
            return importlib.import_module(name)
        except Exception:
            return None

    def _import_from_file(self, path: Path) -> Optional[Any]:
        try:
            spec = importlib.util.spec_from_file_location(path.stem, str(path))
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[path.stem] = module
            spec.loader.exec_module(module)
            return module
        except Exception:
            return None

    def _find_params_class(self, module: Any) -> Optional[type]:
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if "param" in name.lower():
                return obj
            annotations = getattr(obj, "__annotations__", {})
            if {"seed", "min_height", "max_height"}.issubset(set(annotations.keys())):
                return obj
        return None

    def _find_generate_fn(self, module: Any) -> Optional[Callable[..., Any]]:
        candidates: List[Callable[..., Any]] = []
        for _, fn in inspect.getmembers(module, inspect.isfunction):
            sig = inspect.signature(fn)
            pnames = set(sig.parameters.keys())
            if {"width", "height"}.issubset(pnames):
                candidates.append(fn)
            elif "generate" in fn.__name__.lower() and {"width", "height"}.intersection(pnames):
                candidates.append(fn)
        for fn in candidates:
            if "city" in fn.__name__.lower():
                return fn
        return candidates[0] if candidates else None

    def is_ready(self) -> bool:
        return bool(self.city_params_cls and callable(self.generate_city_fn))

    def create_params(
        self,
        *,
        seed: int,
        min_height: int,
        max_height: int,
        empty_prob: float,
        dominant_prob: float,
    ) -> Any:
        if self.city_params_cls is None:
            raise RuntimeError("CityParams-like class not found.")

        # Build kwargs only for fields this class accepts.
        kwargs = {
            "seed": seed,
            "min_height": min_height,
            "max_height": max_height,
            "empty_prob": empty_prob,
            "dominant_prob": dominant_prob,
        }
        sig = inspect.signature(self.city_params_cls)
        accepted = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return self.city_params_cls(**accepted)

    def generate(self, width: int, height: int, params: Any) -> Any:
        if not self.generate_city_fn:
            raise RuntimeError("generate_city-like function not found.")
        return self.generate_city_fn(width=width, height=height, params=params)


class CityGenWorker(QtCore.QObject):
    finished = QtCore.Signal(object, str)  # result, error

    def __init__(
        self,
        adapter: GeneratorAdapter,
        width: int,
        height: int,
        seed: int,
        min_height: int,
        max_height: int,
        empty_prob: float,
        dominant_prob: float,
    ) -> None:
        super().__init__()
        self.adapter = adapter
        self.width = width
        self.height = height
        self.seed = seed
        self.min_height = min_height
        self.max_height = max_height
        self.empty_prob = empty_prob
        self.dominant_prob = dominant_prob

    @QtCore.Slot()
    def run(self) -> None:
        try:
            params = self.adapter.create_params(
                seed=self.seed,
                min_height=self.min_height,
                max_height=self.max_height,
                empty_prob=self.empty_prob,
                dominant_prob=self.dominant_prob,
            )
            raw_city = self.adapter.generate(self.width, self.height, params)
            result = normalize_city(
                raw_city,
                width=self.width,
                height=self.height,
                dominant_prob=self.dominant_prob,
                seed=self.seed,
            )
            self.finished.emit(result, "")
        except Exception as exc:
            self.finished.emit(None, f"{exc}\n\n{traceback.format_exc()}")


def choose_dominant_from_colors(colors: List[str]) -> str:
    if not colors:
        return "-"
    counts = Counter(colors)
    best = max(counts.values())
    tied = {c for c, v in counts.items() if v == best}
    for c in colors:
        if c in tied:
            return c
    return colors[0]


def simulate_trace(colors: List[str], dominant: str) -> List[str]:
    if not colors:
        return ["CELL -> EMPTY"]

    trace = ["STACK -> COLUMN"]
    for i in range(len(colors)):
        if i < len(colors) - 1:
            trace.append("COLUMN -> CUBE COLUMN")
        else:
            trace.append("COLUMN -> CUBE")
    for c in colors:
        trace.append(f"CUBE -> {c} (dominant={dominant})")
    return trace


def normalize_city(
    raw_city: Any,
    *,
    width: int,
    height: int,
    dominant_prob: float,
    seed: int,
) -> CityResult:
    """Normalize different generator output formats to a stable internal structure."""
    grid: List[List[List[str]]] = [[[] for _ in range(width)] for _ in range(height)]
    cells: Dict[Tuple[int, int], CellData] = {}

    # Format A: expected list of rows where each row is list of stacks.
    if isinstance(raw_city, list) and raw_city and isinstance(raw_city[0], list):
        for z, row in enumerate(raw_city[:height]):
            for x, stack in enumerate(row[:width]):
                colors = [str(c) for c in stack] if isinstance(stack, list) else []
                grid[z][x] = colors
                dominant = choose_dominant_from_colors(colors)
                cells[(x, z)] = CellData(
                    x=x,
                    z=z,
                    colors=colors,
                    dominant_color=dominant,
                    trace=simulate_trace(colors, dominant),
                )
        return CityResult(width=width, height=height, grid=grid, cells=cells)

    # Format B: sparse JSON-like list of dict entries.
    if isinstance(raw_city, list) and raw_city and isinstance(raw_city[0], dict):
        for entry in raw_city:
            x = int(entry.get("x", 0))
            z = int(entry.get("z", 0))
            if not (0 <= x < width and 0 <= z < height):
                continue
            colors = [str(c) for c in entry.get("colors", [])]
            dominant = str(entry.get("dominant_color", choose_dominant_from_colors(colors)))
            trace = entry.get("trace")
            trace_list = [str(t) for t in trace] if isinstance(trace, list) else simulate_trace(colors, dominant)
            grid[z][x] = colors
            cells[(x, z)] = CellData(x=x, z=z, colors=colors, dominant_color=dominant, trace=trace_list)

        # Fill missing empty cells.
        for z in range(height):
            for x in range(width):
                if (x, z) not in cells:
                    cells[(x, z)] = CellData(x=x, z=z, colors=[], dominant_color="-", trace=["CELL -> EMPTY"])
        return CityResult(width=width, height=height, grid=grid, cells=cells)

    # Conservative fallback: empty city.
    for z in range(height):
        for x in range(width):
            cells[(x, z)] = CellData(x=x, z=z, colors=[], dominant_color="-", trace=["CELL -> EMPTY"])
    return CityResult(width=width, height=height, grid=grid, cells=cells)


def city_to_sparse_json(city: CityResult) -> List[Dict[str, Any]]:
    out = []
    for z in range(city.height):
        for x in range(city.width):
            cell = city.cells[(x, z)]
            if cell.height == 0:
                continue
            out.append(
                {
                    "x": x,
                    "z": z,
                    "height": cell.height,
                    "dominant_color": cell.dominant_color,
                    "colors": cell.colors,
                    "trace": cell.trace,
                }
            )
    return out


class CityScene2D(QtWidgets.QGraphicsScene):
    hovered = QtCore.Signal(int, int)
    clicked = QtCore.Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self.city: Optional[CityResult] = None
        self.show_heights = True
        self.cell_size = 34
        self.margin = 44
        self._cell_rects: Dict[Tuple[int, int], QtCore.QRectF] = {}
        self._hovered: Optional[Tuple[int, int]] = None

    def set_city(self, city: CityResult) -> None:
        self.city = city
        self._hovered = None
        self.redraw()

    def redraw(self) -> None:
        self.clear()
        self._cell_rects.clear()
        if not self.city:
            return

        grid_w = self.city.width * self.cell_size
        grid_h = self.city.height * self.cell_size
        self.setSceneRect(0, 0, grid_w + 2 * self.margin, grid_h + 2 * self.margin + 80)

        # Legend.
        legend_y = 8
        lx = 12
        for key in ["R", "G", "B"]:
            color = COLOR_MAP[key]
            self.addRect(lx, legend_y, 16, 16, QtGui.QPen(QtCore.Qt.black), QtGui.QBrush(color))
            txt = self.addText(f"{key}")
            txt.setPos(lx + 22, legend_y - 2)
            lx += 70

        for z in range(self.city.height):
            for x in range(self.city.width):
                self._draw_cell(x, z)

        # Axis labels.
        for x in range(self.city.width):
            tx = self.addText(str(x))
            tx.setDefaultTextColor(QtGui.QColor(60, 60, 60))
            tx.setPos(self.margin + x * self.cell_size + 10, self.margin + self.city.height * self.cell_size + 6)

        for z in range(self.city.height):
            tz = self.addText(str(z))
            tz.setDefaultTextColor(QtGui.QColor(60, 60, 60))
            tz.setPos(self.margin - 20, self.margin + z * self.cell_size + 7)

    def _draw_cell(self, x: int, z: int) -> None:
        if not self.city:
            return
        rect = QtCore.QRectF(
            self.margin + x * self.cell_size,
            self.margin + z * self.cell_size,
            self.cell_size,
            self.cell_size,
        )
        self._cell_rects[(x, z)] = rect

        # Base grid cell.
        self.addRect(rect, QtGui.QPen(QtGui.QColor(190, 190, 190), 1), QtGui.QBrush(QtGui.QColor(245, 246, 248)))

        cell = self.city.cells[(x, z)]
        colors = cell.colors
        if not colors:
            return

        # Shadow for depth.
        shadow_rect = QtCore.QRectF(rect.x() + 5, rect.y() + 6, self.cell_size - 10, self.cell_size - 10)
        self.addRect(shadow_rect, QtGui.QPen(QtCore.Qt.NoPen), QtGui.QBrush(QtGui.QColor(0, 0, 0, 35)))

        # Stacked mini-rectangles with slight offset to emulate vertical depth.
        for level, c in enumerate(colors):
            offset = -3 * level
            layer_rect = QtCore.QRectF(
                rect.x() + 4 + offset,
                rect.y() + 4 + offset,
                self.cell_size - 10,
                self.cell_size - 10,
            )
            base = COLOR_MAP.get(c, QtGui.QColor(120, 120, 120))
            self.addRect(layer_rect, QtGui.QPen(QtGui.QColor(30, 30, 30, 180), 0.8), QtGui.QBrush(base))
            # Top highlight edge.
            self.addLine(
                layer_rect.left(),
                layer_rect.top(),
                layer_rect.right(),
                layer_rect.top(),
                QtGui.QPen(QtGui.QColor(255, 255, 255, 110), 1),
            )

        if self.show_heights:
            text_item = self.addText(str(cell.height))
            text_item.setDefaultTextColor(QtGui.QColor(30, 30, 30))
            text_item.setPos(rect.center().x() - 5, rect.center().y() - 10)

    def _cell_at(self, pos: QtCore.QPointF) -> Optional[Tuple[int, int]]:
        for (x, z), rect in self._cell_rects.items():
            if rect.contains(pos):
                return x, z
        return None

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        cell = self._cell_at(event.scenePos())
        self._hovered = cell
        if cell:
            self.hovered.emit(cell[0], cell[1])
        self.redraw()
        if cell:
            rect = self._cell_rects[cell]
            self.addRect(rect, QtGui.QPen(QtGui.QColor(255, 193, 7), 2), QtGui.QBrush(QtCore.Qt.NoBrush))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        cell = self._cell_at(event.scenePos())
        if cell:
            self.clicked.emit(cell[0], cell[1])
        super().mousePressEvent(event)


class CityView2D(QtWidgets.QGraphicsView):
    hovered = QtCore.Signal(int, int)
    clicked = QtCore.Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self.scene2d = CityScene2D()
        self.setScene(self.scene2d)
        self.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.SmoothPixmapTransform
            | QtGui.QPainter.TextAntialiasing
        )
        self.setMouseTracking(True)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.scene2d.hovered.connect(self.hovered)
        self.scene2d.clicked.connect(self.clicked)

    def set_city(self, city: CityResult) -> None:
        self.scene2d.set_city(city)
        self.fitInView(self.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def export_png(self, path: Path, scale: float = 2.0) -> None:
        rect = self.sceneRect()
        image = QtGui.QImage(int(rect.width() * scale), int(rect.height() * scale), QtGui.QImage.Format_ARGB32)
        image.fill(QtGui.QColor("white"))
        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.scale(scale, scale)
        self.scene().render(painter)
        painter.end()
        image.save(str(path))


class City3DCanvas(QtWidgets.QWidget):
    hovered = QtCore.Signal(int, int)
    clicked = QtCore.Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self.city: Optional[CityResult] = None
        self.figure = Figure(figsize=(6, 5), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.ax = self.figure.add_subplot(111, projection="3d")
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

    def set_city(self, city: CityResult) -> None:
        self.city = city
        self.redraw()

    def redraw(self) -> None:
        self.ax.clear()
        if not self.city:
            self.canvas.draw_idle()
            return

        xs, ys, zs, dx, dy, dz, cols = [], [], [], [], [], [], []
        for z in range(self.city.height):
            for x in range(self.city.width):
                cell = self.city.cells[(x, z)]
                if cell.height == 0:
                    continue
                xs.append(x)
                ys.append(z)
                zs.append(0)
                dx.append(0.85)
                dy.append(0.85)
                dz.append(cell.height)
                c = COLOR_MAP.get(cell.dominant_color, QtGui.QColor(120, 120, 120))
                cols.append((c.redF(), c.greenF(), c.blueF(), 0.95))

        if xs:
            self.ax.bar3d(np.array(xs), np.array(ys), np.array(zs), np.array(dx), np.array(dy), np.array(dz), color=cols, shade=True)

        self.ax.set_xlabel("x")
        self.ax.set_ylabel("z")
        self.ax.set_zlabel("height")
        self.ax.set_xlim(0, max(self.city.width, 1))
        self.ax.set_ylim(0, max(self.city.height, 1))
        self.ax.set_zlim(0, max((len(c.colors) for c in self.city.cells.values()), default=1) + 1)
        self.ax.view_init(elev=26, azim=38)
        self.canvas.draw_idle()

    def export_png(self, path: Path) -> None:
        self.figure.savefig(str(path), dpi=220)


class CityViewport(QtWidgets.QWidget):
    hovered = QtCore.Signal(int, int)
    clicked = QtCore.Signal(int, int)

    def __init__(self, title: str) -> None:
        super().__init__()
        self.city: Optional[CityResult] = None
        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setStyleSheet("font-weight: 600;")

        self.stack = QtWidgets.QStackedWidget()
        self.view2d = CityView2D()
        self.view3d = City3DCanvas()
        self.stack.addWidget(self.view2d)
        self.stack.addWidget(self.view3d)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title_label)
        layout.addWidget(self.stack, 1)

        self.view2d.hovered.connect(self.hovered)
        self.view2d.clicked.connect(self.clicked)

    def set_city(self, city: CityResult) -> None:
        self.city = city
        self.view2d.set_city(city)
        self.view3d.set_city(city)

    def set_3d(self, enabled: bool) -> None:
        self.stack.setCurrentWidget(self.view3d if enabled else self.view2d)

    def export_png(self, path: Path) -> None:
        if self.stack.currentWidget() is self.view3d:
            self.view3d.export_png(path)
        else:
            self.view2d.export_png(path)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("COMP382 Procedural City Visualizer")
        self.resize(1480, 860)

        self.adapter = GeneratorAdapter()
        self.city_a: Optional[CityResult] = None
        self.city_b: Optional[CityResult] = None
        self.selected_cell: Optional[Tuple[int, int]] = None
        self._thread: Optional[QtCore.QThread] = None
        self._is_generating: bool = False

        self._build_ui()
        self._bind_signals()
        self._load_sample_on_start()

        if not self.adapter.is_ready():
            self._show_error(
                "Generator Import Error",
                "Could not find `CityParams` and `generate_city` equivalents in project files. "
                "Use the canonical names or keep the files in the repo root.",
            )

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)

        # Left panel.
        left = QtWidgets.QFrame()
        left.setFrameShape(QtWidgets.QFrame.StyledPanel)
        left_lay = QtWidgets.QVBoxLayout(left)

        form = QtWidgets.QFormLayout()
        self.width_spin = QtWidgets.QSpinBox(minimum=2, maximum=100, value=12)
        self.height_spin = QtWidgets.QSpinBox(minimum=2, maximum=100, value=8)
        self.seed_spin = QtWidgets.QSpinBox(minimum=0, maximum=2_000_000_000, value=123)
        self.seed_b_spin = QtWidgets.QSpinBox(minimum=0, maximum=2_000_000_000, value=999)

        self.min_h = QtWidgets.QSpinBox(minimum=1, maximum=100, value=2)
        self.max_h = QtWidgets.QSpinBox(minimum=1, maximum=100, value=8)

        self.empty_prob = QtWidgets.QDoubleSpinBox(minimum=0.0, maximum=1.0, singleStep=0.05, value=0.35, decimals=2)
        self.dom_prob = QtWidgets.QDoubleSpinBox(minimum=0.0, maximum=1.0, singleStep=0.05, value=0.70, decimals=2)

        form.addRow("Width", self.width_spin)
        form.addRow("Height", self.height_spin)
        form.addRow("Seed A", self.seed_spin)
        form.addRow("Seed B", self.seed_b_spin)
        form.addRow("Min Height", self.min_h)
        form.addRow("Max Height", self.max_h)
        form.addRow("Empty Prob", self.empty_prob)
        form.addRow("Dominant Prob", self.dom_prob)

        left_lay.addLayout(form)

        btn_row = QtWidgets.QHBoxLayout()
        self.random_seed_btn = QtWidgets.QPushButton("Randomize seed")
        self.generate_btn = QtWidgets.QPushButton("Generate")
        btn_row.addWidget(self.random_seed_btn)
        btn_row.addWidget(self.generate_btn)
        left_lay.addLayout(btn_row)

        self.save_json_btn = QtWidgets.QPushButton("Save JSON")
        self.export_png_btn = QtWidgets.QPushButton("Export PNG")
        self.demo_btn = QtWidgets.QPushButton("Demo (123 vs 999)")
        self.load_sample_btn = QtWidgets.QPushButton("Load sample")

        self.toggle_3d = QtWidgets.QCheckBox("3D view")
        self.compare_chk = QtWidgets.QCheckBox("Compare seeds (A/B)")
        self.height_overlay_chk = QtWidgets.QCheckBox("Show height overlay")
        self.height_overlay_chk.setChecked(True)
        self.derivation_btn = QtWidgets.QPushButton("Show derivation for selected stack")

        for w in [self.toggle_3d, self.compare_chk, self.height_overlay_chk]:
            left_lay.addWidget(w)
        for b in [self.save_json_btn, self.export_png_btn, self.demo_btn, self.load_sample_btn, self.derivation_btn]:
            left_lay.addWidget(b)

        left_lay.addSpacing(12)

        # Example panel.
        ex_group = QtWidgets.QGroupBox("Examples")
        ex_l = QtWidgets.QVBoxLayout(ex_group)
        self.example_img = QtWidgets.QLabel()
        self.example_img.setMinimumHeight(150)
        self.example_img.setAlignment(QtCore.Qt.AlignCenter)
        self.example_img.setStyleSheet("background:#f3f4f6;border:1px solid #d1d5db;")
        ex_l.addWidget(self.example_img)
        self.example_info = QtWidgets.QLabel("city_output.json")
        self.example_info.setWordWrap(True)
        ex_l.addWidget(self.example_info)
        left_lay.addWidget(ex_group)
        left_lay.addStretch(1)

        # Center panel: two viewports for compare mode.
        center = QtWidgets.QWidget()
        center_lay = QtWidgets.QHBoxLayout(center)
        self.view_a = CityViewport("Seed A")
        self.view_b = CityViewport("Seed B")
        self.view_b.setVisible(False)
        center_lay.addWidget(self.view_a, 1)
        center_lay.addWidget(self.view_b, 1)

        # Right info panel.
        right = QtWidgets.QFrame()
        right.setFrameShape(QtWidgets.QFrame.StyledPanel)
        right_lay = QtWidgets.QVBoxLayout(right)

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setStyleSheet("font-weight:600;")
        right_lay.addWidget(self.status_label)

        self.info_text = QtWidgets.QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMinimumWidth(320)
        right_lay.addWidget(self.info_text, 1)

        self.derivation_text = QtWidgets.QPlainTextEdit()
        self.derivation_text.setReadOnly(True)
        self.derivation_text.setPlaceholderText("Derivation trace will appear here.")
        right_lay.addWidget(self.derivation_text, 1)

        root.addWidget(left, 0)
        root.addWidget(center, 1)
        root.addWidget(right, 0)

    def _bind_signals(self) -> None:
        self.random_seed_btn.clicked.connect(self._randomize_seed)
        self.generate_btn.clicked.connect(self.generate)
        self.save_json_btn.clicked.connect(self.save_json)
        self.export_png_btn.clicked.connect(self.export_png)
        self.demo_btn.clicked.connect(self.run_demo)
        self.load_sample_btn.clicked.connect(self._load_sample_on_start)
        self.derivation_btn.clicked.connect(self.show_derivation)
        self.toggle_3d.toggled.connect(self._update_mode)
        self.compare_chk.toggled.connect(self._on_compare_toggle)
        self.height_overlay_chk.toggled.connect(self._toggle_height_overlay)

        self.view_a.hovered.connect(lambda x, z: self._on_hover(x, z, source="A"))
        self.view_a.clicked.connect(lambda x, z: self._on_click(x, z, source="A"))
        self.view_b.hovered.connect(lambda x, z: self._on_hover(x, z, source="B"))
        self.view_b.clicked.connect(lambda x, z: self._on_click(x, z, source="B"))

    def _toggle_height_overlay(self, state: bool) -> None:
        self.view_a.view2d.scene2d.show_heights = state
        self.view_b.view2d.scene2d.show_heights = state
        if self.city_a:
            self.view_a.view2d.scene2d.redraw()
        if self.city_b:
            self.view_b.view2d.scene2d.redraw()

    def _on_compare_toggle(self, enabled: bool) -> None:
        self.view_b.setVisible(enabled)
        self.view_b.title_label.setText(f"Seed B ({self.seed_b_spin.value()})")

    def _randomize_seed(self) -> None:
        self.seed_spin.setValue(random.randint(1, 10_000_000))

    def _show_warning_if_large_grid(self) -> None:
        area = self.width_spin.value() * self.height_spin.value()
        if area > 1600:
            QtWidgets.QMessageBox.warning(
                self,
                "Large Grid",
                "Grid larger than 40x40 may render slowly. Consider reducing size.",
            )

    def _validate_inputs(self) -> bool:
        if self.min_h.value() > self.max_h.value():
            self._show_error("Input Error", "min_height must be <= max_height.")
            return False
        return True

    def _update_mode(self, use_3d: bool) -> None:
        self.view_a.set_3d(use_3d)
        self.view_b.set_3d(use_3d)

    def _on_hover(self, x: int, z: int, source: str) -> None:
        city = self.city_a if source == "A" else self.city_b
        if not city:
            return
        cell = city.cells.get((x, z))
        if not cell:
            return
        tip = f"({x},{z}) h={cell.height} dom={cell.dominant_color}"
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), tip, self)
        self.status_label.setText(f"Hover {source}: {tip}")

    def _on_click(self, x: int, z: int, source: str) -> None:
        city = self.city_a if source == "A" else self.city_b
        if not city:
            return
        cell = city.cells.get((x, z))
        if not cell:
            return

        self.selected_cell = (x, z)
        self.info_text.setPlainText(
            "\n".join(
                [
                    f"Source: Seed {source}",
                    f"Coordinates: (x={x}, z={z})",
                    f"Height: {cell.height}",
                    f"Dominant color: {cell.dominant_color}",
                    f"Colors: {cell.colors if cell.colors else '[]'}",
                ]
            )
        )
        self.derivation_text.setPlainText("\n".join(cell.trace))

    def show_derivation(self) -> None:
        if not self.selected_cell:
            self._show_error("No Selection", "Click a stack cell first.")
            return

        x, z = self.selected_cell
        city = self.city_a
        if self.compare_chk.isChecked() and self.city_b and self.view_b.isVisible():
            city = self.city_a  # primary for consistent behavior
        if not city:
            return

        cell = city.cells.get((x, z))
        if not cell:
            return
        self.derivation_text.setPlainText("\n".join(cell.trace))

    def generate(self) -> None:
        if self._is_generating:
            self.status_label.setText("Generation already in progress...")
            return
        if not self._validate_inputs():
            return
        self._show_warning_if_large_grid()

        if not self.adapter.is_ready():
            self._show_error("Generator Error", "Generator adapter is not ready.")
            return

        self.status_label.setText("Generating city...")
        self.generate_btn.setEnabled(False)
        self.demo_btn.setEnabled(False)
        self._is_generating = True

        self._thread = QtCore.QThread(self)
        worker = CityGenWorker(
            adapter=self.adapter,
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            seed=self.seed_spin.value(),
            min_height=self.min_h.value(),
            max_height=self.max_h.value(),
            empty_prob=self.empty_prob.value(),
            dominant_prob=self.dom_prob.value(),
        )
        worker.moveToThread(self._thread)
        self._thread.started.connect(worker.run)

        def on_done(result: Any, error: str) -> None:
            self.generate_btn.setEnabled(True)
            self.demo_btn.setEnabled(True)
            self._is_generating = False
            if error:
                self._show_error("Generation failed", error)
                self.status_label.setText("Generation failed")
            else:
                self.city_a = result
                self.view_a.set_city(result)
                self.view_a.title_label.setText(f"Seed A ({self.seed_spin.value()})")
                self.status_label.setText(f"Generated with {self.adapter.debug_source or 'detected module'}")

                if self.compare_chk.isChecked():
                    self._generate_b_sync()

            worker.deleteLater()
            if self._thread:
                self._thread.quit()
                self._thread.wait()

        worker.finished.connect(on_done)
        self._thread.start()

    def _generate_b_sync(self) -> None:
        try:
            params = self.adapter.create_params(
                seed=self.seed_b_spin.value(),
                min_height=self.min_h.value(),
                max_height=self.max_h.value(),
                empty_prob=self.empty_prob.value(),
                dominant_prob=self.dom_prob.value(),
            )
            raw = self.adapter.generate(self.width_spin.value(), self.height_spin.value(), params)
            self.city_b = normalize_city(
                raw,
                width=self.width_spin.value(),
                height=self.height_spin.value(),
                dominant_prob=self.dom_prob.value(),
                seed=self.seed_b_spin.value(),
            )
            self.view_b.set_city(self.city_b)
            self.view_b.title_label.setText(f"Seed B ({self.seed_b_spin.value()})")
        except Exception as exc:
            self._show_error("Seed B Generation failed", str(exc))

    def save_json(self) -> None:
        if not self.city_a:
            self._show_error("No Data", "Generate or load a city first.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save JSON", str(ROOT / "city_export.json"), "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(city_to_sparse_json(self.city_a), f, indent=2)
        self.status_label.setText(f"Saved JSON: {path}")

    def export_png(self) -> None:
        if not self.city_a:
            self._show_error("No Data", "Generate or load a city first.")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export PNG", str(ROOT / "city_view.png"), "PNG (*.png)")
        if not path:
            return
        self.view_a.export_png(Path(path))
        self.status_label.setText(f"Exported PNG: {path}")

    def run_demo(self) -> None:
        if self._is_generating:
            self.status_label.setText("Wait for current generation to finish.")
            return
        self.seed_spin.setValue(123)
        self.seed_b_spin.setValue(999)
        self.compare_chk.setChecked(True)
        self.generate()

        # Save demo outputs after a brief delay to allow render completion.
        def _save_demo() -> None:
            if self.city_a:
                self.view_a.export_png(ROOT / "demo_seed_123.png")
            if self.city_b:
                self.view_b.export_png(ROOT / "demo_seed_999.png")
            self.status_label.setText("Demo complete: demo_seed_123.png, demo_seed_999.png")

        QtCore.QTimer.singleShot(1200, _save_demo)

    def _load_sample_on_start(self) -> None:
        if SAMPLE_IMG.exists():
            pix = QtGui.QPixmap(str(SAMPLE_IMG)).scaled(280, 180, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            self.example_img.setPixmap(pix)
        else:
            self.example_img.setText("Sample screenshot not found")

        if SAMPLE_JSON.exists():
            try:
                with open(SAMPLE_JSON, "r", encoding="utf-8") as f:
                    data = json.load(f)

                max_x = max((int(d.get("x", 0)) for d in data), default=9)
                max_z = max((int(d.get("z", 0)) for d in data), default=9)
                w = max(1, max_x + 1)
                h = max(1, max_z + 1)

                self.width_spin.setValue(min(max(w, 2), self.width_spin.maximum()))
                self.height_spin.setValue(min(max(h, 2), self.height_spin.maximum()))

                city = normalize_city(
                    data,
                    width=self.width_spin.value(),
                    height=self.height_spin.value(),
                    dominant_prob=self.dom_prob.value(),
                    seed=self.seed_spin.value(),
                )
                self.city_a = city
                self.view_a.set_city(city)
                self.status_label.setText("Loaded sample city_output.json")
                self.example_info.setText(f"Sample loaded from: {SAMPLE_JSON.name}")
            except Exception as exc:
                self.example_info.setText(f"Sample JSON load error: {exc}")

    def _show_error(self, title: str, msg: str) -> None:
        QtWidgets.QMessageBox.critical(self, title, msg)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("COMP382 City Visualizer")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
