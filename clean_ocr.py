# -*- coding: utf-8 -*-
"""
清洗 OCR 产物：去掉每页重复的页眉/页脚噪声 + 少量高频错字。
用法:
  python clean_ocr.py <目录或文件.md> [--apply]   (默认只预览，加 --apply 才写回)
"""
import sys, os, re, glob

# 页脚: "系统架构设计师教程(第 2 版)" 各种 OCR 变体
FOOTER = re.compile(r'系统架构设计师教程\s*[\(\（〈]\s*第')
# 页眉: 行首 "第N章" + 章节名 + 乱码页码(含"国"或结尾数字)
HEADER = re.compile(r'^第\s*\d+\s*[!1]?\s*章.{0,45}?[国]\d*[国清因加]?')
# 纯页码垃圾行(整行只有 国/数字/少量符号)
PAGENUM = re.compile(r'^[国同半曰白网汪辆 ]{0,6}\d{1,3}\s*[国戎昌上下恩时因清明]?[。."，,]*\s*$')

# 高频且无歧义的 OCR 错字 -> 修正
# 注意：不做盲目替换（可能改错），改为语义校对（另见 proofread 流程）。
FIXES = []

def clean(text):
    out = []
    for ln in text.split('\n'):
        s = ln.strip()
        if not s:
            out.append('')
            continue
        # 页脚/页眉/纯页码 -> 整行丢弃
        if FOOTER.search(s) or HEADER.match(s) or PAGENUM.match(s):
            continue
        out.append(ln)
    text = '\n'.join(out)
    for a, b in FIXES:
        text = text.replace(a, b)
    return text

def main():
    args = [a for a in sys.argv[1:]]
    apply = '--apply' in args
    args = [a for a in args if a != '--apply']
    target = args[0] if args else '教材知识库/01-系统架构设计师教程'

    files = []
    if os.path.isdir(target):
        files = sorted(glob.glob(os.path.join(target, '*.md')))
    else:
        files = [target]

    total_dropped = 0
    for f in files:
        src = open(f, encoding='utf-8').read()
        cleaned = clean(src)
        # 统计丢了多少行
        dropped = src.count('\n') - cleaned.count('\n')
        total_dropped += dropped
        print(f'{"[应用]" if apply else "[预览]"} {os.path.basename(f)}: 删 {dropped} 行噪声')
        if apply:
            open(f, 'w', encoding='utf-8').write(cleaned)
    print(f'共处理 {len(files)} 个文件，删 {total_dropped} 行。{"已写回。" if apply else "（未写回，加 --apply 生效）"}')

if __name__ == '__main__':
    main()
