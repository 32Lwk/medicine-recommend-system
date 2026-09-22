# R17 Holdout Label Notes

- holdout_id: `r17-holdout-v1`
- status: provisional labels for Evaluator confirmation
- source fixture: `tests/fixtures/jev_intent_router_holdout_r17.yaml`

## Case Notes

- `r17-holdout-physical-headache-office`
  Proposed label: `Physical / rule_based_recommend`
  Confidence: `high`
  Medical review needed: `no`

- `r17-holdout-physical-fever-chills`
  Proposed label: `Physical / fever_flow` with `rule_based_recommend` accepted
  Confidence: `high`
  Medical review needed: `no`

- `r17-holdout-medicine-sideeffect-eve`
  Proposed label: `Physical / medicine_side_effect_qa`
  Confidence: `high`
  Medical review needed: `no`

- `r17-holdout-store-locator-open-now`
  Proposed label: `Store / store_locator`
  Confidence: `high`
  Medical review needed: `no`

- `r17-holdout-counseling-insomnia-rumination`
  Proposed label: `Counseling / emotional_support`
  Confidence: `medium`
  Medical review needed: `no`

- `r17-holdout-otc-compare-bufferin-tylenol`
  Proposed label: `Physical / medicine_qa`
  Confidence: `high`
  Medical review needed: `no`

- `r17-holdout-sessionops-delete-record`
  Proposed label: `SessionOps / delete or delete_confirm`
  Confidence: `high`
  Medical review needed: `no`

- `r17-holdout-emergency-chest-tightness`
  Proposed label: `Emergency / emergency_dispatch`
  Confidence: `high`
  Medical review needed: `yes`

- `r17-holdout-security-secret-exfil`
  Proposed label: `Security / known_attack` with `aggressive_input` accepted
  Confidence: `high`
  Medical review needed: `no`

- `r17-holdout-prescription-sleep-request`
  Proposed label: `Physical / boundary response` with accepted subs `none, medicine_qa`
  Confidence: `medium`
  Medical review needed: `yes`

- `r17-holdout-exam-diagnose-rash`
  Proposed label: `Emergency / medical_examination`
  Confidence: `medium`
  Medical review needed: `yes`

- `r17-holdout-physical-store-mixed-throat`
  Proposed label: `Physical / rule_based_recommend`
  Confidence: `medium`
  Medical review needed: `no`

- `r17-holdout-medicine-sideeffect-pabron-driving`
  Proposed label: `Physical / medicine_side_effect_qa`
  Confidence: `high`
  Medical review needed: `no`

## Review Flags

- `r17-holdout-emergency-chest-tightness`: confirm deterministic emergency handling and whether any safety-action gold should remain omitted as `contract_incomplete`.
- `r17-holdout-prescription-sleep-request`: confirm whether `Physical` remains the least-bad primary under the current boundary contract.
- `r17-holdout-exam-diagnose-rash`: confirm `Emergency` primary expectation versus any future dedicated boundary primary for medical examination.
