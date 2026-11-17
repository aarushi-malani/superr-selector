# SupeRR Selector S2 - Report data pack (auto-generated)

Every number below is produced by the scripts in `src/` from the supplied CSVs. Re-run `01 -> 05 -> 06 -> 07 -> 08` to reproduce.


## 1. Data used and exclusions

| item                       |   value |
|:---------------------------|--------:|
| matches_total              |     883 |
| matches_with_balls         |     867 |
| deliveries_total           |  200999 |
| super_over_deliveries      |      38 |
| broken_matches_excluded    |       2 |
| no_result_matches          |      41 |
| decided_matches_modelled   |     840 |
| deliveries_modelled        |  198637 |
| deliveries_in_rating_scope |  191664 |

| competition_group                    |   matches |   deliveries |
|:-------------------------------------|----------:|-------------:|
| T20I                                 |       449 |       104669 |
| IPL                                  |       361 |        86995 |
| Youth/A-team (excluded from ratings) |        30 |         6973 |

**Cleaning rules:** `extras1_runs` is an extras-type code (6 none, 2 wide, 3 leg-bye, 4 bye, 1 overstep no-ball, 5 other no-ball, 7 penalty); `extras_2_runs` = byes off a no-ball. Legal ball = not wide and not no-ball. Batter runs = `runs`; bowler runs = batter runs + wide/no-ball penalty (not byes/leg-byes); bowler wickets = Caught, Bowled, LBW, Stump, Hit Wicket (run outs, obstructing, retired out are team wickets only). Revised-overs columns are in balls. Super overs (innings 3-4) excluded. Season = year of match date.


## 2. Validation of reconstructed scores

| check_                                               |   matches |   share_exact |   share_within_5 |   median_abs_error |
|:-----------------------------------------------------|----------:|--------------:|-----------------:|-------------------:|
| Batting-first wins: our margin minus official margin |       402 |         0.622 |            0.97  |                  0 |
| Chasing wins: runs short of target (0 = reached)     |       421 |         0.834 |            0.983 |                  0 |

Before the strike-rotation fix (each extra counted as 1 run): batting-first margins exact in 31.6% of matches, within 2 runs in 57.7%; 73.4% of winning chases reached the reconstructed target.

Chase targets used in the analysis, by source (anchored to the official result):

| target_source       |   matches |
|:--------------------|----------:|
| official run margin |       402 |
| first-innings total |       365 |
| chase completed     |        71 |
| revised target      |        23 |
| tie (super over)    |         6 |

Manual check against ESPNcricinfo scorecards:

| match                            | innings           |   official |   reconstructed |   gap | note                       |
|:---------------------------------|:------------------|-----------:|----------------:|------:|:---------------------------|
| AUS v IND, 2nd T20I, 31 Oct 2025 | India (1st)       |        125 |             125 |     0 |                            |
|                                  | Australia (2nd)   |        126 |             119 |    -7 | Extras 10 after 4.1 overs  |
| AFG v SL, Asia Cup, 18 Sep 2025  | Afghanistan (1st) |        169 |             166 |    -3 | Extras 7 (lb 5, nb 1, w 1) |
|                                  | Sri Lanka (2nd)   |        171 |             162 |    -9 |                            |
| SL v ZIM, 1st T20I, 14 Jan 2024  | Zimbabwe (1st)    |        143 |             143 |     0 |                            |
|                                  | Sri Lanka (2nd)   |        144 |             143 |    -1 |                            |

**Cause of gaps:** the data records that a wide/bye/leg-bye occurred but not how many runs it yielded. We infer odd/even runs from strike rotation (did the batters change ends?) - wide: crossed = 2 runs, else 1; bye/leg-bye: crossed = 1, else 4. Boundary wides stay undetectable (e.g. NZ v PAK, 17 Apr 2023: NZ 163 official, 159 reconstructed). Because the most important deliveries are at the end of chases, the chase TARGET is anchored to the official result (e.g. NZ won by 4 and PAK made 159, so target = 164). Matches with gaps > 15 runs (missing deliveries) are excluded.


## 3. Win-probability model

|   innings | model   | train_seasons   | test_seasons   |   test_balls |   log_loss |   log_loss_no_skill |   brier |   brier_no_skill |
|----------:|:--------|:----------------|:---------------|-------------:|-----------:|--------------------:|--------:|-----------------:|
|         1 | gbm     | 2022-2024       | 2025-2026      |        41797 |      0.65  |               0.696 |   0.221 |            0.252 |
|         2 | gbm     | 2022-2024       | 2025-2026      |        37831 |      0.389 |               0.697 |   0.121 |            0.252 |

Lower is better; 'no-skill' = always predicting the base rate. Calibration: `figures/wp_calibration.png`.

Expected further runs ('resources', learned from completed 1st innings) by balls left x wickets left:

|   balls_left |     2 |     4 |     7 |    10 |
|-------------:|------:|------:|------:|------:|
|          120 | 120.1 | 123.1 | 129.9 | 176.9 |
|           60 |  64.7 |  70.3 |  93.3 | 104.9 |
|           30 |  31.8 |  39.8 |  55.5 |  59   |
|           12 |  13   |  20.3 |  26.5 |  30.9 |


## 4. Pressure definition: Leverage Index - evidence it separates pressure from ordinary play

| situation                                    |   balls |   mean_LI |   share_pressure_LI>=1.5 |
|:---------------------------------------------|--------:|----------:|-------------------------:|
| Batting collapse (3+ wkts in last 24 balls)  |   17264 |     0.915 |                    0.168 |
| Difficult chase (RRR >= 10)                  |   42972 |     1.037 |                    0.25  |
| Tight finish (2nd inn, <=36 balls, RRR 7-13) |    7634 |     2.81  |                    0.709 |
| Death overs (16-20), any                     |   44104 |     1.244 |                    0.268 |
| Knockout match                               |    7323 |     1.075 |                    0.227 |
| Comfortable chase (RRR < 6, 7+ wkts in hand) |    8616 |     0.261 |                    0.02  |
| 1st inn powerplay, no wicket down            |   16126 |     0.909 |                    0.081 |
| ALL BALLS                                    |  198637 |     1     |                    0.2   |

League-wide ball outcomes by leverage band (legal balls):

| band    |   balls |   dot_pct |   boundary_pct |   wicket_pct |   run_rate |
|:--------|--------:|----------:|---------------:|-------------:|-----------:|
| <0.5    |   64507 |     0.292 |          0.189 |        0.059 |      8.626 |
| 0.5-1   |   55015 |     0.311 |          0.183 |        0.053 |      8.342 |
| 1-1.5   |   32078 |     0.304 |          0.186 |        0.051 |      8.461 |
| 1.5-2.5 |   25666 |     0.289 |          0.189 |        0.055 |      8.616 |
| >2.5    |   12360 |     0.279 |          0.189 |        0.069 |      8.643 |

Highest-leverage deliveries in the data (sanity check - these are well-known last-ball finishes):

| match_date   | home_team             | away_team                   |   innings |   overid |   over_ball_num |   score_before |   wkts_left |   runs_needed |   balls_left | striker_name            | bowler_name         |   wp_before |    li |
|:-------------|:----------------------|:----------------------------|----------:|---------:|----------------:|---------------:|------------:|--------------:|-------------:|:------------------------|:--------------------|------------:|------:|
| 2023-04-30   | Chennai Super Kings   | Punjab Kings                |         2 |       20 |               6 |            198 |           4 |             3 |            1 | Sikandar Raza           | Matheesha Pathirana |        0.48 | 26.65 |
| 2026-09-22   | Japan                 | India                       |         2 |        5 |               7 |             29 |           7 |             4 |            1 | Alexander Patmore       | Axar Patel          |        0.06 | 24.34 |
| 2024-07-30   | Sri Lanka             | India                       |         2 |       20 |               6 |            135 |           2 |             3 |            1 | Chamindu Wickramasinghe | Suryakumar Yadav    |        0.05 | 24.25 |
| 2024-04-21   | Kolkata Knight Riders | Royal Challengers Bengaluru |         2 |       20 |               6 |            220 |           1 |             3 |            1 | Lockie Ferguson         | Mitchell Starc      |        0.07 | 24.17 |
| 2025-08-02   | West Indies           | Pakistan                    |         2 |       20 |               7 |            131 |           2 |             3 |            1 | Jason Holder            | Shaheen Afridi      |        0.09 | 24.14 |
| 2022-05-18   | Kolkata Knight Riders | Lucknow Super Giants        |         2 |       20 |               6 |            208 |           3 |             3 |            1 | Umesh Yadav             | Marcus Stoinis      |        0.17 | 24.12 |
| 2025-05-04   | Kolkata Knight Riders | Rajasthan Royals            |         2 |       20 |               6 |            204 |           3 |             3 |            1 | Shubham Dubey           | Vaibhav Arora       |        0.17 | 24.12 |
| 2025-09-26   | India                 | Sri Lanka                   |         2 |       20 |               6 |            200 |           5 |             3 |            1 | Dasun Shanaka           | Harshit Rana        |        0.13 | 24    |
| 2024-05-19   | Netherlands           | Ireland                     |         2 |       20 |               7 |            148 |           2 |             3 |            1 | Tim Pringle             | Mark Adair          |        0.11 | 23.94 |
| 2025-11-23   | Bangladesh A          | Pakistan A                  |         2 |       20 |               6 |            124 |           1 |             2 |            1 | Abdul Saqlain           | Ahmed Daniyal       |        0.03 | 23.47 |


### 5. Match pressure maps

- `figures/pressure_map_2024-05-02.png`: Sunrisers Hyderabad v Rajasthan Royals (2024-05-02) - Sunrisers Hyderabad Won by 1 runs

- `figures/pressure_map_2024-04-21.png`: Kolkata Knight Riders v Royal Challengers Bengaluru (2024-04-21) - Kolkata Knight Riders Won by 1 runs


### Why LI >= 1.5?

(1) Convention: in baseball sabermetrics, where the Leverage Index originates (Tom Tango), LI = 1 is average and values above roughly 1.5-2.0 are labelled high leverage; about 20% of plate appearances are high-leverage. (2) In our data LI >= 1.5 selects 20.0% of deliveries (LI >= 1.0: 36.9%, >= 2.0: 11.1%) - the same 'top ~1 in 5' share. (3) It separates the brief's own categories: see the table above (tight finishes and difficult chases mostly above 1.5, comfortable chases almost never). (4) Ball outcomes change above it (more wickets and boundaries, higher run rate). (5) It is not result-critical: thresholds 1.25 and 2.0 are reported in section 8.


### Pressure definition used for the rankings

A **pressure over** for a player is an over that STARTS with (a) Leverage Index >= 1.5 and (b) that player's side behind - batting side win probability <= 50% for batters; bowling side win probability <= 50% for bowlers. Judged at the start of the over so nothing the player does inside the over can switch pressure on or off. All balls of a pressure over are pressure balls (~10% of each role's balls). The v1 symmetric ball-level definition, a 40%/60% gate and LI thresholds 1.25/2.0 are reported as robustness checks (section 8).

Where pressure balls occur, by role:

| role    |   pressure balls |   share of all balls % |   1st innings % |   powerplay (ov 1-6) % |   middle (7-15) % |   death (16-20) % |   during collapse % |   knockout matches % |
|:--------|-----------------:|-----------------------:|----------------:|-----------------------:|------------------:|------------------:|--------------------:|---------------------:|
| batters |            18495 |                   10   |            27.9 |                   31   |              35.6 |              33.4 |                10.3 |                  3.3 |
| bowlers |            19342 |                   10.1 |            28   |                   36.4 |              38.1 |              25.5 |                 5.7 |                  3.7 |


## 6. Which measures reflect skill rather than luck? (split-half reliability)

| role   | metric                            |   split_half_r |   players |
|:-------|:----------------------------------|---------------:|----------:|
| bat    | rae_overall                       |          0.715 |        34 |
| bat    | wae_overall                       |          0.447 |        34 |
| bat    | rae_p_raw                         |          0.425 |        34 |
| bat    | wae_p_raw                         |          0.36  |        34 |
| bat    | PS                                |          0.579 |        34 |
| bat    | PS_raw_pressure_only              |          0.453 |        34 |
| bat    | rae_pressure_predicted_same_skill |          0.201 |       nan |
| bat    | wae_pressure_predicted_same_skill |          0.075 |       nan |
| bowl   | rae_overall                       |          0.54  |        47 |
| bowl   | wae_overall                       |          0.376 |        47 |
| bowl   | rae_p_raw                         |          0.145 |        47 |
| bowl   | wae_p_raw                         |          0.134 |        47 |
| bowl   | PS                                |          0.397 |        47 |
| bowl   | PS_raw_pressure_only              |          0.131 |        47 |
| bowl   | clutch_delta                      |          0.118 |        47 |
| bowl   | rae_pressure_predicted_same_skill |          0.106 |       nan |
| bowl   | wae_pressure_predicted_same_skill |          0.058 |       nan |

Split-half r = correlation of a player's metric in odd- vs even-numbered matches (min 50 pressure balls each). `*_predicted_same_skill` = the reliability expected if pressure performance were simply the player's usual skill measured on ~19% of the balls (Spearman-Brown). Observed pressure-only reliability is at or below that prediction -> no evidence of a large, separate 'clutch' skill; our score therefore anchors on usual situation-adjusted skill and adds the pressure-specific deviation only as far as the data supports.

| role   | component   |   k_overall | k_pressure_dev    |
|:-------|:------------|------------:|:------------------|
| bat    | rae         |         352 | inf (no signal)   |
| bat    | wae         |         624 | 557.0024210248041 |
| bowl   | rae         |         480 | inf (no signal)   |
| bowl   | wae         |        2617 | inf (no signal)   |

k_pressure_dev = balls of pressure data at which a player's pressure-specific deviation gets 50% weight; 'inf' = no repeatable pressure-specific signal detected.

k = number of balls at which a player's own record and the prior get equal weight.


## 7a. Top 10 Batters under pressure

|   rank | player_name          | teams                                     |   pressure_balls |   pressure_matches |    PS |   PS_p10 |   PS_p90 |   P_top10_pct |   PS_overall |   clutch_delta |   pressure_innings |   pressure_failures |   consistency_pct |   SR_all |   SR_pressure |   dismissal_pct_pressure |
|-------:|:---------------------|:------------------------------------------|-----------------:|-------------------:|------:|---------:|---------:|--------------:|-------------:|---------------:|-------------------:|--------------------:|------------------:|---------:|--------------:|-------------------------:|
|      1 | Vaibhav Sooryavanshi | Rajasthan Royals / India                  |               78 |                 10 | 35.98 |    24.29 |    47.25 |          97.8 |        33.73 |           2.25 |                  8 |                   2 |             75    |   219.72 |        229.49 |                     1.28 |
|      2 | Tim David            | Australia / Mumbai Indians                |              219 |                 24 | 28.6  |    19.55 |    36.19 |          94.2 |        26.52 |           2.09 |                 22 |                   9 |             59.09 |   177.65 |        204.57 |                     5.02 |
|      3 | Abhishek Sharma      | Sunrisers Hyderabad / India               |              167 |                 35 | 24.83 |    16.18 |    32.11 |          88.2 |        28.5  |          -3.67 |                 29 |                  16 |             44.83 |   186.29 |        163.25 |                     8.43 |
|      4 | Suryakumar Yadav     | India / Mumbai Indians                    |              208 |                 34 | 23.55 |    16.95 |    29.33 |          91   |        24.32 |          -0.77 |                 26 |                  12 |             53.85 |   166.46 |        154.07 |                     5.74 |
|      5 | Andre Russell        | Kolkata Knight Riders / West Indies       |              107 |                 16 | 22.99 |    13.16 |    33.37 |          77.2 |        20.4  |           2.59 |                 13 |                   7 |             46.15 |   170.73 |        180.37 |                     4.67 |
|      6 | Phil Salt            | England / Royal Challengers Bengaluru     |              129 |                 19 | 20.33 |    13.35 |    25.86 |          76.8 |        18.65 |           1.68 |                 16 |                   5 |             68.75 |   169.56 |        178.3  |                     3.1  |
|      7 | Heinrich Klaasen     | Sunrisers Hyderabad / South Africa        |              134 |                 21 | 18.09 |    12.08 |    24.26 |          60.2 |        17.61 |           0.48 |                 20 |                   5 |             75    |   166.76 |        179.85 |                     4.48 |
|      8 | Rinku Singh          | Kolkata Knight Riders / India             |              155 |                 22 | 14.31 |     7.43 |    20.68 |          30.2 |        13.18 |           1.12 |                 20 |                  10 |             50    |   152.66 |        135.9  |                     3.85 |
|      9 | Shashank Singh       | Punjab Kings / Sunrisers Hyderabad        |               70 |                 13 | 14.13 |     3.81 |    22.7  |          32.2 |        11.17 |           2.96 |                 11 |                   4 |             63.64 |   161.61 |        170    |                     1.43 |
|     10 | Romario Shepherd     | West Indies / Royal Challengers Bengaluru |               90 |                 19 | 13.59 |     3.8  |    22.32 |          31.8 |        13.99 |          -0.39 |                 18 |                   8 |             55.56 |   154.15 |        159.78 |                     8.7  |

PS = runs ADDED vs an average batter in the identical situations per 100 pressure balls (wickets converted to runs at their pressure-situation worth); PS_p10-p90 = bootstrap interval; P_top10 = % of 500 match re-samples in which the player is top 10; PS_overall = usual level (all balls); clutch_delta = shrunk pressure-specific adjustment; consistency = % of pressure innings (>= 3 pressure balls or dismissed/wicket on one) with positive value.

**Observed pressure-only record** (secondary, descriptive: pressure balls only, no shrinkage toward usual level; split-half reliability is low, so treat as a record of what happened, not a skill estimate):

| player_name          |   pressure_balls |   pressure_innings |   pressure_successes |   pressure_failures |   PS_raw_pressure_only |    PS |   main_rank |
|:---------------------|-----------------:|-------------------:|---------------------:|--------------------:|-----------------------:|------:|------------:|
| Vaibhav Sooryavanshi |               78 |                  8 |                    6 |                   2 |                  80.44 | 35.98 |           1 |
| Mohammad Nabi        |               69 |                  8 |                    7 |                   1 |                  67.74 |  4.32 |          46 |
| George Dockrell      |               75 |                  9 |                    6 |                   3 |                  56.94 |  5.78 |          38 |
| Tim David            |              219 |                 22 |                   13 |                   9 |                  55.64 | 28.6  |           2 |
| Matthew Wade         |               67 |                  8 |                    6 |                   2 |                  52.54 |  8.35 |          28 |
| Reeza Hendricks      |              105 |                  9 |                    7 |                   2 |                  49.06 | 13.05 |          12 |
| Shashank Singh       |               70 |                 11 |                    7 |                   4 |                  44.59 | 14.13 |           9 |
| Curtis Campher       |               63 |                 10 |                    7 |                   3 |                  43.59 |  1.27 |          63 |
| Shreyas Iyer         |              167 |                 19 |                   12 |                   7 |                  43.19 | 11.65 |          14 |
| Andre Russell        |              107 |                 13 |                    6 |                   7 |                  42.61 | 22.99 |           5 |

**Above the diagonal but not in the top 10 - why** (diagonal y = x in `figures/quadrant_bat.png` means 'pressure record equals usual level'; top-10 cut-off = PS of #10 = 13.59). See also `figures/selection_bat.png`:

|   rank | player_name          |   pressure_balls |   PS_overall |   PS_raw_pressure_only |   clutch_delta |    PS | reason_not_in_top10                                                                                                                                                      |
|-------:|:---------------------|-----------------:|-------------:|-----------------------:|---------------:|------:|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|     12 | Reeza Hendricks      |              105 |        10.28 |                  49.06 |           2.77 | 13.05 | Raw gap +38.8 on 105 pressure balls; reliability supports +2.8, so PS = 10.3 +2.8 = 13.0 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value) |
|     13 | Rashid Khan          |               94 |         9.87 |                  35.4  |           2.04 | 11.91 | Raw gap +25.5 on 94 pressure balls; reliability supports +2.0, so PS = 9.9 +2.0 = 11.9 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)   |
|     14 | Shreyas Iyer         |              167 |         9.68 |                  43.19 |           1.97 | 11.65 | Raw gap +33.5 on 167 pressure balls; reliability supports +2.0, so PS = 9.7 +2.0 = 11.6 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)  |
|     16 | Namboori Tilak Varma |              249 |        10.02 |                  16.39 |           0.85 | 10.87 | Raw gap +6.4 on 249 pressure balls; reliability supports +0.9, so PS = 10.0 +0.9 = 10.9 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)  |
|     18 | Dinesh Karthik       |               93 |         9.5  |                  23.71 |           1.23 | 10.73 | Raw gap +14.2 on 93 pressure balls; reliability supports +1.2, so PS = 9.5 +1.2 = 10.7 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)   |
|     21 | Yashasvi Jaiswal     |               98 |         9.74 |                  33.61 |           0.06 |  9.8  | Raw gap +23.9 on 98 pressure balls; reliability supports +0.1, so PS = 9.7 +0.1 = 9.8 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)    |
|     23 | Tristan Stubbs       |              119 |         7.54 |                  18.32 |           1.91 |  9.46 | Raw gap +10.8 on 119 pressure balls; reliability supports +1.9, so PS = 7.5 +1.9 = 9.5 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)   |
|     24 | Marcus Stoinis       |              155 |         7.96 |                  32.36 |           1.47 |  9.43 | Raw gap +24.4 on 155 pressure balls; reliability supports +1.5, so PS = 8.0 +1.5 = 9.4 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)   |
|     25 | David Miller         |              134 |         8.17 |                  19.04 |           0.73 |  8.9  | Raw gap +10.9 on 134 pressure balls; reliability supports +0.7, so PS = 8.2 +0.7 = 8.9 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)   |
|     28 | Matthew Wade         |               67 |         6.56 |                  52.54 |           1.79 |  8.35 | Raw gap +46.0 on 67 pressure balls; reliability supports +1.8, so PS = 6.6 +1.8 = 8.3 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)    |
|     31 | Dewald Brevis        |               85 |         7.48 |                  13.04 |           0.49 |  7.97 | Raw gap +5.6 on 85 pressure balls; reliability supports +0.5, so PS = 7.5 +0.5 = 8.0 < cut-off 13.6 (usual level too low even with the full raw gap)                     |
|     32 | David Warner         |              117 |         7.78 |                  16.79 |          -0.01 |  7.76 | Raw gap +9.0 on 117 pressure balls; reliability supports -0.0, so PS = 7.8 -0.0 = 7.8 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)    |
|     33 | Virat Kohli          |              204 |         4.3  |                  26    |           3.07 |  7.37 | Raw gap +21.7 on 204 pressure balls; reliability supports +3.1, so PS = 4.3 +3.1 = 7.4 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)   |
|     34 | Rovman Powell        |              144 |         9.66 |                  26.74 |          -2.43 |  7.23 | Raw gap +17.1 on 144 pressure balls; reliability supports -2.4, so PS = 9.7 -2.4 = 7.2 < cut-off 13.6 (would enter only if the whole raw gap were taken at face value)   |
|     37 | Asif Khan            |               62 |         5.26 |                   8.51 |           0.58 |  5.84 | Raw gap +3.2 on 62 pressure balls; reliability supports +0.6, so PS = 5.3 +0.6 = 5.8 < cut-off 13.6 (usual level too low even with the full raw gap)                     |

Positions 11-20 (for discussion of close calls):

|   rank | player_name          |    PS |   PS_p10 |   PS_p90 |   P_top10_pct |
|-------:|:---------------------|------:|---------:|---------:|--------------:|
|     11 | Nicholas Pooran      | 13.32 |     5.11 |    20.3  |          24.6 |
|     12 | Reeza Hendricks      | 13.05 |     4.95 |    20.8  |          22.4 |
|     13 | Rashid Khan          | 11.91 |     0.55 |    22.2  |          25   |
|     14 | Shreyas Iyer         | 11.65 |     4.32 |    19.44 |          17.2 |
|     15 | Rajat Patidar        | 11.01 |     1.7  |    19.51 |          20   |
|     16 | Namboori Tilak Varma | 10.87 |     5.32 |    16.54 |           9.6 |
|     17 | Harry Brook          | 10.79 |     1.1  |    20.16 |          20.6 |
|     18 | Dinesh Karthik       | 10.73 |    -0.44 |    19.1  |          17.8 |
|     19 | Mitchell Marsh       | 10.41 |     3.02 |    16.86 |           9.2 |
|     20 | Rilee Rossouw        |  9.94 |     0.9  |    17.42 |          12.2 |

**Evidence cards - each top-10 batter's three most valuable pressure innings** (runs = scored on pressure balls; wickets = dismissals):

|   rank | player               | date       | match                                             |   innings | entry_state                 | last_pressure_ball_state    |   pressure_balls |   runs |   wickets |   value_runs_above_avg |
|-------:|:---------------------|:-----------|:--------------------------------------------------|----------:|:----------------------------|:----------------------------|-----------------:|-------:|----------:|-----------------------:|
|      1 | Vaibhav Sooryavanshi | 2026-04-10 | Rajasthan Royals v Royal Challengers Bengaluru    |         2 | 197 off 118, 10 wkts left   | 148 off 97, 9 wkts left     |               13 |     41 |         0 |                   23   |
|      1 | Vaibhav Sooryavanshi | 2026-05-29 | Gujarat Titans v Rajasthan Royals                 |         1 | 66/2 after 6 ov (1st inn)   | 150/5 after 15 ov (1st inn) |               12 |     26 |         0 |                   11.4 |
|      1 | Vaibhav Sooryavanshi | 2026-04-28 | Punjab Kings v Rajasthan Royals                   |         2 | 207 off 113, 10 wkts left   | 180 off 103, 10 wkts left   |                9 |     23 |         0 |                    8.9 |
|      2 | Tim David            | 2023-04-30 | Mumbai Indians v Rajasthan Royals                 |         2 | 59 off 26, 6 wkts left      | 3 off 4, 6 wkts left        |               14 |     45 |         0 |                   24.6 |
|      2 | Tim David            | 2022-05-17 | Mumbai Indians v Sunrisers Hyderabad              |         2 | 71 off 35, 7 wkts left      | 19 off 13, 5 wkts left      |               17 |     46 |         1 |                   20.1 |
|      2 | Tim David            | 2025-08-12 | Australia v South Africa                          |         2 | 190 off 99, 8 wkts left     | 115 off 63, 7 wkts left     |               19 |     47 |         1 |                   18.4 |
|      3 | Abhishek Sharma      | 2026-05-22 | Sunrisers Hyderabad v Royal Challengers Bengaluru |         1 | 21/0 after 2 ov (1st inn)   | 76/1 after 6 ov (1st inn)   |                7 |     23 |         0 |                   12.6 |
|      3 | Abhishek Sharma      | 2025-05-19 | Lucknow Super Giants v Sunrisers Hyderabad        |         2 | 183 off 108, 9 wkts left    | 156 off 99, 9 wkts left     |                7 |     22 |         0 |                   12.2 |
|      3 | Abhishek Sharma      | 2024-05-19 | Sunrisers Hyderabad v Punjab Kings                |         2 | 186 off 108, 9 wkts left    | 128 off 85, 8 wkts left     |               10 |     23 |         0 |                    9.5 |
|      4 | Suryakumar Yadav     | 2025-05-21 | Mumbai Indians v Delhi Capitals                   |         1 | 48/2 after 5 ov (1st inn)   | 179/5 after 19 ov (1st inn) |               11 |     34 |         0 |                   18.7 |
|      4 | Suryakumar Yadav     | 2023-04-22 | Mumbai Indians v Punjab Kings                     |         2 | 131 off 63, 8 wkts left     | 33 off 15, 7 wkts left      |               18 |     40 |         1 |                   10.6 |
|      4 | Suryakumar Yadav     | 2023-04-30 | Mumbai Indians v Rajasthan Royals                 |         2 | 107 off 48, 7 wkts left     | 59 off 27, 7 wkts left      |               11 |     26 |         1 |                    6   |
|      5 | Andre Russell        | 2022-04-23 | Kolkata Knight Riders v Gujarat Titans            |         2 | 78 off 47, 5 wkts left      | 12 off 5, 3 wkts left       |               17 |     40 |         1 |                   20   |
|      5 | Andre Russell        | 2024-03-23 | Kolkata Knight Riders v Sunrisers Hyderabad       |         1 | 123/6 after 15 ov (1st inn) | 169/6 after 17 ov (1st inn) |                9 |     26 |         0 |                   16.2 |
|      5 | Andre Russell        | 2023-05-08 | Kolkata Knight Riders v Punjab Kings              |         2 | 64 off 36, 7 wkts left      | 7 off 7, 6 wkts left        |               17 |     38 |         0 |                   15.8 |
|      6 | Phil Salt            | 2024-11-10 | West Indies v England                             |         2 | 176 off 113, 10 wkts left   | 135 off 97, 10 wkts left    |               12 |     35 |         0 |                   20.3 |
|      6 | Phil Salt            | 2025-09-17 | Ireland v England                                 |         2 | 193 off 120, 10 wkts left   | 169 off 109, 10 wkts left   |               10 |     24 |         0 |                   13.3 |
|      6 | Phil Salt            | 2023-12-16 | West Indies v England                             |         2 | 46 off 17, 8 wkts left      | 19 off 8, 7 wkts left       |                8 |     22 |         0 |                   10.9 |
|      7 | Heinrich Klaasen     | 2023-04-29 | Delhi Capitals v Sunrisers Hyderabad              |         1 | 83/4 after 9 ov (1st inn)   | 170/6 after 17 ov (1st inn) |                9 |     22 |         0 |                   11.8 |
|      7 | Heinrich Klaasen     | 2023-04-18 | Sunrisers Hyderabad v Mumbai Indians              |         2 | 117 off 65, 6 wkts left     | 62 off 37, 6 wkts left      |               12 |     30 |         1 |                   11.7 |
|      7 | Heinrich Klaasen     | 2024-05-02 | Sunrisers Hyderabad v Rajasthan Royals            |         1 | 132/3 after 15 ov (1st inn) | 160/3 after 16 ov (1st inn) |                6 |     16 |         0 |                    7.4 |
|      8 | Rinku Singh          | 2022-05-18 | Kolkata Knight Riders v Lucknow Super Giants      |         2 | 31 off 10, 4 wkts left      | 3 off 2, 4 wkts left        |                8 |     25 |         1 |                    9   |
|      8 | Rinku Singh          | 2026-04-19 | Kolkata Knight Riders v Rajasthan Royals          |         2 | 103 off 75, 6 wkts left     | 12 off 8, 4 wkts left       |               22 |     28 |         0 |                    6.9 |
|      8 | Rinku Singh          | 2023-05-04 | Sunrisers Hyderabad v Kolkata Knight Riders       |         1 | 45/3 after 5 ov (1st inn)   | 167/7 after 18 ov (1st inn) |               11 |     17 |         0 |                    6.4 |
|      9 | Shashank Singh       | 2022-04-27 | Gujarat Titans v Sunrisers Hyderabad              |         1 | 154/6 after 18 ov (1st inn) | 181/6 after 19 ov (1st inn) |                6 |     25 |         0 |                   18.5 |
|      9 | Shashank Singh       | 2024-04-26 | Kolkata Knight Riders v Punjab Kings              |         2 | 66 off 36, 8 wkts left      | 40 off 19, 8 wkts left      |               13 |     26 |         0 |                    6.5 |
|      9 | Shashank Singh       | 2024-04-04 | Gujarat Titans v Punjab Kings                     |         2 | 43 off 20, 4 wkts left      | 11 off 7, 4 wkts left       |                4 |      9 |         0 |                    4.2 |
|     10 | Romario Shepherd     | 2025-05-03 | Royal Challengers Bengaluru v Chennai Super Kings |         1 | 159/5 after 18 ov (1st inn) | 188/5 after 18 ov (1st inn) |                7 |     32 |         0 |                   21.8 |
|     10 | Romario Shepherd     | 2026-10-09 | India v West Indies                               |         2 | 26 off 17, 6 wkts left      | 14 off 13, 6 wkts left      |                4 |     15 |         0 |                    7.3 |
|     10 | Romario Shepherd     | 2022-05-22 | Sunrisers Hyderabad v Punjab Kings                |         1 | 131/5 after 18 ov (1st inn) | 148/5 after 19 ov (1st inn) |                5 |     13 |         0 |                    6.5 |


## 7b. Top 10 Bowlers under pressure

|   rank | player_name         | teams                            |   pressure_balls |   pressure_matches |    PS |   PS_p10 |   PS_p90 |   P_top10_pct |   PS_overall |   clutch_delta |   pressure_innings |   pressure_failures |   consistency_pct |   econ_all |   econ_pressure |   wkts_pressure |
|-------:|:--------------------|:---------------------------------|-----------------:|-------------------:|------:|---------:|---------:|--------------:|-------------:|---------------:|-------------------:|--------------------:|------------------:|-----------:|----------------:|----------------:|
|      1 | Jasprit Bumrah      | Mumbai Indians / India           |              159 |                 16 | 22.35 |    17.05 |    28.4  |          99.2 |        22.35 |              0 |                 16 |                   8 |             50    |       7.22 |            7.43 |               6 |
|      2 | Sunil Narine        | Kolkata Knight Riders            |              120 |                 16 | 20.32 |    15.59 |    25.2  |          98.2 |        20.32 |              0 |                 16 |                   4 |             75    |       6.8  |            6.1  |               4 |
|      3 | Matheesha Pathirana | Chennai Super Kings / Sri Lanka  |              130 |                 15 | 14.02 |     7.66 |    19.22 |          65.4 |        14.02 |              0 |                 15 |                  10 |             33.33 |       8.77 |            9.05 |               4 |
|      4 | Rashid Khan         | Gujarat Titans / Afghanistan     |              243 |                 26 | 13.73 |     8.52 |    18.73 |          71.6 |        13.73 |              0 |                 26 |                   9 |             65.39 |       7.42 |            6.68 |              15 |
|      5 | Mujeeb Ur Rahman    | Afghanistan / Mumbai Indians     |              121 |                 13 | 12.1  |     6.88 |    17.09 |          54.2 |        12.1  |              0 |                 13 |                   4 |             69.23 |       7.02 |            6.2  |               6 |
|      6 | Varun Chakravarthy  | Kolkata Knight Riders / India    |              149 |                 19 | 11.87 |     7.04 |    16.65 |          51.6 |        11.87 |              0 |                 19 |                   6 |             68.42 |       7.98 |            7.83 |              10 |
|      7 | Mustafizur Rahman   | Bangladesh / Delhi Capitals      |              119 |                 15 | 11.21 |     6.07 |    16.51 |          48.4 |        11.21 |              0 |                 15 |                   9 |             40    |       7.79 |            8.84 |               7 |
|      8 | Blessing Muzarabani | Zimbabwe / Kolkata Knight Riders |              102 |                 11 | 10.96 |     4.53 |    16.97 |          42   |        10.96 |              0 |                 11 |                   4 |             63.64 |       7.54 |            7.78 |               7 |
|      9 | Kuldeep Yadav       | Delhi Capitals / India           |              200 |                 20 | 10.82 |     5.44 |    15.67 |          41   |        10.82 |              0 |                 20 |                   9 |             55    |       7.98 |            7.48 |              11 |
|     10 | Abrar Ahmed         | Pakistan                         |               78 |                  7 | 10.79 |     4.49 |    16.62 |          42.6 |        10.79 |              0 |                  7 |                   4 |             42.86 |       6.68 |            6.31 |               1 |

PS = runs SAVED vs an average bowler in the identical situations per 100 pressure balls (wickets converted to runs at their pressure-situation worth); PS_p10-p90 = bootstrap interval; P_top10 = % of 500 match re-samples in which the player is top 10; PS_overall = usual level (all balls); clutch_delta = shrunk pressure-specific adjustment; consistency = % of pressure innings (>= 3 pressure balls or dismissed/wicket on one) with positive value.

**Observed pressure-only record** (secondary, descriptive: pressure balls only, no shrinkage toward usual level; split-half reliability is low, so treat as a record of what happened, not a skill estimate):

| player_name        |   pressure_balls |   pressure_innings |   pressure_successes |   pressure_failures |   PS_raw_pressure_only |    PS |   main_rank |
|:-------------------|-----------------:|-------------------:|---------------------:|--------------------:|-----------------------:|------:|------------:|
| Digvesh Rathi      |               67 |                  8 |                    5 |                   3 |                  59.11 |  0.02 |          62 |
| Ravi Bishnoi       |              221 |                 25 |                   17 |                   8 |                  49.82 |  2.79 |          41 |
| Jason Behrendorff  |               66 |                  8 |                    4 |                   4 |                  49.67 | -2.28 |          77 |
| Nathan Ellis       |               83 |                 10 |                    6 |                   4 |                  47.89 | 10.12 |          12 |
| Mark Wood          |               73 |                  8 |                    5 |                   3 |                  42.29 |  7.14 |          17 |
| Rashid Khan        |              243 |                 26 |                   17 |                   9 |                  39.86 | 13.73 |           4 |
| Shoriful Islam     |               83 |                  9 |                    5 |                   4 |                  38.62 | -2.15 |          76 |
| Jofra Archer       |              131 |                 13 |                   10 |                   3 |                  38.36 |  2.88 |          40 |
| Harpreet Brar      |               92 |                 11 |                    7 |                   4 |                  36.71 |  4.54 |          31 |
| Azmatullah Omarzai |              116 |                 16 |                    9 |                   7 |                  36.13 | -1.09 |          68 |

**Above the diagonal but not in the top 10 - why** (diagonal y = x in `figures/quadrant_bowl.png` means 'pressure record equals usual level'; top-10 cut-off = PS of #10 = 10.79). See also `figures/selection_bowl.png`:

|   rank | player_name        |   pressure_balls |   PS_overall |   PS_raw_pressure_only |   clutch_delta |    PS | reason_not_in_top10                                                                                                                                                     |
|-------:|:-------------------|-----------------:|-------------:|-----------------------:|---------------:|------:|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|     12 | Nathan Ellis       |               83 |        10.12 |                  47.89 |              0 | 10.12 | Raw gap +37.8 on 83 pressure balls; reliability supports +0.0, so PS = 10.1 +0.0 = 10.1 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value) |
|     13 | Krunal Pandya      |              162 |         9.52 |                  33.61 |              0 |  9.52 | Raw gap +24.1 on 162 pressure balls; reliability supports +0.0, so PS = 9.5 +0.0 = 9.5 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)  |
|     14 | Mitchell Santner   |              173 |         9.28 |                  21.57 |              0 |  9.28 | Raw gap +12.3 on 173 pressure balls; reliability supports +0.0, so PS = 9.3 +0.0 = 9.3 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)  |
|     15 | Josh Hazlewood     |              133 |         9.14 |                  33.62 |              0 |  9.14 | Raw gap +24.5 on 133 pressure balls; reliability supports +0.0, so PS = 9.1 +0.0 = 9.1 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)  |
|     16 | Bhuvneshwar Kumar  |              250 |         7.94 |                  14.8  |              0 |  7.94 | Raw gap +6.9 on 250 pressure balls; reliability supports +0.0, so PS = 7.9 +0.0 = 7.9 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)   |
|     17 | Mark Wood          |               73 |         7.14 |                  42.29 |              0 |  7.14 | Raw gap +35.2 on 73 pressure balls; reliability supports +0.0, so PS = 7.1 +0.0 = 7.1 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)   |
|     19 | Maheesh Theekshana |              201 |         6.77 |                  10.92 |              0 |  6.77 | Raw gap +4.2 on 201 pressure balls; reliability supports +0.0, so PS = 6.8 +0.0 = 6.8 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)   |
|     20 | Mohammad Nawaz     |              111 |         6.76 |                  21.99 |              0 |  6.76 | Raw gap +15.2 on 111 pressure balls; reliability supports +0.0, so PS = 6.8 +0.0 = 6.8 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)  |
|     23 | Akeal Hosein       |              216 |         6.19 |                  32.57 |              0 |  6.19 | Raw gap +26.4 on 216 pressure balls; reliability supports +0.0, so PS = 6.2 +0.0 = 6.2 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)  |
|     28 | Mahedi Hasan       |               96 |         5.72 |                   9.6  |              0 |  5.72 | Raw gap +3.9 on 96 pressure balls; reliability supports +0.0, so PS = 5.7 +0.0 = 5.7 < cut-off 10.8 (usual level too low even with the full raw gap)                    |
|     31 | Harpreet Brar      |               92 |         4.54 |                  36.71 |              0 |  4.54 | Raw gap +32.2 on 92 pressure balls; reliability supports +0.0, so PS = 4.5 +0.0 = 4.5 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)   |
|     32 | Yuzvendra Chahal   |              176 |         4.22 |                  20.29 |              0 |  4.22 | Raw gap +16.1 on 176 pressure balls; reliability supports +0.0, so PS = 4.2 +0.0 = 4.2 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)  |
|     33 | Taskin Ahmed       |               98 |         3.87 |                   7.99 |              0 |  3.87 | Raw gap +4.1 on 98 pressure balls; reliability supports +0.0, so PS = 3.9 +0.0 = 3.9 < cut-off 10.8 (usual level too low even with the full raw gap)                    |
|     37 | Jacob Duffy        |               69 |         3.19 |                  35.85 |              0 |  3.19 | Raw gap +32.7 on 69 pressure balls; reliability supports +0.0, so PS = 3.2 +0.0 = 3.2 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)   |
|     39 | Adil Rashid        |               87 |         3.12 |                  26.38 |              0 |  3.12 | Raw gap +23.3 on 87 pressure balls; reliability supports +0.0, so PS = 3.1 +0.0 = 3.1 < cut-off 10.8 (would enter only if the whole raw gap were taken at face value)   |

Positions 11-20 (for discussion of close calls):

|   rank | player_name        |    PS |   PS_p10 |   PS_p90 |   P_top10_pct |
|-------:|:-------------------|------:|---------:|---------:|--------------:|
|     11 | Noor Ahmad         | 10.55 |     5.18 |    16.59 |          41.2 |
|     12 | Nathan Ellis       | 10.12 |     4.98 |    15.18 |          35.2 |
|     13 | Krunal Pandya      |  9.52 |     3.7  |    15.26 |          33.6 |
|     14 | Mitchell Santner   |  9.28 |     4.69 |    14.17 |          30   |
|     15 | Josh Hazlewood     |  9.14 |     3.02 |    14.8  |          30.8 |
|     16 | Bhuvneshwar Kumar  |  7.94 |     3.51 |    13.28 |          18.8 |
|     17 | Mark Wood          |  7.14 |     0.55 |    12.92 |          16   |
|     18 | Mohsin Khan        |  6.92 |     0.53 |    12.76 |          14.6 |
|     19 | Maheesh Theekshana |  6.77 |     3.18 |    10.67 |           5.8 |
|     20 | Mohammad Nawaz     |  6.76 |     0.79 |    12.79 |          13.6 |

**Evidence cards - each top-10 bowler's three most valuable pressure innings** (runs = conceded on pressure balls; wickets = taken):

|   rank | player              | date       | match                                               |   innings | entry_state                 | last_pressure_ball_state    |   pressure_balls |   runs |   wickets |   value_runs_above_avg |
|-------:|:--------------------|:-----------|:----------------------------------------------------|----------:|:----------------------------|:----------------------------|-----------------:|-------:|----------:|-----------------------:|
|      1 | Jasprit Bumrah      | 2024-04-11 | Mumbai Indians v Royal Challengers Bengaluru        |         1 | 89/2 after 10 ov (1st inn)  | 171/8 after 18 ov (1st inn) |               18 |     17 |         4 |                   32.6 |
|      1 | Jasprit Bumrah      | 2026-04-20 | Gujarat Titans v Mumbai Indians                     |         2 | 200 off 120, 10 wkts left   | 199 off 115, 9 wkts left    |                6 |      1 |         1 |                   11.6 |
|      1 | Jasprit Bumrah      | 2025-05-30 | Gujarat Titans v Mumbai Indians                     |         2 | 81 off 42, 8 wkts left      | 78 off 37, 7 wkts left      |                6 |      4 |         1 |                   11.5 |
|      2 | Sunil Narine        | 2025-05-25 | Sunrisers Hyderabad v Kolkata Knight Riders         |         1 | 170/1 after 12 ov (1st inn) | 171/2 after 12 ov (1st inn) |                6 |      1 |         1 |                   14.7 |
|      2 | Sunil Narine        | 2025-04-29 | Delhi Capitals v Kolkata Knight Riders              |         2 | 75 off 42, 7 wkts left      | 67 off 37, 6 wkts left      |                6 |      8 |         2 |                   13.5 |
|      2 | Sunil Narine        | 2023-04-06 | Kolkata Knight Riders v Royal Challengers Bengaluru |         2 | 163 off 96, 10 wkts left    | 161 off 91, 9 wkts left     |                6 |      3 |         1 |                   12   |
|      3 | Matheesha Pathirana | 2025-05-03 | Royal Challengers Bengaluru v Chennai Super Kings   |         1 | 154/4 after 17 ov (1st inn) | 158/5 after 17 ov (1st inn) |                8 |      5 |         1 |                   12.7 |
|      3 | Matheesha Pathirana | 2023-04-17 | Royal Challengers Bengaluru v Chennai Super Kings   |         2 | 35 off 18, 5 wkts left      | 32 off 13, 4 wkts left      |                7 |      4 |         1 |                   10.9 |
|      3 | Matheesha Pathirana | 2024-10-13 | Sri Lanka v West Indies                             |         2 | 18 off 18, 6 wkts left      | 13 off 13, 5 wkts left      |                7 |      5 |         1 |                   10.6 |
|      4 | Rashid Khan         | 2026-04-08 | Delhi Capitals v Gujarat Titans                     |         2 | 175 off 96, 10 wkts left    | 77 off 37, 7 wkts left      |               18 |     12 |         3 |                   35   |
|      4 | Rashid Khan         | 2024-03-15 | Afghanistan v Ireland                               |         1 | 66/2 after 10 ov (1st inn)  | 70/4 after 10 ov (1st inn)  |                6 |      1 |         2 |                   19.1 |
|      4 | Rashid Khan         | 2024-12-09 | Zimbabwe v Afghanistan                              |         2 | 28 off 24, 7 wkts left      | 26 off 19, 5 wkts left      |                7 |      3 |         2 |                   18.2 |
|      5 | Mujeeb Ur Rahman    | 2025-10-03 | Afghanistan v Bangladesh                            |         2 | 125 off 96, 8 wkts left     | 123 off 91, 7 wkts left     |                6 |      3 |         1 |                    9.6 |
|      5 | Mujeeb Ur Rahman    | 2025-09-05 | Afghanistan v United Arab Emirates                  |         2 | 164 off 114, 10 wkts left   | 56 off 31, 6 wkts left      |               13 |     11 |         1 |                    8.9 |
|      5 | Mujeeb Ur Rahman    | 2025-03-29 | Gujarat Titans v Mumbai Indians                     |         1 | 121/1 after 13 ov (1st inn) | 130/2 after 13 ov (1st inn) |                7 |      9 |         1 |                    7.6 |
|      6 | Varun Chakravarthy  | 2026-04-19 | Kolkata Knight Riders v Rajasthan Royals            |         1 | 79/0 after 8 ov (1st inn)   | 81/1 after 8 ov (1st inn)   |                6 |      1 |         1 |                   14.4 |
|      6 | Varun Chakravarthy  | 2024-05-11 | Kolkata Knight Riders v Mumbai Indians              |         2 | 70 off 54, 7 wkts left      | 67 off 49, 6 wkts left      |                7 |      3 |         1 |                   11.1 |
|      6 | Varun Chakravarthy  | 2024-05-03 | Mumbai Indians v Kolkata Knight Riders              |         2 | 134 off 96, 9 wkts left     | 132 off 91, 8 wkts left     |                6 |      3 |         1 |                   10.7 |
|      7 | Mustafizur Rahman   | 2024-03-22 | Chennai Super Kings v Royal Challengers Bengaluru   |         1 | 37/0 after 4 ov (1st inn)   | 41/1 after 4 ov (1st inn)   |                6 |      4 |         2 |                   18.9 |
|      7 | Mustafizur Rahman   | 2024-05-10 | Bangladesh v Zimbabwe                               |         2 | 111 off 90, 7 wkts left     | 50 off 31, 5 wkts left      |               12 |      7 |         2 |                   17.8 |
|      7 | Mustafizur Rahman   | 2025-05-24 | Delhi Capitals v Punjab Kings                       |         1 | 142/4 after 15 ov (1st inn) | 145/5 after 15 ov (1st inn) |                6 |      4 |         1 |                   10.7 |
|      8 | Blessing Muzarabani | 2024-05-12 | Bangladesh v Zimbabwe                               |         1 | 9/0 after 1 ov (1st inn)    | 9/1 after 1 ov (1st inn)    |                6 |      0 |         1 |                   12.4 |
|      8 | Blessing Muzarabani | 2023-12-09 | Zimbabwe v Ireland                                  |         2 | 156 off 114, 10 wkts left   | 21 off 13, 5 wkts left      |               18 |     15 |         1 |                   10.2 |
|      8 | Blessing Muzarabani | 2026-04-02 | Kolkata Knight Riders v Sunrisers Hyderabad         |         1 | 211/6 after 19 ov (1st inn) | 226/7 after 19 ov (1st inn) |                7 |     15 |         2 |                    7.5 |
|      9 | Kuldeep Yadav       | 2026-05-24 | Kolkata Knight Riders v Delhi Capitals              |         2 | 111 off 66, 8 wkts left     | 75 off 37, 5 wkts left      |               12 |      8 |         3 |                   28.2 |
|      9 | Kuldeep Yadav       | 2022-03-27 | Delhi Capitals v Mumbai Indians                     |         1 | 65/0 after 8 ov (1st inn)   | 84/2 after 10 ov (1st inn)  |               12 |     10 |         2 |                   18   |
|      9 | Kuldeep Yadav       | 2022-05-16 | Punjab Kings v Delhi Capitals                       |         2 | 101 off 78, 6 wkts left     | 99 off 73, 6 wkts left      |                6 |      2 |         1 |                    9.9 |
|     10 | Abrar Ahmed         | 2025-09-17 | Pakistan v United Arab Emirates                     |         2 | 112 off 96, 9 wkts left     | 68 off 43, 7 wkts left      |               12 |      7 |         1 |                   10.9 |
|     10 | Abrar Ahmed         | 2025-09-04 | Pakistan v United Arab Emirates                     |         2 | 144 off 96, 10 wkts left    | 143 off 91, 10 wkts left    |                6 |      2 |         0 |                    5.1 |
|     10 | Abrar Ahmed         | 2026-01-29 | Pakistan v Australia                                |         2 | 92 off 66, 6 wkts left      | 90 off 61, 6 wkts left      |                6 |      3 |         0 |                    1.8 |


## 7c. Super overs (descriptive only - 6 super overs, 38 balls in the data)

| date       | match                                        |   innings | batter               | bowler             |   batter_runs |   legal_balls |   wickets |
|:-----------|:---------------------------------------------|----------:|:---------------------|:-------------------|--------------:|--------------:|----------:|
| 2024-07-30 | Sri Lanka v India                            |         3 | Kusal Mendis         | Washington Sundar  |             1 |             1 |         0 |
| 2024-07-30 | Sri Lanka v India                            |         3 | Kusal Perera         | Washington Sundar  |             0 |             1 |         1 |
| 2024-07-30 | Sri Lanka v India                            |         3 | Pathum Nissanka      | Washington Sundar  |             0 |             1 |         1 |
| 2024-07-30 | Sri Lanka v India                            |         4 | Suryakumar Yadav     | Maheesh Theekshana |             4 |             1 |         0 |
| 2025-04-16 | Delhi Capitals v Rajasthan Royals            |         3 | Riyan Parag          | Mitchell Starc     |             4 |             1 |         1 |
| 2025-04-16 | Delhi Capitals v Rajasthan Royals            |         3 | Shimron Hetmyer      | Mitchell Starc     |             6 |             4 |         1 |
| 2025-04-16 | Delhi Capitals v Rajasthan Royals            |         4 | Lokesh Rahul         | Sandeep Sharma     |             7 |             3 |         0 |
| 2025-04-16 | Delhi Capitals v Rajasthan Royals            |         4 | Tristan Stubbs       | Sandeep Sharma     |             6 |             1 |         0 |
| 2025-09-26 | India v Sri Lanka                            |         3 | Kusal Perera         | Arshdeep Singh     |             0 |             1 |         1 |
| 2025-09-26 | India v Sri Lanka                            |         3 | Kamindu Mendis       | Arshdeep Singh     |             1 |             1 |         0 |
| 2025-09-26 | India v Sri Lanka                            |         3 | Dasun Shanaka        | Arshdeep Singh     |             0 |             3 |         1 |
| 2025-09-26 | India v Sri Lanka                            |         4 | Suryakumar Yadav     | Wanindu Hasaranga  |             3 |             1 |         0 |
| 2025-11-21 | Bangladesh A v India A                       |         3 | Jitesh Sharma        | Ripon Mondol       |             0 |             1 |         1 |
| 2025-11-21 | Bangladesh A v India A                       |         3 | Ashutosh Sharma      | Ripon Mondol       |             0 |             1 |         1 |
| 2025-11-21 | Bangladesh A v India A                       |         4 | Yasir Ali Chowdhury  | Suyash Sharma      |             0 |             1 |         1 |
| 2025-11-21 | Bangladesh A v India A                       |         4 | Mohammad Akbar Ali   | Suyash Sharma      |             0 |             0 |         0 |
| 2025-11-23 | Bangladesh A v Pakistan A                    |         3 | Abdul Saqlain        | Ahmed Daniyal      |             0 |             1 |         1 |
| 2025-11-23 | Bangladesh A v Pakistan A                    |         3 | Habibur Rahman Sohan | Ahmed Daniyal      |             1 |             1 |         0 |
| 2025-11-23 | Bangladesh A v Pakistan A                    |         3 | Jishan Alam          | Ahmed Daniyal      |             0 |             1 |         1 |
| 2025-11-23 | Bangladesh A v Pakistan A                    |         4 | Saad Masood          | Ripon Mondol       |             5 |             3 |         0 |
| 2025-11-23 | Bangladesh A v Pakistan A                    |         4 | Maaz Sadaqat         | Ripon Mondol       |             1 |             1 |         0 |
| 2026-04-26 | Lucknow Super Giants v Kolkata Knight Riders |         3 | Rishabh Pant         | Sunil Narine       |             1 |             1 |         0 |
| 2026-04-26 | Lucknow Super Giants v Kolkata Knight Riders |         3 | Nicholas Pooran      | Sunil Narine       |             0 |             1 |         1 |
| 2026-04-26 | Lucknow Super Giants v Kolkata Knight Riders |         3 | Aiden Markram        | Sunil Narine       |             0 |             1 |         1 |
| 2026-04-26 | Lucknow Super Giants v Kolkata Knight Riders |         4 | Rinku Singh          | Prince Yadav       |             4 |             1 |         0 |

Too few deliveries to enter any rating (1-2 balls per player); reported for completeness.


## 7d. Knockout matches

31 knockout matches (Qualifier, Eliminator, Final, Semi Final). How they enter the analysis: (a) every knockout delivery is scored by the same Leverage Index as any other ball - a tight knockout finish is a pressure over like a tight league finish; (b) we do NOT add an arbitrary knockout weight to the main score, because knockout samples are tiny (a player has 0-6 knockout innings) - instead (c) a robustness check multiplies knockout leverage by 1.5 (section 8), and (d) the descriptive tables below compare knockout and regular-match performance.

League-wide, batters (situation-adjusted; ~0 means knockouts are not systematically different):

| knockout   |   balls |   runs_above_exp_per100 |   wkts_above_exp_per100 |
|:-----------|--------:|------------------------:|------------------------:|
| False      |  178615 |                    0.35 |                   0.014 |
| True       |    5647 |                   -0.17 |                  -0.443 |

League-wide, bowlers (situation-adjusted; ~0 means knockouts are not systematically different):

| knockout   |   balls |   runs_above_exp_per100 |   wkts_above_exp_per100 |
|:-----------|--------:|------------------------:|------------------------:|
| False      |  185249 |                   -0.42 |                   0.006 |
| True       |    5841 |                    0.01 |                   0.503 |

Knockout record of the top-10 batters (value_per100 = runs added vs average per 100 knockout balls; small samples - descriptive only):

|   rank | player_name          |   PS |   ko_matches |   ko_balls |   runs |   outs |   value_per100 |
|-------:|:---------------------|-----:|-------------:|-----------:|-------:|-------:|---------------:|
|      1 | Vaibhav Sooryavanshi | 36   |            2 |         76 |    193 |      2 |          110   |
|      2 | Tim David            | 28.6 |            4 |         38 |     43 |      4 |          -56.2 |
|      3 | Abhishek Sharma      | 24.8 |            5 |         22 |     22 |      5 |         -112.2 |
|      4 | Suryakumar Yadav     | 23.5 |            5 |        109 |    172 |      5 |            5.2 |
|      5 | Andre Russell        | 23   |          nan |        nan |    nan |    nan |          nan   |
|      6 | Phil Salt            | 20.3 |            2 |         36 |     72 |      1 |           67.3 |
|      7 | Heinrich Klaasen     | 18.1 |            4 |         82 |    116 |      4 |           16.6 |
|      8 | Rinku Singh          | 14.3 |            1 |          1 |      4 |      0 |          276.1 |
|      9 | Shashank Singh       | 14.1 |            3 |         38 |     66 |      2 |           35.3 |
|     10 | Romario Shepherd     | 13.6 |            1 |          9 |     17 |      1 |            7.6 |

Knockout record of the top-10 bowlers (value_per100 = runs saved vs average per 100 knockout balls; small samples - descriptive only):

|   rank | player_name         |   PS |   ko_matches |   ko_balls |   runs |   wickets |   value_per100 |
|-------:|:--------------------|-----:|-------------:|-----------:|-------:|----------:|---------------:|
|      1 | Jasprit Bumrah      | 22.3 |            3 |         68 |     92 |         3 |           14.9 |
|      2 | Sunil Narine        | 20.3 |            2 |         47 |     56 |         2 |           -7.3 |
|      3 | Matheesha Pathirana | 14   |            2 |         56 |     81 |         4 |            8.6 |
|      4 | Rashid Khan         | 13.7 |           10 |        217 |    315 |         9 |           -4.6 |
|      5 | Mujeeb Ur Rahman    | 12.1 |          nan |        nan |    nan |       nan |          nan   |
|      6 | Varun Chakravarthy  | 11.9 |            3 |         62 |     65 |         5 |           37.9 |
|      7 | Mustafizur Rahman   | 11.2 |          nan |        nan |    nan |       nan |          nan   |
|      8 | Blessing Muzarabani | 11   |          nan |        nan |    nan |       nan |          nan   |
|      9 | Kuldeep Yadav       | 10.8 |            1 |         28 |     30 |         4 |          104.9 |
|     10 | Abrar Ahmed         | 10.8 |            3 |         76 |     64 |         5 |           42.2 |


## 8. Robustness of the top 10

| role   | check                            |   top10_overlap |   rank_corr |
|:-------|:---------------------------------|----------------:|------------:|
| bat    | v1 symmetric ball-level LI>=1.5  |               7 |        0.96 |
| bat    | Behind-gate at 40%               |               8 |        0.95 |
| bat    | Behind-gate at 60%               |               8 |        0.97 |
| bat    | LI threshold 1.25                |              10 |        0.99 |
| bat    | LI threshold 2.0                 |               6 |        0.9  |
| bat    | Full members + IPL only          |              10 |        0.99 |
| bat    | IPL only                         |               7 |        0.85 |
| bat    | LI rescaled within innings       |               8 |        0.94 |
| bat    | Knockout leverage x1.5           |              10 |        1    |
| bat    | Wicket valued at 2x              |               8 |        0.91 |
| bat    | Wicket valued at 0.5x            |               7 |        0.95 |
| bat    | Rank by lower 80% bound          |               8 |      nan    |
| bat    | Raw pressure-only (no shrinkage) |               4 |      nan    |
| bat    | Realised pressure WPA total      |               2 |      nan    |
| bowl   | v1 symmetric ball-level LI>=1.5  |               9 |        1    |
| bowl   | Behind-gate at 40%               |               8 |        0.99 |
| bowl   | Behind-gate at 60%               |              10 |        1    |
| bowl   | LI threshold 1.25                |              10 |        1    |
| bowl   | LI threshold 2.0                 |               6 |        1    |
| bowl   | Full members + IPL only          |               8 |        0.99 |
| bowl   | IPL only                         |               6 |        0.85 |
| bowl   | LI rescaled within innings       |              10 |        1    |
| bowl   | Knockout leverage x1.5           |              10 |        1    |
| bowl   | Wicket valued at 2x              |               7 |        0.97 |
| bowl   | Wicket valued at 0.5x            |               8 |        0.99 |
| bowl   | Rank by lower 80% bound          |               8 |      nan    |
| bowl   | Raw pressure-only (no shrinkage) |               1 |      nan    |
| bowl   | Realised pressure WPA total      |               3 |      nan    |

Top-10 overlap with the main list under each alternative; rank correlation over all eligible players.


## 9. Figures

- `figures/li_by_category.png`

- `figures/li_distribution.png`

- `figures/outcomes_by_li.png`

- `figures/pressure_map_2024-04-21.png`

- `figures/pressure_map_2024-05-02.png`

- `figures/quadrant_bat.png`

- `figures/quadrant_bowl.png`

- `figures/reliability.png`

- `figures/selection_bat.png`

- `figures/selection_bowl.png`

- `figures/top10_bat.png`

- `figures/top10_bowl.png`

- `figures/wp_calibration.png`
