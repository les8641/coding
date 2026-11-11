import csv
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor


BASE_DIR = Path(r"C:\Python\week 11")
DATASET = BASE_DIR / "wind_dataset.csv"
OUTPUT = BASE_DIR / "predictions.csv"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
FEATURE_COLUMNS = (
    "wind_speed_ms",
    "wind_speed_ms_1h_before",
    "wind_speed_ms_2h_before",
    "temperature_C",
    "humidity_pct",
)


def load_rows():
    with DATASET.open("r", newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    rows.sort(key=lambda row: datetime.strptime(row["target_time"], TIME_FORMAT))
    return rows


def in_training_period(target_time):
    return datetime(2023, 1, 1) <= target_time <= datetime(2024, 11, 30, 23, 59, 59)


def in_evaluation_period(target_time):
    return datetime(2024, 12, 1) <= target_time <= datetime(2024, 12, 31, 23, 59, 59)


def numeric_features(row):
    return [float(row[column]) for column in FEATURE_COLUMNS]


def main():
    rows = load_rows()
    training_rows = [
        row
        for row in rows
        if in_training_period(datetime.strptime(row["target_time"], TIME_FORMAT))
    ]
    evaluation_rows = [
        row
        for row in rows
        if in_evaluation_period(datetime.strptime(row["target_time"], TIME_FORMAT))
    ]

    x_train = np.asarray([numeric_features(row) for row in training_rows], dtype=float)
    y_train = np.asarray(
        [float(row["target_wind_speed_ms"]) for row in training_rows], dtype=float
    )
    x_train_with_intercept = np.column_stack((np.ones(len(x_train)), x_train))
    coefficients, _, _, _ = np.linalg.lstsq(
        x_train_with_intercept, y_train, rcond=None
    )
    random_forest = RandomForestRegressor(
        n_estimators=100,
        max_depth=6,
        min_samples_leaf=5,
        random_state=42,
    )
    random_forest.fit(x_train, y_train)

    predictions = []
    actual_values = []
    persistence_values = []
    regression_values = []
    random_forest_values = []
    for row in evaluation_rows:
        actual = float(row["target_wind_speed_ms"])
        persistence = float(row["wind_speed_ms"])
        features = numeric_features(row)
        regression = max(
            0.0,
            float(np.dot(np.r_[1.0, features], coefficients)),
        )
        random_forest_prediction = max(
            0.0, float(random_forest.predict([features])[0])
        )
        predictions.append(
            {
                "prediction_time": row["prediction_time"],
                "target_time": row["target_time"],
                "actual_wind_speed_ms": row["target_wind_speed_ms"],
                "current_wind_speed_prediction": row["wind_speed_ms"],
                "linear_regression_prediction": f"{regression:.10g}",
                "random_forest_prediction": f"{random_forest_prediction:.10g}",
            }
        )
        actual_values.append(actual)
        persistence_values.append(persistence)
        regression_values.append(regression)
        random_forest_values.append(random_forest_prediction)

    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        fieldnames = list(predictions[0])
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(predictions)

    actual_array = np.asarray(actual_values)
    persistence_mae = float(np.mean(np.abs(actual_array - persistence_values)))
    regression_mae = float(np.mean(np.abs(actual_array - regression_values)))
    random_forest_mae = float(
        np.mean(np.abs(actual_array - random_forest_values))
    )
    print(f"TRAINING_ROWS={len(training_rows)}")
    print(f"EVALUATION_ROWS={len(evaluation_rows)}")
    print(f"PERSISTENCE_MAE={persistence_mae:.10f}")
    print(f"LINEAR_REGRESSION_MAE={regression_mae:.10f}")
    print(f"RANDOM_FOREST_MAE={random_forest_mae:.10f}")
    print(
        f"RANDOM_FOREST_VS_LINEAR_CHANGE={random_forest_mae - regression_mae:.10f}"
    )
    print(
        f"RANDOM_FOREST_VS_BASELINE_CHANGE={random_forest_mae - persistence_mae:.10f}"
    )
    print(f"OUTPUT={OUTPUT}")
    print("FIRST_EVALUATION_RESULT")
    print(",".join(fieldnames))
    print(",".join(str(predictions[0][field]) for field in fieldnames))


if __name__ == "__main__":
    main()
