# -*- coding: utf-8 -*-
"""organs_list.json 의 organCd마다 상세페이지(useVcOrganView.do)를 조회해
주소/전화번호/기관 운영강좌 유형을 detail_cache.json 에 누적 저장한다.
중단 후 재실행하면 이미 받은 항목은 건너뛴다(캐시 기반, 재시도 가능).
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

TOOLS = Path(__file__).resolve().parent
LIST_SRC = TOOLS / "organs_list.json"
CACHE = TOOLS / "detail_cache.json"

URL = "https://www.lllcard.kr/guide/useVcOrganView.do"
DELAY = 0.15


def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache):
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_detail(organ_cd):
    data = urllib.parse.urlencode({"organCd": organ_cd}).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=data,
        method="POST",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.lllcard.kr/reg/seoul/guide/useVcOrgan.do",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8")


def parse_detail(html):
    soup = BeautifulSoup(html, "html.parser")
    fields = {}
    for tr in soup.find_all("tr"):
        th = tr.find("th")
        td = tr.find("td")
        if th and td:
            label = th.get_text(" ", strip=True)
            val = " ".join(td.get_text(" ", strip=True).split())
            fields[label] = val
    return fields


def main():
    items = json.loads(LIST_SRC.read_text(encoding="utf-8"))
    cache = load_cache()
    total = len(items)
    fetched = 0
    failed = []

    for i, it in enumerate(items, 1):
        cd = it["organCd"]
        if cd in cache:
            continue
        try:
            html = fetch_detail(cd)
            fields = parse_detail(html)
            cache[cd] = fields
            fetched += 1
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"[{i}/{total}] 실패: {it['name']} ({e})")
            failed.append(cd)
            continue

        if fetched % 50 == 0:
            save_cache(cache)
            print(f"[{i}/{total}] 진행 중... ({fetched}건 신규 수집)")

        time.sleep(DELAY)

    save_cache(cache)
    print(f"완료: 캐시 총 {len(cache)}건 (이번 실행 신규 {fetched}건), 실패 {len(failed)}건")
    if failed:
        print("실패 목록:", failed)


if __name__ == "__main__":
    main()
