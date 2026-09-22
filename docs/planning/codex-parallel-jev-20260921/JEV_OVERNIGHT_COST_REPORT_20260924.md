# JEV Overnight Cost Report

**Date**: 2026-09-23/24  
**Basis**: estimated Jev input × rate; OpenAI intent path measured_proxy — **not invoice**

| Run | Jev ¥ est | OpenAI intent proxy ¥ | Notes |
| --- | ---: | ---: | --- |
| holdout r3 seed42 | 0.228 | 0.127 | small batch |
| holdout r10 seed42 | 0.760 | 0.423 | net proxy negative vs Jev est (label mismatch OK) |
| eval_10 r10 seed20260922 post-trim | 0.582 | 0.852 | api_err=0 |

No runaway retries observed. Cost not used for Gate pass/fail.
