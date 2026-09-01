# -*- coding: utf-8 -*-
"""
把「扫描版(无文本层)」PDF 用 tesseract OCR 成 Markdown。

用法:
  python pdf_ocr_md.py <输入.pdf> [输出.md] [起始页] [结束页]
    - 页号按 PDF 显示页(1 起);省略起止页 = 全书
    - 每页渲染 300dpi 灰度图 -> tesseract chi_sim -> 按书签插入标题
    - 逐页增量写盘,中断后可指定起始页续跑
依赖: pymupdf(fitz) + tesseract.exe + D:/tessdata/chi_sim.traineddata
"""
import sys, os, re, subprocess, tempfile
import fitz

TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA  = r"D:\tessdata"
DPI = 300

def ocr_page(doc, pageno, tmpdir):
    """pageno 为 1 起。返回该页 OCR 文本。每页独立临时文件，避免 Windows 文件锁冲突。"""
    page = doc[pageno - 1]
    pix = page.get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
    tmp_png = os.path.join(tmpdir, f'ocr_p{pageno}.png')
    pix.save(tmp_png)
    try:
        r = subprocess.run(
            [TESSERACT, tmp_png, 'stdout', '-l', 'chi_sim',
             '--tessdata-dir', TESSDATA, '--psm', '3'],
            capture_output=True, timeout=120)
        return r.stdout.decode('utf-8', 'ignore')
    except Exception as e:
        return f'[OCR 失败 p{pageno}: {e}]'
    finally:
        try:
            os.remove(tmp_png)
        except OSError:
            pass

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + '-OCR.md'
    start = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    end   = int(sys.argv[4]) if len(sys.argv) > 4 else None

    doc = fitz.open(src)
    n = doc.page_count
    end = end if end and end <= n else n

    toc = doc.get_toc()
    head_at = {}
    for lvl, title, page in toc:
        title = re.sub(r'\s+', ' ', title).strip()
        head_at.setdefault(page, []).append((lvl, title))

    def heading(lvl, title):
        return '#' * min(lvl + 1, 5) + ' ' + title

    book = re.sub(r'\s+', ' ', os.path.splitext(os.path.basename(src))[0]).strip()

    tmpdir = tempfile.mkdtemp(prefix='ocr_')
    try:
        # 起始页 == 1 时写文件头
        if start == 1:
            with open(dst, 'w', encoding='utf-8') as f:
                f.write('# ' + book + '\n\n')
                f.write(f'> 来源：`{os.path.basename(src)}` 扫描版，tesseract chi_sim OCR，共 {n} 页。\n')
                f.write('> 扫描 OCR 可能有错字，`<!-- pN -->` 可回溯原书对应页核对。\n\n')

        for pageno in range(start, end + 1):
            text = ocr_page(doc, pageno, tmpdir).strip()
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            with open(dst, 'a', encoding='utf-8') as f:
                for lvl, t in head_at.get(pageno, []):
                    f.write(heading(lvl, t) + '\n\n')
                if text:
                    f.write(text + '\n\n')
                f.write(f'<!-- p{pageno} -->\n\n')
            if pageno % 10 == 0 or pageno == end:
                print(f'  进度 {pageno}/{end} 页', flush=True)
    finally:
        doc.close()
        for f in os.listdir(tmpdir):
            try:
                os.remove(os.path.join(tmpdir, f))
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass
    print(f'完成: {dst}  (页 {start}-{end})')

if __name__ == '__main__':
    main()
