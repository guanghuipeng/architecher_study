# -*- coding: utf-8 -*-
import re

src = open('考试大纲-OCR.txt', encoding='utf-8').read()
src = re.sub(r'={5,}\s*第\s*(\d+)\s*页\s*={5,}', r'\n<!-- p\1 -->\n', src)

lines = [re.sub(r'[ \t]+$', '', l) for l in src.split('\n')]
out, blank = [], 0
for l in lines:
    if l.strip() == '':
        blank += 1
        if blank <= 1:
            out.append('')
    else:
        blank = 0
        out.append(l)
text = '\n'.join(out).strip()

header = (
    '# 系统架构设计师考试大纲（第2版）\n\n'
    '> 来源：`考试大纲-OCR.txt`（70 页扫描版 OCR，tesseract chi_sim）。\n'
    '> `<!-- pN -->` 对应原大纲页码。能力地图见 `考试大纲-能力地图.md`。\n\n'
)
with open('教材知识库/00-考试大纲/考试大纲-全文.md', 'w', encoding='utf-8') as f:
    f.write(header + text + '\n')
print('大纲全文已生成，字符数', len(text))
