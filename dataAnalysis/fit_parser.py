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
# WHAT'S NEXT
# ─────────────────────────────────────────────────────────────────────────────
# Step 3 will introduce: functions.
# We'll wrap the parsing logic into reusable functions so we can load any of
# the three .fit files with a single call — and stop repeating ourselves.
