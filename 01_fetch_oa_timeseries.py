"""시군구 하나의 읍면동·집계구 인구·가구·주택·사업체 연도별 수집 + 기본 점검.

사용: python 01_fetch_oa_timeseries.py 33540 --from 2015 --to 2024
  33540 = SGIS 시군구 코드(충북 영동군). 행정안전부 코드(43740)를 넣으면 errCd -100

산출(output/<코드>/):
  raw/pop_<읍면동코드>_<연도>.json   원본 응답
  oa_<코드>.csv / emd_<코드>.csv      집계구 / 읍면동 표
  check_<코드>.csv                    점검 결과(점검표 1·2·4번)
"""
import argparse
import csv
import json
import time
from pathlib import Path

from sgis_common import access_token, api

FIELDS = ["tot_ppltn", "avg_age", "ppltn_dnsty", "aged_child_idx", "oldage_suprt_per",
          "juv_suprt_per", "tot_family", "avg_fmember_cnt", "tot_house", "corp_cnt",
          "employee_cnt"]
SUM_FIELDS = ["tot_ppltn", "tot_family", "tot_house", "corp_cnt", "employee_cnt"]


def children(token, adm_cd, year):
    r = api("/stats/population.json", accessToken=token, year=year, adm_cd=adm_cd, low_search="1")
    if str(r.get("errCd")) != "0":
        raise RuntimeError(f"{adm_cd} {year}: errCd {r.get('errCd')} {r.get('errMsg')}")
    return r.get("result") or []


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def write_csv(path, rows, cols):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def collect(token, sgg, years, out):
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    emd_list = children(token, sgg, years[-1])
    oa_rows, emd_rows = [], []
    for y in years:
        emd_rows += [{"year": y, "adm_cd": e["adm_cd"], **{f: e.get(f) for f in FIELDS}}
                     for e in children(token, sgg, y)]
        for e in emd_list:
            p = raw / f"pop_{e['adm_cd']}_{y}.json"
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
            else:
                data = children(token, e["adm_cd"], y)
                p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                time.sleep(0.2)
            oa_rows += [{"year": y, "emd_cd": e["adm_cd"], "oa_cd": o["adm_cd"],
                         **{f: o.get(f) for f in FIELDS}} for o in data]
    return oa_rows, emd_rows


def check_jumps(oa_rows, threshold=50.0):
    """점검 2: 전년 대비 ±threshold% 이상 변동 칸. 인구/가구 비를 함께 적어 집단가구 여부를 본다."""
    by = {}
    for r in oa_rows:
        by.setdefault(r["oa_cd"], {})[r["year"]] = r
    out = []
    for oa, ys in by.items():
        keys = sorted(ys)
        for a, b in zip(keys, keys[1:]):
            p0, p1 = num(ys[a]["tot_ppltn"]), num(ys[b]["tot_ppltn"])
            if p0 and p1 is not None and abs(p1 - p0) / p0 * 100 >= threshold:
                fam = num(ys[b]["tot_family"])
                out.append({"check": "연도간변동", "oa_cd": oa, "year": b, "field": "tot_ppltn",
                            "value": f"{p0:.0f}→{p1:.0f}",
                            "note": f"인구/가구 {p1 / fam:.1f}" if fam else "가구 N/A"})
    return out


def check_sums(oa_rows, emd_rows):
    """점검 4: 집계구 합계와 읍면동 값 대조. N/A 칸이 있는 곳의 차이 = 가려진 값의 합."""
    emd = {(r["year"], r["adm_cd"]): r for r in emd_rows}
    agg = {}
    for r in oa_rows:
        k = (r["year"], r["emd_cd"])
        a = agg.setdefault(k, {f: [0.0, 0] for f in SUM_FIELDS})
        for f in SUM_FIELDS:
            v = num(r[f])
            if v is None:
                a[f][1] += 1
            else:
                a[f][0] += v
    out = []
    for k, a in agg.items():
        for f in SUM_FIELDS:
            total = num(emd.get(k, {}).get(f))
            s, na = a[f]
            if total is None or (na == 0 and total == s):
                continue
            out.append({"check": "상하위합계", "oa_cd": k[1], "year": k[0], "field": f,
                        "value": f"읍면동 {total:.0f} - 집계구합 {s:.0f} = {total - s:.0f}",
                        "note": f"N/A {na}칸" + (" (N/A 칸 실제값 합계 0)" if na and total == s else "")})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sgg", help="SGIS 시군구 코드 5자리")
    ap.add_argument("--from", dest="y0", type=int, default=2015)
    ap.add_argument("--to", dest="y1", type=int, default=2024)
    ap.add_argument("--out", default="output")
    a = ap.parse_args()
    years = [str(y) for y in range(a.y0, a.y1 + 1)]
    out = Path(a.out) / a.sgg
    token = access_token()
    oa_rows, emd_rows = collect(token, a.sgg, years, out)
    write_csv(out / f"oa_{a.sgg}.csv", oa_rows, ["year", "emd_cd", "oa_cd"] + FIELDS)
    write_csv(out / f"emd_{a.sgg}.csv", emd_rows, ["year", "adm_cd"] + FIELDS)

    codes = {}
    for r in oa_rows:
        codes.setdefault(r["year"], set()).add(r["oa_cd"])
    base = codes[years[0]]
    checks = [{"check": "코드안정성", "oa_cd": "", "year": y, "field": "oa_cd",
               "value": f"{len(s)}개", "note": f"기준연도와 공통 {len(s & base)}개"}
              for y, s in sorted(codes.items())]
    checks += check_jumps(oa_rows) + check_sums(oa_rows, emd_rows)
    write_csv(out / f"check_{a.sgg}.csv", checks, ["check", "oa_cd", "year", "field", "value", "note"])
    print(f"집계구 {len(oa_rows)}행 · 읍면동 {len(emd_rows)}행 · 점검 {len(checks)}건 → {out}")


if __name__ == "__main__":
    main()
