# -*- coding: utf-8 -*-
"""로컬 1회 준비: 평가 대상 기관의 시도·시군구·읍면동·전화번호와 우아병원(wooahospital) 페이지 경로를 data/hosp_min.json.gz 로 저장.
hosppass/data/hospitals.json(ykiho 포함)과 wooahospital/data/hospitals.json.gz(같은 순서)를 사용한다."""
import gzip, json, re, sys, collections
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
HP = json.loads((ROOT.parent / "hosppass" / "data" / "hospitals.json").read_text(encoding="utf-8"))["items"]
WH = json.loads(gzip.decompress((ROOT.parent / "wooahospital" / "data" / "hospitals.json.gz").read_bytes()).decode("utf-8"))["items"]
GR = json.loads(gzip.open(ROOT / "data" / "grades.json.gz", "rt", encoding="utf-8").read())["items"]
want = {g["ykiho"] for g in GR}
sl = lambda s: re.sub(r"[^0-9A-Za-z가-힣]+", "-", s).strip("-") or "x"  # wooahospital/scripts/build_site.py 와 동일
used = collections.defaultdict(set)
out = {}
for i, w in enumerate(WH):
    base = sl(w["n"]) + ("-" + sl(w["e"]) if w["e"] else "")
    s = base; n = 2
    while s in used[(w["s"], w["g"])]:
        s = "%s-%d" % (base, n); n += 1
    used[(w["s"], w["g"])].add(s)
    h = HP[i]
    assert h["name"].strip() == w["n"], i
    if h["ykiho"] in want:
        out[h["ykiho"]] = [w["s"], w["g"], w["n"], (h.get("emd_nm") or "").strip(), (h.get("tel") or "").strip(), "/h/%s/%s/%s/" % (w["s"], w["g"], s)]
with gzip.open(ROOT / "data" / "hosp_min.json.gz", "wt", encoding="utf-8", compresslevel=9) as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("매칭", len(out), "/", len(want))
