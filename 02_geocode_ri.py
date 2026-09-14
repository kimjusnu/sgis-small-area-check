"""주소 목록 지오코딩(주소를 좌표로 변환) + UTM-K(EPSG:5179) → 경위도(EPSG:4326) 변환 + 범위 검사.

사용: python 02_geocode_ri.py 주소목록.csv --bbox 127.4 35.9 128.3 36.5
  주소목록.csv: 「address」 열 필수, 나머지 열은 그대로 옮겨 적음
  --bbox: 경도최소 위도최소 경도최대 위도최대 (해당 시군 범위)

산출: 입력파일명_좌표.csv, 범위 밖 좌표와 실패 주소는 화면에 출력
"""
import argparse
import csv
import time
from pathlib import Path

from sgis_common import access_token, api


def geocode(token, address):
    res = api("/addr/geocode.json", accessToken=token, address=address)
    data = (res.get("result") or {}).get("resultdata") or []
    if not data or not data[0].get("x"):
        return None
    x, y = data[0]["x"], data[0]["y"]
    tc = api("/transformation/transcoord.json", accessToken=token,
             src="5179", dst="4326", posX=x, posY=y).get("result") or {}
    return {"utmk_x": x, "utmk_y": y,
            "lon": round(float(tc.get("posX", 0)), 6), "lat": round(float(tc.get("posY", 0)), 6)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--bbox", nargs=4, type=float, required=True)
    a = ap.parse_args()
    lon0, lat0, lon1, lat1 = a.bbox
    src = Path(a.csv)
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    token = access_token()
    done, failed = [], []
    for r in rows:
        g = geocode(token, r["address"])
        if g is None:
            failed.append(r["address"])
        else:
            done.append({**r, **g})
        time.sleep(0.12)
    if not done:
        raise RuntimeError("지오코딩 결과가 없습니다")
    out = src.with_name(src.stem + "_좌표.csv")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(done[0].keys()))
        w.writeheader()
        w.writerows(done)
    outside = [d for d in done if not (lon0 <= d["lon"] <= lon1 and lat0 <= d["lat"] <= lat1)]
    print(f"성공 {len(done)} · 실패 {len(failed)} · 범위 밖 {len(outside)} → {out.name}")
    for d in outside:
        print("  범위 밖:", d["address"], d["lon"], d["lat"])
    for addr in failed:
        print("  실패:", addr)


if __name__ == "__main__":
    main()
