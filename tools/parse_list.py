# -*- coding: utf-8 -*-
"""list_raw.html(검색 결과 목록) -> organs_list.json
목록 화면에는 기관명/지역(구)/기관구분/AI디지털이용권여부와,
'지도보기' 버튼이 있는 기관에 한해 주소가 포함된다. (없는 기관은 상세페이지에서 보충)
"""
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

TOOLS = Path(__file__).resolve().parent
SRC = TOOLS / "list_raw.html"
OUT = TOOLS / "organs_list.json"

html = SRC.read_text(encoding="utf-8")
soup = BeautifulSoup(html, "html.parser")
table = soup.find("table", id="list")
rows = table.find("tbody").find_all("tr", recursive=False)

items = []
for tr in rows:
    tds = tr.find_all("td", recursive=False)
    a = tds[0].find("a")
    name = a.get_text(strip=True) if a else ""
    href = a.get("href", "") if a else ""
    m = re.search(r"fnEduEetail\('([^']+)'\)", href)
    organ_cd = m.group(1) if m else ""

    region = " ".join(tds[1].get_text(" ", strip=True).split())
    kind = tds[2].get_text(strip=True)
    ai_yn = tds[3].get_text(strip=True)

    addr = detail_addr = ""
    map_a = tds[4].find("a")
    if map_a:
        mm = re.search(
            r"fnOpenModalMapPopup\('([^']*)',\s*'([^']*)',\s*'([^']*)'\)",
            map_a.get("href", ""),
        )
        if mm:
            addr = " ".join(mm.group(2).split())
            detail_addr = " ".join(mm.group(3).split())

    homepage = ""
    home_a = tds[5].find("a")
    if home_a:
        hm = re.search(r"checkUrl\('([^']*)'\)", home_a.get("href", ""))
        if hm:
            homepage = hm.group(1).strip()

    if not organ_cd:
        continue
    items.append({
        "organCd": organ_cd,
        "name": name,
        "region": region,
        "kind": kind,
        "aiYn": ai_yn,
        "addr": addr,
        "detailAddr": detail_addr,
        "homepage": homepage,
    })

OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"파싱 완료: {len(items)}건 -> {OUT}")
