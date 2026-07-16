# -*- coding: utf-8 -*-
"""organs_merged.json -> assets/js/data.js
카카오 로컬 API로 주소를 지오코딩한다. 주소검색 실패 시 기관명 키워드검색으로 2차 보정하고,
그래도 실패하면 자치구 중심 + 결정적 지터로 근사 좌표를 쓴다.
캐시 파일(kakao_cache.json)로 재실행 시 이미 조회한 질의는 건너뛴다.
인증키는 .env(KAKAO_REST_KEY)에서 읽는다.
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
CACHE_FILE = TOOLS / "kakao_cache.json"
OUT = TOOLS.parent / "assets" / "js" / "data.js"


def load_kakao_key():
    env_path = TOOLS.parent / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("KAKAO_REST_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(".env 에서 KAKAO_REST_KEY를 찾을 수 없습니다.")

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

# 카카오 주소검색에서 "정밀"로 인정할 address_type (동/지역 단위는 제외)
PRECISE_ADDRESS_TYPES = {"ROAD_ADDR", "REGION_ADDR"}
KAKAO_ADDR_URL = "https://dapi.kakao.com/v2/local/search/address.json"
KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
REQUEST_SLEEP = 0.05  # 카카오 로컬은 QPS 여유가 커 최소 지연만 둔다

session = requests.Session()
session.headers["Authorization"] = "KakaoAK " + load_kakao_key()

cache = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}


def save_cache():
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def in_seoul(lat, lng):
    return SEOUL_BOX[0] <= lat <= SEOUL_BOX[1] and SEOUL_BOX[2] <= lng <= SEOUL_BOX[3]


def _kakao_get(url, query):
    """카카오 로컬 API 호출. 실패 시 None(에러)/빈 리스트(결과없음)를 구분해 반환한다."""
    for attempt in range(3):
        try:
            r = session.get(url, params={"query": query}, timeout=15)
            if r.status_code == 429:  # 초당 한도 초과 → 잠시 쉬고 재시도
                time.sleep(1.0)
                continue
            r.raise_for_status()
            time.sleep(REQUEST_SLEEP)
            return r.json().get("documents", [])
        except requests.RequestException as e:
            if attempt == 2:
                print(f"  ! 요청 실패: {query!r} ({e})")
                return None
            time.sleep(0.5)
    return None


def kakao_address(query):
    """주소검색: 정밀(ROAD_ADDR/REGION_ADDR) & 서울 범위 내 첫 결과의 (lat, lng)."""
    key = "addr:" + query
    if key not in cache:
        docs = _kakao_get(KAKAO_ADDR_URL, query)
        if docs is None:
            return None  # 에러는 캐시하지 않는다
        hit = None
        for d in docs:
            if d.get("address_type") not in PRECISE_ADDRESS_TYPES:
                continue
            lat, lng = float(d["y"]), float(d["x"])
            if in_seoul(lat, lng):
                hit = {"lat": lat, "lng": lng}
                break
        cache[key] = hit
        save_cache()
    return cache[key]


def kakao_keyword(query):
    """키워드(기관명)검색: 서울 범위 내 첫 결과의 (lat, lng)."""
    key = "kw:" + query
    if key not in cache:
        docs = _kakao_get(KAKAO_KEYWORD_URL, query)
        if docs is None:
            return None
        hit = None
        for d in docs:
            lat, lng = float(d["y"]), float(d["x"])
            if in_seoul(lat, lng):
                hit = {"lat": lat, "lng": lng}
                break
        cache[key] = hit
        save_cache()
    return cache[key]


def clean_query(addr):
    a = re.sub(r"\([^)]*\)", "", addr)
    a = re.sub(r"\d+층.*$", "", a)  # "N층 상세정보" 꼬리 제거
    a = re.sub(r"\s+", " ", a).strip()
    return a


def geocode_one(item):
    addr = item["address"]
    district = item["district"]
    name = item["name"]
    # 1) 주소검색: 원주소 → 괄호/층수 제거한 주소
    seen = set()
    for q in (addr, clean_query(addr) if addr else ""):
        if not q or q in seen:
            continue
        seen.add(q)
        hit = kakao_address(q)
        if hit:
            return hit["lat"], hit["lng"], "geocoded"
    # 2) 키워드검색: 기관명 + 자치구 (동명 구분)
    if name:
        hit = kakao_keyword(f"{name} {district}".strip())
        if hit:
            return hit["lat"], hit["lng"], "geocoded"
    # 3) 폴백: 자치구 중심 + 결정적 지터
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
            "geoApprox": geo != "geocoded",
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
