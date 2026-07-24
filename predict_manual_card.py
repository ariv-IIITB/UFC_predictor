import argparse
import csv
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import pandas as pd 


DEFAULT_TRAIN_CSV =  pd.read_csv('final_data.csv')
DEFAULT_FIGHTERS_CSV =  pd.read_csv('fi')
DEFAULT_OUTPUT_DIR = Path(r"C:\Users\arivm\OneDrive\Documents\Codex")

REQUIRED_INPUT_COLUMNS = [
    "fight_id_manual",
    "event_name",
    "fight_date",
    "fighter_a",
    "fighter_b",
    "division_norm",
    "scheduled_rounds",
    "title_fight",
]

OPTIONAL_RESULT_COLUMNS = [
    "actual_winner",
    "actual_method",
    "actual_round",
    "actual_time",
    "actual_notes",
]

# Compact feature set chosen to be:
# 1) derivable from fighter_state rows
# 2) already present in the historical master file
# 3) reasonably predictive without extra dependencies
MODEL_FEATURES = [
    "scheduled_rounds",
    "title_fight",
    "a_age_years",
    "b_age_years",
    "age_years_diff",
    "a_prior_fights",
    "b_prior_fights",
    "prior_fights_diff",
    "a_prior_win_rate",
    "b_prior_win_rate",
    "prior_win_rate_diff",
    "a_days_since_last_fight",
    "b_days_since_last_fight",
    "days_since_last_fight_diff",
    "reach_diff",
    "height_diff",
    "a_pre_fight_elo",
    "b_pre_fight_elo",
    "elo_diff",
    "striking_offense_diff",
    "striking_defense_diff",
    "grappling_offense_diff",
    "grappling_defense_diff",
    "finishing_durability_diff",
    "momentum_diff",
    "experience_big_fight_diff",
    "physical_diff",
    "overall_diff",
]

# Richer export set for the generated matchup rows CSV.
EXPORT_ROW_COLUMNS = [
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
    "a_age_years",
    "b_age_years",
    "age_years_diff",
    "a_prior_fights",
    "b_prior_fights",
    "prior_fights_diff",
    "a_prior_win_rate",
    "b_prior_win_rate",
    "prior_win_rate_diff",
    "a_days_since_last_fight",
    "b_days_since_last_fight",
    "days_since_last_fight_diff",
    "a_reach",
    "b_reach",
    "reach_diff",
    "a_height",
    "b_height",
    "height_diff",
    "a_pre_fight_elo",
    "b_pre_fight_elo",
    "elo_diff",
    "a_striking_offense",
    "b_striking_offense",
    "striking_offense_diff",
    "a_striking_defense",
    "b_striking_defense",
    "striking_defense_diff",
    "a_grappling_offense",
    "b_grappling_offense",
    "grappling_offense_diff",
    "a_grappling_defense",
    "b_grappling_defense",
    "grappling_defense_diff",
    "a_finishing_durability",
    "b_finishing_durability",
    "finishing_durability_diff",
    "a_momentum",
    "b_momentum",
    "momentum_diff",
    "a_experience_big_fight",
    "b_experience_big_fight",
    "experience_big_fight_diff",
    "a_physical",
    "b_physical",
    "physical_diff",
    "a_overall",
    "b_overall",
    "overall_diff",
]


def slugify(text):
    cleaned = re.sub(r"[^a-z0-9]+", "_", (text or "").strip().lower())
    return cleaned.strip("_") or "card"


def parse_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def normalize_name(name):
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def parse_iso_date(text):
    return datetime.strptime((text or "").strip(), "%Y-%m-%d")


def sigmoid(value):
    if value >= 0:
        exp_term = math.exp(-value)
        return 1.0 / (1.0 + exp_term)
    exp_term = math.exp(value)
    return exp_term / (1.0 + exp_term)


def confidence_tier(probability):
    edge = abs(probability - 0.5)
    if edge >= 0.20:
        return "very_strong"
    if edge >= 0.12:
        return "strong"
    if edge >= 0.07:
        return "medium"
    return "lean"


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
        "actual_winner": "",
        "actual_method": "",
        "actual_round": "",
        "actual_time": "",
        "actual_notes": "",
    }
    fieldnames = REQUIRED_INPUT_COLUMNS + OPTIONAL_RESULT_COLUMNS
    write_csv(path, [row], fieldnames)


@dataclass
class Standardizer:
    means: list
    stds: list

    def transform(self, values):
        return [
            (value - mean) / std if std > 1e-12 else 0.0
            for value, mean, std in zip(values, self.means, self.stds)
        ]


def fit_standardizer(matrix):
    if not matrix:
        raise ValueError("No training rows were found.")
    width = len(matrix[0])
    means = []
    stds = []
    for idx in range(width):
        column = [row[idx] for row in matrix]
        mean_value = sum(column) / len(column)
        variance = sum((value - mean_value) ** 2 for value in column) / len(column)
        std_value = math.sqrt(variance)
        if std_value < 1e-12:
            std_value = 1.0
        means.append(mean_value)
        stds.append(std_value)
    return Standardizer(means, stds)


class LogisticRegressor:
    def __init__(self, feature_count):
        self.weights = [0.0] * feature_count
        self.bias = 0.0

    def fit(self, x_rows, y_rows, epochs=180, learning_rate=0.05, l2=0.0005):
        sample_count = len(x_rows)
        for _ in range(epochs):
            grad_w = [0.0] * len(self.weights)
            grad_b = 0.0
            for features, label in zip(x_rows, y_rows):
                score = self.bias + sum(weight * value for weight, value in zip(self.weights, features))
                prediction = sigmoid(score)
                error = prediction - label
                for idx, value in enumerate(features):
                    grad_w[idx] += error * value
                grad_b += error
            inv_n = 1.0 / sample_count
            for idx in range(len(self.weights)):
                grad = (grad_w[idx] * inv_n) + (l2 * self.weights[idx])
                self.weights[idx] -= learning_rate * grad
            self.bias -= learning_rate * (grad_b * inv_n)

    def predict_proba(self, features):
        score = self.bias + sum(weight * value for weight, value in zip(self.weights, features))
        return sigmoid(score)


def load_training_rows(path):
    rows = []
    labels = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            label_text = (row.get("label_a_win") or "").strip()
            if label_text not in {"0", "1"}:
                continue
            rows.append([parse_float(row.get(column)) for column in MODEL_FEATURES])
            labels.append(float(label_text))
    return rows, labels


def load_fighter_state(path):
    fighters = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            fighter_id = (row.get("fighter_id") or "").strip()
            fighter_name = row.get("fighter_name") or ""
            if fighter_id:
                fighters[("id", fighter_id)] = row
            fighters[("name", normalize_name(fighter_name))] = row
    return fighters


def resolve_fighter(matchup_row, fighters, side):
    fighter_id = (matchup_row.get(f"fighter_{side}_id") or "").strip()
    if fighter_id and ("id", fighter_id) in fighters:
        return fighters[("id", fighter_id)]

    fighter_name = matchup_row.get(f"fighter_{side}") or ""
    key = ("name", normalize_name(fighter_name))
    if key in fighters:
        return fighters[key]
    raise KeyError(f"Could not find fighter_{side}: {fighter_name or fighter_id}")


def build_matchup_row(matchup_row, fighter_a, fighter_b):
    fight_date = parse_iso_date(matchup_row["fight_date"])
    a_last_fight_date = parse_iso_date(fighter_a["last_fight_date"])
    b_last_fight_date = parse_iso_date(fighter_b["last_fight_date"])
    a_days_from_latest = max((fight_date - a_last_fight_date).days, 0)
    b_days_from_latest = max((fight_date - b_last_fight_date).days, 0)
    a_age_years = parse_float(fighter_a.get("age_years")) + (a_days_from_latest / 365.25)
    b_age_years = parse_float(fighter_b.get("age_years")) + (b_days_from_latest / 365.25)

    built = {
        "fight_id_manual": matchup_row["fight_id_manual"],
        "event_name": matchup_row["event_name"],
        "fight_date": matchup_row["fight_date"],
        "fighter_a": fighter_a["fighter_name"],
        "fighter_b": fighter_b["fighter_name"],
        "division_norm": matchup_row["division_norm"],
        "scheduled_rounds": matchup_row["scheduled_rounds"],
        "title_fight": matchup_row["title_fight"],
        "a_fighter_id": fighter_a["fighter_id"],
        "b_fighter_id": fighter_b["fighter_id"],
        "a_last_fight_date": fighter_a["last_fight_date"],
        "b_last_fight_date": fighter_b["last_fight_date"],
        "a_age_years": round(a_age_years, 6),
        "b_age_years": round(b_age_years, 6),
        "a_days_since_last_fight": a_days_from_latest,
        "b_days_since_last_fight": b_days_from_latest,
    }

    numeric_fields = []
    for key in fighter_a.keys():
        if key in {
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
        }:
            continue
        a_column = f"a_{key}"
        b_column = f"b_{key}"
        if a_column not in built:
            built[a_column] = fighter_a.get(key, "")
        if b_column not in built:
            built[b_column] = fighter_b.get(key, "")
        numeric_fields.append(key)

    diff_whitelist = {
        "age_years",
        "prior_fights",
        "prior_win_rate",
        "days_since_last_fight",
        "reach",
        "height",
        "pre_fight_elo",
        "striking_offense",
        "striking_defense",
        "grappling_offense",
        "grappling_defense",
        "finishing_durability",
        "momentum",
        "experience_big_fight",
        "physical",
        "overall",
    }
    for field in diff_whitelist:
        built[f"{field}_diff"] = round(parse_float(fighter_a.get(field)) - parse_float(fighter_b.get(field)), 6)

    built["scheduled_rounds"] = str(int(parse_float(matchup_row["scheduled_rounds"])))
    built["title_fight"] = str(int(parse_float(matchup_row["title_fight"])))
    return built


def matchup_to_feature_vector(row):
    return [parse_float(row.get(column)) for column in MODEL_FEATURES]


def enrich_with_actuals(prediction_row, matchup_row):
    actual_winner = (matchup_row.get("actual_winner") or "").strip()
    if not actual_winner:
        prediction_row["actual_winner"] = ""
        prediction_row["actual_method"] = matchup_row.get("actual_method", "")
        prediction_row["actual_round"] = matchup_row.get("actual_round", "")
        prediction_row["actual_time"] = matchup_row.get("actual_time", "")
        prediction_row["actual_notes"] = matchup_row.get("actual_notes", "")
        prediction_row["prediction_correct"] = ""
        return

    prediction_row["actual_winner"] = actual_winner
    prediction_row["actual_method"] = matchup_row.get("actual_method", "")
    prediction_row["actual_round"] = matchup_row.get("actual_round", "")
    prediction_row["actual_time"] = matchup_row.get("actual_time", "")
    prediction_row["actual_notes"] = matchup_row.get("actual_notes", "")
    prediction_row["prediction_correct"] = "1" if normalize_name(actual_winner) == normalize_name(prediction_row["predicted_winner"]) else "0"


def build_prediction_output(matchup_row, built_row, probability):
    fighter_a = built_row["fighter_a"]
    fighter_b = built_row["fighter_b"]
    predicted_winner = fighter_a if probability >= 0.5 else fighter_b
    predicted_loser = fighter_b if probability >= 0.5 else fighter_a
    a_win_probability = round(probability, 6)
    b_win_probability = round(1.0 - probability, 6)
    output = {
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
        "model_features_used": ",".join(MODEL_FEATURES),
    }
    enrich_with_actuals(output, matchup_row)
    return output


def prediction_fieldnames():
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
        "actual_winner",
        "actual_method",
        "actual_round",
        "actual_time",
        "actual_notes",
        "prediction_correct",
        "model_features_used",
    ]


def load_matchups(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED_INPUT_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Manual matchup CSV is missing columns: {', '.join(missing)}")
        return list(reader)


def save_model_summary(path, standardizer, model):
    payload = {
        "features": MODEL_FEATURES,
        "means": standardizer.means,
        "stds": standardizer.stds,
        "weights": model.weights,
        "bias": model.bias,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Train on the historical UFC master CSV and predict a manual fight card from fighter state rows.")
    parser.add_argument("--matchups", type=Path, help="Manual input CSV describing the card to predict.")
    parser.add_argument("--fighters", type=Path, default=DEFAULT_FIGHTERS_CSV, help="Latest fighter-state CSV.")
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN_CSV, help="Historical training CSV.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated CSVs.")
    parser.add_argument("--write-template", type=Path, help="Only write a blank-ish template CSV to this path and exit.")
    args = parser.parse_args()

    if args.write_template:
        write_template(args.write_template)
        print(f"Template written to: {args.write_template}")
        return

    if not args.matchups:
        raise SystemExit("Pass --matchups <csv> or use --write-template <csv> first.")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    train_matrix, train_labels = load_training_rows(args.train)
    standardizer = fit_standardizer(train_matrix)
    standardized_train = [standardizer.transform(row) for row in train_matrix]
    model = LogisticRegressor(feature_count=len(MODEL_FEATURES))
    model.fit(standardized_train, train_labels)

    fighters = load_fighter_state(args.fighters)
    matchups = load_matchups(args.matchups)

    built_rows = []
    prediction_rows = []
    for matchup_row in matchups:
        fighter_a = resolve_fighter(matchup_row, fighters, "a")
        fighter_b = resolve_fighter(matchup_row, fighters, "b")
        built_row = build_matchup_row(matchup_row, fighter_a, fighter_b)
        standardized_features = standardizer.transform(matchup_to_feature_vector(built_row))
        probability = model.predict_proba(standardized_features)
        built_rows.append({column: built_row.get(column, "") for column in EXPORT_ROW_COLUMNS})
        prediction_rows.append(build_prediction_output(matchup_row, built_row, probability))

    card_slug = slugify(matchups[0]["event_name"]) if matchups else "manual_card"
    model_rows_path = args.out_dir / f"{card_slug}_prediction_rows.csv"
    predictions_path = args.out_dir / f"{card_slug}_predictions.csv"
    model_summary_path = args.out_dir / f"{card_slug}_model_summary.json"

    write_csv(model_rows_path, built_rows, EXPORT_ROW_COLUMNS)
    write_csv(predictions_path, prediction_rows, prediction_fieldnames())
    save_model_summary(model_summary_path, standardizer, model)

    print(f"Saved prediction rows: {model_rows_path}")
    print(f"Saved fight predictions: {predictions_path}")
    print(f"Saved model summary: {model_summary_path}")
    print(f"Predicted fights: {len(prediction_rows)}")


if __name__ == "__main__":
    main()
