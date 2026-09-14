"""행정안전부 법정동코드 시군구(5자리) → SGIS 시군구 코드 대응표 만들기.

공식 연계표: 공공데이터포털 15136368 「국가데이터처_법정동 연계정보」 CSV(cp949)
  열: 시도명, 시군구명, 행정동명, 법정동명, 행정구역코드, 행정동코드, 법정동코드, 개정일자, 연결번호
  행정구역코드 앞 5자리 = SGIS 시군구 코드

주의: 연계표에는 2021년 코드 범위 변경 전후 코드가 함께 들어 있어 법정동 시군구 하나에
      후보가 2개 나오는 경우가 있다(예: 43720 보은군 → 33320, 33520).
      SGIS 응답에 실제로 있는 코드 1개만 남긴다.

사용: python 04_link_sgg_codes.py 연계정보.csv --year 2024
산출: sgg_code_link.csv (법정동시군구, 시도명, 시군구명, SGIS코드, 후보수, 판정)
"""
import argparse
import csv
from collections import defaultdict

from sgis_common import access_token, api


def load_link(path):
    link, names = defaultdict(set), {}
    with open(path, encoding="cp949", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            k = row["법정동코드"][:5]
            link[k].add(row["행정구역코드"][:5])
            names[k] = (row["시도명"], row["시군구명"])
    return link, names


def sgis_sgg_codes(token, year):
    sido = api("/stats/population.json", accessToken=token, year=year, low_search="1")["result"]
    codes = set()
    for s in sido:
        for g in api("/stats/population.json", accessToken=token, year=year,
                     adm_cd=s["adm_cd"], low_search="1").get("result") or []:
            codes.add(g["adm_cd"])
    return codes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("link_csv")
    ap.add_argument("--year", default="2024")
    a = ap.parse_args()
    link, names = load_link(a.link_csv)
    valid = sgis_sgg_codes(access_token(), a.year)
    rows = []
    for k in sorted(link):
        hit = sorted(link[k] & valid)
        verdict = "확정" if len(hit) == 1 else ("SGIS에 없음" if not hit else "후보 복수")
        rows.append({"법정동시군구": k, "시도명": names[k][0], "시군구명": names[k][1],
                     "SGIS코드": hit[0] if len(hit) == 1 else "|".join(hit),
                     "후보수": len(link[k]), "판정": verdict})
    with open("sgg_code_link.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    count = defaultdict(int)
    for r in rows:
        count[r["판정"]] += 1
    print(f"법정동 시군구 {len(rows)}개 · SGIS {a.year} 시군구 {len(valid)}개 · {dict(count)}")


if __name__ == "__main__":
    main()
