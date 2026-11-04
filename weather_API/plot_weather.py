"""새 기간 CSV의 시간별 기온을 그래프로 저장하고 표시한다."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


START_TIME = "202601010900"
END_TIME = "202601071800"
DATA_PATH = Path(__file__).with_name(f"weather_{START_TIME}_{END_TIME}.csv")
PLOT_PATH = Path(__file__).with_name(
    f"temperature_{START_TIME}_{END_TIME}.png"
)


def load_hourly_weather(path: Path) -> tuple[pd.Series, list[pd.Timestamp]]:
    """CSV의 datetime을 시간 인덱스로 변환하고 누락 시각을 NaN으로 채운다."""
    data = pd.read_csv(path, encoding="utf-8-sig")
    data["datetime"] = pd.to_datetime(data["datetime"], errors="raise")
    data = data.sort_values("datetime").set_index("datetime")

    if data.index.has_duplicates:
        duplicates = data.index[data.index.duplicated()].unique().tolist()
        raise ValueError(f"중복 시각이 있습니다: {duplicates}")

    hourly_index = pd.date_range(data.index.min(), data.index.max(), freq="h")
    missing_times = hourly_index.difference(data.index)
    temperature = data["temperature_C"].reindex(hourly_index)
    temperature = pd.to_numeric(temperature, errors="coerce")
    return temperature, missing_times.tolist()


def plot_temperature(temperature: pd.Series, output_path: Path) -> None:
    """시간별 기온을 그려 결측 구간은 선이 끊긴 상태로 PNG에 저장하고 표시한다."""
    figure, axis = plt.subplots(figsize=(12, 5))
    axis.plot(temperature.index, temperature, label="Temperature")
    axis.set_title("Temperature over time")
    axis.set_xlabel("Time (KST)")
    axis.set_ylabel("Temperature (°C)")
    axis.grid(True, alpha=0.3)
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    print(f"그래프 저장 위치: {output_path}")
    plt.show()
    plt.close(figure)


def main() -> int:
    """CSV를 읽고 누락 시각을 확인한 뒤 기온 그래프를 생성한다."""
    temperature, missing_times = load_hourly_weather(DATA_PATH)
    print(f"누락 시각 수: {len(missing_times)}")
    if missing_times:
        print("누락 시각:")
        for timestamp in missing_times:
            print(timestamp.strftime("%Y-%m-%d %H:%M:%S"))
    plot_temperature(temperature, PLOT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
