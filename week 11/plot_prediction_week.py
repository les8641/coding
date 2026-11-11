import csv
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(r"C:\Python\week 11")
INPUT = BASE_DIR / "predictions.csv"
OUTPUT = BASE_DIR / "prediction_week.png"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def main():
    with INPUT.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    parsed = [
        (
            datetime.strptime(row["target_time"], TIME_FORMAT),
            float(row["actual_wind_speed_ms"]),
            float(row["current_wind_speed_prediction"]),
            float(row["linear_regression_prediction"]),
        )
        for row in rows
    ]
    december = [item for item in parsed if item[0].month == 12]
    week = [
        item
        for item in december
        if datetime(2024, 12, 1) <= item[0] <= datetime(2024, 12, 7, 23)
    ]

    times = [item[0] for item in week]
    actual = [item[1] for item in week]
    baseline = [item[2] for item in week]
    regression = [item[3] for item in week]

    plt.figure(figsize=(14, 6))
    plt.plot(times, actual, color="black", label="Actual")
    plt.plot(
        times,
        baseline,
        color="gray",
        linestyle=":",
        label="Baseline (current wind)",
    )
    plt.plot(times, regression, color="blue", label="Linear regression")
    plt.xlabel("Target time (KST)")
    plt.ylabel("Wind speed (m/s)")
    plt.title("Wind-speed predictions: 2024-12-01 00:00 - 2024-12-07 23:00 KST")
    plt.legend()
    plt.grid(True, alpha=0.25)
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.savefig(OUTPUT, dpi=150)
    plt.close()

    actual_december = np.asarray([item[1] for item in december])
    baseline_december = np.asarray([item[2] for item in december])
    regression_december = np.asarray([item[3] for item in december])
    baseline_mae = np.mean(np.abs(actual_december - baseline_december))
    regression_mae = np.mean(np.abs(actual_december - regression_december))
    print(f"WEEK_ROWS={len(week)}")
    print(f"DECEMBER_ROWS={len(december)}")
    print(f"BASELINE_DECEMBER_MAE={baseline_mae:.10f}")
    print(f"LINEAR_REGRESSION_DECEMBER_MAE={regression_mae:.10f}")
    print(f"OUTPUT={OUTPUT}")


if __name__ == "__main__":
    main()
