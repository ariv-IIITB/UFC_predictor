

import csv
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
HISTORY_CSV = BASE_DIR / "history_for_odds.csv"
ODDS_CSV = BASE_DIR / "ufc_final_best_odds.csv"
OUTPUT_DIR = BASE_DIR

# Config 
START_DATE = "2021-01-01"
END_DATE = "2025-09-06"
EDGE_THRESHOLD = 0.03  # only bet when model edge over implied prob >= this


def parse_float(value):
    try:
        if value is None:
            return 0.0
        text = str(value).strip()
        return float(text) if text != "" else 0.0
    except Exception:
        return 0.0


def parse_date(text):
    return datetime.strptime((text or "").strip(), "%Y-%m-%d")


def normalize_name(text):
    return " ".join((text or "").strip().lower().split())


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_history_with_prior_stats():

    rows = []
    if not HISTORY_CSV.exists():
        raise FileNotFoundError(f"Missing {HISTORY_CSV}")

    with HISTORY_CSV.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            r["fight_date"] = (r.get("fight_date") or "").strip()
            rows.append(r)

    # sort by date
    rows.sort(key=lambda r: parse_date(r.get("fight_date", "1970-01-01")))

    # running counts per fighter
    counts = {}
    processed = []

    for row in rows:
        a_name = normalize_name(row.get("a_fighter_name"))
        b_name = normalize_name(row.get("b_fighter_name"))

        a_stats = counts.get(a_name, {"wins": 0, "fights": 0})
        b_stats = counts.get(b_name, {"wins": 0, "fights": 0})

        # prior stats (before this fight)
        row["a_prior_fights"] = a_stats["fights"]
        row["b_prior_fights"] = b_stats["fights"]
        row["a_prior_wins"] = a_stats["wins"]
        row["b_prior_wins"] = b_stats["wins"]

        row["a_prior_win_rate"] = (a_stats["wins"] / a_stats["fights"]) if a_stats["fights"] > 0 else 0.0
        row["b_prior_win_rate"] = (b_stats["wins"] / b_stats["fights"]) if b_stats["fights"] > 0 else 0.0

        processed.append(row)

        # update with this fight result
        a_won = (row.get("label_a_win") or "").strip() == "1"
        a_stats["fights"] = a_stats.get("fights", 0) + 1
        b_stats["fights"] = b_stats.get("fights", 0) + 1
        if a_won:
            a_stats["wins"] = a_stats.get("wins", 0) + 1
        else:
            b_stats["wins"] = b_stats.get("wins", 0) + 1

        counts[a_name] = a_stats
        counts[b_name] = b_stats

    return processed


def load_odds():
    odds = {}
    if not ODDS_CSV.exists():
        raise FileNotFoundError(f"Missing {ODDS_CSV}")

    with ODDS_CSV.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            fid = (r.get("fight_id") or "").strip()
            if not fid:
                continue
            a_odds = parse_float(r.get("a_odds_decimal"))
            b_odds = parse_float(r.get("b_odds_decimal"))
            if a_odds <= 1.0 or b_odds <= 1.0:
                continue
            odds[fid] = {
                "fight_id": fid,
                "a_odds": a_odds,
                "b_odds": b_odds,
                "fight_date": (r.get("fight_date") or "").strip(),
                "event_name": r.get("event_name", ""),
                "a_fighter_name": r.get("a_fighter_name", ""),
                "b_fighter_name": r.get("b_fighter_name", ""),
                "source": r.get("source", ""),
                "region": r.get("region", ""),
            }
    return odds


def run_backtest():
    start_date = parse_date(START_DATE)
    end_date = parse_date(END_DATE)

    history = load_history_with_prior_stats()
    odds = load_odds()

    odds_used_rows = []
    backtest_rows = []

    skipped_debut_or_unknown = 0
    skipped_no_odds = 0
    matched = 0
    bets_placed = 0
    wins = 0
    losses = 0
    units_staked = 0.0
    profit_units = 0.0

    for row in history:
        fid = (row.get("fight_id") or "").strip()
        if fid == "":
            continue
        try:
            fd = parse_date(row.get("fight_date", "1970-01-01"))
        except Exception:
            continue
        if fd < start_date or fd > end_date:
            continue

        if fid not in odds:
            skipped_no_odds += 1
            continue

        a_prior = int(row.get("a_prior_fights", 0))
        b_prior = int(row.get("b_prior_fights", 0))
        if a_prior <= 0 or b_prior <= 0:
            skipped_debut_or_unknown += 1
            continue

        matched += 1
        o = odds[fid]

        p_a = float(row.get("a_prior_win_rate", 0.0))
        p_b = float(row.get("b_prior_win_rate", 0.0))
        if p_a == 0.0 and p_b == 0.0:
            p_a = 0.5
            p_b = 0.5

        if p_a >= p_b:
            predicted_side = "a"
            chosen_prob = p_a
            chosen_odds = o["a_odds"]
            predicted_winner = row.get("a_fighter_name") or o.get("a_fighter_name")
        else:
            predicted_side = "b"
            chosen_prob = p_b
            chosen_odds = o["b_odds"]
            predicted_winner = row.get("b_fighter_name") or o.get("b_fighter_name")

        implied_prob = 1.0 / chosen_odds
        edge = chosen_prob - implied_prob
        bet = 1 if edge >= EDGE_THRESHOLD else 0

        a_won = (row.get("label_a_win") or "").strip() == "1"
        actual_winner = row.get("a_fighter_name") if a_won else row.get("b_fighter_name")
        predicted_correct = (predicted_side == "a" and a_won) or (predicted_side == "b" and not a_won)

        fight_profit = 0.0
        if bet:
            bets_placed += 1
            units_staked += 1.0
            if predicted_correct:
                wins += 1
                fight_profit = chosen_odds - 1.0
            else:
                losses += 1
                fight_profit = -1.0
            profit_units += fight_profit

        odds_used_rows.append({
            "fight_id": fid,
            "fight_date": row.get("fight_date", ""),
            "a_fighter_name": row.get("a_fighter_name", ""),
            "b_fighter_name": row.get("b_fighter_name", ""),
            "a_odds": o["a_odds"],
            "b_odds": o["b_odds"],
            "chosen_side": predicted_side,
            "chosen_prob": round(chosen_prob, 4),
            "chosen_odds": round(chosen_odds, 4),
            "edge": round(edge, 4),
            "bet_placed": bet,
        })

        backtest_rows.append({
            "fight_id": fid,
            "fight_date": row.get("fight_date", ""),
            "a_fighter_name": row.get("a_fighter_name", ""),
            "b_fighter_name": row.get("b_fighter_name", ""),
            "a_prior_fights": a_prior,
            "b_prior_fights": b_prior,
            "a_prior_win_rate": round(float(row.get("a_prior_win_rate", 0.0)), 4),
            "b_prior_win_rate": round(float(row.get("b_prior_win_rate", 0.0)), 4),
            "predicted_side": predicted_side,
            "predicted_winner": predicted_winner,
            "actual_winner": actual_winner,
            "predicted_correct": 1 if predicted_correct else 0,
            "chosen_odds": round(chosen_odds, 4),
            "edge": round(edge, 4),
            "bet_placed": bet,
            "profit_units": round(fight_profit, 4),
        })

    roi = (profit_units / units_staked) if units_staked > 0 else 0.0
    win_rate_when_bet = (wins / bets_placed) if bets_placed > 0 else 0.0

    summary = {
        "start_date": START_DATE,
        "end_date": END_DATE,
        "edge_threshold": EDGE_THRESHOLD,
        "skipped_debut_or_unknown": skipped_debut_or_unknown,
        "skipped_no_odds": skipped_no_odds,
        "matched_fights": matched,
        "bets_placed": bets_placed,
        "wins": wins,
        "losses": losses,
        "units_staked": round(units_staked, 4),
        "profit_units": round(profit_units, 4),
        "roi": round(roi, 4),
        "win_rate_when_bet": round(win_rate_when_bet, 4),
        "note": "Simplified prior-win-rate model for readability and reproducibility.",
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "ufc_final_best_odds_used.csv", odds_used_rows, [
        "fight_id",
        "fight_date",
        "a_fighter_name",
        "b_fighter_name",
        "a_odds",
        "b_odds",
        "chosen_side",
        "chosen_prob",
        "chosen_odds",
        "edge",
        "bet_placed",
    ])

    write_csv(OUTPUT_DIR / "ufc_final_backtest.csv", backtest_rows, [
        "fight_id",
        "fight_date",
        "a_fighter_name",
        "b_fighter_name",
        "a_prior_fights",
        "b_prior_fights",
        "a_prior_win_rate",
        "b_prior_win_rate",
        "predicted_side",
        "predicted_winner",
        "actual_winner",
        "predicted_correct",
        "chosen_odds",
        "edge",
        "bet_placed",
        "profit_units",
    ])

    (OUTPUT_DIR / "ufc_final_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Saved summary: {OUTPUT_DIR / 'ufc_final_summary.json'}")
    print(f"Saved backtest: {OUTPUT_DIR / 'ufc_final_backtest.csv'}")
    print(f"Saved odds used: {OUTPUT_DIR / 'ufc_final_best_odds_used.csv'}")
    print(f"Bets placed: {summary['bets_placed']}")
    print(f"ROI: {summary['roi']}")


if __name__ == "__main__":
    run_backtest()
