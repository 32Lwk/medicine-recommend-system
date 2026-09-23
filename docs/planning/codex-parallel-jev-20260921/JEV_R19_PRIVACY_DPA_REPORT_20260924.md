# JEV R19 Privacy / DPA Report — TypeSafe System One

**Role:** Privacy Challenger (R19+) — independent re-verification of Worker C findings  
**Report date:** 2026-09-24 (original Worker C)  
**Challenger re-verify:** 2026-09-23 (official pages only; no invent Confirmed)  
**Endpoint in repo:** `https://api.typesafe.ai/v1/systemone`  
**Scope:** Primary-source research (official Privacy Policy / DPA / MCA / docs / Trust Center HTTP) + production payload boundary notes.  
**Go/No-Go:** ❌ **Still BLOCKING** for production shadow / live IntentRouter traffic.

Classification legend: **Confirmed** | **Contract-dependent** | **Unknown** | **Blocking**.

---

## 1. Verdict

| Gate | Result |
|---|---|
| Overall privacy/DPA for production enablement | **BLOCKING** |
| Public DPA document exists | **Confirmed** |
| Fixed retention TTL / ZDR for *our* account | **Blocking** (not confirmed) |
| Named subprocessor inventory (static/public) | **Unknown → Blocking** |
| MCA/Order binding for medicine-recommend | **Contract-dependent → Blocking** until Owner confirms |
| Free-text PII scrub + payload minimization in code | **Implemented** (prior Worker; heuristic; residual FN risk) — *not re-audited this Challenger pass* |

**Bottom line (Challenger):** Official legal pages were re-fetched and key clauses re-extracted. Training-on-Input denial and public DPA/MCA text remain **Confirmed**. **Numeric retention / account ZDR remain Unknown → Production Shadow stays BLOCKING.** Do not treat public legal HTML as proof that medicine-recommend’s Order elected ZDR or accepted Schedule I as-is for health-adjacent free text.

---

## 2. Sources (official only) — Challenger HTTP check 2026-09-23

| Document | URL | Status | Notes |
|---|---|---|---|
| Privacy Policy | https://typesafe.ai/privacy · https://typesafe.ai/legal/privacy-policy | **200** | Last updated **2025-11-19** (`<time datetime="2025-11-19">`) |
| Data Processing Addendum (DPA) | https://typesafe.ai/legal/data-processing · https://typesafe.ai/data-processing | **200** | Last updated **2026-04-24** |
| Master Customer Agreement (MCA) | https://typesafe.ai/legal/mca | **200** | Last updated **2026-09-19** |
| Docs Legal index | https://docs.typesafe.ai/legal · https://docs.typesafe.ai/legal.md | **200** | ZDR enterprise offer stated |
| Docs index | https://docs.typesafe.ai/llms.txt | **200** | |
| API reference | https://docs.typesafe.ai/api.md | **200** | `POST https://api.typesafe.ai/v1/systemone` |
| State guidance | https://docs.typesafe.ai/concepts/state.md | **200** | No retention TTL |
| Trust Center | https://trust.typesafe.ai/ | **200** | Vanta SPA; static body ≈ title only |
| Subprocessors (DPA-referenced) | https://trust.typesafe.ai/subprocessors | **200** | Same SPA; **named list not Confirmed** |
| Status | https://status.typesafe.ai/ | **200** | Availability only |

**404 (not public HTML):** `/security`, `/dpa`, `/legal/dpa`, `/legal/data-processing-addendum`.  
**Not Confirmed:** blog / marketing claims.

---

## 3. Findings matrix (Challenger classification)

### 3.1 Training usage

| Finding | Class | Evidence (official) |
|---|---|---|
| Will not train / fine-tune on customer **Input** | **Confirmed** | Privacy Policy: “We will not train or fine tune any artificial intelligence or machine learning models on your prompts or other Input.” Also: will not train on Input; disclose Input only to service providers (paraphrase of paired clause). |
| No Customer Data in training datasets without prior consent | **Confirmed** | MCA §4.1: will not “include Customer Data in a dataset used to train (i.e., to modify the model weights of) any artificial intelligence or machine learning models without Customer’s prior consent.” |
| Telemetry may be processed without restriction (incl. improve Services) | **Confirmed** | MCA §4.3: Telemetry = technical logs, hashes, summary statistics, classifications, metrics, learnings; “Process Telemetry without restriction, including to improve the Services…” — **not** model-weight training, but derived metrics may persist. |

### 3.2 Retention

| Finding | Class | Evidence |
|---|---|---|
| Privacy Policy retention = “as long as reasonably necessary” | **Confirmed** (criterion only) | Privacy Policy Retention section — **no fixed day count**. |
| DPA Schedule I Duration of Processing = criteria-only | **Confirmed** (criterion only) | Schedule I §8: retained “for as long as necessary taking into account the purpose of the Processing…” — **no fixed TTL**. |
| Zero Data Retention (ZDR) offered for enterprise | **Contract-dependent** | Docs Legal: “We also offer zero data retention (ZDR) for enterprise customers. Contact privacy@typesafe.ai.” **Not Confirmed** that medicine-recommend has ZDR. |
| MCA: no obligation to store/retain; may delete at sole discretion | **Confirmed** | MCA §10.3 Effect of Termination — **vendor discretion**, not a customer deletion SLA. |
| Per-request / log TTL for System One API | **Unknown → Blocking** | No public numeric Input/log retention in Privacy / DPA / MCA / API / State docs (re-searched 2026-09-23). |

### 3.3 Deletion / data subject rights

| Finding | Class | Evidence |
|---|---|---|
| Deletion on request (Privacy Policy) | **Confirmed** (process) | “…When you request that we do so, we take measures to delete…” — **no SLA**. |
| DPA: processor forwards DSAR; assists | **Confirmed** | DPA Data Subject Rights: promptly forward requests; assist Customer. |
| Customer-triggered purge SLA / API delete endpoint | **Unknown** | Not found in public API docs. |
| Backups may retain Confidential Information | **Confirmed** | MCA §10.3 backups carve-out. |

### 3.4 Region / transfers

| Finding | Class | Evidence |
|---|---|---|
| Services hosted in the United States | **Confirmed** | Privacy Policy International Visitors: “The Services are hosted in the United States…” |
| EU/UK transfers via SCCs / UK Addendum | **Confirmed** (contract text) | DPA international transfer / SCC provisions. |
| Japan APPI-specific clauses | **Unknown** | No APPI / Japan adequacy mapping found on Privacy / DPA / MCA HTML (string search). |
| Subprocessor geography / named list | **Unknown → Blocking** | DPA authorizes subprocessors at `https://trust.typesafe.ai/subprocessors`; static fetch has Vanta shell only — **no named vendors Confirmed**. |

### 3.5 DPA / contract applicability

| Finding | Class | Evidence |
|---|---|---|
| Public DPA text exists | **Confirmed** | https://typesafe.ai/legal/data-processing |
| MCA incorporates DPA by reference | **Confirmed** | MCA §4.4 → https://typesafe.ai/data-processing |
| Whether medicine-recommend’s account accepted MCA/Order | **Contract-dependent → Blocking** | Not in public pages / not inventable from repo. |
| Schedule I §4 Sensitive Data → **N/A** | **Blocking** (product mismatch risk) | Exact public text ends: “…restrictions for onward transfers or additional security measures: **N/A**.” OTC symptom free-text may be health-related personal data; Schedule I marks sensitive transfer/safeguards as N/A. Needs legal acceptance or amendment — **not Confirmed as OK for our payload**. |

### 3.6 Security / subprocessors

| Finding | Class | Evidence |
|---|---|---|
| Security Measures pointed to Trust Center | **Confirmed** (pointer only) | DPA references Trust Center `https://trust.typesafe.ai/` for security description of Personal Data protection. |
| Security incident notify ≤ 72h | **Confirmed** | DPA §5.2: within 72 hours after becoming aware. |
| Named subprocessors | **Unknown → Blocking** | URL exists; content not Confirmed without interactive Trust Center. |
| SOC2 / ISO certificate text | **Unknown** | Not statically readable from Trust Center HTML. |

---

## 4. What we send (code) — boundary note (prior Worker; not re-proven this pass)

Endpoint: `POST https://api.typesafe.ai/v1/systemone` (docs: `https://docs.typesafe.ai/api.md` — **Confirmed**).

Documented production intent (see `src/services/jev_client.py` / routing minimize path):

| Field | Production boundary |
|---|---|
| `user_input` | Current turn; length-capped; PII redact |
| `recent_turns` / `recent_context` | Short history only; PII redact |
| `meta.*` | Route / product-name / focus tags — minimize |
| Forbidden | Full medical profile, symptoms dumps, prompts, RAG, ids/secrets |

**Challenger note:** Code minimize/redact reduces exposure but **does not unblock** retention/DPA/subprocessor gaps. Heuristic PII redaction remains residual FN risk. Schedule I Sensitive Data **N/A** still conflicts with possible health-adjacent free text even after scrub.

---

## 5. Residual risks (keep Blocking)

1. **Account contract gap:** Public DPA ≠ proof our Order accepted MCA/DPA or elected ZDR.  
2. **Retention TTL unknown:** Criteria-only retention; Telemetry perpetual-use license; no ZDR confirmation for this account.  
3. **Subprocessors unread:** Trust Center is interactive Vanta SPA.  
4. **Schedule I Sensitive Data N/A** vs symptom-bearing / health-adjacent free text.  
5. **PII redaction is heuristic.**  
6. **Japan APPI / end-user notice** for US third-party processing — Owner/legal.  
7. **Eval-only paths** may still differ from production minimize (check before any enablement).

---

## 6. Unblock checklist (Owner / Legal) — Production Shadow

1. Confirm MCA/Order + DPA acceptance for the production TypeSafe project.  
2. Request **ZDR** (or written retention ≤ N days) via `privacy@typesafe.ai`; archive email + Order.  
3. Export Trust Center subprocessors + Security Measures; store under `docs/ops/` (no secrets).  
4. Legal review of health-adjacent Input vs DPA Schedule I Sensitive Data **N/A**.  
5. Update app Privacy Policy third-party disclosure for TypeSafe System One.  
6. Keep `JEV_ENABLED` / production shadow flags **OFF** until above cleared.

---

## 7. Classification summary

| Class | Items |
|---|---|
| **Confirmed** | Public Privacy / DPA / MCA text & dates; train-on-Input denial; Telemetry unrestricted processing; US hosting; SCCs in DPA; DSAR assist; 72h incident; MCA↔DPA incorporate; criteria-only retention language; API endpoint; Trust Center URLs exist; `/security` etc. 404 |
| **Contract-dependent** | ZDR election; Order/MCA bind for our account; subprocessors change notices |
| **Unknown** | Numeric API Input/log TTL; APPI mapping; named subprocessors; certificate details; purge API/SLA |
| **Blocking** | **Production Shadow / live enablement**; account ZDR/retention unconfirmed; Schedule I sensitive-data N/A mismatch; subprocessors unread |

---

## 8. Challenger verification log

| Check | Result |
|---|---|
| Re-fetch Privacy / DPA / MCA / docs legal / API / state / Trust | Done 2026-09-23 |
| Invent Confirmed for retention TTL or our ZDR? | **No** — remains Blocking |
| Invent named subprocessors from Trust Center SPA? | **No** — Unknown → Blocking |
| Change Production Shadow gate? | **No** — remains **BLOCKING** |

---

*Privacy Challenger — R19+ — independent official-page re-verify*  
*No commit / no push / no secrets displayed.*
