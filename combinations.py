from itertools import combinations
import pandas as pd

INPUT = "fighter_state.csv"
OUTPUT = "sample_manual_card.csv"

# ----------------------------
# Load fighter state
# ----------------------------
fighters = pd.read_csv(INPUT)

fighters["last_fight_date"] = pd.to_datetime(
    fighters["last_fight_date"],
    errors="coerce",
)

# ----------------------------
# Keep fighters active in last 3 years
# ----------------------------
today = pd.Timestamp.today().normalize()
cutoff = today - pd.DateOffset(years=3)

fighters = fighters[
    fighters["last_fight_date"] >= cutoff
].copy()

# ----------------------------
# Clean data
# ----------------------------
fighters = fighters.dropna(
    subset=[
        "fighter_id",
        "fighter_name",
        "division_norm",
    ]
)

fighters["fighter_name"] = fighters["fighter_name"].str.strip()
fighters["division_norm"] = (
    fighters["division_norm"]
    .str.strip()
    .str.lower()
)

# Keep latest row for each fighter
fighters = (
    fighters.sort_values("last_fight_date")
            .drop_duplicates("fighter_id", keep="last")
)

fight_date = today.strftime("%Y-%m-%d")

rows = []
fight_num = 1

# ----------------------------
# Round robin within divisions
# ----------------------------
for division, group in fighters.groupby("division_norm"):

    group = group.sort_values("fighter_name")

    fighter_list = group.to_dict("records")

    for fighter_a, fighter_b in combinations(fighter_list, 2):

        rows.append({
            "fight_id_manual": f"manual_{fight_num:06d}",
            "event_name": "Manual Card",
            "fight_date": fight_date,

            "fighter_a_id": fighter_a["fighter_id"],
            "fighter_b_id": fighter_b["fighter_id"],

            "fighter_a": fighter_a["fighter_name"],
            "fighter_b": fighter_b["fighter_name"],

            "division_norm": division,

            "scheduled_rounds": 3,
            "title_fight": 0,

            "actual_winner": "",
            "actual_method": "",
            "actual_round": "",
            "actual_time": "",
            "actual_notes": "",
        })

        fight_num += 1

manual_card = pd.DataFrame(rows)

manual_card.to_csv(OUTPUT, index=False)

print(f"Active fighters: {len(fighters):,}")
print(f"Generated matchups: {len(manual_card):,}")
print(f"Saved to: {OUTPUT}")

print("\nMatchups per division:")
for division, group in fighters.groupby("division_norm"):
    n = len(group)
    print(f"{division:20} {n:3d} fighters -> {n*(n-1)//2:,} matchups")