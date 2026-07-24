import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import xgboost as xgb


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_HISTORY_CSV = BASE_DIR / "history_for_odds.csv"
DEFAULT_ODDS_CSV = BASE_DIR / "ufc_final_best_odds.csv"
DEFAULT_OUTPUT_DIR = BASE_DIR
START_DATE = "2021-01-01"
END_DATE = "2025-09-06"
EDGE_THRESHOLD = 0.03

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


@dataclass
class XGBConfig:
    num_boost_round: int = 65
    eta: float = 0.05
    max_depth: int = 5
    min_child_weight: float = 3.0
    subsample: float = 0.80
    colsample_bytree: float = 0.80
    reg_lambda: float = 1.0
    eval_metric: str = "logloss,auc"
    n_jobs: int = -1


XGB_CONFIG = XGBConfig()


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


def parse_date(text):
    return datetime.strptime((text or "").strip(), "%Y-%m-%d")


def normalize_name(text):
    return " ".join((text or "").strip().lower().split())


def row_value(row, key, default=""):
    value = row.get(key)
    if value is None:
        return default
    return value


def enrich_row(row):
    row["age_years_diff"] = parse_float(row.get("a_age_years")) - parse_float(row.get("b_age_years"))
    row["prior_fights_diff"] = parse_float(row.get("a_prior_fights")) - parse_float(row.get("b_prior_fights"))
    row["prior_win_rate_diff"] = parse_float(row.get("a_prior_win_rate")) - parse_float(row.get("b_prior_win_rate"))
    row["days_since_last_fight_diff"] = parse_float(row.get("a_days_since_last_fight")) - parse_float(row.get("b_days_since_last_fight"))
    row["reach_diff"] = parse_float(row.get("a_reach")) - parse_float(row.get("b_reach"))
    row["height_diff"] = parse_float(row.get("a_height")) - parse_float(row.get("b_height"))
    return row


def row_to_feature_vector(row):
    return [parse_float(row.get(column)) for column in MODEL_FEATURES]


def train_xgboost_model(train_matrix, train_labels, config):
    x_matrix = np.asarray(train_matrix, dtype=np.float32)
    y_vector = np.asarray(train_labels, dtype=np.float32)
    dtrain = xgb.DMatrix(x_matrix, label=y_vector)
    eval_metric_list = [metric.strip() for metric in config.eval_metric.split(",") if metric.strip()]
    params = {
        "objective": "binary:logistic",
        "eval_metric": eval_metric_list,
        "eta": config.eta,
        "max_depth": config.max_depth,
        "min_child_weight": config.min_child_weight,
        "subsample": config.subsample,
        "colsample_bytree": config.colsample_bytree,
        "lambda": config.reg_lambda,
        "tree_method": "hist",
        "seed": 42,
        "nthread": config.n_jobs,
    }
    return xgb.train(params, dtrain, num_boost_round=config.num_boost_round)


def load_labeled_history_rows(path):
    labeled_rows = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            label_text = (row.get("label_a_win") or "").strip()
            if label_text not in {"0", "1"}:
                continue
            enrich_row(row)
            labeled_rows.append((parse_date(row["fight_date"]), row_to_feature_vector(row), float(label_text)))
    labeled_rows.sort(key=lambda item: item[0])
    return labeled_rows


def orientation_key(row):
    a_id = row.get("a_fighter_id") or ""
    b_id = row.get("b_fighter_id") or ""
    a_name = normalize_name(row.get("a_fighter_name"))
    b_name = normalize_name(row.get("b_fighter_name"))
    return (a_id > b_id, a_name, b_name)


def load_canonical_fights(path):
    fights = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            fight_id = row["fight_id"]
            enrich_row(row)
            existing = fights.get(fight_id)
            if existing is None or orientation_key(row) < orientation_key(existing):
                fights[fight_id] = row
    return fights


def load_final_odds(path):
    odds_by_fight = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            fight_id = (row.get("fight_id") or "").strip()
            a_odds = parse_float(row.get("a_odds_decimal"), default=-1.0)
            b_odds = parse_float(row.get("b_odds_decimal"), default=-1.0)
            if not fight_id or a_odds <= 1.0 or b_odds <= 1.0:
                continue
            odds_by_fight[fight_id] = {
                "fight_id": fight_id,
                "fight_date": row.get("fight_date", ""),
                "event_name": row.get("event_name", ""),
                "a_fighter_name": row.get("a_fighter_name", ""),
                "b_fighter_name": row.get("b_fighter_name", ""),
                "region": row.get("region", ""),
                "source": row.get("source", ""),
                "adding_date": row.get("adding_date", ""),
                "selection": row.get("selection", ""),
                "a_odds_decimal": a_odds,
                "b_odds_decimal": b_odds,
                "match_type": row.get("match_type", ""),
            }
    return odds_by_fight


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    start_date = parse_date(START_DATE)
    end_date = parse_date(END_DATE)
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    labeled_history_rows = load_labeled_history_rows(DEFAULT_HISTORY_CSV)
    fights = load_canonical_fights(DEFAULT_HISTORY_CSV)
    odds_by_fight = load_final_odds(DEFAULT_ODDS_CSV)

    fights_by_date = defaultdict(list)
    for fight_id, row in fights.items():
        fight_date = parse_date(row["fight_date"])
        if start_date <= fight_date <= end_date:
            fights_by_date[fight_date].append((fight_id, row))

    selected_odds_rows = []
    backtest_rows = []
    summary = defaultdict(float)
    growing_train_matrix = []
    growing_train_labels = []
    train_cursor = 0

    for fight_date in sorted(fights_by_date):
        while train_cursor < len(labeled_history_rows) and labeled_history_rows[train_cursor][0] < fight_date:
            _, features, label = labeled_history_rows[train_cursor]
            growing_train_matrix.append(features)
            growing_train_labels.append(label)
            train_cursor += 1

        if not growing_train_matrix:
            summary["skipped_dates_no_training_data"] += 1
            continue

        model = train_xgboost_model(growing_train_matrix, growing_train_labels, XGB_CONFIG)
        summary["model_retrain_dates"] += 1
        summary["training_rows_latest"] = len(growing_train_matrix)

        for fight_id, row in sorted(fights_by_date[fight_date], key=lambda item: item[0]):
            summary["historical_fights_in_window"] += 1
            if parse_float(row.get("a_prior_fights")) <= 0 or parse_float(row.get("b_prior_fights")) <= 0:
                summary["skipped_debut_or_unknown"] += 1
                continue

            odds_row = odds_by_fight.get(fight_id)
            if not odds_row:
                summary["skipped_no_odds"] += 1
                continue

            a_odds = odds_row["a_odds_decimal"]
            b_odds = odds_row["b_odds_decimal"]
            summary["matched_fights"] += 1

            selected_odds_rows.append(
                {
                    "fight_id": fight_id,
                    "fight_date": row_value(row, "fight_date"),
                    "event_name": row_value(row, "event_name", odds_row.get("event_name", "")),
                    "a_fighter_name": row_value(row, "a_fighter_name", odds_row.get("a_fighter_name", "")),
                    "b_fighter_name": row_value(row, "b_fighter_name", odds_row.get("b_fighter_name", "")),
                    "region": odds_row["region"],
                    "source": odds_row["source"],
                    "adding_date": odds_row["adding_date"],
                    "selection": odds_row["selection"],
                    "a_odds_decimal": round(a_odds, 6),
                    "b_odds_decimal": round(b_odds, 6),
                    "match_type": odds_row["match_type"],
                }
            )

            feature_array = np.asarray([row_to_feature_vector(row)], dtype=np.float32)
            probability_a = float(model.predict(xgb.DMatrix(feature_array))[0])
            probability_b = 1.0 - probability_a
            predicted_side = "a" if probability_a >= probability_b else "b"
            predicted_winner = row_value(row, "a_fighter_name", odds_row.get("a_fighter_name", "")) if predicted_side == "a" else row_value(row, "b_fighter_name", odds_row.get("b_fighter_name", ""))
            chosen_probability = probability_a if predicted_side == "a" else probability_b
            chosen_odds = a_odds if predicted_side == "a" else b_odds
            implied_probability = 1.0 / chosen_odds
            edge = chosen_probability - implied_probability
            bet_placed = 1 if edge >= EDGE_THRESHOLD else 0

            label_a = (row.get("label_a_win") or "").strip()
            a_won = label_a == "1"
            predicted_correct = (predicted_side == "a" and a_won) or (predicted_side == "b" and not a_won)
            actual_winner = row_value(row, "a_fighter_name", odds_row.get("a_fighter_name", "")) if a_won else row_value(row, "b_fighter_name", odds_row.get("b_fighter_name", ""))

            profit_units = 0.0
            if bet_placed:
                summary["bets_placed"] += 1
                summary["units_staked"] += 1.0
                if predicted_correct:
                    profit_units = chosen_odds - 1.0
                    summary["wins"] += 1
                else:
                    profit_units = -1.0
                    summary["losses"] += 1
                summary["profit_units"] += profit_units

            backtest_rows.append(
                {
                    "fight_id": fight_id,
                    "fight_date": row_value(row, "fight_date"),
                    "event_name": row_value(row, "event_name", odds_row.get("event_name", "")),
                    "division_norm": row_value(row, "division_norm"),
                    "a_fighter_name": row_value(row, "a_fighter_name", odds_row.get("a_fighter_name", "")),
                    "b_fighter_name": row_value(row, "b_fighter_name", odds_row.get("b_fighter_name", "")),
                    "a_prior_fights": row_value(row, "a_prior_fights"),
                    "b_prior_fights": row_value(row, "b_prior_fights"),
                    "odds_source": odds_row["source"],
                    "odds_region": odds_row["region"],
                    "odds_added_at": odds_row["adding_date"],
                    "odds_selection": odds_row["selection"],
                    "odds_match_type": odds_row["match_type"],
                    "a_odds_decimal": round(a_odds, 6),
                    "b_odds_decimal": round(b_odds, 6),
                    "model_prob_a": round(probability_a, 6),
                    "model_prob_b": round(probability_b, 6),
                    "predicted_side": predicted_side,
                    "predicted_winner": predicted_winner,
                    "actual_winner": actual_winner,
                    "predicted_correct": "1" if predicted_correct else "0",
                    "chosen_odds_decimal": round(chosen_odds, 6),
                    "chosen_implied_probability": round(implied_probability, 6),
                    "chosen_model_probability": round(chosen_probability, 6),
                    "edge": round(edge, 6),
                    "bet_placed": str(bet_placed),
                    "profit_units": round(profit_units, 6),
                }
            )

    summary_payload = {
        "start_date": START_DATE,
        "end_date": END_DATE,
        "region": "us",
        "odds_selection": "latest",
        "edge_threshold": EDGE_THRESHOLD,
        "historical_fights_in_window": int(summary["historical_fights_in_window"]),
        "skipped_debut_or_unknown": int(summary["skipped_debut_or_unknown"]),
        "skipped_no_odds": int(summary["skipped_no_odds"]),
        "skipped_dates_no_training_data": int(summary["skipped_dates_no_training_data"]),
        "model_retrain_dates": int(summary["model_retrain_dates"]),
        "training_rows_latest": int(summary["training_rows_latest"]),
        "matched_fights": int(summary["matched_fights"]),
        "bets_placed": int(summary["bets_placed"]),
        "wins": int(summary["wins"]),
        "losses": int(summary["losses"]),
        "units_staked": round(summary["units_staked"], 6),
        "profit_units": round(summary["profit_units"], 6),
        "roi": round((summary["profit_units"] / summary["units_staked"]) if summary["units_staked"] else 0.0, 6),
        "win_rate_when_bet": round((summary["wins"] / summary["bets_placed"]) if summary["bets_placed"] else 0.0, 6),
        "note": "Final clean run using the fixed best-odds CSV and walk-forward XGBoost retraining.",
        "xgb_config": XGB_CONFIG.__dict__,
    }

    summary_out = DEFAULT_OUTPUT_DIR / "ufc_final_summary.json"
    backtest_out = DEFAULT_OUTPUT_DIR / "ufc_final_backtest.csv"
    odds_out = DEFAULT_OUTPUT_DIR / "ufc_final_best_odds_used.csv"

    write_csv(
        odds_out,
        selected_odds_rows,
        [
            "fight_id",
            "fight_date",
            "event_name",
            "a_fighter_name",
            "b_fighter_name",
            "region",
            "source",
            "adding_date",
            "selection",
            "a_odds_decimal",
            "b_odds_decimal",
            "match_type",
        ],
    )
    write_csv(
        backtest_out,
        backtest_rows,
        [
            "fight_id",
            "fight_date",
            "event_name",
            "division_norm",
            "a_fighter_name",
            "b_fighter_name",
            "a_prior_fights",
            "b_prior_fights",
            "odds_source",
            "odds_region",
            "odds_added_at",
            "odds_selection",
            "odds_match_type",
            "a_odds_decimal",
            "b_odds_decimal",
            "model_prob_a",
            "model_prob_b",
            "predicted_side",
            "predicted_winner",
            "actual_winner",
            "predicted_correct",
            "chosen_odds_decimal",
            "chosen_implied_probability",
            "chosen_model_probability",
            "edge",
            "bet_placed",
            "profit_units",
        ],
    )
    summary_out.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    print(f"Saved summary: {summary_out}")
    print(f"Saved backtest: {backtest_out}")
    print(f"Saved odds used: {odds_out}")
    print(f"Bets placed: {summary_payload['bets_placed']}")
    print(f"ROI: {summary_payload['roi']}")


if __name__ == "__main__":
    main()