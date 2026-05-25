-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS fact_player_season CASCADE;
DROP TABLE IF EXISTS dim_player CASCADE;
DROP TABLE IF EXISTS dim_club CASCADE;
DROP TABLE IF EXISTS dim_position CASCADE;

-- DIMENSION: dim_position
CREATE TABLE dim_position (
    position_id   SERIAL PRIMARY KEY,
    position_name VARCHAR(50) NOT NULL UNIQUE,   -- Forward / Midfielder / Defender / Goalkeeper
    position_type VARCHAR(20)                     -- Outfield / Goalkeeper
);

COMMENT ON TABLE dim_position IS 'Player position dimension';

-- DIMENSION: dim_club
CREATE TABLE dim_club (
    club_id   SERIAL PRIMARY KEY,
    club_name VARCHAR(100) NOT NULL UNIQUE,
    country   VARCHAR(80),                        -- derived / enriched later
    league    VARCHAR(80)
);

COMMENT ON TABLE dim_club IS 'Football club dimension';

-- DIMENSION: dim_player
CREATE TABLE dim_player (
    player_id   SERIAL PRIMARY KEY,
    player_name VARCHAR(150) NOT NULL,
    club_id     INT  REFERENCES dim_club(club_id),
    position_id INT  REFERENCES dim_position(position_id),
    UNIQUE (player_name, club_id)
);

COMMENT ON TABLE dim_player IS 'Player dimension — one row per player-club combination';

-- FACT TABLE: fact_player_season
-- Season-level grain: one row per player per club for UCL 2021-22 season


CREATE TABLE fact_player_season (
    fact_id         SERIAL PRIMARY KEY,
    player_id       INT NOT NULL REFERENCES dim_player(player_id),
    club_id         INT NOT NULL REFERENCES dim_club(club_id),
    position_id     INT NOT NULL REFERENCES dim_position(position_id),
    minutes_played  INT,
    match_played    INT,
    goals           INT,
    assists         INT,
    distance_covered NUMERIC(8,2),
    goals_right_foot   INT,
    goals_left_foot    INT,
    goals_headers      INT,
    goals_penalties    INT,
    goals_inside_area  INT,
    goals_outside_area INT,
    total_attempts  INT,
    shots_on_target INT,
    shots_off_target INT,
    shots_blocked   INT,
    corner_taken    INT,
    offsides        INT,
    dribbles        INT,
    tackles         INT,
    tackles_won     INT,
    tackles_lost    INT,
    balls_recovered INT,
    clearances      INT,
    pass_attempted  INT,
    pass_completed  INT,
    pass_accuracy   NUMERIC(5,2),
    cross_accuracy  NUMERIC(5,2),
    fouls_committed INT,
    fouls_suffered  INT,
    yellow_cards    INT,
    red_cards       INT,
    gk_saved        INT,
    gk_conceded     INT,
    gk_clean_sheets INT,
    gk_saved_penalties INT,
    gk_punches      INT,
    goals_per_90        NUMERIC(6,3),
    assists_per_90      NUMERIC(6,3),
    ga_per_90           NUMERIC(6,3),
    save_rate           NUMERIC(5,3),
    fouls_per_90        NUMERIC(6,3),
    pass_completion_pct NUMERIC(5,2),
    pots_score      NUMERIC(10,4),
    perf_score      NUMERIC(10,4),
    loaded_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE fact_player_season IS
  'Season-level fact table: one row per player/club for UCL 2021-22';

CREATE INDEX idx_fact_club     ON fact_player_season(club_id);
CREATE INDEX idx_fact_player   ON fact_player_season(player_id);
CREATE INDEX idx_fact_position ON fact_player_season(position_id);
CREATE INDEX idx_fact_goals    ON fact_player_season(goals DESC);
CREATE INDEX idx_fact_pots     ON fact_player_season(pots_score DESC);