import csv
import math
from collections import defaultdict
from pathlib import Path
from statistics import NormalDist


SOURCE_FEATURE_CSV = Path(r"C:\Users\arivm\OneDrive\Documents\Codex\ufc_prefight_post2001_binary_mirrored.csv")
SOURCE_SPLIT_CSV = Path(r"C:\Users\arivm\OneDrive\Documents\Codex\ufc_prefight_post2001_binary_mirrored_xgboost.csv")
OUTPUT_CSV = Path(r"C:\Users\arivm\OneDrive\Documents\Codex\ufc_prefight_post2001_binary_mirrored_xgboost_with_overalls.csv")

ELO_BASE = 1500.0
ELO_K = 24.0
SHRINK_K = 5.0
PRECISION_BLEND = 0.70
NORMAL_DIST = NormalDist()

OVERALL_WEIGHTS = {
    "striking_offense": 0.18,
    "striking_defense": 0.14,
    "grappling_offense": 0.15,
    "grappling_defense": 0.13,
    "finishing_durability": 0.14,
    "momentum": 0.10,
    "experience_big_fight": 0.08,
    "physical": 0.08,
}

BUCKET_FEATURES = {
    "striking_offense": [
        ("rw_sig_lpm", "pos"),
        ("rw_sig_acc", "pos"),
        ("rw_kd_rate", "pos"),
        ("last3_sig_lpm", "pos"),
        ("last5_sig_lpm", "pos"),
        ("last_fight_sig_lpm", "pos"),
    ],
    "striking_defense": [
        ("rw_sig_absorb_lpm", "neg"),
        ("rw_sig_def_proxy", "pos"),
        ("rw_kd_absorb_rate", "neg"),
        ("last3_sig_absorb_lpm", "neg"),
        ("last3_kd_absorb_rate", "neg"),
    ],
    "grappling_offense": [
        ("rw_td_per15", "pos"),
        ("rw_sub_per15", "pos"),
        ("rw_ctrl_share", "pos"),
        ("last3_td_per15", "pos"),
        ("last3_sub_per15", "pos"),
        ("last3_ctrl_share", "pos"),
    ],
    "grappling_defense": [
        ("rw_td_allowed_per15", "neg"),
        ("rw_sub_allowed_per15", "neg"),
        ("rw_ctrl_allowed_per15", "neg"),
        ("last3_td_allowed_per15", "neg"),
        ("last3_sub_allowed_per15", "neg"),
        ("last3_ctrl_allowed_per15", "neg"),
    ],
    "finishing_durability": [
        ("finish_rate_rw", "pos"),
        ("finish_loss_rate_rw", "neg"),
        ("rw_kd_rate", "pos"),
        ("rw_kd_absorb_rate", "neg"),
        ("last3_finish_rate", "pos"),
        ("last3_finish_loss_rate", "neg"),
    ],
    "momentum": [
        ("last5_win_rate", "pos"),
        ("last3_win_rate", "pos"),
        ("rw_win_rate", "pos"),
        ("recent_finish_form", "pos"),
        ("last_fight_result", "pos"),
        ("activity_score", "direct"),
    ],
    "experience_big_fight": [
        ("log_prior_fights", "pos"),
        ("log_prior_scheduled_rounds_total", "pos"),
        ("log_prior_title_fights", "pos"),
        ("rw_avg_scheduled_rounds", "pos"),
        ("pre_fight_elo", "pos"),
    ],
    "physical": [
        ("reach", "pos"),
        ("height", "pos"),
        ("reach_height_gap", "pos"),
        ("age_prime_score", "direct"),
    ],
}

SHRINKABLE_METRICS = {
    "rw_sig_lpm",
    "rw_sig_acc",
    "rw_kd_rate",
    "last3_sig_lpm",
    "last5_sig_lpm",
    "last_fight_sig_lpm",
    "rw_sig_absorb_lpm",
    "rw_sig_def_proxy",
    "rw_kd_absorb_rate",
    "last3_sig_absorb_lpm",
    "last3_kd_absorb_rate",
    "rw_td_per15",
    "rw_sub_per15",
    "rw_ctrl_share",
    "last3_td_per15",
    "last3_sub_per15",
    "last3_ctrl_share",
    "rw_td_allowed_per15",
    "rw_sub_allowed_per15",
    "rw_ctrl_allowed_per15",
    "last3_td_allowed_per15",
    "last3_sub_allowed_per15",
    "last3_ctrl_allowed_per15",
    "finish_rate_rw",
    "finish_loss_rate_rw",
    "last3_finish_rate",
    "last3_finish_loss_rate",
    "last5_win_rate",
    "last3_win_rate",
    "rw_win_rate",
    "recent_finish_form",
    "last_fight_result",
    "rw_avg_scheduled_rounds",
}

METRICS_TO_STANDARDIZE = {
    feature_name
    for bucket_features in BUCKET_FEATURES.values()
    for feature_name, direction in bucket_features
    if direction != "direct"
}

INTERACTION_NAMES = (
    "reach_sig_volume_interaction_diff",
    "td_control_interaction_diff",
    "elo_momentum_interaction_diff",
)

SCORE_OUTPUT_COLUMNS = (
    "a_pre_fight_elo",
    "b_pre_fight_elo",
    "elo_diff",
    "a_striking_offense",
    "a_striking_defense",
    "a_grappling_offense",
    "a_grappling_defense",
    "a_finishing_durability",
    "a_momentum",
    "a_experience_big_fight",
    "a_physical",
    "a_overall",
    "b_striking_offense",
    "b_striking_defense",
    "b_grappling_offense",
    "b_grappling_defense",
    "b_finishing_durability",
    "b_momentum",
    "b_experience_big_fight",
    "b_physical",
    "b_overall",
    "striking_offense_diff",
    "striking_defense_diff",
    "grappling_offense_diff",
    "grappling_defense_diff",
    "finishing_durability_diff",
    "momentum_diff",
    "experience_big_fight_diff",
    "physical_diff",
    "overall_diff",
    "reach_sig_volume_interaction_diff",
    "td_control_interaction_diff",
    "elo_momentum_interaction_diff",
)


def parse_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    value = str(value).strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def safe_div(num, den, epsilon=1e-6):
    if num is None or den is None:
        return None
    den = den if abs(den) > epsilon else epsilon
    return num / den


def safe_rate(multiplier, numerator, denominator):
    numerator = parse_float(numerator)
    denominator = parse_float(denominator)
    if numerator is None or denominator is None:
        return None
    return safe_div(multiplier * numerator, denominator)


def average(values):
    clean = [value for value in values if value is not None and not math.isnan(value)]
    if not clean:
        return None
    return sum(clean) / len(clean)


def variance(values):
    clean = [value for value in values if value is not None and not math.isnan(value)]
    if len(clean) < 2:
        return None
    mean_value = sum(clean) / len(clean)
    return sum((value - mean_value) ** 2 for value in clean) / (len(clean) - 1)


def clip(value, low, high):
    return min(max(value, low), high)


def quantile(values, q):
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    position = q * (len(values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return values[lower]
    frac = position - lower
    return values[lower] * (1 - frac) + values[upper] * frac


def build_normalizer(values):
    clean = sorted(value for value in values if value is not None and not math.isnan(value))
    if len(clean) < 2:
        return None
    p05 = quantile(clean, 0.05)
    p95 = quantile(clean, 0.95)
    clipped = [clip(value, p05, p95) for value in clean]
    mean_value = sum(clipped) / len(clipped)
    std_value = math.sqrt(sum((value - mean_value) ** 2 for value in clipped) / len(clipped))
    if std_value < 1e-6:
        std_value = 1.0
    return {"p05": p05, "p95": p95, "mean": mean_value, "std": std_value}


def zscore_to_100(value, normalizer, direction):
    if value is None or normalizer is None:
        return 50.0
    clipped_value = clip(value, normalizer["p05"], normalizer["p95"])
    z_value = (clipped_value - normalizer["mean"]) / normalizer["std"]
    z_value = clip(z_value, -3.0, 3.0)
    if direction == "neg":
        z_value = -z_value
    return clip(NORMAL_DIST.cdf(z_value) * 100.0, 0.0, 100.0)


def weighted_average(components):
    available = [(score, weight) for score, weight in components if score is not None]
    if not available:
        return 50.0
    total_weight = sum(weight for _, weight in available)
    if total_weight <= 0:
        return 50.0
    return sum(score * weight for score, weight in available) / total_weight


def activity_score(days_since_last_fight):
    days = parse_float(days_since_last_fight)
    if days is None:
        return 50.0
    if days < 30:
        return 60.0
    if days < 60:
        return 60.0 + ((days - 30.0) / 30.0) * 40.0
    if days <= 300:
        return 100.0
    if days <= 500:
        return 100.0 - ((days - 300.0) / 200.0) * 60.0
    return max(20.0, 40.0 - ((days - 500.0) / 1000.0) * 20.0)


def age_prime_score(age_years):
    age = parse_float(age_years)
    if age is None:
        return 50.0
    return max(0.0, 100.0 - 8.0 * abs(age - 30.0))


def log1p_or_none(value):
    value = parse_float(value)
    if value is None or value < 0:
        return None
    return math.log1p(value)


def side_value(row, side, field):
    return parse_float(row.get(f"{side}_{field}"))


def load_split_map():
    split_map = {}
    with SOURCE_SPLIT_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            split_map[(row["fight_id"], row["label_a_win"])] = row["split"]
    return split_map


def load_xgboost_base_rows():
    base_rows = {}
    with SOURCE_SPLIT_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            base_rows[(row["fight_id"], row["label_a_win"])] = row
    return base_rows


def load_rows():
    split_map = load_split_map()
    with SOURCE_FEATURE_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["split"] = split_map.get((row["fight_id"], row["label_a_win"]), "")
    return rows


def attach_pre_fight_elo(rows):
    rows_by_fight = defaultdict(list)
    for row in rows:
        rows_by_fight[row["fight_id"]].append(row)

    ratings = defaultdict(lambda: ELO_BASE)
    ordered_fights = sorted(rows_by_fight.items(), key=lambda item: (item[1][0]["fight_date"], item[0]))

    for _, fight_rows in ordered_fights:
        for row in fight_rows:
            row["a_pre_fight_elo"] = ratings[row["a_fighter_id"]]
            row["b_pre_fight_elo"] = ratings[row["b_fighter_id"]]
            row["elo_diff"] = row["a_pre_fight_elo"] - row["b_pre_fight_elo"]

        canonical = next((row for row in fight_rows if row["label_a_win"] == "1"), fight_rows[0])
        a_id = canonical["a_fighter_id"]
        b_id = canonical["b_fighter_id"]
        actual_a = 1.0 if canonical["label_a_win"] == "1" else 0.0

        rating_a = ratings[a_id]
        rating_b = ratings[b_id]
        expected_a = 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))
        expected_b = 1.0 - expected_a

        ratings[a_id] = rating_a + ELO_K * (actual_a - expected_a)
        ratings[b_id] = rating_b + ELO_K * ((1.0 - actual_a) - expected_b)


def compute_side_derived(row, side):
    rw_fight_seconds = side_value(row, side, "rw_avg_fight_seconds")
    last3_fight_seconds = side_value(row, side, "last3_avg_fight_seconds")
    last5_fight_seconds = side_value(row, side, "last5_avg_fight_seconds")
    last_fight_seconds = side_value(row, side, "last_fight_fight_seconds")

    rw_ctrl_for = side_value(row, side, "rw_avg_ctrl_seconds_for")
    rw_ctrl_against = side_value(row, side, "rw_avg_ctrl_seconds_against")
    last3_ctrl_for = side_value(row, side, "last3_avg_ctrl_seconds_for")
    last3_ctrl_against = side_value(row, side, "last3_avg_ctrl_seconds_against")

    reach = side_value(row, side, "reach")
    height = side_value(row, side, "height")
    reach_height_gap = None if reach is None or height is None else reach - height

    derived = {
        "division": row["division_norm"],
        "prior_fights": max(side_value(row, side, "prior_fights") or 0.0, 0.0),
        "reach": reach,
        "height": height,
        "reach_height_gap": reach_height_gap,
        "rw_sig_lpm": safe_rate(60.0, side_value(row, side, "rw_avg_sig_landed_for"), rw_fight_seconds),
        "rw_sig_acc": safe_div(side_value(row, side, "rw_avg_sig_landed_for"), side_value(row, side, "rw_avg_sig_attempted_for")),
        "rw_kd_rate": safe_rate(60.0, side_value(row, side, "rw_avg_kd_for"), rw_fight_seconds),
        "last3_sig_lpm": safe_rate(60.0, side_value(row, side, "last3_avg_sig_landed_for"), last3_fight_seconds),
        "last5_sig_lpm": safe_rate(60.0, side_value(row, side, "last5_avg_sig_landed_for"), last5_fight_seconds),
        "last_fight_sig_lpm": safe_rate(60.0, side_value(row, side, "last_fight_sig_landed_for"), last_fight_seconds),
        "rw_sig_absorb_lpm": safe_rate(60.0, side_value(row, side, "rw_avg_sig_landed_against"), rw_fight_seconds),
        "rw_sig_def_proxy": 1.0 - safe_div(side_value(row, side, "rw_avg_sig_landed_against"), side_value(row, side, "rw_avg_sig_attempted_against")) if side_value(row, side, "rw_avg_sig_landed_against") is not None and side_value(row, side, "rw_avg_sig_attempted_against") is not None else None,
        "rw_kd_absorb_rate": safe_rate(60.0, side_value(row, side, "rw_avg_kd_against"), rw_fight_seconds),
        "last3_sig_absorb_lpm": safe_rate(60.0, side_value(row, side, "last3_avg_sig_landed_against"), last3_fight_seconds),
        "last3_kd_absorb_rate": safe_rate(60.0, side_value(row, side, "last3_avg_kd_against"), last3_fight_seconds),
        "rw_td_per15": safe_rate(900.0, side_value(row, side, "rw_avg_td_landed_for"), rw_fight_seconds),
        "rw_sub_per15": safe_rate(900.0, side_value(row, side, "rw_avg_sub_att_for"), rw_fight_seconds),
        "rw_ctrl_share": safe_div(rw_ctrl_for, (rw_ctrl_for or 0.0) + (rw_ctrl_against or 0.0)),
        "last3_td_per15": safe_rate(900.0, side_value(row, side, "last3_avg_td_landed_for"), last3_fight_seconds),
        "last3_sub_per15": safe_rate(900.0, side_value(row, side, "last3_avg_sub_att_for"), last3_fight_seconds),
        "last3_ctrl_share": safe_div(last3_ctrl_for, (last3_ctrl_for or 0.0) + (last3_ctrl_against or 0.0)),
        "rw_td_allowed_per15": safe_rate(900.0, side_value(row, side, "rw_avg_td_landed_against"), rw_fight_seconds),
        "rw_sub_allowed_per15": safe_rate(900.0, side_value(row, side, "rw_avg_sub_att_against"), rw_fight_seconds),
        "rw_ctrl_allowed_per15": safe_rate(900.0, rw_ctrl_against, rw_fight_seconds),
        "last3_td_allowed_per15": safe_rate(900.0, side_value(row, side, "last3_avg_td_landed_against"), last3_fight_seconds),
        "last3_sub_allowed_per15": safe_rate(900.0, side_value(row, side, "last3_avg_sub_att_against"), last3_fight_seconds),
        "last3_ctrl_allowed_per15": safe_rate(900.0, last3_ctrl_against, last3_fight_seconds),
        "finish_rate_rw": side_value(row, side, "rw_avg_finish_win_flag"),
        "finish_loss_rate_rw": side_value(row, side, "rw_avg_finish_loss_flag"),
        "last3_finish_rate": side_value(row, side, "last3_avg_finish_win_flag"),
        "last3_finish_loss_rate": side_value(row, side, "last3_avg_finish_loss_flag"),
        "last5_win_rate": side_value(row, side, "last5_avg_win_flag"),
        "last3_win_rate": side_value(row, side, "last3_avg_win_flag"),
        "rw_win_rate": side_value(row, side, "rw_avg_win_flag"),
        "recent_finish_form": average([side_value(row, side, "last3_avg_finish_win_flag"), side_value(row, side, "last5_avg_finish_win_flag")]),
        "last_fight_result": (side_value(row, side, "last_fight_win_flag") or 0.0) - (side_value(row, side, "last_fight_loss_flag") or 0.0),
        "activity_score": activity_score(row.get(f"{side}_days_since_last_fight")),
        "log_prior_fights": log1p_or_none(row.get(f"{side}_prior_fights")),
        "log_prior_scheduled_rounds_total": log1p_or_none(row.get(f"{side}_prior_scheduled_rounds_total")),
        "log_prior_title_fights": log1p_or_none(row.get(f"{side}_prior_title_fights")),
        "rw_avg_scheduled_rounds": side_value(row, side, "rw_avg_scheduled_rounds"),
        "age_prime_score": age_prime_score(row.get(f"{side}_age_years")),
        "pre_fight_elo": parse_float(row.get(f"{side}_pre_fight_elo")),
    }
    return derived


def attach_derived(rows):
    for row in rows:
        row["_derived"] = {
            "a": compute_side_derived(row, "a"),
            "b": compute_side_derived(row, "b"),
        }


def fit_shrinkage_means(rows):
    values = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row.get("split") != "train":
            continue
        for side in ("a", "b"):
            derived = row["_derived"][side]
            division = derived["division"]
            for metric in SHRINKABLE_METRICS:
                value = derived.get(metric)
                if value is not None and not math.isnan(value):
                    values[division][metric].append(value)
    means = defaultdict(dict)
    for division, metrics in values.items():
        for metric, metric_values in metrics.items():
            means[division][metric] = average(metric_values)
    return means


def apply_shrinkage(rows, shrink_means):
    for row in rows:
        row["_shrunk"] = {}
        for side in ("a", "b"):
            derived = row["_derived"][side]
            division = derived["division"]
            prior_fights = derived["prior_fights"]
            weight = prior_fights / (prior_fights + SHRINK_K) if prior_fights is not None else 0.0
            shrunk = {}
            for metric, value in derived.items():
                if metric not in SHRINKABLE_METRICS:
                    shrunk[metric] = value
                    continue
                division_mean = shrink_means.get(division, {}).get(metric)
                if value is None and division_mean is None:
                    shrunk[metric] = None
                elif value is None:
                    shrunk[metric] = division_mean
                elif division_mean is None:
                    shrunk[metric] = value
                else:
                    shrunk[metric] = weight * value + (1.0 - weight) * division_mean
            row["_shrunk"][side] = shrunk


def fit_normalizers(rows):
    values = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row.get("split") != "train":
            continue
        for side in ("a", "b"):
            shrunk = row["_shrunk"][side]
            division = shrunk["division"]
            for metric in METRICS_TO_STANDARDIZE:
                value = shrunk.get(metric)
                if value is not None and not math.isnan(value):
                    values[division][metric].append(value)
    normalizers = defaultdict(dict)
    for division, metrics in values.items():
        for metric, metric_values in metrics.items():
            normalizers[division][metric] = build_normalizer(metric_values)
    return normalizers


def metric_score(shrunk, metric_name, direction, normalizers):
    if direction == "direct":
        direct_value = shrunk.get(metric_name)
        if direct_value is None:
            return 50.0
        return clip(direct_value, 0.0, 100.0)

    division = shrunk["division"]
    normalizer = normalizers.get(division, {}).get(metric_name)
    if normalizer is None:
        fallback_values = []
        for division_normalizers in normalizers.values():
            if division_normalizers.get(metric_name):
                fallback_values.extend([division_normalizers[metric_name]["p05"], division_normalizers[metric_name]["p95"]])
        normalizer = build_normalizer(fallback_values) if fallback_values else None
    return zscore_to_100(shrunk.get(metric_name), normalizer, direction)


def fit_bucket_weights(rows, normalizers):
    bucket_weights = {}
    for bucket_name, features in BUCKET_FEATURES.items():
        variances = {}
        for metric_name, direction in features:
            scores = []
            for row in rows:
                if row.get("split") != "train":
                    continue
                for side in ("a", "b"):
                    scores.append(metric_score(row["_shrunk"][side], metric_name, direction, normalizers))
            variances[metric_name] = variance(scores)

        inverse_variance = {}
        for metric_name, _ in features:
            metric_variance = variances.get(metric_name)
            inverse_variance[metric_name] = 0.0 if metric_variance is None or metric_variance <= 1e-6 else 1.0 / metric_variance

        total_inverse_variance = sum(inverse_variance.values())
        equal_weight = 1.0 / len(features)
        blended = {}
        for metric_name, _ in features:
            inv_weight = inverse_variance[metric_name] / total_inverse_variance if total_inverse_variance > 0 else equal_weight
            blended[metric_name] = PRECISION_BLEND * inv_weight + (1.0 - PRECISION_BLEND) * equal_weight

        total_blended = sum(blended.values())
        bucket_weights[bucket_name] = {metric_name: weight / total_blended for metric_name, weight in blended.items()}
    return bucket_weights


def score_side(shrunk, normalizers, bucket_weights):
    bucket_scores = {}
    for bucket_name, features in BUCKET_FEATURES.items():
        components = []
        for metric_name, direction in features:
            score = metric_score(shrunk, metric_name, direction, normalizers)
            components.append((score, bucket_weights[bucket_name][metric_name]))
        bucket_scores[bucket_name] = weighted_average(components)
    bucket_scores["overall"] = sum(bucket_scores[name] * weight for name, weight in OVERALL_WEIGHTS.items())
    return bucket_scores


def add_interactions(output_row, a_shrunk, b_shrunk, a_scores, b_scores):
    rw_sig_lpm_diff = (a_shrunk.get("rw_sig_lpm") or 0.0) - (b_shrunk.get("rw_sig_lpm") or 0.0)
    reach_diff = (a_shrunk.get("reach") or 0.0) - (b_shrunk.get("reach") or 0.0)
    td_control_a = (a_shrunk.get("rw_td_per15") or 0.0) * (a_shrunk.get("rw_ctrl_share") or 0.0)
    td_control_b = (b_shrunk.get("rw_td_per15") or 0.0) * (b_shrunk.get("rw_ctrl_share") or 0.0)
    elo_diff = parse_float(output_row.get("elo_diff")) or 0.0
    momentum_diff = a_scores["momentum"] - b_scores["momentum"]

    output_row["reach_sig_volume_interaction_diff"] = round(reach_diff * rw_sig_lpm_diff, 4)
    output_row["td_control_interaction_diff"] = round(td_control_a - td_control_b, 4)
    output_row["elo_momentum_interaction_diff"] = round(elo_diff * (momentum_diff / 100.0), 4)


def build_output_rows(rows, normalizers, bucket_weights, base_rows):
    output_rows = []
    for row in rows:
        a_shrunk = row["_shrunk"]["a"]
        b_shrunk = row["_shrunk"]["b"]
        a_scores = score_side(a_shrunk, normalizers, bucket_weights)
        b_scores = score_side(b_shrunk, normalizers, bucket_weights)

        output_row = {}
        output_row["a_pre_fight_elo"] = round(parse_float(row["a_pre_fight_elo"]) or ELO_BASE, 4)
        output_row["b_pre_fight_elo"] = round(parse_float(row["b_pre_fight_elo"]) or ELO_BASE, 4)
        output_row["elo_diff"] = round(parse_float(row["elo_diff"]) or 0.0, 4)
        for bucket_name, score in a_scores.items():
            output_row[f"a_{bucket_name}"] = round(score, 4)
        for bucket_name, score in b_scores.items():
            output_row[f"b_{bucket_name}"] = round(score, 4)
        for bucket_name in OVERALL_WEIGHTS:
            output_row[f"{bucket_name}_diff"] = round(a_scores[bucket_name] - b_scores[bucket_name], 4)
        output_row["overall_diff"] = round(a_scores["overall"] - b_scores["overall"], 4)

        add_interactions(output_row, a_shrunk, b_shrunk, a_scores, b_scores)

        base_key = (row["fight_id"], row["label_a_win"])
        merged_row = dict(base_rows[base_key])
        for column in SCORE_OUTPUT_COLUMNS:
            merged_row[column] = output_row[column]
        output_rows.append(merged_row)
    return output_rows


def write_rows(rows):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    rows = load_rows()
    base_rows = load_xgboost_base_rows()
    attach_pre_fight_elo(rows)
    attach_derived(rows)
    shrink_means = fit_shrinkage_means(rows)
    apply_shrinkage(rows, shrink_means)
    normalizers = fit_normalizers(rows)
    bucket_weights = fit_bucket_weights(rows, normalizers)
    output_rows = build_output_rows(rows, normalizers, bucket_weights, base_rows)
    write_rows(output_rows)

    print(f"Saved: {OUTPUT_CSV}")
    print(f"Rows: {len(output_rows)}")
    print(f"Train rows: {sum(1 for row in output_rows if row['split'] == 'train')}")
    print(f"Valid rows: {sum(1 for row in output_rows if row['split'] == 'valid')}")
    print(f"Interaction columns: {', '.join(INTERACTION_NAMES)}")


if __name__ == "__main__":
    main()
