# 우아병원등급 (wooahgrade)

건강보험심사평가원 병원평가정보서비스(data.go.kr 15094093, `apis.data.go.kr/B551182/hospAsmInfoService1/getHospAsmInfo1`, 요양기관별 평가등급 37,435곳)로 만든 병원 평가등급 사이트(Python 정적 생성기). https://wooahgrade.wooahouse.com

- `scripts/fetch_data.py` — 전체 평가등급을 38호출로 받아 `data/grades.json.gz` 저장(월 1회 Actions). `scripts/prepare_hospitals.py` — 로컬 1회: hosppass 병원 정보·우아병원 페이지 경로를 `data/hosp_min.json.gz`로 저장(신규 기관은 주소 파싱으로 대체).
- 평가항목 코드(`asmGrd01~24`)는 API 문서(openapi.do 페이지의 응답 스키마) 기준. **천식(asmGrd16)은 값 체계('양호'·0)가 달라 제외**. 02·11은 없음.
- `scripts/build_site.py` — 평가항목 허브, 항목×시도·시군구 허브, 병원급 이상(의원 제외) 개별 평가 페이지, 지역 허브, 검색 인덱스. 의원은 항목 표에서 우아병원(wooahospital) 페이지로 연결.
- Actions: push 시 빌드, 매월 5일 KST 05:00 수집→커밋→빌드. 시크릿 `API_KEY`. 네이버 소유확인 토큰은 `scripts/common.py` `NAVER_TOKEN`.
