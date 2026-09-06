"""Bilingual message table: Simplified Chinese (default) and English.

Every user-facing string in the program lives here, as a ``(zh, en)`` pair
under a stable key.  Call sites use :func:`t`::

    t("status.reloaded", id=db.id)

The chosen language is remembered between runs in a small settings file under
the user's config folder (``%APPDATA%/roco-trail-helper/settings.json`` on
Windows), so it survives switching database folders and re-installing.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_LANG = "zh"
LANGUAGES = {"zh": "简体中文", "en": "English"}

_lang = DEFAULT_LANG


# ------------------------------------------------------------------ state
def _settings_path() -> Path:
    base = os.environ.get("APPDATA")
    if not base:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "roco-trail-helper" / "settings.json"


def load_language() -> str:
    """Adopt the language remembered from the last run (or the default)."""
    lang = None
    try:
        data = json.loads(_settings_path().read_text(encoding="utf-8"))
        if isinstance(data, dict):
            lang = data.get("language")
    except Exception:                     # missing, unreadable or corrupt file
        lang = None
    set_language(lang if lang in LANGUAGES else DEFAULT_LANG)
    return _lang


def save_language(lang: str) -> None:
    """Remember `lang` for next time; a read-only home is not worth crashing over."""
    path = _settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if path.exists():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        data["language"] = lang
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def set_language(lang: str) -> None:
    global _lang
    if lang in LANGUAGES:
        _lang = lang


def get_language() -> str:
    return _lang


def t(key: str, **kwargs) -> str:
    """The `key` message in the current language, ``.format``-ed with kwargs."""
    zh, en = STRINGS[key]
    text = zh if _lang == "zh" else en
    return text.format(**kwargs) if kwargs else text


# ---------------------------------------------------------------- strings
# Vocabulary, kept consistent throughout:
#   数据库 = database   图标 = icon        相似度 = similarity
#   突出度 = stand-out  剪贴板 = clipboard
STRINGS: dict[str, tuple[str, str]] = {
    # ---------------------------------------------------------- shell / app
    "app.title": ("洛克王国 草系徽章试炼 助手",
                  "Roco Kingdom Grass Badge Trail Helper"),
    "menu.language": ("语言 / Language", "语言 / Language"),
    "status.language_switched": ("界面语言已切换为简体中文。",
                                 "Interface language switched to English."),
    "status.ready": ("就绪。", "Ready."),

    "idle_hint": ("复制一个图标  —  Ctrl+V 查询，Ctrl+N 录入",
                  "Copy an icon  —  Ctrl+V to check it,  Ctrl+N to add it"),

    "help.text": ("""复制一个图标到剪贴板（对着一个图标截图就行，多大都可以），然后：

    Ctrl+V   查询单个图标 - 回答 Y 或 N，并显示数据库中和你的输入
             最接近的10个图标
    Ctrl+N   （批量）录入当前数据库 - 会先查一遍，
             如果数据库里已经有相似的，
             会把两个都显示出来，问你是否座位新图标添加。
             如果粘贴的是一整张网格截图会自动切成单个图标。
    Ctrl+E   编辑数据库：所有图标的缩略图，可重命名、可多选删除
    F5       从磁盘重新载入数据库
    F1       本帮助

也可通过按钮操作。

判定会给出两个数字。“相似度”是数据库中最接近的那个图标有多像；
“突出度”是它比数据库里其余图标高出多少。判定为 Y 需要两个都达到阈值，
阈值可以在右上角调 - 每个数据库分别保存。""",
                  """Copy an icon to the clipboard (any screenshot crop of one
icon, any size), then:

    Ctrl+V   check one icon  -  answers Y or N and shows the 10
             icons in the database closest to your input
    Ctrl+N   add to this database, one icon or many  -  searches
             first, and if something similar is already stored
             it shows both and asks whether to add yours as a
             new icon.
             A pasted grid screenshot is split into single icons
             automatically.
    Ctrl+E   edit the database: thumbnails of every icon, with
             rename and multi-select delete
    F5       reload the database from disk
    F1       this help

All of these are buttons as well.

The verdict shows two numbers.  "similarity" is how close the
closest icon in the database is; "stand-out" is how far it
rises above the rest of the database.  A Y needs both above
their thresholds, which you can adjust at the top right -
they are saved per database."""),

    # ------------------------------------------------------- shared buttons
    "btn.open": ("打开", "Open"),
    "btn.create": ("新建", "Create"),
    "btn.delete": ("删除", "Delete"),
    "btn.cancel": ("取消", "Cancel"),
    "btn.close": ("关闭", "Close"),
    "btn.rename": ("重命名", "Rename"),

    "common.and_more": ("\n  ……还有 {count} 个", "\n  ... and {count} more"),
    "scores": ("相似度 {sim:.3f}   突出度 {rel:.3f}",
               "similarity {sim:.3f}   stand-out {rel:.3f}"),
    "db.summary": ("数据库 {id:03d}   -   {count} 个图标",
                   "DB {id:03d}   -   {count} icon(s)"),

    # ---------------------------------------------------------- DB chooser
    "dbchooser.title": ("选择数据库", "Select icon database"),
    "dbchooser.heading": ("数据库列表", "Databases"),
    "dbchooser.new_id": ("新数据库编号：", "New database id:"),
    "dbchooser.row": ("数据库 {id:03d}    {count} 个图标", "DB {id:03d}    {count} icon(s)"),
    "dbchooser.pick_title": ("选择数据库", "Select a database"),
    "dbchooser.pick_body": ("选中一个数据库，或者新建一个。", "Pick a database, or create one."),
    "dbchooser.cannot_open": ("无法打开", "Cannot open"),
    "dbchooser.invalid_title": ("编号无效", "Invalid id"),
    "dbchooser.invalid_body": ("数据库编号必须是数字。", "The database id must be a number."),
    "dbchooser.exists_title": ("已存在", "Already exists"),
    "dbchooser.delete_title": ("删除数据库", "Delete database"),
    "dbchooser.delete_body": ("确定删除数据库 {id:03d} 以及其中的每一个图标？\n此操作无法撤销。",
                              "Delete DB {id:03d} and every icon in it?\nThis cannot be undone."),

    # ------------------------------------------------------ similar dialog
    "similar.title": ("数据库中已有相似的图标", "Similar icon already in the database"),
    "similar.headline": ("最接近的已有图标得分 {score:.3f}（{id}  {name}）。",
                         "Best existing match scores {score:.3f} ({id}  {name})."),
    "similar.sub": ("数据库里的图标应当各不相同 - 新的这个真的不一样吗？",
                    "Icons are meant to be unique - is the new one really different?"),
    "similar.new": ("新图标（剪贴板）", "New (clipboard)"),
    "similar.existing": ("已有的 {id}", "Existing {id}"),
    "similar.add": ("作为新图标添加", "Add as new icon"),
    "similar.replace": ("替换 {id}", "Replace {id}"),

    # -------------------------------------------------------- batch import
    "batch.title": ("从粘贴的整张截图导入 {count} 个图标",
                    "Import {count} icons from the pasted grid"),
    "batch.headline": ("在剪贴板图片里找到 {count} 个图标。",
                       "Found {count} icons in the clipboard image."),
    "batch.sub": ("勾选左边的图标表示把它作为新条目添加；勾选右边表示保留数据库里已有的那个，跳过你这个。",
                  "Tick the left icon to add it as a new entry, or the right one "
                  "to keep what is already stored and skip yours."),
    "batch.add_as_new": ("添加为新图标", "add as new"),
    "batch.already_in": ("数据库中已有", "already in the database"),
    "batch.looks_similar": ("与已有图标相似", "looks similar to"),
    "batch.skip_keep": ("跳过 - 保留 {id} {name}", "skip - keep {id} {name}"),
    "batch.nothing_similar": ("数据库中没有相似的", "nothing similar stored"),
    "batch.skip_this": ("跳过这个图标", "skip this icon"),
    "batch.summary": ("{add} 个待添加    {skip} 个待跳过",
                      "{add} to add    {skip} to skip"),
    "batch.summary_undecided": ("    还有 {count} 个未决定", "    {count} still undecided"),
    "batch.undecided_skip": ("未决定 -> 跳过", "Undecided -> skip"),
    "batch.undecided_add": ("未决定 -> 添加为新图标", "Undecided -> add as new"),
    "batch.import": ("导入", "Import"),
    "batch.import_n": ("导入 {count} 个图标", "Import {count} icon(s)"),
    "batch.not_a_grid": ("不是网格 - 按单个图标处理", "Not a grid - treat as one icon"),

    # -------------------------------------------------------------- editor
    "editor.title": ("编辑数据库 {id:03d}", "Edit DB {id:03d}"),
    "editor.filter": ("筛选：", "filter:"),
    "editor.shown": ("，显示 {count} 个", ", {count} shown"),
    "editor.rename_btn": ("重命名…", "Rename..."),
    "editor.delete_ticked": ("删除勾选的", "Delete ticked"),
    "editor.tick_all": ("全选", "Tick all"),
    "editor.untick_all": ("全不选", "Untick all"),
    "editor.empty": ("这个数据库里还没有图标。", "No icons here yet."),
    "editor.no_match": ("没有符合筛选条件的图标。", "Nothing matches the filter."),
    "editor.rename_one": ("恰好勾选一个图标来重命名（也可以直接双击它）。",
                          "Tick exactly one icon to rename (or double-click it)."),
    "editor.delete_pick": ("先勾选要删除的图标。", "Tick the icons you want to delete."),
    "editor.delete_title": ("删除图标", "Delete icons"),
    "editor.delete_body": ("确定从数据库 {id:03d} 删除 {count} 个图标？\n\n{names}{more}\n\n此操作无法撤销。",
                           "Delete {count} icon(s) from DB {id:03d}?\n\n{names}{more}\n\n"
                           "This cannot be undone."),

    # --------------------------------------------------------- main window
    "main.no_db": ("未选择数据库", "No database"),
    "main.switch_db": ("切换数据库…", "Switch DB..."),
    "main.open_folder": ("打开文件夹", "Open folder"),
    "main.rel_label": ("突出度 ≥", "stand-out >="),
    "main.sim_label": ("相似度 ≥", "similarity >="),
    "main.btn_check": ("查询剪贴板图标  (Ctrl+V)", "Check clipboard icon  (Ctrl+V)"),
    "main.btn_add": ("把剪贴板图标录入数据库  (Ctrl+N)", "Add clipboard icon to DB  (Ctrl+N)"),
    "main.btn_edit": ("编辑数据库  (Ctrl+E)", "Edit database  (Ctrl+E)"),
    "main.btn_help": ("快捷键  (F1)", "Shortcuts  (F1)"),
    "main.input_title": ("输入（剪贴板）", "Input (clipboard)"),
    "main.match_title": ("最接近的图标", "Best match"),
    "main.tab_candidates": ("候选", "Candidates"),
    "main.tab_all": ("全部图标", "All icons"),
    "main.reload": ("重新载入 (F5)", "Reload (F5)"),
    "main.pasted_size": ("粘贴的图片 {w}x{h} 像素", "pasted {w}x{h}px"),
    "main.score_suffix": ("   得分 {score:.3f}", "   score {score:.3f}"),
    "main.last_added": ("最后录入的图标", "last icon added"),

    "col.rank": ("名次", "Rank"),
    "col.icon": ("图标", "Icon"),
    "col.score": ("得分", "Score"),
    "col.id": ("编号", "Id"),
    "col.name": ("名称", "Name"),
    "col.added": ("录入时间", "Added"),

    # --------------------------------------------------------------- menus
    "menu.database": ("数据库", "Database"),
    "menu.switch_create": ("切换 / 新建数据库…", "Switch / create database..."),
    "menu.edit_db": ("编辑数据库（重命名 / 删除图标）…",
                     "Edit database (rename / delete icons)..."),
    "menu.open_folder": ("打开数据库文件夹", "Open database folder"),
    "menu.reload": ("从磁盘重新载入", "Reload from disk"),
    "menu.quit": ("退出", "Quit"),
    "menu.icon": ("图标", "Icon"),
    "menu.check": ("用数据库查询剪贴板里的图标", "Check clipboard icon against the database"),
    "menu.add": ("把剪贴板里的图标录入数据库", "Add clipboard icon to the database"),
    "menu.rename_selected": ("重命名选中的", "Rename selected"),
    "menu.delete_selected": ("删除选中的", "Delete selected"),
    "menu.help": ("帮助", "Help"),
    "menu.help_item": ("快捷键与工作原理", "Shortcuts and how it works"),

    # ------------------------------------------------------- rename / name
    "delete.one_body": ("确定从数据库 {dbid:03d} 移除 {id}（{name}）？",
                        "Remove {id} ({name}) from DB {dbid:03d}?"),

    "rename.title": ("重命名", "Rename"),
    "rename.prompt": ("{id} 的新名称：", "New name for {id}:"),
    "name.title": ("图标名称", "Icon name"),
    "name.prompt": ("给这个图标起个名字：", "Name for this icon:"),

    # ------------------------------------------------------------ verdicts
    "verdict.empty_db": ("N  -  数据库是空的。按 Ctrl+N 把这个图标录入。",
                         "N  -  the database is empty.  Press Ctrl+N to add this icon."),
    "verdict.yes": ("Y  -  数据库中已有：{name}      {numbers}",
                    "Y  -  already in the DB:  {name}      {numbers}"),
    "verdict.no": ("N  -  数据库中没有。按Ctrl+N 录入。      {numbers}",
                   "N  -  not in the DB.  Ctrl+N adds it.      {numbers}"),
    "verdict.similar_found": ("发现相似的图标：{name}   相似度 {sim:.3f}   突出度 {rel:.3f}",
                              "Similar icon found:  {name}   similarity {sim:.3f}   "
                              "stand-out {rel:.3f}"),
    "verdict.imported": ("已从整张截图导入 {count} 个图标",
                         "Imported {count} icon(s) from the grid"),
    "verdict.imported_skipped": ("，并按你的选择跳过 {count} 个",
                                 ", skipped {count} by your choice"),
    "verdict.stored": ("{verb}  {id}  {name}", "{verb}  {id}  {name}"),
    "verb.added": ("已录入", "Added"),
    "verb.replaced": ("已替换", "Replaced"),

    # ------------------------------------------------------------ statuses
    "status.opened_db": ("已打开数据库 {id:03d}（{count} 个图标）。   {hint}",
                         "Opened DB {id:03d} ({count} icons).   {hint}"),
    "hint.use_keys": ("Ctrl+N 录入剪贴板图标，Ctrl+V 查询。",
                      "Ctrl+N adds the clipboard icon, Ctrl+V checks one."),
    "hint.empty_db": ("这个数据库是空的 - 复制一个图标，按 Ctrl+N 录入。",
                      "This database is empty - copy an icon and press Ctrl+N to add it."),
    "status.reloaded": ("已重新载入数据库 {id:03d}。", "Reloaded DB {id:03d}."),
    "status.thresholds": ("现在判定为 Y 需要相似度 ≥ {sim:.2f} 且突出度 ≥ {rel:.2f}。",
                          "Verdict now needs similarity >= {sim:.2f} and "
                          "stand-out >= {rel:.2f}."),
    "status.matching": ("查询中…", "Matching..."),
    "status.empty_db": ("还没有可以比对的图标 - 先用 Ctrl+N 录入几个。",
                        "Nothing to compare against yet - add icons with Ctrl+N first."),
    "status.best": ("最接近 {id} {name} {sim:.3f}{runner_up}   （数据库中位数 {median:.3f}）",
                    "Best {id} {name} {sim:.3f}{runner_up}   (DB median {median:.3f})"),
    "status.runner_up": ("   次接近 {score:.3f}", "   next best {score:.3f}"),
    "status.looking": ("正在寻找图标…", "Looking for icons..."),
    "status.found_checking": ("找到 {count} 个图标 - 正在逐个与数据库比对…",
                              "Found {count} icons - checking each against the database..."),
    "status.import_cancelled": ("已取消导入。", "Import cancelled."),
    "status.db_now_holds": ("数据库 {id:03d} 现在有 {count} 个图标。",
                            "DB {id:03d} now holds {count} icons."),
    "status.checking_dups": ("正在检查是否重复…", "Checking for duplicates..."),
    "status.add_cancelled": ("已取消录入。", "Add cancelled."),
    "status.stored": ("{verb} {id}，数据库 {dbid:03d} 现有 {count} 个图标。",
                      "{verb} {id} in DB {dbid:03d} ({count} icons)."),
    "status.renamed": ("已把 {id} 重命名为 {name}。", "Renamed {id} to {name}."),
    "status.deleted_one": ("已删除 {id}。", "Deleted {id}."),
    "status.deleted_n": ("已从数据库 {id:03d} 删除 {count} 个图标。",
                         "Deleted {count} icon(s) from DB {id:03d}."),

    # -------------------------------------------------------------- import
    "import.title": ("导入", "Import"),
    "import.body": ("已向数据库 {id:03d} 录入 {count} 个图标。{detail}",
                    "Added {count} icon(s) to DB {id:03d}.{detail}"),
    "import.detail": ("\n\n按你的选择跳过了 {count} 个：\n{lines}{more}",
                      "\n\nSkipped {count} by your choice:\n{lines}{more}"),
    "import.kept": ("  保留 {id} {name}", "  kept {id} {name}"),
    "import.skipped_nothing": ("  已跳过（数据库中没有相似的）",
                               "  skipped (nothing similar stored)"),

    # ----------------------------------------------------------- clipboard
    "clip.no_image_title": ("剪贴板里没有图片", "No image on the clipboard"),
    "clip.read_failed": ("读不到剪贴板：{error}", "could not read the clipboard: {error}"),
    "clip.files_no_image": ("剪贴板里是文件，但其中没有一个是图片。",
                            "the clipboard holds files, but none of them is an image"),
    "clip.no_image": ("剪贴板里没有图片。", "the clipboard does not contain an image"),

    # ------------------------------------------------------------ database
    "db.exists": ("数据库 {id} 已经存在：{path}", "database {id} already exists at {path}"),
    "db.not_found": ("{root} 下没有编号为 {id} 的数据库", "no database {id} under {root}"),

    # ----------------------------------------------------------------- CLI
    "cli.desc": ("命令行版本：用图片文件代替剪贴板。\n\n"
                 "    python -m iconmatch.cli list\n"
                 "    python -m iconmatch.cli match --db 1 shot.png\n"
                 "    python -m iconmatch.cli add   --db 1 shot.png --name 小火猴\n"
                 "    python -m iconmatch.cli add   --db 1 grid.png     # 自动切分网格\n"
                 "    python -m iconmatch.cli remove --db 1 0003",
                 "Headless companion to the GUI: work with image files instead of "
                 "the clipboard.\n\n"
                 "    python -m iconmatch.cli list\n"
                 "    python -m iconmatch.cli match --db 1 shot.png\n"
                 "    python -m iconmatch.cli add   --db 1 shot.png --name Pikachu\n"
                 "    python -m iconmatch.cli add   --db 1 grid.png   # split automatically\n"
                 "    python -m iconmatch.cli remove --db 1 0003"),
    "cli.help.root": ("数据库所在的文件夹", "database root folder"),
    "cli.help.lang": ("界面语言：zh（简体中文）或 en（English）",
                      "interface language: zh (Simplified Chinese) or en (English)"),
    "cli.help.list": ("列出所有数据库", "list databases"),
    "cli.help.match": ("用数据库查询图片文件", "match image files against a database"),
    "cli.help.add": ("把图片文件录入数据库", "add image files to a database"),
    "cli.help.remove": ("按编号删除一个图标", "remove an icon by id"),
    "cli.help.name": ("只在单个文件时有意义", "only meaningful with a single file"),
    "cli.help.create": ("数据库不存在时自动新建", "create the database if missing"),
    "cli.help.force": ("即使已有相似图标也照样录入", "add even if a similar icon exists"),
    "cli.help.no_split": ("把每个文件都当成单个图标，不自动切分网格",
                          "treat each file as one icon instead of auto-splitting a grid"),
    "cli.no_dbs": ("{root} 下没有数据库", "no databases under {root}"),
    "cli.db_row": ("数据库 {id:03d}  {count} 个图标", "DB {id:03d}  {count} icon(s)"),
    "cli.no_db": ("{root} 下没有编号为 {id} 的数据库（加 --create 可以新建）",
                  "no database {id} under {root} (use --create)"),
    "cli.match_empty": ("{file}: N（数据库是空的）", "{file}: N (database is empty)"),
    "cli.match_row": ("{file}: {verdict}  最接近={id} {name} 相似度={sim:.3f} "
                      "突出度={rel:.3f}   {extra}",
                      "{file}: {verdict}  best={id} {name} sim={sim:.3f} "
                      "standout={rel:.3f}   {extra}"),
    "cli.grid": ("{file}: 网格，共 {count} 个图标", "{file}: grid of {count} icons"),
    "cli.skipped": ("  {name}: 已跳过 - 与 {id} {best} 太相似"
                    "（相似度={sim:.3f} 突出度={rel:.3f}）；要照样录入就加 --force",
                    "  {name}: SKIPPED - too similar to {id} {best} "
                    "(sim={sim:.3f} standout={rel:.3f}); use --force to add anyway"),
    "cli.added": ("  {name}: 已录入为 {id} {stored}", "  {name}: added as {id} {stored}"),
    "cli.removed": ("已删除 {id}", "removed {id}"),

    # ---------------------------------------------------------- entry point
    "main.help.root": ("存放 db_XXX 数据库文件夹的目录",
                       "folder that holds the db_XXX directories"),
}
