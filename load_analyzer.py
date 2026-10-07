import argparse
import csv
import math
from pathlib import Path
from typing import TypedDict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


DATA_FILE = Path(__file__).with_name("load_data.csv")
RESULT_FILE = Path(__file__).with_name("load_result.csv")
PLOT_FILE = Path(__file__).with_name("stress_plot.png")
AREA_MM2 = 100.0
REFERENCE_STRESS_MPA = 6.0


class LoadRow(TypedDict):
    time_s: float
    force_N: float


class ResultRow(LoadRow):
    stress_MPa: float


def read_load_data(file_path: Path) -> tuple[list[LoadRow], int]:
    """Read time and force values from a CSV file."""
    with file_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)

        expected_columns = {"time_s", "force_N"}
        if reader.fieldnames is None or set(reader.fieldnames) != expected_columns:
            raise ValueError("CSV 열 이름은 time_s와 force_N이어야 합니다.")

        rows: list[LoadRow] = []
        excluded_count = 0
        for row_number, row in enumerate(reader, start=2):
            invalid_values: list[tuple[str, str]] = []
            time_value = row["time_s"]
            force_value = row["force_N"]

            try:
                time_s = float(time_value)
                if not math.isfinite(time_s):
                    raise ValueError
            except (TypeError, ValueError):
                invalid_values.append(("time_s", repr(time_value)))
                time_s = 0.0

            try:
                force_N = float(force_value)
                if not math.isfinite(force_N):
                    raise ValueError
            except (TypeError, ValueError):
                invalid_values.append(("force_N", repr(force_value)))
                force_N = 0.0

            if invalid_values:
                excluded_count += 1
                for column_name, invalid_value in invalid_values:
                    print(
                        f"CSV {row_number}행: {column_name} 문제 값 "
                        f"{invalid_value}"
                    )
                continue

            rows.append({"time_s": time_s, "force_N": force_N})

    return rows, excluded_count


def format_number(value: float) -> str:
    """Format a numeric result without unnecessary trailing zeroes."""
    return f"{value:g}"


def calculate_stress(rows: list[LoadRow], area_mm2: float) -> list[ResultRow]:
    """Add stress values in MPa to the load data."""
    if area_mm2 <= 0:
        raise ValueError("단면적은 0보다 커야 합니다.")

    return [
        {
            "time_s": row["time_s"],
            "force_N": row["force_N"],
            "stress_MPa": row["force_N"] / area_mm2,
        }
        for row in rows
    ]


def write_result_data(file_path: Path, rows: list[ResultRow]) -> None:
    """Write load and stress data to a separate CSV file."""
    with file_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["time_s", "force_N", "stress_MPa"],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_stress_plot(file_path: Path, rows: list[ResultRow]) -> None:
    """Save a time-stress plot with markers connected by a line."""
    times = [row["time_s"] for row in rows]
    stresses = [row["stress_MPa"] for row in rows]
    maximum_row = max(rows, key=lambda row: row["stress_MPa"])

    figure, axes = plt.subplots()
    axes.plot(times, stresses, marker="o")
    axes.scatter(
        maximum_row["time_s"],
        maximum_row["stress_MPa"],
        color="red",
        zorder=3,
    )
    axes.annotate(
        f"{format_number(maximum_row['stress_MPa'])} MPa",
        (maximum_row["time_s"], maximum_row["stress_MPa"]),
        xytext=(8, 8),
        textcoords="offset points",
    )
    axes.set_xlabel("Time (s)")
    axes.set_ylabel("Stress (MPa)")
    axes.grid(True)
    figure.tight_layout()
    figure.savefig(file_path)
    plt.close(figure)


def main() -> None:
    parser = argparse.ArgumentParser(description="하중 CSV를 분석합니다.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=DATA_FILE,
        help="분석할 CSV 파일 경로 (기본값: load_bad.csv)",
    )
    args = parser.parse_args()

    rows, excluded_count = read_load_data(args.csv_path)
    print(f"제외한 행 수: {excluded_count}개")
    print(f"유효한 데이터 수: {len(rows)}개")
    if not rows:
        print("유효한 데이터가 없어 계산과 그래프 생성을 중단합니다.")
        return

    result_rows = calculate_stress(rows, AREA_MM2)
    maximum_row = max(rows, key=lambda row: row["force_N"])
    maximum_stress_row = max(result_rows, key=lambda row: row["stress_MPa"])
    exceeded_count = sum(
        row["stress_MPa"] > REFERENCE_STRESS_MPA for row in result_rows
    )
    write_result_data(RESULT_FILE, result_rows)
    write_stress_plot(PLOT_FILE, result_rows)

    print(f"데이터 개수: {len(rows)}개")
    print(f"최대 하중: {format_number(maximum_row['force_N'])} N")
    print(f"최대 하중 시간: {format_number(maximum_row['time_s'])} s")
    print(
        f"최대 응력: {format_number(maximum_stress_row['stress_MPa'])} MPa"
    )
    print(
        f"최대 응력 시간: {format_number(maximum_stress_row['time_s'])} s"
    )
    print(f"기준 응력(6MPa) 초과 데이터 개수: {exceeded_count}개")


if __name__ == "__main__":
    main()
