/**
 * チャット処理進捗のポーリングと DOM 更新（多言語対応）
 */
(function (global) {
    'use strict';

    var pollRoot = global.__mrcProcessingPoll = global.__mrcProcessingPoll || {
        timer: null,
        sessionId: null,
        useAdminSession: false,
        onUpdate: null,
        onInactive: null,
        hasSeenActive: false,
        inactiveStreak: 0,
        generation: 0,
    };
    var lastRenderedKey = '';
    var lastApiLanguage = null;
    var INPUT_LANG_KEY = 'processingInputLanguage';

    var JAPANESE_MEDICAL_TERMS = [
        '精神疾患', 'うつ病', '統合失調症', '不安障害', 'パニック障害',
        '頭痛', '腹痛', '発熱', '咳', '鼻水', '下痢', '便秘', '吐き気',
        '不眠', '倦怠感', '疲労感', 'ストレス', 'イライラ', '不安',
        '風邪', 'インフルエンザ', '花粉症', 'アレルギー', '湿疹',
        '肩こり', '腰痛', '関節痛', '筋肉痛', 'めまい', '動悸',
        'のどの痛み', '喉の痛み', '胃痛', '胸痛', '背痛'
    ];

    var I18N = {
        ja: {
            badge: 'AI分析中',
            progressAria: '処理の進捗',
            defaultLabel: '処理中...',
            steps: {
                validate: '入力を確認しています',
                triage: '症状の種類を分析しています',
                diagnosis: '診断名を確認しています',
                emergency: '緊急度を確認しています',
                dialect: '言葉遣いを整えています',
                store: '店舗案内か確認しています',
                counseling: 'お話を整理しています',
                attributes: 'お客様情報を確認しています',
                symptom_analysis: '症状を詳しく分析しています',
                medicine_select: 'お薬を選定しています',
                medicine_qa: '医薬品の質問に回答しています',
                safety: '安全性を確認しています',
                usage_notes: '使用上の注意を作成しています',
                translate: '回答を整えています',
                finalize: '回答を仕上げています'
            },
            stepDetails: {
                emergency: {
                    crisis_language: 'クライシス対応を準備しています',
                    medical_self: '医療緊急の案内を準備しています',
                    store_incident: '店舗インシデント対応を準備しています',
                    emergency_dispatch: '緊急応答を準備しています'
                },
                medicine_select: {
                    explanation: '推奨理由を作成しています'
                },
                attributes: {
                    nlu: '症状と属性を整理しています'
                }
            }
        },
        en: {
            badge: 'AI analyzing',
            progressAria: 'Processing progress',
            defaultLabel: 'Processing...',
            steps: {
                validate: 'Checking your input',
                triage: 'Analyzing symptom type',
                diagnosis: 'Checking diagnosis terms',
                emergency: 'Assessing urgency',
                dialect: 'Normalizing wording',
                store: 'Checking store inquiries',
                counseling: 'Organizing your message',
                attributes: 'Reviewing your profile',
                symptom_analysis: 'Analyzing symptoms in detail',
                medicine_select: 'Selecting medicines',
                safety: 'Checking safety',
                usage_notes: 'Preparing usage instructions',
                translate: 'Preparing your answer',
                finalize: 'Finalizing response'
            },
            stepDetails: {
                emergency: {
                    crisis_language: 'Preparing crisis support response',
                    medical_self: 'Preparing medical emergency guidance',
                    store_incident: 'Preparing store incident response',
                    emergency_dispatch: 'Preparing emergency response'
                },
                medicine_select: {
                    explanation: 'Generating recommendation reasons'
                }
            }
        },
        ko: {
            badge: 'AI 분석 중',
            progressAria: '처리 진행 상황',
            defaultLabel: '처리 중...',
            steps: {
                validate: '입력 내용을 확인하고 있습니다',
                triage: '증상 유형을 분석하고 있습니다',
                diagnosis: '진단명을 확인하고 있습니다',
                emergency: '긴급도를 확인하고 있습니다',
                dialect: '표현을 정리하고 있습니다',
                store: '매장 안내 여부를 확인하고 있습니다',
                counseling: '대화 내용을 정리하고 있습니다',
                attributes: '고객 정보를 확인하고 있습니다',
                symptom_analysis: '증상을 자세히 분석하고 있습니다',
                medicine_select: '의약품을 선정하고 있습니다',
                safety: '안전성을 확인하고 있습니다',
                usage_notes: '사용상의 주의를 작성하고 있습니다',
                translate: '답변을 정리하고 있습니다',
                finalize: '답변을 마무리하고 있습니다'
            },
            stepDetails: {
                emergency: {
                    crisis_language: '위기 대응을 준비하고 있습니다',
                    medical_self: '의료 응급 안내를 준비하고 있습니다',
                    store_incident: '매장 인시던트 대응을 준비하고 있습니다',
                    emergency_dispatch: '응급 응답을 준비하고 있습니다'
                },
                medicine_select: {
                    explanation: '추천 이유를 작성하고 있습니다'
                }
            }
        },
        zh: {
            badge: 'AI分析中',
            progressAria: '处理进度',
            defaultLabel: '处理中...',
            steps: {
                validate: '正在确认输入内容',
                triage: '正在分析症状类型',
                diagnosis: '正在确认诊断名称',
                emergency: '正在确认紧急程度',
                dialect: '正在整理措辞',
                store: '正在确认是否为门店咨询',
                counseling: '正在整理对话内容',
                attributes: '正在确认您的信息',
                symptom_analysis: '正在详细分析症状',
                medicine_select: '正在筛选药品',
                safety: '正在确认安全性',
                usage_notes: '正在生成使用注意事项',
                translate: '正在整理回复',
                finalize: '正在完成回复'
            },
            stepDetails: {
                emergency: {
                    crisis_language: '正在准备危机支援回复',
                    medical_self: '正在准备医疗紧急指引',
                    store_incident: '正在准备店内事件应对',
                    emergency_dispatch: '正在准备紧急回复'
                },
                medicine_select: {
                    explanation: '正在生成推荐理由'
                }
            }
        }
    };

    function normalizeLang(lang) {
        if (lang === 'ja' || lang === 'en' || lang === 'ko' || lang === 'zh') {
            return lang;
        }
        return null;
    }

    function getUiLanguage() {
        if (typeof global.currentLanguage === 'string' && global.currentLanguage) {
            return global.currentLanguage;
        }
        try {
            return sessionStorage.getItem('language') || 'ja';
        } catch (e) {
            return 'ja';
        }
    }

    function getProcessingLanguage() {
        try {
            var stored = sessionStorage.getItem(INPUT_LANG_KEY);
            if (normalizeLang(stored)) {
                return stored;
            }
        } catch (e) { /* ignore */ }
        if (normalizeLang(lastApiLanguage)) {
            return lastApiLanguage;
        }
        return null;
    }

    function setProcessingLanguage(lang) {
        lang = normalizeLang(lang);
        if (!lang) {
            return;
        }
        try {
            sessionStorage.setItem(INPUT_LANG_KEY, lang);
        } catch (e) { /* ignore */ }
    }

    function detectInputLanguage(text, uiLang) {
        if (!text || typeof text !== 'string') {
            return 'ja';
        }
        text = text.trim();
        if (!text) {
            return 'ja';
        }

        uiLang = normalizeLang(uiLang) || getUiLanguage();

        if (uiLang && uiLang !== 'en' && uiLang === 'ja' && text.length <= 10) {
            if (JAPANESE_MEDICAL_TERMS.indexOf(text) !== -1) {
                return 'ja';
            }
        }

        if (/[\uAC00-\uD7AF]/.test(text)) {
            return 'ko';
        }

        if (/[\u4E00-\u9FFF]/.test(text)) {
            if (/[\u3040-\u309F\u30A0-\u30FF]/.test(text)) {
                return 'ja';
            }
            if (text.length <= 10) {
                if (JAPANESE_MEDICAL_TERMS.indexOf(text) !== -1) {
                    return 'ja';
                }
                if (uiLang === 'ja') {
                    return 'ja';
                }
            }
            return 'zh';
        }

        if (/[\u3040-\u309F\u30A0-\u30FF]/.test(text)) {
            return 'ja';
        }

        return 'en';
    }

    function getCurrentLang(data) {
        if (data && normalizeLang(data.language)) {
            return data.language;
        }
        var inputLang = getProcessingLanguage();
        if (inputLang) {
            return inputLang;
        }
        return getUiLanguage();
    }

    function getLocale(lang) {
        return I18N[lang] || I18N.ja;
    }

    function localizeStatusData(data) {
        if (!data || !data.active) {
            return data;
        }
        if (normalizeLang(data.language)) {
            lastApiLanguage = data.language;
            setProcessingLanguage(data.language);
        }
        var lang = getCurrentLang(data);
        var locale = getLocale(lang);
        var stepId = data.step_id;
        var label = (stepId && locale.steps[stepId]) ? locale.steps[stepId] : (data.label || locale.defaultLabel);
        var detailLabel = data.detail_label || '';
        if (!detailLabel && data.detail_code && stepId && locale.stepDetails && locale.stepDetails[stepId]) {
            detailLabel = locale.stepDetails[stepId][data.detail_code] || '';
        }
        return {
            active: true,
            step_id: stepId,
            label: label,
            detail_label: detailLabel,
            detail_code: data.detail_code || '',
            step: data.step,
            total: data.total,
            percent: data.percent,
            language: lang,
            badge: locale.badge,
            progressAria: locale.progressAria,
            advice_preview: data.advice_preview || '',
            flow_id: data.flow_id || '',
            flow_description: data.flow_description || '',
            flow_hint: data.flow_hint || '',
            agent_name: data.agent_name || '',
            agent_role: data.agent_role || '',
            agent_description: data.agent_description || ''
        };
    }

    function statusKey(data) {
        if (!data || !data.active) return 'inactive';
        return [
            getCurrentLang(data), data.flow_id, data.step_id, data.detail_code,
            data.agent_name, data.step, data.percent, data.label,
            data.detail_label, data.flow_hint, data.advice_preview || ''
        ].join(':');
    }

    function buildProcessingCardElement(label, step, total, percent, badge, progressAria, detailLabel, meta) {
        meta = meta || {};
        var safePercent = Math.min(100, Math.max(0, percent || 0));

        var card = document.createElement('div');
        card.className = 'processing-status-card';

        var header = document.createElement('div');
        header.className = 'processing-status-header';

        var badgeEl = document.createElement('span');
        badgeEl.className = 'processing-status-badge';
        badgeEl.textContent = badge || 'AI分析中';

        var pillEl = document.createElement('span');
        pillEl.className = 'processing-status-step-pill';
        pillEl.textContent = (step || 0) + ' / ' + (total || 14);

        header.appendChild(badgeEl);
        header.appendChild(pillEl);

        var labelEl = document.createElement('p');
        labelEl.className = 'processing-status-label';
        labelEl.textContent = label || '処理中...';

        var track = document.createElement('div');
        track.className = 'processing-status-track';
        track.setAttribute('role', 'progressbar');
        track.setAttribute('aria-valuenow', String(safePercent));
        track.setAttribute('aria-valuemin', '0');
        track.setAttribute('aria-valuemax', '100');
        track.setAttribute('aria-label', progressAria || '処理の進捗');

        var fill = document.createElement('div');
        fill.className = 'processing-status-bar-fill';
        fill.style.width = safePercent + '%';

        track.appendChild(fill);
        card.appendChild(header);
        card.appendChild(labelEl);
        if (detailLabel) {
            var detailEl = document.createElement('p');
            detailEl.className = 'processing-status-detail';
            detailEl.style.cssText = 'margin: 4px 0 0; font-size: 0.85em; color: #555;';
            detailEl.textContent = detailLabel;
            card.appendChild(detailEl);
        }
        if (meta.agent_name) {
            var agentEl = document.createElement('p');
            agentEl.className = 'processing-status-agent';
            agentEl.style.cssText = 'margin: 6px 0 0; font-size: 0.8em; color: #2e7d32; font-weight: 600;';
            var agentLine = '【' + meta.agent_name + '】';
            if (meta.agent_role) {
                agentLine += ' ' + meta.agent_role;
            }
            agentEl.textContent = agentLine;
            card.appendChild(agentEl);
        }
        if (meta.agent_description) {
            var agentDescEl = document.createElement('p');
            agentDescEl.className = 'processing-status-agent-desc';
            agentDescEl.style.cssText = 'margin: 2px 0 0; font-size: 0.75em; color: #666;';
            agentDescEl.textContent = meta.agent_description;
            card.appendChild(agentDescEl);
        }
        if (meta.flow_description) {
            var flowEl = document.createElement('p');
            flowEl.className = 'processing-status-flow';
            flowEl.style.cssText = 'margin: 4px 0 0; font-size: 0.75em; color: #1565c0;';
            flowEl.textContent = 'フロー: ' + meta.flow_description;
            card.appendChild(flowEl);
        }
        if (meta.flow_hint) {
            var hintEl = document.createElement('p');
            hintEl.className = 'processing-status-flow-hint';
            hintEl.style.cssText = 'margin: 2px 0 0; font-size: 0.75em; color: #555;';
            hintEl.textContent = meta.flow_hint;
            card.appendChild(hintEl);
        }
        card.appendChild(track);

        return card;
    }

    function mountProcessingCard(container, label, step, total, percent, badge, progressAria, detailLabel, meta) {
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
        container.appendChild(buildProcessingCardElement(label, step, total, percent, badge, progressAria, detailLabel, meta));
    }

    function getTypingIndicatorHtml() {
        var locale = getLocale(getCurrentLang(null));
        var bubble = document.createElement('div');
        bubble.className = 'message-content processing-status-bubble';

        var wrapper = document.createElement('div');
        wrapper.className = 'processing-status-wrapper';
        wrapper.appendChild(buildProcessingCardElement(
            locale.steps.validate,
            1,
            14,
            0,
            locale.badge,
            locale.progressAria
        ));
        var slowSlot = document.createElement('div');
        slowSlot.className = 'processing-slow-request-slot';
        bubble.appendChild(wrapper);
        bubble.appendChild(slowSlot);
        return bubble.outerHTML;
    }

    function renderProcessingStatus(targetEl, data) {
        if (!targetEl || !data || !data.active) return;

        var localized = localizeStatusData(data);
        var label = localized.label;
        var detailLabel = localized.detail_label || '';
        var step = localized.step || 0;
        var total = localized.total || 14;
        var percent = Math.min(100, Math.max(0, localized.percent || 0));
        var badge = localized.badge;
        var progressAria = localized.progressAria;
        var key = statusKey(localized);

        var bubble = targetEl.querySelector('.processing-status-bubble') ||
            targetEl.querySelector('.message-content');
        var host = bubble || targetEl;
        if (host && host.classList) {
            host.classList.add('processing-status-bubble');
        }

        var wrapper = targetEl.querySelector('.processing-status-wrapper');
        if (!wrapper && host) {
            wrapper = document.createElement('div');
            wrapper.className = 'processing-status-wrapper';
            host.appendChild(wrapper);
        }
        if (!wrapper) return;

        var previewEl = wrapper.querySelector('.processing-advice-preview');
        if (localized.advice_preview) {
            if (!previewEl) {
                previewEl = document.createElement('div');
                previewEl.className = 'processing-advice-preview';
                wrapper.appendChild(previewEl);
            }
            previewEl.textContent = localized.advice_preview;
        } else if (previewEl) {
            previewEl.remove();
        }

        var meta = {
            agent_name: localized.agent_name,
            agent_role: localized.agent_role,
            agent_description: localized.agent_description,
            flow_description: localized.flow_description,
            flow_hint: localized.flow_hint
        };
        if (key !== lastRenderedKey || !wrapper.querySelector('.processing-status-label')) {
            mountProcessingCard(wrapper, label, step, total, percent, badge, progressAria, detailLabel, meta);
            lastRenderedKey = key;
            return;
        }

        var badgeEl = wrapper.querySelector('.processing-status-badge');
        var labelEl = wrapper.querySelector('.processing-status-label');
        var detailEl = wrapper.querySelector('.processing-status-detail');
        var agentEl = wrapper.querySelector('.processing-status-agent');
        var flowEl = wrapper.querySelector('.processing-status-flow');
        var fillEl = wrapper.querySelector('.processing-status-bar-fill');
        var trackEl = wrapper.querySelector('.processing-status-track');
        var pillEl = wrapper.querySelector('.processing-status-step-pill');

        if (badgeEl) badgeEl.textContent = badge;
        if (labelEl) labelEl.textContent = label;
        if (detailLabel) {
            if (!detailEl) {
                detailEl = document.createElement('p');
                detailEl.className = 'processing-status-detail';
                detailEl.style.cssText = 'margin: 4px 0 0; font-size: 0.85em; color: #555;';
                if (labelEl && labelEl.parentNode) {
                    labelEl.parentNode.insertBefore(detailEl, labelEl.nextSibling);
                }
            }
            detailEl.textContent = detailLabel;
        } else if (detailEl) {
            detailEl.remove();
        }
        if (agentEl && meta.agent_name) {
            agentEl.textContent = '【' + meta.agent_name + '】' + (meta.agent_role ? ' ' + meta.agent_role : '');
        }
        if (flowEl && meta.flow_description) {
            flowEl.textContent = 'フロー: ' + meta.flow_description;
        }
        if (pillEl) pillEl.textContent = step + ' / ' + total;
        if (fillEl) fillEl.style.width = percent + '%';
        if (trackEl) {
            trackEl.setAttribute('aria-valuenow', String(percent));
            trackEl.setAttribute('aria-label', progressAria);
        }
        lastRenderedKey = key;
    }

    function shouldStopPollingForInactive() {
        if (pollRoot.hasSeenActive && pollRoot.inactiveStreak >= 2) {
            return true;
        }
        if (!pollRoot.hasSeenActive && pollRoot.inactiveStreak >= 3) {
            return true;
        }
        return false;
    }

    function finishPollingInactive() {
        var cb = pollRoot.onInactive;
        var hadActive = pollRoot.hasSeenActive;
        stopProcessingPoll();
        if (typeof cb === 'function') {
            try {
                cb({ hasSeenActive: hadActive });
            } catch (e) { /* ignore */ }
        }
    }

    function pollOnce() {
        if (!pollRoot.timer) {
            return;
        }
        var gen = pollRoot.generation;
        var url = '/api/processing-status';
        if (pollRoot.useAdminSession && pollRoot.sessionId) {
            url += '?session_id=' + encodeURIComponent(pollRoot.sessionId);
        }
        fetch(url, { credentials: 'include', headers: { 'Cache-Control': 'no-cache' } })
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                if (!pollRoot.timer || gen !== pollRoot.generation) {
                    return;
                }
                var payload = localizeStatusData(data || { active: false }) || { active: false };
                if (payload.active) {
                    pollRoot.hasSeenActive = true;
                    pollRoot.inactiveStreak = 0;
                } else {
                    pollRoot.inactiveStreak += 1;
                }
                if (typeof pollRoot.onUpdate === 'function') {
                    pollRoot.onUpdate(payload);
                }
                if (!payload.active && shouldStopPollingForInactive()) {
                    finishPollingInactive();
                }
            })
            .catch(function () { /* ignore */ });
    }

    function startProcessingPoll(options) {
        options = options || {};
        stopProcessingPoll();
        pollRoot.generation += 1;
        pollRoot.sessionId = options.sessionId || null;
        pollRoot.useAdminSession = Boolean(options.adminSession);
        pollRoot.onUpdate = options.onUpdate || null;
        pollRoot.onInactive = options.onInactive || null;
        pollRoot.hasSeenActive = false;
        pollRoot.inactiveStreak = 0;
        var interval = options.interval || 1000;
        var maxPolls = options.maxPolls || 180;
        var pollCount = 0;
        lastRenderedKey = '';
        lastApiLanguage = null;
        pollOnce();
        pollCount += 1;
        pollRoot.timer = setInterval(function () {
            pollCount += 1;
            if (pollCount >= maxPolls) {
                finishPollingInactive();
                return;
            }
            pollOnce();
        }, interval);
    }

    function stopProcessingPoll() {
        pollRoot.generation += 1;
        if (pollRoot.timer) {
            clearInterval(pollRoot.timer);
            pollRoot.timer = null;
        }
        pollRoot.sessionId = null;
        pollRoot.useAdminSession = false;
        pollRoot.onUpdate = null;
        pollRoot.onInactive = null;
        pollRoot.hasSeenActive = false;
        pollRoot.inactiveStreak = 0;
        lastRenderedKey = '';
        lastApiLanguage = null;
    }

    if (typeof document !== 'undefined') {
        document.addEventListener('DOMContentLoaded', function () {
            stopProcessingPoll();
        });
        window.addEventListener('pagehide', function () {
            stopProcessingPoll();
        });
    }

    global.ProcessingStatus = {
        startProcessingPoll: startProcessingPoll,
        stopProcessingPoll: stopProcessingPoll,
        renderProcessingStatus: renderProcessingStatus,
        getTypingIndicatorHtml: getTypingIndicatorHtml,
        localizeStatusData: localizeStatusData,
        getCurrentLang: getCurrentLang,
        getUiLanguage: getUiLanguage,
        getProcessingLanguage: getProcessingLanguage,
        setProcessingLanguage: setProcessingLanguage,
        detectInputLanguage: detectInputLanguage
    };
})(typeof window !== 'undefined' ? window : this);
