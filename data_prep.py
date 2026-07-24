import pandas as pd
from sklearn.impute import SimpleImputer

data = pd.read_csv('final_data.csv')

data['fight_date'] = pd.to_datetime(data['fight_date'])

# splitting into training and testing data
cutoff_date = pd.to_datetime('2025-02-28')
train_data = data[data['fight_date'] <= cutoff_date]
test_data = data[data['fight_date'] > cutoff_date]

todrop = [ #constructed through hit and trial after seeing correlation and importances csv
    "a_avg_ctrl_seconds_for","a_avg_kd_against","a_avg_sig_landed_for","a_avg_sub_att_against",
    "a_finishing_durability","a_last3_avg_decision_loss_flag","a_last3_avg_finish_loss_flag",
    "a_last3_avg_finish_win_flag","a_last3_avg_scheduled_rounds","a_last3_avg_sig_landed_against",
    "a_last3_avg_sub_att_against","a_last3_avg_sub_att_for","a_last3_avg_td_landed_against",
    "a_last3_avg_win_flag","a_last5_avg_ctrl_seconds_against","a_last5_avg_ctrl_seconds_for",
    "a_last5_avg_decision_loss_flag","a_last5_avg_decision_win_flag","a_last5_avg_finish_loss_flag",
    "a_last5_avg_finish_win_flag","a_last5_avg_scheduled_rounds","a_last5_avg_sig_attempted_against",
    "a_last5_avg_sig_landed_against","a_last5_avg_sig_landed_for","a_last5_avg_sub_att_against",
    "a_last5_avg_sub_att_for","a_last5_avg_td_landed_against","a_last5_avg_td_landed_for",
    "a_last5_avg_win_flag","a_last_fight_fight_seconds","a_last_fight_loss_flag","a_last_fight_sub_att_for",
    "a_momentum","a_overall","a_prior_decision_losses","a_prior_finish_wins","a_prior_scheduled_rounds_total",
    "a_prior_wins","a_rw_avg_ctrl_seconds_against","a_rw_avg_ctrl_seconds_for","a_rw_avg_fight_seconds",
    "a_rw_avg_kd_against","a_rw_avg_kd_for","a_rw_avg_loss_flag","a_rw_avg_no_contest_flag",
    "a_rw_avg_sig_attempted_against","a_rw_avg_sig_attempted_for","a_rw_avg_sub_att_for",
    "a_rw_avg_td_landed_against","a_rw_avg_title_fight_flag","a_rw_avg_win_flag","a_striking_offense",
    "a_weight","avg_ctrl_seconds_for_diff","avg_sig_attempted_for_diff","avg_sub_att_for_diff",
    "avg_td_landed_for_diff","b_avg_ctrl_seconds_for","b_avg_kd_for","b_avg_sub_att_for",
    "b_finishing_durability","b_last3_avg_ctrl_seconds_for","b_last3_avg_decision_loss_flag",
    "b_last3_avg_kd_against","b_last3_avg_sig_attempted_against","b_last3_avg_sig_landed_against",
    "b_last3_avg_sub_att_against","b_last3_avg_sub_att_for","b_last3_avg_win_flag",
    "b_last5_avg_ctrl_seconds_against","b_last5_avg_ctrl_seconds_for","b_last5_avg_finish_win_flag",
    "b_last5_avg_kd_against","b_last5_avg_loss_flag","b_last5_avg_sig_landed_against",
    "b_last5_avg_sig_landed_for","b_last5_avg_sub_att_against","b_last5_avg_sub_att_for",
    "b_last5_avg_td_landed_against","b_last5_avg_td_landed_for","b_last5_avg_win_flag",
    "b_last_fight_loss_flag","b_last_fight_sig_attempted_against","b_overall","b_prior_decision_losses",
    "b_prior_finish_wins","b_prior_scheduled_rounds_total","b_prior_wins","b_rw_avg_ctrl_seconds_against",
    "b_rw_avg_decision_loss_flag","b_rw_avg_decision_win_flag","b_rw_avg_fight_seconds",
    "b_rw_avg_finish_loss_flag","b_rw_avg_kd_against","b_rw_avg_kd_for","b_rw_avg_loss_flag",
    "b_rw_avg_no_contest_flag","b_rw_avg_scheduled_rounds","b_rw_avg_sig_attempted_against",
    "b_rw_avg_sig_attempted_for","b_rw_avg_sub_att_against","b_rw_avg_td_landed_against",
    "b_rw_avg_title_fight_flag","b_rw_avg_win_flag","b_stance_code","b_weight",
    "last3_avg_ctrl_seconds_for_diff","last3_avg_loss_flag_diff","last3_avg_sig_attempted_against_diff",
    "last3_avg_sig_attempted_for_diff","last3_avg_sig_landed_against_diff","last3_avg_sub_att_for_diff",
    "last3_avg_title_fight_flag_diff","last5_avg_ctrl_seconds_for_diff","last5_avg_decision_loss_flag_diff",
    "last5_avg_decision_win_flag_diff","last5_avg_fight_seconds_diff","last5_avg_finish_loss_flag_diff",
    "last5_avg_finish_win_flag_diff","last5_avg_kd_for_diff","last5_avg_no_contest_flag_diff",
    "last5_avg_sig_attempted_against_diff","last5_avg_sig_attempted_for_diff","last5_avg_sig_landed_for_diff",
    "last5_avg_sub_att_against_diff","last5_avg_sub_att_for_diff","last5_avg_title_fight_flag_diff",
    "last_fight_finish_win_flag_diff","last_fight_sig_attempted_against_diff","last_fight_sub_att_against_diff",
    "last_fight_sub_att_for_diff","momentum_diff","prior_wins_diff","reach_sig_volume_interaction_diff",
    "rw_avg_ctrl_seconds_against_diff","rw_avg_kd_against_diff","rw_avg_loss_flag_diff",
    "rw_avg_scheduled_rounds_diff","rw_avg_sub_att_against_diff","rw_avg_td_landed_against_diff",
    "rw_avg_win_flag_diff","weight_diff",'label_a_win', 'fight_id', 'fight_date', 'split'
]

# 6. Create final X and y
y_train = train_data['label_a_win']
X_train = train_data.drop(columns=todrop).astype(float)

y_test = test_data['label_a_win']
X_test = test_data.drop(columns=todrop).astype(float)

print(f"X_train shape: {X_train.shape} | y_train shape: {y_train.shape}")
print(f"X_test shape:  {X_test.shape}  | y_test shape:  {y_test.shape}")
