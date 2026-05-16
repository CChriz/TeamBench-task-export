---
title: TeamBench Leaderboard
emoji: 📊
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "5.12.0"
python_version: "3.12"
app_file: app.py
pinned: true
license: mit
---

# TeamBench Leaderboard

Multi-agent benchmark evaluating LLM teamwork with OS-enforced role separation.

## Running locally

```bash
cd leaderboard
pip install -r requirements.txt
python app.py
```

The app loads data from `data/leaderboard_data.json` (per-model TeamBench-90 results). `data/cross_model_stats.json` holds the role-mixing breakdown used in the cross-provider tab.
