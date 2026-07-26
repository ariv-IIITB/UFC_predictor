export interface Fighter {
  fighter_id: string
  fighter_name: string
  last_fight_date: string | null
  division_norm: string | null
  division_group: string | null
  height: number | null
  weight: number | null
  reach: number | null
  stance: string | null
  age_years: number | null
  prior_fights: number | null
  prior_wins: number | null
  prior_losses: number | null
  prior_draws: number | null
  prior_no_contests: number | null
  prior_finish_wins: number | null
  prior_finish_losses: number | null
  prior_decision_wins: number | null
  prior_decision_losses: number | null
  prior_title_fights: number | null
  prior_win_rate: number | null
  avg_kd_for: number | null
  avg_kd_against: number | null
  avg_sig_landed_for: number | null
  avg_sig_landed_against: number | null
  avg_td_landed_for: number | null
  avg_td_landed_against: number | null
  avg_sub_att_for: number | null
  avg_sub_att_against: number | null
  avg_ctrl_seconds_for: number | null
  avg_ctrl_seconds_against: number | null
  pre_fight_elo: number | null
  striking_offense: number | null
  striking_defense: number | null
  grappling_offense: number | null
  grappling_defense: number | null
  finishing_durability: number | null
  momentum: number | null
  experience_big_fight: number | null
  physical: number | null
  overall: number | null
}

export interface FightHistory {
  fight_id: string
  fight_date: string
  event_name: string | null
  division_norm: string | null
  a_fighter_name: string
  b_fighter_name: string
  a_prior_fights: number | null
  b_prior_fights: number | null
  odds_source: string | null
  odds_region: string | null
  odds_added_at: string | null
  odds_selection: string | null
  odds_match_type: string | null
  a_odds_decimal: number | null
  b_odds_decimal: number | null
  model_prob_a: number | null
  model_prob_b: number | null
  predicted_side: string | null
  predicted_winner: string | null
  actual_winner: string | null
  predicted_correct: boolean | null
  chosen_odds_decimal: number | null
  chosen_implied_probability: number | null
  chosen_model_probability: number | null
  edge: number | null
  bet_placed: boolean | null
  profit_units: number | null
}

export interface Prediction {
  fight_id_manual: string
  event_name: string | null
  fight_date: string | null
  division_norm: string | null
  fighter_a: string
  fighter_b: string
  predicted_winner: string | null
  predicted_loser: string | null
  a_win_probability: number | null
  b_win_probability: number | null
  predicted_margin_pct: number | null
  confidence_tier: string | null
  actual_winner: string | null
  actual_method: string | null
  actual_round: number | null
  actual_time: string | null
  actual_notes: string | null
  prediction_correct: boolean | null
  model_feature_count: number | null
}

export interface ModelSummary {
  start_date: string
  end_date: string
  region: string
  odds_selection: string
  edge_threshold: number
  historical_fights_in_window: number
  skipped_debut_or_unknown: number
  skipped_no_odds: number
  skipped_dates_no_training_data: number
  model_retrain_dates: number
  training_rows_latest: number
  matched_fights: number
  bets_placed: number
  wins: number
  losses: number
  units_staked: number
  profit_units: number
  roi: number
  win_rate_when_bet: number
  note: string
}
