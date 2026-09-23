# JEV R19 Privacy / DPA Report — TypeSafe System One

**Role:** Worker C (Privacy/DPA)  
**Date:** 2026-09-24  
**Endpoint in repo:** `https://api.typesafe.ai/v1/systemone`  
**Scope:** Primary-source research (official Privacy Policy / DPA / MCA / docs) + production payload boundary (minimize + PII redact).  
**Go/No-Go:** ❌ **Still BLOCKING** for production shadow / live IntentRouter traffic.

Classification legend used below: **Confirmed** | **Contract-dependent** | **Unknown** | **Blocking**.

---

## 1. Verdict

| Gate | Result |
|---|---|
| Overall privacy/DPA for production enablement | **BLOCKING** |
| Public DPA document exists | **Confirmed** (URL below) |
| Fixed retention TTL / ZDR for *our* account | **Blocking** (not confirmed) |
| Free-text PII scrub + payload minimization in code | **Implemented this round** (heuristic; residual FN risk) |
| Subprocessor inventory (named list) | **Unknown / Blocking** (Trust Center SPA; not scrapeable without session) |

**Bottom line:** Official legal pages are now located and summarized. Training-on-Input is publicly denied. **Nevertheless production remains BLOCKING** until (a) Order/MCA+DPA applicability to medicine-recommend is confirmed, (b) retention/ZDR election is documented for this account, (c) subprocessors are recorded from Trust Center, and (d) health-data / Schedule I “Sensitive Data: N/A” mismatch is accepted or renegotiated.

---

## 2. Sources (official only)

| Document | URL | Retrieved |
|---|---|---|
| Privacy Policy | https://typesafe.ai/privacy · https://typesafe.ai/legal/privacy-policy | 200 OK (Last updated **Nov 19, 2025**) |
| Data Processing Addendum (DPA) | https://typesafe.ai/legal/data-processing · https://typesafe.ai/data-processing | 200 OK (Last updated **Apr 24, 2026**) |
| Master Customer Agreement (MCA) | https://typesafe.ai/legal/mca | 200 OK (Last updated **Sep 19, 2026**) |
| Docs Legal index | https://docs.typesafe.ai/legal · https://docs.typesafe.ai/legal.md | 200 OK |
| Docs index | https://docs.typesafe.ai/llms.txt | 200 OK |
| API reference (endpoint) | https://docs.typesafe.ai/api.md | 200 OK — documents `POST https://api.typesafe.ai/v1/systemone` |
| State guidance | https://docs.typesafe.ai/concepts/state.md | 200 OK |
| Trust Center | https://trust.typesafe.ai/ | 200 OK (Vanta SPA; body not statically readable) |
| Subprocessors (referenced by DPA) | https://trust.typesafe.ai/subprocessors | 200 OK (same Vanta SPA; **named list not Confirmed**) |
| Status | https://status.typesafe.ai/ | 200 OK (availability only) |

**Not found as public HTML (404):** `/security`, `/dpa`, `/legal/dpa`, `/legal/data-processing-addendum`.  
**Not treated as Confirmed:** blog marketing pages.

---

## 3. Findings matrix

### 3.1 Training usage

| Finding | Class | Evidence |
|---|---|---|
| TypeSafe will not train / fine-tune models on customer **Input** | **Confirmed** | Privacy Policy: “We will not train or fine tune any artificial intelligence or machine learning models on your prompts or other Input.” Repeated: will not train on Input; disclose Input only to service providers. |
| MCA: no Customer Data in training datasets without prior consent | **Confirmed** | MCA §4.1: will not include Customer Data in a dataset used to train (modify model weights) without Customer’s prior consent. |
| Telemetry may be processed without restriction (incl. improve Services) | **Confirmed** | MCA §4.3 Telemetry definition + “Process Telemetry without restriction, including to improve the Services…” — **not** model-weight training, but derived metrics may persist. |

### 3.2 Retention

| Finding | Class | Evidence |
|---|---|---|
| Privacy Policy retention = “as long as reasonably necessary” | **Confirmed** (criterion only) | Privacy Policy §Retention — no fixed day count. |
| DPA Schedule I Duration of Processing = “as long as necessary…” | **Confirmed** (criterion only) | DPA Schedule I §8 — no fixed TTL. |
| Zero Data Retention (ZDR) offered for enterprise | **Contract-dependent** | Docs Legal: “We also offer zero data retention (ZDR) for enterprise customers. Contact privacy@typesafe.ai.” **Not Confirmed** that medicine-recommend has ZDR. |
| MCA: TypeSafe under no obligation to store/retain; may delete at sole discretion (during/after Term) | **Confirmed** | MCA §10.3 Effect of Termination. This is **vendor discretion**, not a customer deletion SLA. |
| Per-request / log TTL for System One API | **Unknown → Blocking** for ops certainty | No public numeric retention for API Input/logs found outside ZDR sales path. |

### 3.3 Deletion / data subject rights

| Finding | Class | Evidence |
|---|---|---|
| Deletion on request (Privacy Policy) | **Confirmed** (process) | “When you request that we do so, we take measures to delete…” — **no SLA** published. |
| DPA: processor forwards DSAR to Customer; assists | **Confirmed** | DPA §4.1–4.2. |
| Customer-triggered purge SLA / API delete endpoint | **Unknown** | Not found in public API docs. |
| Backups may retain Confidential Information | **Confirmed** | MCA §10.3 backups carve-out. |

### 3.4 Region / transfers

| Finding | Class | Evidence |
|---|---|---|
| Services hosted in the United States | **Confirmed** | Privacy Policy §International Visitors. |
| EU/UK transfers via SCCs / UK Addendum | **Confirmed** (contract text) | DPA §6. |
| Japan APPI-specific clauses / adequacy mapping | **Unknown** | Not stated on Privacy Policy / DPA pages reviewed. |
| Subprocessor geography list | **Unknown → Blocking** | DPA points to Trust Center; list not extracted without authenticated/JS Trust Center. |

### 3.5 DPA / contract applicability

| Finding | Class | Evidence |
|---|---|---|
| Public DPA text exists and is linked from docs | **Confirmed** | https://typesafe.ai/legal/data-processing |
| MCA incorporates DPA by reference | **Confirmed** | MCA §4.4 cites https://typesafe.ai/data-processing |
| Whether medicine-recommend’s TypeSafe account accepted MCA/Order | **Contract-dependent → Blocking** until Owner confirms | Not in repo; cannot invent. |
| DPA Schedule I “Sensitive Data Transferred: **N/A**” | **Blocking** (product mismatch risk) | OTC symptom free-text may be health-related personal data under GDPR/APPI; Schedule I says N/A. Needs legal acceptance or amendment. |

### 3.6 Security / subprocessors

| Finding | Class | Evidence |
|---|---|---|
| Security Measures referenced to Trust Center | **Confirmed** (pointer only) | DPA §5.1 / Schedule I §11 → https://trust.typesafe.ai/ |
| Security incident notify ≤ 72h | **Confirmed** | DPA §5.2 |
| Named subprocessors | **Unknown → Blocking** | URL exists; content not Confirmed in this research pass |
| SOC2 / ISO certificates | **Unknown** | Trust Center SPA only; no static certificate text Confirmed |

---

## 4. What we send (code) after this Worker’s changes

Endpoint: `POST https://api.typesafe.ai/v1/systemone` (`src/services/jev_client.py`).

### 4.1 Allowlisted outbound state

| Field | Production boundary |
|---|---|
| `user_input` | Current turn only; max 4000 chars; **PII redact** |
| `recent_turns` / `recent_context` | **Max 2** prior turns × **160** chars; PII redact; same list alias |
| `meta.last_*_route` | Route labels only |
| `meta.last_recommended_medicines` | Max 3 product names (no profile dump) |
| `meta.medicine_qa_focus` | Focus tags only |
| `channel`, `app_context` | Non-PII enums/constants |

### 4.2 Explicitly forbidden / removed

- `active_symptoms` / `symptoms` / `diagnosis` **no longer exported**
- `system_prompt` / `prompt` / `rag*` / `dialogue_state` / `messages` / `medical_profile` / `user_attributes` / ids / secrets in `_FORBIDDEN_STATE_KEYS`
- Session / medical-profile dumps must not appear as top-level or `meta` keys (`validate_jev_state_contract` / scrub)

### 4.3 Code + tests touched (no commit)

- `src/dialogue/routing/jev_pii_redact.py` — stronger rules + ordering
- `src/dialogue/routing/jev_router.py` — minimize turns/chars; drop symptoms; expand forbid list
- `tests/dialogue/routing/test_jev_pii_redact.py` — adversarial FN cases
- `tests/dialogue/routing/test_jev_router.py` — depth expectations updated  
- Pytest: **38 passed** (`test_jev_pii_redact.py` + `test_jev_router.py`)

---

## 5. Residual risks (keep Blocking)

1. **Account contract gap:** Public DPA ≠ proof our Order accepted MCA/DPA or elected ZDR.  
2. **Retention TTL unknown:** Criteria-only retention; Telemetry perpetual; no ZDR confirmation.  
3. **Subprocessors unread:** Trust Center requires interactive access.  
4. **Sensitive data Schedule I N/A** vs symptom-bearing free text still leaving trust boundary (even after PII scrub — symptoms themselves may be sensitive).  
5. **PII redaction is heuristic:** Adversarial FN tests cover common JP/US patterns; novel obfuscation can slip.  
6. **Eval script drift:** `scripts/eval_jev_intent_router_10.py` can still attach `active_symptoms` in eval-only state builder (not production path).  
7. **Japan APPI / end-user notice:** Third-party (TypeSafe US) processing should be reflected in our privacy notices — Owner/legal.

---

## 6. Unblock checklist (Owner / Legal)

1. Confirm MCA/Order + DPA acceptance for the production TypeSafe project.  
2. Request **ZDR** (or written retention ≤ N days) via `privacy@typesafe.ai`; archive email + Order.  
3. Export Trust Center subprocessors + Security Measures; store under `docs/ops/` (no secrets).  
4. Legal review of health-adjacent Input vs DPA Schedule I “Sensitive Data: N/A”.  
5. Update app Privacy Policy third-party disclosure for TypeSafe System One.  
6. Keep `JEV_ENABLED` / shadow flags **OFF** until above cleared.

---

## 7. Classification summary counts

| Class | Count (approx.) |
|---|---|
| Confirmed | Training ban; US hosting; public DPA/MCA text; DSAR assist; 72h incident; endpoint docs; code minimize/redact shipped |
| Contract-dependent | ZDR; Order/MCA bind; subprocessors refresh notices |
| Unknown | Numeric API retention; APPI mapping; certificate details |
| Blocking | Production enablement until §6 checklist; Schedule I sensitive-data mismatch; subprocessors unread; account ZDR/retention unconfirmed |

---

*Worker C — Privacy/DPA — R19+ — 2026-09-24*  
*No commit / no push / no secrets displayed.*
