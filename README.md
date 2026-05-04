# 🐙 GitHub Archive — Analytics Pipeline

![Status](https://img.shields.io/badge/Status-v1.0%20Complete-brightgreen)
![PySpark](https://img.shields.io/badge/PySpark-3.4-orange)
![Delta Lake](https://img.shields.io/badge/Delta%20Lake-2.2-blue)
![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red)
![Python](https://img.shields.io/badge/Python-3.10%2B-green)
![Architecture](https://img.shields.io/badge/Architecture-Medallion-purple)

A production-grade data engineering pipeline that ingests raw GitHub Archive events, processes them through a **Medallion Architecture** (Bronze → Silver → Gold) and serves business insights through an interactive **Streamlit dashboard**.

> **Note:** This project was built with AI-assisted development (Claude by Anthropic).
> All architectural decisions, performance trade-offs and data engineering design
> were driven by my own understanding and requirements throughout the build.

---

## 🏗️ Architecture

```
landing/                    bronze/                   silver/                  gold/
──────────────────────────────────────────────────────────────────────────────────────
.json files            →   immutable raw store   →   fact_events          →   gold_daily_activity
dropped here               files moved here           (partitioned                gold_event_type_trends
                           after processing           year / month / day)         gold_top_repos
                                                                                  gold_actor_summary
                                                   dim_actor (SCD-1)             gold_org_leaderboard
                                                   dim_org   (SCD-1)             gold_pr_funnel
                                                   dim_repo  (SCD-1)             gold_bot_vs_human
                                                   watermark (file names)
                                                                             gold/watermark (timestamp)
```

**Run behaviour at a glance**

| Scenario | What happens |
|---|---|
| Landing has new files | Processed → moved to bronze → Silver merged → Gold updated for new dates |
| Landing is empty | Prints "nothing to do" and exits cleanly |
| Same file dropped again | Watermark detects duplicate → skipped silently |
| New day arrives | Only that day recomputed in Gold — all historical partitions untouched |

---

## ⚙️ Key Design Decisions

Every decision below was a deliberate trade-off not a default.

**Why Delta Lake over plain Parquet?**
Delta gives ACID transactions and the `MERGE` operation. Silver dimension tables use SCD Type-1 merge on each run the pipeline upserts without duplicates. Plain Parquet has no merge primitive; you would have to rewrite the full table every run.

**Why denormalise `actor_login`, `repo_name`, `org_login` into `fact_events`?**
Gold aggregations need names alongside IDs. Joining fact rows to dimension tables at Gold compute time causes expensive shuffle on every run. These strings already exist in the raw data so the cost of including them in the fact table at Silver write time is zero. Gold becomes pure `GROUP BY` with no joins and no shuffle.

**Why `approx_count_distinct` instead of `COUNT DISTINCT`?**
Exact `COUNT DISTINCT` requires a full shuffle to collect all values across executors. `approx_count_distinct` uses the HyperLogLog algorithm (~5% relative error) and eliminates that shuffle entirely. A 5% error is completely acceptable for a BI dashboard KPI.

**Why partition Gold by `event_date` on some tables but not others?**
Tables like `gold_daily_activity` grow one row per day — partitioning lets the dashboard read only the requested date's folder. Tables like `gold_top_repos` are always full window snapshots where every query needs all data. Partitioning those would create small file problems with no read benefit.

**Why `partitionOverwriteMode=dynamic` on Gold writes?**
Without it, `mode=overwrite` replaces the entire table even when only one new day was written. Dynamic mode restricts the overwrite to only the partitions present in the current batch historical partitions are never touched.

**Why `event_year` in the Silver MERGE condition?**
Delta Lake uses partition pruning during MERGE. If the join condition includes a partition column, Delta only opens the relevant partition folders instead of scanning the whole table. At large scale the difference is seconds vs minutes.

---

## 📊 Silver Layer — Star Schema

```
                    ┌─────────────┐
                    │  dim_actor  │
                    │  actor_id PK│
                    └──────┬──────┘
                           │
┌────────────┐    ┌────────┴────────┐    ┌────────────┐
│  dim_org   │    │  fact_events    │    │  dim_repo  │
│  org_id PK ├────┤  event_id  PK   ├────┤  repo_id PK│
└────────────┘    │  event_type     │    └────────────┘
                  │  actor_id  FK   │
                  │  actor_login  * │  ← denormalised
                  │  org_id    FK   │
                  │  org_login    * │  ← denormalised
                  │  repo_id   FK   │
                  │  repo_name    * │  ← denormalised
                  │  is_bot         │
                  │  event_date     │
                  │  ingestion_ts   │
                  └─────────────────┘
  * denormalised into fact so Gold needs zero joins
```

**QA gates run after every Silver load:**
- Fact duplicate keys
- Null `event_type`, `actor_id`, `created_at_ts`
- Duplicate primary keys in all 3 dims
- Orphan fact rows with no matching `dim_repo`

Gold does not run if any check fails.

---

## 📈 Gold Layer — 7 Business Tables

| Table | Answers | Write strategy |
|---|---|---|
| `gold_daily_activity` | How active is GitHub each day? | Incremental by `event_date` |
| `gold_event_type_trends` | How do event types trend + day-over-day change? | Incremental by `event_date` |
| `gold_pr_funnel` | What does the PR review lifecycle look like? | Incremental by `event_date` |
| `gold_bot_vs_human` | What share of GitHub is automated? | Incremental by `event_date` |
| `gold_top_repos` | Which repos attract the most activity? | Full overwrite, rolling 90 days |
| `gold_actor_summary` | Who are the most productive developers? | Full overwrite, rolling 90 days |
| `gold_org_leaderboard` | Which organisations drive the most contributions? | Full overwrite, rolling 90 days |

---

## 📊 Dashboard

Built with Streamlit and Plotly. Reads Gold Delta tables directly via the `deltalake` Python library — no Spark session needed at dashboard runtime.

**8 sections:**

| Section | Source table |
|---|---|
| KPI cards — events, actors, repos, bot % | `gold_daily_activity` |
| Daily stacked bar by event type | `gold_daily_activity` |
| Bot vs human donut | `gold_bot_vs_human` |
| PushEvent spotlight + log/linear toggle | `gold_event_type_trends` |
| Day-over-day % change | `gold_event_type_trends` |
| Top repos + org leaderboard | `gold_top_repos` · `gold_org_leaderboard` |
| PR funnel + daily review ratio | `gold_pr_funnel` |
| Developer leaderboard (human / bot tabs) | `gold_actor_summary` |
| Bot automation rate by event type | `gold_bot_vs_human` |
| Raw data explorer + CSV download | all 7 tables |

**Run the dashboard:**
```bash
streamlit run dashboard/dashboard.py
```

---

## 🗺️ Roadmap

| Version | Status | What |
|---|---|---|
| **v1** | ✅ Complete | Batch pipeline · local Spark · watermarked · Streamlit dashboard |
| **v1.5** | 🔜 Next | Apache Airflow orchestration · scheduled DAG · parameterised refill DAG |
| **v2** | 📋 Planned | Cloud storage (S3 / ADLS) · Spark Structured Streaming · Kappa architecture · dbt Gold |

**v1.5 upgrade is one file away.** The entire pipeline is a single `run_pipeline()` function with no notebook-specific dependencies. Wrapping it in an Airflow DAG requires one thin 10-line DAG file — zero pipeline logic changes.

**v2 Kappa upgrade** replaces `spark.read.json(files)` with `spark.readStream` consuming from Kafka or S3 event notifications. Every transform function from `_expand()` onwards stays unchanged.

---

## 📁 Repository Structure

```
github-archive-pipeline/
│
├── notebooks/
│   ├── github_pipeline_v1.ipynb   # Full Bronze → Silver → Gold pipeline
│   └── gold_layer.ipynb           # Gold logic reference
│
├── dashboard/
│   └── dashboard.py               # Streamlit dashboard
│
│
└── README.md
```

---

## 👤 About

Hi, I'm Bhargav — a Data Engineering enthusiast building production-grade pipelines. Passionate about distributed systems, data reliability, and turning raw data into business value at scale.
