# JEV R21 False-pass Challenger (Worker I)

**Date**: 2026-09-24  
**Workspace**: `d:\Programing\medicine-recommend`  
**Challenged document**: `JEV_R21_GATE_B_FINAL_REPORT_20260924.md` (Worker B Closed-candidate Yes for H-03/H-04/H-05)  
**Also appended**: same section in the Final Report under “False-pass Challenger (Worker I)”.

## Verdict

**Reject Closed-candidate** for H-03, H-04, and H-05.  
Gate B **Hard No-Go**. Product safety **未合格** (do not claim Passed).  
SafetyGate not weakened. Gold not retargeted. No commit / no push.

## Residuals: Closed vs still Open

| Residual | Closed? | Evidence |
| --- | --- | --- |
| R19 ambiguous_policy incomplete drop | Closed | Prior fix retained |
| R19 crisis_detector_error → crisis_resources | Closed | Prior fix retained |
| F-H03-R2 adapter/DB/empty → SF-E1 | **Closed-candidate OK** | Live: adapter boom → `policy_boundary`, ≤2 adapter calls |
| Infinite adapter recursion | Closed (attack failed) | Finite re-entry + static copy |
| F-H03-R1 lexical / detector FN | **Open** | Lexical recover only when `incomplete`; complete+wiped `処方してください` → `continue` |
| F-H03-R3 D2 default OFF | **Open** | Staging/prod defaults OFF; path inoperative |
| F-H04-R1 soft SI paraphrase | **Open** | Complete+FN → `no_policy_hit`; soft gaps → SF-E1; **FP** OTC/complaint → crisis |
| F-H04-R2 scope / staging proof | **Open** | HEAD `469c9fe`+dirty ≠ staging `8a3c571` |
| F-H05-R1 mock removal | Partial | Mocks gone in WIP; prescription assert tautology remains → H-05 **Open** |
| Gold retargeting | Clear | No gold edits |
| Flag left ON | Clear (defaults) | All 0 / unset — also means policy fixes not live on default |

## Key live hits (reproduce)

1. **soft_si FP**: incomplete + `controlled_drug_detector_error` + `もうだめだ風邪が治らない` → `crisis_resources`.  
2. **lexical FN**: `evaluation_complete=True` + cues wiped + `処方してください` → `no_policy_hit`.  
3. **H-05 denominator**: `{status:ok, message_count:0, sage_diagnosis:{}}` satisfies current prescription assert.  
4. **SHA / dirty WT**: Closed cannot equal green deploy.

## Non-claims

Not Gate B Go. Not H-03/H-04/H-05 Closed. Not product safety Passed. Not Production Shadow Ready.
