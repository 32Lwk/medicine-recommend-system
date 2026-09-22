# JEV Local Cost Report — 2026-09-23

**Scope**: Local synthetic shadow evaluation only (not invoice; not production live).  
**Contract**: cost reporting required for Gate A; cost **not** in pass/fail.

## Rates (harness)

- USDJPY reference: 157.0
- Jev input: $0.042 / MTok (estimated)

## Stage3 repeat=10 seed=42

| Path | Basis | Runs w/ cost | Tokens / proxy | JPY |
| --- | --- | ---: | ---: | ---: |
| Jev | estimated | 70 | input_sum=96410 | **0.635728** |
| current OpenAI intent-router | measured_proxy | 100 | — | **0.8522** |
| Net saved estimate (proxy−est) | mixed labels | — | — | 0.216472 |

Do not conflate measured_proxy OpenAI reduction with estimated Jev spend or invoice net savings.

## Stage3b repeat=10 seed=20260922

| Path | JPY |
| --- | ---: |
| Jev estimated | 0.635728 |
| OpenAI intent saved (measured_proxy) | 0.8526 |
| Net saved estimate | 0.216872 |

## API call control

- Worker C serial only; high-risk fixtures not sent to live Jev
- API guard max_calls_per_batch=50; trips=0
- No infinite retry / runaway duplication observed in r10 runs (api_err=0)

## Artifacts

- `log/analysis/jev_r11_r10_seed42_20260923.json` → `cost`
- `log/analysis/jev_r11_r10_seed20260922_20260923.json` → `cost`
