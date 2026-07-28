# Routing E2E Live Test — 2026-07-28

Base URL: http://127.0.0.1:5000/

## symptom_casual_headache — FAIL (physical)
口語頭痛

- [NG] `頭バキバキ…` → route=Concierge kind=concierge_greeting (23122ms)
  - errors: render expected 'sage_reco' got 'sage_status'
  - snippet: 頭がバキバキするのですね、お辛そうです。こちらは市販薬に関する相談窓口ですので、頭痛やのどの痛みなどの症状に対する市販薬のご提案が可能です。どのような症状でお悩みですか？
ご挨拶

## Summary
- Total: 1
- Passed: 0
- Failed: 1

### By category
- **physical**: 0 pass / 1 fail