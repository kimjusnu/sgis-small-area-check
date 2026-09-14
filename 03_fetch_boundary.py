"""행정동 경계(hadmarea.geojson) 수집 → UTM-K(EPSG:5179)를 경위도(EPSG:4326)로 변환해 저장.

사용: python 03_fetch_boundary.py 34011 34012 --year 2024
  인자: SGIS 시군구 코드(여러 개 가능). year는 hadmarea 명세의 필수 인자
  ※ 집계구 경계(statsarea.geojson)는 명세에 year 인자가 없음

필요 패키지: pyproj
산출: boundary_<코드들>_<연도>_wgs84.geojson
"""
import argparse
import json

from pyproj import Transformer

from sgis_common import access_token, api

TR = Transformer.from_crs("EPSG:5179", "EPSG:4326", always_xy=True)


def reproject(coords):
    if isinstance(coords[0], (int, float)):
        return list(TR.transform(coords[0], coords[1]))
    return [reproject(c) for c in coords]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("codes", nargs="+")
    ap.add_argument("--year", required=True)
    a = ap.parse_args()
    token = access_token()
    features = []
    for cd in a.codes:
        gj = api("/boundary/hadmarea.geojson", accessToken=token, year=a.year,
                 adm_cd=cd, low_search="1")
        if str(gj.get("errCd", "0")) != "0":
            raise RuntimeError(f"{cd}: errCd {gj.get('errCd')} {gj.get('errMsg')}")
        feats = gj.get("features") or []
        print(f"{cd}: {len(feats)}개")
        features += [{**f, "geometry": {**f["geometry"],
                                        "coordinates": reproject(f["geometry"]["coordinates"])}}
                     for f in feats]
    name = f"boundary_{'_'.join(a.codes)}_{a.year}_wgs84.geojson"
    with open(name, "w", encoding="utf-8") as fp:
        json.dump({"type": "FeatureCollection", "features": features}, fp, ensure_ascii=False)
    print(f"저장: {name} ({len(features)}개)")


if __name__ == "__main__":
    main()
