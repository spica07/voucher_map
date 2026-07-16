# -*- coding: utf-8 -*-
"""organs_list.json + detail_cache.json -> organs_merged.json
목록(organCd·name·kind·aiYn·homepage)과 상세페이지(주소·전화·분야)를 병합하고
주소/분야 텍스트를 정제한다. 좌표는 geocode.py에서 별도로 채운다.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TOOLS = Path(__file__).resolve().parent
LIST_SRC = TOOLS / "organs_list.json"
DETAIL_SRC = TOOLS / "detail_cache.json"
OUT = TOOLS / "organs_merged.json"

CATEGORY_ORDER = [
    "학력보완교육", "성인 문해교육", "직업능력 향상교육",
    "성인 진로개발역량 향상교육", "인문교양교육", "문화예술교육", "시민참여교육",
]

DISTRICT_ORDER = [
    "강남구", "강동구", "강북구", "강서구", "관악구", "광진구", "구로구", "금천구",
    "노원구", "도봉구", "동대문구", "동작구", "마포구", "서대문구", "서초구", "성동구",
    "성북구", "송파구", "양천구", "영등포구", "용산구", "은평구", "종로구", "중구", "중랑구",
]


def clean_address(raw):
    if not raw:
        return ""
    a = raw.strip()
    a = re.sub(r"^\(\d{5}\)\s*", "", a)  # 우편번호 제거
    a = re.sub(r"\s*(지도보기|홈페이지)\s*$", "", a)  # 목록 버튼 라벨이 붙어온 꼬리 제거
    a = " ".join(a.split())
    # 원본 데이터 입력 오류로 도로명주소가 그대로 중복 입력된 경우(예: "OO시 OO구 OO로 6 OO시 OO구 OO로 6 상세명")
    # 마지막 "서울특별시" 등장 지점부터를 채택해 중복분을 제거한다
    if a.count("서울특별시") > 1:
        a = a[a.rindex("서울특별시"):]
    return a


def extract_district(address):
    for d in DISTRICT_ORDER:
        if d in address:
            return d
    return ""


def parse_categories(raw):
    if not raw:
        return []
    # 괄호 안 세부항목(쉼표 포함 가능)을 통째로 제거한 뒤 콤마로 분리한다
    stripped = re.sub(r"\([^)]*\)", "", raw)
    out = []
    for seg in stripped.split(","):
        seg = seg.strip()
        if not seg:
            continue
        matched = next((c for c in CATEGORY_ORDER if seg == c or seg.startswith(c)), None)
        cat = matched or seg
        if cat not in out:
            out.append(cat)
    return out


def clean_phone(raw):
    if not raw:
        return ""
    cleaned = re.sub(r"\s*-\s*", "-", raw.strip())
    if re.fullmatch(r"-+", cleaned):  # 전화번호 미기재를 "-"로 표시한 경우
        return ""
    return cleaned


def main():
    list_items = json.loads(LIST_SRC.read_text(encoding="utf-8"))
    detail = json.loads(DETAIL_SRC.read_text(encoding="utf-8"))

    merged = []
    missing_detail = 0
    for it in list_items:
        d = detail.get(it["organCd"])
        if not d:
            missing_detail += 1
            d = {}
        address = clean_address(d.get("주소", "") or it.get("addr", ""))
        district = extract_district(address) or extract_district(it.get("region", ""))
        merged.append({
            "organCd": it["organCd"],
            "name": it["name"],
            "district": district,
            "address": address,
            "phone": clean_phone(d.get("전화번호", "")),
            "kind": it["kind"],
            "aiYn": it["aiYn"] == "Y",
            "categories": parse_categories(d.get("기관 운영강좌 유형", "")),
            "homepage": it.get("homepage", ""),
        })

    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"병합 완료: {len(merged)}건 -> {OUT} (상세 누락 {missing_detail}건)")

    no_district = sum(1 for m in merged if not m["district"])
    print(f"자치구 추출 실패: {no_district}건")


if __name__ == "__main__":
    main()
