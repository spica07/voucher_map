# -*- coding: utf-8 -*-
"""서울시 평생학습이용권 사용처 목록 전체를 가져와 원본 HTML로 저장한다.
출처: https://www.lllcard.kr/reg/seoul/guide/useVcOrgan.do (POST 검색 결과)
"""
import sys
import urllib.request
import urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TOOLS = Path(__file__).resolve().parent
OUT = TOOLS / "list_raw.html"

URL = "https://www.lllcard.kr/guide/useVcOrganListAjax.do"
PAGE_SIZE = 2000  # 전체 974건을 한 번에 받기 위한 넉넉한 값

data = urllib.parse.urlencode({
    "searchSidoCd": "11",  # 서울특별시
    "searchLocalCd": "",
    "searchOrganNm": "",
    "pageIndex": "1",
    "pageSize": str(PAGE_SIZE),
    "searchChkCates": "",
}).encode("utf-8")

req = urllib.request.Request(
    URL,
    data=data,
    method="POST",
    headers={
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.lllcard.kr/reg/seoul/guide/useVcOrgan.do",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    },
)

with urllib.request.urlopen(req, timeout=60) as res:
    html = res.read().decode("utf-8")

OUT.write_text(html, encoding="utf-8")
print(f"저장 완료: {OUT} ({len(html):,} bytes)")
