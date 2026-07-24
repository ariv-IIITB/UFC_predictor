import argparse
import csv
import difflib
import json
import math
import re
import dataclasses
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import xgboost as xgb


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TRAIN_CSV = BASE_DIR / "default_train.csv"
DEFAULT_LABEL_SOURCE_CSV = BASE_DIR / "final_data.csv"
DEFAULT_FIGHTERS_CSV = BASE_DIR / "fighter_state.csv"
DEFAULT_CATEGORY_MAPS_JSON = BASE_DIR / "ufc_prefight_post2001_binary_mirrored_xgboost_category_maps.json"
DEFAULT_OUTPUT_DIR = BASE_DIR
DEFAULT_XGB_MODEL_PATH = BASE_DIR / "ufc_predict_manual_card_xgboost_model_reduced.json"
EXCLUDED_TRAIN_COLUMNS = {"fight_id", "fight_date", "split", "label_a_win"}


# ---------------------------------------------------------------------------
# XGBoost hyperparameters -- THE ONLY PLACE YOU SHOULD NEED TO EDIT.
#
# Change any value below and every run picks it up automatically (these
# become the CLI defaults too, so `python ufc_predict.py --matchups ...`
# with no extra flags always trains with exactly what's here). You can
# still override a single run from the command line with e.g.
# `--max-depth 6`, but you no longer need to.
# ---------------------------------------------------------------------------
@dataclass
class XGBConfig:
    num_boost_round: int = 500         # n_estimators / boosting rounds
    eta: float = 0.035                 # learning rate
    max_depth: int = 5
    min_child_weight: float = 3.0
    subsample: float = 0.80
    colsample_bytree: float = 0.7
    reg_lambda: float = 1.0            # L2 regularization
    eval_metric: str = "logloss,auc"   # comma-separated
    n_jobs: int = -1                   # -1 = use all cores (native 'nthread')
    early_stopping_rounds: int = 100   # only used if a 'valid' split exists


XGB_CONFIG = XGBConfig()
# ---------------------------------------------------------------------------


# Fighter-name fuzzy matching. AUTO_RESOLVE requires a single, very close
# candidate before we'll silently use it in place of an exact match.
# SUGGESTION_CUTOFF is looser and only used to surface "did you mean" hints
# in skip messages -- it never changes which row gets used.
FUZZY_AUTO_RESOLVE_CUTOFF = 0.90
FUZZY_SUGGESTION_CUTOFF = 0.6
FUZZY_SUGGESTION_LIMIT = 3

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


def parse_int(value, default=0):
    return int(parse_float(value, default=default))


def normalize_name(name):
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def parse_iso_date(text):
    return datetime.strptime((text or "").strip(), "%Y-%m-%d")


def safe_div(num, den, default=0.0):
    den_value = parse_float(den, default=None)
    if den_value in (None, 0.0):
        return default
    return parse_float(num) / den_value


def safe_rate(multiplier, numerator, denominator, default=0.0):
    den_value = parse_float(denominator, default=None)
    if den_value in (None, 0.0):
        return default
    return multiplier * parse_float(numerator) / den_value


def division_group(division_norm):
    division = (division_norm or "").strip().lower()
    if division.startswith("women's "):
        return "women"
    if division in {"open weight", "catch weight", "super heavyweight", "superfight championship", "other"}:
        return "special"
    return "men"


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


def load_category_maps(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def infer_model_features(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
    features = [column for column in headers if column not in EXCLUDED_TRAIN_COLUMNS]
    if not features:
        raise ValueError("No usable model features were found in the training CSV.")
    return features


def csv_headers(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or []


def build_export_columns(feature_columns):
    prefix_columns = [
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
    ordered = []
    seen = set()
    for column in prefix_columns + feature_columns:
        if column not in seen:
            ordered.append(column)
            seen.add(column)
    return ordered


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

    def fit(self, x_rows, y_rows, epochs=40, learning_rate=0.05, l2=0.0005):
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


def train_xgboost_model(
    train_matrix,
    train_labels,
    num_boost_round,
    eta,
    max_depth,
    min_child_weight,
    subsample,
    colsample_bytree,
    reg_lambda,
    eval_metric,
    nthread,
    valid_matrix=None,
    valid_labels=None,
    early_stopping_rounds=None,
):
    x_matrix = np.asarray(train_matrix, dtype=np.float32)
    y_vector = np.asarray(train_labels, dtype=np.float32)
    dtrain = xgb.DMatrix(x_matrix, label=y_vector)
    params = {
        "objective": "binary:logistic",
        "eval_metric": eval_metric,
        "eta": eta,
        "max_depth": max_depth,
        "min_child_weight": min_child_weight,
        "subsample": subsample,
        "colsample_bytree": colsample_bytree,
        "lambda": reg_lambda,
        "tree_method": "hist",
        "seed": 42,
        "nthread": nthread,
    }

    train_kwargs = {"num_boost_round": num_boost_round}
    has_valid_set = valid_matrix is not None and valid_labels is not None and len(valid_matrix) > 0
    if has_valid_set:
        valid_x = np.asarray(valid_matrix, dtype=np.float32)
        valid_y = np.asarray(valid_labels, dtype=np.float32)
        dvalid = xgb.DMatrix(valid_x, label=valid_y)
        train_kwargs["evals"] = [(dtrain, "train"), (dvalid, "valid")]
        if early_stopping_rounds:
            train_kwargs["early_stopping_rounds"] = early_stopping_rounds

    booster = xgb.train(params, dtrain, **train_kwargs)
    best_iteration = getattr(booster, "best_iteration", None) if has_valid_set else None
    return booster, params, best_iteration


def load_training_rows(path, feature_columns):
    """Returns (feature_rows, labels, splits). splits[i] is the lowercased
    'split' column value for that row ("" if the column is absent), so
    callers can carve out a 'valid' subset for XGBoost early stopping
    without a second pass over the file.
    """
    rows = []
    labels = []
    splits = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        has_split_column = "split" in (reader.fieldnames or [])
        for row in reader:
            label_text = (row.get("label_a_win") or "").strip()
            if label_text not in {"0", "1"}:
                continue
            rows.append([parse_float(row.get(column)) for column in feature_columns])
            labels.append(float(label_text))
            splits.append((row.get("split") or "").strip().lower() if has_split_column else "")
    return rows, labels, splits


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


def fighter_name_pool(fighters):
    """All normalized fighter names available for fuzzy matching."""
    return [key[1] for key in fighters if key[0] == "name"]


def find_close_fighter_names(fighter_name, fighters, cutoff, limit):
    normalized_target = normalize_name(fighter_name)
    return difflib.get_close_matches(normalized_target, fighter_name_pool(fighters), n=limit, cutoff=cutoff)


def resolve_fighter(matchup_row, fighters, side):
    """Look up a fighter row for one side of a matchup.

    Returns (fighter_row, match_type) on success, where match_type is one of
    "exact_id", "exact_name", or "fuzzy_name:<matched name>" so callers can
    log when an auto-correction was applied. Raises KeyError with concrete
    "did you mean" suggestions when no confident match exists, so a bad name
    in the matchup CSV is easy to fix instead of just crashing.
    """
    fighter_id = (matchup_row.get(f"fighter_{side}_id") or "").strip()
    if fighter_id and ("id", fighter_id) in fighters:
        return fighters[("id", fighter_id)], "exact_id"

    fighter_name = matchup_row.get(f"fighter_{side}") or ""
    key = ("name", normalize_name(fighter_name))
    if key in fighters:
        return fighters[key], "exact_name"

    # Auto-resolve only when there is exactly one very-close candidate --
    # ambiguity (e.g. two similarly-spelled fighters) should never be
    # guessed silently, so we fall through to the error path instead.
    close_matches = find_close_fighter_names(fighter_name, fighters, cutoff=FUZZY_AUTO_RESOLVE_CUTOFF, limit=2)
    if len(close_matches) == 1:
        matched_row = fighters[("name", close_matches[0])]
        return matched_row, f"fuzzy_name:{matched_row.get('fighter_name', close_matches[0])}"

    suggestions = find_close_fighter_names(fighter_name, fighters, cutoff=FUZZY_SUGGESTION_CUTOFF, limit=FUZZY_SUGGESTION_LIMIT)
    suggestion_names = [fighters[("name", candidate)].get("fighter_name", candidate) for candidate in suggestions]
    if suggestion_names:
        hint = f" Closest names in fighter_state.csv: {', '.join(suggestion_names)}."
    else:
        hint = " No similar names found in fighter_state.csv -- this fighter may be missing entirely."
    raise KeyError(f"Could not find fighter_{side}: {fighter_name or fighter_id}.{hint}")


def code_for(mapping, raw_value):
    normalized = (raw_value or "").strip()
    if normalized in mapping:
        return mapping[normalized]
    return mapping.get("__missing__", 0)


def side_feature_value(fighter_row, base_field, fight_date):
    if base_field == "age_years":
        last_fight_date = parse_iso_date(fighter_row["last_fight_date"])
        return round(parse_float(fighter_row.get("age_years")) + (max((fight_date - last_fight_date).days, 0) / 365.25), 6)
    if base_field == "days_since_last_fight":
        last_fight_date = parse_iso_date(fighter_row["last_fight_date"])
        return max((fight_date - last_fight_date).days, 0)
    return fighter_row.get(base_field, "")


def attach_engineered_features(built, category_maps):
    division_norm = built.get("division_norm", "")
    built["fight_year"] = parse_iso_date(built["fight_date"]).year
    built["division_norm_code"] = code_for(category_maps.get("division_norm", {}), division_norm)
    built["division_group_code"] = code_for(category_maps.get("division_group", {}), division_group(division_norm))
    built["a_stance_code"] = code_for(category_maps.get("a_stance", {}), built.get("a_stance"))
    built["b_stance_code"] = code_for(category_maps.get("b_stance", {}), built.get("b_stance"))
    built["a_reach_height_gap"] = round(parse_float(built.get("a_reach")) - parse_float(built.get("a_height")), 6)
    built["b_reach_height_gap"] = round(parse_float(built.get("b_reach")) - parse_float(built.get("b_height")), 6)
    built["reach_height_gap_diff"] = round(parse_float(built.get("a_reach_height_gap")) - parse_float(built.get("b_reach_height_gap")), 6)
    built["stance_same"] = 1 if (built.get("a_stance") or "").strip() and built.get("a_stance") == built.get("b_stance") else 0

    for key in list(built.keys()):
        if key.startswith("a_"):
            base_field = key[2:]
            b_column = f"b_{base_field}"
            diff_column = f"{base_field}_diff"
            if b_column in built and diff_column not in built:
                built[diff_column] = round(parse_float(built.get(key)) - parse_float(built.get(b_column)), 6)

    built["elo_diff"] = round(parse_float(built.get("a_pre_fight_elo")) - parse_float(built.get("b_pre_fight_elo")), 6)

    a_rw_sig_lpm = safe_rate(60.0, built.get("a_rw_avg_sig_landed_for"), built.get("a_rw_avg_fight_seconds"))
    b_rw_sig_lpm = safe_rate(60.0, built.get("b_rw_avg_sig_landed_for"), built.get("b_rw_avg_fight_seconds"))
    reach_diff = parse_float(built.get("reach_diff"))
    built["reach_sig_volume_interaction_diff"] = round(reach_diff * (a_rw_sig_lpm - b_rw_sig_lpm), 6)

    a_td_per15 = safe_rate(900.0, built.get("a_rw_avg_td_landed_for"), built.get("a_rw_avg_fight_seconds"))
    b_td_per15 = safe_rate(900.0, built.get("b_rw_avg_td_landed_for"), built.get("b_rw_avg_fight_seconds"))
    a_ctrl_share = safe_div(
        built.get("a_rw_avg_ctrl_seconds_for"),
        parse_float(built.get("a_rw_avg_ctrl_seconds_for")) + parse_float(built.get("a_rw_avg_ctrl_seconds_against")),
    )
    b_ctrl_share = safe_div(
        built.get("b_rw_avg_ctrl_seconds_for"),
        parse_float(built.get("b_rw_avg_ctrl_seconds_for")) + parse_float(built.get("b_rw_avg_ctrl_seconds_against")),
    )
    built["td_control_interaction_diff"] = round((a_td_per15 * a_ctrl_share) - (b_td_per15 * b_ctrl_share), 6)
    built["elo_momentum_interaction_diff"] = round(parse_float(built.get("elo_diff")) * (parse_float(built.get("momentum_diff")) / 100.0), 6)


def fill_remaining_feature_columns(built, matchup_row, fighter_a, fighter_b, feature_columns, fight_date):
    for column in feature_columns:
        if column in built:
            continue
        if column in matchup_row:
            built[column] = matchup_row.get(column, "")
            continue
        if column.startswith("a_"):
            built[column] = side_feature_value(fighter_a, column[2:], fight_date)
            continue
        if column.startswith("b_"):
            built[column] = side_feature_value(fighter_b, column[2:], fight_date)
            continue
        if column.endswith("_diff"):
            base_field = column[:-5]
            a_column = f"a_{base_field}"
            b_column = f"b_{base_field}"
            if a_column in built and b_column in built:
                built[column] = round(parse_float(built.get(a_column)) - parse_float(built.get(b_column)), 6)
                continue
        built[column] = ""


def build_matchup_row(matchup_row, fighter_a, fighter_b, feature_columns, category_maps):
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

    built["scheduled_rounds"] = str(int(parse_float(matchup_row["scheduled_rounds"])))
    built["title_fight"] = str(int(parse_float(matchup_row["title_fight"])))
    attach_engineered_features(built, category_maps)
    fill_remaining_feature_columns(built, matchup_row, fighter_a, fighter_b, feature_columns, fight_date)
    return built


def matchup_to_feature_vector(row, feature_columns):
    return [parse_float(row.get(column)) for column in feature_columns]


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


def build_prediction_output(matchup_row, built_row, probability, feature_columns):
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
        "model_feature_count": len(feature_columns),
        "model_features_used": ",".join(feature_columns),
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
        "model_feature_count",
        "model_features_used",
    ]


def load_matchups(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in REQUIRED_INPUT_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Manual matchup CSV is missing columns: {', '.join(missing)}")
        return list(reader)


def save_model_summary(path, standardizer, model, feature_columns):
    backend = "xgboost" if isinstance(model, xgb.Booster) else "logistic_fallback"
    payload = {
        "backend": backend,
        "features": feature_columns,
    }
    if standardizer is not None:
        payload["means"] = standardizer.means
        payload["stds"] = standardizer.stds
    if isinstance(model, xgb.Booster):
        payload["xgboost_config"] = json.loads(model.save_config())
    else:
        payload["weights"] = model.weights
        payload["bias"] = model.bias
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_xgb_config_overrides(path):
    """Apply a JSON file of XGBConfig field overrides on top of XGB_CONFIG.

    Unknown keys raise immediately (a typo'd param should never be silently
    ignored). Returns a new XGBConfig; XGB_CONFIG itself is left untouched.
    """
    overrides = json.loads(path.read_text(encoding="utf-8"))
    valid_fields = {field.name for field in dataclasses.fields(XGBConfig)}
    unknown = sorted(set(overrides) - valid_fields)
    if unknown:
        raise ValueError(
            f"Unknown field(s) in --xgb-config {path}: {', '.join(unknown)}. "
            f"Valid fields: {', '.join(sorted(valid_fields))}."
        )
    return dataclasses.replace(XGB_CONFIG, **overrides)


def main():
    # --xgb-config is resolved in a lightweight pre-pass so its values can
    # become the *defaults* for the main parser below -- meaning the
    # precedence is: XGB_CONFIG (in this file) < --xgb-config JSON <
    # explicit --eta/--max-depth/etc. flags on the command line.
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--xgb-config", type=Path)
    pre_args, _ = pre_parser.parse_known_args()
    effective_xgb_config = XGB_CONFIG if not pre_args.xgb_config else load_xgb_config_overrides(pre_args.xgb_config)

    parser = argparse.ArgumentParser(description="Train on the historical UFC master CSV and predict a manual fight card from fighter state rows.")
    parser.add_argument("--matchups", type=Path, help="Manual input CSV describing the card to predict.")
    parser.add_argument("--fighters", type=Path, default=DEFAULT_FIGHTERS_CSV, help="Latest fighter-state CSV.")
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN_CSV, help="Historical training CSV.")
    parser.add_argument(
        "--label-source",
        type=Path,
        default=DEFAULT_LABEL_SOURCE_CSV,
        help="CSV used for label_a_win rows when --train is a reduced feature-only schema.",
    )
    parser.add_argument("--category-maps", type=Path, default=DEFAULT_CATEGORY_MAPS_JSON, help="Category map JSON used to encode division and stance fields.")
    parser.add_argument("--xgb-model-out", type=Path, default=DEFAULT_XGB_MODEL_PATH, help="Where to save the trained XGBoost booster.")
    parser.add_argument("--use-logistic-fallback", action="store_true", help="Use the old fallback logistic trainer instead of XGBoost.")
    parser.add_argument("--num-boost-round", type=int, default=effective_xgb_config.num_boost_round, help="Boosting rounds for XGBoost (n_estimators). Edit XGB_CONFIG at the top of this file to change the default.")
    parser.add_argument("--eta", type=float, default=effective_xgb_config.eta, help="Learning rate for XGBoost. Edit XGB_CONFIG at the top of this file to change the default.")
    parser.add_argument("--max-depth", type=int, default=effective_xgb_config.max_depth, help="Max tree depth for XGBoost. Edit XGB_CONFIG at the top of this file to change the default.")
    parser.add_argument("--min-child-weight", type=float, default=effective_xgb_config.min_child_weight, help="Min child weight for XGBoost. Edit XGB_CONFIG at the top of this file to change the default.")
    parser.add_argument("--subsample", type=float, default=effective_xgb_config.subsample, help="Subsample ratio for XGBoost. Edit XGB_CONFIG at the top of this file to change the default.")
    parser.add_argument("--colsample-bytree", type=float, default=effective_xgb_config.colsample_bytree, help="Column sample ratio for XGBoost. Edit XGB_CONFIG at the top of this file to change the default.")
    parser.add_argument("--reg-lambda", type=float, default=effective_xgb_config.reg_lambda, help="L2 regularization for XGBoost. Edit XGB_CONFIG at the top of this file to change the default.")
    parser.add_argument(
        "--eval-metric",
        type=str,
        default=effective_xgb_config.eval_metric,
        help="Comma-separated eval metrics for XGBoost, e.g. 'logloss,auc'. Edit XGB_CONFIG at the top of this file to change the default.",
    )
    parser.add_argument(
        "--n-jobs",
        type=int,
        default=effective_xgb_config.n_jobs,
        help="Threads for XGBoost (-1 = use all available cores; maps to the native 'nthread' param). Edit XGB_CONFIG at the top of this file to change the default.",
    )
    parser.add_argument(
        "--early-stopping-rounds",
        type=int,
        default=effective_xgb_config.early_stopping_rounds,
        help="Stop boosting if the valid-split metric hasn't improved in this many rounds. "
        "Only applies when the training source has a 'split' column with 'valid' rows -- "
        "otherwise this is ignored and a warning is printed. Edit XGB_CONFIG at the top of "
        "this file to change the default.",
    )
    parser.add_argument(
        "--xgb-config",
        type=Path,
        help="Optional JSON file with any subset of XGBConfig fields "
        "(num_boost_round, eta, max_depth, min_child_weight, subsample, "
        "colsample_bytree, reg_lambda, eval_metric, n_jobs, early_stopping_rounds). "
        "Values here override XGB_CONFIG and are themselves overridden by any "
        "explicit --eta/--max-depth/etc. flags passed on the command line.",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for generated CSVs.")
    parser.add_argument("--epochs", type=int, default=40, help="Training epochs for the fallback logistic model.")
    parser.add_argument("--learning-rate", type=float, default=0.05, help="Learning rate for the fallback logistic model.")
    parser.add_argument("--l2", type=float, default=0.0005, help="L2 regularization for the fallback logistic model.")
    parser.add_argument("--write-template", type=Path, help="Only write a blank-ish template CSV to this path and exit.")
    args = parser.parse_args()

    if args.write_template:
        write_template(args.write_template)
        print(f"Template written to: {args.write_template}")
        return

    if not args.matchups:
        raise SystemExit("Pass --matchups <csv> or use --write-template <csv> first.")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    feature_columns = infer_model_features(args.train)
    train_headers = csv_headers(args.train)
    train_rows_source = args.train
    if "label_a_win" not in train_headers:
        label_headers = csv_headers(args.label_source)
        if "label_a_win" not in label_headers:
            raise ValueError(
                f"Neither --train ({args.train}) nor --label-source ({args.label_source}) has label_a_win."
            )
        missing_features = [column for column in feature_columns if column not in set(label_headers)]
        if missing_features:
            raise ValueError(
                "--label-source is missing feature columns required by --train schema: "
                + ", ".join(missing_features[:10])
                + ("..." if len(missing_features) > 10 else "")
            )
        train_rows_source = args.label_source
    category_maps = load_category_maps(args.category_maps)
    train_matrix, train_labels, train_splits = load_training_rows(train_rows_source, feature_columns)

    has_valid_split = any(split_value == "valid" for split_value in train_splits)
    if has_valid_split:
        fit_matrix, fit_labels, valid_matrix, valid_labels = [], [], [], []
        for features, label, split_value in zip(train_matrix, train_labels, train_splits):
            if split_value == "valid":
                valid_matrix.append(features)
                valid_labels.append(label)
            else:
                fit_matrix.append(features)
                fit_labels.append(label)
    else:
        fit_matrix, fit_labels = train_matrix, train_labels
        valid_matrix, valid_labels = None, None
        print(
            "No 'split' column with 'valid' rows found in the training source -- "
            "training on all rows with no held-out set, so --early-stopping-rounds "
            "has nothing to watch and is ignored this run."
        )

    xgb_best_iteration = None
    if args.use_logistic_fallback:
        standardizer = fit_standardizer(fit_matrix)
        standardized_train = [standardizer.transform(row) for row in fit_matrix]
        model = LogisticRegressor(feature_count=len(feature_columns))
        model.fit(standardized_train, fit_labels, epochs=args.epochs, learning_rate=args.learning_rate, l2=args.l2)
        model_backend = "logistic_fallback"
    else:
        standardizer = None
        eval_metric_list = [metric.strip() for metric in args.eval_metric.split(",") if metric.strip()]
        model, xgb_params, xgb_best_iteration = train_xgboost_model(
            train_matrix=fit_matrix,
            train_labels=fit_labels,
            num_boost_round=args.num_boost_round,
            eta=args.eta,
            max_depth=args.max_depth,
            min_child_weight=args.min_child_weight,
            subsample=args.subsample,
            colsample_bytree=args.colsample_bytree,
            reg_lambda=args.reg_lambda,
            eval_metric=eval_metric_list,
            nthread=args.n_jobs,
            valid_matrix=valid_matrix,
            valid_labels=valid_labels,
            early_stopping_rounds=args.early_stopping_rounds,
        )
        args.xgb_model_out.parent.mkdir(parents=True, exist_ok=True)
        model.save_model(args.xgb_model_out)
        model_backend = "xgboost"
        if xgb_best_iteration is not None:
            print(
                f"Early stopping engaged: best iteration {xgb_best_iteration + 1} of "
                f"{args.num_boost_round} requested rounds. Predictions below use only "
                "trees up to that point."
            )

    fighters = load_fighter_state(args.fighters)
    matchups = load_matchups(args.matchups)
    export_columns = build_export_columns(feature_columns)

    built_rows = []
    prediction_rows = []
    skipped_matchups = []
    for matchup_row in matchups:
        try:
            fighter_a, a_match_type = resolve_fighter(matchup_row, fighters, "a")
            fighter_b, b_match_type = resolve_fighter(matchup_row, fighters, "b")
        except KeyError as exc:
            skipped_matchups.append(
                {
                    "fight_id_manual": matchup_row.get("fight_id_manual", ""),
                    "fighter_a": matchup_row.get("fighter_a", ""),
                    "fighter_b": matchup_row.get("fighter_b", ""),
                    "reason": str(exc),
                }
            )
            continue

        for side_label, fighter_name, match_type in (
            ("fighter_a", matchup_row.get("fighter_a", ""), a_match_type),
            ("fighter_b", matchup_row.get("fighter_b", ""), b_match_type),
        ):
            if match_type.startswith("fuzzy_name:"):
                matched_name = match_type.split(":", 1)[1]
                print(
                    f"WARNING: auto-matched {side_label} '{fighter_name}' -> "
                    f"'{matched_name}' in fighter_state.csv (fuzzy match, no exact hit). "
                    "Double-check this is the right fighter."
                )
        built_row = build_matchup_row(matchup_row, fighter_a, fighter_b, feature_columns, category_maps)
        feature_vector = matchup_to_feature_vector(built_row, feature_columns)
        if model_backend == "xgboost":
            feature_array = np.asarray([feature_vector], dtype=np.float32)
            dmatrix = xgb.DMatrix(feature_array)
            if xgb_best_iteration is not None:
                probability = float(model.predict(dmatrix, iteration_range=(0, xgb_best_iteration + 1))[0])
            else:
                probability = float(model.predict(dmatrix)[0])
        else:
            standardized_features = standardizer.transform(feature_vector)
            probability = model.predict_proba(standardized_features)
        built_rows.append({column: built_row.get(column, "") for column in export_columns})
        prediction_rows.append(build_prediction_output(matchup_row, built_row, probability, feature_columns))

    card_slug = slugify(matchups[0]["event_name"]) if matchups else "manual_card"
    model_rows_path = args.out_dir / f"{card_slug}_prediction_rows.csv"
    predictions_path = args.out_dir / f"{card_slug}_predictions.csv"
    model_summary_path = args.out_dir / f"{card_slug}_model_summary.json"

    write_csv(model_rows_path, built_rows, export_columns)
    write_csv(predictions_path, prediction_rows, prediction_fieldnames())
    save_model_summary(model_summary_path, standardizer, model, feature_columns)

    print(f"Saved prediction rows: {model_rows_path}")
    print(f"Saved fight predictions: {predictions_path}")
    print(f"Saved model summary: {model_summary_path}")
    if model_backend == "xgboost":
        print(f"Saved XGBoost model: {args.xgb_model_out}")
    print(f"Model features used: {len(feature_columns)}")
    print(f"Model backend: {model_backend}")
    print(f"Predicted fights: {len(prediction_rows)}")
    if skipped_matchups:
        skipped_path = args.out_dir / f"{card_slug}_skipped_fights.csv"
        write_csv(skipped_path, skipped_matchups, ["fight_id_manual", "fighter_a", "fighter_b", "reason"])
        print(f"Skipped fights (missing fighter rows): {len(skipped_matchups)} -- see {skipped_path}")
        for skipped in skipped_matchups:
            print(
                " - "
                f"{skipped['fight_id_manual'] or 'unknown_id'}: "
                f"{skipped['fighter_a']} vs {skipped['fighter_b']} "
                f"({skipped['reason']})"
            )
    else:
        print("No fights skipped -- every fighter matched fighter_state.csv.")


if __name__ == "__main__":
    main()