# Project-GitHub-Archive-Analytics-Pipeline
Welcome! 🚀
This project demonstrates a production-grade data engineering project implementing a three-tier **Medallion Architecture** (Bronze, Silver, Gold) using PySpark and Delta Lake. This pipeline transforms raw GitHub event data into high-value analytical tables and a real-time Streamlit dashboard. 

---

## 🏗️ Pipline Architecture
The project follows a modular, watermarked batch processing pattern to ensure reliability and idempotency:

- **Landing:** Entry point for raw .json.gz GitHub Archive files.  
- **Bronze:** Long-term cold storage for immutable raw data.  
- **Silver:** High-fidelity Data Lakehouse layer featuring:
    - **Fact Events:** Partitioned by date, year, month, and day for query optimization.
    - **Normalized Dimensions:** Structured tables for dim_actor, dim_org, and dim_repo.
- **Gold:** Business-level aggregates including daily activity trends, bot-vs-human behavior, and Pull Request (PR) funnel analysis.

---
## 🛠️ Key Technical Features
- **Idempotent Ingestion:** A custom watermark orchestrator tracks processed files to prevent data duplication and allow for safe re-runs.
- **ACID Transactions:** Leverages Delta Lake for schema enforcement and atomic MERGE operations.
- **Advanced Analytics:**
  - **Bot Detection:** Regex-based identification of automated actors (e.g., Dependabot, GitHub Actions) to provide clean human-only metrics.
  - **Incremental Processing:** The Gold layer recomputes only for new dates detected by the watermark, significantly reducing compute costs.
- **Interactive Visualization:** A custom-themed Streamlit dashboard providing deep insights into repository performance, developer leaderboards, and automation rates.

---

## 📊 Analytics Dashboard
The dashboard utilizes Streamlit to visualize the Gold tables:
- **KPI Overview:** Real-time metrics for total events, unique actors, and bot traffic percentages.
- **PR Funnel:** Visualization of the PR lifecycle from creation to review and completion.
- **Automation Insights:** Comparative analysis of human vs. bot activity across different event types.
- **Raw Data Explorer:** Direct interface to query and download Gold layer data as CSVs.

---

## 🗺️ Roadmap (v2 Upgrade Path)

- **Cloud Migration:** Transition local paths to cloud storage (e.g., AWS S3 or Azure ADLS).  - **Orchestration:** Wrap the pipeline in Apache Airflow for scheduled automation.
- **Streaming:** Transition from batch to Structured Streaming (Kappa Architecture) for real-time ingestion. 

---

## 🌟 About Me

Hi there! I'm Bhargav. I'm an IT professional and a Data Engineering enthusiast, aspiring to work in a challenging environment. I’m passionate about data, problem-solving, and building efficient solutions.
