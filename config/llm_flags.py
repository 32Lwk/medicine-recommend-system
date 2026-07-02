"""
LLM 機能フラグ（環境変数）
"""
from __future__ import annotations

import os


def _flag(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def is_agent_enabled() -> bool:
    """
    エージェント経路のキルスイッチ。
    ON: 全セッションで ChatOrchestrator 経路。OFF: 従来経路のみ。
    本番既定は ON（docs/dev/ARCHITECTURE_MULTI_AGENT.md 参照）。
    """
    return _flag("LLM_AGENT_ENABLED", True)


def is_gpt_recommend_fallback_enabled() -> bool:
    """本番チャットで GPT が OTC を選ぶフォールバック（デフォルト OFF）"""
    return _flag("LLM_GPT_RECOMMEND_FALLBACK", False)


def is_gpt5_profile() -> bool:
    return (os.getenv("LLM_MODEL_PROFILE") or "gpt5").strip().lower() == "gpt5"


def get_canary_percent() -> int:
    """非エージェント LLM カナリア（レガシー LLM 経由用）。エージェントカナリアは廃止。"""
    try:
        return max(0, min(100, int(os.getenv("LLM_CANARY_PERCENT", "0"))))
    except ValueError:
        return 0


def _is_pytest_running() -> bool:
    """pytest 実行中は dev 自動 ON を抑止（既存テストの v2 OFF 前提を維持）。"""
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def is_chat_pipeline_v2_enabled() -> bool:
    """
    Chat Pipeline v2 キルスイッチ（Web / LINE 共通）。
    - 明示 true/false → その値
    - 未設定 + 開発ランタイム（APP_ENV=development 等）→ True（ローカル / GCP dev 一括 ON）
    - 未設定 + 本番 → False
    ON 時は IntentRouter / dispatch / LLM も未設定ならすべて True（段階フラグ不要）。
    """
    val = os.getenv("CHAT_PIPELINE_V2")
    if val is not None:
        return _flag("CHAT_PIPELINE_V2", False)
    if _is_pytest_running():
        return False
    from config.app_config import is_development_runtime

    return is_development_runtime()


def _v2_subflag_enabled(name: str) -> bool:
    """
    v2 サブフラグ。CHAT_PIPELINE_V2 有効時は未設定なら True（一括 ON）。
    明示 false で個別 OFF（本番カナリア用）。
    """
    if not is_chat_pipeline_v2_enabled():
        return False
    val = os.getenv(name)
    if val is None:
        return True
    return val.strip().lower() in ("1", "true", "yes", "on")


def _parse_sid_list(env_name: str) -> frozenset[str]:
    raw = os.getenv(env_name) or ""
    return frozenset(s.strip() for s in raw.split(",") if s.strip())


def is_chat_pipeline_v2_for_session(sid: str | None) -> bool:
    """
    セッション単位の v2 有効判定。
    - CHAT_PIPELINE_V2=false → 常に False
    - CHAT_PIPELINE_V2_DENYLIST → 一致 sid は False（ロールバック）
    - CHAT_PIPELINE_V2_ALLOWLIST が非空 → リスト内 sid のみ True（カナリア）
    - 上記以外 → グローバルフラグに従う
    """
    if not is_chat_pipeline_v2_enabled():
        return False
    if not sid:
        return True
    deny = _parse_sid_list("CHAT_PIPELINE_V2_DENYLIST")
    if sid in deny:
        return False
    allow = _parse_sid_list("CHAT_PIPELINE_V2_ALLOWLIST")
    if allow:
        return sid in allow
    return True


def is_intent_router_v2_enabled(sid: str | None = None) -> bool:
    """
    Wave 1b IntentRouter。
    v2 有効時は既定 ON。CHAT_PIPELINE_V2_INTENT_ROUTER=false で shadow のみ / OFF。
    """
    if not is_chat_pipeline_v2_for_session(sid):
        return False
    return _v2_subflag_enabled("CHAT_PIPELINE_V2_INTENT_ROUTER")


def is_intent_router_dispatch_enabled(sid: str | None = None) -> bool:
    """
    Wave 1b IntentRouter 本線 dispatch。
    v2 + router 有効時は既定 ON。CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH=false で shadow のみ。
    """
    if not is_intent_router_v2_enabled(sid):
        return False
    return _v2_subflag_enabled("CHAT_PIPELINE_V2_INTENT_ROUTER_DISPATCH")


def is_intent_router_llm_enabled(sid: str | None = None) -> bool:
    """
    Wave 1b Stage B — structured LLM IntentRouter。
    v2 + router 有効時は既定 ON。CHAT_PIPELINE_V2_INTENT_ROUTER_LLM=false で gate/triage のみ。
    """
    if not is_intent_router_v2_enabled(sid):
        return False
    return _v2_subflag_enabled("CHAT_PIPELINE_V2_INTENT_ROUTER_LLM")


# --- Phase 1 レイテンシ最適化フラグ（既定 OFF = post-p0 と同一挙動） ---
# 独立フラグにして A/B（OFF=baseline / ON=after）を同一ビルドで計測可能にする。


def is_triage_single_call_enabled() -> bool:
    """トリアージ stage1+stage2 を 1 回の structured call に統合（既定 OFF）。

    OFF 時は従来の 2 段（Other 時のみ stage2）。ルーティング結果は等価を維持する。
    """
    return _flag("LATENCY_TRIAGE_SINGLE_CALL", False)


def is_explain_fast_lowrisk_enabled() -> bool:
    """低リスク症状の説明生成（explain ロール）を高速モデルに切替（既定 OFF）。

    高リスク（小児/発熱/妊娠授乳/高齢/持病・治療中/併用薬/アレルギー）は上位モデル維持。
    """
    return _flag("LATENCY_EXPLAIN_FAST_LOWRISK", False)


def is_explain_cache_enabled() -> bool:
    """バッチ使用上の注意（explain）の結果キャッシュ（既定 OFF）。

    キーに医薬品セット＋リスク関連ユーザー属性＋症状を含め、個別因子絡みは都度生成。
    """
    return _flag("LATENCY_EXPLAIN_CACHE", False)


def is_reco_parallel_enabled() -> bool:
    """推奨フローの独立 LLM 処理（使用上の注意 / 個別アドバイス）の並列化（既定 OFF）。"""
    return _flag("LATENCY_RECO_PARALLEL", False)


# --- Phase 1b スコアリング/LLM境界（既定 OFF = post-p0 と同一挙動） ---


def is_explain_batch_stabilize_enabled() -> bool:
    """説明 batch の empty completion 対策（リトライ・max_tokens 増）を有効化（既定 OFF）。"""
    return _flag("LATENCY_EXPLAIN_BATCH_STABILIZE", False)


def is_rb_llm_external_enabled() -> bool:
    """missing_info / 説明生成 LLM を rule_based 関数外（chat flow）へ移す（既定 OFF）。

    ON 時、rule_based 計測区間は純 Python スコアリング中心になり、p1 説明最適化が e2e に反映されやすくなる。
    """
    return _flag("LATENCY_RB_LLM_EXTERNAL", False)


def is_score_parallel_enabled() -> bool:
    """quick / detailed スコアリングループの ThreadPool 並列化（既定 OFF）。"""
    return _flag("LATENCY_SCORE_PARALLEL", False)


# --- Phase 2 安全ガードフラグ（既定 OFF = 現状維持） ---


def is_violence_context_guard_enabled() -> bool:
    """store_emergency_handler の violence 曖昧語（「喧嘩」等）に文脈ガードを適用（既定 OFF）。

    ON 時、曖昧語単体では緊急検知せず、強い暴力シグナルの共起を要求する
    （「友人と喧嘩しました」等の心理相談文脈を誤って緊急扱いしないため）。
    """
    return _flag("SAFETY_VIOLENCE_CONTEXT_GUARD", False)


def is_emergency_channel_split_enabled() -> bool:
    """緊急応答メッセージをチャネル別に出し分ける（既定 OFF）。

    ON 時、Web/LINE チャネルでは「店内のスタッフに連絡」系の文言を
    公的窓口（119/110/受診）中心の文言に置き換える。店頭キオスク
    （`is_kiosk_deployment()`）ではスタッフ文言を維持する。
    """
    return _flag("SAFETY_EMERGENCY_CHANNEL_SPLIT", False)


def is_kiosk_deployment() -> bool:
    """このデプロイが店頭キオスク運用かどうか（既定 False = Web/LINE 相当）。

    店頭キオスクは物理的に別デプロイ/別インスタンスとして運用される想定のため、
    セッション単位ではなくデプロイ単位の環境フラグで判定する。
    """
    return _flag("EMERGENCY_KIOSK_MODE", False)


def is_counseling_context_maintain_enabled() -> bool:
    """counseling_mode.active 中の期間/状況フォローアップで文脈を維持する（既定 OFF）。

    ON 時、triage が Physical と判定しても、明確な身体症状キーワードを含まない
    フォローアップ回答（「1ヶ月ほどです」「残業が続いています」等）ではカウンセリングを
    終了しない（「1ヶ月ほどです」等が no_recommendation 受診テンプレへ落ちる回帰の是正）。
    """
    return _flag("UX_COUNSELING_CONTEXT_MAINTAIN", False)


def is_counseling_tone_variety_enabled() -> bool:
    """counseling 応答の定型句（「応援しています」等）反復を抑制する（既定 OFF）。

    ON 時、プロンプトの定型句リテラル例示を抽象化し、直近使用済みの定型句を
    避けるよう LLM に指示する。エラーフォールバックの定型句もローテーションする。
    """
    return _flag("UX_COUNSELING_TONE_VARIETY", False)


def is_concierge_intent_routing_enabled() -> bool:
    """Concierge 意図分類の拡張プローブ（API/SSE/rule_based 等）を有効化する（既定 OFF）。

    ON 時、`_META_PROBE_RULES` に無い技術系メタ質問（「APIの仕組みを教えて」「SSEについて」
    「rule_basedとは」「医薬品推奨の仕組み」等）も architecture intent として検出する。
    技術詳細コンテンツ（concierge_knowledge.ja.json の technical_details）は本フラグ ON かつ
    development ランタイムの場合のみ参照される（production は既存の抽象的な内容のまま）。
    """
    return _flag("ROUTING_CONCIERGE_INTENT", False)


def is_concierge_followup_routing_enabled() -> bool:
    """Concierge フォローアップ文脈維持（MR-4）を有効化する（既定 OFF）。

    ON 時、直前ターンの concierge_intent（redirect 含む）を継承し、
    「具体例を教えて」「SSEについて」「Cloud Runは？」等の短いトピック継続を
    gate / orchestrator で Concierge に優先ルーティングする（症状文脈より優先）。
    """
    return _flag("ROUTING_CONCIERGE_FOLLOWUP", False)


def is_store_procurement_routing_enabled() -> bool:
    """医薬品購入先クエリ（「OTCを買える店」「市販薬の購入先」等）の Store ルーティングを補完する（既定 OFF）。

    ON 時、`classify_medicine_procurement_route` は明示的な処方箋文脈が無くても
    OTC/市販薬文脈が明示されていれば "otc_store" をデフォルトとする
    （店舗案内へ正しく振り分け、`counseling_unknown_request`/Physical への誤流入を防ぐ）。
    """
    return _flag("ROUTING_STORE_PROCUREMENT", False)


def is_low_risk_headache_reco_enabled() -> bool:
    """頻出・低リスクの単独頭痛で OTC 解熱鎮痛薬を提示する（既定 OFF）。

    ON 時、年齢未入力セッションでも主要解熱鎮痛薬を `_filter_medicines_when_age_unknown`
    で全除外しない（小児文脈・赤旗頭痛は除外）。めまい等 CAUTION_DEFER 症状は変更しない。
    """
    return _flag("RECO_LOW_RISK_HEADACHE", False)


def is_ux_correction_delete_cancel_enabled() -> bool:
    """削除確認待ちからの「キャンセル」「やっぱり消さない」を SessionOps で明示応答する（既定 OFF）。

    ON 時、pending_memory_delete がセッションに無くても dialogue_state.pending.session_delete
    または直前 bot の memory_delete_confirm から削除確認待ちを復元し、
    counseling_unknown_request へ流さず memory_delete_cancelled を返す。
    """
    return _flag("UX_CORRECTION_DELETE_CANCEL", False)


def is_ux_session_ops_real_data_enabled() -> bool:
    """SessionOps の質問種別ごとに実データ応答を返す（既定 OFF）。

    ON 時、ステータス / 記録項目一覧 / LLM要約 / 会話履歴参照を別 handler・別 kind で出し分ける。
    OFF 時は従来どおり status→統合ステータス、summarize→要約（履歴参照も要約経路）の使い回し。
    """
    return _flag("UX_SESSION_OPS_REAL_DATA", False)


def is_ux_progressive_clarification_enabled() -> bool:
    """曖昧入力連続時に clarification 文案を段階的に変える（既定 OFF）。

    ON 時、1回目は従来の確認質問、2回目は別の症状例・選択肢、3回目以降は既存の
    clarification ループ脱出（llm_unavailable short_circuit）と整合する。
    """
    return _flag("UX_PROGRESSIVE_CLARIFICATION", False)


def is_ux_reco_dedup_enabled() -> bool:
    """マルチターン同一推奨の抑制 + 終了意図検出（既定 OFF）。

    ON 時、前ターンと同一の推奨薬リストは再推奨せず要約応答へ。
    「ありがとう」「これで終わり」等の終了意図では sage_reco を出さず締め応答へ。
    """
    return _flag("UX_RECO_DEDUP", False)
