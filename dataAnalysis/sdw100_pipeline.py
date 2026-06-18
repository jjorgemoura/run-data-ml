"""
SDW100 2026 — End-to-End ML Pipeline
=====================================
Centurion South Downs Way 100 race results analysis.

What this script does:
  1. Load & clean  — parse the Excel results file, handle both waves and DNFs
  2. Feature eng.  — compute segment paces (min/km) between all 13 checkpoints
  3. EDA plots     — pace fade across the field, DNF dropout locations
  4. Model A       — finish time regression (predict finish from halfway split)
  5. Model B       — DNF classifier (predict dropout risk from early checkpoints)
  6. Interpretation — feature importance, SHAP-style analysis

Requirements:
  pip install pandas openpyxl scikit-learn matplotlib seaborn numpy

Usage:
  python sdw100_pipeline.py
  # Place the Excel file in the same directory, or update DATA_PATH below.
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")           # headless — saves to PNG files
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (mean_absolute_error, r2_score,
                             roc_auc_score, classification_report,
                             ConfusionMatrixDisplay, confusion_matrix)
from sklearn.pipeline import Pipeline
from sklearn.inspection import permutation_importance

# ── paths ────────────────────────────────────────────────────────────────────
# DATA_PATH   = "/mnt/user-data/uploads/Centurion_South_Downs_Way_100_2026.xlsx"
# OUTPUT_DIR  = "/mnt/user-data/outputs"

DATA_PATH   = "../dataSources/racesResults/CenturionSDW100_2026.xlsx"
OUTPUT_DIR  = "outputs"

import os
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save(fig, name):
    path = f"{OUTPUT_DIR}/{name}"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓  saved → {path}")


# ════════════════════════════════════════════════════════════════════════════
# 1. LOAD & CLEAN
# ════════════════════════════════════════════════════════════════════════════
print("\n── 1. Load & clean ──────────────────────────────────────────────────")

# Row 0 is a title row; row 1 is the header we want.
df_raw = pd.read_excel(DATA_PATH, header=1)

# Checkpoint columns in race order
CHECKPOINTS = [
    "Beacon Hill Beeches", "QECP", "South Harting", "Cocking",
    "Houghton Farm", "Washington", "Botolphs", "Saddlescombe Farm",
    "Housedean Farm", "Southease", "Alfriston", "Jevington", "Finish",
]

# Approximate cumulative distances (km) — scaled to the full 160 km / 100-mile course.
# Derived from official mile markers, converted and rescaled to sum to 160 km.
CP_DIST_KM = {
    "Beacon Hill Beeches": 13.5,
    "QECP":                33.6,
    "South Harting":       43.4,
    "Cocking":             57.4,
    "Houghton Farm":       72.0,
    "Washington":          85.3,   # ← roughly halfway (53 miles)
    "Botolphs":            97.2,
    "Saddlescombe Farm":  107.5,
    "Housedean Farm":     121.0,   # ← major crew checkpoint; long dwell times expected
    "Southease":          126.4,
    "Alfriston":          138.2,
    "Jevington":          149.4,
    "Finish":             160.0,
}

# ── Parse timestamps ─────────────────────────────────────────────────────────
df_raw["Start"] = pd.to_datetime(df_raw["Start"], errors="coerce")
for cp in CHECKPOINTS:
    df_raw[cp] = pd.to_datetime(df_raw[cp], errors="coerce")

# ── Parse finish time (stored as "HH:MM:SS" string) ─────────────────────────
def time_str_to_minutes(t):
    """Convert 'HH:MM:SS' string to total minutes (float)."""
    if pd.isna(t):
        return np.nan
    parts = str(t).strip().split(":")
    if len(parts) != 3:
        return np.nan
    return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60

df_raw["finish_minutes"] = df_raw["Time"].apply(time_str_to_minutes)
df_raw["finish_hours"]   = df_raw["finish_minutes"] / 60

# ── Finisher / DNF flag ──────────────────────────────────────────────────────
# 'Overall' is populated for finishers, null for DNFs.
df_raw["is_finisher"] = df_raw["Overall"].notna().astype(int)

# ── Categorical encodings ────────────────────────────────────────────────────
df_raw["is_male"] = (df_raw["Gender"] == "Male").astype(int)

# Age group: encode 10-year bands numerically (0 = open, 1 = V40, 2 = V50 …)
age_map = {
    "M": 0, "F": 0,
    "MV40": 1, "FV40": 1, "XV40": 1,
    "MV50": 2, "FV50": 2,
    "MV60": 3, "FV60": 3,
    "MV70": 4,
}
df_raw["age_group_enc"] = df_raw["Group"].map(age_map).fillna(0).astype(int)

# Wave (bib ≥ 2000 → wave 2, 1-hour later start)
df_raw["wave2"] = (df_raw["Bib"] >= 2000).astype(int)

print(f"  Total runners : {len(df_raw)}")
print(f"  Finishers     : {df_raw['is_finisher'].sum()}")
print(f"  DNFs          : {(df_raw['is_finisher'] == 0).sum()}")
print(f"  Completion    : {df_raw['is_finisher'].mean()*100:.1f}%")


# ════════════════════════════════════════════════════════════════════════════
# 2. FEATURE ENGINEERING — elapsed times & segment paces
# ════════════════════════════════════════════════════════════════════════════
print("\n── 2. Feature engineering ───────────────────────────────────────────")

df = df_raw.copy()

# Elapsed time from gun start to each checkpoint (minutes)
EL_COLS = []
for cp in CHECKPOINTS:
    col = f"el_{cp}"
    df[col] = (df[cp] - df["Start"]).dt.total_seconds() / 60
    EL_COLS.append(col)

# Segment pace (min/km) between consecutive checkpoints
# Note: Housedean Farm is a major crew checkpoint where runners rest 30–90 min.
# That dwell time is included in the Housedean → Southease segment pace and
# is intentional — it reflects real racing behaviour.
SEG_NAMES  = []   # human-readable labels
SEG_COLS   = []   # DataFrame column names
prev_dist  = 0.0
prev_cp    = None

for cp in CHECKPOINTS:
    dist_km  = CP_DIST_KM[cp]
    seg_km   = dist_km - prev_dist

    if prev_cp is None:
        col   = "pace_start_beacon"
        label = f"Start→{cp[:8]}"
        df[col] = df[f"el_{cp}"] / dist_km   # pace from gun to first CP
    else:
        col   = f"pace_{prev_cp[:6].replace(' ','_')}_{cp[:6].replace(' ','_')}"
        label = f"{prev_cp[:8]}→{cp[:8]}"
        df[col] = (df[f"el_{cp}"] - df[f"el_{prev_cp}"]) / seg_km

    SEG_COLS.append(col)
    SEG_NAMES.append(label)
    prev_dist = dist_km
    prev_cp   = cp

# Also derive: pace fade ratio per runner (late-race / early-race pace)
# Early = average pace through first 4 checkpoints
# Late  = average pace from Washington to Finish
early_cols = SEG_COLS[:4]
late_cols  = SEG_COLS[6:]   # Washington onward

df["early_pace_avg"] = df[early_cols].mean(axis=1)
df["late_pace_avg"]  = df[late_cols].mean(axis=1)
df["fade_ratio"]     = df["late_pace_avg"] / df["early_pace_avg"]
# >1 means slowing down (late pace > early pace), <1 means speeding up

print(f"  Segment columns created : {len(SEG_COLS)}")
print(f"  Elapsed columns created : {len(EL_COLS)}")
print(f"  Median fade ratio (finishers): "
      f"{df[df['is_finisher']==1]['fade_ratio'].median():.2f}x")

# Separate finishers and DNFs for analysis
fin  = df[df["is_finisher"] == 1].copy()
dnfs = df[df["is_finisher"] == 0].copy()


# ════════════════════════════════════════════════════════════════════════════
# 3. EDA — PACE FADE ACROSS THE FIELD
# ════════════════════════════════════════════════════════════════════════════
print("\n── 3. EDA — pace fade & DNF analysis ───────────────────────────────")

# ── 3a. Pace fade plot ───────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(14, 11))
fig.suptitle("SDW100 2026 — Pace Fade Across the Field", fontsize=14, fontweight="bold", y=0.98)

ax = axes[0]
fin_valid = fin[SEG_COLS].dropna()

# Percentile bands + median
p10  = fin_valid[SEG_COLS].quantile(0.10)
p25  = fin_valid[SEG_COLS].quantile(0.25)
p50  = fin_valid[SEG_COLS].quantile(0.50)
p75  = fin_valid[SEG_COLS].quantile(0.75)
p90  = fin_valid[SEG_COLS].quantile(0.90)

x = range(len(SEG_COLS))
short_labels = [n.split("→")[1][:12] for n in SEG_NAMES]   # destination name only

ax.fill_between(x, p10, p90, alpha=0.12, color="#1D9E75", label="10th–90th %ile")
ax.fill_between(x, p25, p75, alpha=0.22, color="#1D9E75", label="25th–75th %ile")
ax.plot(x, p50, color="#1D9E75", linewidth=2.5, marker="o", markersize=5, label="Median")
ax.plot(x, p10, color="#1D9E75", linewidth=0.8, linestyle="--", alpha=0.6)
ax.plot(x, p90, color="#1D9E75", linewidth=0.8, linestyle="--", alpha=0.6)

# Annotate Housedean (the major crew stop anomaly)
house_idx = SEG_COLS.index("pace_Saddle_Housed") if "pace_Saddle_Housed" in SEG_COLS else 8
ax.annotate("Housedean Farm\n(crew stop — dwell\ntime included)",
            xy=(house_idx, p50.iloc[house_idx]),
            xytext=(house_idx - 2.2, p50.iloc[house_idx] + 2.5),
            arrowprops=dict(arrowstyle="->", color="#888"),
            fontsize=8, color="#555")

ax.set_xticks(list(x))
ax.set_xticklabels(short_labels, rotation=35, ha="right", fontsize=8)
ax.set_ylabel("Segment pace (min/km)")
ax.set_xlabel("Segment (destination checkpoint)")
ax.legend(fontsize=8)
ax.set_title("Median segment pace with percentile bands — all finishers (n=357)", fontsize=10)
ax.grid(axis="y", alpha=0.3)

# ── 3b. Gender split overlay ─────────────────────────────────────────────────
ax2 = axes[1]
for gender_val, label, color in [(1, "Male (n=295)", "#185FA5"), (0, "Female (n=61)", "#C2185B")]:
    sub = fin[fin["is_male"] == gender_val][SEG_COLS].dropna()
    med = sub.median()
    ax2.plot(x, med, color=color, linewidth=2, marker="o", markersize=4, label=label)

ax2.set_xticks(list(x))
ax2.set_xticklabels(short_labels, rotation=35, ha="right", fontsize=8)
ax2.set_ylabel("Median segment pace (min/km)")
ax2.set_xlabel("Segment (destination checkpoint)")
ax2.legend(fontsize=9)
ax2.set_title("Median pace by gender — note similar fade patterns", fontsize=10)
ax2.grid(axis="y", alpha=0.3)

plt.tight_layout()
save(fig, "01_pace_fade.png")

# ── 3c. DNF dropout locations ────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("SDW100 2026 — DNF Analysis (143 DNFs, 28.6% rate)", fontsize=13, fontweight="bold")

# Where did DNFs drop? Find last populated checkpoint per DNF runner
def last_checkpoint_reached(row):
    for cp in reversed(CHECKPOINTS):
        if pd.notna(row[cp]):
            return cp
    return "Before start"

dnfs["last_cp"] = dnfs.apply(last_checkpoint_reached, axis=1)

# Count DNFs by last checkpoint reached
dropout_counts = dnfs["last_cp"].value_counts().reindex(CHECKPOINTS, fill_value=0)

ax = axes[0]
colors = ["#E24B4A" if c > dropout_counts.median() else "#F4A0A0"
          for c in dropout_counts.values]
bars = ax.barh(range(len(CHECKPOINTS)), dropout_counts.values, color=colors, edgecolor="white")
ax.set_yticks(range(len(CHECKPOINTS)))
ax.set_yticklabels(CHECKPOINTS, fontsize=8)
ax.set_xlabel("Number of DNFs")
ax.set_title("DNF count by last checkpoint reached", fontsize=10)
ax.bar_label(bars, padding=3, fontsize=8)
ax.grid(axis="x", alpha=0.3)
ax.invert_yaxis()

# DNF rate by gender
ax2 = axes[1]
dnf_by_gender = df.groupby("Gender")["is_finisher"].agg(
    finishers="sum", total="count"
).reset_index()
dnf_by_gender["dnf_rate"] = 1 - dnf_by_gender["finishers"] / dnf_by_gender["total"]
dnf_by_gender["finish_rate"] = dnf_by_gender["finishers"] / dnf_by_gender["total"]

bar_w = 0.35
genders = dnf_by_gender["Gender"].tolist()
fin_rates = dnf_by_gender["finish_rate"].tolist()
dnf_rates = dnf_by_gender["dnf_rate"].tolist()

pos = np.arange(len(genders))
b1 = ax2.bar(pos - bar_w/2, [r*100 for r in fin_rates], bar_w,
             label="Finished", color="#1D9E75", alpha=0.85)
b2 = ax2.bar(pos + bar_w/2, [r*100 for r in dnf_rates],  bar_w,
             label="DNF",      color="#E24B4A", alpha=0.85)
ax2.set_xticks(pos)
ax2.set_xticklabels(genders)
ax2.set_ylabel("Percentage of starters (%)")
ax2.set_title("Finish vs DNF rate by gender", fontsize=10)
ax2.legend()
ax2.set_ylim(0, 100)
ax2.grid(axis="y", alpha=0.3)
ax2.bar_label(b1, fmt="%.0f%%", padding=3, fontsize=8)
ax2.bar_label(b2, fmt="%.0f%%", padding=3, fontsize=8)

plt.tight_layout()
save(fig, "02_dnf_analysis.png")

# ── 3d. Finish time distribution ─────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("SDW100 2026 — Finish Time Distribution", fontsize=13, fontweight="bold")

ax = axes[0]
ax.hist(fin["finish_hours"], bins=30, color="#1D9E75", edgecolor="white", alpha=0.85)
ax.axvline(24, color="#E24B4A", linewidth=1.5, linestyle="--", label="24-hour goal")
ax.axvline(fin["finish_hours"].median(), color="#BA7517", linewidth=1.5,
           linestyle="--", label=f"Median ({fin['finish_hours'].median():.1f}h)")
ax.set_xlabel("Finish time (hours)")
ax.set_ylabel("Number of runners")
ax.set_title("All finishers", fontsize=10)
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)

ax2 = axes[1]
for gender_val, label, color in [(1, "Male", "#185FA5"), (0, "Female", "#C2185B")]:
    sub = fin[fin["is_male"] == gender_val]["finish_hours"]
    ax2.hist(sub, bins=20, alpha=0.65, color=color, edgecolor="white", label=f"{label} (n={len(sub)})")
ax2.axvline(24, color="#E24B4A", linewidth=1.5, linestyle="--", label="24-hour goal")
ax2.set_xlabel("Finish time (hours)")
ax2.set_ylabel("Number of runners")
ax2.set_title("By gender", fontsize=10)
ax2.legend(fontsize=9)
ax2.grid(axis="y", alpha=0.3)

plt.tight_layout()
save(fig, "03_finish_distribution.png")

print(f"  Finish time:  median={fin['finish_hours'].median():.2f}h, "
      f"min={fin['finish_hours'].min():.2f}h, max={fin['finish_hours'].max():.2f}h")
print(f"  Sub-24h:      {(fin['finish_hours'] < 24).sum()} runners "
      f"({(fin['finish_hours'] < 24).mean()*100:.0f}% of finishers)")
print(f"  Top dropout:  {dropout_counts.idxmax()} ({dropout_counts.max()} runners)")


# ════════════════════════════════════════════════════════════════════════════
# 4. MODEL A — FINISH TIME REGRESSION
# ════════════════════════════════════════════════════════════════════════════
print("\n── 4. Model A — finish time regression ──────────────────────────────")

# ── Feature set: elapsed time at Washington (~halfway) + demographics ─────────
# This answers: "given my halfway split, what finish time does the field suggest?"
FEATURES_WASH = ["el_Washington", "is_male", "age_group_enc"]

fin_model = fin.dropna(subset=FEATURES_WASH + ["finish_minutes"]).copy()
X_wash = fin_model[FEATURES_WASH]
y_wash = fin_model["finish_minutes"]

print(f"  Training set: {len(fin_model)} finishers")

# ── Model 1: linear regression baseline ──────────────────────────────────────
lr = LinearRegression()
cv_lr = cross_val_score(lr, X_wash, y_wash, cv=5,
                        scoring="neg_mean_absolute_error")
mae_lr = -cv_lr.mean()
print(f"  Linear Regression   MAE: {mae_lr:.1f} min  ({mae_lr/60:.2f} hrs)")

# ── Model 2: Random Forest ────────────────────────────────────────────────────
rf = RandomForestRegressor(n_estimators=300, max_depth=8,
                           min_samples_leaf=5, random_state=42)
cv_rf = cross_val_score(rf, X_wash, y_wash, cv=5,
                        scoring="neg_mean_absolute_error")
mae_rf = -cv_rf.mean()
print(f"  Random Forest       MAE: {mae_rf:.1f} min  ({mae_rf/60:.2f} hrs)")

# ── Extend features: add early segment paces ─────────────────────────────────
# Including pacing discipline early gives richer signal
early_pace_cols = SEG_COLS[:6]   # first 6 segments (up to and including Washington)
FEATURES_FULL   = FEATURES_WASH + early_pace_cols

fin_full = fin.dropna(subset=FEATURES_FULL + ["finish_minutes"]).copy()
X_full   = fin_full[FEATURES_FULL]
y_full   = fin_full["finish_minutes"]

rf_full = RandomForestRegressor(n_estimators=300, max_depth=8,
                                min_samples_leaf=5, random_state=42)
cv_rf_full = cross_val_score(rf_full, X_full, y_full, cv=5,
                             scoring="neg_mean_absolute_error")
mae_rf_full = -cv_rf_full.mean()
print(f"  Random Forest+pace  MAE: {mae_rf_full:.1f} min  ({mae_rf_full/60:.2f} hrs)  ← with pacing features")

# ── Fit final model on all data for visualisation & importance ────────────────
rf_full.fit(X_full, y_full)
fin_full["predicted_minutes"] = rf_full.predict(X_full)
fin_full["predicted_hours"]   = fin_full["predicted_minutes"] / 60
fin_full["actual_hours"]      = fin_full["finish_minutes"] / 60
fin_full["residual_hours"]    = fin_full["actual_hours"] - fin_full["predicted_hours"]

# ── Regression plots ──────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle("SDW100 2026 — Finish Time Prediction (Random Forest)", fontsize=13, fontweight="bold")

# Actual vs predicted
ax = axes[0]
ax.scatter(fin_full["actual_hours"], fin_full["predicted_hours"],
           alpha=0.45, s=18, color="#185FA5", edgecolors="none")
lims = [fin_full["actual_hours"].min() - 0.5, fin_full["actual_hours"].max() + 0.5]
ax.plot(lims, lims, "r--", linewidth=1.2, label="Perfect prediction")
ax.set_xlabel("Actual finish time (hrs)")
ax.set_ylabel("Predicted finish time (hrs)")
ax.set_title(f"Actual vs Predicted\nMAE = {mae_rf_full/60:.2f} hrs", fontsize=10)
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

# Residual distribution
ax2 = axes[1]
ax2.hist(fin_full["residual_hours"], bins=25, color="#185FA5", edgecolor="white", alpha=0.8)
ax2.axvline(0, color="red", linewidth=1.2, linestyle="--")
ax2.set_xlabel("Residual (actual − predicted, hrs)")
ax2.set_ylabel("Count")
ax2.set_title("Residual distribution\n(centred = unbiased)", fontsize=10)
ax2.grid(axis="y", alpha=0.3)

# Feature importances
ax3 = axes[2]
feat_labels = ["Elapsed@Washington", "Gender", "Age group"] + \
              [f"Pace seg {i+1}" for i in range(len(early_pace_cols))]
importances = rf_full.feature_importances_
order = np.argsort(importances)
colors_imp = ["#1D9E75" if i >= len(FEATURES_WASH) else "#185FA5"
              for i in order]
ax3.barh(range(len(FEATURES_FULL)), importances[order],
         color=colors_imp, edgecolor="white")
ax3.set_yticks(range(len(FEATURES_FULL)))
ax3.set_yticklabels([feat_labels[i] for i in order], fontsize=8)
ax3.set_xlabel("Feature importance (mean decrease impurity)")
ax3.set_title("Feature importances\n(green = pace features)", fontsize=10)
ax3.grid(axis="x", alpha=0.3)

plt.tight_layout()
save(fig, "04_finish_time_model.png")

# ── Practical output: what does the model predict at different splits? ─────────
print("\n  Predicted finish time for different halfway (Washington) splits:")
print("  " + "-" * 52)
print(f"  {'Washington split':22s}  {'Predicted finish':16s}  {'Pace zone'}")
print("  " + "-" * 52)

# Use median pace ratios from field for early segments, vary only Washington split
median_paces = fin_full[early_pace_cols].median().values
for wash_hrs in [5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]:
    wash_min = wash_hrs * 60
    x_row = np.array([[wash_min, 1, 0] + list(median_paces)])
    pred_hr = rf_full.predict(x_row)[0] / 60
    zone = "sub-24h 🎯" if pred_hr < 24 else ("sub-28h" if pred_hr < 28 else "tough")
    print(f"  {wash_hrs:.1f}h ({wash_hrs*60:.0f} min)           "
          f"{pred_hr:.1f}h               {zone}")


# ════════════════════════════════════════════════════════════════════════════
# 5. MODEL B — DNF CLASSIFIER
# ════════════════════════════════════════════════════════════════════════════
print("\n── 5. Model B — DNF classifier ──────────────────────────────────────")

# ── ML concept: binary classification with class imbalance ──────────────────
# Class imbalance: 357 finishers vs 143 DNFs (71/29 split).
# We use class_weight='balanced' to prevent the model ignoring DNFs.
#
# Features: pacing through the FIRST FIVE checkpoints only (Cocking, ~57km).
# The goal is to predict DNF risk EARLY — before Washington halfway.

EARLY_SEG_COLS = SEG_COLS[:5]  # segments up to Houghton Farm / Cocking area
FEATURES_DNF   = EARLY_SEG_COLS + ["is_male", "age_group_enc"]

df_dnf = df.dropna(subset=FEATURES_DNF).copy()
X_dnf  = df_dnf[FEATURES_DNF]
y_dnf  = df_dnf["is_finisher"]

print(f"  Training set: {len(df_dnf)} runners "
      f"({y_dnf.sum()} finishers, {(1-y_dnf).sum()} DNFs)")
print(f"  Class balance: {y_dnf.mean()*100:.0f}% finish, "
      f"{(1-y_dnf).mean()*100:.0f}% DNF")

# ── Logistic regression baseline ─────────────────────────────────────────────
lr_pipe = Pipeline([
    ("scaler", StandardScaler()),
    ("clf",    LogisticRegression(class_weight="balanced", max_iter=1000,
                                  random_state=42))
])
cv_lr_dnf = cross_val_score(lr_pipe, X_dnf, y_dnf,
                            cv=StratifiedKFold(5, shuffle=True, random_state=42),
                            scoring="roc_auc")
print(f"  Logistic Regression AUC: {cv_lr_dnf.mean():.3f} ± {cv_lr_dnf.std():.3f}")

# ── Gradient Boosting classifier ──────────────────────────────────────────────
gb_clf = GradientBoostingClassifier(
    n_estimators=200, max_depth=3, learning_rate=0.05,
    subsample=0.8, random_state=42
)
cv_gb = cross_val_score(gb_clf, X_dnf, y_dnf,
                        cv=StratifiedKFold(5, shuffle=True, random_state=42),
                        scoring="roc_auc")
print(f"  Gradient Boosting   AUC: {cv_gb.mean():.3f} ± {cv_gb.std():.3f}")

# ── Fit and plot ──────────────────────────────────────────────────────────────
gb_clf.fit(X_dnf, y_dnf)
df_dnf["dnf_risk"]  = gb_clf.predict_proba(X_dnf)[:, 0]  # P(DNF)
df_dnf["predicted"] = gb_clf.predict(X_dnf)

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle("SDW100 2026 — DNF Risk Classifier (early checkpoints only)",
             fontsize=13, fontweight="bold")

# DNF risk score distributions
ax = axes[0]
ax.hist(df_dnf[df_dnf["is_finisher"]==1]["dnf_risk"], bins=25,
        alpha=0.7, color="#1D9E75", edgecolor="white", label="Finishers")
ax.hist(df_dnf[df_dnf["is_finisher"]==0]["dnf_risk"], bins=25,
        alpha=0.7, color="#E24B4A", edgecolor="white", label="DNFs")
ax.set_xlabel("Predicted P(DNF)")
ax.set_ylabel("Count")
ax.set_title(f"DNF risk score distribution\nAUC = {cv_gb.mean():.3f}", fontsize=10)
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)

# Confusion matrix
ax2 = axes[1]
cm = confusion_matrix(y_dnf, df_dnf["predicted"])
disp = ConfusionMatrixDisplay(cm, display_labels=["DNF", "Finisher"])
disp.plot(ax=ax2, colorbar=False, cmap="Blues")
ax2.set_title("Confusion matrix (training data)\nNote: use with care — train=test here", fontsize=9)

# Feature importances
ax3 = axes[2]
dnf_feat_labels = ([f"Pace seg {i+1}\n({SEG_NAMES[i].split('→')[1][:10]})"
                    for i in range(len(EARLY_SEG_COLS))]
                   + ["Gender", "Age group"])
imp_gb = gb_clf.feature_importances_
order_gb = np.argsort(imp_gb)
ax3.barh(range(len(FEATURES_DNF)), imp_gb[order_gb],
         color="#185FA5", edgecolor="white")
ax3.set_yticks(range(len(FEATURES_DNF)))
ax3.set_yticklabels([dnf_feat_labels[i] for i in order_gb], fontsize=8)
ax3.set_xlabel("Feature importance")
ax3.set_title("What predicts DNF risk?\n(early pacing segments)", fontsize=10)
ax3.grid(axis="x", alpha=0.3)

plt.tight_layout()
save(fig, "05_dnf_classifier.png")

# ── ML lesson: precision vs recall tradeoff ───────────────────────────────────
print("\n  Classification report (default 0.5 threshold):")
print(classification_report(y_dnf, df_dnf["predicted"],
                            target_names=["DNF", "Finisher"]))

print("  ⚠  Note on class imbalance:")
print("     A naive model predicting 'everyone finishes' would score 71% accuracy.")
print("     AUC measures discrimination ability independent of threshold.")
print("     Higher recall for DNF = catches more true dropouts (at cost of false alarms).")


# ════════════════════════════════════════════════════════════════════════════
# 6. PACE FADE DEEP DIVE — where the race breaks people
# ════════════════════════════════════════════════════════════════════════════
print("\n── 6. Pace fade deep dive ────────────────────────────────────────────")

# ── 6a. Fade ratio by finish time bucket ─────────────────────────────────────
fin["finish_bucket"] = pd.cut(
    fin["finish_hours"],
    bins=[0, 18, 20, 22, 24, 26, 28, 40],
    labels=["<18h", "18–20h", "20–22h", "22–24h", "24–26h", "26–28h", "28h+"]
)

fig, axes = plt.subplots(1, 2, figsize=(15, 6))
fig.suptitle("SDW100 2026 — Pace Fade Deep Dive", fontsize=13, fontweight="bold")

ax = axes[0]
bucket_paces = []
bucket_labels = fin["finish_bucket"].cat.categories
for bucket in bucket_labels:
    sub = fin[fin["finish_bucket"] == bucket][SEG_COLS].dropna()
    if len(sub) > 5:
        bucket_paces.append(sub.median())
    else:
        bucket_paces.append(pd.Series([np.nan] * len(SEG_COLS), index=SEG_COLS))

x = range(len(SEG_COLS))
cmap = plt.cm.RdYlGn_r
colors_b = [cmap(i / max(len(bucket_labels)-1, 1)) for i in range(len(bucket_labels))]
for i, (paces, label, c) in enumerate(zip(bucket_paces, bucket_labels, colors_b)):
    if not paces.isna().all():
        ax.plot(x, paces.values, color=c, linewidth=1.8, marker="o",
                markersize=3.5, label=str(label), alpha=0.85)

ax.set_xticks(list(x))
ax.set_xticklabels([n.split("→")[1][:10] for n in SEG_NAMES],
                   rotation=35, ha="right", fontsize=7.5)
ax.set_ylabel("Median pace (min/km)")
ax.set_title("Pacing profile by finish time band\n(faster runners = lower pace values = green)", fontsize=9)
ax.legend(fontsize=7.5, loc="upper left")
ax.grid(axis="y", alpha=0.3)

# ── 6b. Pace delta — how much slower is each segment vs the runner's own average?
ax2 = axes[1]
# Compute normalised pace: each segment pace / runner's personal median pace
# This shows relative effort independent of overall speed
fin_valid2 = fin.dropna(subset=SEG_COLS).copy()
fin_valid2["personal_median_pace"] = fin_valid2[SEG_COLS].median(axis=1)
normalised = fin_valid2[SEG_COLS].div(fin_valid2["personal_median_pace"], axis=0)

norm_p25 = normalised.quantile(0.25)
norm_p50 = normalised.quantile(0.50)
norm_p75 = normalised.quantile(0.75)

ax2.fill_between(x, norm_p25, norm_p75, alpha=0.2, color="#185FA5")
ax2.plot(x, norm_p50, color="#185FA5", linewidth=2.5, marker="o", markersize=5)
ax2.axhline(1.0, color="#888", linewidth=1, linestyle="--", label="Own average pace")
# Highlight where runners go significantly above their average
for i, v in enumerate(norm_p50.values):
    if v > 1.3:   # 30% slower than personal average
        ax2.axvspan(i-0.5, i+0.5, alpha=0.08, color="#E24B4A")

ax2.set_xticks(list(x))
ax2.set_xticklabels([n.split("→")[1][:10] for n in SEG_NAMES],
                    rotation=35, ha="right", fontsize=7.5)
ax2.set_ylabel("Pace ratio (1.0 = own average)")
ax2.set_title("Normalised segment pace\n(how much slower than personal average?)", fontsize=9)
ax2.legend(fontsize=8)
ax2.grid(axis="y", alpha=0.3)

plt.tight_layout()
save(fig, "06_pace_fade_deep_dive.png")


# ════════════════════════════════════════════════════════════════════════════
# 7. SUMMARY STATS — print to console
# ════════════════════════════════════════════════════════════════════════════
print("\n── 7. Summary ───────────────────────────────────────────────────────")
print(f"""
  Dataset
  ───────────────────────────────────────────────────
  Runners   : {len(df)}   (wave 1: {(df['wave2']==0).sum()}, wave 2: {(df['wave2']==1).sum()})
  Finishers : {fin['is_finisher'].sum()}  ({fin['is_finisher'].sum()/len(df)*100:.1f}%)
  DNFs      : {(df['is_finisher']==0).sum()}  ({(df['is_finisher']==0).sum()/len(df)*100:.1f}%)

  Finish times (all finishers)
  ───────────────────────────────────────────────────
  Fastest   : {fin['finish_hours'].min():.2f}h
  Median    : {fin['finish_hours'].median():.2f}h
  Slowest   : {fin['finish_hours'].max():.2f}h
  Sub-24h   : {(fin['finish_hours']<24).sum()} runners ({(fin['finish_hours']<24).mean()*100:.0f}%)

  Model A — finish time regression
  ───────────────────────────────────────────────────
  Linear Regression MAE : {mae_lr/60:.2f} hrs  (baseline)
  Random Forest MAE     : {mae_rf/60:.2f} hrs  (halfway split only)
  RF + pacing features  : {mae_rf_full/60:.2f} hrs  (best model)

  Model B — DNF classifier (from early checkpoints)
  ───────────────────────────────────────────────────
  Gradient Boosting AUC : {cv_gb.mean():.3f}  (0.5 = random, 1.0 = perfect)

  Output files
  ───────────────────────────────────────────────────
  01_pace_fade.png         — pace fade with percentile bands
  02_dnf_analysis.png      — dropout locations & gender split
  03_finish_distribution.png — finish time histograms
  04_finish_time_model.png — regression predictions & feature importance
  05_dnf_classifier.png    — DNF risk scores & feature importance
  06_pace_fade_deep_dive.png — pace by finish band & normalised fade
""")

print("  ✓  Pipeline complete.")
