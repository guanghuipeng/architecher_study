# -*- coding: utf-8 -*-
"""
软考架构师 间隔复习调度器
用法:
  python due.py                       列出今天到期该复习的卡片 + 统计
  python due.py add "知识点" "章节"   新学完一个知识点,加入台账(明天复习)
  python due.py review <ID> pass      复习后回忆成功 -> 升级,延长下次间隔
  python due.py review <ID> fail      回忆失败 -> 降回盒0,明天再复习
  python due.py all                   列出全部卡片

台账文件: 复习台账.txt  (每行: ID|知识点|章节|学日期|上次复习|盒子|下次复习)
盒子间隔(天): [1, 3, 7, 15, 30, 60, 120]  盒0=新学 -> 盒6=掌握
规则: 每天先清"到期复习",再看是否学新内容; 到期>30条就当天只复习不学新。
"""
import sys, os, datetime
# 让控制台尽量显示中文; 同时把可读结果写到 今日复习.md (UTF-8), 用编辑器打开看, 绕开控制台乱码
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8","utf8"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
if os.name == "nt":
    try: os.system("chcp 65001 >nul 2>nul")
    except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "复习台账.txt")
TODAY_MD = os.path.join(HERE, "今日复习.md")
INTERVALS = [1, 3, 7, 15, 30, 60, 120]
TODAY = datetime.date.today()

def parse_date(s):
    if not s or s == "-": return None
    return datetime.date.fromisoformat(s.strip())

def fmt_date(d):
    return d.isoformat() if d else "-"

def load():
    if not os.path.exists(LEDGER): return []
    rows = []
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            rows.append(line.split("|"))
    return rows

def save(rows):
    with open(LEDGER, "w", encoding="utf-8") as f:
        f.write("# 格式: ID|知识点|章节|学日期|上次复习|盒子|下次复习\n")
        for r in rows:
            f.write("|".join(r) + "\n")

def next_due(box):
    return TODAY + datetime.timedelta(days=INTERVALS[min(box, len(INTERVALS)-1)])

def cmd_due():
    rows = load()
    lines = []  # 写入 今日复习.md 的可读内容
    def out(s=""):
        print(s)
        lines.append(s)
    if not rows:
        out("台账为空。学完一个知识点后用: python due.py add \"知识点\" \"章节\"")
        _write_today_md(lines); return
    due, overdue, future = [], [], []
    for r in rows:
        nd = parse_date(r[6])
        if nd is None: continue
        if nd <= TODAY: due.append(r)
        else: future.append(r)
        if nd < TODAY: overdue.append(r)
    out(f"# 今日复习清单 — {TODAY.isoformat()}")
    out("")
    out(f"**到期该复习: {len(due)} 条**（其中逾期 {len(overdue)} 条）")
    out("")
    if due:
        out("| ID | 盒 | 知识点 | 章节 | 状态 |")
        out("|---|---|---|---|---|")
        for r in sorted(due, key=lambda x: parse_date(x[6])):
            days_late = (TODAY - parse_date(r[6])).days
            tag = f"⚠逾期{days_late}天" if days_late>0 else "今日到期"
            out(f"| {r[0]} | 盒{r[5]} | {r[1]} | {r[2]} | {tag} |")
        out("")
        out("## 复习动作（每张卡先在脑中回想，再翻书/笔记确认，然后告诉我结果）")
        out("")
        for r in sorted(due, key=lambda x: parse_date(x[6])):
            out(f"- 卡片 [{r[0]}]《{r[1]}》")
            out(f"  - 想得起来 → 回我「**卡{r[0]} pass**」")
            out(f"  - 想不起来 → 回我「**卡{r[0]} fail**」")
    else:
        out("✅ 今天没有到期复习。可以学新内容（或休息）。")
    out("")
    from collections import Counter
    dist = Counter(r[5] for r in rows)
    out(f"---")
    out(f"卡片总数: {len(rows)}  |  盒子分布: " + " ".join(f"盒{b}:{dist.get(str(b),0)}" for b in range(len(INTERVALS))))
    if len(due) > 30:
        out("")
        out("⚠ 到期超过 30 条 → 今天**只复习、不学新**，先稳住存量。")
    if future:
        nxt = min(parse_date(r[6]) for r in future if parse_date(r[6]))
        out(f"下一次有卡片到期: {nxt.isoformat()}")
    out("")
    out("> 控制台若乱码，直接读本文件 `今日复习.md` 即可。")
    _write_today_md(lines)

def _write_today_md(lines):
    with open(TODAY_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def cmd_add(point, chap):
    rows = load()
    nid = str(max([int(r[0]) for r in rows] + [0]) + 1)
    rows.append([nid, point, chap, TODAY.isoformat(), "-", "0", next_due(0).isoformat()])
    save(rows)
    msg = f"✅ 已加入卡片 [{nid}] 《{point}》({chap})  下次复习: {next_due(0).isoformat()}"
    print(msg)
    with open(TODAY_MD, "a", encoding="utf-8") as f:
        f.write("\n\n" + msg + "\n")
    cmd_due()  # 刷新今日清单

def cmd_review(nid, result):
    rows = load()
    hit = False
    for r in rows:
        if r[0] == nid:
            hit = True
            box = int(r[5])
            if result == "pass":
                box = min(box + 1, len(INTERVALS)-1)
                r[5] = str(box)
                r[4] = TODAY.isoformat()
                r[6] = next_due(box).isoformat()
                msg = f"✅ [{nid}] 回忆成功 -> 盒{box}  下次复习 {r[6]}"
            else:
                r[5] = "0"
                r[4] = TODAY.isoformat()
                r[6] = next_due(0).isoformat()
                msg = f"🔁 [{nid}] 回忆失败 -> 降回盒0  明天再复习 {r[6]}"
            print(msg)
            with open(TODAY_MD, "a", encoding="utf-8") as f:
                f.write("\n\n" + msg + "\n")
    if not hit:
        print(f"找不到 ID={nid}"); return
    save(rows)
    cmd_due()  # 刷新今日清单

def cmd_all():
    rows = load()
    for r in rows:
        print(f"[{r[0]}] 盒{r[5]} {r[1]}  ({r[2]})  学:{r[3]} 复习:{r[4]} 下次:{r[6]}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args: cmd_due()
    elif args[0]=="add" and len(args)>=3: cmd_add(args[1], args[2])
    elif args[0]=="review" and len(args)>=3: cmd_review(args[1], args[2])
    elif args[0]=="all": cmd_all()
    else:
        print(__doc__)
