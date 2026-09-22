"""Matplotlib house style: squircle frames, rounded artists and palettes."""
import numpy as np
from cycler import cycler
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.collections import LineCollection
from matplotlib.container import BarContainer, ErrorbarContainer
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from functools import wraps
from matplotlib.lines import Line2D
from matplotlib.offsetbox import DrawingArea
from matplotlib.path import Path
from matplotlib.patches import FancyBboxPatch, PathPatch
from matplotlib.ticker import MaxNLocator, Formatter
from matplotlib.transforms import Bbox


HVB_PALETTES = {
    # Data lines on a white background.
    "default": [
        (0.207843, 0.486275, 0.854902),  # blue   #357CDA
        (0.850980, 0.000000, 0.000000),  # red    #D90000
        (0.258824, 0.760784, 0.458824),  # green  #42C275
        (0.505882, 0.254902, 0.584314),  # purple #814195
        (0.866667, 0.482353, 0.000000),  # orange #DD7B00
        (0.917647, 0.878431, 0.039216),  # yellow #EAE00A
        (0.972549, 0.207843, 0.635294),  # pink   #F835A2
        (0.392157, 0.203922, 0.113725),  # brown  #64341D
    ],
    # Context series sitting behind the primary lines.
    "muted": [
        (0.584314, 0.760784, 1.000000),  # blue   #95C2FF
        (1.000000, 0.627451, 0.568627),  # red    #FFA091
        (0.635294, 0.866667, 0.698039),  # green  #A2DDB2
        (0.823529, 0.635294, 0.882353),  # purple #D2A2E1
        (0.964706, 0.733333, 0.552941),  # orange #F6BB8D
        (0.898039, 0.890196, 0.650980),  # yellow #E5E3A6
        (1.000000, 0.670588, 0.811765),  # pink   #FFABCF
        (0.800000, 0.623529, 0.545098),  # brown  #CC9F8B
    ],
    # Fills and confidence bands. Use opaque, not alpha.
    "fill": [
        (0.733333, 0.847059, 1.000000),  # blue   #BBD8FF
        (1.000000, 0.764706, 0.725490),  # red    #FFC3B9
        (0.752941, 0.913725, 0.796078),  # green  #C0E9CB
        (0.894118, 0.760784, 0.937255),  # purple #E4C2EF
        (0.988235, 0.827451, 0.698039),  # orange #FCD3B2
        (0.929412, 0.925490, 0.760784),  # yellow #EDECC2
        (1.000000, 0.792157, 0.874510),  # pink   #FFCADF
        (0.882353, 0.752941, 0.698039),  # brown  #E1C0B2
    ],
    # Data lines on a dark background (#141414).
    "dark": [
        (0.611765, 0.788235, 1.000000),  # blue   #9CC9FF
        (1.000000, 0.329412, 0.086275),  # red    #FF5416
        (0.298039, 0.831373, 0.521569),  # green  #4CD485
        (0.811765, 0.541176, 0.890196),  # purple #CF8AE3
        (0.929412, 0.619608, 0.243137),  # orange #ED9E3E
        (0.890196, 0.815686, 0.247059),  # yellow #E3D03F
        (0.964706, 0.439216, 0.643137),  # pink   #F670A4
        (0.796078, 0.525490, 0.407843),  # brown  #CB8668
    ],
    "dark2": [tuple(c[:3]) for c in plt.get_cmap("Dark2")(np.linspace(0.0, 1.0, 8))],
    "viridis": [tuple(c[:3]) for c in plt.get_cmap("viridis")(np.linspace(0.15, 0.9, 6))],
}


def get_hvb_palette(name="default"):
    key = str(name).lower()
    if key not in HVB_PALETTES:
        raise ValueError(f"Unknown palette '{name}'. Available: {sorted(HVB_PALETTES)}")
    return list(HVB_PALETTES[key])


def set_hvb_palette(name="default"):
    palette = get_hvb_palette(name)
    mpl.rcParams["axes.prop_cycle"] = cycler(color=palette)
    return palette


# ----------------------------
# 1) Scale helpers
# ----------------------------
def _clean_numeric_string(text):
    if text in {"-0", "-0.0", "-0.00"}:
        return "0"
    return text


def _get_hvb_tick_locations(axis):
    if axis is None:
        return np.array([], dtype=float)

    try:
        locs = np.asarray(axis.get_majorticklocs(), dtype=float)
    except Exception:
        return np.array([], dtype=float)

    locs = locs[np.isfinite(locs)]
    if locs.size == 0:
        return locs

    try:
        vmin, vmax = axis.get_view_interval()
        lo, hi = sorted((float(vmin), float(vmax)))
        span = hi - lo
        tol = max(abs(span), abs(lo), abs(hi), 1.0) * 1e-12
        locs = locs[(locs >= lo - tol) & (locs <= hi + tol)]
    except Exception:
        pass

    return np.unique(locs)


def _infer_hvb_decimals(axis, fallback=0, max_decimals=12):
    locs = _get_hvb_tick_locations(axis)
    if locs.size <= 1:
        return max(0, int(fallback))

    diffs = np.abs(np.diff(locs))
    diffs = diffs[diffs > 0]
    if diffs.size == 0:
        return max(0, int(fallback))

    min_step = float(np.min(diffs))
    atol = max(min_step * 0.1, 1e-12)

    for decimals in range(max(0, int(fallback)), max(0, int(max_decimals)) + 1):
        rounded = np.round(locs, decimals=decimals)
        labels = [_format_hvb_number(value, decimals=decimals) for value in locs]
        if np.all(np.abs(rounded - locs) <= atol) and len(set(labels)) == len(labels):
            return decimals

    return max(0, int(max_decimals))


def _format_hvb_number(value, decimals=None, axis=None, max_decimals=12):
    if not np.isfinite(value):
        return str(value)

    if decimals is None:
        decimals = _infer_hvb_decimals(axis, max_decimals=max_decimals)

    rounded_int = np.round(value)
    if np.isclose(value, rounded_int, rtol=0.0, atol=1e-10):
        return str(int(rounded_int))
    text = f"{value:.{int(decimals)}f}".rstrip("0").rstrip(".")
    return _clean_numeric_string(text)


class HVBNumberFormatter(Formatter):
    def __init__(self, decimals=None, max_decimals=12):
        self.decimals = None if decimals is None else max(0, int(decimals))
        self.max_decimals = max(0, int(max_decimals))

    def __call__(self, value, pos=None):
        return _format_hvb_number(
            value,
            decimals=self.decimals,
            axis=getattr(self, "axis", None),
            max_decimals=self.max_decimals,
        )


def make_hvb_number_formatter(decimals=None, max_decimals=12):
    return HVBNumberFormatter(decimals=decimals, max_decimals=max_decimals)


def apply_hvb_breaks(ax, x_nbreaks=5, y_nbreaks=5, prune_outer=True):
    prune = "both" if prune_outer else None
    ax.xaxis.set_major_locator(MaxNLocator(nbins=x_nbreaks, prune=prune))
    ax.yaxis.set_major_locator(MaxNLocator(nbins=y_nbreaks, prune=prune))
    return ax


def apply_hvb_number_formatters(ax, x_decimals=None, y_decimals=None, x_formatter=None, y_formatter=None):
    ax.xaxis.set_major_formatter(x_formatter or make_hvb_number_formatter(decimals=x_decimals))
    ax.yaxis.set_major_formatter(y_formatter or make_hvb_number_formatter(decimals=y_decimals))
    return ax


def apply_hvb_scales(
    ax,
    x_nbreaks=5,
    y_nbreaks=5,
    prune_outer=True,
    x_decimals=None,
    y_decimals=None,
    x_formatter=None,
    y_formatter=None,
    apply_breaks=True,
    apply_formatters=True,
):
    if apply_breaks:
        apply_hvb_breaks(ax, x_nbreaks=x_nbreaks, y_nbreaks=y_nbreaks, prune_outer=prune_outer)
    if apply_formatters:
        apply_hvb_number_formatters(
            ax,
            x_decimals=x_decimals,
            y_decimals=y_decimals,
            x_formatter=x_formatter,
            y_formatter=y_formatter,
        )
    return ax


# ----------------------------
# 2) Squircle / frame system
# ----------------------------
def _superellipse_unit_vertices(exponent=70.0, npts=1600):
    t = np.linspace(0, 2 * np.pi, int(npts), endpoint=False)
    c = np.cos(t)
    s = np.sin(t)
    x = np.sign(c) * (np.abs(c) ** (2.0 / exponent))
    y = np.sign(s) * (np.abs(s) ** (2.0 / exponent))
    X = (x + 1) / 2
    Y = (y + 1) / 2
    return np.column_stack([X, Y])


def _path_from_vertices(verts_xy):
    codes = np.full(len(verts_xy), Path.LINETO, dtype=np.uint8)
    codes[0] = Path.MOVETO
    verts2 = np.vstack([verts_xy, verts_xy[0]])
    codes2 = np.append(codes, Path.CLOSEPOLY)
    return Path(verts2, codes2)


def _clip_tick_elements(ax, clip_patch):
    for tick in ax.xaxis.get_major_ticks() + ax.xaxis.get_minor_ticks():
        for artist in (tick.tick1line, tick.tick2line, tick.gridline):
            artist.set_clip_path(clip_patch)
    for tick in ax.yaxis.get_major_ticks() + ax.yaxis.get_minor_ticks():
        for artist in (tick.tick1line, tick.tick2line, tick.gridline):
            artist.set_clip_path(clip_patch)


def _clip_axes_artists(ax, clip_patch, skip=()):
    skip_ids = {id(obj) for obj in skip}
    for artist in list(ax.lines) + list(ax.collections) + list(ax.images) + list(ax.patches):
        if id(artist) in skip_ids:
            continue
        if hasattr(artist, "set_clip_path"):
            artist.set_clip_path(clip_patch)
    for artist in ax.artists:
        if id(artist) in skip_ids:
            continue
        if hasattr(artist, "set_clip_path"):
            artist.set_clip_path(clip_patch)
    _clip_tick_elements(ax, clip_patch)
    for gl in ax.get_xgridlines() + ax.get_ygridlines():
        gl.set_clip_path(clip_patch)


def squircle_axes_frame(
    ax,
    exponent=70.0,
    inset=0.008,
    linewidth=None,
    edgecolor=None,
    facecolor=None,
    border_z=15,
    fill_z=-2,
):
    if linewidth is None:
        linewidth = ax.spines["left"].get_linewidth()
    if edgecolor is None:
        edgecolor = ax.spines["left"].get_edgecolor()
    if facecolor is None:
        facecolor = ax.get_facecolor()

    ax.patch.set_visible(False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    verts = _superellipse_unit_vertices(exponent=exponent, npts=1600)
    verts[:, 0] = inset + (1 - 2 * inset) * verts[:, 0]
    verts[:, 1] = inset + (1 - 2 * inset) * verts[:, 1]
    path = _path_from_vertices(verts)

    fill = PathPatch(
        path,
        transform=ax.transAxes,
        facecolor=facecolor,
        edgecolor="none",
        zorder=fill_z,
        clip_on=False,
    )
    border = PathPatch(
        path,
        transform=ax.transAxes,
        facecolor="none",
        edgecolor=edgecolor,
        linewidth=linewidth,
        zorder=border_z,
        clip_on=False,
        joinstyle="round",
        capstyle="round",
    )
    ax.add_patch(fill)
    ax.add_patch(border)

    _clip_axes_artists(ax, fill, skip=(fill, border))
    return fill, border


def ensure_ticks_over_grid(ax, grid_z=0, tick_z=12, include_minor=True,
                           show_grid=None):
    """Raise ticks above the grid. `show_grid` None leaves visibility alone."""
    ax.set_axisbelow(True)
    if show_grid is not None:
        ax.grid(bool(show_grid), which="major", zorder=grid_z)
    x_ticks = list(ax.xaxis.get_major_ticks())
    y_ticks = list(ax.yaxis.get_major_ticks())
    if include_minor:
        x_ticks += list(ax.xaxis.get_minor_ticks())
        y_ticks += list(ax.yaxis.get_minor_ticks())

    for gl in ax.get_xgridlines() + ax.get_ygridlines():
        gl.set_zorder(grid_z)

    for tick in x_ticks + y_ticks:
        try:
            tick.gridline.set_zorder(grid_z)
        except Exception:
            pass
        tick.tick1line.set_zorder(tick_z)
        tick.tick2line.set_zorder(tick_z)
    return ax


# ----------------------------
# 3) Legend squircle (BoxStyle)
# ----------------------------
def _corner_radius(exponent, width, height):
    """Absolute corner radius of a superellipse on a width x height box."""
    r = np.sqrt(2) * (1 - 2.0 ** (-1.0 / float(exponent))) / (np.sqrt(2) - 1)
    return 0.5 * r * np.sqrt(max(width, 1e-9) * max(height, 1e-9))


def _exponent_for_radius(radius, width, height):
    """Exponent giving a corner of `radius` on a width x height box."""
    r = 2.0 * float(radius) / np.sqrt(max(width, 1e-9) * max(height, 1e-9))
    k = min(max(r * (np.sqrt(2) - 1) / np.sqrt(2), 1e-9), 0.5)
    return max(-np.log(2.0) / np.log1p(-k), 2.0)


@mpatches._register_style(mpatches.BoxStyle._style_list, name="superellipse")
class SuperellipseBoxStyle:
    def __init__(self, pad=0.22, exponent=70.0, npts=320.0, radius=None):
        self.pad = float(pad)
        self.exponent = float(exponent)
        self.npts = int(max(60, round(float(npts))))
        # float or callable; a corner of this absolute size regardless of box size
        self.radius = radius

    def __call__(self, x0, y0, width, height, mutation_size):
        pad = mutation_size * self.pad
        x0p, y0p = x0 - pad, y0 - pad
        wp, hp = width + 2 * pad, height + 2 * pad

        exponent = self.exponent
        r = self.radius() if callable(self.radius) else self.radius
        if r:
            exponent = _exponent_for_radius(r, wp, hp)

        verts = _superellipse_unit_vertices(exponent=exponent, npts=self.npts)
        verts[:, 0] = x0p + wp * verts[:, 0]
        verts[:, 1] = y0p + hp * verts[:, 1]
        return _path_from_vertices(verts)


def set_legend_squircle(leg, exponent=70.0, pad=0.22, npts=320, match_ax=None,
                        inset=0.008):
    """`match_ax` matches the frame's corner in absolute size, not shape."""
    radius = None
    if match_ax is not None:
        def radius():
            bb = match_ax.get_window_extent()
            s = 1.0 - 2.0 * inset
            return _corner_radius(exponent, bb.width * s, bb.height * s)
    frame = leg.get_frame()
    frame.set_boxstyle(SuperellipseBoxStyle(pad=pad, exponent=exponent,
                                            npts=npts, radius=radius))
    return frame


def _iter_drawing_areas(artist):
    if isinstance(artist, DrawingArea):
        yield artist
    if hasattr(artist, "get_children"):
        for child in artist.get_children():
            yield from _iter_drawing_areas(child)


def style_hvb_errorbar_legend(leg, cap_half_length=None):
    if leg is None:
        return leg

    for drawing_area in _iter_drawing_areas(leg):
        children = list(drawing_area.get_children())
        line_collections = [child for child in children if isinstance(child, LineCollection)]
        cap_markers = [
            child for child in children
            if isinstance(child, Line2D) and child.get_marker() == "_" and child.get_linestyle() == "None"
            and child.get_visible()
        ]
        if not line_collections or len(cap_markers) < 2:
            continue

        stem = line_collections[0]
        stem.set_capstyle("butt")

        color = stem.get_colors()[0]
        lw = float(np.atleast_1d(stem.get_linewidth())[0])
        seg = stem.get_segments()[0]
        vertical = abs(seg[1][1] - seg[0][1]) >= abs(seg[1][0] - seg[0][0])

        for marker_line in cap_markers:
            x0 = float(np.asarray(marker_line.get_xdata())[0])
            y0 = float(np.asarray(marker_line.get_ydata())[0])
            marker_size = float(marker_line.get_markersize())
            half = 0.35 * marker_size if cap_half_length is None else float(cap_half_length)

            if vertical:
                xdata = [x0 - half, x0 + half]
                ydata = [y0, y0]
            else:
                xdata = [x0, x0]
                ydata = [y0 - half, y0 + half]

            rounded_cap = Line2D(
                xdata,
                ydata,
                color=color,
                linewidth=lw,
                linestyle="-",
                marker="None",
                solid_capstyle="round",
                solid_joinstyle="round",
                zorder=marker_line.get_zorder(),
            )
            drawing_area.add_artist(rounded_cap)
            marker_line.set_visible(False)

        for child in children:
            if isinstance(child, Line2D) and child.get_linestyle() == "-" and child.get_marker() == "none":
                child.set_solid_capstyle("round")
                child.set_solid_joinstyle("round")
            elif isinstance(child, Line2D) and child.get_marker() not in {"None", "none", "_"}:
                child.set_markeredgewidth(0.0)

    return leg


def style_hvb_legend(
    leg,
    exponent=70.0,
    pad=0.22,
    npts=320,
    match_ax=None,
    inset=0.008,
    linewidth=None,
    edgecolor=None,
    facecolor=None,
    alpha=None,
    style_errorbars=True,
):
    frame = set_legend_squircle(leg, exponent=exponent, pad=pad, npts=npts,
                                match_ax=match_ax, inset=inset)
    # bar and hist originals are hidden once rounded; keep their swatches
    for handle in getattr(leg, "legend_handles", []):
        if isinstance(handle, mpatches.Patch):
            handle.set_visible(True)
    if linewidth is not None:
        frame.set_linewidth(linewidth)
    if edgecolor is not None:
        frame.set_edgecolor(edgecolor)
    if facecolor is not None:
        frame.set_facecolor(facecolor)
    if alpha is not None:
        frame.set_alpha(alpha)
    frame.set_joinstyle("round")
    if style_errorbars:
        style_hvb_errorbar_legend(leg)
    return leg


# ----------------------------
# 4) Rounded-rectangle helpers
# ----------------------------
def _resolve_patch_colors(patch, facecolor=None, edgecolor=None):
    fc = patch.get_facecolor() if facecolor is None else facecolor
    ec = patch.get_edgecolor() if edgecolor is None else edgecolor
    return fc, ec


def _rounded_rect_patch_from_rect(rect, rounding_size=0.12, linewidth=None, facecolor=None, edgecolor=None):
    x = rect.get_x()
    y = rect.get_y()
    w = rect.get_width()
    h = rect.get_height()
    if w < 0:
        x = x + w
        w = abs(w)
    if h < 0:
        y = y + h
        h = abs(h)
    if np.isclose(w, 0.0) or np.isclose(h, 0.0):
        return None

    fc, ec = _resolve_patch_colors(rect, facecolor=facecolor, edgecolor=edgecolor)
    new_patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0,rounding_size={rounding_size}",
        linewidth=rect.get_linewidth() if linewidth is None else linewidth,
        edgecolor=ec,
        facecolor=fc,
        alpha=rect.get_alpha(),
        transform=rect.get_data_transform(),
        zorder=rect.get_zorder(),
        mutation_aspect=1.0,
    )
    new_patch.set_joinstyle("round")
    return new_patch


def _baseline_square_overlay_patch_from_rect(
    rect,
    rounding_size=0.12,
    facecolor=None,
    orientation="vertical",
    x=None,
    y=None,
    width=None,
    height=None,
):
    x_raw = rect.get_x() if x is None else x
    y_raw = rect.get_y() if y is None else y
    w_raw = rect.get_width() if width is None else width
    h_raw = rect.get_height() if height is None else height

    x0 = min(x_raw, x_raw + w_raw)
    x1 = max(x_raw, x_raw + w_raw)
    y0 = min(y_raw, y_raw + h_raw)
    y1 = max(y_raw, y_raw + h_raw)
    w = x1 - x0
    h = y1 - y0
    if np.isclose(w, 0.0) or np.isclose(h, 0.0):
        return None

    r = min(float(rounding_size), 0.5 * w, 0.5 * h)
    if np.isclose(r, 0.0):
        return None

    fc, _ = _resolve_patch_colors(rect, facecolor=facecolor, edgecolor=None)
    orientation = str(orientation).lower()
    if orientation == "vertical":
        oy = y0 if h_raw >= 0 else y1 - r
        overlay = mpl.patches.Rectangle(
            (x0, oy),
            w,
            r,
            facecolor=fc,
            edgecolor="none",
            alpha=rect.get_alpha(),
            transform=rect.get_data_transform(),
            zorder=rect.get_zorder() + 0.05,
        )
    elif orientation == "horizontal":
        ox = x0 if w_raw >= 0 else x1 - r
        overlay = mpl.patches.Rectangle(
            (ox, y0),
            r,
            h,
            facecolor=fc,
            edgecolor="none",
            alpha=rect.get_alpha(),
            transform=rect.get_data_transform(),
            zorder=rect.get_zorder() + 0.05,
        )
    else:
        raise ValueError("orientation must be 'vertical' or 'horizontal'")
    return overlay


def _one_sided_rounded_rect_path(x_raw, y_raw, w_raw, h_raw, rounding_size=0.12, orientation="vertical"):
    x0 = min(x_raw, x_raw + w_raw)
    x1 = max(x_raw, x_raw + w_raw)
    y0 = min(y_raw, y_raw + h_raw)
    y1 = max(y_raw, y_raw + h_raw)
    w = x1 - x0
    h = y1 - y0
    if np.isclose(w, 0.0) or np.isclose(h, 0.0):
        return None

    r = min(float(rounding_size), 0.5 * w, 0.5 * h)
    if np.isclose(r, 0.0):
        verts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        codes = [Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO, Path.CLOSEPOLY]
        return Path(verts, codes)

    k = 0.5522847498307936
    o = str(orientation).lower()

    if o == "vertical":
        if h_raw >= 0:
            verts = [
                (x0, y0),
                (x1, y0),
                (x1, y1 - r),
                (x1, y1 - r + k * r),
                (x1 - r + k * r, y1),
                (x1 - r, y1),
                (x0 + r, y1),
                (x0 + r - k * r, y1),
                (x0, y1 - r + k * r),
                (x0, y1 - r),
                (x0, y0),
                (x0, y0),
            ]
        else:
            verts = [
                (x0, y1),
                (x1, y1),
                (x1, y0 + r),
                (x1, y0 + r - k * r),
                (x1 - r + k * r, y0),
                (x1 - r, y0),
                (x0 + r, y0),
                (x0 + r - k * r, y0),
                (x0, y0 + r - k * r),
                (x0, y0 + r),
                (x0, y1),
                (x0, y1),
            ]
        codes = [
            Path.MOVETO,
            Path.LINETO,
            Path.LINETO,
            Path.CURVE4,
            Path.CURVE4,
            Path.CURVE4,
            Path.LINETO,
            Path.CURVE4,
            Path.CURVE4,
            Path.CURVE4,
            Path.LINETO,
            Path.CLOSEPOLY,
        ]
        return Path(verts, codes)

    if o == "horizontal":
        if w_raw >= 0:
            verts = [
                (x0, y0),
                (x1 - r, y0),
                (x1 - r + k * r, y0),
                (x1, y0 + r - k * r),
                (x1, y0 + r),
                (x1, y1 - r),
                (x1, y1 - r + k * r),
                (x1 - r + k * r, y1),
                (x1 - r, y1),
                (x0, y1),
                (x0, y0),
                (x0, y0),
            ]
        else:
            verts = [
                (x1, y0),
                (x0 + r, y0),
                (x0 + r - k * r, y0),
                (x0, y0 + r - k * r),
                (x0, y0 + r),
                (x0, y1 - r),
                (x0, y1 - r + k * r),
                (x0 + r - k * r, y1),
                (x0 + r, y1),
                (x1, y1),
                (x1, y0),
                (x1, y0),
            ]
        codes = [
            Path.MOVETO,
            Path.LINETO,
            Path.CURVE4,
            Path.CURVE4,
            Path.CURVE4,
            Path.LINETO,
            Path.CURVE4,
            Path.CURVE4,
            Path.CURVE4,
            Path.LINETO,
            Path.LINETO,
            Path.CLOSEPOLY,
        ]
        return Path(verts, codes)

    raise ValueError("orientation must be 'vertical' or 'horizontal'")


def _one_sided_rounded_patch(
    x_raw,
    y_raw,
    w_raw,
    h_raw,
    rounding_size=0.12,
    orientation="vertical",
    transform=None,
    facecolor="none",
    edgecolor="black",
    linewidth=1.0,
    alpha=None,
    zorder=None,
    clip_on=True,
):
    path = _one_sided_rounded_rect_path(
        x_raw,
        y_raw,
        w_raw,
        h_raw,
        rounding_size=rounding_size,
        orientation=orientation,
    )
    if path is None:
        return None
    patch = PathPatch(
        path,
        transform=transform,
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=linewidth,
        alpha=alpha,
        zorder=zorder,
        clip_on=clip_on,
    )
    patch.set_joinstyle("round")
    patch.set_capstyle("round")
    return patch


def _one_sided_rounded_patch_from_rect(rect, rounding_size=0.12, linewidth=None, facecolor=None, edgecolor=None, orientation="vertical"):
    x = rect.get_x()
    y = rect.get_y()
    w = rect.get_width()
    h = rect.get_height()
    fc, ec = _resolve_patch_colors(rect, facecolor=facecolor, edgecolor=edgecolor)
    return _one_sided_rounded_patch(
        x,
        y,
        w,
        h,
        rounding_size=rounding_size,
        orientation=orientation,
        transform=rect.get_data_transform(),
        facecolor=fc,
        edgecolor=ec,
        linewidth=rect.get_linewidth() if linewidth is None else linewidth,
        alpha=rect.get_alpha(),
        zorder=rect.get_zorder(),
        clip_on=True,
    )


def style_hvb_bars(
    bar_container,
    rounding_size=0.09,
    linewidth=None,
    facecolor=None,
    edgecolor=None,
    orientation=None,
):
    if getattr(bar_container, "_hvb_styled", False):
        return getattr(bar_container, "_hvb_styled_patches", [])
    patches = getattr(bar_container, "patches", bar_container)
    inferred_orientation = orientation or getattr(bar_container, "orientation", "vertical")
    styled = []
    overlays = []
    for rect in patches:
        new_patch = _rounded_rect_patch_from_rect(
            rect,
            rounding_size=rounding_size,
            linewidth=linewidth,
            facecolor=facecolor,
            edgecolor=edgecolor,
        )
        if new_patch is None:
            continue
        target_ax = rect.axes
        target_ax.add_patch(new_patch)
        overlay = _baseline_square_overlay_patch_from_rect(
            rect,
            rounding_size=rounding_size,
            facecolor=facecolor,
            orientation=inferred_orientation,
        )
        if overlay is not None:
            target_ax.add_patch(overlay)
            overlays.append(overlay)
        rect.set_visible(False)
        styled.append(new_patch)
    try:
        bar_container._hvb_styled = True
        bar_container._hvb_styled_patches = styled
        bar_container._hvb_styled_overlays = overlays
    except Exception:
        pass
    return styled


def style_hvb_horizontal_bars(bar_container, rounding_size=0.09, linewidth=None, facecolor=None, edgecolor=None):
    return style_hvb_bars(
        bar_container,
        rounding_size=rounding_size,
        linewidth=linewidth,
        facecolor=facecolor,
        edgecolor=edgecolor,
        orientation="horizontal",
    )


def style_hvb_histogram(
    hist_patches,
    rounding_size=0.09,
    linewidth=None,
    facecolor=None,
    edgecolor=None,
    gap_fraction=0.02,
):
    styled = []
    for rect in hist_patches:
        if getattr(rect, "_hvb_styled", False):
            continue
        width = rect.get_width()
        if np.isclose(width, 0.0):
            continue

        shrink = abs(width) * float(gap_fraction)
        x = rect.get_x() + 0.5 * np.sign(width) * shrink
        y = rect.get_y()
        w = width - np.sign(width) * shrink
        h = rect.get_height()
        if np.isclose(w, 0.0):
            continue

        temp_rect = mpl.patches.Rectangle((x, y), w, h, transform=rect.get_data_transform())
        temp_rect.set_facecolor(rect.get_facecolor() if facecolor is None else facecolor)
        temp_rect.set_edgecolor(rect.get_edgecolor() if edgecolor is None else edgecolor)
        temp_rect.set_linewidth(rect.get_linewidth() if linewidth is None else linewidth)
        temp_rect.set_alpha(rect.get_alpha())
        temp_rect.set_zorder(rect.get_zorder())

        new_patch = _one_sided_rounded_patch_from_rect(
            temp_rect,
            rounding_size=rounding_size,
            linewidth=linewidth,
            facecolor=facecolor,
            edgecolor=edgecolor,
            orientation="vertical",
        )
        if new_patch is None:
            continue
        rect.axes.add_patch(new_patch)
        rect.set_visible(False)
        rect._hvb_styled = True
        rect._hvb_styled_patch = new_patch
        styled.append(new_patch)
    return styled


def style_hvb_boxplot(boxplot_dict, linewidth=None, facecolor=None, edgecolor=None, mediancolor=None):
    styled_boxes = []
    for box in boxplot_dict.get("boxes", []):
        if getattr(box, "_hvb_styled", False):
            continue
        if not isinstance(box, mpl.patches.PathPatch):
            continue

        ax = box.axes
        if linewidth is not None:
            box.set_linewidth(linewidth)
        if facecolor is not None:
            box.set_facecolor(facecolor)
        if edgecolor is not None:
            box.set_edgecolor(edgecolor)
        box.set_joinstyle("round")

        border_patch = PathPatch(
            box.get_path(),
            transform=box.get_transform(),
            facecolor="none",
            edgecolor=box.get_edgecolor(),
            linewidth=box.get_linewidth(),
            joinstyle="round",
            capstyle="round",
            zorder=box.get_zorder() + 0.3,
        )
        ax.add_patch(border_patch)
        box.set_edgecolor((0, 0, 0, 0))
        box._hvb_styled = True
        box._hvb_border_patch = border_patch
        styled_boxes.append((box, border_patch))

    for key in ("whiskers", "caps", "means"):
        for line in boxplot_dict.get(key, []):
            if linewidth is not None:
                line.set_linewidth(linewidth)
            if edgecolor is not None:
                line.set_color(edgecolor)
            line.set_solid_capstyle("round")
            line.set_solid_joinstyle("round")

    for line in boxplot_dict.get("medians", []):
        if linewidth is not None:
            line.set_linewidth(linewidth)
        if mediancolor is not None:
            line.set_color(mediancolor)
        line.set_solid_capstyle("round")
        line.set_solid_joinstyle("round")
        line.set_zorder(2.15)

    for flier in boxplot_dict.get("fliers", []):
        flier.set_markeredgewidth(0.0)

    return styled_boxes


def style_hvb_violin(violin_dict, linewidth=None, facecolor=None, edgecolor=None, alpha=0.9):
    for body in violin_dict.get("bodies", []):
        if getattr(body, "_hvb_styled", False):
            continue
        if facecolor is not None:
            body.set_facecolor(facecolor)
        if edgecolor is not None:
            body.set_edgecolor(edgecolor)
        if linewidth is not None:
            body.set_linewidth(linewidth)
        body.set_alpha(alpha)
        body.set_joinstyle("round")
        body._hvb_styled = True
    for key in ("cbars", "cmins", "cmaxes", "cmedians"):
        artist = violin_dict.get(key)
        if artist is not None:
            if linewidth is not None:
                artist.set_linewidth(linewidth)
            if edgecolor is not None:
                artist.set_color(edgecolor)
            if hasattr(artist, "set_capstyle"):
                artist.set_capstyle("round")
    return violin_dict


def style_hvb_colorbar(cbar, rounding_size=0.08, linewidth=None, edgecolor=None, facecolor=None, inset=0.01):
    cbar.ax.grid(False)
    if edgecolor is None:
        edgecolor = mpl.rcParams.get("axes.edgecolor", "black")
    if linewidth is None:
        linewidth = mpl.rcParams.get("axes.linewidth", 1.5)
    if facecolor is None:
        facecolor = cbar.ax.get_facecolor()

    prior = getattr(cbar.ax, "_hvb_colorbar_clip_patch", None), getattr(cbar.ax, "_hvb_colorbar_border_patch", None)
    if all(p is not None for p in prior):
        clip_patch, border = prior
        _clip_axes_artists(cbar.ax, clip_patch, skip=(clip_patch, border))
    else:
        ax = cbar.ax
        ax.patch.set_visible(False)
        for spine in ax.spines.values():
            spine.set_visible(False)

        x0 = inset
        y0 = inset
        w = 1.0 - 2.0 * inset
        h = 1.0 - 2.0 * inset

        clip_patch = mpatches.Rectangle(
            (x0, y0),
            w,
            h,
            transform=ax.transAxes,
            facecolor=facecolor,
            edgecolor="none",
            linewidth=0.0,
            clip_on=False,
            zorder=-2,
        )
        border = mpatches.Rectangle(
            (x0, y0),
            w,
            h,
            transform=ax.transAxes,
            facecolor="none",
            edgecolor=edgecolor,
            linewidth=linewidth,
            clip_on=False,
            zorder=14,
        )

        ax.add_patch(clip_patch)
        ax.add_patch(border)
        _clip_axes_artists(ax, clip_patch, skip=(clip_patch, border))
        ax._hvb_colorbar_clip_patch = clip_patch
        ax._hvb_colorbar_border_patch = border

    cbar.outline.set_visible(False)
    cbar.ax._hvb_skip_auto_finish = True
    return cbar.ax._hvb_colorbar_clip_patch, cbar.ax._hvb_colorbar_border_patch


# ----------------------------
# 5) Errorbar styling
# ----------------------------
def _cap_segments(ax, x, y, points, horizontal):
    half = points * ax.figure.dpi / 72.0
    xy = ax.transData.transform(np.column_stack([np.asarray(x, float), np.asarray(y, float)]))
    d = np.array([half, 0.0]) if horizontal else np.array([0.0, half])
    inv = ax.transData.inverted()
    a = inv.transform(xy - d)
    b = inv.transform(xy + d)
    return [(tuple(p), tuple(q)) for p, q in zip(a, b)]


def style_hvb_errorbar(err_container, ax=None, capsize=None, line_kwargs=None, clip_path=None):
    if hasattr(err_container, "hvb_custom_caps"):
        for artist in err_container.hvb_custom_caps:
            try:
                artist.remove()
            except ValueError:
                pass
        err_container.hvb_custom_caps = []

    if ax is None:
        data_line = err_container.lines[0]
        ax = data_line.axes if data_line is not None else None
    if ax is None:
        raise ValueError("Could not infer axes for errorbar container.")

    data_line, caplines, barlinecols = err_container.lines
    if capsize is None:
        capsize = float(mpl.rcParams.get("errorbar.capsize", 5.0))
    if line_kwargs is None:
        line_kwargs = {}

    base_lw = None
    base_color = None
    if data_line is not None:
        data_line.set_solid_capstyle("round")
        data_line.set_solid_joinstyle("round")
        base_lw = data_line.get_linewidth()
        base_color = data_line.get_color()
    if base_lw is None:
        base_lw = float(mpl.rcParams.get("lines.linewidth", 2.0))

    for lc in barlinecols:
        lc.set_linewidth(base_lw)
        lc.set_capstyle("butt")
        if base_color is not None:
            lc.set_color(base_color)
        for key, value in line_kwargs.items():
            setter = getattr(lc, f"set_{key}", None)
            if setter is not None:
                setter(value)
        if clip_path is not None:
            lc.set_clip_path(clip_path)

    custom_caps = []
    if caplines:
        for line in caplines:
            x = np.asarray(line.get_xdata())
            y = np.asarray(line.get_ydata())
            color = base_color or line.get_color()
            lw = base_lw if base_lw is not None else line.get_markeredgewidth()
            is_horizontal = (np.nanmax(x) - np.nanmin(x)) >= (np.nanmax(y) - np.nanmin(y))
            segs = _cap_segments(ax, x, y, capsize, is_horizontal)
            lc = LineCollection(segs, colors=[color], linewidths=lw, capstyle="round", zorder=line.get_zorder())
            if clip_path is not None:
                lc.set_clip_path(clip_path)
            ax.add_collection(lc, autolim=False)
            custom_caps.append(lc)
            line.set_visible(False)

    err_container.hvb_custom_caps = custom_caps
    try:
        err_container._hvb_styled = True
    except Exception:
        pass
    return err_container


# ----------------------------
# 6) Convenience wrapper
# ----------------------------


def _line_overlaps_corner_box(line, corner_box, renderer):
    if not line.get_visible():
        return False
    try:
        bbox = line.get_window_extent(renderer)
    except Exception:
        return False
    if bbox is None:
        return False
    if not np.all(np.isfinite([bbox.x0, bbox.y0, bbox.x1, bbox.y1])):
        return False
    return bbox.overlaps(corner_box)


def resolve_hvb_corner_tick_overlaps(ax, clearance_pt=None, prefer="x", include_minor=True):
    fig = ax.figure
    canvas = fig.canvas
    if canvas is None:
        return ax

    renderer = canvas.get_renderer()
    if renderer is None:
        return ax

    bbox = ax.get_window_extent(renderer)
    if bbox is None or bbox.width <= 0 or bbox.height <= 0:
        return ax

    if clearance_pt is None:
        major_ticks = list(ax.xaxis.get_major_ticks()) + list(ax.yaxis.get_major_ticks())
        tick_sizes = []
        for tick in major_ticks:
            try:
                tick_sizes.append(float(tick.tick1line.get_markersize()))
            except Exception:
                pass
        try:
            frame_lw = float(ax.spines["left"].get_linewidth())
        except Exception:
            frame_lw = 1.5
        clearance_pt = (max(tick_sizes) if tick_sizes else 6.0) + frame_lw + 2.0

    clearance_px = float(clearance_pt) * fig.dpi / 72.0

    corners = {
        "bl": Bbox.from_extents(bbox.x0, bbox.y0, bbox.x0 + clearance_px, bbox.y0 + clearance_px),
        "br": Bbox.from_extents(bbox.x1 - clearance_px, bbox.y0, bbox.x1, bbox.y0 + clearance_px),
        "tl": Bbox.from_extents(bbox.x0, bbox.y1 - clearance_px, bbox.x0 + clearance_px, bbox.y1),
        "tr": Bbox.from_extents(bbox.x1 - clearance_px, bbox.y1 - clearance_px, bbox.x1, bbox.y1),
    }

    x_ticks = list(ax.xaxis.get_major_ticks())
    y_ticks = list(ax.yaxis.get_major_ticks())
    if include_minor:
        x_ticks += list(ax.xaxis.get_minor_ticks())
        y_ticks += list(ax.yaxis.get_minor_ticks())

    for tick in x_ticks:
        tick.tick1line.set_visible(True)
        tick.tick2line.set_visible(True)
    for tick in y_ticks:
        tick.tick1line.set_visible(True)
        tick.tick2line.set_visible(True)

    x_lines = [tick.tick1line for tick in x_ticks] + [tick.tick2line for tick in x_ticks]
    y_lines = [tick.tick1line for tick in y_ticks] + [tick.tick2line for tick in y_ticks]

    for corner_box in corners.values():
        x_hits = [line for line in x_lines if _line_overlaps_corner_box(line, corner_box, renderer)]
        y_hits = [line for line in y_lines if _line_overlaps_corner_box(line, corner_box, renderer)]
        if x_hits and y_hits:
            if str(prefer).lower().startswith("y"):
                for line in x_hits:
                    line.set_visible(False)
            else:
                for line in y_hits:
                    line.set_visible(False)
    return ax


def _flat_face_corner_fraction(exponent, cross_half_px, tol_px):
    """Fraction of a face, from each end, taken by the rounded corner."""
    tol = min(max(tol_px / float(cross_half_px), 1e-9), 0.5)
    x_flat = (1.0 - (1.0 - tol) ** exponent) ** (1.0 / exponent)
    return (1.0 - x_flat) / 2.0


def ticks_on_flat_faces(ax, exponent=70.0, inset=0.008, tol_px=0.1,
                        clearance_px=1.0, include_minor=True, hide_labels=False):
    """Hide ticks that would fall on a rounded corner rather than a flat face."""
    fig = ax.figure
    pos = ax.get_position()
    W = pos.width * fig.get_figwidth() * fig.dpi
    H = pos.height * fig.get_figheight() * fig.dpi
    if W <= 0 or H <= 0:
        return ax

    inv = ax.transAxes.inverted()

    def limits(corner_frac, span_px, tick_lw):
        margin = (tick_lw / 2.0 * fig.dpi / 72.0 + clearance_px) / span_px
        lo = inset + (1.0 - 2.0 * inset) * corner_frac + margin
        return lo, 1.0 - lo

    # x ticks sit on the horizontal faces, so their corner is bounded by tol in y
    x_lo, x_hi = limits(_flat_face_corner_fraction(exponent, H / 2.0, tol_px), W,
                        plt.rcParams["xtick.major.width"])
    y_lo, y_hi = limits(_flat_face_corner_fraction(exponent, W / 2.0, tol_px), H,
                        plt.rcParams["ytick.major.width"])

    def mask(axis, index, lo, hi):
        # Tick.get_loc() is only populated at draw time, so pair the tick
        # objects with the locator values instead.
        major = list(axis.get_majorticklocs())
        pairs = list(zip(axis.get_major_ticks(len(major)), major))
        if include_minor:
            minor = list(axis.get_minorticklocs())
            pairs += list(zip(axis.get_minor_ticks(len(minor)), minor))
        for tick, loc in pairs:
            pt = [0.0, 0.0]
            pt[index] = loc
            frac = inv.transform(ax.transData.transform(pt))[index]
            if lo <= frac <= hi:
                continue
            tick.tick1line.set_visible(False)
            tick.tick2line.set_visible(False)
            if hide_labels:
                tick.label1.set_visible(False)
                tick.label2.set_visible(False)

    mask(ax.xaxis, 0, x_lo, x_hi)
    mask(ax.yaxis, 1, y_lo, y_hi)
    return ax


def _install_flat_face_handler(ax, **kwargs):
    """Re-apply the flat-face rule on every draw."""
    canvas = ax.figure.canvas
    prior = getattr(ax, "_hvb_flat_face_cid", None)
    if prior is not None:
        try:
            canvas.mpl_disconnect(prior)
        except Exception:
            pass

    def _on_draw(event):
        if event.canvas is canvas:
            ticks_on_flat_faces(ax, **kwargs)

    ax._hvb_flat_face_cid = canvas.mpl_connect("draw_event", _on_draw)
    ax._hvb_flat_face_callback = _on_draw
    return ax


def _remove_flat_face_handler(ax):
    canvas = getattr(ax.figure, "canvas", None)
    prior = getattr(ax, "_hvb_flat_face_cid", None)
    if prior is not None and canvas is not None:
        try:
            canvas.mpl_disconnect(prior)
        except Exception:
            pass
    for attr in ("_hvb_flat_face_cid", "_hvb_flat_face_callback"):
        if hasattr(ax, attr):
            delattr(ax, attr)
    return ax


def _install_hvb_draw_handler(
    ax,
    avoid_corner_tick_overlaps=True,
    clearance_pt=None,
    prefer="x",
    include_minor=True,
    grid_z=0,
    tick_z=12,
):
    canvas = ax.figure.canvas
    prior_cid = getattr(ax, "_hvb_draw_handler_cid", None)
    if prior_cid is not None:
        try:
            canvas.mpl_disconnect(prior_cid)
        except Exception:
            pass

    def _on_draw(event):
        if event.canvas is not canvas:
            return
        ensure_ticks_over_grid(
            ax,
            grid_z=grid_z,
            tick_z=tick_z,
            include_minor=include_minor,
        )
        if avoid_corner_tick_overlaps:
            resolve_hvb_corner_tick_overlaps(
                ax,
                clearance_pt=clearance_pt,
                prefer=prefer,
                include_minor=include_minor,
            )

    cid = canvas.mpl_connect("draw_event", _on_draw)
    ax._hvb_draw_handler_cid = cid
    ax._hvb_draw_handler_callback = _on_draw
    return ax


def _remove_hvb_draw_handler(ax):
    canvas = getattr(ax.figure, "canvas", None)
    prior_cid = getattr(ax, "_hvb_draw_handler_cid", None)
    if prior_cid is not None and canvas is not None:
        try:
            canvas.mpl_disconnect(prior_cid)
        except Exception:
            pass
    if hasattr(ax, "_hvb_draw_handler_cid"):
        delattr(ax, "_hvb_draw_handler_cid")
    if hasattr(ax, "_hvb_draw_handler_callback"):
        delattr(ax, "_hvb_draw_handler_callback")
    return ax


def finish_hvb(
    ax,
    apply_scales=False,
    x_nbreaks=5,
    y_nbreaks=5,
    prune_outer=True,
    x_decimals=None,
    y_decimals=None,
    squircle_frame=True,
    frame_kwargs=None,
    style_legend=True,
    legend_kwargs=None,
    style_bars=True,
    bar_kwargs=None,
    style_errorbars=True,
    grid=None,
    flat_face_ticks=False,
    avoid_corner_tick_overlaps=True,
    corner_tick_clearance_pt=None,
    corner_tick_prefer="x",
    corner_tick_include_minor=True,
):
    if ax.name != "rectilinear":
        return ax
    if apply_scales:
        apply_hvb_scales(
            ax,
            x_nbreaks=x_nbreaks,
            y_nbreaks=y_nbreaks,
            prune_outer=prune_outer,
            x_decimals=x_decimals,
            y_decimals=y_decimals,
        )

    if style_bars:
        for container in ax.containers:
            if isinstance(container, BarContainer) and not getattr(container, "_hvb_styled", False):
                style_hvb_bars(container, **(bar_kwargs or {}))

    has_raster_or_image = len(ax.images) > 0
    if has_raster_or_image:
        ax.grid(False)

    clip_fill = None
    if squircle_frame:
        existing_fill = getattr(ax, "_hvb_frame_fill", None)
        existing_border = getattr(ax, "_hvb_frame_border", None)
        if existing_fill is not None and existing_border is not None:
            clip_fill = existing_fill
            _clip_axes_artists(ax, clip_fill, skip=(existing_fill, existing_border))
        else:
            clip_fill, border = squircle_axes_frame(ax, **(frame_kwargs or {}))
            ax._hvb_frame_fill = clip_fill
            ax._hvb_frame_border = border
        if not has_raster_or_image:
            ensure_ticks_over_grid(ax)

    if style_errorbars:
        for container in ax.containers:
            if isinstance(container, ErrorbarContainer):
                style_hvb_errorbar(container, ax=ax, clip_path=clip_fill)

    if style_legend and ax.get_legend() is not None:
        lk = dict(legend_kwargs or {})
        if squircle_frame:
            fk = frame_kwargs or {}
            lk.setdefault("match_ax", ax)
            lk.setdefault("exponent", fk.get("exponent", 70.0))
            lk.setdefault("inset", fk.get("inset", 0.008))
        style_hvb_legend(ax.get_legend(), **lk)

    if squircle_frame and not has_raster_or_image:
        _install_hvb_draw_handler(
            ax,
            avoid_corner_tick_overlaps=avoid_corner_tick_overlaps,
            clearance_pt=corner_tick_clearance_pt,
            prefer=corner_tick_prefer,
            include_minor=corner_tick_include_minor,
        )

    if flat_face_ticks and squircle_frame:
        fk = frame_kwargs or {}
        ff = {"exponent": fk.get("exponent", 70.0),
              "inset": fk.get("inset", 0.008)}
        if isinstance(flat_face_ticks, dict):
            ff.update(flat_face_ticks)
        ticks_on_flat_faces(ax, **ff)
        _install_flat_face_handler(ax, **ff)

    if grid is not None:
        ax.grid(bool(grid))

    return ax


def _iter_axes(fig):
    stack = list(fig.axes)
    seen = set()
    while stack:
        ax = stack.pop(0)
        if id(ax) in seen:
            continue
        seen.add(id(ax))
        yield ax
        stack.extend(getattr(ax, "child_axes", []))


def finish_hvb_figure(fig, **kwargs):
    """Run finish_hvb on every axes of `fig`, including insets and figure legends."""
    finished = []
    for ax in _iter_axes(fig):
        if getattr(ax, "_hvb_skip_auto_finish", False):
            continue
        finish_hvb(ax, **kwargs)
        if ax.name == "rectilinear":
            finished.append(ax)
    if kwargs.get("style_legend", True):
        lk = dict(kwargs.get("legend_kwargs") or {})
        if finished and kwargs.get("squircle_frame", True):
            fk = kwargs.get("frame_kwargs") or {}
            lk.setdefault("match_ax", finished[0])
            lk.setdefault("exponent", fk.get("exponent", 70.0))
            lk.setdefault("inset", fk.get("inset", 0.008))
        for leg in fig.legends:
            style_hvb_legend(leg, **lk)
    return fig


_HVB_RUNTIME = {
    "active": False,
    "originals": {},
    "config": {},
}


def _hvb_patch(target, name, wrapper_factory):
    key = (target, name)
    if key not in _HVB_RUNTIME["originals"]:
        _HVB_RUNTIME["originals"][key] = getattr(target, name)
    original = _HVB_RUNTIME["originals"][key]
    setattr(target, name, wrapper_factory(original))
    return original


def _hvb_runtime_config():
    return _HVB_RUNTIME["config"] if _HVB_RUNTIME["active"] else None


def _get_hvb_finish_kwargs():
    cfg = _hvb_runtime_config() or {}
    return dict(cfg.get("finish_kwargs", {}))


def _maybe_finish_figure(fig):
    cfg = _hvb_runtime_config()
    if not cfg or not cfg.get("auto_finish", True):
        return fig
    return finish_hvb_figure(fig, **_get_hvb_finish_kwargs())


def _finish_all_open_figures():
    for num in plt.get_fignums():
        try:
            fig = plt.figure(num)
        except Exception:
            continue
        _maybe_finish_figure(fig)


def activate_hvb(
    style=None,
    palette="default",
    auto_finish=True,
    auto_style_artists=True,
    finish_kwargs=None,
):
    if _HVB_RUNTIME["active"]:
        deactivate_hvb()

    if style is not None:
        plt.style.use(style)
    if palette is not None:
        set_hvb_palette(palette)

    _HVB_RUNTIME["active"] = True
    _HVB_RUNTIME["config"] = {
        "style": style,
        "palette": palette,
        "auto_finish": bool(auto_finish),
        "auto_style_artists": bool(auto_style_artists),
        "finish_kwargs": dict(finish_kwargs or {}),
    }

    def wrap_show(original):
        @wraps(original)
        def _wrapped_show(*args, **kwargs):
            _finish_all_open_figures()
            return original(*args, **kwargs)
        return _wrapped_show

    def wrap_savefig(original):
        @wraps(original)
        def _wrapped_savefig(self, *args, **kwargs):
            _maybe_finish_figure(self)
            return original(self, *args, **kwargs)
        return _wrapped_savefig

    def wrap_bar(original):
        @wraps(original)
        def _wrapped_bar(self, *args, **kwargs):
            out = original(self, *args, **kwargs)
            cfg = _hvb_runtime_config()
            if cfg and cfg.get("auto_style_artists", True) and not getattr(out, "_hvb_styled", False):
                style_hvb_bars(out)
            return out
        return _wrapped_bar

    def wrap_barh(original):
        @wraps(original)
        def _wrapped_barh(self, *args, **kwargs):
            out = original(self, *args, **kwargs)
            cfg = _hvb_runtime_config()
            if cfg and cfg.get("auto_style_artists", True) and not getattr(out, "_hvb_styled", False):
                style_hvb_horizontal_bars(out)
            return out
        return _wrapped_barh

    def wrap_hist(original):
        @wraps(original)
        def _wrapped_hist(self, *args, **kwargs):
            out = original(self, *args, **kwargs)
            cfg = _hvb_runtime_config()
            if cfg and cfg.get("auto_style_artists", True):
                patches = out[2]
                if isinstance(patches, np.ndarray):
                    for row in patches.ravel():
                        style_hvb_histogram(row)
                else:
                    style_hvb_histogram(patches)
            return out
        return _wrapped_hist

    def wrap_boxplot(original):
        @wraps(original)
        def _wrapped_boxplot(self, *args, **kwargs):
            out = original(self, *args, **kwargs)
            cfg = _hvb_runtime_config()
            if cfg and cfg.get("auto_style_artists", True):
                style_hvb_boxplot(out)
            return out
        return _wrapped_boxplot

    def wrap_violinplot(original):
        @wraps(original)
        def _wrapped_violinplot(self, *args, **kwargs):
            out = original(self, *args, **kwargs)
            cfg = _hvb_runtime_config()
            if cfg and cfg.get("auto_style_artists", True):
                style_hvb_violin(out)
            return out
        return _wrapped_violinplot

    def wrap_errorbar(original):
        @wraps(original)
        def _wrapped_errorbar(self, *args, **kwargs):
            out = original(self, *args, **kwargs)
            cfg = _hvb_runtime_config()
            if cfg and cfg.get("auto_style_artists", True):
                style_hvb_errorbar(out, ax=self, clip_path=getattr(self, "_hvb_frame_fill", None))
            return out
        return _wrapped_errorbar

    def wrap_legend(original):
        @wraps(original)
        def _wrapped_legend(self, *args, **kwargs):
            leg = original(self, *args, **kwargs)
            cfg = _hvb_runtime_config()
            if cfg and cfg.get("auto_style_artists", True) and leg is not None:
                style_hvb_legend(leg)
            return leg
        return _wrapped_legend

    def wrap_imshow(original):
        @wraps(original)
        def _wrapped_imshow(self, *args, **kwargs):
            out = original(self, *args, **kwargs)
            cfg = _hvb_runtime_config()
            if cfg:
                self.grid(False)
            return out
        return _wrapped_imshow

    def wrap_colorbar(original):
        @wraps(original)
        def _wrapped_colorbar(self, *args, **kwargs):
            cbar = original(self, *args, **kwargs)
            cfg = _hvb_runtime_config()
            if cfg and cfg.get("auto_style_artists", True):
                style_hvb_colorbar(cbar)
            return cbar
        return _wrapped_colorbar

    _hvb_patch(plt, "show", wrap_show)
    _hvb_patch(Figure, "savefig", wrap_savefig)
    _hvb_patch(Axes, "bar", wrap_bar)
    _hvb_patch(Axes, "barh", wrap_barh)
    _hvb_patch(Axes, "hist", wrap_hist)
    _hvb_patch(Axes, "boxplot", wrap_boxplot)
    _hvb_patch(Axes, "violinplot", wrap_violinplot)
    _hvb_patch(Axes, "errorbar", wrap_errorbar)
    _hvb_patch(Axes, "legend", wrap_legend)
    _hvb_patch(Axes, "imshow", wrap_imshow)
    _hvb_patch(Figure, "colorbar", wrap_colorbar)

    return _HVB_RUNTIME["config"]


def deactivate_hvb():
    for (target, name), original in list(_HVB_RUNTIME["originals"].items()):
        setattr(target, name, original)

    for num in plt.get_fignums():
        try:
            fig = plt.figure(num)
        except Exception:
            continue
        for ax in _iter_axes(fig):
            _remove_hvb_draw_handler(ax)
            _remove_flat_face_handler(ax)

    _HVB_RUNTIME["originals"].clear()
    _HVB_RUNTIME["config"] = {}
    _HVB_RUNTIME["active"] = False
    return None


def scale_rc(scale=1.0, text=False, tick_size=(6.7, 3.5)):
    """rcParams scaling the style for a smaller figure.

    `text` may be True, False, or a separate factor. `tick_size` is in points.
    """
    rc = {
        "axes.linewidth": 2.6 * scale,
        "xtick.major.width": 2.0 * scale,
        "ytick.major.width": 2.0 * scale,
        "xtick.minor.width": 1.4 * scale,
        "ytick.minor.width": 1.4 * scale,
        "grid.linewidth": 0.9 * scale,
    }
    if tick_size is not None:
        major, minor = tick_size
        rc.update({"xtick.major.size": major, "ytick.major.size": major,
                   "xtick.minor.size": minor, "ytick.minor.size": minor})
    if text is not False:
        ts = scale if text is True else float(text)
        rc.update({
            "font.size": 12 * ts,
            "axes.labelsize": 16 * ts,
            "axes.titlesize": 18 * ts,
            "xtick.labelsize": 14 * ts,
            "ytick.labelsize": 14 * ts,
            "legend.fontsize": 12 * ts,
        })
    return rc


def dark_rc(background="#141414", foreground="white", grid="#333333",
            legend_face="#1E1E1E", legend_edge="#3A3A3A", palette="dark"):
    """rcParams for a dark background. Layer over the base style."""
    rc = {
        "figure.facecolor": background,
        "axes.facecolor": background,
        "savefig.facecolor": "auto",
        "savefig.edgecolor": "auto",
        "text.color": foreground,
        "axes.edgecolor": foreground,
        "axes.labelcolor": foreground,
        "xtick.color": foreground,
        "ytick.color": foreground,
        "grid.color": grid,
        "legend.facecolor": legend_face,
        "legend.edgecolor": legend_edge,
        "legend.labelcolor": foreground,
    }
    if palette:
        rc["axes.prop_cycle"] = cycler(color=get_hvb_palette(palette))
    return rc


def use(dark=False, scale=None, text=False, linewidth=None, palette=None,
        grid=False, exponent=120.0, flat_face_ticks=True, auto=True):
    """Apply the style globally. Figures are finished automatically on save.

    `dark` may be True or a background color. `scale` shrinks frame, tick and
    data-line weights; `text` scales font sizes with it.
    """
    plt.style.use(["default", get_style_path()])
    mpl.rcParams["axes.grid"] = bool(grid)
    if scale is not None:
        mpl.rcParams.update(scale_rc(scale, text=text))
        mpl.rcParams["lines.linewidth"] *= scale
    if linewidth is not None:
        mpl.rcParams["lines.linewidth"] = linewidth
    if dark:
        bg = "#141414" if dark is True else dark
        mpl.rcParams.update(dark_rc(background=bg, palette=palette or "dark"))
    elif palette:
        set_hvb_palette(palette)
    if auto:
        activate_hvb(palette=None, finish_kwargs={
            "flat_face_ticks": flat_face_ticks,
            "frame_kwargs": {"exponent": exponent},
            "legend_kwargs": {"exponent": exponent},
        })
    return mpl.rcParams


def get_style_path():
    """Return the absolute path to the packaged hvb mplstyle file."""
    from pathlib import Path
    return str(Path(__file__).with_name("hvb.mplstyle"))
