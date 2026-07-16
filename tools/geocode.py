# -*- coding: utf-8 -*-
"""organs_merged.json -> assets/js/data.js
Nominatim으로 주소를 지오코딩한다. 실패 시 자치구 중심 + 결정적 지터로 근사 좌표를 쓴다.
캐시 파일(geocode_cache.json)로 재실행 시 이미 조회한 주소는 건너뛴다.
"""
import json
import re
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

TOOLS = Path(__file__).resolve().parent
SRC = TOOLS / "organs_merged.json"
CACHE_FILE = TOOLS / "geocode_cache.json"
OUT = TOOLS.parent / "assets" / "js" / "data.js"

SEOUL_CENTERS = {
    "종로구": (37.5735, 126.9790), "중구": (37.5641, 126.9979), "용산구": (37.5324, 126.9900),
    "성동구": (37.5634, 127.0369), "광진구": (37.5385, 127.0823), "동대문구": (37.5744, 127.0396),
    "중랑구": (37.6063, 127.0927), "성북구": (37.5894, 127.0167), "강북구": (37.6396, 127.0257),
    "도봉구": (37.6688, 127.0471), "노원구": (37.6542, 127.0568), "은평구": (37.6027, 126.9291),
    "서대문구": (37.5791, 126.9368), "마포구": (37.5663, 126.9019), "양천구": (37.5170, 126.8664),
    "강서구": (37.5509, 126.8495), "구로구": (37.4954, 126.8874), "금천구": (37.4569, 126.8955),
    "영등포구": (37.5264, 126.8962), "동작구": (37.5124, 126.9393), "관악구": (37.4784, 126.9516),
    "서초구": (37.4837, 127.0324), "강남구": (37.5172, 127.0473), "송파구": (37.5145, 127.1059),
    "강동구": (37.5301, 127.1237),
}
SEOUL_BOX = (37.41, 37.72, 126.76, 127.20)

session = requests.Session()
session.headers["User-Agent"] = "voucher-map/1.0"

cache = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}


def save_cache():
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def in_seoul(lat, lng):
    return SEOUL_BOX[0] <= lat <= SEOUL_BOX[1] and SEOUL_BOX[2] <= lng <= SEOUL_BOX[3]


def is_precise_result(item):
    category = item.get("category")
    result_type = item.get("type")
    if category in {"boundary", "highway"}:
        return False
    if category == "place" and result_type != "house":
        return False
    if result_type in {
        "administrative", "quarter", "suburb", "neighbourhood", "city", "town",
        "village", "road", "primary", "secondary", "tertiary", "residential",
        "service", "bus_stop",
    }:
        return False
    return True


def nominatim(query):
    if query in cache:
        return [item for item in cache[query] if is_precise_result(item)]
    try:
        r = session.get(
            "https://nominatim.openstreetmap.org/search",
            params={"format": "jsonv2", "q": query, "countrycodes": "kr",
                    "accept-language": "ko", "addressdetails": 1, "limit": 3},
            timeout=15,
        )
        r.raise_for_status()
        results = []
        for x in r.json():
            lat, lng = float(x["lat"]), float(x["lon"])
            item = {
                "lat": lat, "lng": lng,
                "category": x.get("category") or x.get("class"),
                "type": x.get("type"),
            }
            if in_seoul(lat, lng) and is_precise_result(item):
                results.append(item)
    except requests.RequestException as e:
        print(f"  ! 요청 실패: {query!r} ({e})")
        results = None
    if results is not None:
        cache[query] = results
        save_cache()
    time.sleep(1.1)
    return results or []


def clean_query(addr):
    a = re.sub(r"\([^)]*\)", "", addr)
    a = re.sub(r"\d+층.*$", "", a)  # "N층 상세정보" 꼬리 제거
    a = re.sub(r"\s+", " ", a).strip()
    return a


def road_only(addr):
    """도로명+번지까지만 남기고 동/호/층 등 상세주소를 제거한다.
    (건물 내 동/호수가 붙으면 Nominatim이 매칭에 실패하는 경우가 많다)"""
    m = re.search(r"^.*?(?:로|길)\s*\d+(?:-\d+)?", addr)
    return m.group(0) if m else ""


def geocode_one(item):
    addr = item["address"]
    district = item["district"]
    queries = []
    if addr:
        queries.append(addr)
        cq = clean_query(addr)
        if cq and cq != addr:
            queries.append(cq)
        rq = road_only(addr)
        if rq and rq not in (addr, cq):
            queries.append(rq)
    seen = set()
    for q in queries:
        if q in seen or not q:
            continue
        seen.add(q)
        results = nominatim(q)
        if results:
            return results[0]["lat"], results[0]["lng"], "geocoded"
    clat, clng = SEOUL_CENTERS.get(district, (37.5665, 126.9780))
    seed = sum(ord(c) for c in item["organCd"])
    jlat = ((seed * 37) % 100 - 50) * 0.00028
    jlng = ((seed * 61) % 100 - 50) * 0.00034
    return round(clat + jlat, 6), round(clng + jlng, 6), "approx"


def main():
    items = json.loads(SRC.read_text(encoding="utf-8"))
    geocoded = approx = 0
    out_items = []
    for i, it in enumerate(items, 1):
        lat, lng, geo = geocode_one(it)
        if geo == "geocoded":
            geocoded += 1
        else:
            approx += 1
        out_items.append({
            "id": i,
            "name": it["name"],
            "district": it["district"],
            "address": it["address"],
            "phone": it["phone"],
            "kind": it["kind"],
            "aiYn": it["aiYn"],
            "categories": it["categories"],
            "homepage": it["homepage"],
            "lat": lat,
            "lng": lng,
        })
        if i % 50 == 0:
            print(f"[{i}/{len(items)}] geocoded={geocoded} approx={approx}")

    from datetime import date
    meta = {"surveyDate": date.today().isoformat(), "total": len(out_items)}

    js = (
        "/* 서울 평생학습이용권 사용처 데이터 — 자동 생성 파일 */\n"
        "window.VOUCHERS = " + json.dumps(out_items, ensure_ascii=False, indent=2) + ";\n"
        "window.DATA_META = " + json.dumps(meta, ensure_ascii=False, indent=2) + ";\n"
    )
    OUT.write_text(js, encoding="utf-8")
    print(f"완료: {len(out_items)}건 (지오코딩 {geocoded} / 근사 {approx}) -> {OUT}")


if __name__ == "__main__":
    main()
