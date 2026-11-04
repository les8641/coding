# 기상청 시간자료 수집 및 기온 그래프

## 작업 내용

기상청 API허브의 종관기상관측 시간자료 기간 조회 API를 사용해 서울 관측소의
시간별 기상자료를 수집하고, 기온을 CSV와 PNG 그래프로 저장했다.

- 관측소: `108` (서울)
- 조회 기간: `2026-01-01 09:00` ~ `2026-01-07 18:00` (KST)
- API 출처:
  [기상청 API허브 종관기상관측 시간자료 기간 조회](https://apihub.kma.go.kr/api/typ01/url/kma_sfctm3.php)
- 요청 항목: `TM(1)`, `WS(4)`, `TA(12)`, `HM(14)`
- CSV 열: `datetime`, `temperature_C`, `humidity_pct`, `wind_speed_ms`

## 파일

- [collect_weather.py](./collect_weather.py): API 호출, 응답 보관, 자료행 변환 및 CSV 저장
- [plot_weather.py](./plot_weather.py): CSV를 읽어 시간별 기온 그래프 생성
- [weather_202601010900_202601071800.csv](./weather_202601010900_202601071800.csv): 변환한 자료
- [weather_raw_202601010900_202601071800.txt](./weather_raw_202601010900_202601071800.txt): 원본 응답
- [temperature_202601010900_202601071800.png](./temperature_202601010900_202601071800.png): 기온 그래프

## 실행 방법

PowerShell에서 작업 폴더로 이동한다.

```powershell
cd C:\Python\weather_API
```

먼저 수집 코드를 실행하고, 프롬프트에 기상청에서 발급받은 인증키를 입력한다.
인증키는 `getpass.getpass()`로 입력되며 화면에 표시되지 않는다.

```powershell
python .\collect_weather.py
```

수집이 완료되면 API를 다시 호출하지 않고 그래프 코드를 실행한다.

```powershell
python .\plot_weather.py
```

그래프는 `temperature_202601010900_202601071800.png`로 저장되며 실행 중 화면에도
표시된다.

## 누락·결측 확인 결과

- 자료 행수: `154`
- 예상 1시간 간격 행수: `154`
- 누락 시각: `0`건
- `temperature_C` 결측: `0`건
- `humidity_pct` 결측: `0`건
- `wind_speed_ms` 결측: `0`건
- 첫 시각: `2026-01-01 09:00:00`
- 마지막 시각: `2026-01-07 18:00:00`
- 중복 시각: `0`건

## 그래프 해석

그래프에서 기온은 1월 2일 08시 `-11.2°C`까지 하락한 뒤 상승해 1월 4일 14시 `4.4°C`로 가장 높았다.
전체적으로 겨울철의 낮은 기온이 나타나며, 조회 시작 시각의 `-10.0°C`에서 종료 시각의 `-0.5°C`로 완만하게 높아졌다.

## 인증키 보안 확인

인증키는 코드·CSV·원본 응답 파일·README·그래프 파일에 기록하지 않는다.
코드에서는 실행 중 `getpass.getpass()`로만 입력받고, 요청 URL이나 오류에 인증키가
출력되지 않도록 처리했다.
