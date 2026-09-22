# hvb

Matplotlib house style: a packaged mplstyle plus helpers for a squircle axes
frame, rounded bar/histogram/boxplot/violin/errorbar styling, and a set of
categorical palettes.

```
pip install git+https://github.com/AlexanderBeach/hvb
```

```python
import matplotlib.pyplot as plt
import hvb

hvb.use(scale=0.6)          # or hvb.use(scale=0.6, dark=True)

fig, ax = plt.subplots()
ax.plot(x, y)
fig.savefig("figure.pdf")   # styling is applied on save
```

## Palettes

| name | use |
|---|---|
| `default` | data lines on white |
| `muted` | context series behind the primary lines |
| `fill` | fills and confidence bands |
| `dark` | data lines on a dark background (#141414) |
| `dark2`, `viridis` | colormap samplings |

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

All four categorical palettes share the same eight hues, so a colour means the
same series in any register. `muted` and `fill` are low-contrast
and are not meant to carry category identity on their own.

`hvb.use(palette="muted")` sets the colour cycle; `hvb.get_hvb_palette("fill")`
returns the colours as RGB tuples.

## Helpers

`use(...)` applies everything globally and finishes figures on save. `scale`
shrinks frame, tick and line weights together; `text=True` scales fonts with
them; `dark=True` switches to the dark background and palette.

For finer control: `finish_hvb(ax, ...)` applies the frame, legend, bar and
errorbar styling and `finish_hvb_figure(fig, ...)` does it for every axes;
`scale_rc()` and `dark_rc()` return the rcParams dicts that `use()` applies, for
layering under `plt.style.context`; `ticks_on_flat_faces(ax)` hides ticks that
would fall on a rounded corner.
