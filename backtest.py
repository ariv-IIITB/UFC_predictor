import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import xgboost as xgb


BASE_DIR = Path(__file__).resolve().parent
HISTORY_CSV = BASE_DIR / "history_for_odds.csv"
ODDS_CSV = BASE_DIR / "ufc_final_best_odds.csv"
OUTPUT_DIR = BASE_DIR

START_DATE = "2021-01-01"
END_DATE = "2025-09-06"
EDGE_THRESHOLD = 0.03

NUM_BOOST_ROUND = 65
ETA = 0.05
MAX_DEPTH = 5
MIN_CHILD_WEIGHT = 3.0
SUBSAMPLE = 0.80
COLSAMPLE_BYTREE = 0.80
REG_LAMBDA = 1.0
N_JOBS = -1

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


def normalize_name(text):
    return " ".join((text or "").strip().lower().split())


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def add_diff_features(row):
    row["age_years_diff"] = parse_float(row.get("a_age_years")) - parse_float(row.get("b_age_years"))
    row["prior_fights_diff"] = parse_float(row.get("a_prior_fights")) - parse_float(row.get("b_prior_fights"))
    row["prior_win_rate_diff"] = parse_float(row.get("a_prior_win_rate")) - parse_float(row.get("b_prior_win_rate"))
    row["days_since_last_fight_diff"] = parse_float(row.get("a_days_since_last_fight")) - parse_float(row.get("b_days_since_last_fight"))
    row["reach_diff"] = parse_float(row.get("a_reach")) - parse_float(row.get("b_reach"))
    row["height_diff"] = parse_float(row.get("a_height")) - parse_float(row.get("b_height"))


def feature_vector(row):
    values = []
    for column in MODEL_FEATURES:
        values.append(parse_float(row.get(column)))
    return values


def train_model(train_matrix, train_labels):
    dtrain = xgb.DMatrix(np.asarray(train_matrix, dtype=np.float32), label=np.asarray(train_labels, dtype=np.float32))
    params = {
        "objective": "binary:logistic",
        "eval_metric": ["logloss", "auc"],
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
    return xgb.train(params, dtrain, num_boost_round=NUM_BOOST_ROUND)


def load_training_rows():
    rows = []
    with HISTORY_CSV.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            label_text = (row.get("label_a_win") or "").strip()
            if label_text not in {"0", "1"}:
                continue
            add_diff_features(row)
            rows.append((parse_date(row["fight_date"]), feature_vector(row), float(label_text)))
    rows.sort(key=lambda item: item[0])
    return rows


def canonical_key(row):
    a_id = row.get("a_fighter_id") or ""
    b_id = row.get("b_fighter_id") or ""
    a_name = normalize_name(row.get("a_fighter_name"))
    b_name = normalize_name(row.get("b_fighter_name"))
    return (a_id > b_id, a_name, b_name)


def load_fights():
    fights = {}
    with HISTORY_CSV.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            fight_id = row["fight_id"]
            add_diff_features(row)
            if fight_id not in fights or canonical_key(row) < canonical_key(fights[fight_id]):
                fights[fight_id] = row
    return fights


def load_odds():
    odds_by_fight = {}
    with ODDS_CSV.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            fight_id = (row.get("fight_id") or "").strip()
            a_odds = parse_float(row.get("a_odds_decimal"))
            b_odds = parse_float(row.get("b_odds_decimal"))

            if fight_id == "" or a_odds <= 1.0 or b_odds <= 1.0:
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
                "match_type": row.get("match_type", ""),
                "a_odds_decimal": a_odds,
                "b_odds_decimal": b_odds,
            }

    return odds_by_fight


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    start_date = parse_date(START_DATE)
    end_date = parse_date(END_DATE)

    training_rows = load_training_rows()
    fights = load_fights()
    odds_by_fight = load_odds()

    fights_by_date = {}
    for fight_id, row in fights.items():
        fight_date = parse_date(row["fight_date"])
        if fight_date < start_date or fight_date > end_date:
            continue
        fights_by_date.setdefault(fight_date, []).append((fight_id, row))

    odds_used_rows = []
    backtest_rows = []

    historical_fights_in_window = 0
    skipped_debut_or_unknown = 0
    skipped_no_odds = 0
    skipped_dates_no_training_data = 0
    model_retrain_dates = 0
    training_rows_latest = 0
    matched_fights = 0
    bets_placed = 0
    wins = 0
    losses = 0
    units_staked = 0.0
    profit_units = 0.0

    growing_train_matrix = []
    growing_train_labels = []
    training_index = 0

    for fight_date in sorted(fights_by_date):
        while training_index < len(training_rows) and training_rows[training_index][0] < fight_date:
            _, features, label = training_rows[training_index]
            growing_train_matrix.append(features)
            growing_train_labels.append(label)
            training_index += 1

        if not growing_train_matrix:
            skipped_dates_no_training_data += 1
            continue

        model = train_model(growing_train_matrix, growing_train_labels)
        model_retrain_dates += 1
        training_rows_latest = len(growing_train_matrix)

        for fight_id, row in sorted(fights_by_date[fight_date], key=lambda item: item[0]):
            historical_fights_in_window += 1

            if parse_float(row.get("a_prior_fights")) <= 0 or parse_float(row.get("b_prior_fights")) <= 0:
                skipped_debut_or_unknown += 1
                continue

            if fight_id not in odds_by_fight:
                skipped_no_odds += 1
                continue

            odds_row = odds_by_fight[fight_id]
            matched_fights += 1

            a_name = row.get("a_fighter_name", odds_row["a_fighter_name"])
            b_name = row.get("b_fighter_name", odds_row["b_fighter_name"])
            a_odds = odds_row["a_odds_decimal"]
            b_odds = odds_row["b_odds_decimal"]

            odds_used_rows.append(
                {
                    "fight_id": fight_id,
                    "fight_date": row.get("fight_date", ""),
                    "event_name": row.get("event_name", odds_row["event_name"]),
                    "a_fighter_name": a_name,
                    "b_fighter_name": b_name,
                    "region": odds_row["region"],
                    "source": odds_row["source"],
                    "adding_date": odds_row["adding_date"],
                    "selection": odds_row["selection"],
                    "a_odds_decimal": round(a_odds, 6),
                    "b_odds_decimal": round(b_odds, 6),
                    "match_type": odds_row["match_type"],
                }
            )

            dmatrix = xgb.DMatrix(np.asarray([feature_vector(row)], dtype=np.float32))
            probability_a = float(model.predict(dmatrix)[0])
            probability_b = 1.0 - probability_a

            if probability_a >= probability_b:
                predicted_side = "a"
                predicted_winner = a_name
                chosen_probability = probability_a
                chosen_odds = a_odds
            else:
                predicted_side = "b"
                predicted_winner = b_name
                chosen_probability = probability_b
                chosen_odds = b_odds

            implied_probability = 1.0 / chosen_odds
            edge = chosen_probability - implied_probability
            bet_placed = 1 if edge >= EDGE_THRESHOLD else 0

            a_won = (row.get("label_a_win") or "").strip() == "1"
            actual_winner = a_name if a_won else b_name
            predicted_correct = (predicted_side == "a" and a_won) or (predicted_side == "b" and not a_won)

            fight_profit = 0.0
            if bet_placed:
                bets_placed += 1
                units_staked += 1.0
                if predicted_correct:
                    wins += 1
                    fight_profit = chosen_odds - 1.0
                else:
                    losses += 1
                    fight_profit = -1.0
                profit_units += fight_profit

            backtest_rows.append(
                {
                    "fight_id": fight_id,
                    "fight_date": row.get("fight_date", ""),
                    "event_name": row.get("event_name", odds_row["event_name"]),
                    "division_norm": row.get("division_norm", ""),
                    "a_fighter_name": a_name,
                    "b_fighter_name": b_name,
                    "a_prior_fights": row.get("a_prior_fights", ""),
                    "b_prior_fights": row.get("b_prior_fights", ""),
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
                    "profit_units": round(fight_profit, 6),
                }
            )

    if units_staked == 0.0:
        roi = 0.0
    else:
        roi = profit_units / units_staked

    if bets_placed == 0:
        win_rate_when_bet = 0.0
    else:
        win_rate_when_bet = wins / bets_placed

    summary = {
        "start_date": START_DATE,
        "end_date": END_DATE,
        "region": "us",
        "odds_selection": "latest",
        "edge_threshold": EDGE_THRESHOLD,
        "historical_fights_in_window": historical_fights_in_window,
        "skipped_debut_or_unknown": skipped_debut_or_unknown,
        "skipped_no_odds": skipped_no_odds,
        "skipped_dates_no_training_data": skipped_dates_no_training_data,
        "model_retrain_dates": model_retrain_dates,
        "training_rows_latest": training_rows_latest,
        "matched_fights": matched_fights,
        "bets_placed": bets_placed,
        "wins": wins,
        "losses": losses,
        "units_staked": round(units_staked, 6),
        "profit_units": round(profit_units, 6),
        "roi": round(roi, 6),
        "win_rate_when_bet": round(win_rate_when_bet, 6),
        "note": "Final clean run using the fixed best-odds CSV and walk-forward XGBoost retraining.",
        "xgb_config": {
            "num_boost_round": NUM_BOOST_ROUND,
            "eta": ETA,
            "max_depth": MAX_DEPTH,
            "min_child_weight": MIN_CHILD_WEIGHT,
            "subsample": SUBSAMPLE,
            "colsample_bytree": COLSAMPLE_BYTREE,
            "reg_lambda": REG_LAMBDA,
            "eval_metric": "logloss,auc",
            "n_jobs": N_JOBS,
        },
    }

    summary_out = OUTPUT_DIR / "ufc_final_summary.json"
    backtest_out = OUTPUT_DIR / "ufc_final_backtest.csv"
    odds_out = OUTPUT_DIR / "ufc_final_best_odds_used.csv"

    write_csv(
        odds_out,
        odds_used_rows,
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

    summary_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Saved summary: {summary_out}")
    print(f"Saved backtest: {backtest_out}")
    print(f"Saved odds used: {odds_out}")
    print(f"Bets placed: {summary['bets_placed']}")
    print(f"ROI: {summary['roi']}")


if __name__ == "__main__":
    main()
