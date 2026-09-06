# 洛克王国 · 草系徽章之旅 助手
## Roco Kingdom Grass Badge Trail Helper

> 把精灵头像截图粘进来，立刻告诉你**这只你打过没有**。
> Paste a spirit's icon and it tells you **whether you have battled it before**.

**[简体中文](#简体中文) · [English](#english)**

![界面截图](docs/screenshot-zh.png)

---

<a id="简体中文"></a>

# 简体中文

## 这个工具解决什么问题

草系徽章之旅里，**每个等级段第一次和某只精灵对战都会给奖励**——但游戏界面
不会告诉你这只精灵你之前打没打过。等级段一多，精灵一多，就只能靠脑子记，
很容易漏掉本来能拿的奖励，或者把时间浪费在已经打过的精灵身上。

这个小程序替你记：

* **一秒查询** —— 截图复制精灵头像，按 `Ctrl+V`，界面直接回答 **Y（打过了）**
  或 **N（没打过）**，并把你的截图和图鉴中最像的那个并排放出来，你自己也能一眼核对。
* **批量登记** —— 已经打过一大堆？把整屏的精灵列表截一张图，`Ctrl+N` 一次性
  全部登记进去，程序会自动把网格切成一个一个的图标。
* **一个等级段一个图鉴** —— 图鉴之间互不干扰，切换只要一下。

截图多大、裁得松一点紧一点都没关系：程序会自己找到图标、对齐、缩放再比对。
一张 50 像素的小裁图和一张 220 像素的大裁图会得到同样的答案。

## 怎么用

### 一、下载现成的程序（推荐）

到 [Releases](../../releases) 下载 `RocoKingdomTrailHelper.exe`，双击就能用，
不需要装 Python。

> Windows 会对没有数字签名的程序弹一个 SmartScreen 提示：点“更多信息”→
> “仍要运行”。图鉴会存在 exe 旁边的 `data` 文件夹里，所以建议把 exe 放在一个
> 固定的文件夹里，别放在下载目录随手一丢。

### 二、从源码运行

需要 Windows + Python 3.10 以上。

```powershell
.\run.ps1
```

第一次运行会自动建好 `.venv` 并装依赖（numpy 和 pillow），之后直接启动界面。
`Get-Help .\run.ps1 -Full` 有完整说明，常用参数：

| 参数 | 作用 |
| --- | --- |
| `-Lang zh\|en` | 指定界面语言（默认简体中文，程序里也能随时切换） |
| `-Root <路径>` | 换一个存放图鉴的文件夹，不存在会自动创建 |
| `-Console` | 用 `python.exe` 启动，保留控制台窗口，方便看报错 |
| `-Log <文件>` | 把输出写进文件，错误写进 `<文件>.err` |
| `-Wait` | 等程序关闭后再返回，并带回退出码 |
| `-Reinstall` | 删掉虚拟环境重装一遍再启动 |
| `-SkipChecks` | 跳过环境检查，启动快一两秒 |

### 三、日常操作

启动后先选一个图鉴，或者填个数字新建一个（**建议一个等级段用一个图鉴**）。然后：

| 想做什么 | 怎么做 |
| --- | --- |
| 查这只打过没有 | 截图复制头像 → `Ctrl+V` |
| 把这只登记进去 | `Ctrl+N` |
| 批量登记一整屏 | 截整个列表 → `Ctrl+N`，自动切分后逐行确认 |
| 改名字 / 删图标 / 看缩略图 | `Ctrl+E` |
| 从磁盘重新载入 | `F5` |
| 快捷键和说明 | `F1` |
| 切换语言 | 菜单栏 **语言 / Language** |

这些操作在窗口下方都有按钮，菜单里也都有——不用背快捷键。

### 批量登记是怎么回事

`Ctrl+N` 会先看你粘贴的是什么。如果是**一整张网格截图**，程序会切成一个一个
图标，然后开一个确认列表，每一行让你二选一：

* **左边**是你截的图标，可以直接改名字。勾左边 = 作为新条目登记。
* **右边**是图鉴里已经有的、跟它很像的那个，附相似度和领先度。勾右边 =
  保留已有的，跳过你这个。

没找到相似图标的行默认勾“登记”；**有可能重复的行默认不选，并高亮**——
程序不会替你做主。只要还有一行没决定，“导入”按钮就一直是灰的，底下还有个
计数告诉你还剩几行。想省事就用“未决定 → 全部登记”或“未决定 → 全部跳过”。

网格几行几列都行，最后一行不满也行，格子稍微歪一点也行。万一把单个图标误判成
网格，点“不是网格 - 按单个图标处理”就回到单张流程。

### 判定结果怎么看

绿条 **Y** 表示打过了，红条 **N** 表示没打过。后面跟着两个数字：

* **相似度** —— 图鉴里最像的那个图标有多像（0~1）。
* **领先度** —— 它比图鉴里其余图标高出多少。

判定为 Y 需要两个都达到阈值，阈值在右上角可以调，**每个图鉴单独保存**。
为什么要两个数字？因为这个游戏的头像都是“深色圆盘 + 同样的背景”，图鉴越大，
所有图标的相似度就一起往上飘，单看相似度早晚会失灵；领先度不受规模影响，
从 14 个图标到 250 个图标都是同一个阈值。

### 文件都在哪

```
data/db_001/index.json      图鉴信息、阈值、图标清单
data/db_001/norm/0001.png   归一化后的 128x128 图块（比对用的就是它）
data/db_001/raw/0001.png    你当初粘贴的原图，留个底
```

界面语言记在 `%APPDATA%\roco-trail-helper\settings.json`，跟图鉴分开存，
换图鉴文件夹也不会丢。

### 不用图形界面

```powershell
.venv\Scripts\python.exe -m iconmatch.cli list
.venv\Scripts\python.exe -m iconmatch.cli add   --db 1 --create shots\*.png
.venv\Scripts\python.exe -m iconmatch.cli match --db 1 shot.png
.venv\Scripts\python.exe -m iconmatch.cli remove --db 1 0007
```

同样的图鉴文件、同样的判定规则；`add` 遇到疑似重复会跳过，`--force` 可以强行
录入，`--lang en` 切换输出语言。

### 已知的边界

* 裁图**切进图标里面**（少了角、尾巴）可能会让相似度掉到阈值以下。把整只精灵
  连同一点背景一起截进去就好，50 像素往上都行。
* 两只本来就长得几乎一样的精灵（同一只的进化型或者换色）会互相打高分。这时候
  程序会把两张图都摆出来问你——这是设计如此，不是阈值能解决的问题。
* 阈值、编号、名字都是每个图鉴各自独立的，不会跨图鉴共享。

---

<a id="english"></a>

# English

![Screenshot](docs/screenshot-en.png)

## What this solves

On the grass badge trail, **the first battle against a given spirit at each
level pays a reward** — but the game's UI never tells you whether you have
already fought that one. With enough levels and enough spirits, you are left
remembering it yourself: easy to miss a reward you could have had, easy to waste
a fight on a spirit that no longer pays.

This program remembers for you:

* **Check in one second** — copy a spirit's icon (any screenshot crop), press
  `Ctrl+V`, and the banner answers **Y (already fought)** or **N (new)**, with
  your crop and the closest stored icon side by side so you can judge it yourself.
* **Register in bulk** — already fought dozens? Screenshot the whole list and
  press `Ctrl+N`: the grid is split into individual icons and registered in one go.
* **One database per level** — databases are independent and switching is one click.

Crop size and tightness do not matter: the program finds the icon, centres it and
rescales it before comparing. A 50-pixel crop and a 220-pixel one give the same answer.

## Using it

### 1. Download the built program (recommended)

Grab `RocoKingdomTrailHelper.exe` from [Releases](../../releases) and run it — no
Python needed.

> Windows shows a SmartScreen prompt for unsigned programs: click *More info* →
> *Run anyway*. Databases are kept in a `data` folder next to the exe, so put the
> exe somewhere permanent rather than leaving it in Downloads.

### 2. Run from source

Windows plus Python 3.10 or newer.

```powershell
.\run.ps1
```

The first run builds `.venv` and installs the dependencies (numpy and pillow),
then starts the GUI. `Get-Help .\run.ps1 -Full` documents everything; the useful
parameters are:

| parameter | what it does |
| --- | --- |
| `-Lang zh\|en` | interface language (Simplified Chinese by default; switchable in-app) |
| `-Root <path>` | use a different folder of databases; created if missing |
| `-Console` | start via `python.exe` so a console window shows any error |
| `-Log <file>` | send output to `<file>` and errors to `<file>.err` |
| `-Wait` | block until the app closes and return its exit code |
| `-Reinstall` | delete and rebuild the virtualenv, then start |
| `-SkipChecks` | skip the environment checks for a slightly faster start |

### 3. Everyday use

On startup, pick a database or create one by number (**one database per level**
works well). Then:

| what you want | how |
| --- | --- |
| check whether you fought this one | copy the icon → `Ctrl+V` |
| register this one | `Ctrl+N` |
| register a whole screen at once | screenshot the list → `Ctrl+N`, then confirm row by row |
| rename / delete / browse thumbnails | `Ctrl+E` |
| reload from disk | `F5` |
| shortcuts and how it works | `F1` |
| switch language | the **语言 / Language** menu |

All of these are also buttons along the bottom of the window and entries in the
menus — no need to memorise the keys.

### How bulk registering works

`Ctrl+N` looks at what you pasted. A **grid screenshot** is split into one crop
per icon and opens a confirmation list where every row is a choice between two icons:

* **left** — the icon you pasted, with an editable name. Tick it to register it
  as a new entry.
* **right** — whatever the database already holds that looks like it, with the
  similarity and stand-out scores. Tick it to keep the stored one and skip yours.

Rows where nothing similar was found default to *register*; rows that might be
duplicates start **undecided and highlighted** — the program never resolves those
for you. The Import button stays disabled while any row is undecided, and a
running count shows how many are left. *Undecided → register all* and
*Undecided → skip all* settle the rest in one click.

The grid may be any size, the last row need not be full, and cells need not be
perfectly aligned. If a single icon is ever mistaken for a grid, **Not a grid —
treat as one icon** falls back to the single-icon flow.

### Reading the verdict

A green **Y** means you have fought it; a red **N** means you have not. Two
numbers follow:

* **similarity** — how close the best stored icon is (0–1).
* **stand-out** — how far that icon rises above the rest of the database.

A Y needs both above their thresholds, adjustable at the top right and **saved
per database**. Why two numbers? Every icon in this game is a dark disc on the
same background, so as a database grows *all* similarities drift upwards together
and any fixed similarity threshold slowly stops meaning anything. Stand-out is
scale free: one threshold holds from 14 icons to 250.

### Where the files live

```
data/db_001/index.json      metadata, thresholds, the icon list
data/db_001/norm/0001.png   normalised 128x128 tile - what matching uses
data/db_001/raw/0001.png    exactly what you pasted, kept for reference
```

The interface language is remembered in `%APPDATA%\roco-trail-helper\settings.json`,
separately from the databases, so it survives switching database folders.

### Without the GUI

```powershell
.venv\Scripts\python.exe -m iconmatch.cli list
.venv\Scripts\python.exe -m iconmatch.cli add   --db 1 --create shots\*.png
.venv\Scripts\python.exe -m iconmatch.cli match --db 1 shot.png
.venv\Scripts\python.exe -m iconmatch.cli remove --db 1 0007
```

Same database files, same decisions; `add` refuses near-duplicates unless you pass
`--force`, and `--lang zh|en` switches the output language.

### Limits

* A crop that cuts *into* the icon (losing a horn or half the body) can drop
  similarity below the threshold. Include the whole spirit plus a little
  background; anything from ~50px upwards works.
* Two spirits that genuinely look nearly identical (an evolution or a recolour)
  will score high against each other. The program shows you both and asks — that
  is by design, not a threshold problem.
* Thresholds, ids and names are per database and never carry across.

---

<a id="技术细节--how-it-works"></a>

# 技术细节 / How matching works

**1. 归一化 / Normalise** (`iconmatch/imaging.py`) — 从图片边缘量出背景色，离
背景足够远的像素算作前景，最大的连通块就是图标；按它的**质心**取框、按**面积**
定大小（而不是外接矩形——截图裁掉一只耳朵会让外接矩形大变，质心和面积几乎不动），
输出 128x128 RGBA 图块，背景统一刷成一个固定颜色。

The background colour is measured from the border, the largest connected blob is
the icon, and the crop is framed on the blob's **centroid** and sized from its
**area** rather than its bounding box — a crop that clips an ear moves the
bounding box a lot but the area and centroid barely at all. Nothing keys off the
dark disc, so icons whose horns or wings break out of it work the same way.

**2. 描述 / Describe** (`iconmatch/features.py`) — 四块特征各自 L2 归一化后加权
拼接：粗颜色布局 (28x28 RGB, 0.30)、只在图标像素上的颜色直方图 (HSV 12x4x4, 0.35)、
DCT 感知哈希 (0.15)、轮廓 (0.20)。查询图会在 27 种略微不同的缩放/偏移下描述并取
最好的一个——这就是它能吃下不同裁剪松紧的原因。

Four blocks, each L2-normalised and weighted, concatenated so one dot product
gives the whole score; the query is described at 27 slightly different
scales/offsets and the best is taken.

**3. 判定 / Decide** (`iconmatch/database.py`) — 相似度 = 最佳候选的原始得分；
领先度 = `(best - median) / (1 - median)`。两个都过阈值才是 Y。

| 键 key | 默认 default | 含义 meaning |
| --- | --- | --- |
| `match_sim` | 0.80 | 判 Y 需要的相似度 / similarity needed for a Y |
| `match_rel` | 0.70 | 判 Y 需要的领先度 / stand-out needed for a Y |
| `dup_sim` | 0.78 | 录入时触发“相似”提示的相似度 / triggers the duplicate dialog |
| `dup_rel` | 0.55 | 录入时触发“相似”提示的领先度 / same, stand-out |

默认值在 `iconmatch/config.py`，会复制进每个图鉴的 `index.json`，之后按图鉴各改
各的。重复提示的一对故意比判定的一对松：多问一次只是多点一下鼠标，图鉴里混进
重复项的代价更大。图标少于 4 个时中位数没有意义，此时领先度记作 1.0，只看相似度。

Defaults live in `iconmatch/config.py` and are copied into each database's
`index.json`. The duplicate pair is deliberately looser than the match pair:
being asked about an icon that turns out to be new costs a click, a duplicate in
the database costs more. Below 4 icons the median is meaningless, so stand-out is
reported as 1.0 and only similarity gates the verdict.

## 测试 / Tests

```powershell
.venv\Scripts\python.exe tests\test_pipeline.py     # 合成图标，自带数据 / synthetic, self-contained
.venv\Scripts\python.exe tests\test_real_icons.py   # 真实截图（有才跑）/ real screenshot, if present
.venv\Scripts\python.exe tests\bench_scale.py       # 250 图标压力测试 / 250-icon stress test
.venv\Scripts\python.exe tests\test_grid_split.py   # 网格切分 / grid detection
```

每个查询都测两遍：图标**在**图鉴里时必须答 Y，把它从图鉴里去掉重新打分后必须答 N。
Each query is scored twice: once with the icon in the database (must say Y) and
once with it dropped and the rest rescored (must say N).

| 数据集 set | 图标数 icons | 排名 ranking | 在库时答 Y | 不在库时答 N |
| --- | --- | --- | --- | --- |
| 合成（同框同眼同嘴）synthetic | 14 | 56/56 | 56/56 | 56/56 |
| 真实截图 real screenshot | 18 | 108/108 | 108/108 | 108/108 |
| 合成美术图，含近似重复 near-duplicates | 250 | 500/500 | 500/500 | 394/500 |

250 个的那组是把游戏原画贴到**完全相同**的圆盘上合成的，既去掉了真实截图的取景
差异，又塞进了大量真正的近似重复（同一只的进化型和换色）。那 106 个失败案例就是
本来就长得几乎一样的图标，没有任何阈值能分开——所以录入时程序会把两张图摆出来问你。
排名始终是满分：正确的那个图标只要在库里，就一定排第一。

The two-number rule is what makes that table hold at both ends. Judging on raw
similarity alone, the best possible threshold is a different number for each set
— 0.94, 0.93, 0.97 — and one fixed value tuned on the small sets mislabels 304 of
the 500 absent cases at 250 icons. The same fixed stand-out threshold of 0.70
works for all three.

`test_grid_split.py` checks that a real 3x6 screenshot splits into exactly 18
icons which all match themselves back out of the database, that synthetic sheets
of 2x3, 4x7, 5x6, 3x5 and 1x4 (including a partial last row) split into the right
counts, and that a single icon is *not* mistaken for a grid. The real-icon tests
read a screenshot from a sibling project and skip cleanly (exit 0) if it is not
there; point them elsewhere with
`python tests\test_real_icons.py path\to\grid.png --rows 3 --cols 6`.

## 许可 / License

MIT — 见 [LICENSE](LICENSE)。 / MIT, see [LICENSE](LICENSE).
