# SGIS 소지역 통계 연도 비교 전 점검

국가데이터처 SGIS OpenAPI3로 읍면동·집계구 통계를 연도별로 받을 때, 연도 비교에 들어가기 전에
확인할 항목 6개(`점검표.csv`)와 그중 반복 작업을 줄이는 수집·점검 코드 4종입니다.

## 준비

- Python 3.10 이상, `03_fetch_boundary.py`만 `pyproj` 필요
- SGIS 개발지원센터에서 발급받은 서비스 ID·보안 Key를 환경변수 또는 실행 위치의 `.env`에 둡니다
  (`.env.example` 참고). 코드와 결과 파일에는 키를 적지 않습니다

## 파일

| 파일 | 하는 일 | 점검표 번호 |
|---|---|---|
| `01_fetch_oa_timeseries.py` | 시군구 하나의 읍면동·집계구 연도별 수집, 원본 JSON 보관, 점검 결과 CSV 출력 | 1, 2, 4 |
| `02_geocode_ri.py` | 주소 목록 지오코딩, UTM-K → 경위도 변환, 범위 밖 좌표 출력 | 6 |
| `03_fetch_boundary.py` | 행정동 경계 수집 후 경위도 GeoJSON 저장 | 6 |
| `04_link_sgg_codes.py` | 법정동 연계정보로 행정안전부 시군구 코드 → SGIS 시군구 코드 대응표 작성 | 5 |
| `sgis_common.py` | 인증키 읽기, 호출 재시도, 토큰 발급 | - |

## 사용 예

```
python 01_fetch_oa_timeseries.py 33540 --from 2015 --to 2024
python 02_geocode_ri.py 주소목록.csv --bbox 127.4 35.9 128.3 36.5
python 03_fetch_boundary.py 34011 34012 --year 2024
python 04_link_sgg_codes.py 국가데이터처_법정동연계정보.csv --year 2024
```

## 알아 둘 점

- SGIS 코드는 행정안전부 코드와 다릅니다(충북 영동군 SGIS 33540, 행정안전부 43740)
- 법정동 연계정보에는 2021년 코드 범위 변경 전후 코드가 함께 있어 후보가 2개인 시군구가 있습니다.
  `04`는 SGIS 응답에 실제로 있는 코드만 남깁니다. 2026-09-14 실행 결과 324개 중 확정 287,
  SGIS에 없음 36(시도·일반구가 있는 시 단위·폐지 군), 후보 복수 1(안양시 만안구)
- `01`의 상하위 합계 점검에서 차이가 0이 아닌 N/A 칸은 값이 가려진 칸입니다.
  차이가 0이면 N/A 칸의 실제값 합계가 0이라는 뜻입니다
- 사업체수는 2020년 조사기반에서 등록기반으로 바뀌어 2019→2020 증가분을 실제 변화로 읽지 않습니다

## 공식 안내 위치

- SGIS 자료제공 소개 FAQ: https://sgis.mods.go.kr/view/pss/dataProvdIntrcn
- SGIS 코드표 및 이용설명서(ref_code.zip): 통계자료 이용안내, 소지역 통계 이용매뉴얼, 행정구역 코드
- 전국사업체조사 2020년 등록기반 전환: https://kosis.kr/civilComplaint/qnaDetail.do?boardIdx=21510
- 법정동 연계정보: https://www.data.go.kr/data/15136368/fileData.do
- 집계구 시계열 자료제공: https://www.data.go.kr/data/15129688/fileData.do
