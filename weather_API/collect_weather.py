"""기상청 종관기상관측 시간자료를 조회해 CSV로 저장한다."""

import csv
import getpass
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


API_URL = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php"
TIMEOUT_SECONDS = 10
OUTPUT_DIR = Path(__file__).parent
START_TIME = "202601010900"
END_TIME = "202601071800"
RAW_RESPONSE_PATH = OUTPUT_DIR / f"weather_raw_{START_TIME}_{END_TIME}.txt"
CSV_PATH = OUTPUT_DIR / f"weather_{START_TIME}_{END_TIME}.csv"


def _find_message(value: Any) -> str | None:
    """JSON 값에서 message 필드를 찾아 반환한다."""
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() == "message" and item is not None:
                return str(item)
        for item in value.values():
            message = _find_message(item)
            if message:
                return message
    elif isinstance(value, list):
        for item in value:
            message = _find_message(item)
            if message:
                return message
    return None


def _body_message(body: str) -> str:
    """오류 본문에서 message를 추출한다."""
    try:
        message = _find_message(json.loads(body))
    except json.JSONDecodeError:
        message = None
    if message:
        return message

    match = re.search(
        r"""["'<]?\s*message\s*["'>]?\s*[:=]\s*["']?([^"'\r\n<}]+)""",
        body,
        flags=re.IGNORECASE,
    )
    return match.group(1).strip() if match else "응답 본문에서 message를 찾을 수 없습니다."


def _decode_response(response: requests.Response) -> tuple[str, str]:
    """응답의 charset을 우선 사용해 본문을 디코딩한다."""
    charset = response.encoding or response.apparent_encoding or "utf-8"
    return response.content.decode(charset, errors="replace"), charset


def _find_header_numbers(lines: list[str]) -> dict[str, int]:
    """# 헤더에서 공식 번호-변수 표기를 찾아 변수별 0 기반 위치를 반환한다."""
    header_numbers: dict[str, int] = {}
    for line in lines:
        if not line.lstrip().startswith("#"):
            continue
        for number, name in re.findall(r"\b(\d+)\s*[.:]\s*([A-Za-z][A-Za-z0-9_]*)", line):
            header_numbers[name.upper()] = int(number) - 1

    required = {"TM": 1, "WS": 4, "TA": 12, "HM": 14}
    missing = [name for name in required if name not in header_numbers]
    if missing:
        raise ValueError(f"필수 헤더 번호를 찾지 못했습니다: {', '.join(missing)}")
    return {name: header_numbers[name] for name in required}


def _is_missing(value: str, field: str) -> bool:
    """공식 자료의 결측 표기와 빈 토큰을 빈값으로 변환할지 판단한다."""
    if not value or value.upper() in {"MM", "NA", "N/A", "-"}:
        return True
    try:
        numeric = float(value)
    except ValueError:
        return False

    # -99 계열은 결측 sentinel이며, 일반적인 음수 기온(-9 등)은 보존한다.
    if field == "temperature_C":
        return numeric <= -99
    return numeric <= -99


def _parse_rows(lines: list[str], positions: dict[str, int]) -> list[dict[str, str]]:
    """설명줄을 제외한 공백 구분 자료행을 표의 열 이름으로 변환한다."""
    records: list[dict[str, str]] = []
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) <= max(positions.values()):
            raise ValueError(f"{line_number}행의 필드 수가 부족합니다.")

        raw_datetime = fields[positions["TM"]]
        try:
            parsed_datetime = datetime.strptime(raw_datetime, "%Y%m%d%H%M")
        except ValueError as error:
            raise ValueError(f"{line_number}행의 TM 값이 올바르지 않습니다: {raw_datetime}") from error

        record = {"datetime": parsed_datetime.strftime("%Y-%m-%d %H:%M:%S")}
        for source, target in (
            ("WS", "wind_speed_ms"),
            ("TA", "temperature_C"),
            ("HM", "humidity_pct"),
        ):
            value = fields[positions[source]]
            record[target] = "" if _is_missing(value, target) else value
        records.append(record)
    return records


def _save_csv(records: list[dict[str, str]]) -> None:
    """정렬된 표를 인덱스 없이 UTF-8 BOM CSV로 저장한다."""
    records.sort(key=lambda record: record["datetime"])
    datetimes = [record["datetime"] for record in records]
    duplicates = sorted(value for value, count in Counter(datetimes).items() if count > 1)
    if duplicates:
        raise ValueError(f"중복 시각이 있습니다: {', '.join(duplicates)}")

    columns = ["datetime", "temperature_C", "humidity_pct", "wind_speed_ms"]
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    """인증키 입력부터 조회, 원본 보관, 변환, 검증, 저장, 통계 출력까지 수행한다."""
    auth_key = getpass.getpass("기상청 API 인증키: ")
    params = {
        "tm1": START_TIME,
        "tm2": END_TIME,
        "stn": "108",
        "help": "1",
        "authKey": auth_key,
    }

    try:
        response = requests.get(API_URL, params=params, timeout=TIMEOUT_SECONDS)
        body, charset = _decode_response(response)
    except requests.RequestException:
        print("요청 실패: 네트워크 요청 오류", file=sys.stderr)
        return 1
    except (LookupError, UnicodeError) as error:
        print(f"응답 디코딩 실패: {error}", file=sys.stderr)
        return 1

    print(f"HTTP 상태: {response.status_code} {response.reason}")
    print(f"응답 charset: {charset}")
    try:
        RAW_RESPONSE_PATH.write_bytes(response.content)
    except OSError as error:
        print(f"원본 응답 저장 실패: {error}", file=sys.stderr)
        return 1
    print(f"원본 응답 저장 위치: {RAW_RESPONSE_PATH}")

    if not response.ok:
        print(f"실패 message: {_body_message(body)}", file=sys.stderr)
        return 1

    try:
        lines = body.splitlines()
        positions = _find_header_numbers(lines)
        records = _parse_rows(lines, positions)
        if not records:
            raise ValueError("자료행이 없습니다.")
        _save_csv(records)
    except (OSError, ValueError) as error:
        print(f"자료 처리 실패: {error}", file=sys.stderr)
        return 1

    missing_counts = {
        column: sum(record[column] == "" for record in records)
        for column in ("temperature_C", "humidity_pct", "wind_speed_ms")
    }
    print(f"행수: {len(records)}")
    print(f"열별 결측수: {missing_counts}")
    print(f"첫 시각: {records[0]['datetime']}")
    print(f"마지막 시각: {records[-1]['datetime']}")
    print(f"저장 위치: {CSV_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
