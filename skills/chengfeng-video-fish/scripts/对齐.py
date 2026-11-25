# 第 3 步：给每段配音对上逐字时间，顺手查吞字、多念
# Fish 接口只给音频、不给逐字时间：用本机 whisper.cpp（开 DTW）识别出每个字的时刻，再按原稿逐字对齐；
# 识别错的字用原稿的字，时间按前后插值。60 秒级的段，DTW 比按 token 时间准（实测拼接点只差 0.1 秒左右）。
# 每句第一个字：识别出来常比真开口晚 0.1 秒左右，前面 0.25 秒内有停顿结束的，贴到停顿结束那一刻。
# 用法：python3 对齐.py <工作目录> [--段 s03]      已对齐过、mp3 没变的段跳过
# 出：段/<id>.wav（48 kHz）、段/<id>.json（逐句逐字毫秒、对不上的地方）；屏幕上列出疑似吞字、多念的段
import difflib, json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 共用 as g

参 = sys.argv[1:]
if not 参:
    sys.exit("用法：python3 对齐.py <工作目录> [--段 s03]")
W = 参[0]
段们 = g.选段(g.段落(W), 参)
模型, DTW = g.whisper模型()
SAME = str.maketrans("他它壹麽", "她她一么")  # 同音的 ta、繁体写法识别不稳，对齐时当同一个字
可疑 = []


def 识别(wav16, 提示, tmp, tag):
    subprocess.run(["whisper-cli", "-m", 模型, "-l", "zh", "-nfa", "-dtw", DTW, "-ojf", "-of", f"{tmp}/{tag}", "--prompt", 提示, "-f", wav16],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    tks = []  # (字列表, DTW 起 ms)
    for seg in g.读(f"{tmp}/{tag}.json").get("transcription", []):
        for tk in seg.get("tokens", []):
            t = tk.get("text", "")
            if t.startswith("[_") or not t.strip():
                continue
            d = tk.get("t_dtw", -1)
            if d is None or d < 0:
                sys.exit("whisper 没给 t_dtw（DTW 没开成）：检查 whisper-cli 版本和模型名")
            tks.append(([c for c in t if not c.isspace() and c not in g.PUNCT], d * 10.0))
    out = []  # (字, 起ms, 止ms)：一个 token 多个字时在它和下一个 token 之间平分；每字最长 300 ms
    for k, (cs, a) in enumerate(tks):
        if not cs:
            continue
        nxt = tks[k + 1][1] if k + 1 < len(tks) else a + 300 * len(cs)
        span = max(60.0 * len(cs), min(nxt - a, 300.0 * len(cs)))
        for i, c in enumerate(cs):
            out.append((c.lower().translate(SAME), a + span * i / len(cs), a + span * (i + 1) / len(cs)))
    return out


def 对一段(sid):
    mp3 = os.path.join(W, "段", sid + ".mp3")
    with open(os.path.join(W, "段", sid + ".txt"), encoding="utf-8") as f:
        稿 = f.read().strip()
    wav48 = os.path.join(W, "段", sid + ".wav")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", mp3, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", wav48], check=True)
    dur = g.时长(wav48)
    tmp = tempfile.mkdtemp()
    wav16 = f"{tmp}/a.wav"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", mp3, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav16], check=True)

    units = re.findall(r"[A-Za-z0-9.]+|[^\sA-Za-z0-9]", 稿)   # 汉字一个一个，英文和数字连成一个，标点单独
    sc, owner = [], []
    for i, u in enumerate(units):
        if u in g.PUNCT:
            continue
        for c in u.lower().translate(SAME):
            sc.append(c); owner.append(i)

    def match(rec):
        sm = difflib.SequenceMatcher(None, sc, [r[0] for r in rec], autojunk=False)
        return sm, sum(b.size for b in sm.get_matching_blocks())

    rec = 识别(wav16, 稿, tmp, "w1"); sm, got = match(rec); used = "原稿提示"
    if got < 0.9 * len(sc):   # whisper 偶尔整段跳过：换通用提示再认一次，取对得多的
        rec2 = 识别(wav16, "以下是普通话的句子。", tmp, "w2"); sm2, got2 = match(rec2)
        if got2 > got:
            rec, sm, got, used = rec2, sm2, got2, "通用提示"
    times = [None] * len(sc)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            r = rec[blk.b + k]; times[blk.a + k] = (r[1], r[2])
    miss = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            at = rec[j1][1] if j1 < len(rec) else (rec[-1][2] if rec else 0)
            miss.append({"原稿": "".join(sc[i1:i2]), "识别": "".join(r[0] for r in rec[j1:j2]), "约在秒": round(at / 1000, 2)})
    k = 0
    while k < len(times):            # 没对上的字按前后已知时间平分
        if times[k] is None:
            j = k
            while j < len(times) and times[j] is None: j += 1
            a = times[k - 1][1] if k > 0 else 0.0
            b = times[j][0] if j < len(times) else dur * 1000
            for m in range(j - k):
                times[k + m] = (a + (b - a) * m / (j - k), a + (b - a) * (m + 1) / (j - k))
            k = j
        else:
            k += 1
    ut = {}
    for c_i, u in enumerate(owner):
        s, e = times[c_i]
        ut[u] = (min(ut[u][0], s), max(ut[u][1], e)) if u in ut else (s, e)
    sentences, cur, last_e = [], [], 0.0
    for i, u in enumerate(units):
        if u in g.PUNCT:
            cur.append({"text": u, "start_time": int(round(last_e)), "end_time": int(round(last_e))})
            if u in g.END:
                sentences.append(cur); cur = []
        else:
            s, e = ut[i]
            cur.append({"text": u, "start_time": int(round(s)), "end_time": int(round(e))}); last_e = e
    if cur:
        sentences.append(cur)
    log = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", wav48, "-af", "silencedetect=noise=-40dB:d=0.15", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    静止 = [float(x) * 1000 for x in re.findall(r"silence_end: ([\d.]+)", log)]
    for ws in sentences:          # 句首贴到停顿结束
        sp = [w for w in ws if w["text"] not in g.PUNCT]
        if not sp: continue
        a = sp[0]["start_time"]; 前 = [e for e in 静止 if 0 < a - e <= 250]
        if 前: sp[0]["start_time"] = int(round(前[-1]))
    subs = []
    for ws in sentences:
        sp = [w for w in ws if w["text"] not in g.PUNCT] or ws
        subs.append({"text": "".join(w["text"] for w in ws), "start_time": sp[0]["start_time"], "end_time": sp[-1]["end_time"], "words": ws})
    g.写(os.path.join(W, "段", sid + ".json"),
         {"duration": round(dur, 3), "align": {"prompt": used, "chars": len(sc), "matched": got, "mismatch": miss},
          "subtitle": {"sentences": subs}})
    比 = got / max(1, len(sc))
    print(f"{sid}  {dur:.1f} 秒  原稿 {len(sc)} 字，对上 {got}（{比:.0%}）")
    for m in miss:
        print(f"    对不上：原稿「{m['原稿']}」识别「{m['识别']}」约 {m['约在秒']:.2f} 秒")
    吞 = [m for m in miss if len(m["原稿"]) >= 2 and len(m["识别"]) <= len(m["原稿"]) // 3]
    多 = [m for m in miss if len(m["识别"]) >= 3 and not m["原稿"]]
    if 比 < 0.95 or 吞 or 多:
        可疑.append((sid, 比, 吞, 多))


for d in 段们:
    sid = d["id"]
    mp3, js = os.path.join(W, "段", sid + ".mp3"), os.path.join(W, "段", sid + ".json")
    if not os.path.exists(mp3):
        print(f"{sid}  还没配音，跳过"); continue
    if os.path.exists(js) and os.path.getmtime(js) >= os.path.getmtime(mp3):
        print(f"{sid}  已对齐，跳过"); continue
    对一段(sid)
if 可疑:
    print("\n要人看一眼的段（识别也会认错，先听这一段再决定要不要重配）：")
    for sid, 比, 吞, 多 in 可疑:
        说 = [f"对上 {比:.0%}"] + [f"可能吞了「{m['原稿']}」" for m in 吞] + [f"可能多念「{m['识别']}」" for m in 多]
        print(f"  {sid}：" + "；".join(说) + f"  → 重配：python3 配音.py {W} --段 {sid} --重配")
print("下一步：python3 拼接.py " + W)
