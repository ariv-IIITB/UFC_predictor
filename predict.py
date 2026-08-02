import argparse
import csv
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import xgboost as xgb


BASE_DIR = Path(__file__).resolve().parent
TRAIN_CSV = BASE_DIR / "default_train.csv"
LABEL_SOURCE_CSV = BASE_DIR / "final_data.csv"
FIGHTERS_CSV = BASE_DIR / "fighter_state.csv"
CATEGORY_MAPS_JSON = BASE_DIR / "ufc_prefight_post2001_binary_mirrored_xgboost_category_maps.json"
OUTPUT_DIR = BASE_DIR
MODEL_OUT = BASE_DIR / "ufc_predict_manual_card_xgboost_model_reduced.json"

NUM_BOOST_ROUND = 600
ETA = 0.04
MAX_DEPTH = 4
MIN_CHILD_WEIGHT = 3.0
SUBSAMPLE = 0.90
COLSAMPLE_BYTREE = 0.80
REG_LAMBDA = 1.0
EVAL_METRIC = ["logloss", "auc"]
N_JOBS = -1
EARLY_STOPPING_ROUNDS = 100

TRAIN_COLUMNS_TO_SKIP = {"fight_id", "fight_date", "split", "label_a_win"}
REQUIRED_MATCHUP_COLUMNS = [
    "fight_id_manual",
    "event_name",
    "fight_date",
    "fighter_a",
    "fighter_b",
    "division_norm",
    "scheduled_rounds",
    "title_fight",
]


def parse_float(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text == "":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_date(text):
    return datetime.strptime((text or "").strip(), "%Y-%m-%d")


def slugify(text):
    cleaned = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower())
    return cleaned.strip("_") or "card"


def confidence_tier(probability):
    edge = abs(probability - 0.5)
    if edge >= 0.20:
        return "very_strong"
    if edge >= 0.12:
        return "strong"
    if edge >= 0.07:
        return "medium"
    return "lean"


def division_group(division_name):
    division_name = (division_name or "").strip().lower()
    if division_name.startswith("women's "):
        return "women"
    if division_name in {"open weight", "catch weight", "super heavyweight", "superfight championship", "other"}:
        return "special"
    return "men"


def safe_divide(numerator, denominator):
    denominator = parse_float(denominator)
    if denominator == 0.0:
        return 0.0
    return parse_float(numerator) / denominator


def safe_rate(multiplier, numerator, denominator):
    denominator = parse_float(denominator)
    if denominator == 0.0:
        return 0.0
    return multiplier * parse_float(numerator) / denominator


def read_headers(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or []


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_template(path):
    row = {
        "fight_id_manual": "ufc330_001",
        "event_name": "UFC 330",
        "fight_date": "2026-08-15",
        "fighter_a": "Islam Makhachev",
        "fighter_b": "Ian Machado Garry",
        "division_norm": "welterweight",
        "scheduled_rounds": "5",
        "title_fight": "1",
    }
    write_csv(path, [row], REQUIRED_MATCHUP_COLUMNS)


def load_category_maps():
    if not CATEGORY_MAPS_JSON.exists():
        return {}
    return json.loads(CATEGORY_MAPS_JSON.read_text(encoding="utf-8"))


def load_feature_columns():
    headers = read_headers(TRAIN_CSV)
    feature_columns = [column for column in headers if column not in TRAIN_COLUMNS_TO_SKIP]
    if not feature_columns:
        raise ValueError("No usable model features were found in the training CSV.")
    return feature_columns


def get_training_rows_file(feature_columns):
    train_headers = set(read_headers(TRAIN_CSV))
    if "label_a_win" in train_headers:
        return TRAIN_CSV

    label_headers = set(read_headers(LABEL_SOURCE_CSV))
    if "label_a_win" not in label_headers:
        raise ValueError("Training data has no label_a_win column.")

    missing_columns = [column for column in feature_columns if column not in label_headers]
    if missing_columns:
        raise ValueError("Label source file is missing some model feature columns.")

    return LABEL_SOURCE_CSV


def load_training_rows(path, feature_columns):
    train_matrix = []
    train_labels = []
    train_splits = []

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        has_split_column = "split" in (reader.fieldnames or [])

        for row in reader:
            label_text = (row.get("label_a_win") or "").strip()
            if label_text not in {"0", "1"}:
                continue

            feature_values = []
            for column in feature_columns:
                feature_values.append(parse_float(row.get(column)))

            train_matrix.append(feature_values)
            train_labels.append(float(label_text))

            if has_split_column:
                train_splits.append((row.get("split") or "").strip().lower())
            else:
                train_splits.append("")

    if not train_matrix:
        raise ValueError("No training rows were found.")

    return train_matrix, train_labels, train_splits


def train_model(train_matrix, train_labels, train_splits):
    fit_matrix = []
    fit_labels = []
    valid_matrix = []
    valid_labels = []

    for features, label, split_name in zip(train_matrix, train_labels, train_splits):
        if split_name == "valid":
            valid_matrix.append(features)
            valid_labels.append(label)
        else:
            fit_matrix.append(features)
            fit_labels.append(label)

    dtrain = xgb.DMatrix(np.asarray(fit_matrix, dtype=np.float32), label=np.asarray(fit_labels, dtype=np.float32))
    params = {
        "objective": "binary:logistic",
        "eval_metric": EVAL_METRIC,
        "eta": ETA,
        "max_depth": MAX_DEPTH,
        "min_child_weight": MIN_CHILD_WEIGHT,
        "subsample": SUBSAMPLE,
        "colsample_bytree": COLSAMPLE_BYTREE,
        "lambda": REG_LAMBDA,
        "tree_method": "hist",
        "seed": 42,
        "nthread": N_JOBS,
    }

    train_args = {"num_boost_round": NUM_BOOST_ROUND}
    best_iteration = None

    if valid_matrix:
        dvalid = xgb.DMatrix(np.asarray(valid_matrix, dtype=np.float32), label=np.asarray(valid_labels, dtype=np.float32))
        train_args["evals"] = [(dtrain, "train"), (dvalid, "valid")]
        train_args["early_stopping_rounds"] = EARLY_STOPPING_ROUNDS
    else:
        print("No valid split found, so the model trains on all rows with no early stopping.")

    model = xgb.train(params, dtrain, **train_args)

    if valid_matrix:
        best_iteration = getattr(model, "best_iteration", None)

    return model, best_iteration


def load_fighters():
    fighters_by_id = {}
    fighters_by_name = {}

    with FIGHTERS_CSV.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            fighter_id = (row.get("fighter_id") or "").strip()
            fighter_name = (row.get("fighter_name") or "").strip()

            if fighter_id != "":
                fighters_by_id[fighter_id] = row
            if fighter_name != "":
                fighters_by_name[fighter_name] = row

    return fighters_by_id, fighters_by_name


def find_fighter(matchup_row, side, fighters_by_id, fighters_by_name):
    fighter_id = (matchup_row.get(f"fighter_{side}_id") or "").strip()
    fighter_name = (matchup_row.get(f"fighter_{side}") or "").strip()

    if fighter_id != "" and fighter_id in fighters_by_id:
        return fighters_by_id[fighter_id]

    if fighter_name != "" and fighter_name in fighters_by_name:
        return fighters_by_name[fighter_name]

    missing_value = fighter_name or fighter_id or f"fighter_{side}"
    raise KeyError(f"Could not find exact match for fighter_{side}: {missing_value}")


def code_for(mapping, value):
    value = (value or "").strip()
    if value in mapping:
        return mapping[value]
    return mapping.get("__missing__", 0)


def get_side_value(fighter_row, base_field, fight_date):
    if base_field == "age_years":
        last_fight_date = parse_date(fighter_row["last_fight_date"])
        days_since_last = max((fight_date - last_fight_date).days, 0)
        return round(parse_float(fighter_row.get("age_years")) + (days_since_last / 365.25), 6)

    if base_field == "days_since_last_fight":
        last_fight_date = parse_date(fighter_row["last_fight_date"])
        return max((fight_date - last_fight_date).days, 0)

    return fighter_row.get(base_field, "")


def add_engineered_features(built_row, category_maps):
    division_name = built_row.get("division_norm", "")
    built_row["fight_year"] = parse_date(built_row["fight_date"]).year
    built_row["division_norm_code"] = code_for(category_maps.get("division_norm", {}), division_name)
    built_row["division_group_code"] = code_for(category_maps.get("division_group", {}), division_group(division_name))
    built_row["a_stance_code"] = code_for(category_maps.get("a_stance", {}), built_row.get("a_stance"))
    built_row["b_stance_code"] = code_for(category_maps.get("b_stance", {}), built_row.get("b_stance"))

    built_row["a_reach_height_gap"] = round(parse_float(built_row.get("a_reach")) - parse_float(built_row.get("a_height")), 6)
    built_row["b_reach_height_gap"] = round(parse_float(built_row.get("b_reach")) - parse_float(built_row.get("b_height")), 6)
    built_row["reach_height_gap_diff"] = round(parse_float(built_row.get("a_reach_height_gap")) - parse_float(built_row.get("b_reach_height_gap")), 6)

    if (built_row.get("a_stance") or "").strip() != "" and built_row.get("a_stance") == built_row.get("b_stance"):
        built_row["stance_same"] = 1
    else:
        built_row["stance_same"] = 0

    for key in list(built_row.keys()):
        if not key.startswith("a_"):
            continue
        base_field = key[2:]
        b_key = f"b_{base_field}"
        diff_key = f"{base_field}_diff"
        if b_key in built_row and diff_key not in built_row:
            built_row[diff_key] = round(parse_float(built_row.get(key)) - parse_float(built_row.get(b_key)), 6)

    built_row["elo_diff"] = round(parse_float(built_row.get("a_pre_fight_elo")) - parse_float(built_row.get("b_pre_fight_elo")), 6)

    a_sig_lpm = safe_rate(60.0, built_row.get("a_rw_avg_sig_landed_for"), built_row.get("a_rw_avg_fight_seconds"))
    b_sig_lpm = safe_rate(60.0, built_row.get("b_rw_avg_sig_landed_for"), built_row.get("b_rw_avg_fight_seconds"))
    built_row["reach_sig_volume_interaction_diff"] = round(parse_float(built_row.get("reach_diff")) * (a_sig_lpm - b_sig_lpm), 6)

    a_td_per15 = safe_rate(900.0, built_row.get("a_rw_avg_td_landed_for"), built_row.get("a_rw_avg_fight_seconds"))
    b_td_per15 = safe_rate(900.0, built_row.get("b_rw_avg_td_landed_for"), built_row.get("b_rw_avg_fight_seconds"))

    a_control_share = safe_divide(
        built_row.get("a_rw_avg_ctrl_seconds_for"),
        parse_float(built_row.get("a_rw_avg_ctrl_seconds_for")) + parse_float(built_row.get("a_rw_avg_ctrl_seconds_against")),
    )
    b_control_share = safe_divide(
        built_row.get("b_rw_avg_ctrl_seconds_for"),
        parse_float(built_row.get("b_rw_avg_ctrl_seconds_for")) + parse_float(built_row.get("b_rw_avg_ctrl_seconds_against")),
    )

    built_row["td_control_interaction_diff"] = round((a_td_per15 * a_control_share) - (b_td_per15 * b_control_share), 6)
    built_row["elo_momentum_interaction_diff"] = round(parse_float(built_row.get("elo_diff")) * (parse_float(built_row.get("momentum_diff")) / 100.0), 6)


def fill_missing_feature_columns(built_row, matchup_row, fighter_a, fighter_b, feature_columns, fight_date):
    for column in feature_columns:
        if column in built_row:
            continue

        if column in matchup_row:
            built_row[column] = matchup_row.get(column, "")
            continue

        if column.startswith("a_"):
            built_row[column] = get_side_value(fighter_a, column[2:], fight_date)
            continue

        if column.startswith("b_"):
            built_row[column] = get_side_value(fighter_b, column[2:], fight_date)
            continue

        if column.endswith("_diff"):
            base_field = column[:-5]
            a_column = f"a_{base_field}"
            b_column = f"b_{base_field}"
            if a_column in built_row and b_column in built_row:
                built_row[column] = round(parse_float(built_row.get(a_column)) - parse_float(built_row.get(b_column)), 6)
                continue

        built_row[column] = ""


def build_matchup_row(matchup_row, fighter_a, fighter_b, feature_columns, category_maps):
    fight_date = parse_date(matchup_row["fight_date"])
    a_last_fight_date = parse_date(fighter_a["last_fight_date"])
    b_last_fight_date = parse_date(fighter_b["last_fight_date"])

    a_days_since_last = max((fight_date - a_last_fight_date).days, 0)
    b_days_since_last = max((fight_date - b_last_fight_date).days, 0)

    built_row = {
        "fight_id_manual": matchup_row["fight_id_manual"],
        "event_name": matchup_row["event_name"],
        "fight_date": matchup_row["fight_date"],
        "fighter_a": fighter_a["fighter_name"],
        "fighter_b": fighter_b["fighter_name"],
        "division_norm": matchup_row["division_norm"],
        "scheduled_rounds": str(int(parse_float(matchup_row["scheduled_rounds"]))),
        "title_fight": str(int(parse_float(matchup_row["title_fight"]))),
        "a_fighter_id": fighter_a["fighter_id"],
        "b_fighter_id": fighter_b["fighter_id"],
        "a_last_fight_date": fighter_a["last_fight_date"],
        "b_last_fight_date": fighter_b["last_fight_date"],
        "a_age_years": round(parse_float(fighter_a.get("age_years")) + (a_days_since_last / 365.25), 6),
        "b_age_years": round(parse_float(fighter_b.get("age_years")) + (b_days_since_last / 365.25), 6),
        "a_days_since_last_fight": a_days_since_last,
        "b_days_since_last_fight": b_days_since_last,
    }

    columns_to_skip = {
        "fighter_id",
        "fighter_name",
        "last_fight_date",
        "event_name",
        "fight_id",
        "division_raw",
        "division_norm",
        "division_group",
        "scheduled_rounds",
        "title_fight",
        "opponent_fighter_id",
        "opponent_fighter_name",
        "result",
    }

    for column in fighter_a.keys():
        if column in columns_to_skip:
            continue
        built_row[f"a_{column}"] = fighter_a.get(column, "")
        built_row[f"b_{column}"] = fighter_b.get(column, "")

    add_engineered_features(built_row, category_maps)
    fill_missing_feature_columns(built_row, matchup_row, fighter_a, fighter_b, feature_columns, fight_date)
    return built_row


def build_feature_vector(built_row, feature_columns):
    feature_vector = []
    for column in feature_columns:
        feature_vector.append(parse_float(built_row.get(column)))
    return feature_vector


def build_prediction_row(built_row, probability, feature_columns):
    fighter_a = built_row["fighter_a"]
    fighter_b = built_row["fighter_b"]

    if probability >= 0.5:
        predicted_winner = fighter_a
        predicted_loser = fighter_b
    else:
        predicted_winner = fighter_b
        predicted_loser = fighter_a

    a_win_probability = round(probability, 6)
    b_win_probability = round(1.0 - probability, 6)

    return {
        "fight_id_manual": built_row["fight_id_manual"],
        "event_name": built_row["event_name"],
        "fight_date": built_row["fight_date"],
        "division_norm": built_row["division_norm"],
        "fighter_a": fighter_a,
        "fighter_b": fighter_b,
        "predicted_winner": predicted_winner,
        "predicted_loser": predicted_loser,
        "a_win_probability": a_win_probability,
        "b_win_probability": b_win_probability,
        "predicted_margin_pct": round(abs(a_win_probability - b_win_probability) * 100.0, 3),
        "confidence_tier": confidence_tier(a_win_probability),
        "model_feature_count": len(feature_columns),
        "model_features_used": ",".join(feature_columns),
    }


def prediction_columns():
    return [
        "fight_id_manual",
        "event_name",
        "fight_date",
        "division_norm",
        "fighter_a",
        "fighter_b",
        "predicted_winner",
        "predicted_loser",
        "a_win_probability",
        "b_win_probability",
        "predicted_margin_pct",
        "confidence_tier",
        "model_feature_count",
        "model_features_used",
    ]


def export_columns(feature_columns):
    start_columns = [
        "fight_id_manual",
        "event_name",
        "fight_date",
        "fighter_a",
        "fighter_b",
        "division_norm",
        "scheduled_rounds",
        "title_fight",
        "a_fighter_id",
        "b_fighter_id",
        "a_last_fight_date",
        "b_last_fight_date",
    ]

    columns = []
    seen = set()

    for column in start_columns + feature_columns:
        if column in seen:
            continue
        columns.append(column)
        seen.add(column)

    return columns


def load_matchups(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        missing_columns = [column for column in REQUIRED_MATCHUP_COLUMNS if column not in headers]
        if missing_columns:
            raise ValueError(f"Matchup CSV is missing columns: {', '.join(missing_columns)}")
        return list(reader)


def save_model_summary(path, model, feature_columns, best_iteration):
    summary = {
        "backend": "xgboost",
        "features": feature_columns,
        "num_boost_round": NUM_BOOST_ROUND,
        "eta": ETA,
        "max_depth": MAX_DEPTH,
        "min_child_weight": MIN_CHILD_WEIGHT,
        "subsample": SUBSAMPLE,
        "colsample_bytree": COLSAMPLE_BYTREE,
        "reg_lambda": REG_LAMBDA,
        "eval_metric": EVAL_METRIC,
        "n_jobs": N_JOBS,
        "early_stopping_rounds": EARLY_STOPPING_ROUNDS,
        "best_iteration": best_iteration,
        "xgboost_config": json.loads(model.save_config()),
    }
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Train the UFC model and predict a manual fight card.")
    parser.add_argument("matchups", nargs="?", type=Path, help="CSV file with the fights you want to predict.")
    parser.add_argument("--write-template", type=Path, help="Write a simple input template and stop.")
    parser.add_argument("--out-dir", type=Path, default=OUTPUT_DIR, help="Folder where the prediction files should be saved.")
    args = parser.parse_args()

    if args.write_template:
        write_template(args.write_template)
        print(f"Template written to: {args.write_template}")
        return

    if args.matchups is None:
        raise SystemExit("Pass a matchup CSV file or use --write-template.")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    feature_columns = load_feature_columns()
    training_rows_file = get_training_rows_file(feature_columns)
    train_matrix, train_labels, train_splits = load_training_rows(training_rows_file, feature_columns)
    model, best_iteration = train_model(train_matrix, train_labels, train_splits)
    model.save_model(MODEL_OUT)

    if best_iteration is not None:
        print(f"Early stopping used. Best iteration: {best_iteration + 1}")

    category_maps = load_category_maps()
    fighters_by_id, fighters_by_name = load_fighters()
    matchups = load_matchups(args.matchups)

    built_rows = []
    prediction_rows = []
    skipped_rows = []
    model_row_columns = export_columns(feature_columns)

    for matchup_row in matchups:
        try:
            fighter_a = find_fighter(matchup_row, "a", fighters_by_id, fighters_by_name)
            fighter_b = find_fighter(matchup_row, "b", fighters_by_id, fighters_by_name)
        except KeyError as error:
            skipped_rows.append(
                {
                    "fight_id_manual": matchup_row.get("fight_id_manual", ""),
                    "fighter_a": matchup_row.get("fighter_a", ""),
                    "fighter_b": matchup_row.get("fighter_b", ""),
                    "reason": str(error),
                }
            )
            continue

        built_row = build_matchup_row(matchup_row, fighter_a, fighter_b, feature_columns, category_maps)
        feature_vector = build_feature_vector(built_row, feature_columns)
        dmatrix = xgb.DMatrix(np.asarray([feature_vector], dtype=np.float32))

        if best_iteration is None:
            probability = float(model.predict(dmatrix)[0])
        else:
            probability = float(model.predict(dmatrix, iteration_range=(0, best_iteration + 1))[0])

        built_rows.append({column: built_row.get(column, "") for column in model_row_columns})
        prediction_rows.append(build_prediction_row(built_row, probability, feature_columns))

    card_slug = slugify(matchups[0]["event_name"]) if matchups else "manual_card"
    prediction_rows_path = args.out_dir / f"{card_slug}_prediction_rows.csv"
    predictions_path = args.out_dir / f"{card_slug}_predictions.csv"
    summary_path = args.out_dir / f"{card_slug}_model_summary.json"

    write_csv(prediction_rows_path, built_rows, model_row_columns)
    write_csv(predictions_path, prediction_rows, prediction_columns())
    save_model_summary(summary_path, model, feature_columns, best_iteration)

    print(f"Saved prediction rows: {prediction_rows_path}")
    print(f"Saved fight predictions: {predictions_path}")
    print(f"Saved model summary: {summary_path}")
    print(f"Saved XGBoost model: {MODEL_OUT}")
    print(f"Predicted fights: {len(prediction_rows)}")

    if skipped_rows:
        skipped_path = args.out_dir / f"{card_slug}_skipped_fights.csv"
        write_csv(skipped_path, skipped_rows, ["fight_id_manual", "fighter_a", "fighter_b", "reason"])
        print(f"Skipped fights: {len(skipped_rows)}")
        print(f"Skipped file: {skipped_path}")
    else:
        print("No fights were skipped.")


if __name__ == "__main__":
    main()
