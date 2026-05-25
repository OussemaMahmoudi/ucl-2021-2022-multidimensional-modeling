import os
import sys
import logging
import warnings
import pandas as pd
import numpy as np
import psycopg2
import pygrametl
from pygrametl.datasources import PandasSource
from pygrametl.tables import (
    CachedDimension,
    FactTable,
    SlowlyChangingDimension,
)

warnings.filterwarnings("ignore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

DATA_DIR = r"c:\Users\oussa\OneDrive\Bureau\MMD Project\files"

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "database": "champions_dwh",
    "user":     "postgres",
    "password": "your_password", 
}



def load_csv(fname):
    """Load a dirty CSV with standard NA tokens."""
    path = os.path.join(DATA_DIR, fname)
    return pd.read_csv(path, na_values=["N/A", "unknown", "-", "", "nan"])


def normalize_position(pos):
    """Standardise position labels to: Forward / Midfielder / Defender / Goalkeeper."""
    m = {
        "gk":         "Goalkeeper",
        "goalkeeper": "Goalkeeper",
        "forward":    "Forward",
        "midfielder": "Midfielder",
        "defender":   "Defender",
    }
    return m.get(str(pos).strip().lower(), str(pos).strip().title())


def clean_str(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()
    return df


def to_num(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def fill_median(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = df[c].fillna(df[c].median())
    return df


def clean_key_stats():
    log.info("Cleaning key_stats_dirty.csv ...")
    df = load_csv("key_stats_dirty.csv")
    df = clean_str(df, ["player_name", "club", "position"])
    df["position"] = df["position"].apply(normalize_position)
    df = df.drop_duplicates(subset=["player_name", "club"])
    df = to_num(df, ["minutes_played", "match_played", "goals", "assists", "distance_covered"])

    # Fix anomalies
    df.loc[df["distance_covered"] < 0, "distance_covered"] = np.nan
    df.loc[df["minutes_played"]  > 1170, "minutes_played"] = np.nan
    df = fill_median(df, ["goals", "assists", "distance_covered", "minutes_played"])
    df["match_played"] = df["match_played"].clip(lower=1)
    log.info(f"  -> {len(df)} rows")
    return df


def clean_goals():
    log.info("Cleaning goals_dirty.csv ...")
    df = load_csv("goals_dirty.csv")
    df = clean_str(df, ["player_name", "club", "position"])
    df["position"] = df["position"].apply(normalize_position)
    df = df.drop_duplicates(subset=["player_name", "club"])
    cols = ["goals", "right_foot", "left_foot", "headers",
            "others", "inside_area", "outside_areas", "penalties", "match_played"]
    df = to_num(df, cols)
    df.loc[df["goals"] > 50, "goals"] = np.nan
    df.loc[df["goals"] < 0,  "goals"] = np.nan
    df.loc[df["inside_area"] < 0, "inside_area"] = np.nan
    df = fill_median(df, ["goals", "right_foot", "left_foot", "headers", "inside_area"])
    log.info(f"  -> {len(df)} rows")
    return df


def clean_attempts():
    log.info("Cleaning attempts_dirty.csv ...")
    df = load_csv("attempts_dirty.csv")
    df = clean_str(df, ["player_name", "club", "position"])
    df["position"] = df["position"].apply(normalize_position)
    df = df.drop_duplicates(subset=["player_name", "club"])
    cols = ["total_attempts", "on_target", "off_target", "blocked", "match_played"]
    df = to_num(df, cols)
    df.loc[df["total_attempts"] > 200, "total_attempts"] = np.nan
    df.loc[df["total_attempts"] < 0,   "total_attempts"] = np.nan
    df = fill_median(df, ["total_attempts", "on_target", "off_target", "blocked"])
    log.info(f"  -> {len(df)} rows")
    return df


def clean_attacking():
    log.info("Cleaning attacking_dirty.csv ...")
    df = load_csv("attacking_dirty.csv")
    df = clean_str(df, ["player_name", "club", "position"])
    df["position"] = df["position"].apply(normalize_position)
    df = df.drop_duplicates(subset=["player_name", "club"])
    cols = ["assists", "corner_taken", "offsides", "dribbles", "match_played"]
    df = to_num(df, cols)
    df.loc[df["assists"] > 20, "assists"] = np.nan
    df.loc[df["assists"] < 0,  "assists"] = np.nan
    df.loc[df["match_played"] < 0, "match_played"] = np.nan
    df.loc[df["dribbles"]    < 0, "dribbles"]    = np.nan
    df = fill_median(df, ["assists", "dribbles"])
    log.info(f"  -> {len(df)} rows")
    return df


def clean_defending():
    log.info("Cleaning defending_dirty.csv ...")
    df = load_csv("defending_dirty.csv")
    df = clean_str(df, ["player_name", "club", "position"])
    df["position"] = df["position"].apply(normalize_position)
    df = df.drop_duplicates(subset=["player_name", "club"])
    num_cols = [c for c in ["tackles", "t_won", "t_lost",
                             "balls_recoverd", "clearance", "match_played"]
                if c in df.columns]
    df = to_num(df, num_cols)
    if "balls_recoverd" in df.columns:
        df.loc[df["balls_recoverd"] > 500, "balls_recoverd"] = np.nan
        df.loc[df["balls_recoverd"] < 0,   "balls_recoverd"] = np.nan
    if "t_won" in df.columns and "tackles" in df.columns:
        df.loc[df["t_won"] > df["tackles"], "t_won"] = df["tackles"]
    df = fill_median(df, num_cols)
    log.info(f"  -> {len(df)} rows")
    return df


def clean_distribution():
    log.info("Cleaning distribution_dirty.csv ...")
    df = load_csv("distribution_dirty.csv")
    df = clean_str(df, ["player_name", "club", "position"])
    df["position"] = df["position"].apply(normalize_position)
    df = df.drop_duplicates(subset=["player_name", "club"])
    num_cols = [c for c in ["pass_attempted", "pass_completed",
                             "pass_accuracy", "cross_accuracy", "match_played"]
                if c in df.columns]
    df = to_num(df, num_cols)
    if "pass_accuracy" in df.columns:
        df.loc[df["pass_accuracy"] > 100, "pass_accuracy"] = np.nan
    if "pass_completed" in df.columns and "pass_attempted" in df.columns:
        mask = df["pass_completed"] > df["pass_attempted"]
        df.loc[mask, ["pass_completed", "pass_attempted"]] = \
            df.loc[mask, ["pass_attempted", "pass_completed"]].values
    df = fill_median(df, num_cols)
    log.info(f"  -> {len(df)} rows")
    return df


def clean_disciplinary():
    log.info("Cleaning disciplinary_dirty.csv ...")
    df = load_csv("disciplinary_dirty.csv")
    df = clean_str(df, ["player_name", "club", "position"])
    df["position"] = df["position"].apply(normalize_position)
    df = df.drop_duplicates(subset=["player_name", "club"])
    cols = ["fouls_committed", "fouls_suffered", "red", "yellow",
            "minutes_played", "match_played"]
    df = to_num(df, cols)
    df.loc[df["minutes_played"] < 0, "minutes_played"] = np.nan
    df.loc[df["red"] > df["match_played"], "red"] = 1
    df = fill_median(df, ["fouls_committed", "fouls_suffered", "yellow"])
    df["red"] = df["red"].fillna(0)
    log.info(f"  -> {len(df)} rows")
    return df


def clean_goalkeeping():
    log.info("Cleaning goalkeeping_dirty.csv ...")
    df = load_csv("goalkeeping_dirty.csv")
    df = clean_str(df, ["player_name", "club", "position"])
    df = df.drop_duplicates(subset=["player_name", "club"])
    cols = ["saved", "conceded", "saved_penalties",
            "cleansheets", "punches made", "match_played"]
    df = to_num(df, cols)
    df.loc[df["saved"] > 100, "saved"] = np.nan
    df.loc[df["saved"] < 0,   "saved"] = np.nan
    mask = (df["conceded"] == 0) & (df["cleansheets"] == 0)
    df.loc[mask, "cleansheets"] = df.loc[mask, "match_played"]
    df = fill_median(df, ["saved", "conceded", "cleansheets"])
    df["match_played"] = df["match_played"].clip(lower=1)
    log.info(f"  -> {len(df)} rows")
    return df



def build_master():
    log.info("=== Building master dataframe ===")
    key  = clean_key_stats()
    gls  = clean_goals()
    att  = clean_attempts()
    atk  = clean_attacking()
    dff  = clean_defending()
    dis  = clean_distribution()
    dsc  = clean_disciplinary()
    gk   = clean_goalkeeping()

    master = key[["player_name", "club", "position",
                  "minutes_played", "match_played",
                  "goals", "assists", "distance_covered"]].copy()

    def left(base, other, on, cols):
        keep = [c for c in cols if c in other.columns]
        return base.merge(other[["player_name", "club"] + keep],
                          on=on, how="left", suffixes=("", "_dup"))

    KEY = ["player_name", "club"]
    master = left(master, gls, KEY,
                  ["right_foot", "left_foot", "headers", "penalties",
                   "inside_area", "outside_areas"])
    master = left(master, att, KEY,
                  ["total_attempts", "on_target", "off_target", "blocked"])
    master = left(master, atk, KEY, ["corner_taken", "offsides", "dribbles"])
    master = left(master, dff, KEY, ["tackles", "t_won", "t_lost",
                                      "balls_recoverd", "clearance"])
    master = left(master, dis, KEY,
                  ["pass_attempted", "pass_completed",
                   "pass_accuracy", "cross_accuracy"])
    master = left(master, dsc, KEY,
                  ["fouls_committed", "fouls_suffered", "red", "yellow"])
    master = left(master, gk,  KEY,
                  ["saved", "conceded", "cleansheets",
                   "saved_penalties", "punches made"])

    master.rename(columns={
        "t_won":         "tackles_won",
        "t_lost":        "tackles_lost",
        "balls_recoverd":"balls_recovered",
        "clearance":     "clearances",
        "red":           "red_cards",
        "yellow":        "yellow_cards",
        "saved":         "gk_saved",
        "conceded":      "gk_conceded",
        "cleansheets":   "gk_clean_sheets",
        "saved_penalties":"gk_saved_penalties",
        "punches made":  "gk_punches",
        "right_foot":    "goals_right_foot",
        "left_foot":     "goals_left_foot",
        "headers":       "goals_headers",
        "penalties":     "goals_penalties",
        "inside_area":   "goals_inside_area",
        "outside_areas": "goals_outside_area",
        "on_target":     "shots_on_target",
        "off_target":    "shots_off_target",
        "blocked":       "shots_blocked",
    }, inplace=True)

    master = master[[c for c in master.columns if not c.endswith("_dup")]]

    mins90 = (master["minutes_played"] / 90).replace(0, np.nan)
    master["goals_per_90"]   = (master["goals"]   / mins90).round(3)
    master["assists_per_90"] = (master["assists"]  / mins90).round(3)
    master["ga_per_90"]      = ((master["goals"] + master["assists"]) / mins90).round(3)
    master["fouls_per_90"]   = (master["fouls_committed"].fillna(0) / mins90).round(3)

    gk_den = master["gk_saved"].fillna(0) + master["gk_conceded"].fillna(0)
    master["save_rate"] = (master["gk_saved"].fillna(0) / gk_den.replace(0, np.nan)).round(3)

    pa = master["pass_completed"].fillna(0)
    pt = master["pass_attempted"].fillna(0)
    master["pass_completion_pct"] = (pa / pt.replace(0, np.nan) * 100).round(2)

    master["pots_score"] = (
        master["goals"].fillna(0)           * 2
        + master["assists"].fillna(0)
        + master["tackles_won"].fillna(0)   / 10
        + master["pass_accuracy"].fillna(0) / 10
        + master["distance_covered"].fillna(0) / 10
    ).round(4)

    log.info(f"Master dataset: {len(master)} rows x {master.shape[1]} cols")
    return master


def safe_int(val):
    try:
        v = float(val)
        if np.isnan(v) or np.isinf(v):
            return None
        return int(round(v))
    except (TypeError, ValueError):
        return None


def safe_float(val, dp=3):
    try:
        v = float(val)
        if np.isnan(v) or np.isinf(v):
            return None
        return round(v, dp)
    except (TypeError, ValueError):
        return None


def run_etl(master: pd.DataFrame):
    log.info("=== Connecting to PostgreSQL ===")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False

    wrapper = pygrametl.ConnectionWrapper(conn)

    dim_position = CachedDimension(
        name="dim_position",
        key="position_id",
        attributes=["position_name", "position_type"],
        lookupatts=["position_name"],
    )
    position_type_map = {
        "Goalkeeper": "Goalkeeper",
        "Forward":    "Outfield",
        "Midfielder": "Outfield",
        "Defender":   "Outfield",
    }
    for pos in master["position"].dropna().unique():
        dim_position.ensure({
            "position_name": pos,
            "position_type": position_type_map.get(pos, "Outfield"),
        })
    log.info("dim_position loaded")

    dim_club = CachedDimension(
        name="dim_club",
        key="club_id",
        attributes=["club_name", "country", "league"],
        lookupatts=["club_name"],
    )
    for club in master["club"].dropna().unique():
        dim_club.ensure({"club_name": club, "country": None, "league": "UCL"})
    log.info("dim_club loaded")

    dim_player = CachedDimension(
        name="dim_player",
        key="player_id",
        attributes=["player_name", "club_id", "position_id"],
        lookupatts=["player_name", "club_id"],
    )

    fact_table = FactTable(
        name="fact_player_season",
        keyrefs=["player_id", "club_id", "position_id"],
        measures=[
            "minutes_played", "match_played", "goals", "assists",
            "distance_covered",
            "goals_right_foot", "goals_left_foot", "goals_headers",
            "goals_penalties", "goals_inside_area", "goals_outside_area",
            "total_attempts", "shots_on_target", "shots_off_target",
            "shots_blocked",
            "corner_taken", "offsides", "dribbles",
            "tackles", "tackles_won", "tackles_lost",
            "balls_recovered", "clearances",
            "pass_attempted", "pass_completed", "pass_accuracy",
            "cross_accuracy",
            "fouls_committed", "fouls_suffered", "yellow_cards", "red_cards",
            "gk_saved", "gk_conceded", "gk_clean_sheets",
            "gk_saved_penalties", "gk_punches",
            "goals_per_90", "assists_per_90", "ga_per_90",
            "save_rate", "fouls_per_90", "pass_completion_pct",
            "pots_score", "perf_score",
        ],
    )

    log.info("Loading facts ...")
    INT_COLS = [
        "minutes_played", "match_played", "goals", "assists",
        "goals_right_foot", "goals_left_foot", "goals_headers",
        "goals_penalties", "goals_inside_area", "goals_outside_area",
        "total_attempts", "shots_on_target", "shots_off_target",
        "shots_blocked", "corner_taken", "offsides", "dribbles",
        "tackles", "tackles_won", "tackles_lost", "balls_recovered",
        "clearances", "pass_attempted", "pass_completed",
        "fouls_committed", "fouls_suffered", "yellow_cards", "red_cards",
        "gk_saved", "gk_conceded", "gk_clean_sheets",
        "gk_saved_penalties", "gk_punches",
    ]
    FLOAT_COLS = [
        "distance_covered", "pass_accuracy", "cross_accuracy",
        "goals_per_90", "assists_per_90", "ga_per_90", "save_rate",
        "fouls_per_90", "pass_completion_pct", "pots_score", "perf_score",
    ]

    source = PandasSource(master)
    loaded = 0
    for row in source:
        player_name = str(row.get("player_name", "")).strip()
        club_name   = str(row.get("club", "")).strip()
        pos_name    = str(row.get("position", "Unknown")).strip()

        if not player_name or player_name == "nan":
            continue

        club_id     = dim_club.lookup({"club_name": club_name})
        position_id = dim_position.lookup({"position_name": pos_name})
        player_id   = dim_player.ensure({
            "player_name": player_name,
            "club_id":     club_id,
            "position_id": position_id,
        })

        fact_row = {
            "player_id":   player_id,
            "club_id":     club_id,
            "position_id": position_id,
        }
        for c in INT_COLS:
            fact_row[c] = safe_int(row.get(c))
        for c in FLOAT_COLS:
            fact_row[c] = safe_float(row.get(c))

        fact_table.insert(fact_row)
        loaded += 1

    wrapper.commit()
    wrapper.close()
    log.info(f"ETL complete — {loaded} fact rows inserted.")

if __name__ == "__main__":
    master = build_master()
    out = os.path.join(os.path.dirname(DATA_DIR), "results", "master_clean.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    master.to_csv(out, index=False)
    log.info(f"Master CSV saved -> {out}")

    try:
        run_etl(master)
    except Exception as e:
        log.warning(f"PostgreSQL not available — skipping DB load. ({e})")
        log.info("Master CSV is still available for dashboard use.")
