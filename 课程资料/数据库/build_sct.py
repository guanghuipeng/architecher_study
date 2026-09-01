# -*- coding: utf-8 -*-
"""按讲义《SQL语言之概览》Page 9-10 建立 SCT 学生选课数据库（SQLite）。
注意：SQLite 中含 # 等特殊字符的列名必须用双引号包起来，如 "S#"。
此脚本为参考答案，自己建完再对照。"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sct.db")
if os.path.exists(DB):
    os.remove(DB)

con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys = ON")
cur = con.cursor()

cur.executescript("""
CREATE TABLE Dept    ( "D#" char(2) PRIMARY KEY, Dname char(10), Dean char(10) );
CREATE TABLE Teacher ( "T#" char(3) PRIMARY KEY, Tname char(10), "D#" char(2),
                       Salary float,
                       FOREIGN KEY("D#") REFERENCES Dept("D#") );
CREATE TABLE Student ( "S#" char(8) PRIMARY KEY, Sname char(10), Ssex char(2),
                       Sage integer, "D#" char(2), Sclass char(6),
                       FOREIGN KEY("D#") REFERENCES Dept("D#") );
CREATE TABLE Course  ( "C#" char(3) PRIMARY KEY, Cname char(12), Chours integer,
                       Credit float, "T#" char(3),
                       FOREIGN KEY("T#") REFERENCES Teacher("T#") );
CREATE TABLE SC      ( "S#" char(8), "C#" char(3), Score float,
                       PRIMARY KEY("S#", "C#"),
                       FOREIGN KEY("S#") REFERENCES Student("S#"),
                       FOREIGN KEY("C#") REFERENCES Course("C#") );
""")

data = {
    "Dept": [
        ("02","机电","李三"), ("03","计算机","李四"), ("04","自动控制","李五"),
    ],
    "Teacher": [
        ("001","赵三","03",1200.00), ("002","赵四","03",1400.00),
        ("003","赵五","04",1000.00), ("004","赵六","04",1100.00),
    ],
    "Student": [
        ("98030101","张三","男",20,"03","980301"),
        ("98030102","张四","女",20,"03","980301"),
        ("98030103","张五","男",19,"03","980301"),
        ("98040201","王三","男",21,"04","980402"),
        ("98040202","王四","男",20,"04","980402"),
        ("98040203","王五","女",20,"04","980402"),
    ],
    "Course": [
        ("001","数据库",40,6,"001"),
        ("002","高等数学",80,6,"004"),
        ("003","数据结构",48,6,"003"),
        ("004","编译原理",40,6,"001"),
        ("005","C语言",30,4,"003"),
    ],
    "SC": [
        ("98030101","001",92), ("98030101","002",85), ("98030101","003",88),
        ("98030102","001",54), ("98030102","002",85), ("98030102","003",48),
        ("98040202","001",55), ("98040202","002",90), ("98040202","003",80),
        ("98040203","003",56),
    ],
}
order = ["Dept","Teacher","Student","Course","SC"]
for t in order:
    cur.executemany(f"INSERT INTO {t} VALUES ({','.join(['?']*len(data[t][0]))})", data[t])
con.commit()

def show(title, sql):
    print(f"\n=== {title} ===\n{sql}\n-- 结果:")
    for row in cur.execute(sql):
        print("  ", row)

show("1. 全表 Student", 'Select * From Student')
show("2. σ_{Sage<=19}(Π_{Sname,Sage})", 'Select Sname, Sage From Student Where Sage<=19')
show("3. 去重: 成绩>80的学号", 'Select Distinct "S#" From SC Where Score>80')
show("4. 排序: 002号课>80降序", 'Select "S#" From SC Where "C#"=\'002\' and Score>80 Order By Score Desc')
show("5. 二表等值连接: 001号课成绩降序显示姓名",
     'Select Sname, Score From Student, SC Where Student."S#"=SC."S#" and SC."C#"=\'001\' Order By Score Desc')
show("6. 三表连接: '数据库'课成绩降序显示姓名",
     'Select Sname, Score From Student, SC, Course Where Student."S#"=SC."S#" and SC."C#"=Course."C#" and Course.Cname=\'数据库\' Order By Score Desc')
show("7. 同表连接: 既学001又学002的学号",
     'Select S1."S#" From SC S1, SC S2 Where S1."S#"=S2."S#" and S1."C#"=\'001\' and S2."C#"=\'002\'')
show("8. 同表连接: 001号成绩比002号高的学号",
     'Select S1."S#" From SC S1, SC S2 Where S1."S#"=S2."S#" and S1."C#"=\'001\' and S2."C#"=\'002\' and S1.Score>S2.Score')
show("9. 不等值连接θ: 有薪水差额的两位教师",
     'Select T1.Tname, T2.Tname From Teacher T1, Teacher T2 Where T1.Salary>T2.Salary')

print("\n表行数:")
for t in ["Dept","Teacher","Student","Course","SC"]:
    print(f"  {t}: {cur.execute(f'Select Count(*) From {t}').fetchone()[0]} 条")
con.close()
print(f"\n建库完成: {DB}")
