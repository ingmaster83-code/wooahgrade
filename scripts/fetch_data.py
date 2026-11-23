# -*- coding: utf-8 -*-
"""우아병원등급 수집기 — 건강보험심사평가원 병원평가정보서비스(data.go.kr 15094093, B551182/hospAsmInfoService1/getHospAsmInfo1).
요양기관별 평가등급(asmGrd01~24)을 전부 받아 data/grades.json.gz 로 저장. 키: 환경변수 API_KEY → DATA_GO_KR_API_KEY → ../hosppass/.env (코드에 넣지 않는다).
사용: python scripts/fetch_data.py"""
import gzip, json, os, re, sys, time
from pathlib import Path
import requests
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
URL = "https://apis.data.go.kr/B551182/hospAsmInfoService1/getHospAsmInfo1"


def key():
    for n in ("API_KEY", "DATA_GO_KR_API_KEY"):
        if os.environ.get(n):
            return os.environ[n].strip()
    for p in (ROOT / ".env", ROOT.parent / "hosppass" / ".env"):
        if p.exists():
            m = re.search(r"^API_KEY\s*=\s*(\S+)", p.read_text(encoding="utf-8"), re.M)
            if m:
                return m.group(1).strip("\"'")
    sys.exit("API_KEY 필요")


K = key()
S = requests.Session()
out, page, n = [], 1, 1000
while True:
    for attempt in range(6):
        try:
            r = S.get(URL, params=dict(serviceKey=K, _type="json", pageNo=page, numOfRows=n), timeout=90)
            j = r.json()
            b = j["response"]["body"]
            break
        except Exception as e:
            print("재시도", page, str(e)[:60])
            time.sleep(5 + 5 * attempt)
    else:
        sys.exit("실패")
    it = (b.get("items") or {}).get("item") or []
    it = it if isinstance(it, list) else [it]
    out += it
    total = int(b.get("totalCount") or 0)
    print(page, len(out), "/", total, flush=True)
    if page * n >= total or not it:
        break
    page += 1
    time.sleep(0.3)
prev = ROOT / "data" / "grades.json.gz"
if prev.exists():
    old = len(json.loads(gzip.open(prev, "rt", encoding="utf-8").read())["items"])
    if len(out) < old * 0.8:
        sys.exit("직전(%d)보다 크게 줄어(%d) 중단" % (old, len(out)))
(ROOT / "data").mkdir(exist_ok=True)
with gzip.open(prev, "wt", encoding="utf-8", compresslevel=9) as f:
    json.dump(dict(asof=time.strftime("%Y-%m-%d"), items=out), f, ensure_ascii=False, separators=(",", ":"))
print("저장", len(out))
