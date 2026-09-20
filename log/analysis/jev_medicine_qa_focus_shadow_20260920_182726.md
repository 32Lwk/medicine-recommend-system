# Jev Medicine QA Focus Shadow (scaffold)

- Timestamp: `20260920_182726`
- Fixture: `D:/Programing/medicine-recommend/tests/fixtures/jev_medicine_qa_focus_pilot.yaml`
- Mode: `dry_run_schema_only`
- label_status_default: `draft`
- Eligibility: **NOT in scope**
- Production flags / chat_post_pipeline: **unchanged**

## Schema

Schema OK.

## Comparison surface (documented)

1. Current: `infer_medicine_qa_focuses` (this scaffold uses `use_llm_enrichment=False` for offline baseline).
2. Future: Jev Focus adapter (draft questions in this script; not in `jev_decisions` / pipeline).
3. Do **not** merge Eligibility; physical_symptom_pivot FN is a Focus-side risk flag only.

## Per-scenario

- `focus-comparison-loxonin-ibu` tag=`comparison` current=['comparison'] soft_pass=`True` pivot_expected=`False`
- `focus-side-effect-drowsiness` tag=`side_effect` current=['side_effect'] soft_pass=`True` pivot_expected=`False`
- `focus-dosage-usage` tag=`dosage` current=['side_effect', 'usage'] soft_pass=`True` pivot_expected=`False`
- `focus-photo-product-image` tag=`photo` current=['product_image'] soft_pass=`True` pivot_expected=`False`
- `focus-age-limit` tag=`age_limit` current=['age'] soft_pass=`True` pivot_expected=`False`
- `focus-ambiguous-anaphora` tag=`ambiguous` current=['general'] soft_pass=`True` pivot_expected=`False`
- `focus-physical-pivot-symptom` tag=`physical_pivot_symptom` current=['general'] soft_pass=`True` pivot_expected=`True`

## Notes

- Scaffold only. Draft labels must never hard-fail CI or Gate B.
- Eligibility / resolve_medicine_qa_route is out of scope.
- No JEV_FOCUS flags and no chat_post_pipeline changes.
- Dry-run schema + optional rule baseline. Set JEV_API_KEY and pass --live for optional Focus-question stub.
