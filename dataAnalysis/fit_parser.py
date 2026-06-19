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
# print(f"FIT Protocol Messages: {activity.messages}")


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


# ── Build a DataFrame from our list of dicts ──────────────────────────────────
#
# pd.DataFrame(list_of_dicts) converts automatically:
#   - each dict becomes one row
#   - the dict keys become column names

print("\n── Step 4: pandas DataFrames ─────────────────────────────────────────")

sdw26 = pd.DataFrame(races["SDW100 2026"]["records"])

# CONCEPT: .shape, .dtypes, .head()
# These are your first three instincts whenever you load new data.
#   .shape   → (rows, columns) — how big is it?
#   .dtypes  → the data type of each column
#   .head(n) → print the first n rows (default 5)

print(f"\n  Shape  : {sdw26.shape[0]:,} rows × {sdw26.shape[1]} columns")
print(f"\n  Column types:\n{sdw26.dtypes}")
print(f"\n  First 3 rows:\n{sdw26.head(3)}")


# ── Add computed columns ───────────────────────────────────────────────────────
#
# CONCEPT: derived columns
# You create a new column by assigning to df["new_col"].
# The expression on the right operates on the whole column at once —
# no loop needed. This is called "vectorised" operation and is very fast.

# Elapsed time in hours from the race start
start_time = sdw26["timestamp"].iloc[0]        # .iloc[0] = first row by position

# CONCEPT: .iloc[n]
# Integer Location — access a row by its position number (0 = first, -1 = last).
# Different from .loc which uses the index label.

sdw26["elapsed_hours"] = (
    (sdw26["timestamp"] - start_time)
    .dt.total_seconds()                        # timedelta → seconds
    / 3600                                     # seconds → hours
)

# Pace in min/km
# First compute the per-second steps — how much distance and time each row covers.
# .diff() gives the difference between each row and the row before it.
sdw26["dist_step_km"]  = sdw26["distance_km"].diff()
sdw26["time_step_min"] = sdw26["elapsed_hours"].diff() * 60

# ── WHY naive pace (time_step / dist_step) was wrong ────────────────────────
# Two problems with dividing step-by-step at 1-second resolution:
#
# 1. FILTERING BIAS: 42% of rows have dist_step = 0 (GPS didn't update, or
#    standing still at aid stations). dividing by 0 gives infinity, which we
#    filter out — so ALL stopped time disappears from the stats, making the
#    median look far faster than reality.
#
# 2. GPS QUANTIZATION: the device records distance in 1-metre increments.
#    Moving at ~3 m/s always produces exactly 0.003 km/step → always 5.56 min/km.
#    The data is too coarse at 1-second resolution to give smooth pace.
#
# FIX: .rolling(window=60) — sum distance and time over a 60-second window
# before dividing. Stopped seconds dilute the fast seconds, quantization
# noise averages out, and the result matches real-world expectations.
#
# CONCEPT: .rolling(window)
# Computes a statistic over a sliding window of N consecutive rows.
# .sum() on a rolling window adds up the last N values at each row.
# min_periods=30 means: only compute if at least 30 rows exist in the window
# (avoids unreliable values at the very start of the data).

PACE_WINDOW = 60   # seconds

sdw26["dist_60s"]    = sdw26["dist_step_km"].rolling(window=PACE_WINDOW, min_periods=30).sum()
sdw26["time_60s"]    = sdw26["time_step_min"].rolling(window=PACE_WINDOW, min_periods=30).sum()
sdw26["pace_min_km"] = sdw26["time_60s"] / sdw26["dist_60s"]

# CONCEPT: filtering out bad values with .loc and boolean masks
# A boolean mask is a column of True/False values.
# df.loc[mask, "col"] = value  sets that column only where mask is True.
# Only filter truly impossible values — > 60 min/km means nearly stopped
# for the entire 60-second window, which we treat as NaN.
bad_pace = sdw26["pace_min_km"] > 60
sdw26.loc[bad_pace, "pace_min_km"] = float("nan")   # NaN = "not a number" in pandas


# ── describe() — instant statistical summary ──────────────────────────────────
#
# CONCEPT: .describe()
# One method gives you count, mean, std, min, 25th/50th/75th percentile, max
# for every numeric column. Essential first look at any dataset.

print(f"\n  Statistical summary:")
print(sdw26[["heart_rate", "pace_min_km", "elapsed_hours"]].describe().round(2))


# ── groupby — aggregate by HR zone ───────────────────────────────────────────
#
# CONCEPT: groupby + agg
# groupby splits the DataFrame into groups by a column value,
# then agg computes a summary statistic for each group.
# Think of it as: "for each HR zone, calculate the mean pace."
#
# First we need to assign each row to a HR zone.
# pd.cut() bins a continuous value into discrete categories.

hr_bins   = [0,  100, 120, 140, 160, 220]
hr_labels = ["Zone 1\n(<100)", "Zone 2\n(100–120)",
             "Zone 3\n(120–140)", "Zone 4\n(140–160)", "Zone 5\n(160+)"]

sdw26["hr_zone"] = pd.cut(sdw26["heart_rate"], bins=hr_bins, labels=hr_labels)

zone_summary = (
    sdw26
    .groupby("hr_zone", observed=True)          # group by zone
    .agg(
        time_hours  = ("elapsed_hours", "count"),   # rows ≈ seconds
        avg_pace    = ("pace_min_km",   "mean"),
        avg_hr      = ("heart_rate",    "mean"),
    )
    .assign(time_hours=lambda df: (df["time_hours"] / 3600).round(2))
    .round(2)
)

print(f"\n  Time and pace by HR zone (SDW100 2026):")
print(zone_summary)


# ── Do the same for all three races in one loop ───────────────────────────────
#
# CONCEPT: storing DataFrames in a dict
# Just as we stored session summaries in a dict, we can store DataFrames.
# This lets us loop over all races without repeating code.

print(f"\n  Building DataFrames for all races...")

dfs = {}
for race_name, data in races.items():
    df = pd.DataFrame(data["records"])

    start = df["timestamp"].iloc[0]
    df["elapsed_hours"] = (
        (df["timestamp"] - start).dt.total_seconds() / 3600
    )
    df["dist_step_km"]  = df["distance_km"].diff()
    df["time_step_min"] = df["elapsed_hours"].diff() * 60
    df["dist_60s"]      = df["dist_step_km"].rolling(window=PACE_WINDOW, min_periods=30).sum()
    df["time_60s"]      = df["time_step_min"].rolling(window=PACE_WINDOW, min_periods=30).sum()
    df["pace_min_km"]   = df["time_60s"] / df["dist_60s"]
    df.loc[df["pace_min_km"] > 60, "pace_min_km"] = float("nan")
    df["race"] = race_name                     # tag each row with the race name

    dfs[race_name] = df
    print(f"  {race_name}: {df.shape[0]:,} rows, columns: {list(df.columns)}")

# CONCEPT: pd.concat()
# Stacks multiple DataFrames on top of each other into one.
# ignore_index=True gives the combined DataFrame fresh row numbers.
all_races = pd.concat(dfs.values(), ignore_index=True)
print(f"\n  Combined DataFrame: {all_races.shape[0]:,} rows")

# Quick per-race pace summary using the combined DataFrame
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


# ── Plot 1: SDW100 2026 — Heart rate and pace over time ──────────────────────
#
# CONCEPT: plt.subplots(nrows, ncols, figsize, sharex)
# Returns two objects:
#   fig            — the overall canvas (the "sheet of paper")
#   (ax_hr, ax_pace) — the individual subplot areas drawn on that sheet
#
# figsize=(width, height) in inches.
# sharex=True links the x-axis on both subplots — zooming one zooms both.

sdw26 = dfs["SDW100 2026"]

fig, (ax_hr, ax_pace) = plt.subplots(nrows=2, ncols=1, figsize=(14, 8), sharex=True)

# CONCEPT: fig.suptitle()
# Sets one title for the whole figure, sitting above all subplots.
fig.suptitle("SDW100 2026 — Heart Rate and Pace", fontsize=14)


# ── CONCEPT: ax.plot(x, y, ...) ──────────────────────────────────────────────
# Draws a line connecting the (x, y) points.
#   color     — CSS colour name or hex (e.g. "#e63946")
#   linewidth — thickness in points; 0.6 is thin, 2.0 is thick
#   alpha     — opacity: 0.0 = invisible, 1.0 = fully opaque
#               use < 1 when data is dense so overlapping lines stay visible

ax_hr.plot(
    sdw26["elapsed_hours"],
    sdw26["heart_rate"],
    color="crimson",
    linewidth=0.6,
    alpha=0.7,
)
ax_hr.set_ylabel("Heart rate (bpm)")
ax_hr.set_title("Heart rate", loc="left", fontsize=10)

# Smooth pace over 5 minutes (300 rows ≈ 300 seconds) for cleaner visuals.
# The 60-second window from Step 4 was needed for accurate stats;
# 300 seconds makes the chart readable without distorting the shape.
# We create a temporary Series just for the plot — the column is unchanged.
smooth_pace_sdw26 = sdw26["pace_min_km"].rolling(300, min_periods=60).mean()

ax_pace.plot(
    sdw26["elapsed_hours"],
    smooth_pace_sdw26,
    color="steelblue",
    linewidth=1.0,
)
ax_pace.set_ylabel("Pace (min/km)")
ax_pace.set_xlabel("Elapsed time (hours)")
ax_pace.set_title("Pace (5-min rolling average)", loc="left", fontsize=10)

# CONCEPT: ax.invert_yaxis()
# A lower pace number means faster (6 min/km is faster than 10 min/km).
# Inverting the y-axis puts "fast" at the top — the same convention used
# by Garmin, Strava, and every running watch you own.
ax_pace.invert_yaxis()

# CONCEPT: plt.tight_layout()
# Automatically adjusts margins and spacing so axis labels don't overlap subplots.
plt.tight_layout()

# CONCEPT: plt.savefig(path, dpi=...)
# Saves the figure to disk. dpi (dots per inch) controls image resolution.
# 150 dpi is sharp on screen; 300 dpi is print quality.
out_path = OUTPUT_DIR / "sdw26_hr_pace.png"
plt.savefig(out_path, dpi=150)
print(f"  Saved: {out_path}")

# CONCEPT: plt.close()
# Releases the figure from memory. Always call this after saving — otherwise
# matplotlib accumulates open figures and eventually runs out of memory.
plt.close()


# ── Plot 2: All races — pace over distance ────────────────────────────────────
#
# CONCEPT: plotting multiple series on one Axes
# Call ax.plot() once per series — each call adds another line to the same chart.
# The `label=` keyword names the line; ax.legend() then draws the legend
# automatically using all the labels you assigned.

fig, ax = plt.subplots(figsize=(14, 6))
fig.suptitle("Pace comparison — all three races", fontsize=14)

RACE_COLOURS = {
    "SDW100 2025": "steelblue",
    "SDW100 2026": "crimson",
    "OMD100 2026": "darkorange",
}

for name, df in dfs.items():
    smooth = df["pace_min_km"].rolling(300, min_periods=60).mean()
    ax.plot(
        df["distance_km"],
        smooth,
        label=name,
        color=RACE_COLOURS[name],
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
# WHAT'S NEXT
# ─────────────────────────────────────────────────────────────────────────────
# Step 6 will introduce: Machine Learning basics with scikit-learn.
# We'll train a simple model to predict finishing time from early-race data —
# the first step toward the ML portfolio goal.
