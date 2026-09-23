# JEV R19+ Worker D — AWS Staging Identity & Uniqueness Probe

**Date**: 2026-09-24 (probe run ~11:12 JST)  
**Worker**: D (AWS/IaC)  
**Mode**: READ-ONLY identity + inventory (first pass)  
**Deploy executed**: **NO**

```text
DEPLOY_READY=no
```

---

## Executive verdict

| Gate | Result |
|------|--------|
| Staging uniquely identified (docs + DNS + Worker) | **YES** (doc/DNS evidence) |
| Staging separated from GCP production | **YES** (hosts disjoint; no production touch) |
| STS identity works | **NO** — all probed profiles failed |
| Region matches docs (`ap-northeast-1`) | **YES** (config + IaC defaults; live API unconfirmed) |
| Live ECS cluster/service inventory | **BLOCKED** (no valid credentials) |
| Deploy this pass | **NO** — wait Supervisor; prefer `DEPLOY_READY=no` |

**Bottom line**: Staging hosts and IaC state files clearly point at AWS Fargate+Tunnel staging on documented account `***973` / region `ap-northeast-1`. **Do not deploy** until `aws login` restores STS for the new-account profile and live ECS inventory confirms cluster/service/task env (flags OFF).

---

## 1. Doc / IaC inventory (read first)

| Source | Finding |
|--------|---------|
| `docs/ops/AWS_INFRA.md` | Staging `aws-medicine.yutok.dev` / `aws.medicine.yutok.dev`; region `ap-northeast-1`; profile note: new account → `default` (`***973`), old backup → `medicine-recommend-dev` (`***994`) |
| `docs/ops/AWS_STAGING_CHECKLIST.md` | Fargate+Tunnel SSOT; health curls for Worker/Origin; ALB expected 0 |
| `docs/ops/AWS_FARGATE_TUNNEL.md` | Cluster `default`, service `medicine-recommend`, family `medicine-recommend-tunnel` |
| `docs/ops/AWS_ACCOUNT_MIGRATION.md` | Old `***994` → new `***973` (2026-08-06); CLI must re-login |
| `scripts/lib/aws_common.sh` | Defaults: `AWS_ACCOUNT_ID=***973`, `AWS_REGION=ap-northeast-1`, `ECS_CLUSTER=default`, `ECS_SERVICE=medicine-recommend`; **local default profile = `medicine-recommend-dev`** (mismatch risk vs INFRA “use default for new account”) |
| `scripts/.aws-deploy-mode` | `fargate_tunnel` |
| `scripts/.aws-fargate-tunnel.json` | account `***973`, region `ap-northeast-1`, cluster `default`, service `medicine-recommend`, task_family `medicine-recommend-tunnel`, origin `origin-aws-medicine.yutok.dev`, worker `aws-medicine.yutok.dev` |
| `scripts/.aws-staging-stop-state.json` | Stopped 2026-08-06 (budget); previous desired=1; pipeline Source outbound disabled |
| `workers/wrangler.toml` | Routes both staging hosts; `ORIGIN_URL=https://origin-aws-medicine.yutok.dev` |
| Production | `medicine.yutok.dev` (GCP) — **out of scope; not probed for change** |

**Account anonymization**: documented new account ends `***973`; old backup ends `***994`. Full IDs exist in-repo docs but are not repeated here beyond trailing digits already used in program state.

---

## 2. STS identity probe (no secrets printed)

| Profile | STS `get-caller-identity` | Notes |
|---------|---------------------------|-------|
| `default` | **FAIL** — session expired; reauthenticate via `aws login` | `~/.aws/config` shows `login_session` ARN for account ending `***973` (root login session) — **correct account target, expired session** |
| `medicine-recommend-dev` | **FAIL** — `InvalidClientTokenId` | Region in config: `ap-northeast-1`; likely stale access keys (migration doc: old-account keys) |
| `admin` | **FAIL** — `InvalidClientTokenId` | Same class of failure |
| `admin-cli` | **FAIL** — `InvalidClientTokenId` | Same class of failure |

**Configured profile names only**: `admin-cli`, `admin`, `medicine-recommend-dev`, `default`.

**Implication**: Cannot verify live AccountId / Arn / UserId. Cannot list ECS, describe services, or read task definition env (JEV flags). Script default `AWS_PROFILE=medicine-recommend-dev` would hit **invalid** credentials even after `default` is re-logged unless profile mapping is fixed.

---

## 3. Live inventory attempt (non-destructive)

| Check | Result |
|-------|--------|
| `ecs list-clusters` (`default` / `medicine-recommend-dev`) | **FAIL** (auth) |
| ALB count / service loadBalancers | **NOT RUN** (auth) |
| Task definition env / feature flags | **NOT RUN** (auth) |
| Wake / idle-stop Lambdas | **NOT RUN** (auth) |

**Documented expected names** (unconfirmed live):

- Cluster: `default`
- Service: `medicine-recommend`
- Task family: `medicine-recommend-tunnel`
- Pipeline (historical stop state): `medicine-recommend-main`
- Wake Lambda (docs): `medicine-recommend-wake-staging`
- Idle-stop rule (docs): `medicine-recommend-staging-idle-stop`

---

## 4. Staging health (staging hosts only)

Production `medicine.yutok.dev` was **not** called.

| URL | HTTP | Body / notes |
|-----|------|----------------|
| `https://aws-medicine.yutok.dev/health` | **503** | `{"status":"starting","eta_seconds":180}` — Worker wake/proxy path (idle/cold) |
| `https://aws.medicine.yutok.dev/health` | **503** | Same wake payload (legacy alias) |
| `https://origin-aws-medicine.yutok.dev/health` | **530** | Cloudflare `error code: 1033` — Tunnel origin down (consistent with desired=0 / no cloudflared) |

**Interpretation**: Public staging entry is uniquely the AWS Worker + Tunnel stack (not GCP production). Health shape matches wake-on-access docs (`AWS_WAKE_ON_ACCESS.md` / checklist: 503 when stopped, 200 when up). Origin 1033 confirms Tunnel/Fargate not serving.

**Side effect note**: Worker `/health` returns `starting` and may invoke Wake Lambda. This pass did **not** run `resume-aws-staging.sh` or `deploy-aws-ecs.sh`. No DNS changes. No production resource mutations.

---

## 5. Uniqueness & separation assessment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Staging hostnames distinct from production | **PASS** | `aws-medicine.*` / `aws.medicine.*` vs `medicine.yutok.dev` |
| Deploy mode / state files point at Fargate Tunnel staging | **PASS** | `.aws-deploy-mode`, `.aws-fargate-tunnel.json` |
| Live AWS account binding via STS | **FAIL** | All profiles unauthenticated |
| Live ECS proves only staging service | **FAIL** | Inventory blocked |
| Profile → account mapping safe for scripts | **FAIL / RISK** | `aws_common.sh` defaults to `medicine-recommend-dev` (invalid); new account session is `default` (expired) |

**Staging uniquely confirmed for deploy purposes?**  
**Partial (DNS/docs YES; live identity NO)** → treat as **NOT confirmed for deploy**.

---

## 6. Decision gates → DEPLOY_READY

Per Worker D charter: deploy only if staging uniquely identified **and** separated **and** STS works **and** region matches. Default first pass: do not deploy.

| Required | Met? |
|----------|------|
| Staging uniquely identified | Partial — DNS/docs only |
| Separated from production | Yes (host separation; no prod ops) |
| STS identity works | **No** |
| Region matches docs | Config/docs yes; API unconfirmed |
| Build/tests green + flags OFF in task env | **Not verified** (no task env read) |
| Supervisor signal | Assumed wait |

→ **`DEPLOY_READY=no`**

**Actions NOT taken**: `resume-aws-staging.sh`, `deploy-aws-ecs.sh`, `stop-aws-staging.sh`, push, DNS, production create/delete/change.

---

## 7. Pre-deploy checklist (for when Supervisor + identity OK)

Do **not** execute until STS proves Account=`***973` and Owner/Supervisor says go.

1. **Re-auth**
   - Prefer: `aws login` for profile targeting account `***973` (docs: method C `default`, or new named profile `medicine-recommend-dev-***973`).
   - Re-run: `aws sts get-caller-identity --profile <chosen>` — confirm Account ends `***973`, region `ap-northeast-1`.
   - Fix script usage: always `AWS_PROFILE=...` explicitly for new account; do not rely on stale `medicine-recommend-dev` keys.
2. **Live inventory (read-only)**
   - `ecs describe-services --cluster default --services medicine-recommend`
   - Confirm `desiredCount`, task definition `medicine-recommend-tunnel`, `loadBalancers=[]`
   - `elbv2 describe-load-balancers` → expect 0 (new account)
   - Inspect task def env: `JEV_*` / `POLICY_ENFORCEMENT_D2` must be OFF / absent-as-false
3. **Cost / wake**
   - Confirm idle-stop ENABLED; avoid leaving desired>0 overnight
   - Prefer explicit `resume-aws-staging.sh` over accidental wake-from-curl loops
4. **Build / tests**
   - Local main green; image build only after identity OK
5. **Deploy path**
   - `deploy-aws-ecs.sh` (current local main only) → wait Origin `/health` 200 → Worker `/health` 200
   - Smoke: Translate/Polly/CDN only if already in staging scope
6. **Hard no-gos**
   - No GCP `medicine.yutok.dev` changes
   - No DNS edits
   - No enabling JEV primary / D2 in task env this R19+ pass unless separate Owner approval

---

## 8. Blockers (ordered)

1. **BLOCKER — STS**: `default` session expired (`aws login` required for `***973`).
2. **BLOCKER — Profile hygiene**: `medicine-recommend-dev` / `admin` / `admin-cli` tokens invalid (`InvalidClientTokenId`); migration leftover keys risk wrong-account ops if somehow revived.
3. **BLOCKER — Live ECS unconfirmed**: cannot prove cluster/service/task env/flags without API.
4. **SOFT — Script default profile mismatch**: `aws_common.sh` → `medicine-recommend-dev` vs INFRA guidance `AWS_PROFILE=default` for new account.
5. **SOFT — Staging cold**: Worker 503 starting / Origin 530 (1033); expected when stopped; resume+deploy only after gates above.
6. **PROGRAM — R18 readiness**: production shadow Not Ready; AWS staging deploy is orthogonal but Supervisor should still gate any live change.

---

## 9. Return summary (for Supervisor)

| Field | Value |
|-------|--------|
| **DEPLOY_READY** | **no** |
| **Account (anonymized)** | Doc/state target `***973` (new); old backup `***994`; **STS unverified** |
| **Region** | `ap-northeast-1` (config + IaC) |
| **Service names** | Cluster `default` / Service `medicine-recommend` / Task family `medicine-recommend-tunnel` (docs + state file; live unconfirmed) |
| **Health** | Worker hosts **503** `starting`; Origin **530** `1033` |
| **Deploy this pass** | **None** |
| **Blockers** | Expired/invalid AWS credentials; no live ECS inventory; profile default mismatch |

**Next Owner action**: `aws login` on the new-account profile → re-run this probe’s STS + ECS describe section → Supervisor sets deploy go/no-go.

---

## 10. Commands reference (safe re-probe only)

```powershell
# Identity (print Account/Arn/UserId only — no secret keys)
aws sts get-caller-identity --profile default
aws sts get-caller-identity --profile medicine-recommend-dev

# Inventory (after identity OK)
aws ecs describe-services --profile default --region ap-northeast-1 `
  --cluster default --services medicine-recommend `
  --query "services[0].{status:status,desired:desiredCount,running:runningCount,taskDef:taskDefinition,lbs:loadBalancers}"

# Health (staging only)
curl.exe -sS https://aws-medicine.yutok.dev/health
curl.exe -sS https://origin-aws-medicine.yutok.dev/health
```

---

*Worker D first-pass probe complete. No push. No production mutations. No deploy.*
