# =============================================================================
# FIT FILE PARSER — Step-by-step Python Tutorial
# =============================================================================
# This file is a tutorial. Each section introduces new Python concepts
# while building a real parser for Garmin .fit activity files.
#
# Run this file at any point with:
#   python dataAnalysis/fit_parser.py
# (from the project root, or adjust the path below to where your .fit files are)
# =============================================================================


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Imports, Variables, and Data Types
# ─────────────────────────────────────────────────────────────────────────────
#
# CONCEPT: import
# Python doesn't load everything by default — you ask for what you need.
# `fitparse` is the library that knows how to read binary .fit files.
# Without this line, Python wouldn't know what FitFile is.

import fitparse


# CONCEPT: variables
# A variable is a named container for a value. You assign with =
# Python figures out the type automatically (no need to declare "string" or "int").

race_name = "SDW100 2026"          # str  — a piece of text, always in quotes
distance_miles = 100               # int  — a whole number
distance_km = 160.0                # float — a number with decimals


# CONCEPT: f-strings  (formatted string literals)
# Prefix a string with f"..." and you can embed variables inside {} directly.
# This is the modern, readable way to build strings in Python.

print(f"Race: {race_name}")
print(f"Distance: {distance_miles} miles / {distance_km} km")


# CONCEPT: a path is just a string
# We store the file path in a variable so we only have to change it in one place.

FIT_FILE = "../dataSources/racesFIT/SDW100_2026.fit"


# CONCEPT: calling a function / creating an object
# FitFile(...) is a constructor — it opens the .fit file and prepares it for reading.
# We store the result in a variable called `activity` so we can use it later.

activity = fitparse.FitFile(FIT_FILE)

print(f"FIT Protocol Version: {activity.protocol_version}")
print(f"FIT Profile Version: {activity.profile_version}")


# CONCEPT: get_messages() — reading data from the file
# A .fit file is made up of different message types.
# "session" contains one summary record for the whole activity.
# get_messages("session") returns all session messages (there's usually just one).
#
# `for ... in ...` is a loop — we'll dig into loops properly in Step 2.
# For now, just know it runs the indented block once per item it finds.

print("\n── Session Summary ──────────────────────────────────────────────────")

for session in activity.get_messages("session"):
    # Each message has fields. We fetch a field's value by name with get_value().
    total_seconds = session.get_value("total_elapsed_time")   # float, in seconds
    total_km      = session.get_value("total_distance") / 1000  # convert m → km
    avg_hr        = session.get_value("avg_heart_rate")
    max_hr        = session.get_value("max_heart_rate")
    ascent_m      = session.get_value("total_ascent")

    # CONCEPT: arithmetic
    # Python uses standard operators: + - * / // (floor divide) % (modulo) ** (power)
    total_hours   = total_seconds / 3600          # seconds ÷ 3600 = hours
    total_minutes = (total_seconds % 3600) / 60   # remaining seconds → minutes

    # CONCEPT: round()
    # round(value, decimal_places) rounds a float to the given number of decimals.
    total_km_rounded = round(total_km, 2)

    print(f"  Sport         : {session.get_value('sport')} / {session.get_value('sub_sport')}")
    print(f"  Total time    : {int(total_hours)}h {int(total_minutes)}m")
    print(f"  Total distance: {total_km_rounded} km")
    print(f"  Avg heart rate: {avg_hr} bpm")
    print(f"  Max heart rate: {max_hr} bpm")
    print(f"  Total ascent  : {ascent_m} m")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — Lists, Dictionaries, Loops, and Conditionals
# ─────────────────────────────────────────────────────────────────────────────
#
# In your exploration above you already used several of these — a `set`, a
# `for` loop, `if/elif`, and the `+=` operator. Let's formalise them and
# introduce two more essential structures: list and dict.
#
#
# CONCEPT: list
# An ordered, growable sequence of values. Created with square brackets [].
# You add items with .append(). Access items by position (index) starting at 0.

print(f"\n--------------------------------------------------------------------")
fruits = ["apple", "banana", "cherry"]
fruits.append("date")          # add an item to the end
print(fruits[0])               # "apple"  — first item
print(fruits[-1])              # "date"   — last item (negative index counts from end)
print(len(fruits))             # 4        — how many items


# CONCEPT: dict  (dictionary)
# A collection of key → value pairs. Created with curly braces {}.
# Look up a value instantly by its key — no need to loop through everything.
# Keys are usually strings; values can be anything.

runner = {
    "name":     "Jorge",
    "race":     "SDW100 2026",
    "distance": 160.0,
}
print(runner["name"])          # "Jorge"
runner["dnf"] = True           # add a new key after creation
print(runner)


# ── Replacing 9 counter variables with one dict ───────────────────────────────
#
# Above you wrote 9 separate counter variables (countRecord, countLap, …).
# A dict is the natural tool for this — one variable, any number of keys.
# dict.get(key, default) returns the value for the key, or `default` if missing.

print("\n── Message type counts (dict version) ───────────────────────────────")

msg_counts = {}                                    # start with an empty dict

for msg in activity.get_messages():
    name = msg.name                                # e.g. "record", "lap", "session"
    msg_counts[name] = msg_counts.get(name, 0) + 1  # increment, starting from 0

for name, count in msg_counts.items():             # .items() gives (key, value) pairs
    print(f"  {name:22s} {count:6d}")


# CONCEPT: if / elif / else
# Runs different code depending on a condition.
# Conditions use ==, !=, <, >, <=, >=, and, or, not.
# Only the FIRST matching branch runs; the rest are skipped.

total_msgs = sum(msg_counts.values())              # sum() adds all values in the dict

if total_msgs > 100_000:
    print(f"\n  Large file: {total_msgs:,} messages")
elif total_msgs > 10_000:
    print(f"\n  Medium file: {total_msgs:,} messages")
else:
    print(f"\n  Small file: {total_msgs:,} messages")


# ── Collecting all data points into a list of dicts ───────────────────────────
#
# Each "record" message is one GPS/sensor snapshot — roughly every second.
# We'll collect them all into a list where each item is a dict with three keys.
# This is the raw data that all future analysis will work from.

print("\n── Loading all data points ───────────────────────────────────────────")

data_points = []                                   # start with an empty list

for msg in activity.get_messages("record"):
    timestamp = msg.get_value("timestamp")         # datetime object
    heart_rate = msg.get_value("heart_rate")       # int, bpm  (may be None if missing)
    distance = msg.get_value("distance")           # float, metres

    # CONCEPT: None
    # Python uses None to mean "no value". Sensor dropouts produce None here.
    # We skip records where heart rate or distance is missing.
    if heart_rate is None or distance is None:
        continue                                   # `continue` skips to the next loop iteration

    point = {
        "timestamp":  timestamp,
        "heart_rate": heart_rate,
        "distance_km": round(distance / 1000, 3), # convert metres → km
    }
    data_points.append(point)                      # add this point to our list

print(f"  Data points loaded : {len(data_points):,}")
print(f"  First point        : {data_points[0]}")
print(f"  Last point         : {data_points[-1]}")


# ── Basic stats straight from the list ────────────────────────────────────────
#
# CONCEPT: list comprehension  [expression for item in list]
# A compact way to build a new list by transforming or filtering an existing one.
# Read it as: "give me heart_rate for each point in data_points".

heart_rates = [p["heart_rate"] for p in data_points]

print(f"\n── Heart rate stats ─────────────────────────────────────────────────")
print(f"  Min HR : {min(heart_rates)} bpm")
print(f"  Max HR : {max(heart_rates)} bpm")
print(f"  Avg HR : {round(sum(heart_rates) / len(heart_rates), 1)} bpm")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Functions
# ─────────────────────────────────────────────────────────────────────────────
#
# CONCEPT: function
# A function is a named, reusable block of code. You define it once with `def`,
# then call it by name as many times as you like.
#
# Anatomy:
#   def function_name(parameter1, parameter2):
#       # body — indented
#       return result
#
# `parameters` are the inputs the function expects.
# `return` sends a value back to whoever called the function.
# A function without `return` gives back None implicitly.
#
# WHY bother? Right now our parsing code is written once for SDW100_2026.fit.
# To load the other two files we'd have to copy-paste everything.
# Functions let us write the logic once and call it three times — one per file.


# ── Function 1: parse the session summary from a FIT file ────────────────────
#
# This replaces the session loop we wrote in Step 1.
# It takes a `FitFile` object as input and returns a dict of summary values.

def parse_session(activity):
    """Return a dict with the key summary fields from the session message."""
    for session in activity.get_messages("session"):
        total_seconds = session.get_value("total_elapsed_time")
        return {
            "sport":       session.get_value("sport"),
            "sub_sport":   session.get_value("sub_sport"),
            "total_hours": round(total_seconds / 3600, 2),
            "total_km":    round(session.get_value("total_distance") / 1000, 2),
            "avg_hr":      session.get_value("avg_heart_rate"),
            "max_hr":      session.get_value("max_heart_rate"),
            "total_ascent":session.get_value("total_ascent"),
        }
    raise ValueError(f"No session message found — file may be corrupt or incomplete")


# ── Function 2: parse all data points from a FIT file ────────────────────────
#
# This wraps the record-reading loop from Step 2.
# Notice the parameter has a default value: check_fields=None.
# That means you can call it without passing check_fields — it'll use None.

def parse_records(activity, check_fields=None):
    """
    Return a list of dicts, one per valid record message.
    check_fields: list of field names that must be non-None to include the record.
                  Defaults to ["distance"] — heart_rate is optional (not all
                  devices record HR, e.g. OMD100 2026).
    """
    # CONCEPT: default mutable argument trap
    # Never write `check_fields=[]` as a default — Python creates that list once
    # and shares it across all calls. Use None and set the default inside:
    if check_fields is None:
        check_fields = ["distance"]

    points = []
    for msg in activity.get_messages("record"):
        values = {field.name: field.value for field in msg.fields}

        # CONCEPT: any() + generator expression
        # any(condition for item in iterable) returns True if ANY item matches.
        # Here: skip this record if ANY required field is missing.
        if any(values.get(f) is None for f in check_fields):
            continue

        points.append({
            "timestamp":   values["timestamp"],
            "heart_rate":  values.get("heart_rate"),   # None if not recorded
            "distance_km": round(values["distance"] / 1000, 3),
        })
    return points


# ── Function 3: load a FIT file and return everything we need ─────────────────
#
# This is the public-facing function — the one callers will actually use.
# It calls the two helpers above and bundles the results into one dict.
#
# CONCEPT: type hints  (the `str` and `->` in the signature)
# Python doesn't enforce these at runtime, but they tell readers (and VS Code)
# what type the parameter expects and what the function returns.

def load_fit_file(path: str) -> dict:
    """Load a .fit file and return {"session": {...}, "records": [...]}."""
    activity = fitparse.FitFile(path)
    return {
        "session": parse_session(activity),
        "records": parse_records(activity),
    }


# ── Use the functions to load all three races ─────────────────────────────────

print("\n── Step 3: loading all three FIT files via functions ────────────────")

FIT_FILES = {
    "SDW100 2025": "../dataSources/racesFIT/SDW100_2025.fit",
    "SDW100 2026": "../dataSources/racesFIT/SDW100_2026.fit",
    "OMD100 2026": "../dataSources/racesFIT/OMD100_2026.fit",
}

# CONCEPT: dict of dicts
# The value stored under each key is itself a dict returned by load_fit_file().
races = {}
for name, path in FIT_FILES.items():
    races[name] = load_fit_file(path)
    print(f"  Loaded: {name}")

# ── Print a comparison table ──────────────────────────────────────────────────

# CONCEPT: conditional expression  (ternary operator)
# A compact if/else that fits on one line:
#   value_if_true  if  condition  else  value_if_false
# Used below to display "N/A" when avg_hr is None instead of crashing.

print(f"\n  {'Race':<14}  {'Time':>8}  {'Dist km':>8}  {'Avg HR':>9}  {'Ascent':>7}  {'Points':>7}")
print(f"  {'-'*14}  {'-'*8}  {'-'*8}  {'-'*9}  {'-'*7}  {'-'*7}")

for name, data in races.items():
    s   = data["session"]
    h   = int(s["total_hours"])
    m   = int((s["total_hours"] - h) * 60)
    hr  = f"{s['avg_hr']} bpm" if s["avg_hr"] is not None else "N/A"
    print(
        f"  {name:<14}  {h}h {m:02d}m  "
        f"{s['total_km']:>8.2f}  "
        f"{hr:>9}  "
        f"{s['total_ascent']:>5} m  "
        f"{len(data['records']):>7,}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — pandas DataFrames
# ─────────────────────────────────────────────────────────────────────────────
#
# CONCEPT: DataFrame
# A DataFrame is a table — rows and columns, like a spreadsheet or SQL table.
# It's the core data structure in pandas, and the foundation of data science
# in Python. Every row is one observation; every column is one variable.
#
# We import pandas with the alias `pd` — this is a universal convention.
# You'll see `pd.something` everywhere in data science code.

import pandas as pd

print("\n── Step 4: pandas DataFrames ─────────────────────────────────────────")


# ── Quick look at the raw data ─────────────────────────────────────────────────
#
# Build one DataFrame to illustrate the three basic inspection tools.
# We'll generalise to all three races once we've defined a helper function.

raw_df = pd.DataFrame(races["SDW100 2026"]["records"])

# CONCEPT: .shape, .dtypes, .head()
# These are your first three instincts whenever you load new data.
#   .shape   → (rows, columns) — how big is it?
#   .dtypes  → the data type of each column
#   .head(n) → print the first n rows (default 5)

print(f"\n  Shape  : {raw_df.shape[0]:,} rows × {raw_df.shape[1]} columns")
print(f"\n  Column types:\n{raw_df.dtypes}")
print(f"\n  First 3 rows:\n{raw_df.head(3)}")


# ── build_race_df() — enriches one race's records into a full DataFrame ────────
#
# CONCEPT: derived columns
# You create a new column by assigning to df["new_col"].
# The expression on the right operates on the whole column at once —
# no loop needed. This is called "vectorised" operation and is very fast.
#
# CONCEPT: .iloc[n]
# Integer Location — access a row by its position number (0 = first, -1 = last).
# Different from .loc which uses the index label.
#
# CONCEPT: .diff()
# Returns the difference between each row and the row before it.
# Row 0 becomes NaN (nothing to subtract from).
# df["distance_km"].diff() gives the km added in each 1-second step.
#
# CONCEPT: .rolling(window)
# Computes a statistic over a sliding window of N consecutive rows.
# .sum() on a rolling window adds up the last N values at each row.
# min_periods=30 means: only compute if at least 30 rows exist in the window
# (avoids unreliable values at the very start of the data).
#
# WHY rolling and not per-second pace?  Two problems at 1-second resolution:
# 1. FILTERING BIAS — 42% of rows have dist_step = 0 (stopped at aid stations,
#    GPS not updating). Dividing by 0 → infinity → filtered out, removing all
#    stopped time and making stats look far faster than reality.
# 2. GPS QUANTIZATION — distance stored in 1-metre increments. At ~3 m/s you
#    always get exactly 0.003 km/step → always 5.56 min/km regardless of actual
#    speed. Fix: sum 60 seconds of distance AND time before dividing. Stopped
#    seconds dilute the fast seconds; quantization noise averages out.

PACE_WINDOW = 60   # seconds


def build_race_df(records, pace_window=PACE_WINDOW):
    """Convert a list of record dicts into an enriched DataFrame.

    Adds elapsed_hours and pace_min_km (60-second rolling window).
    """
    df = pd.DataFrame(records)

    start = df["timestamp"].iloc[0]        # .iloc[0] = first row by position

    df["elapsed_hours"] = (
        (df["timestamp"] - start)
        .dt.total_seconds()                # timedelta → seconds
        / 3600                             # seconds → hours
    )

    df["dist_step_km"]  = df["distance_km"].diff()
    df["time_step_min"] = df["elapsed_hours"].diff() * 60

    df["dist_60s"]    = df["dist_step_km"].rolling(window=pace_window, min_periods=30).sum()
    df["time_60s"]    = df["time_step_min"].rolling(window=pace_window, min_periods=30).sum()
    df["pace_min_km"] = df["time_60s"] / df["dist_60s"]

    # CONCEPT: boolean mask + .loc
    # A boolean mask is a column of True/False values.
    # df.loc[mask, "col"] = value  sets that column only where mask is True.
    # NaN = "not a number" — pandas' way to represent missing numeric values.
    bad_pace = df["pace_min_km"] > 60
    df.loc[bad_pace, "pace_min_km"] = float("nan")

    return df


# ── HR zone constants and hr_zone_summary() function ──────────────────────────
#
# CONCEPT: pd.cut()
# Bins a continuous numeric column into labelled categories.
# bins=[0,100,120,...] defines the bucket edges; labels= names each bucket.
#
# CONCEPT: .groupby().agg()
# groupby splits the DataFrame into groups by a column's value, then agg
# computes a summary statistic for each group.
# Think of it as: "for each HR zone, calculate the mean pace and total time."
#
# CONCEPT: .assign(lambda df: ...)
# Adds or overwrites a column using a function of the current DataFrame.
# Useful for chaining — you can reference a column you just created in the
# same chain without breaking it into separate statements.

HR_BINS   = [0, 100, 120, 140, 160, 220]
HR_LABELS = ["Zone 1\n(<100)", "Zone 2\n(100–120)",
             "Zone 3\n(120–140)", "Zone 4\n(140–160)", "Zone 5\n(160+)"]


def hr_zone_summary(df):
    """Return a per-HR-zone summary table, or None if the race has no HR data."""
    if df["heart_rate"].isna().all():
        return None

    return (
        df
        .assign(hr_zone=pd.cut(df["heart_rate"], bins=HR_BINS, labels=HR_LABELS))
        .groupby("hr_zone", observed=True)
        .agg(
            time_hours = ("elapsed_hours", "count"),
            avg_pace   = ("pace_min_km",   "mean"),
            avg_hr     = ("heart_rate",    "mean"),
        )
        .assign(time_hours=lambda d: (d["time_hours"] / 3600).round(2))
        .round(2)
    )


# ── Run the pipeline on all three races ───────────────────────────────────────
#
# CONCEPT: storing DataFrames in a dict
# Just as we stored session summaries in a dict, we can store DataFrames.
# This lets us loop over all races without repeating code.

print(f"\n  Building DataFrames for all races...")

dfs = {}
for name, data in races.items():
    df = build_race_df(data["records"])
    df["race"] = name
    dfs[name] = df

    # CONCEPT: .describe()
    # One method gives you count, mean, std, min, 25/50/75th percentile, max
    # for every numeric column. Essential first look at any dataset.
    print(f"\n  ── {name} ({df.shape[0]:,} rows) ──────────────────────────────")
    print(df[["heart_rate", "pace_min_km", "elapsed_hours"]].describe().round(2))

    summary = hr_zone_summary(df)
    if summary is not None:
        print(f"\n  Time and pace by HR zone:")
        print(summary)
    else:
        print(f"\n  No HR data — skipping zone summary.")


# ── Combine all races into one DataFrame ──────────────────────────────────────
#
# CONCEPT: pd.concat()
# Stacks multiple DataFrames on top of each other into one.
# ignore_index=True gives the combined DataFrame fresh row numbers.

all_races = pd.concat(dfs.values(), ignore_index=True)
print(f"\n  Combined DataFrame: {all_races.shape[0]:,} rows")

print(f"\n  Median pace (min/km) per race:")
print(
    all_races
    .groupby("race")["pace_min_km"]
    .median()
    .round(2)
)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Visualisation with matplotlib
# ─────────────────────────────────────────────────────────────────────────────
#
# CONCEPT: matplotlib
# matplotlib is Python's foundational plotting library.
# pyplot is its interactive interface — you build plots step by step and either
# show them on screen or save them to a file.
# `plt` is the universal alias, used everywhere in data science code.
#
# Install: uv pip install matplotlib --python .venv/bin/python3

import matplotlib.pyplot as plt
from pathlib import Path

# CONCEPT: pathlib.Path
# A clean, cross-platform way to work with filesystem paths.
# Path("output") creates a path object representing the "output/" directory.
# .mkdir(parents=True, exist_ok=True) creates it if it doesn't already exist,
# without erroring if it does.

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("\n── Step 5: Visualisation ─────────────────────────────────────────────")

# Consistent colours so the same race always gets the same colour across charts.
RACE_COLOURS = {
    "SDW100 2025": "steelblue",
    "SDW100 2026": "crimson",
    "OMD100 2026": "darkorange",
}


# ── plot_race() — per-race HR + pace chart ────────────────────────────────────
#
# CONCEPT: plt.subplots(nrows, ncols, figsize, sharex)
# Returns two objects:
#   fig          — the overall canvas (the "sheet of paper")
#   ax (or axes) — the individual subplot area(s) drawn on that sheet
#
# When called with nrows=2 it returns a tuple of two Axes — we unpack with (a, b).
# When called without nrows/ncols (default = one subplot) it returns a single Axes.
# We pick between the two layouts based on whether the race has HR data.
#
# figsize=(width, height) in inches.
# sharex=True links the x-axis on all subplots — scrolling one scrolls both.

def plot_race(name, df, out_dir):
    """Save a per-race chart: HR (if available) + pace over elapsed time.

    Races without HR data (e.g. OMD100) get a pace-only single-panel chart.
    Returns the path to the saved file.
    """
    colour = RACE_COLOURS.get(name, "slategray")
    has_hr = df["heart_rate"].notna().any()

    if has_hr:
        fig, (ax_hr, ax_pace) = plt.subplots(
            nrows=2, ncols=1, figsize=(14, 8), sharex=True
        )
    else:
        fig, ax_pace = plt.subplots(figsize=(14, 4))

    # CONCEPT: fig.suptitle()
    # Sets one title for the whole figure, sitting above all subplots.
    title_suffix = "Heart Rate and Pace" if has_hr else "Pace"
    fig.suptitle(f"{name} — {title_suffix}", fontsize=14)

    if has_hr:
        # CONCEPT: ax.plot(x, y, ...) — draw a line connecting (x, y) points.
        #   color     — CSS colour name or hex (e.g. "#e63946")
        #   linewidth — thickness in points; 0.6 is thin, 2.0 is thick
        #   alpha     — opacity (0 = invisible, 1 = fully opaque)
        #               use < 1 when data is dense so overlapping lines stay visible
        ax_hr.plot(
            df["elapsed_hours"],
            df["heart_rate"],
            color=colour,
            linewidth=0.6,
            alpha=0.7,
        )
        ax_hr.set_ylabel("Heart rate (bpm)")
        ax_hr.set_title("Heart rate", loc="left", fontsize=10)

    # Smooth pace over 5 minutes (300 rows ≈ 300 seconds) for cleaner visuals.
    # The 60-second window in build_race_df was for accurate stats; this wider
    # pass makes the chart readable without distorting the shape.
    smooth_pace = df["pace_min_km"].rolling(300, min_periods=60).mean()

    ax_pace.plot(
        df["elapsed_hours"],
        smooth_pace,
        color=colour,
        linewidth=1.0,
    )
    ax_pace.set_ylabel("Pace (min/km)")
    ax_pace.set_xlabel("Elapsed time (hours)")
    ax_pace.set_title("Pace (5-min rolling average)", loc="left", fontsize=10)

    # CONCEPT: ax.invert_yaxis()
    # For pace, lower number = faster. Inverting puts "fast" at the top —
    # the same convention used by Garmin, Strava, and every running watch.
    ax_pace.invert_yaxis()

    # CONCEPT: plt.tight_layout()
    # Adjusts margins so axis labels don't overlap subplots.
    plt.tight_layout()

    # CONCEPT: plt.savefig(path, dpi=...)
    # Saves the figure to disk. dpi controls resolution (150 = sharp on screen).
    out_path = out_dir / (name.replace(" ", "_") + "_hr_pace.png")
    plt.savefig(out_path, dpi=150)

    # CONCEPT: plt.close()
    # Releases the figure from memory. Always call after saving — otherwise
    # matplotlib accumulates open figures and eventually runs out of memory.
    plt.close()
    return out_path


# ── Generate one chart per race ───────────────────────────────────────────────

for name, df in dfs.items():
    out_path = plot_race(name, df, OUTPUT_DIR)
    print(f"  Saved: {out_path}")


# ── Combined chart: all races — pace over distance ────────────────────────────
#
# CONCEPT: plotting multiple series on one Axes
# Call ax.plot() once per series — each call adds another line to the same chart.
# The `label=` keyword names the line; ax.legend() draws the legend automatically
# using all the labels you assigned.

fig, ax = plt.subplots(figsize=(14, 6))
fig.suptitle("Pace comparison — all three races", fontsize=14)

for name, df in dfs.items():
    smooth = df["pace_min_km"].rolling(300, min_periods=60).mean()
    ax.plot(
        df["distance_km"],
        smooth,
        label=name,
        color=RACE_COLOURS.get(name, "slategray"),
        linewidth=1.0,
        alpha=0.85,
    )

ax.set_xlabel("Distance (km)")
ax.set_ylabel("Pace (min/km)")
ax.set_title("5-minute rolling pace — lower is faster", loc="left", fontsize=10)
ax.invert_yaxis()

# CONCEPT: ax.legend(loc=...)
# Draws a legend using the label= values set on each plot() call.
# loc="best" lets matplotlib find the least-cluttered position automatically.
ax.legend(loc="best")

plt.tight_layout()

out_path = OUTPUT_DIR / "all_races_pace.png"
plt.savefig(out_path, dpi=150)
print(f"  Saved: {out_path}")
plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Machine Learning with scikit-learn
# ─────────────────────────────────────────────────────────────────────────────
#
# CONCEPT: supervised ML workflow
# Almost every supervised problem follows the same six steps:
#
#   1. Define X (features) and y (target)
#   2. Split into train and test sets
#   3. Scale features
#   4. Fit a model on the training set
#   5. Predict on the test set
#   6. Evaluate: how far off are the predictions?
#
# Our first problem: given heart rate and race position (elapsed time,
# distance covered), can we predict pace?
#
# This is a genuine physical question — higher HR late in a race usually
# means you're working hard just to hold a pace that would have felt easy
# at the start. Terrain (uphills/downhills) complicates it, but the
# average signal should be learnable.

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

print("\n── Step 6: Machine Learning ──────────────────────────────────────────")


# ── 1. Build the feature matrix X and target vector y ────────────────────────
#
# CONCEPT: X and y
# X is the feature matrix — a 2D table of inputs, shape (n_samples, n_features).
# y is the target vector — a 1D array of what we want to predict, shape (n_samples,).
# Every row of X has a corresponding value in y.
#
# We use both SDW100 races because they have HR data.
# OMD100 has no HR, so we exclude it from this model.

FEATURES = ["heart_rate", "elapsed_hours", "distance_km"]
TARGET   = "pace_min_km"

sdw_df = pd.concat(
    [df for name, df in dfs.items() if "SDW100" in name],
    ignore_index=True,
)

# Drop any row where a feature or the target is NaN.
# NaN in X or y will crash most sklearn models.
ml_df = sdw_df[FEATURES + [TARGET]].dropna()

print(f"\n  Rows available : {len(ml_df):,}")
print(f"  Features       : {FEATURES}")
print(f"  Target         : {TARGET}")

X = ml_df[FEATURES]
y = ml_df[TARGET]


# ── 2. Train / test split ─────────────────────────────────────────────────────
#
# CONCEPT: train_test_split
# We never evaluate a model on the data it was trained on — that would be
# like marking your own exam. We hold back 20% of rows as the "test set"
# to measure how the model performs on data it has never seen.
#
# test_size=0.2   → 20% test, 80% train
# random_state=42 → seeds the shuffle so the split is reproducible;
#                   anyone who runs this code gets the exact same rows

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\n  Train rows : {len(X_train):,}")
print(f"  Test rows  : {len(X_test):,}")


# ── 3. Feature scaling ────────────────────────────────────────────────────────
#
# CONCEPT: StandardScaler
# Our three features live on very different numeric scales:
#   heart_rate    → roughly 60–200
#   elapsed_hours → 0–22
#   distance_km   → 0–127
#
# Linear models sum weighted features. Without scaling, a large-range feature
# can dominate even if it's less informative. StandardScaler shifts every
# feature to mean=0, std=1 so they're all on equal footing.
# It also makes the learned coefficients directly comparable — a larger
# absolute coefficient means that feature matters more.
#
# Critical rule — fit on TRAIN, transform BOTH:
#   scaler.fit_transform(X_train) — learn mean/std from training data, then apply
#   scaler.transform(X_test)      — apply the SAME scaling, don't re-learn
#
# Fitting on the test set would "leak" test information into the pipeline
# and give over-optimistic evaluation scores.

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)

print(f"\n  Feature means learned from training data: {scaler.mean_.round(1)}")
print(f"  (After applying the scaler these all become 0)")


# ── 4. Train the model ────────────────────────────────────────────────────────
#
# CONCEPT: LinearRegression
# The simplest regression model. It learns one weight (coefficient) per feature
# plus a bias (intercept), so the prediction is:
#
#   predicted_pace = w₁·heart_rate + w₂·elapsed_hours + w₃·distance_km + b
#
# "Training" finds the weights that minimise the mean squared error between
# predictions and reality. For linear regression this is a single matrix
# operation — not iterative — so it's near-instant even on 100 k rows.
#
# .fit(X, y) does all of this in one call.

model = LinearRegression()
model.fit(X_train_scaled, y_train)

print(f"\n  Intercept (baseline pace at avg features): {model.intercept_:.2f} min/km")
print(f"\n  Feature coefficients (after scaling — bigger abs value = more influence):")
for feat, coef in zip(FEATURES, model.coef_):
    arrow = "↑ slower" if coef > 0 else "↓ faster"
    print(f"    {feat:<18}: {coef:+.3f}  ({arrow})")


# ── 5 & 6. Predict and evaluate ───────────────────────────────────────────────
#
# CONCEPT: MAE — Mean Absolute Error
# Average absolute difference between prediction and reality, in the same
# units as the target (min/km).
# MAE = 2.5 means: on average, the model is off by 2.5 min/km.
#
# CONCEPT: R² — coefficient of determination
# Fraction of the target's variance that the model explains.
#   R² = 1.0 → perfect predictions
#   R² = 0.0 → no better than always predicting the mean
#   R² < 0.0 → actively worse than predicting the mean
#
# A linear model can only capture straight-line relationships. Trail pace
# depends on terrain in a non-linear way (uphills slow you down more than
# downhills speed you up), so R² will be meaningful but not close to 1.
# That sets up the motivation for non-linear models in a later step.

y_pred = model.predict(X_test_scaled)

mae = mean_absolute_error(y_test, y_pred)
r2  = r2_score(y_test, y_pred)

print(f"\n  Test MAE : {mae:.2f} min/km")
print(f"  Test R²  : {r2:.3f}")


# ── Visualise results ─────────────────────────────────────────────────────────
#
# Left panel: actual vs predicted scatter.
#   A perfect model puts every point on the diagonal y=x line.
#   Spread away from the diagonal shows where the model struggles.
#
# Right panel: coefficient bar chart.
#   Positive (red) → that feature predicts slower pace.
#   Negative (blue) → that feature predicts faster pace.
#
# We sample 5 000 rows so the scatter isn't too dense to read.

rng    = np.random.default_rng(42)
sample = rng.integers(0, len(y_test), size=5_000)

y_test_arr = y_test.to_numpy()

fig, (ax_scatter, ax_coef) = plt.subplots(ncols=2, figsize=(14, 6))
fig.suptitle("Step 6: Linear Regression — Pace Prediction", fontsize=14)

ax_scatter.scatter(
    y_test_arr[sample],
    y_pred[sample],
    alpha=0.15,
    s=5,
    color="steelblue",
)
lims = [y_test_arr.min(), min(y_test_arr.max(), 40)]
ax_scatter.plot(lims, lims, color="crimson", linewidth=1.2, label="perfect prediction")
ax_scatter.set_xlabel("Actual pace (min/km)")
ax_scatter.set_ylabel("Predicted pace (min/km)")
ax_scatter.set_title(
    f"Actual vs Predicted  (MAE = {mae:.2f} min/km,  R² = {r2:.3f})",
    loc="left", fontsize=10,
)
ax_scatter.legend()

coef_colours = ["crimson" if c > 0 else "steelblue" for c in model.coef_]
ax_coef.barh(FEATURES, model.coef_, color=coef_colours)
ax_coef.axvline(0, color="black", linewidth=0.8)
ax_coef.set_xlabel("Coefficient (scaled units)")
ax_coef.set_title("Feature weights — red = slower, blue = faster", loc="left", fontsize=10)

plt.tight_layout()
out_path = OUTPUT_DIR / "step6_pace_prediction.png"
plt.savefig(out_path, dpi=150)
print(f"\n  Saved: {out_path}")
plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — Feature Engineering and Random Forest
# ─────────────────────────────────────────────────────────────────────────────
#
# Two improvements over Step 6:
#
#   1. Feature engineering — derive race_progress (0→1) from distance.
#      A model that sees race_progress=0.9 knows "this runner is deep in the race"
#      regardless of whether the total is 125 km or 171 km.
#
#   2. RandomForestRegressor — an ensemble model that handles non-linear
#      interactions between features.
#
# The key limitation of Step 6's linear model:
# "HR=150 at km 5" and "HR=150 at km 120" produce the exact same pace
# prediction. That's wrong — at km 120 your legs are shredded and the same
# HR effort yields a much slower speed. A Random Forest can learn rules like:
#   IF race_progress > 0.85 AND heart_rate > 130 THEN pace ≈ 14.3 min/km
# Linear regression fundamentally cannot represent that kind of condition.

from sklearn.ensemble import RandomForestRegressor

print("\n── Step 7: Feature Engineering and Random Forest ────────────────────")


# ── Feature engineering: race_progress ────────────────────────────────────────
#
# CONCEPT: feature engineering
# Raw values are not always the most informative form you can give a model.
# Derived features that encode domain knowledge often matter more than the
# choice of model.
#
# race_progress = distance_km / max_distance_km for that race → range [0, 1].
# We compute it per-race before concatenating so each race normalises to its
# own finish line, not a shared one.

def add_features(df):
    """Add engineered features to a single race DataFrame."""
    df = df.copy()
    df["race_progress"] = df["distance_km"] / df["distance_km"].max()
    return df


sdw_enhanced = pd.concat(
    [add_features(df) for name, df in dfs.items() if "SDW100" in name],
    ignore_index=True,
)

FEATURES_V2 = ["heart_rate", "elapsed_hours", "distance_km", "race_progress"]

ml_df2 = sdw_enhanced[FEATURES_V2 + [TARGET]].dropna()
X2     = ml_df2[FEATURES_V2]
y2     = ml_df2[TARGET]

X2_train, X2_test, y2_train, y2_test = train_test_split(
    X2, y2, test_size=0.2, random_state=42
)

scaler2    = StandardScaler()
X2_train_sc = scaler2.fit_transform(X2_train)
X2_test_sc  = scaler2.transform(X2_test)


# ── Linear baseline with new features ─────────────────────────────────────────
#
# Re-run linear regression with the same 4-feature dataset so the comparison
# with Random Forest is fair (same rows, same split).

lr2 = LinearRegression()
lr2.fit(X2_train_sc, y2_train)
lr2_pred = lr2.predict(X2_test_sc)
lr2_mae  = mean_absolute_error(y2_test, lr2_pred)
lr2_r2   = r2_score(y2_test, lr2_pred)


# ── Random Forest ──────────────────────────────────────────────────────────────
#
# CONCEPT: RandomForestRegressor
# A Random Forest is an ensemble — a committee — of decision trees.
# Each tree is trained on a different random sample of the rows, and at every
# split it considers only a random subset of features. This forces trees to be
# different from each other.
#
# When we predict, we average all 100 trees. Because each tree makes different
# errors, those errors partially cancel — the "wisdom of crowds" effect.
# This averaging is why ensembles almost always outperform a single model.
#
# Unlike linear regression, a single decision tree splits on conditions:
#   IF race_progress > 0.85 AND heart_rate > 130 → predict 14.3 min/km
# With 100 such trees combined, the forest captures non-linear patterns that
# no weighted sum of features can express.
#
# Key parameters:
#   n_estimators=100  → number of trees (more = more stable, but slower)
#   n_jobs=-1         → use all CPU cores to build trees in parallel
#   random_state=42   → reproducibility

rf = RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42)

print(f"\n  Training Random Forest on {len(X2_train):,} rows… ", end="", flush=True)
rf.fit(X2_train_sc, y2_train)
print("done.")

rf_preds = rf.predict(X2_test_sc)
rf_mae   = mean_absolute_error(y2_test, rf_preds)
rf_r2    = r2_score(y2_test, rf_preds)


# ── Compare all three models (random split) ───────────────────────────────────
#
# MAE (Mean Absolute Error): lower is better. Measured in min/km.
# R²: higher is better. 0 = no better than predicting the mean, 1 = perfect.
#
# CONCEPT: temporal data leakage
# GPS records are 1 second apart. Consecutive rows have nearly identical pace
# values. A random 80/20 split puts row 3601 in the test set while rows 3600
# and 3602 (almost identical) land in training. The Random Forest sees a
# "test" row whose direct neighbours it already trained on — making the problem
# trivially easy and the R² look far better than it really is.
# This is called temporal autocorrelation leakage.

print(f"\n  Random split (optimistic — neighbouring rows bleed between sets):")
print(f"  {'Model':<32}  {'MAE (min/km)':>12}  {'R²':>8}")
print(f"  {'-'*56}")
print(f"  {'Step 6 — Linear, 3 features':<32}  {mae:>12.2f}  {r2:>8.3f}")
print(f"  {'Linear, 4 features':<32}  {lr2_mae:>12.2f}  {lr2_r2:>8.3f}")
print(f"  {'Random Forest, 4 features':<32}  {rf_mae:>12.2f}  {rf_r2:>8.3f}")


# ── Honest evaluation: train on 2025, test on 2026 ────────────────────────────
#
# CONCEPT: proper train/test split for time-series data
# The clean solution: train on one complete race, test on a different one.
# The model has never seen any second of the test race — no temporal leakage.
# This measures whether what it learned from 2025 generalises to 2026.

sdw25_feat = add_features(dfs["SDW100 2025"])[FEATURES_V2 + [TARGET]].dropna()
sdw26_feat = add_features(dfs["SDW100 2026"])[FEATURES_V2 + [TARGET]].dropna()

X_25 = sdw25_feat[FEATURES_V2]
y_25 = sdw25_feat[TARGET]
X_26 = sdw26_feat[FEATURES_V2]
y_26 = sdw26_feat[TARGET]

scaler_cv  = StandardScaler()
X_25_sc    = scaler_cv.fit_transform(X_25)   # fit on 2025 only
X_26_sc    = scaler_cv.transform(X_26)        # apply same scaling to 2026

rf_cv = RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42)
rf_cv.fit(X_25_sc, y_25)
y_26_pred  = rf_cv.predict(X_26_sc)

cv_mae = mean_absolute_error(y_26, y_26_pred)
cv_r2  = r2_score(y_26, y_26_pred)

lr_cv = LinearRegression()
lr_cv.fit(X_25_sc, y_25)
y_26_pred_lr = lr_cv.predict(X_26_sc)
cv_lr_mae = mean_absolute_error(y_26, y_26_pred_lr)
cv_lr_r2  = r2_score(y_26, y_26_pred_lr)

print(f"\n  Cross-race split: train=SDW100 2025, test=SDW100 2026 (honest):")
print(f"  {'Model':<32}  {'MAE (min/km)':>12}  {'R²':>8}")
print(f"  {'-'*56}")
print(f"  {'Linear, 4 features':<32}  {cv_lr_mae:>12.2f}  {cv_lr_r2:>8.3f}")
print(f"  {'Random Forest, 4 features':<32}  {cv_mae:>12.2f}  {cv_r2:>8.3f}")


# ── Feature importance ─────────────────────────────────────────────────────────
#
# CONCEPT: feature_importances_
# After training, rf.feature_importances_ holds a score for each feature —
# how much of the model's total predictive power came from that feature.
# The scores sum to 1.
#
# This is different from linear coefficients:
#   Linear coef   → "if this feature increases by 1 std, pace changes by X min/km"
#   RF importance → "what fraction of the model's decisions relied on this feature"
#
# We use rf_cv (trained on 2025 only) so the importances come from the honest
# model — the one that had to generalise, not just memorise.

importances = rf_cv.feature_importances_
sorted_idx  = importances.argsort()   # ascending for a horizontal bar chart

print(f"\n  Feature importances (RF trained on 2025):")
for i in sorted_idx[::-1]:
    print(f"    {FEATURES_V2[i]:<18}: {importances[i]:.3f}")


# ── Visualise ─────────────────────────────────────────────────────────────────
#
# Left:  feature importance from the honest (cross-race) model
# Right: actual vs predicted for SDW100 2026 — the race the model never saw.
#        A perfect model would put all points on the diagonal y=x line.
#        The spread here reflects the true generalisation gap.

fig, (ax_imp, ax_pred) = plt.subplots(ncols=2, figsize=(14, 6))
fig.suptitle("Step 7: Random Forest — honest cross-race evaluation", fontsize=14)

ax_imp.barh(
    [FEATURES_V2[i] for i in sorted_idx],
    importances[sorted_idx],
    color="darkorange",
)
ax_imp.set_xlabel("Importance (fraction of total)")
ax_imp.set_title("Feature importance (trained on 2025)", loc="left", fontsize=10)

# Scatter: predictions on 2026 (data the model never saw during training)
rng    = np.random.default_rng(42)
sample = rng.integers(0, len(y_26), size=5_000)
y_26_arr = y_26.to_numpy()

ax_pred.scatter(y_26_arr[sample], y_26_pred[sample], alpha=0.15, s=5, color="darkorange")
lims = [y_26_arr.min(), min(y_26_arr.max(), 40)]
ax_pred.plot(lims, lims, color="crimson", linewidth=1.2, label="perfect prediction")
ax_pred.set_xlabel("Actual pace — SDW100 2026 (min/km)")
ax_pred.set_ylabel("Predicted pace (min/km)")
ax_pred.set_title(
    f"Cross-race: train 2025 → test 2026  (MAE={cv_mae:.2f},  R²={cv_r2:.3f})",
    loc="left", fontsize=10,
)
ax_pred.legend()

plt.tight_layout()
out_path = OUTPUT_DIR / "step7_random_forest.png"
plt.savefig(out_path, dpi=150)
print(f"\n  Saved: {out_path}")
plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — External data: predicting SDW100 finish time from checkpoint splits
# ─────────────────────────────────────────────────────────────────────────────
#
# Steps 6 and 7 worked on GPS data with 100k+ rows per race — one row per
# second. Consecutive rows are nearly identical, so a random train/test split
# was not honest (neighbours bled between sets).
#
# Here we have the full SDW100 2026 results: 500 runners, one row each.
# Each row is fully independent of the others — a random split is correct.
#
# Problem: given a runner's elapsed time at the first four checkpoints
# (~34 miles / 55 km into the race), can we predict their finishing time?
# This is exactly what pacers and crews estimate at aid stations.
#
# New concepts: pd.read_excel, pd.to_datetime, pd.to_timedelta,
#               pd.get_dummies (one-hot encoding), dropna(subset=[...]).

print("\n── Step 8: Finish Time Prediction from Checkpoint Splits ────────────")


# ── Load the race results ──────────────────────────────────────────────────────
#
# CONCEPT: pd.read_excel(path, header=N)
# Reads an Excel .xlsx file into a DataFrame.
# header=1 skips the first row (the race title) and uses the second row
# as column names.

RESULTS_FILE = "../dataSources/racesResults/CenturionSDW100_2026.xlsx"
results_raw  = pd.read_excel(RESULTS_FILE, header=1)

# CONCEPT: dropna(subset=[...])
# Drops rows where ANY of the listed columns is NaN.
# DNFs have no Overall position, so this keeps only finishers.
finishers = results_raw.dropna(subset=["Overall"]).copy()

print(f"\n  Total entries : {len(results_raw)}")
print(f"  Finishers     : {len(finishers)}")
print(f"  DNFs          : {len(results_raw) - len(finishers)}")


# ── Parse datetimes and finish time ───────────────────────────────────────────
#
# CONCEPT: pd.to_datetime()
# Converts a string like "2026-06-13 06:57:48" to a datetime object so we
# can do date arithmetic — subtracting two datetimes gives a timedelta.
#
# CONCEPT: pd.to_timedelta() + .dt.total_seconds()
# "13:27:13" is a duration, not a clock time — to_timedelta() parses it.
# .dt.total_seconds() then converts the timedelta to a plain float (seconds).

CP_COLS = ["Start", "Beacon Hill Beeches", "QECP", "South Harting", "Cocking"]
for col in CP_COLS:
    finishers[col] = pd.to_datetime(finishers[col])

finishers["finish_hours"] = (
    pd.to_timedelta(finishers["Time"])
    .dt.total_seconds() / 3600
)


# ── Feature engineering: elapsed time to each checkpoint ─────────────────────
#
# Each runner's Start timestamp differs (two waves: 05:30 and 06:30).
# Subtracting Start from the checkpoint time gives elapsed hours for everyone
# on the same scale.

CHECKPOINT_MAP = {
    "split_cp1": "Beacon Hill Beeches",   # ~24 km / 15 miles
    "split_cp2": "QECP",                  # ~37 km / 23 miles
    "split_cp3": "South Harting",         # ~48 km / 30 miles
    "split_cp4": "Cocking",               # ~55 km / 34 miles
}

for feat, col in CHECKPOINT_MAP.items():
    finishers[feat] = (
        (finishers[col] - finishers["Start"]).dt.total_seconds() / 3600
    )


# ── Encode categorical features ───────────────────────────────────────────────
#
# CONCEPT: pd.get_dummies(series, prefix=, drop_first=True)
# ML models only understand numbers, not strings like "Male" or "Female".
# get_dummies creates one binary (0/1) column per category value.
# This is called one-hot encoding.
#
# CONCEPT: drop_first=True — avoiding the dummy variable trap
# Gender has three values here: Male, Female, Non Binary.
# Alphabetically Female comes first, so drop_first removes it.
# Result: gender_Male=1 → Male,  gender_Non Binary=1 → Non Binary,
#         both 0 → Female.  Two columns encode three categories perfectly.
# Adding gender_Female on top would be redundant (the three always sum to 1),
# which confuses linear regression. drop_first removes the redundant one.

gender_dummies = pd.get_dummies(finishers["Gender"], prefix="gender", drop_first=True)

# Collapse the 10 age groups into 4 cleaner categories.
finishers["age_cat"] = finishers["Group"].apply(
    lambda g: "Open"    if g in ("M", "F", "XV40") else
              "V40"     if "40" in g else
              "V50"     if "50" in g else "V60plus"
)
age_dummies = pd.get_dummies(finishers["age_cat"], prefix="age", drop_first=True)

# Attach the dummy columns to the table (they share the same row index).
finishers = pd.concat([finishers, gender_dummies, age_dummies], axis=1)


# ── Build the model-ready DataFrame ───────────────────────────────────────────

SPLIT_FEATS = list(CHECKPOINT_MAP.keys())
CAT_FEATS   = list(gender_dummies.columns) + list(age_dummies.columns)
FEATURES_V3 = SPLIT_FEATS + CAT_FEATS
TARGET_V3   = "finish_hours"

ml_results = finishers[FEATURES_V3 + [TARGET_V3]].dropna()

print(f"\n  Runners with complete data: {len(ml_results)}")
print(f"  Features: {FEATURES_V3}")

desc = ml_results[TARGET_V3].describe()
print(f"\n  Finish time — min: {desc['min']:.2f}h  mean: {desc['mean']:.2f}h  max: {desc['max']:.2f}h")

X3 = ml_results[FEATURES_V3]
y3 = ml_results[TARGET_V3]


# ── Train / test split ────────────────────────────────────────────────────────
#
# Each row is one independent runner — no temporal autocorrelation.
# A random split is honest here.

X3_train, X3_test, y3_train, y3_test = train_test_split(
    X3, y3, test_size=0.2, random_state=42
)

scaler3     = StandardScaler()
X3_train_sc = scaler3.fit_transform(X3_train)
X3_test_sc  = scaler3.transform(X3_test)


# ── Linear Regression ─────────────────────────────────────────────────────────

lr3      = LinearRegression()
lr3.fit(X3_train_sc, y3_train)
lr3_pred = lr3.predict(X3_test_sc)
lr3_mae  = mean_absolute_error(y3_test, lr3_pred)
lr3_r2   = r2_score(y3_test, lr3_pred)


# ── Random Forest ─────────────────────────────────────────────────────────────

rf3      = RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=42)
rf3.fit(X3_train_sc, y3_train)
rf3_pred = rf3.predict(X3_test_sc)
rf3_mae  = mean_absolute_error(y3_test, rf3_pred)
rf3_r2   = r2_score(y3_test, rf3_pred)


def h_to_hm(h):
    """Convert a fractional hour float to a readable 'Xh YYm' string."""
    return f"{int(h)}h {int((h % 1) * 60):02d}m"


print(f"\n  {'Model':<22}  {'MAE':>10}  {'R²':>8}")
print(f"  {'-'*44}")
print(f"  {'Linear Regression':<22}  {h_to_hm(lr3_mae):>10}  {lr3_r2:>8.3f}")
print(f"  {'Random Forest':<22}  {h_to_hm(rf3_mae):>10}  {rf3_r2:>8.3f}")


# ── Visualise ─────────────────────────────────────────────────────────────────

fig, (ax_scatter, ax_imp) = plt.subplots(ncols=2, figsize=(14, 6))
fig.suptitle("Step 8: SDW100 2026 — Finish Time Prediction", fontsize=14)

# Actual vs predicted for the test set, coloured by gender.
# With 71 test runners, every data point is readable — unlike the 5000-sample
# GPS charts from Steps 6 and 7.
#
# We derive gender masks from the one-hot columns so each category gets its
# own colour. Female = both dummy columns are 0.
test_idx = y3_test.index
test_male = ml_results.loc[test_idx, "gender_Male"].values
test_nb   = ml_results.loc[test_idx, "gender_Non Binary"].values if "gender_Non Binary" in ml_results.columns else (test_male * 0)

gender_series = [
    (test_male == 1,                                  "steelblue",  "Male"),
    ((test_male == 0) & (test_nb == 0),               "crimson",    "Female"),
    (test_nb == 1,                                    "darkorange", "Non Binary"),
]
for mask, colour, label in gender_series:
    if mask.any():
        ax_scatter.scatter(
            y3_test.values[mask],
            rf3_pred[mask],
            alpha=0.75, s=50, color=colour, label=label,
        )

lims = [y3_test.min() - 0.5, y3_test.max() + 0.5]
ax_scatter.plot(lims, lims, color="black", linewidth=1.0, linestyle="--", label="perfect prediction")
ax_scatter.set_xlabel("Actual finish time (hours)")
ax_scatter.set_ylabel("Predicted finish time (hours)")
ax_scatter.set_title(
    f"Test set  (MAE = {h_to_hm(rf3_mae)},  R² = {rf3_r2:.3f})",
    loc="left", fontsize=10,
)
ax_scatter.legend()

# Feature importance
imp3       = rf3.feature_importances_
sorted_idx = imp3.argsort()
# Clean up feature labels for the chart
feat_labels = [f.replace("split_cp", "CP ").replace("gender_Male", "gender\n(male)")
                .replace("age_", "age ") for f in FEATURES_V3]

ax_imp.barh(
    [feat_labels[i] for i in sorted_idx],
    imp3[sorted_idx],
    color="steelblue",
)
ax_imp.set_xlabel("Importance (fraction of total)")
ax_imp.set_title("What predicts finish time?", loc="left", fontsize=10)

plt.tight_layout()
out_path = OUTPUT_DIR / "step8_finish_prediction.png"
plt.savefig(out_path, dpi=150)
print(f"\n  Saved: {out_path}")
plt.close()


# ─────────────────────────────────────────────────────────────────────────────
# WHAT'S NEXT
# ─────────────────────────────────────────────────────────────────────────────
# Step 9: cross-race generalisation — train on SDW100 2025 historical results
# and test on SDW100 2026, asking whether a model built from one year's field
# can predict the next year's finishing times.
