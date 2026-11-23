# -*- coding: utf-8 -*-
"""우아병원등급 정적 사이트 생성기.
입력: data/grades.json.gz(심평원 병원평가정보 — 요양기관별 평가등급) · data/hosp_min.json.gz(시도·시군구·전화·우아병원 경로)
출력: _site/  (항목 허브, 항목×지역 허브, 병원급 이상 개별 평가 페이지, 지역 허브, 안내, 검색 인덱스, sitemap)
천식(asmGrd16)은 값 체계('양호'·0 등)가 다른 항목이라 공식 문서로 해석을 확인하기 전까지 싣지 않는다.
"""
import collections, gzip, json, re, shutil, sys
from datetime import datetime, timedelta, timezone

from common import *  # noqa

sys.stdout.reconfigure(encoding="utf-8")
DATA = ROOT / "data"
TODAY = (datetime.now(timezone.utc) + timedelta(hours=9)).date()

SHORT = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종",
         "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원", "충청북도": "충북", "충청남도": "충남", "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
         "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주", "전남광주통합특별시": "전남광주"}

# 코드 → (URL 슬러그, 표시명, 설명)
ITEMS = {
    "01": ("급성기뇌졸중", "급성기 뇌졸중", "급성기 뇌졸중으로 입원한 환자에게 필요한 검사·치료가 적절히 이뤄졌는지 심평원이 평가한 항목입니다."),
    "03": ("혈액투석", "혈액투석", "만성 신부전 환자의 혈액투석 진료의 질을 심평원이 평가한 항목입니다."),
    "04": ("의료급여정신과", "의료급여 정신과", "의료급여 정신과 진료의 적정성을 심평원이 평가한 항목입니다."),
    "05": ("수술부위감염예방항생제", "수술부위 감염예방 항생제", "수술 전후 감염을 막기 위한 예방적 항생제 사용이 적절했는지 평가한 항목입니다."),
    "06": ("관상동맥우회술", "관상동맥우회술", "심장 혈관을 잇는 관상동맥우회술 진료의 질을 평가한 항목입니다."),
    "07": ("급성상기도감염항생제처방률", "급성상기도감염 항생제 처방률", "감기 등 급성 상기도감염 외래 진료에서 항생제를 처방한 비율을 평가한 항목으로, 처방률이 낮을수록 높은 등급입니다."),
    "08": ("주사제처방률", "주사제 처방률", "외래 진료에서 주사제를 처방한 비율을 평가한 항목으로, 처방률이 낮을수록 높은 등급입니다."),
    "09": ("약품목수", "처방 약품목수", "외래 처방 1건당 약 품목수를 평가한 항목으로, 품목수가 적을수록 높은 등급입니다."),
    "10": ("요양병원", "요양병원", "요양병원 입원 진료의 구조와 과정을 심평원이 평가한 항목입니다."),
    "12": ("대장암", "대장암", "대장암 수술 등 진료의 적정성을 심평원이 평가한 항목입니다."),
    "13": ("위암", "위암", "위암 수술 등 진료의 적정성을 심평원이 평가한 항목입니다."),
    "14": ("유방암", "유방암", "유방암 수술 등 진료의 적정성을 심평원이 평가한 항목입니다."),
    "15": ("폐암", "폐암", "폐암 진료의 적정성을 심평원이 평가한 항목입니다."),
    "17": ("만성폐쇄성폐질환", "만성폐쇄성폐질환(COPD)", "만성폐쇄성폐질환 외래 진료의 적정성을 심평원이 평가한 항목입니다."),
    "18": ("폐렴", "폐렴", "폐렴으로 입원한 환자의 진료 적정성을 심평원이 평가한 항목입니다."),
    "19": ("중환자실", "중환자실", "중환자실의 인력·시설과 진료 수준을 심평원이 평가한 항목입니다."),
    "20": ("신생아중환자실", "신생아중환자실", "신생아중환자실의 인력·시설과 진료 수준을 심평원이 평가한 항목입니다."),
    "21": ("마취", "마취", "마취 관리의 적정성을 심평원이 평가한 항목입니다."),
    "22": ("정신건강입원", "정신건강 입원영역", "정신건강 입원 진료의 적정성을 심평원이 평가한 항목입니다."),
    "23": ("급성하기도감염항생제처방률", "급성하기도감염 항생제 처방률", "기관지염 등 급성 하기도감염 외래 진료에서 항생제를 처방한 비율을 평가한 항목으로, 처방률이 낮을수록 높은 등급입니다."),
    "24": ("고혈압당뇨병", "고혈압·당뇨병", "고혈압·당뇨병 외래 진료의 적정성을 심평원이 평가한 항목입니다."),
}
ORDER = ["01", "19", "20", "03", "10", "12", "13", "14", "15", "06", "18", "17", "24", "22", "04", "21", "05", "07", "23", "08", "09"]
SLUG = {c: v[0] for c, v in ITEMS.items()}
NAME = {c: v[1] for c, v in ITEMS.items()}
DESC = {c: v[2] for c, v in ITEMS.items()}
BYSLUG = {v[0]: c for c, v in ITEMS.items()}


def sho(s):
    return SHORT.get(s, s)


def cut(s, n):
    return s if len(s) <= n else s[:n].rstrip() + "…"


def load():
    G = json.loads(gzip.open(DATA / "grades.json.gz", "rt", encoding="utf-8").read())
    M = json.loads(gzip.open(DATA / "hosp_min.json.gz", "rt", encoding="utf-8").read())
    rows = []
    for g in G["items"]:
        gr = {}
        for c in ITEMS:
            v = g.get("asmGrd" + c)
            if v is not None and str(v).strip() in ("1", "2", "3", "4", "5"):
                gr[c] = int(v)
        if not gr:
            continue
        m = M.get(g["ykiho"])
        if m:
            s, gg, name, emd, tel, path = m
        else:
            t = (g.get("addr") or "").split()
            s = SHORT.get(t[0], "") if t else ""
            gg = t[1] if len(t) > 1 else ""
            name, emd, tel, path = (g.get("yadmNm") or "").strip(), "", "", ""
        if not s or not gg:
            continue
        rows.append(dict(id=g["ykiho"], name=name, type=g.get("clCdNm") or "", s=s, g=gg, emd=emd, tel=tel, wh=path, addr=(g.get("addr") or "").strip(), gr=gr))
    return rows, G.get("asof", "")


def badge(n):
    return '<span class="gr gr%d">%d등급</span>' % (n, n)


def rtable(L, cap, show_region=True, code=None):
    L = L[:cap]
    head = "<tr><th>기관</th><th>종별</th>%s<th>%s</th></tr>" % ("<th>지역</th>" if show_region else "", "등급" if code else "1등급 항목")
    rows = []
    for r in L:
        if r["type"] != "의원":
            nm = '<a href="%s">%s</a>' % (r["url"], esc(r["name"]))
        elif r["wh"]:
            nm = '<a href="https://wooahospital.wooahouse.com%s">%s</a>' % (q(r["wh"]), esc(r["name"]))
        else:
            nm = esc(r["name"])
        last = badge(r["gr"][code]) if code else esc(str(sum(1 for v in r["gr"].values() if v == 1)) + "개")
        rows.append("<tr><td>%s</td><td>%s</td>%s<td>%s</td></tr>" % (nm, esc(r["type"]), ("<td>%s</td>" % esc(r["s"] + " " + r["g"])) if show_region else "", last))
    return '<div class="tbl-wrap"><table class="tbl">%s%s</table></div>' % (head, "".join(rows))


def hub(path, h1, sub, L, code, extra="", cap=150, title=None, desc=None, crumbs=None, prio="0.7", region=True, faq=None, stat_html=None):
    body = ['<div class="page-head"><h1>%s</h1><p>%s</p></div>' % (esc(h1), esc(sub)), stat_html or "", ad(), extra, '<h2 class="group-title">%s</h2>' % ("등급 목록 (높은 등급 순)" if code else "기관 목록"),
            rtable(L, cap, region, code)]
    if len(L) > cap:
        body.append('<p class="note">기관이 많아 %d곳만 표시했습니다. 지역별 페이지에서 좁혀 보세요.</p>' % cap)
    write(path, layout(path, title or h1, desc or sub, "\n".join(b for b in body if b), faq, crumbs or [("홈", "/")], coupang=True), prio)


def gstat(L, code):
    c = collections.Counter(r["gr"][code] for r in L)
    n = len(L)
    s = "등급이 공개된 기관 <b>%d곳</b> 중 1등급 %d곳, 2등급 %d곳, 3등급 %d곳, 4등급 %d곳, 5등급 %d곳입니다." % (n, c[1], c[2], c[3], c[4], c[5])
    return '<p class="lead">%s <small>(1등급이 가장 높은 등급)</small></p>' % s


def page_hospital(r, by_sgg_type, hubs):
    gr = r["gr"]
    tops = [NAME[c] for c in ORDER if gr.get(c) == 1]
    lead = ["<b>%s</b>은(는) %s %s에 있는 %s으로, 건강보험심사평가원이 공개한 <b>%d개 평가항목</b>의 등급이 있습니다." % (esc(r["name"]), esc(r["s"]), esc(r["g"]), esc(r["type"]), len(gr))]
    if tops:
        lead.append("1등급을 받은 항목은 %s입니다." % esc(", ".join(tops[:6]) + (" 등" if len(tops) > 6 else "")))
    else:
        lead.append("1등급을 받은 항목은 없습니다. 등급은 항목마다 평가 방법과 대상 기간이 달라 서로 단순 비교할 수 없습니다.")
    rows = []
    for c in ORDER:
        if c in gr:
            n = gr[c]
            rows.append('<tr><td><a href="/item/%s/">%s</a></td><td>%s</td><td>%s</td></tr>' % (q(SLUG[c]), esc(NAME[c]), badge(n), esc(cut(DESC[c], 60))))
    tbl = '<div class="tbl-wrap"><table class="tbl"><tr><th>평가항목</th><th>등급</th><th>항목 설명</th></tr>%s</table></div>' % "".join(rows)
    body = ['<div class="page-head"><h1>%s 평가등급</h1><p>%s</p></div>' % (esc(r["name"]), esc(" · ".join(x for x in (r["type"], r["s"] + " " + r["g"]) if x))), '<p class="lead">%s</p>' % " ".join(lead), ad(), tbl]
    info = [("종별", r["type"]), ("주소", r["addr"]), ("전화", r["tel"])]
    body.append('<h2 class="group-title">기관 정보</h2><div class="tbl-wrap"><table class="tbl">%s</table></div>' % "".join("<tr><th>%s</th><td>%s</td></tr>" % (a, esc(b)) for a, b in info if b))
    if r["wh"]:
        body.append('<p><a class="btn" href="https://wooahospital.wooahouse.com%s">🏥 진료시간·진료과목·주차는 우아병원에서 보기</a></p>' % q(r["wh"]))
    body.append('<div class="note-box">평가등급은 심평원이 항목별로 평가한 결과이며 병원의 전체 의료 수준을 뜻하지 않습니다. 평가 대상 기간·방법은 항목마다 다르고, 등급이 없는 항목은 평가 대상이 아니거나 등급이 산정되지 않은 경우입니다. 진료 선택은 의료진과 상담하세요.</div>')
    sib = [o for o in by_sgg_type.get((r["s"], r["g"], r["type"]), []) if o is not r][:8]
    if sib:
        body.append('<h2 class="group-title">같은 지역 다른 %s <small>%s</small></h2>' % (esc(r["type"]), esc(r["s"] + " " + r["g"])))
        body.append(rtable(sib, 8, False))
    chips = []
    if ("region", r["s"]) in hubs:
        chips.append('<a class="chip" href="/region/%s/">%s 병원 평가등급</a>' % (q(r["s"]), esc(r["s"])))
    if ("rg", r["s"], r["g"]) in hubs:
        chips.append('<a class="chip" href="/region/%s/%s/">%s %s</a>' % (q(r["s"]), q(r["g"]), esc(r["s"]), esc(r["g"])))
    for c in ORDER:
        if c in gr and ("ir", c, r["s"], r["g"]) in hubs:
            chips.append('<a class="chip" href="/item/%s/%s/%s/">%s %s 평가</a>' % (q(SLUG[c]), q(r["s"]), q(r["g"]), esc(r["g"]), esc(NAME[c])))
            break
    if chips:
        body.append('<div class="chips">%s</div>' % "".join(chips))
    faq = [("%s의 평가등급은 어떻게 되나요?" % r["name"], "심평원이 공개한 %d개 항목의 등급이 있습니다. %s" % (len(gr), ("1등급 항목은 " + ", ".join(tops[:6]) + "입니다.") if tops else "항목별 등급은 위 표를 확인하세요.")),
           ("1등급이 가장 좋은 등급인가요?", "네, 심평원 평가는 1등급이 가장 높고 5등급이 가장 낮습니다. 다만 항목마다 평가 방법과 대상 기간이 달라 서로 단순 비교하기는 어렵습니다."),
           ("평가는 어디서 하나요?", "건강보험심사평가원이 의료기관의 진료 적정성을 평가해 공개한 정보이며, 이 페이지는 공공데이터포털의 병원평가정보를 정리한 것입니다.")]
    crumbs = [("홈", "/"), (r["s"], "/region/%s/" % r["s"]), (cut(r["name"], 26), r["url"])]
    ld = [{"@context": "https://schema.org", "@type": "MedicalOrganization", "name": r["name"], "address": r["addr"]}]
    title = ("%s 평가등급 - %s %s %s %s" % (r["name"], r["s"], r["g"], r["emd"], r["type"])).replace("  ", " ")
    desc = "%s(%s %s) 건강보험심사평가원 평가등급 %d개 항목%s." % (r["name"], r["s"], r["g"], len(gr), (": 1등급 " + ", ".join(tops[:3]) + (" 등" if len(tops) > 3 else "")) if tops else "")
    write(r["url"], layout(r["url"], title, desc, "\n".join(body), faq, crumbs, "article", ld, coupang=True), "0.6")


def build():
    rows, asof = load()
    print("평가 기관", len(rows), "수집일", asof)
    for r in rows:
        r["url"] = "/h/%s/%s/%s/" % (r["s"], r["g"], re.sub(r"[^0-9A-Za-z가-힣]+", "-", r["name"] + ("-" + r["emd"] if r["emd"] else "")).strip("-") + "-" + re.sub(r"[^0-9a-z]", "", r["id"][-12:].lower())[-6:])
    assert len({r["url"] for r in rows}) == len(rows), "URL 충돌"
    big = [r for r in rows if r["type"] != "의원"]
    print("개별 페이지 대상(의원 제외)", len(big))
    by_item_all = {c: [r for r in rows if c in r["gr"]] for c in ITEMS}
    by_is, by_ig = collections.defaultdict(list), collections.defaultdict(list)
    for c, L in by_item_all.items():
        for r in L:
            by_is[(c, r["s"])].append(r)
            by_ig[(c, r["s"], r["g"])].append(r)
    by_s, by_sg, by_sgt = collections.defaultdict(list), collections.defaultdict(list), collections.defaultdict(list)
    for r in big:
        by_s[r["s"]].append(r)
        by_sg[(r["s"], r["g"])].append(r)
        by_sgt[(r["s"], r["g"], r["type"])].append(r)

    def key(c):
        return lambda r: (r["gr"][c], r["type"] != "상급종합", r["name"])

    hubs = {("region", s) for s in by_s} | {("rg", s, g) for (s, g), L in by_sg.items() if len(L) >= 3} | {("ir", c, s, g) for (c, s, g), L in by_ig.items() if len(L) >= 3} \
        | {("is", c, s) for (c, s), L in by_is.items() if len(L) >= 3}
    OUT.mkdir(parents=True, exist_ok=True)
    for ch in OUT.iterdir():
        shutil.rmtree(ch) if ch.is_dir() else ch.unlink()
    for r in big:
        page_hospital(r, by_sgt, hubs)
    # 항목 허브
    for c in ORDER:
        L = sorted(by_item_all[c], key=key(c))
        if not L:
            continue
        sc = collections.Counter(r["s"] for r in L)
        extra = '<h2 class="group-title">지역별</h2><div class="chips">%s</div>' % "".join(
            ('<a class="chip" href="/item/%s/%s/">%s <small>%d</small></a>' % (q(SLUG[c]), q(s), esc(s), n)) if ("is", c, s) in hubs else '<span class="chip">%s <small>%d</small></span>' % (esc(s), n) for s, n in sc.most_common())
        top1 = sum(1 for r in L if r["gr"][c] == 1)
        hub("/item/%s/" % q(SLUG[c]).strip("/") if False else "/item/%s/" % SLUG[c], "%s 평가 1등급 병원·의원" % NAME[c], DESC[c], L, c, extra, 100,
            "%s 평가등급 - 1등급 병원·의원 %d곳 (전국)" % (NAME[c], top1), "%s 평가에서 등급이 공개된 기관 %d곳의 지역별 1등급 병원·의원 목록입니다. %s" % (NAME[c], len(L), DESC[c]),
            [("홈", "/"), ("평가항목", "/item/"), (NAME[c], "/item/%s/" % SLUG[c])], "0.8", stat_html=gstat(L, c),
            faq=[("%s 평가는 무엇인가요?" % NAME[c], DESC[c]), ("1등급 기관은 몇 곳인가요?", "공개된 결과 기준 전국 %d곳이 1등급입니다(등급 공개 %d곳 중)." % (top1, len(L)))])
        for s, n in sc.items():
            if ("is", c, s) in hubs:
                L2 = sorted(by_is[(c, s)], key=key(c))
                gc = collections.Counter(r["g"] for r in L2)
                ex = '<h2 class="group-title">시군구별</h2><div class="chips">%s</div>' % "".join(
                    ('<a class="chip" href="/item/%s/%s/%s/">%s <small>%d</small></a>' % (q(SLUG[c]), q(s), q(g), esc(g), k)) if ("ir", c, s, g) in hubs else '<span class="chip">%s <small>%d</small></span>' % (esc(g), k) for g, k in gc.most_common(80))
                t1 = sum(1 for r in L2 if r["gr"][c] == 1)
                hub("/item/%s/%s/" % (SLUG[c], s), "%s %s 평가 1등급 %d곳" % (s, NAME[c], t1), "등급이 공개된 기관 %d곳" % len(L2), L2, c, ex, 120,
                    "%s %s 평가등급 - 1등급 병원·의원 %d곳" % (s, NAME[c], t1), "%s의 %s 평가 결과입니다. 등급이 공개된 기관 %d곳 중 1등급은 %d곳입니다." % (s, NAME[c], len(L2), t1),
                    [("홈", "/"), (NAME[c], "/item/%s/" % SLUG[c]), (s, "/item/%s/%s/" % (SLUG[c], s))], "0.6", region=True, stat_html=gstat(L2, c))
        for (cc, s, g), L3 in by_ig.items():
            if cc == c and ("ir", c, s, g) in hubs:
                L3 = sorted(L3, key=key(c))
                t1 = sum(1 for r in L3 if r["gr"][c] == 1)
                hub("/item/%s/%s/%s/" % (SLUG[c], s, g), "%s %s %s 평가 1등급 %d곳" % (s, g, NAME[c], t1), "등급이 공개된 기관 %d곳" % len(L3), L3, c, "", 100,
                    "%s %s %s 평가등급 - 1등급 %d곳" % (s, g, NAME[c], t1), "%s %s의 %s 평가 결과입니다. 등급이 공개된 기관 %d곳 중 1등급은 %d곳입니다." % (s, g, NAME[c], len(L3), t1),
                    [("홈", "/"), (NAME[c], "/item/%s/" % SLUG[c]), (s, "/item/%s/%s/" % (SLUG[c], s)), (g, "/item/%s/%s/%s/" % (SLUG[c], s, g))], "0.5", region=False, stat_html=gstat(L3, c))
    cards = "".join('<a class="card" href="/item/%s/"><b>%s</b><span>%d곳</span></a>' % (q(SLUG[c]), esc(NAME[c]), len(by_item_all[c])) for c in ORDER if by_item_all[c])
    write("/item/", layout("/item/", "평가항목별 병원 평가등급", "급성기뇌졸중·암·혈액투석·중환자실·고혈압당뇨병 등 심평원 평가항목별 1등급 병원 목록입니다.", '<div class="page-head"><h1>평가항목별 병원 평가등급</h1></div>' + ad() + '<div class="card-grid">%s</div>' % cards, None, [("홈", "/"), ("평가항목", "/item/")]), "0.8")
    # 지역
    for s, L in by_s.items():
        L2 = sorted(L, key=lambda r: (-sum(1 for v in r["gr"].values() if v == 1), r["name"]))
        gc = collections.Counter(r["g"] for r in L2)
        ex = '<h2 class="group-title">시군구별</h2><div class="chips">%s</div>' % "".join(
            ('<a class="chip" href="/region/%s/%s/">%s <small>%d</small></a>' % (q(s), q(g), esc(g), k)) if ("rg", s, g) in hubs else '<span class="chip">%s <small>%d</small></span>' % (esc(g), k) for g, k in gc.most_common(80))
        ic = [c for c in ORDER if ("is", c, s) in hubs]
        ex += '<h2 class="group-title">평가항목별</h2><div class="chips">%s</div>' % "".join('<a class="chip" href="/item/%s/%s/">%s</a>' % (q(SLUG[c]), q(s), esc(NAME[c])) for c in ic)
        hub("/region/%s/" % s, "%s 병원 평가등급 모아보기" % s, "병원급 이상 의료기관의 평가항목별 등급", L2, None, ex, 150, "%s 병원 평가등급 - 병원급 이상 %d곳" % (s, len(L2)),
            "%s 병원·요양병원·종합병원 %d곳의 심평원 평가등급(1등급 항목 수 순)입니다." % (s, len(L2)), [("홈", "/"), ("지역별", "/region/"), (s, "/region/%s/" % s)], "0.8", stat_html='<p class="lead">등급이 공개된 병원급 이상 의료기관 <b>%d곳</b>입니다. 의원 단위는 평가항목별 페이지에서 볼 수 있습니다.</p>' % len(L2))
    for (s, g), L in by_sg.items():
        if len(L) >= 3:
            L2 = sorted(L, key=lambda r: (-sum(1 for v in r["gr"].values() if v == 1), r["name"]))
            hub("/region/%s/%s/" % (s, g), "%s %s 병원 평가등급" % (s, g), "병원급 이상 의료기관의 평가항목별 등급", L2, None, "", 100, "%s %s 병원 평가등급 - 병원급 이상 %d곳" % (s, g, len(L2)),
                "%s %s의 병원·요양병원 %d곳의 심평원 평가등급입니다." % (s, g, len(L2)), [("홈", "/"), (s, "/region/%s/" % s), (g, "/region/%s/%s/" % (s, g))], "0.6", region=False)
    cards = "".join('<a class="card" href="/region/%s/"><b>%s</b><span>%d곳</span></a>' % (q(s), esc(s), len(L)) for s, L in sorted(by_s.items(), key=lambda t: -len(t[1])))
    write("/region/", layout("/region/", "지역별 병원 평가등급", "시도별 병원급 이상 의료기관의 심평원 평가등급을 확인하세요.", '<div class="page-head"><h1>지역별 병원 평가등급</h1></div>' + ad() + '<div class="card-grid">%s</div>' % cards, None, [("홈", "/"), ("지역별", "/region/")]), "0.8")
    # 홈
    body = ['<div class="hero"><h1>병원 평가등급 찾기</h1><p>건강보험심사평가원 평가 결과를 항목별·지역별로 한눈에</p>'
            '<div class="today-box"><div><small>평가 기관</small><b>%s곳</b></div><div><small>평가항목</small><b>%d개</b></div><div><small>병원급 이상</small><b>%s곳</b></div></div></div>' % ("{:,}".format(len(rows)), len(ORDER), "{:,}".format(len(big))),
            '<div class="search-box"><input id="q" type="search" placeholder="병원 검색 (병원급 이상, 예: 서울대학교병원)" autocomplete="off"><div id="sr" class="sr-list"></div></div>', ad(),
            '<h2 class="group-title">평가항목별</h2><div class="card-grid">%s</div>' % cards,
            '<h2 class="group-title">지역별</h2><div class="card-grid">%s</div>' % "".join('<a class="card" href="/region/%s/"><b>%s</b><span>%d곳</span></a>' % (q(s), esc(s), len(L)) for s, L in sorted(by_s.items(), key=lambda t: -len(t[1]))),
            '<script src="/assets/js/search.js"></script>']
    faq = [("평가등급은 어디서 나온 정보인가요?", "건강보험심사평가원이 의료기관의 진료 적정성을 평가해 공개하고 공공데이터포털에 제공한 병원평가정보입니다."),
           ("1등급이 가장 좋은 건가요?", "네, 1등급이 가장 높고 5등급이 가장 낮습니다. 항목마다 평가 대상과 기간이 달라 서로 단순 비교는 어렵습니다."),
           ("1등급 병원이면 무조건 좋은 병원인가요?", "아닙니다. 평가항목별 결과일 뿐 병원 전체의 의료 수준을 뜻하지 않습니다. 진료과·증상에 맞는 항목을 참고하고 의료진과 상담하세요.")]
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "우아병원등급", "url": BASE + "/", "potentialAction": {"@type": "SearchAction", "target": BASE + "/?q={q}", "query-input": "required name=q"}}]
    write("/", layout("/", "병원 평가등급 - 심평원 평가 1등급 병원·의원 찾기 | 우아병원등급", "건강보험심사평가원 병원평가 결과를 급성기뇌졸중·암·혈액투석·중환자실·고혈압당뇨병 등 항목별, 지역별로 정리했습니다.", "\n".join(body), faq, None, "website", ld), "1.0")
    idx = [[r["name"], r["url"], r["type"], r["s"] + " " + r["g"], ""] for r in big]
    (OUT / "search_index.json").write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    pages_static(asof)
    finish()


def pages_static(asof):
    body = ['<div class="page-head"><h1>병원 평가등급 읽는 법</h1></div>', ad(),
            '<h2 class="group-title">등급은 어떻게 읽나요?</h2><ul class="lead"><li>평가등급은 <b>1등급이 가장 높고 5등급이 가장 낮습니다</b>.</li><li>항목마다 평가 대상 기관·기간·방법이 달라 <b>다른 항목의 등급을 단순 비교할 수 없습니다</b>.</li><li>등급이 없는 항목은 평가 대상이 아니거나 등급이 산정되지 않은 경우입니다.</li></ul>',
            '<h2 class="group-title">항목별로 무엇을 평가하나요?</h2><ul class="lead">%s</ul>' % "".join("<li><b>%s</b> — %s</li>" % (esc(NAME[c]), esc(DESC[c])) for c in ORDER),
            '<div class="note-box">평가등급은 병원 전체의 의료 수준을 뜻하지 않습니다. 증상·진료과에 맞는 항목을 참고하되 진료 선택은 의료진과 상담하세요.</div>']
    write("/guide/", layout("/guide/", "병원 평가등급 읽는 법", "심평원 병원 평가등급(1~5등급)의 의미와 평가항목별 설명입니다.", "\n".join(body), None, [("홈", "/"), ("등급 읽는 법", "/guide/")]), "0.5")
    body = ['<div class="page-head"><h1>데이터 설명</h1></div>', '<p class="lead">우아병원등급은 공공데이터포털의 <b>건강보험심사평가원_병원평가정보서비스</b>(병원평가상세등급조회)를 정리합니다(데이터 수집일 %s). 요양기관별 평가등급이 공개된 항목만 싣고, 값 체계를 공식 문서로 확인하지 못한 천식 항목은 싣지 않았습니다. 병원 기본 정보는 우아병원·hosppass와 같은 심평원 병원정보를 사용합니다.</p>' % esc(asof)]
    write("/about/", layout("/about/", "데이터 설명", "우아병원등급이 사용하는 심평원 병원평가정보 데이터와 정리 방법을 설명합니다.", "\n".join(body), None, [("홈", "/"), ("데이터 설명", "/about/")]), "0.3")
    body = ['<div class="page-head"><h1>개인정보처리방침</h1></div>', '<p class="lead">우아병원등급은 회원가입·로그인 없이 이용하며 개인정보를 수집하지 않습니다. 사이트 개선을 위해 Google Analytics를 사용하고, 광고 게재를 위해 Google AdSense와 쿠팡 파트너스를 사용하며 이 과정에서 쿠키가 사용될 수 있습니다.</p>']
    write("/privacy/", layout("/privacy/", "개인정보처리방침", "우아병원등급 개인정보처리방침", "\n".join(body), None, [("홈", "/"), ("개인정보처리방침", "/privacy/")]), sitemap=False)


def finish():
    shutil.copytree(ROOT / "assets", OUT / "assets")
    for nf in ROOT.glob("naver*.html"):
        shutil.copy(nf, OUT / nf.name)
    today = TODAY.isoformat()
    urls = "".join("<url><loc>%s%s</loc><lastmod>%s</lastmod><priority>%s</priority></url>" % (BASE, q(p), today, pr) for p, pr in WRITTEN)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % urls, encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE, encoding="utf-8")
    (OUT / "CNAME").write_text("wooahgrade.wooahouse.com\n", encoding="utf-8")
    nf = layout("/404.html", "페이지를 찾을 수 없습니다", "요청한 페이지를 찾을 수 없습니다.", '<div class="page-head"><h1>페이지를 찾을 수 없습니다</h1></div><div class="chips"><a class="chip" href="/">홈으로</a><a class="chip" href="/item/">평가항목</a><a class="chip" href="/region/">지역별</a></div>', None, None, noindex=True)
    (OUT / "404.html").write_text(nf, encoding="utf-8")
    print("페이지", len(WRITTEN), "(sitemap)")


if __name__ == "__main__":
    build()
