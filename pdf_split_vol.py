# -*- coding: utf-8 -*-
"""
把大 PDF 按页拆成上下两个分册(单个 <100MB，绕过 GitHub 单文件上限)，保留书签目录。

用法:
  python pdf_split_vol.py <输入.pdf> <拆分页(1起)> [上册名] [下册名]
    - 拆分页 = 下册第一页的页码(1起)
    - 上册 = 1..拆分页-1，下册 = 拆分页..末页
    - 书签按原页码重新编号到各自分册
"""
import sys, os
import fitz

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    src = sys.argv[1]
    split = int(sys.argv[2])
    base = os.path.splitext(src)[0]
    up = sys.argv[3] if len(sys.argv) > 3 else base + '-上册.pdf'
    down = sys.argv[4] if len(sys.argv) > 4 else base + '-下册.pdf'

    doc = fitz.open(src)
    n = doc.page_count
    toc = doc.get_toc()

    def build(p_start, p_end):
        d = fitz.open()
        d.insert_pdf(doc, from_page=p_start - 1, to_page=p_end - 1)
        newtoc = [[l, t, p - p_start + 1] for l, t, p in toc if p_start <= p <= p_end]
        d.set_toc(newtoc)
        return d

    up_doc = build(1, split - 1)
    down_doc = build(split, n)
    up_doc.save(up); down_doc.save(down)
    up_doc.close(); down_doc.close(); doc.close()

    for f, pages in [(up, split - 1), (down, n - split + 1)]:
        print(f'{f}  ({os.path.getsize(f)/1e6:.1f} MB, {pages} 页)')

if __name__ == '__main__':
    main()
