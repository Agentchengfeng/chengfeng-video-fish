# 第 2 步：调 Fish Audio 官方接口，一段一段配音，存 段/<id>.mp3
# 接口照官方文档写：POST https://api.fish.audio/v1/tts（https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech）
# 用法：python3 配音.py <工作目录> [--段 s03,s05] [--重配] [--voice <声音ID>] [--model s2.1-pro] [--只算]
#   已经有 mp3 的段跳过；--重配 连有的也重配（配合 --段 只重配那几段）。--只算 只打印要配几段、多少字节，不调接口。
#   声音 ID：--voice，或 config.json 的 voice_id。模型：--model，或 config.json 的 model，都没写用 s2.1-pro。
# 按输入文字的 UTF-8 字节收费（价格见 https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits）。
import json, os, sys, time, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 共用 as g

参 = sys.argv[1:]
def 取(名, 默认=None):
    if 名 not in 参: return 默认
    i = 参.index(名); v = 参[i + 1]; del 参[i:i + 2]; return v
def 有(名):
    if 名 in 参: 参.remove(名); return True
    return False
声音 = 取("--voice") or g.配置().get("voice_id")
模型 = 取("--model") or g.配置().get("model") or "s2.1-pro"
重配, 只算 = 有("--重配"), 有("--只算")
if not 参:
    sys.exit("用法：python3 配音.py <工作目录> [--段 s03,s05] [--重配] [--voice <声音ID>] [--model s2.1-pro] [--只算]")
W = 参[0]
段们 = g.选段(g.段落(W), 参)
要配 = [d for d in 段们 if 重配 or not os.path.exists(os.path.join(W, "段", d["id"] + ".mp3"))]
print(f"要配 {len(要配)} 段，共 {sum(d['字节'] for d in 要配)} 字节（UTF-8），模型 {模型}")
if 只算 or not 要配:
    sys.exit(0)
if not 声音:
    sys.exit("没有声音 ID：在 fish.audio 上打开你要用的声音，复制它的 ID（32 位字母和数字），\n"
             f"用 --voice <ID>，或写进 {g.配置目录}/config.json：{{\"voice_id\": \"<ID>\"}}")
钥 = g.key()
预设 = g.配置().get("tts", {})   # 想改别的参数（temperature、prosody 等）写在 config.json 的 "tts" 里，照官方文档的字段名


def 配(文):
    body = {"text": 文, "reference_id": 声音, "format": "mp3", "mp3_bitrate": 192, "latency": "normal"}
    body.update(预设)
    req = urllib.request.Request("https://api.fish.audio/v1/tts", data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Authorization": "Bearer " + 钥, "Content-Type": "application/json", "model": 模型})
    for 第几次 in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            说 = e.read().decode("utf-8", "replace")[:300]
            if e.code == 401:
                sys.exit(f"401：key 不对或失效（{说}）")
            if e.code == 402:
                sys.exit(f"402：这个模型没有 API 余额，去 https://fish.audio/app/developers/billing/ 充值（{说}）")
            if e.code in (400, 404):
                sys.exit(f"{e.code}：参数不对，多半是声音 ID 或模型名写错了（{说}）")
            if e.code == 429 or e.code >= 500:
                等 = 2 ** 第几次
                print(f"  {e.code}，{等} 秒后重试"); time.sleep(等); continue
            sys.exit(f"{e.code}：{说}")
        except urllib.error.URLError as e:
            等 = 2 ** 第几次
            print(f"  连不上（{e.reason}），{等} 秒后重试"); time.sleep(等)
    sys.exit("重试 6 次还是不行，停")


for d in 要配:
    with open(os.path.join(W, "段", d["id"] + ".txt"), encoding="utf-8") as f:
        文 = f.read().strip()
    音 = 配(文)
    if len(音) < 1000:
        sys.exit(f"{d['id']}：接口返回的不像音频（{len(音)} 字节）：{音[:200]!r}")
    for 尾 in (".wav", ".json"):          # 旧的对齐结果作废
        p = os.path.join(W, "段", d["id"] + 尾)
        if os.path.exists(p): os.remove(p)
    with open(os.path.join(W, "段", d["id"] + ".mp3"), "wb") as f:
        f.write(音)
    print(f"  {d['id']} 配好，{g.时长(os.path.join(W, '段', d['id'] + '.mp3')):.1f} 秒")
print("下一步：python3 对齐.py " + W)
