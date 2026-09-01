# -*- coding: utf-8 -*-
"""
把「单个大 markdown」按某级标题拆成多个文件（用于教材知识库分章）。

用法:
  python split_md.py <输入.md> <输出目录> <标题级别#> <文件前缀-模式>

例(按 ### 小时拆):
  python split_md.py "32小时通关-文本版.md" 教材知识库/02-32小时通关 3 "第{idx}小时-{title}"

命名规则:
  从标题里抓「第 N 章/小时/篇」→ {idx} 用两位补零,{title} 为后半段标题(去空格)。
  若标题无「第N章」格式,则用完整标题做文件名。
  每个文件头部保留父级标题(上一级)作为副标题,并标注原书页码范围。
"""
import sys, os, re

def main():
    if len(sys.argv) < 5:
        print(__doc__); sys.exit(1)
    src, outdir, level, pat = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    os.makedirs(outdir, exist_ok=True)

    text = open(src, encoding='utf-8').read()
    lines = text.split('\n')

    # 定位所有标题行: (行号, 级别, 文本)
    heads = []
    for i, ln in enumerate(lines):
        m = re.match(r'^(#{1,6}) (.*)$', ln)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))

    # 找目标级别的标题及其父级
    split_pts = []  # (起始行号, 结束行号, 标题, 父标题)
    parent = ''
    for k, (ln, lv, t) in enumerate(heads):
        if lv < level:
            parent = t
        elif lv == level:
            split_pts.append([ln, None, t, parent])
    for i in range(len(split_pts)):
        split_pts[i][1] = split_pts[i+1][0] if i+1 < len(split_pts) else len(lines)

    def fname(t):
        m = re.match(r'第\s*(\d+)\s*(章|小时|篇|讲|节)\s*(.*)', t)
        if m:
            idx = int(m.group(1)); rest = re.sub(r'\s+', '', m.group(3))
            base = pat.replace('{idx}', f'{idx:02d}').replace('{title}', rest or m.group(2))
            return base if base.endswith('.md') else base + '.md'
        safe = re.sub(r'[\\/:*?"<>|]', '', t).strip()
        return safe + '.md'

    book = heads[0][2] if heads else ''
    written = []
    for start, end, t, parent in split_pts:
        body = '\n'.join(lines[start:end]).strip()
        fn = fname(t)
        header = f'# {t}\n'
        if parent:
            header += f'\n> 所属：{parent}\n'
        body = re.sub(r'^#+ .*\n', '', body, count=1)  # 去掉文件内重复的该标题
        with open(os.path.join(outdir, fn), 'w', encoding='utf-8') as f:
            f.write(header + '\n' + body + '\n')
        written.append(fn)

    # 未拆分的开头部分(第一个标题之前)单独存 _前言
    if split_pts and split_pts[0][0] > 0:
        head_txt = '\n'.join(lines[:split_pts[0][0]]).strip()
        if head_txt.strip('#'):
            with open(os.path.join(outdir, '00-前言目录.md'), 'w', encoding='utf-8') as f:
                f.write(head_txt + '\n')
            written.insert(0, '00-前言目录.md')

    print(f'拆成 {len(written)} 个文件 -> {outdir}')
    for w in written[:40]:
        print('  ', w)

if __name__ == '__main__':
    main()
