# Icon Matcher

Keeps numbered databases of game icons (Roco Kingdom style avatars: a creature
on a dark disc, on the game's beige background) and answers one question about
an icon on your clipboard: **is this one already in the database?**

The answer is a Y/N plus two numbers, and the input and the best match are
always shown side by side so you can check the call yourself.

## Running it

```powershell
.\run.ps1
```

That builds `.venv` on first use (and repairs it if a package went missing),
then starts the GUI with no console window, with the databases in `.\data`.
`Get-Help .\run.ps1 -Full` documents it; the parameters are:

| parameter | what it does |
| --- | --- |
| `-Root <path>` | use a different folder of databases; it is created if missing |
| `-Console` | start via `python.exe` so a console window shows any error |
| `-Log <file>` | send output to `<file>` and errors to `<file>.err` |
| `-Wait` | block until the app closes and return its exit code |
| `-Reinstall` | delete and rebuild the virtualenv, then start |
| `-SkipChecks` | skip the venv/dependency checks for a slightly faster start |

```powershell
.\run.ps1 -Root D:\icons\roco
```

```powershell
.\run.ps1 -Console -Log .\im.log
```

Equivalent manual form:

```bash
.venv/Scripts/python.exe main.py
```

On startup you pick a database (or create one by numeric id). Then:

| action | how |
| --- | --- |
| check the clipboard icon against the DB | `Ctrl+V` (or `Ctrl+M`, the button, or **Icon** menu) |
| add the clipboard icon to the DB | `Ctrl+N` (or the button, or **Icon** menu) |
| add a whole grid screenshot at once | `Ctrl+N` - grids are split and reviewed row by row |
| rename / delete icons, browse thumbnails | `Ctrl+E` (or the button, or **Database** menu) |
| shortcuts / how it works | `F1` (or **Help** menu) |
| reload from disk | `F5` |
| rename / delete an entry | select it in the list, use the buttons or **Icon** menu |
| switch or create a database | **Switch DB...**, or the **Database** menu |

The two clipboard actions and **Edit database** are always reachable three ways
- the buttons above the status bar, the menus (which show the shortcuts next to
them), and the keys. When a check comes back N, the banner itself says `Ctrl+N adds it`.

Adding always runs a search first. If something similar is already stored, both
icons are shown and you choose: *add as new*, *replace the existing one*, or
*cancel*.

### Adding a whole screenshot at once

`Ctrl+N` looks at what you pasted. A single icon goes through the flow above; an
image holding a **grid** of icons is split into one crop per icon and opens a
conflict-resolution list instead. Each row is a choice between two icons:

* **left** - the icon you pasted, with an editable name. Tick it to add it as a
  new entry.
* **right** - whatever the database already holds that looks like it, with the
  similarity and stand-out scores. Tick it to keep the stored one and skip yours.

Rows where nothing similar was found default to *add*; rows with a possible
match start **undecided** and are highlighted. The program never resolves those
for you - the **Import** button stays disabled while any row is undecided, and a
running count shows how many will be added, skipped, and still need an answer.
*Undecided -> add as new* and *Undecided -> skip* settle the rest in one click
when you do want a bulk answer. Whatever you tick is what happens; nothing is
re-judged afterwards.

The grid may be any size, rows need not be full, and cells need not be perfectly
aligned; if the split ever misfires on a single icon, **Not a grid - treat as
one icon** falls back.

The same happens in the CLI: `add` splits grid screenshots automatically, and
`--no-split` turns that off.

### Editing a database

`Ctrl+E` (or the **Edit database** button) opens the editor: every
icon as a thumbnail, a filter box for names and ids, tick boxes for multi-select
delete, and rename via the button or a double-click. Changes are written
immediately and the main window follows along.

### Without the GUI

```bash
.venv/Scripts/python.exe -m iconmatch.cli list
.venv/Scripts/python.exe -m iconmatch.cli add   --db 1 --create shots/*.png
.venv/Scripts/python.exe -m iconmatch.cli match --db 1 shot.png
.venv/Scripts/python.exe -m iconmatch.cli remove --db 1 0007
```

Same database files, same decisions; `add` refuses near-duplicates unless you
pass `--force`.

## On disk

```
data/db_001/index.json      metadata, thresholds, the icon list
data/db_001/norm/0001.png   normalised 128x128 RGBA tile - what matching uses
data/db_001/raw/0001.png    exactly what you pasted, kept for reference
```

Databases are independent; `--root` (CLI) or `main.py --root` (GUI) points at a
different collection of them.

## How a match is decided

**1. Normalise** (`iconmatch/imaging.py`). The background colour is measured
from the border of the pasted image, everything far enough from it becomes
foreground, and the largest connected blob is the icon. The crop is then framed
on the blob's **centroid** and sized from its **area**, not its bounding box —
a screenshot that clips an ear or a tail moves the bounding box a lot but the
area and centroid barely at all. Output is a 128x128 RGBA tile: alpha marks the
icon, and the background is flattened to one fixed colour so background texture
cannot influence anything. Nothing keys off the black disc, so icons whose
horns, wings or tails break out of it are handled the same way.

**2. Describe** (`iconmatch/features.py`). Four blocks, each L2-normalised and
weighted: coarse colour layout (28x28 RGB), colour histogram over the icon
pixels only (HSV 12x4x4), a DCT perceptual hash, and the silhouette. They are
concatenated so that one dot product yields the whole score, and the query is
described at 27 slightly different scales/offsets, taking the best - that is
what absorbs differences in how tightly you cropped.

**3. Decide** (`iconmatch/database.py`). Two numbers:

* **similarity** - the raw score of the best candidate, 0..1.
* **stand-out** - how far that candidate rises above the median of the rest of
  the database, `(best - median) / (1 - median)`.

A verdict of **Y** needs both to clear their thresholds. Similarity on its own
is not enough: every icon in this game shares a dark disc on the same
background, so as a database grows, *all* similarities drift upwards together
and any fixed similarity threshold slowly stops meaning anything. Stand-out is
scale free and holds one operating point from 14 icons to 250 (numbers below).

### Thresholds

Defaults live in `iconmatch/config.py` and are copied into each database's
`index.json`, where they can be edited per database:

| key | default | meaning |
| --- | --- | --- |
| `match_sim` | 0.80 | similarity needed for a Y |
| `match_rel` | 0.70 | stand-out needed for a Y |
| `dup_sim` | 0.78 | similarity that triggers the "similar icon" dialog when adding |
| `dup_rel` | 0.55 | stand-out that triggers it |

The GUI edits `match_sim` and `match_rel` directly (top right) and saves them to
the open database. The duplicate pair is deliberately looser than the match
pair: being asked about an icon that turns out to be new costs a click, a
duplicate in the database costs more.

Below `MIN_ICONS_FOR_REL` (4) icons the median is meaningless, so stand-out is
reported as 1.0 and only similarity gates the verdict.

## Tests

```bash
.venv/Scripts/python.exe tests/test_pipeline.py     # synthetic icons, self-contained
.venv/Scripts/python.exe tests/test_real_icons.py   # real avatar screenshot, if present
.venv/Scripts/python.exe tests/bench_scale.py       # 250-icon stress test, if artwork present
.venv/Scripts/python.exe tests/test_grid_split.py   # grid detection, real + synthetic
```

`test_grid_split.py` checks that a real 3x6 screenshot splits into exactly 18
icons which then all match themselves back out of the database, that synthetic
sheets of 2x3, 4x7, 5x6, 3x5 and 1x4 (including a partial last row) split into
the right counts, and that a single icon is *not* mistaken for a grid.

Each query is scored twice: once as-is (the icon **is** in the database, the app
must say Y) and once with that icon dropped and the rest rescored (the icon is
**absent**, the app must say N).

| set | icons | ranking | said Y when present | said N when absent |
| --- | --- | --- | --- | --- |
| synthetic (shared frame, eyes, mouth) | 14 | 56/56 | 56/56 | 56/56 |
| real avatar screenshot | 18 | 108/108 | 108/108 | 108/108 |
| composed artwork, near-duplicates | 250 | 500/500 | 500/500 | 394/500 |

The 250-icon set is built by compositing the game's creature artwork onto an
*identical* disc, which both removes the framing variety of real screenshots and
includes genuine near-duplicates (evolutions and recolours of the same
creature). Those 106 cases are icons that really do look almost the same as
another one; no threshold separates them, which is why adding shows you both
images and asks. Ranking stays perfect throughout - the correct icon is always
first when it is present.

The two-number rule is what makes that table hold at both ends. Judging on raw
similarity alone, the best possible threshold is a different number for each
set - 0.94, 0.93, 0.97 - and one fixed value tuned on the small sets mislabels
304 of the 500 absent cases at 250 icons. The same fixed stand-out threshold of
0.70 works for all three.

The real-icon tests read a screenshot from the sibling `rocom_spirits` project
and skip cleanly (exit 0) if it is not there. Point them elsewhere with
`python tests/test_real_icons.py path/to/grid.png --rows 3 --cols 6`.

## Limits

* A crop that cuts *into* the icon (losing a horn or half the body) can drop
  similarity below the threshold. Include the whole icon plus a little
  background; anything from ~50px upwards works.
* Two icons that genuinely look nearly identical will score high against each
  other. That is a display-and-ask situation, not a threshold problem.
* Everything is per-database: thresholds, ids and names do not carry across.
