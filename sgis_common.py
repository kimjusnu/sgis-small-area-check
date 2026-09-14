"""SGIS OpenAPI3 공통 함수: 인증키 읽기, 호출, 토큰 발급.

인증키는 코드에 적지 않는다. 아래 두 곳 중 먼저 찾은 값을 쓴다.
  1) 환경변수 SGIS_SERVICE_ID, SGIS_SECURITY_KEY
  2) 실행 위치의 .env 파일 (같은 이름의 키)
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://sgisapi.kostat.go.kr/OpenAPI3"
KEY_NAMES = ("SGIS_SERVICE_ID", "SGIS_SECURITY_KEY")


def load_credentials(env_path=".env"):
    creds = {k: os.environ.get(k, "") for k in KEY_NAMES}
    path = Path(env_path)
    if not all(creds.values()) and path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() in KEY_NAMES and not creds[k.strip()]:
                    creds[k.strip()] = v.strip()
    missing = [k for k, v in creds.items() if not v]
    if missing:
        raise RuntimeError(f"SGIS 인증키가 없습니다: {', '.join(missing)} (환경변수 또는 .env)")
    return creds


def api(path, retries=3, timeout=60, **params):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries - 1:
                raise RuntimeError(f"SGIS 호출 실패: {path} — {e}") from e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def access_token(creds=None):
    creds = creds or load_credentials()
    r = api("/auth/authentication.json",
            consumer_key=creds["SGIS_SERVICE_ID"],
            consumer_secret=creds["SGIS_SECURITY_KEY"])
    if str(r.get("errCd")) != "0":
        raise RuntimeError(f"SGIS 인증 실패: {r.get('errMsg')}")
    return r["result"]["accessToken"]
