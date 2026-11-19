import csv
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "wind_dataset.csv"
OUTPUT_PATH = BASE_DIR / "classified_wind.csv"
PREDICTIONS_OUTPUT_PATH = BASE_DIR / "classification_predictions.csv"
SCORES_OUTPUT_PATH = BASE_DIR / "classification_scores.csv"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
LABEL_COLUMN = "wind_next1h"
FEATURE_COLUMNS = (
    "wind_speed_ms",
    "temperature_C",
    "humidity_pct",
    "wind_speed_ms_1h_before",
    "wind_speed_ms_2h_before",
)

TRAIN_START = datetime(2023, 1, 1)
TRAIN_END = datetime(2024, 11, 30, 23, 59, 59)
EVALUATION_START = datetime(2024, 12, 1)
EVALUATION_END = datetime(2024, 12, 31, 23, 59, 59)


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, TIME_FORMAT)


def load_and_classify() -> tuple[list[dict[str, str]], list[str]]:
    with INPUT_PATH.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"CSV header is missing: {INPUT_PATH}")
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    required_columns = {"prediction_time", "target_time", "target_wind_speed_ms"}
    missing_columns = required_columns - set(fieldnames)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Required column(s) missing: {missing}")

    previous_prediction_time = None
    for row_number, row in enumerate(rows, start=2):
        prediction_time = parse_time(row["prediction_time"])
        target_time = parse_time(row["target_time"])

        if target_time - prediction_time != timedelta(hours=1):
            raise ValueError(
                f"Rows {row_number}: prediction_time and target_time "
                "must be exactly one hour apart"
            )
        if (
            previous_prediction_time is not None
            and prediction_time < previous_prediction_time
        ):
            raise ValueError(
                f"Rows are not in chronological order at CSV row {row_number}"
            )

        target_wind_speed = float(row["target_wind_speed_ms"])
        row[LABEL_COLUMN] = "1" if target_wind_speed >= 4.0 else "0"
        previous_prediction_time = prediction_time

    if LABEL_COLUMN not in fieldnames:
        fieldnames.append(LABEL_COLUMN)
    return rows, fieldnames


def in_period(
    row: dict[str, str], start: datetime, end: datetime
) -> bool:
    target_time = parse_time(row["target_time"])
    return start <= target_time <= end


def print_period_summary(
    name: str,
    rows: list[dict[str, str]],
    start: datetime,
    end: datetime,
) -> None:
    period_rows = [row for row in rows if in_period(row, start, end)]
    label_counts = {
        "0": sum(row[LABEL_COLUMN] == "0" for row in period_rows),
        "1": sum(row[LABEL_COLUMN] == "1" for row in period_rows),
    }
    print(f"{name}_ROWS={len(period_rows)}")
    print(f"{name}_LABEL_0={label_counts['0']}")
    print(f"{name}_LABEL_1={label_counts['1']}")
    if name == "EVALUATION":
        if not period_rows:
            raise ValueError("Evaluation period has no rows")
        print("FIRST_EVALUATION_ROW=" + repr(period_rows[0]))


def numeric_features(row: dict[str, str]) -> list[float]:
    return [float(row[column]) for column in FEATURE_COLUMNS]


def create_classification_predictions(
    training_rows: list[dict[str, str]],
    evaluation_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    x_train = np.asarray(
        [numeric_features(row) for row in training_rows], dtype=float
    )
    y_train = np.asarray(
        [int(row[LABEL_COLUMN]) for row in training_rows], dtype=int
    )
    x_evaluation = np.asarray(
        [numeric_features(row) for row in evaluation_rows], dtype=float
    )

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_evaluation_scaled = scaler.transform(x_evaluation)
    model = LogisticRegression(max_iter=1000)
    model.fit(x_train_scaled, y_train)
    strong_wind_probabilities = model.predict_proba(x_evaluation_scaled)[:, 1]

    predictions = []
    for row, probability in zip(
        evaluation_rows, strong_wind_probabilities, strict=True
    ):
        predictions.append(
            {
                "prediction_time": row["prediction_time"],
                "target_time": row["target_time"],
                "actual_wind_speed_ms": row["target_wind_speed_ms"],
                "actual_label": row[LABEL_COLUMN],
                "current_wind_speed_ms": row["wind_speed_ms"],
                "always_0_prediction": "0",
                "current_wind_ge_4_prediction": (
                    "1" if float(row["wind_speed_ms"]) >= 4.0 else "0"
                ),
                "strong_wind_probability": f"{probability:.10f}",
                "logistic_regression_prediction": (
                    "1" if probability >= 0.50 else "0"
                ),
                "logistic_regression_0.50_prediction": (
                    "1" if probability >= 0.50 else "0"
                ),
                "logistic_regression_0.20_prediction": (
                    "1" if probability >= 0.20 else "0"
                ),
            }
        )
    return predictions


def calculate_scores(
    evaluation_rows: list[dict[str, str]],
    prediction_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    evaluation_keys = [
        (row["prediction_time"], row["target_time"])
        for row in evaluation_rows
    ]
    prediction_keys = [
        (row["prediction_time"], row["target_time"])
        for row in prediction_rows
    ]
    if evaluation_keys != prediction_keys:
        raise ValueError("Prediction rows do not match the evaluation rows")

    methods = {
        "always_0": "always_0_prediction",
        "current_wind_ge_4": "current_wind_ge_4_prediction",
        "logistic_regression_0.50": "logistic_regression_0.50_prediction",
        "logistic_regression_0.20": "logistic_regression_0.20_prediction",
    }
    scores = []
    for method, prediction_column in methods.items():
        actual = [int(row["actual_label"]) for row in prediction_rows]
        predicted = [int(row[prediction_column]) for row in prediction_rows]
        hit = sum(a == 1 and p == 1 for a, p in zip(actual, predicted))
        miss = sum(a == 1 and p == 0 for a, p in zip(actual, predicted))
        false_alarm = sum(
            a == 0 and p == 1 for a, p in zip(actual, predicted)
        )
        correct_negative = sum(
            a == 0 and p == 0 for a, p in zip(actual, predicted)
        )
        predicted_positive = hit + false_alarm
        scores.append(
            {
                "method": method,
                "evaluation_rows": str(len(prediction_rows)),
                "hit_true_positive": str(hit),
                "miss_false_negative": str(miss),
                "false_alarm_false_positive": str(false_alarm),
                "correct_negative": str(correct_negative),
                "accuracy": f"{(hit + correct_negative) / len(actual):.10f}",
                "precision": (
                    f"{hit / predicted_positive:.10f}"
                    if predicted_positive
                    else "N/A"
                ),
                "recall": (
                    f"{hit / (hit + miss):.10f}"
                    if hit + miss
                    else "해당없음"
                ),
            }
        )
    return scores


def print_scores(scores: list[dict[str, str]]) -> None:
    headers = [
        "method",
        "hit",
        "miss",
        "false_alarm",
        "correct_negative",
        "accuracy",
        "precision",
        "recall",
    ]
    print("\nCLASSIFICATION_SCORES")
    print("\t".join(headers))
    for score in scores:
        print(
            "\t".join(
                [
                    score["method"],
                    score["hit_true_positive"],
                    score["miss_false_negative"],
                    score["false_alarm_false_positive"],
                    score["correct_negative"],
                    score["accuracy"],
                    score["precision"],
                    score["recall"],
                ]
            )
        )

    score_by_method = {score["method"]: score for score in scores}
    threshold_headers = [
        "metric",
        "threshold_0.50",
        "threshold_0.20",
    ]
    print("\nLOGISTIC_REGRESSION_THRESHOLD_COMPARISON")
    print("\t".join(threshold_headers))
    for metric, score_key in [
        ("hit", "hit_true_positive"),
        ("miss", "miss_false_negative"),
        ("false_alarm", "false_alarm_false_positive"),
        ("precision", "precision"),
        ("recall", "recall"),
    ]:
        threshold_050 = score_by_method["logistic_regression_0.50"][score_key]
        threshold_020 = score_by_method["logistic_regression_0.20"][score_key]
        print("\t".join([metric, threshold_050, threshold_020]))


def main() -> None:
    rows, fieldnames = load_and_classify()
    training_rows = [
        row for row in rows
        if in_period(row, TRAIN_START, TRAIN_END)
    ]
    evaluation_rows = [
        row for row in rows
        if in_period(row, EVALUATION_START, EVALUATION_END)
    ]
    if not training_rows:
        raise ValueError("Training period has no rows")
    if not evaluation_rows:
        raise ValueError("Evaluation period has no rows")

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    classification_predictions = create_classification_predictions(
        training_rows, evaluation_rows
    )
    prediction_fieldnames = list(classification_predictions[0])
    with PREDICTIONS_OUTPUT_PATH.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=prediction_fieldnames)
        writer.writeheader()
        writer.writerows(classification_predictions)

    actual_strong_wind_count = sum(
        row["actual_label"] == "1" for row in classification_predictions
    )
    scores = calculate_scores(evaluation_rows, classification_predictions)
    with SCORES_OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        score_fieldnames = list(scores[0])
        writer = csv.DictWriter(file, fieldnames=score_fieldnames)
        writer.writeheader()
        writer.writerows(scores)

    print(f"INPUT_ROWS={len(rows)}")
    print("TIME_ORDER=verified")
    print("ONE_HOUR_INTERVAL=verified")
    print_period_summary("TRAIN", rows, TRAIN_START, TRAIN_END)
    print_period_summary(
        "EVALUATION", rows, EVALUATION_START, EVALUATION_END
    )
    print(f"OUTPUT={OUTPUT_PATH}")
    print(f"PREDICTIONS_OUTPUT={PREDICTIONS_OUTPUT_PATH}")
    print("PREDICTION_ROWS=" + str(len(classification_predictions)))
    print("SAME_EVALUATION_ROWS=verified")
    print(f"ACTUAL_STRONG_WIND_ROWS={actual_strong_wind_count}")
    print(f"SCORES_OUTPUT={SCORES_OUTPUT_PATH}")
    print_scores(scores)


if __name__ == "__main__":
    main()
