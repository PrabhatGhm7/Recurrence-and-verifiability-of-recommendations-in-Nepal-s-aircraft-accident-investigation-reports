"""
reproduce_analysis.py - recompute every statistic reported in the paper from the
published dataset, and check each against the value printed in the manuscript.

Paper: "Recommended again: An audit of safety recommendations in Nepal's
published aircraft accident investigation reports, 2012-2025"

Input : Supplementary_Data_S1.xlsx (sheets 'Recommendations', 'Corpus', 'Chain_members')
Output: results.json (all computed values) and a PASS/FAIL list on screen

Usage : python reproduce_analysis.py [path/to/Supplementary_Data_S1.xlsx]
Needs : pandas, numpy, scipy, statsmodels, scikit-learn, openpyxl
Runtime: about one minute (5,000 permutations x 2 and 10,000 bootstrap draws x 2)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

XLSX = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Supplementary_Data_S1.xlsx")
R = {}          # every computed value, written to results.json
CHECKS = []     # (label, computed, value printed in the paper)


def check(label, value, paper, tol=0.051):
    CHECKS.append((label, value, paper, abs(float(value) - float(paper)) <= tol))


def pct(x):
    return round(100 * float(x), 1)


# =============================================================================
# Data
# =============================================================================
rec = pd.read_excel(XLSX, sheet_name="Recommendations", header=3, keep_default_na=False)
rec["Accident date"] = pd.to_datetime(rec["Accident date"])
corpus = pd.read_excel(XLSX, sheet_name="Corpus", header=3)
corpus = corpus[corpus["Report ID"].astype(str).str.match(r"^(9N|TC|S2)-")]
members = pd.read_excel(XLSX, sheet_name="Chain_members", header=3)
members["Accident date"] = pd.to_datetime(members["Accident date"])

yes = lambda col: rec[col].eq("Yes")
rec["mand"] = rec["Directive force"].eq("Mandatory").astype(int)
rec["conc"] = rec["Type of action"].eq("Discrete action").astype(int)
rec["gen"] = rec["Actor specificity"].eq("Generic").astype(int)
rec["broad"] = yes("Broad reissue (same problem)").astype(int)
rec["strict"] = yes("Strict reissue (same remedy)").astype(int)
rec["state"] = rec["Addressee level"].eq("State").astype(int)
# accident date as a continuous variable, in years, centred on 2018
rec["yc"] = rec["Accident date"].dt.year + rec["Accident date"].dt.dayofyear / 365.25 - 2018
N = len(rec)
check("Recommendations", N, 269, 0)
check("Reports", rec["Report ID"].nunique(), 18, 0)

# =============================================================================
# 3.1 Output and timeliness
# =============================================================================
per = rec.groupby("Report ID").size()
R["recs_per_report"] = {"median": float(per.median()), "min": int(per.min()), "max": int(per.max())}
check("Median recommendations per report", per.median(), 13.5)
check("Interim recommendations", (rec["Type"] == "Interim").sum(), 11, 0)

cat = corpus.set_index("Report ID")["Category"]
byc = per.groupby(cat.reindex(per.index)).agg(["median", "sum", "count"])
R["recs_by_aircraft"] = byc.to_dict()
check("Median recs, aeroplane reports", byc.loc["Aeroplane", "median"], 15)
check("Median recs, helicopter reports", byc.loc["Helicopter", "median"], 8.5)

days = (pd.to_datetime(corpus["Report date used"]) - pd.to_datetime(corpus["Accident date"])).dt.days.dropna()
R["timeliness"] = {"dated_reports": int(len(days)), "median_days": float(days.median()),
                   "min": int(days.min()), "max": int(days.max()), "within_365": int((days <= 365).sum())}
check("Reports with a printed date", len(days), 14, 0)
check("Median days to printed date", days.median(), 279, 0)
check("Printed dates within 365 days", (days <= 365).sum(), 12, 0)

rep = rec.groupby("Report ID").agg(date=("Accident date", "min"), n=("Rec ID", "size"),
                                   mand=("mand", "mean"), conc=("conc", "mean"), gen=("gen", "mean"))
R["kendall"] = {}
for col in ["n", "mand", "conc", "gen"]:
    t = stats.kendalltau(rep["date"].map(pd.Timestamp.toordinal), rep[col])
    R["kendall"][col] = {"tau": round(t.statistic, 3), "p": round(t.pvalue, 4)}
check("Kendall tau, recs per report vs date", R["kendall"]["n"]["tau"], -0.20, 0.006)
check("Kendall p, recs per report vs date", R["kendall"]["n"]["p"], 0.25, 0.006)

# =============================================================================
# 3.2 Addressees and system level
# =============================================================================
R["addressee_category"] = rec["Addressee category"].value_counts().to_dict()
R["addressee_level"] = rec["Addressee level"].value_counts().to_dict()
check("CAAN recommendations", R["addressee_category"]["Regulator (CAAN)"], 102, 0)
check("Named operator recommendations", R["addressee_category"]["Named operator"], 78, 0)
check("All-operator recommendations", R["addressee_category"]["All operators (sector-wide)"], 41, 0)
check("State recommendations", R["addressee_level"]["State"], 18, 0)

role = rec.loc[rec["Addressee level"] == "Regulator", "CAAN role"].value_counts()
R["caan_role"] = role.to_dict()
check("CAAN as regulator", role["Regulator"], 75, 0)
check("CAAN as service provider", role["Service provider"], 27, 0)
rr = rec[rec["Addressee level"] == "Regulator"].groupby("CAAN role")["broad"].mean()
check("Broad reissue %, CAAN regulator role", pct(rr["Regulator"]), 25.3)
check("Broad reissue %, CAAN service role", pct(rr["Service provider"]), 0.0)

sl = rec["System level"].value_counts()
R["system_level"] = sl.to_dict()
for lev, n in [("Micro", 30), ("Meso", 136), ("Macro", 103)]:
    check(f"{lev}-level recommendations", sl[lev], n, 0)
check("Operator recs at micro level", ((rec["Addressee level"] == "Operators") & (rec["System level"] == "Micro")).sum(), 12, 0)

# =============================================================================
# 3.3 Framing (Table 4) and change over time
# =============================================================================
fc = rec["Directive force"].value_counts()
R["framing"] = {"force": fc.to_dict(), "timeframe": rec["Timeframe"].value_counts().to_dict(),
                "discrete": int(rec["conc"].sum()), "generic": int(rec["gen"].sum())}
check("Advisory %", pct(fc["Advisory"] / N), 71.4)
check("Mandatory %", pct(fc["Mandatory"] / N), 23.0)
check("Weak %", pct(fc["Weak"] / N), 5.6)
check("Discrete action %", pct(rec["conc"].mean()), 42.4)
check("Generic addressee %", pct(rec["gen"].mean()), 17.8)
check("Deadlines stated", (rec["Timeframe"] == "Deadline").sum(), 0, 0)
check("Urgency word only", (rec["Timeframe"] == "Urgency only").sum(), 17, 0)
check("Discrete action %, State", pct(rec.loc[rec.state == 1, "conc"].mean()), 61.1)

table4 = {}
for lev in ["State", "Regulator", "Operators", "Other bodies", "All"]:
    d = rec if lev == "All" else rec[rec["Addressee level"] == lev]
    table4[lev] = {"n": len(d), "micro": int((d["System level"] == "Micro").sum()),
                   "meso": int((d["System level"] == "Meso").sum()), "macro": int((d["System level"] == "Macro").sum()),
                   "mandatory": int(d.mand.sum()), "advisory": int((d["Directive force"] == "Advisory").sum()),
                   "weak": int((d["Directive force"] == "Weak").sum()), "discrete": int(d.conc.sum()),
                   "urgency_only": int((d["Timeframe"] == "Urgency only").sum()), "generic": int(d.gen.sum()),
                   "in_chain": int(yes("In recurrence chain")[d.index].sum()),
                   "broad": int(d.broad.sum()), "strict": int(d.strict.sum())}
R["table4"] = table4

ame = rec[rec["Report ID"] == "9N-AME"]
e3x = rec[(rec["Period"] == "2022–25") & (rec["Report ID"] != "9N-AME")]
check("Mandatory %, 9N-AME", pct(ame.mand.mean()), 79.6)
check("Mandatory %, other 2022-25 reports", pct(e3x.mand.mean()), 2.6)

# chi-square by period, with permutation p (descriptive; reported in the dataset)
R["chi_square_by_period"] = {}
rng_perm = np.random.default_rng(1)
for col in ["Directive force", "Type of action", "Actor specificity", "Timeframe"]:
    ct = pd.crosstab(rec["Period"], rec[col])
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    res = {"chi2": round(chi2, 2), "dof": int(dof), "p": round(p, 4),
           "cramers_v": round(np.sqrt(chi2 / (N * (min(ct.shape) - 1))), 3)}
    if col in ("Directive force", "Type of action"):
        e, y, cnt = rec["Period"].values, rec[col].values, 0
        for _ in range(5000):
            cnt += stats.chi2_contingency(pd.crosstab(rng_perm.permutation(e), y))[0] >= chi2
        res["p_perm"] = round((cnt + 1) / 5001, 4)
    R["chi_square_by_period"][col] = res

# GEE: logistic, exchangeable working correlation, clustered by report
def gee(formula, data, term):
    m = smf.gee(formula, groups="Report ID", data=data, family=sm.families.Binomial(),
                cov_struct=sm.cov_struct.Exchangeable()).fit()
    ci = m.conf_int().loc[term]
    return {"OR": round(float(np.exp(m.params[term])), 3),
            "CI": [round(float(np.exp(ci[0])), 3), round(float(np.exp(ci[1])), 3)],
            "p": round(float(m.pvalues[term]), 4)}

R["gee_trend"] = {}
noame = rec[rec["Report ID"] != "9N-AME"]
for y in ["mand", "conc", "gen"]:
    for lab, d in [("all", rec), ("exAME", noame)]:
        R["gee_trend"][f"{y}_{lab}"] = gee(f"{y} ~ yc", d, "yc")
g = R["gee_trend"]
for key, (o, lo, hi) in {"conc_all": (1.09, 1.01, 1.19), "conc_exAME": (1.06, 0.96, 1.16),
                         "mand_all": (1.04, 0.79, 1.38), "mand_exAME": (0.82, 0.71, 0.95),
                         "gen_all": (1.14, 0.98, 1.31)}.items():
    check(f"GEE OR per year, {key}", g[key]["OR"], o, 0.006)
    check(f"GEE CI lower, {key}", g[key]["CI"][0], lo, 0.006)
    check(f"GEE CI upper, {key}", g[key]["CI"][1], hi, 0.006)

# cluster bootstrap: resample reports within the first and last periods
rng = np.random.default_rng(7)
agg = rec.groupby("Report ID").agg(period=("Period", "first"), n=("Rec ID", "size"),
                                   m=("mand", "sum"), c=("conc", "sum"))
R["bootstrap"] = {}
for lab in ["all", "exAME"]:
    a = agg if lab == "all" else agg.drop("9N-AME")
    grp = {p: a[a.period == p][["n", "m", "c"]].values for p in ["2012–16", "2022–25"]}
    share = lambda x: x[:, 1:].sum(0) / x[:, 0].sum()
    obs = share(grp["2022–25"]) - share(grp["2012–16"])
    draws = []
    for _ in range(10000):
        s = []
        for p in ["2022–25", "2012–16"]:
            x = grp[p][rng.integers(0, len(grp[p]), len(grp[p]))]
            s.append(share(x))
        draws.append(s[0] - s[1])
    d = np.array(draws)
    R["bootstrap"][lab] = {
        "mandatory": {"diff": round(obs[0] * 100, 1), "CI": [round(np.percentile(d[:, 0], 2.5) * 100, 1), round(np.percentile(d[:, 0], 97.5) * 100, 1)]},
        "discrete": {"diff": round(obs[1] * 100, 1), "CI": [round(np.percentile(d[:, 1], 2.5) * 100, 1), round(np.percentile(d[:, 1], 97.5) * 100, 1)]}}
b = R["bootstrap"]
check("Bootstrap CI lower, discrete, all", b["all"]["discrete"]["CI"][0], -3.3)
check("Bootstrap CI upper, discrete, all", b["all"]["discrete"]["CI"][1], 37.8)
check("Bootstrap CI lower, discrete, excl. AME", b["exAME"]["discrete"]["CI"][0], -11.5)
check("Bootstrap CI upper, discrete, excl. AME", b["exAME"]["discrete"]["CI"][1], 30.9)

# =============================================================================
# 3.4 Recurrence
# =============================================================================
later = rec[rec["Accident date"] > rec["Accident date"].min()]
nl = len(later)
R["recurrence"] = {"chains": int(members["Chain"].nunique()), "in_chain": int(yes("In recurrence chain").sum()),
                   "later_recs": nl, "broad": int(rec.broad.sum()), "strict": int(rec.strict.sum()),
                   "share_broad": pct(rec.broad.sum() / nl), "share_strict": pct(rec.strict.sum() / nl)}
check("Recurrence chains", R["recurrence"]["chains"], 16, 0)
check("Recommendations in chains", R["recurrence"]["in_chain"], 85, 0)
check("Recommendations after the first report", nl, 254, 0)
check("Broad reissues", R["recurrence"]["broad"], 64, 0)
check("Strict reissues", R["recurrence"]["strict"], 38, 0)
check("Broad reissue share %", R["recurrence"]["share_broad"], 25.2)
check("Strict reissue share %", R["recurrence"]["share_strict"], 15.0)
check("Reports contributing to chains", members["Report ID"].nunique(), 15, 0)

m = members.copy()
ev_b = m[m["Status in chain"] != "First issue"][["Chain", "Report ID"]].drop_duplicates()
ev_s = m[m["Status in chain"] == "Strict reissue"][["Chain", "Report ID"]].drop_duplicates()
R["recurrence"].update({"events_broad": len(ev_b), "events_strict": len(ev_s),
                        "reports_with_broad": int(rec.loc[rec.broad == 1, "Report ID"].nunique()),
                        "reports_with_strict": int(rec.loc[rec.strict == 1, "Report ID"].nunique()),
                        "chains_with_strict": int(ev_s["Chain"].nunique())})
check("Report-level events, broad", len(ev_b), 52, 0)
check("Report-level events, strict", len(ev_s), 38, 0)
check("Reports with a broad reissue", R["recurrence"]["reports_with_broad"], 13, 0)
check("Reports with a strict reissue", R["recurrence"]["reports_with_strict"], 12, 0)
check("Chains with a strict reissue", R["recurrence"]["chains_with_strict"], 15, 0)

lx = noame[noame["Accident date"] > noame["Accident date"].min()]
R["recurrence"]["exAME"] = {"share_broad": pct(noame.broad.sum() / len(lx)), "share_strict": pct(noame.strict.sum() / len(lx))}
check("Broad reissue share %, excl. AME", R["recurrence"]["exAME"]["share_broad"], 26.3)
check("Strict reissue share %, excl. AME", R["recurrence"]["exAME"]["share_strict"], 16.1)

# chain spans (Table 5, Figure 3)
spans = members.groupby("Chain")["Accident date"].agg(["min", "max"])
R["chain_span_years"] = ((spans["max"] - spans["min"]).dt.days / 365.25).round(1).to_dict()
check("CH01 span (years)", R["chain_span_years"]["CH01"], 11.2)
check("CH01 reports", members.loc[members.Chain == "CH01", "Report ID"].nunique(), 7, 0)

# similarity screen: TF-IDF cosine similarity on the verbatim texts
texts = rec["Recommendation text (verbatim)"].tolist()
S = cosine_similarity(TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit_transform(texts))
pos = {r: i for i, r in enumerate(rec["Rec ID"])}
dates = rec["Accident date"].values

def best_earlier(row):
    grp = members[(members.Chain == row.Chain) & (members["Accident date"] < row["Accident date"])]
    return max(S[pos[y], pos[row["Rec ID"]]] for y in grp["Rec ID"])

reiss = members[members["Status in chain"] != "First issue"].copy()
reiss["best"] = reiss.apply(best_earlier, axis=1)
ms_s = reiss.loc[reiss["Status in chain"] == "Strict reissue", "best"].values
ms_b = reiss["best"].values
R["recall"] = {t: {"strict": pct((ms_s >= t).mean()), "broad": pct((ms_b >= t).mean()),
                   "candidate_pairs": int(((dates[:, None] < dates[None, :]) & (S >= t)).sum())}
               for t in (0.2, 0.3, 0.4, 0.5)}
R["median_best_similarity_strict"] = round(float(np.median(ms_s)), 2)
check("Recall of screen at 0.30, strict %", R["recall"][0.3]["strict"], 48.8)
check("Recall of screen at 0.30, broad %", R["recall"][0.3]["broad"], 31.9)
check("Recall of screen at 0.20, strict %", R["recall"][0.2]["strict"], 55.8)
check("Recall of screen at 0.20, broad %", R["recall"][0.2]["broad"], 39.1)
band = int(((dates[:, None] < dates[None, :]) & (S >= 0.18) & (S < 0.30)).sum())
check("Cross-report pairs with similarity 0.18-0.30", band, 14, 0)
check("Similarity CH01: 9N-ANC-09 vs 9N-AME-44", round(S[pos["9N-ANC-09"], pos["9N-AME-44"]], 2), 0.93, 0.006)
check("Similarity CH09: 9N-AHH-04 vs 9N-AMI-03", round(S[pos["9N-AHH-04"], pos["9N-AMI-03"]], 2), 0.78, 0.006)

# State versus other addressees
def two_by_two(y):
    s = rec.state == 1
    return [[int((s & (rec[y] == 1)).sum()), int((s & (rec[y] == 0)).sum())],
            [int((~s & (rec[y] == 1)).sum()), int((~s & (rec[y] == 0)).sum())]]

R["state_vs_others"] = {}
for y in ["broad", "strict"]:
    tab = two_by_two(y)
    orr, p = stats.fisher_exact(tab)
    R["state_vs_others"][y] = {"table": tab, "fisher_OR": round(orr, 2), "fisher_p": round(p, 4),
                               "gee": gee(f"{y} ~ state", later, "state")}
sv = R["state_vs_others"]
check("Strict reissue %, State", pct(rec.loc[rec.state == 1, "strict"].mean()), 55.6)
check("Strict reissue %, CAAN", pct(rec.loc[rec["Addressee level"] == "Regulator", "strict"].mean()), 7.8)
check("Strict reissue %, operators", pct(rec.loc[rec["Addressee level"] == "Operators", "strict"].mean()), 15.4)
check("GEE OR State, strict", sv["strict"]["gee"]["OR"], 8.37, 0.006)
check("GEE CI State, strict, lower", sv["strict"]["gee"]["CI"][0], 3.28, 0.006)
check("GEE CI State, strict, upper", sv["strict"]["gee"]["CI"][1], 21.37, 0.006)
check("GEE OR State, broad", sv["broad"]["gee"]["OR"], 4.07, 0.006)
check("GEE CI State, broad, lower", sv["broad"]["gee"]["CI"][0], 1.43, 0.006)
check("GEE CI State, broad, upper", sv["broad"]["gee"]["CI"][1], 11.55, 0.006)
check("Fisher p, State, broad", sv["broad"]["fisher_p"], 0.003, 0.0006)

# recurrence by system level
bl = rec.groupby("System level")["broad"].mean()
chi2, p, _, _ = stats.chi2_contingency(pd.crosstab(rec["System level"], rec["broad"]))
R["broad_by_system_level"] = {"pct": (bl * 100).round(1).to_dict(), "chi2": round(chi2, 2), "p": round(p, 4)}
check("Broad reissue %, micro", pct(bl["Micro"]), 3.3)
check("Broad reissue %, meso", pct(bl["Meso"]), 24.3)
check("Broad reissue %, macro", pct(bl["Macro"]), 29.1)
check("Chi-square, broad reissue x system level", chi2, 8.56, 0.006)
check("p, broad reissue x system level", p, 0.014, 0.0006)

# =============================================================================
# 3.6 CAAN self-reported figures (as published; Aviation Safety Report 2020)
# =============================================================================
check("CAAN 2020 complied %", pct(157 / 206), 76.2)

# =============================================================================
# Report
# =============================================================================
json.dump(R, open("results.json", "w"), indent=1, default=str)
fails = [c for c in CHECKS if not c[3]]
w = max(len(c[0]) for c in CHECKS)
for lab, v, p, ok in CHECKS:
    print(f"{'PASS' if ok else 'FAIL'}  {lab:<{w}}  computed {v!s:>8}   paper {p}")
print(f"\n{len(CHECKS) - len(fails)} of {len(CHECKS)} values in the paper reproduced. Full results in results.json.")
