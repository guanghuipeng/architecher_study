# -*- coding: utf-8 -*-
"""极简 SQLite 终端 SQL 交互器。零依赖（仅 Python 自带 sqlite3）。
用法: python sqlrepl.py [数据库文件]
SQL 以分号 ; 结尾才执行(可跨多行)；\q 退出；\d 列出所有表；\t 表名 看结构"""
import sqlite3, sys, os

db = sys.argv[1] if len(sys.argv) > 1 else "mydb.sqlite"
con = sqlite3.connect(db)
con.execute("PRAGMA foreign_keys = ON")   # 开外键约束，便于演示完整性检查
cur = con.cursor()
print(f"SQLite {sqlite3.sqlite_version} | 库: {os.path.abspath(db)} | 外键: ON")
print("SQL 以 ; 结尾执行 | \\q 退出 | \\d 列表 | \\t 表名 看结构\n")

buf = []
while True:
    try:
        line = input("sqlite> " if not buf else "   ...> ")
    except (EOFError, KeyboardInterrupt):
        print(); break
    if not buf:
        s = line.strip()
        if s in ("\\q", ".exit", ".quit"):
            break
        if s == "\\d":
            for r in cur.execute("Select name From sqlite_master Where type='table' Order by name"):
                print("  ", r[0])
            continue
        if s.startswith("\\t "):
            t = s[3:].strip()
            for r in cur.execute(f'PRAGMA table_info("{t}")'):
                nn = "NOT NULL" if r[3] else "NULL"
                pk = "PK" if r[5] else ""
                print(f"  {r[1]:12} {r[2]:12} {nn:8} {pk}")
            continue
    buf.append(line)
    sql = "\n".join(buf)
    if sql.rstrip().endswith(";"):
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            if cur.description:                       # SELECT 类
                cols = [d[0] for d in cur.description]
                print(" | ".join(cols))
                print("-+-".join("-" * max(6, len(c)) for c in cols))
                for r in rows:
                    print(" | ".join(str(x) for x in r))
                print(f"({len(rows)} 行)")
            elif cur.rowcount != -1:                  # INSERT/UPDATE/DELETE
                print(f"OK, 影响 {cur.rowcount} 行")
            else:                                      # CREATE/DROP/ALTER
                print("OK")
        except sqlite3.Error as e:
            print(f"错误: {e}")
        con.commit()
        buf = []
con.close()
