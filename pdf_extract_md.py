# -*- coding: utf-8 -*-
"""
把「有文本层」的 PDF 抽取成 Markdown，用于全文检索/阅读。

用法:
  python pdf_extract_md.py <输入.pdf> [输出.md]

- 读取 PDF 书签(目录)作为标题层级，插入到对应页
- 每页正文后加 <!-- pN --> 页标记(渲染不可见,可 grep 定位回原书)
- 只适合有文本层的 PDF;扫描版请用 pdf_ocr_md.py
"""
import sys, os, re
import fitz

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + "-文本版.md"

    doc = fitz.open(src)
    n = doc.page_count
    toc = doc.get_toc()  # [(level, title, page1based)]

    # 标题插入表: page(1based) -> [(level, title)]
    head_at = {}
    for lvl, title, page in toc:
        title = re.sub(r'\s+', ' ', title).strip()
        head_at.setdefault(page, []).append((lvl, title))

    def heading(lvl, title):
        # 篇(1级) -> ##，小时/章(2级) -> ###，更深 -> ####
        return '#' * min(lvl + 1, 4) + ' ' + title

    out = []
    book = re.sub(r'\s+', ' ', os.path.splitext(os.path.basename(src))[0]).strip()
    out.append('# ' + book)
    out.append('')
    out.append('> 来源：`' + os.path.basename(src) + '` 文本层提取，' + str(n) + ' 页。')
    out.append('> 每页末尾 `<!-- pN -->` 对应原书页码，可用它回溯 PDF。')
    out.append('')

    for i in range(n):
        pageno = i + 1
        # 先插入该页命中的标题
        for lvl, t in head_at.get(pageno, []):
            out.append(heading(lvl, t))
            out.append('')
        text = doc[i].get_text('text').strip()
        if text:
            # 行内多余空格收敛, 折叠 3+ 连续空行为单空行
            text = re.sub(r' +', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            out.append(text)
            out.append('')
        out.append(f'<!-- p{pageno} -->')
        out.append('')

    doc.close()
    with open(dst, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    size = os.path.getsize(dst)
    print(f'完成: {dst}  ({size/1024:.0f} KB, {n} 页, 目录 {len(toc)} 条)')

if __name__ == '__main__':
    main()
