import csv
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False

BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "classification_predictions.csv"
OUTPUT_PATH = BASE_DIR / "strong_wind_december.png"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def load_rows() -> list[dict[str, str]]:
    with INPUT_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def main() -> None:
    start = datetime(2024, 12, 1)
    end = datetime(2024, 12, 7, 23, 59, 59)
    rows = [
        row
        for row in load_rows()
        if start <= parse_time(row["target_time"]) <= end
    ]
    if not rows:
        raise ValueError("12월 1~7일 예측 행이 없습니다.")

    times = [parse_time(row["target_time"]) for row in rows]
    actual_wind = [float(row["actual_wind_speed_ms"]) for row in rows]
    actual_strong = [int(row["actual_label"]) for row in rows]
    threshold_050 = [
        int(row["logistic_regression_0.50_prediction"]) for row in rows
    ]
    threshold_020 = [
        int(row["logistic_regression_0.20_prediction"]) for row in rows
    ]

    fig, (upper, lower) = plt.subplots(
        2,
        1,
        figsize=(14, 8),
        sharex=True,
        constrained_layout=True,
    )

    upper.plot(times, actual_wind, color="#1f77b4", linewidth=1.5,
               label="실제 풍속")
    upper.axhline(
        4.0,
        color="#d62728",
        linestyle="--",
        linewidth=1.5,
        label="강풍 기준선 4.0 m/s",
    )
    upper.set_ylabel("풍속 (m/s)")
    upper.set_title("2024년 12월 1~7일 실제 풍속과 강풍 기준")
    upper.grid(alpha=0.25)
    upper.legend(loc="upper right")

    lower.scatter(
        [time for time, value in zip(times, actual_strong) if value == 1],
        [2.0] * sum(actual_strong),
        color="#d62728",
        marker="o",
        s=28,
        label="실제 강풍",
    )
    lower.scatter(
        [time for time, value in zip(times, threshold_050) if value == 1],
        [1.0] * sum(threshold_050),
        color="#ff7f0e",
        marker="^",
        s=36,
        label="로지스틱 0.50",
    )
    lower.scatter(
        [time for time, value in zip(times, threshold_020) if value == 1],
        [0.0] * sum(threshold_020),
        color="#9467bd",
        marker="s",
        s=36,
        label="로지스틱 0.20",
    )
    lower.set_yticks([0.0, 1.0, 2.0])
    lower.set_yticklabels(
        ["0.20 예측 강풍", "0.50 예측 강풍", "실제 강풍"]
    )
    lower.set_ylim(-0.5, 2.5)
    lower.set_ylabel("강풍 판정")
    lower.set_xlabel("정답 시각 (KST)")
    lower.grid(alpha=0.25)
    lower.legend(loc="upper right")

    lower.xaxis.set_major_locator(mdates.DayLocator())
    lower.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    lower.set_xlim(times[0], times[-1])

    fig.savefig(OUTPUT_PATH, dpi=160)
    print(f"PLOT_ROWS={len(rows)}")
    print(f"PLOT_OUTPUT={OUTPUT_PATH}")

    wrong_cases = []
    december_2_start = datetime(2024, 12, 2)
    december_2_end = datetime(2024, 12, 2, 23, 59, 59)
    for row in rows:
        target_time = parse_time(row["target_time"])
        if december_2_start <= target_time <= december_2_end:
            actual = int(row["actual_label"])
            prediction_050 = int(
                row["logistic_regression_0.50_prediction"]
            )
            prediction_020 = int(
                row["logistic_regression_0.20_prediction"]
            )
            if actual != prediction_050 or actual != prediction_020:
                wrong_cases.append(row)

    if not wrong_cases:
        raise ValueError("12월 2일 틀린 사례가 없습니다.")
    wrong = wrong_cases[0]
    print("DECEMBER_2_WRONG_CASE")
    print(
        "target_time={target_time}, actual_wind_speed_ms={actual_wind_speed_ms}, "
        "actual_label={actual_label}, "
        "0.50_prediction={prediction_050}, "
        "0.20_prediction={prediction_020}, "
        "strong_wind_probability={probability}".format(
            target_time=wrong["target_time"],
            actual_wind_speed_ms=wrong["actual_wind_speed_ms"],
            actual_label=wrong["actual_label"],
            prediction_050=wrong[
                "logistic_regression_0.50_prediction"
            ],
            prediction_020=wrong[
                "logistic_regression_0.20_prediction"
            ],
            probability=wrong["strong_wind_probability"],
        )
    )


if __name__ == "__main__":
    main()
