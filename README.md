# hvb

hvb is a matplotlib house style. It consists of a style file, `hvb.mplstyle`, and helper
functions that replace the square axes frame with a superellipse (a "squircle," the curve
|x|^n + |y|^n = 1, which is a rectangle with rounded corners when n is large), round the
corners of bars, histograms, box plots, violin plots, and error bars, and provide a set of
categorical color palettes.

## Installation

```
pip install git+https://github.com/AlexanderBeach/hvb
```

## Usage

```python
import numpy as np
import matplotlib.pyplot as plt
import hvb

hvb.use(scale=0.6)          # or hvb.use(scale=0.6, dark=True)

x = np.linspace(0, 10, 200)
fig, ax = plt.subplots()
ax.plot(x, np.sin(x), label="sin")
ax.legend()
fig.savefig("figure.pdf")   # the frame and legend are styled on save
```

`hvb.use()` applies the style globally. The squircle frame, the legend frame, and the tick
placement are applied when a figure is saved with `fig.savefig` or shown with `plt.show`, not
when it is drawn, so a figure rendered with `fig.canvas.draw()` alone will still have the
default matplotlib frame.

The arguments to `hvb.use()` are:

- `scale`: multiplies the frame, tick, grid, and data line widths, for figures smaller than
  the default size. Font sizes are left unchanged unless `text` is also set.
- `text`: `True` scales the font sizes by `scale` as well. A number scales the font sizes by
  that factor instead.
- `dark`: `True` switches to a `#141414` background with white text and frame, and the `dark`
  palette. A color string sets a different background color.
- `palette`: the name of the palette used for the color cycle (see below).
- `linewidth`: the data line width in points, overriding the width set by `scale`.
- `grid`: `False` by default. Calling `ax.grid(True)` on an individual axes still turns the
  grid on for that axes.
- `exponent`: the superellipse exponent n of the frame, 120 by default. A higher exponent gives
  smaller corners. The legend frame uses the same absolute corner radius as the axes frame,
  whatever the size of the legend.
- `flat_face_ticks`: `True` by default, which hides any tick that would land on a rounded
  corner of the frame rather than on a straight edge.
- `auto`: `False` sets the rcParams only, without the squircle frame, the legend styling, or
  the rounded bars and error bars.

Polar and 3D axes are left with the default matplotlib frame.

## Palettes

| name | use |
|---|---|
| `default` | data lines on a white background |
| `muted` | context series that sit behind the primary lines |
| `fill` | fills and confidence bands, used opaque rather than with transparency |
| `dark` | data lines on a dark (`#141414`) background |
| `dark2`, `viridis` | samples of the matplotlib colormaps of the same name |

| # | hue | `default` | `muted` | `fill` | `dark` |
|---|---|---|---|---|---|
| 0 | blue | `#357CDA` | `#95C2FF` | `#BBD8FF` | `#9CC9FF` |
| 1 | red | `#D90000` | `#FFA091` | `#FFC3B9` | `#FF5416` |
| 2 | green | `#42C275` | `#A2DDB2` | `#C0E9CB` | `#4CD485` |
| 3 | purple | `#814195` | `#D2A2E1` | `#E4C2EF` | `#CF8AE3` |
| 4 | orange | `#DD7B00` | `#F6BB8D` | `#FCD3B2` | `#ED9E3E` |
| 5 | yellow | `#EAE00A` | `#E5E3A6` | `#EDECC2` | `#E3D03F` |
| 6 | pink | `#F835A2` | `#FFABCF` | `#FFCADF` | `#F670A4` |
| 7 | brown | `#64341D` | `#CC9F8B` | `#E1C0B2` | `#CB8668` |

The four categorical palettes use the same eight hues in the same order, so a given index
refers to the same series in every palette. The `muted` and `fill` colors have low contrast
against a white background, so they should not be the only thing that distinguishes one
category from another.

`hvb.use(palette="muted")` sets the color cycle to a named palette, and
`hvb.get_hvb_palette("fill")` returns a palette as a list of RGB tuples.

## Lower-level functions

`finish_hvb(ax, ...)` applies the frame, legend, bar, and error bar styling to a single axes,
and `finish_hvb_figure(fig, ...)` does the same for every axes in a figure, including inset
axes and figure legends. `scale_rc()` and `dark_rc()` return the dictionaries of rcParams that
`hvb.use()` applies, so they can be layered over the style file with `plt.style.context`.
`ticks_on_flat_faces(ax)` hides the ticks that would fall on a rounded corner of the frame.
