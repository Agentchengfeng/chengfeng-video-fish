# 第 1 步：把口播稿拆成段，一段配一次音（改稿后只重配改了的段）
# 用法：python3 分段.py <口播稿.md> [工作目录]       工作目录默认是稿子旁边的 <稿子名>-配音/
# 口播稿：用「## 段名」分段，一段 15–35 秒（约 80–180 字）为宜；没有 ## 就按空行分段，再合到每段约 150 字。
# 【】里的字不念（放在画面上的字、提示词、网址），拆段时去掉；markdown 的 **、`、行首 >、- 也去掉。
# 出：段落.json（每段 id、段名、要念的字数、字节数）、段/<id>.txt。某段的字变了，删掉它旧的 mp3、wav、json，下一步只重配它。
import hashlib, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 共用 as g

if len(sys.argv) < 2:
    sys.exit("用法：python3 分段.py <口播稿.md> [工作目录]")
稿 = sys.argv[1]
W = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(稿)[0] + "-配音"
os.makedirs(os.path.join(W, "段"), exist_ok=True)
with open(稿, encoding="utf-8") as f:
    行们 = f.read().split("\n")


def 洗(s):
    s = re.sub(r"【[^】]*】", "", s)
    s = re.sub(r"<!--.*?-->", "", s)
    s = re.sub(r"^\s*(>|[-*+]|\d+\.)\s+", "", s)
    s = s.replace("**", "").replace("`", "")
    return s.strip()


块 = []   # (段名, 文字)
if any(x.startswith("## ") for x in 行们):
    名, 存 = None, []
    for x in 行们:
        if x.startswith("## "):
            if 名 is not None:
                块.append((名, 存))
            名, 存 = x[3:].strip(), []
        elif 名 is not None and not x.startswith("#"):
            存.append(洗(x))
    if 名 is not None:
        块.append((名, 存))
    块 = [(n, "".join(t for t in ts if t)) for n, ts in 块]
else:
    段们, 当前 = [], ""
    for 段 in re.split(r"\n\s*\n", "\n".join(行们)):
        t = "".join(洗(x) for x in 段.split("\n") if not x.startswith("#"))
        if not t:
            continue
        if 当前 and len(当前) + len(t) > 150:
            段们.append(当前); 当前 = ""
        当前 += t
    if 当前:
        段们.append(当前)
    块 = [(f"第{i + 1}段", t) for i, t in enumerate(段们)]
块 = [(n, t) for n, t in 块 if t]
if not 块:
    sys.exit("稿子里没有要念的字")

旧 = {d["id"]: d for d in g.读(os.path.join(W, "段落.json"))} if os.path.exists(os.path.join(W, "段落.json")) else {}
出, 改了 = [], []
for i, (名, 文) in enumerate(块):
    sid = f"s{i + 1:02d}"
    指纹 = hashlib.md5(文.encode("utf-8")).hexdigest()[:12]
    if sid in 旧 and 旧[sid].get("指纹") != 指纹:
        for 尾 in (".mp3", ".wav", ".json"):
            p = os.path.join(W, "段", sid + 尾)
            if os.path.exists(p):
                os.remove(p)
        改了.append(sid)
    with open(os.path.join(W, "段", sid + ".txt"), "w", encoding="utf-8") as f:
        f.write(文 + "\n")
    字 = len(re.findall(r"[一-鿿]|[A-Za-z]+|\d+(?:\.\d+)?", 文))
    出.append({"id": sid, "段名": 名, "字数": 字, "字节": len(文.encode("utf-8")), "指纹": 指纹})
for sid in set(旧) - {d["id"] for d in 出}:
    for 尾 in (".txt", ".mp3", ".wav", ".json"):
        p = os.path.join(W, "段", sid + 尾)
        if os.path.exists(p):
            os.remove(p)
g.写(os.path.join(W, "段落.json"), 出)
print(f"工作目录 {W}：{len(出)} 段，共 {sum(d['字数'] for d in 出)} 字、{sum(d['字节'] for d in 出)} 字节")
for d in 出:
    print(f"  {d['id']}  {d['字数']:>4} 字  {d['段名']}")
if 改了:
    print("字变了、要重配的段：" + "、".join(改了))
