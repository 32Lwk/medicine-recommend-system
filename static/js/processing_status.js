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
        keepAliveWhileLocked: false,
        hasSeenActive: false,
        inactiveStreak: 0,
        generation: 0,
        pollIntervalMs: 2500,
        pollBackoffMs: 2500,
        ssePaused: false,
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
            agentPrefix: '担当: ',
            flowPrefix: 'フロー: ',
            agentNames: {},
            slowHints: {},
            flowSteps: {},
            steps: {
                validate: '入力を確認しています',
                triage: '症状の種類を分析しています',
                diagnosis: '診断名を確認しています',
                emergency: '緊急度を確認しています',
                dialect: '言葉遣いを整えています',
                store: '店舗案内か確認しています',
                counseling: 'お話を整理しています',
                attributes: 'お客様情報を確認しています',
                symptom_analysis: '症状の内容を読み取り、該当する市販薬の種類を判定しています',
                medicine_select: 'お薬を選定しています',
                medicine_qa: '医薬品の質問に回答しています',
                concierge: 'ご案内を準備しています',
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
                    explanation: '推奨理由を作成しています',
                    rule_match: '症状に合う市販薬候補をルールで照合しています',
                    candidate_match: '候補を照合しています'
                },
                attributes: {
                    nlu: '症状と属性を整理しています'
                },
                symptom_analysis: {
                    llm_classify: 'AIで症状と医薬品の種類を分類しています',
                    symptom_extract: 'お話から症状キーワードを抽出しています',
                    symptom_check: '症状を確認しています',
                    contraindication_prep: '年齢・妊娠・併用薬など禁忌の前提を確認しています'
                }
            },
            flowSteps: {
                physical: {
                    triage: '症状相談として受け付けています',
                    symptom_analysis: '症状を確認しています',
                    medicine_select: '候補を照合しています'
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
                symptom_analysis: 'Reading symptoms and determining OTC medicine type',
                medicine_select: 'Selecting medicines',
                medicine_qa: 'Answering your medicine question',
                concierge: 'Preparing guidance',
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
                    explanation: 'Generating recommendation reasons',
                    rule_match: 'Matching OTC candidates to your symptoms',
                    candidate_match: 'Comparing medicine candidates'
                },
                symptom_analysis: {
                    llm_classify: 'Classifying symptoms and OTC medicine type with AI',
                    symptom_extract: 'Extracting symptom keywords from your message',
                    symptom_check: 'Reviewing your symptoms',
                    contraindication_prep: 'Checking age, pregnancy, and drug interaction prerequisites'
                },
                medicine_qa: {
                    context_load: 'Reviewing previously recommended medicines',
                    history_read: 'Reading the conversation context',
                    question_parse: 'Summarizing your question',
                    interaction_check: 'Checking drug interaction cautions',
                    doping_check: 'Checking sports and testing cautions',
                    side_effect_check: 'Reviewing side effect information',
                    answer_draft: 'Drafting the answer',
                    answer_compose: 'Composing an easy-to-read answer',
                    safety_review: 'Final safety review',
                    format_response: 'Formatting the response for display'
                },
                attributes: {
                    nlu: 'Analyzing symptoms and profile'
                }
            },
            agentPrefix: 'Agent: ',
            flowPrefix: 'Flow: ',
            agentNames: {
                TriageAgent: 'Triage Agent',
                SafetyGate: 'Safety Gate',
                NLUAgent: 'NLU',
                PhysicalOrchestrator: 'Recommendation',
                ExplanationAgent: 'Explanation',
                CounselingManager: 'Counseling',
                ConciergeAgent: 'Concierge',
                StoreInquiryAgent: 'Store Info',
                EmergencyRouter: 'Emergency',
                MedicineQAAgent: 'Medicine Q&A',
                ModerationAgent: 'Moderation',
                ChatOrchestrator: 'Orchestrator'
            },
            slowHints: {
                symptom_analysis: {
                    llm_classify: 'AI analysis may take a moment. Please wait.'
                },
                medicine_qa: {
                    answer_compose: 'Preparing your answer. Please wait.',
                    answer_draft: 'Preparing your answer. Please wait.'
                },
                medicine_select: {
                    scoring: 'Evaluating many candidates may take a moment.',
                    candidate_search: 'Searching the database. Please wait.',
                    explanation: 'Generating recommendation reasons. Please wait.'
                },
                attributes: {
                    nlu: 'Organizing symptoms may take a moment.'
                }
            },
            flowSteps: {
                ask_qa: {
                    triage: 'Checking the type of inquiry',
                    medicine_qa: 'Preparing your medicine Q&A answer'
                },
                physical: {
                    triage: 'Routing as a symptom consultation',
                    symptom_analysis: 'Reading symptoms and finding OTC medicine types',
                    medicine_select: 'Comparing medicine candidates'
                },
                greeting: {
                    triage: 'Checking if this is a greeting'
                },
                store: {
                    store: 'Checking your store-related question'
                }
            }
        },
        ko: {
            badge: 'AI 분석 중',
            progressAria: '처리 진행 상황',
            defaultLabel: '처리 중...',
            agentPrefix: '담당: ',
            flowPrefix: '플로우: ',
            agentNames: {
                TriageAgent: '트리아지',
                SafetyGate: '안전 게이트',
                NLUAgent: 'NLU',
                PhysicalOrchestrator: '증상 추천',
                ExplanationAgent: '추천 이유',
                CounselingManager: '상담',
                ConciergeAgent: '안내',
                StoreInquiryAgent: '매장 안내',
                EmergencyRouter: '긴급 대응',
                MedicineQAAgent: '의약품 Q&A',
                ModerationAgent: '모더레이션',
                ChatOrchestrator: '오케스트레이터'
            },
            slowHints: {
                symptom_analysis: {
                    llm_classify: 'AI 분석 중입니다. 잠시만 기다려 주세요.'
                },
                medicine_qa: {
                    answer_compose: '답변을 작성하고 있습니다. 잠시만 기다려 주세요.',
                    answer_draft: '답변을 작성하고 있습니다. 잠시만 기다려 주세요.'
                },
                medicine_select: {
                    scoring: '후보가 많으면 평가에 시간이 걸릴 수 있습니다.',
                    candidate_search: '데이터베이스를 검색하고 있습니다. 잠시만 기다려 주세요.',
                    explanation: '추천 이유를 생성하고 있습니다. 잠시만 기다려 주세요.'
                },
                attributes: {
                    nlu: '증상 정리 중입니다. 잠시만 기다려 주세요.'
                }
            },
            flowSteps: {
                ask_qa: {
                    triage: '상담 유형을 확인하고 있습니다',
                    medicine_qa: '의약품 Q&A 답변을 준비하고 있습니다'
                },
                physical: {
                    triage: '증상 상담으로 접수하고 있습니다',
                    symptom_analysis: '증상을 읽고 해당 일반의약품 종류를 찾고 있습니다',
                    medicine_select: '후보 의약품을 비교하고 있습니다'
                },
                greeting: {
                    triage: '인사인지 확인하고 있습니다'
                },
                store: {
                    store: '매장 관련 질문을 확인하고 있습니다'
                }
            },
            steps: {
                validate: '입력 내용을 확인하고 있습니다',
                triage: '증상 유형을 분석하고 있습니다',
                diagnosis: '진단명을 확인하고 있습니다',
                emergency: '긴급도를 확인하고 있습니다',
                dialect: '표현을 정리하고 있습니다',
                store: '매장 안내 여부를 확인하고 있습니다',
                counseling: '대화 내용을 정리하고 있습니다',
                attributes: '고객 정보를 확인하고 있습니다',
                symptom_analysis: '증상 내용을 읽고 해당 일반의약품 종류를 판정하고 있습니다',
                medicine_select: '의약품을 선정하고 있습니다',
                medicine_qa: '의약품 질문에 답변하고 있습니다',
                concierge: '안내 문구를 준비하고 있습니다',
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
                    explanation: '추천 이유를 작성하고 있습니다',
                    rule_match: '증상에 맞는 일반의약품 후보를 규칙으로 대조하고 있습니다'
                },
                symptom_analysis: {
                    llm_classify: 'AI로 증상과 의약품 종류를 분류하고 있습니다',
                    symptom_extract: '대화에서 증상 키워드를 추출하고 있습니다',
                    contraindication_prep: '연령·임신·병용 약 등 금기 전제를 확인하고 있습니다'
                },
                medicine_qa: {
                    context_load: '이전에 추천한 의약품을 확인하고 있습니다',
                    history_read: '대화 흐름을 읽고 있습니다',
                    question_parse: '질문 요점을 정리하고 있습니다',
                    interaction_check: '병용 주의를 확인하고 있습니다',
                    doping_check: '경기·검사 관련 주의를 확인하고 있습니다',
                    side_effect_check: '부작용 정보를 확인하고 있습니다',
                    answer_draft: '답변 초안을 작성하고 있습니다',
                    answer_compose: '이해하기 쉬운 답변으로 정리하고 있습니다',
                    safety_review: '안전 주의를 최종 확인하고 있습니다',
                    format_response: '답변을 보기 쉽게 정리하고 있습니다'
                },
                attributes: {
                    nlu: '증상과 정보를 정리하고 있습니다'
                }
            }
        },
        zh: {
            badge: 'AI分析中',
            progressAria: '处理进度',
            defaultLabel: '处理中...',
            agentPrefix: '负责: ',
            flowPrefix: '流程: ',
            agentNames: {
                TriageAgent: '分诊',
                SafetyGate: '安全门',
                NLUAgent: 'NLU',
                PhysicalOrchestrator: '症状推荐',
                ExplanationAgent: '推荐理由',
                CounselingManager: '咨询',
                ConciergeAgent: '前台指引',
                StoreInquiryAgent: '门店咨询',
                EmergencyRouter: '紧急应对',
                MedicineQAAgent: '药品问答',
                ModerationAgent: '内容审核',
                ChatOrchestrator: '编排器'
            },
            slowHints: {
                symptom_analysis: {
                    llm_classify: 'AI 分析中，请稍候。'
                },
                medicine_qa: {
                    answer_compose: '正在撰写回答，请稍候。',
                    answer_draft: '正在撰写回答，请稍候。'
                },
                medicine_select: {
                    scoring: '候选较多时评估可能需要一些时间。',
                    candidate_search: '正在搜索数据库，请稍候。',
                    explanation: '正在生成推荐理由，请稍候。'
                },
                attributes: {
                    nlu: '正在整理症状，请稍候。'
                }
            },
            flowSteps: {
                ask_qa: {
                    triage: '正在确认咨询类型',
                    medicine_qa: '正在准备药品问答回复'
                },
                physical: {
                    triage: '正在作为症状咨询受理',
                    symptom_analysis: '正在读取症状并查找适用的非处方药类型',
                    medicine_select: '正在比较药品候选'
                },
                greeting: {
                    triage: '正在确认是否为问候'
                },
                store: {
                    store: '正在确认门店相关问题'
                }
            },
            steps: {
                validate: '正在确认输入内容',
                triage: '正在分析症状类型',
                diagnosis: '正在确认诊断名称',
                emergency: '正在确认紧急程度',
                dialect: '正在整理措辞',
                store: '正在确认是否为门店咨询',
                counseling: '正在整理对话内容',
                attributes: '正在确认您的信息',
                symptom_analysis: '正在读取症状并判定适用的非处方药类型',
                medicine_select: '正在筛选药品',
                medicine_qa: '正在回答药品问题',
                concierge: '正在准备指引内容',
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
                    explanation: '正在生成推荐理由',
                    rule_match: '正在按规则比对符合症状的药品候选'
                },
                symptom_analysis: {
                    llm_classify: '正在用 AI 分类症状与药品类型',
                    symptom_extract: '正在从对话中提取症状关键词',
                    contraindication_prep: '正在确认年龄、妊娠与合并用药等禁忌前提'
                },
                medicine_qa: {
                    context_load: '正在确认此前推荐的药品',
                    history_read: '正在读取对话内容',
                    question_parse: '正在整理您的问题要点',
                    interaction_check: '正在确认药物相互作用注意事项',
                    doping_check: '正在确认竞技与检测相关注意事项',
                    side_effect_check: '正在确认副作用信息',
                    answer_draft: '正在起草回答',
                    answer_compose: '正在整理为易懂的回答',
                    safety_review: '正在进行安全注意事项的最终确认',
                    format_response: '正在将回答整理为易读格式'
                },
                attributes: {
                    nlu: '正在整理症状与属性'
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

    /** 処理バブルの表示言語（UI が非 ja のときは UI 言語を優先） */
    function getProcessingDisplayLang(data) {
        var uiLang = normalizeLang(getUiLanguage());
        if (uiLang && uiLang !== 'ja') {
            return uiLang;
        }
        return getCurrentLang(data);
    }

    function getLocale(lang) {
        return I18N[lang] || I18N.ja;
    }

    function pickClientStepLabel(data, locale) {
        var stepId = data.step_id;
        var detailCode = data.detail_code || '';
        var flowId = data.flow_id || '';
        if (detailCode && locale.stepDetails && locale.stepDetails[stepId]) {
            var detail = locale.stepDetails[stepId][detailCode];
            if (detail) {
                return detail;
            }
        }
        if (flowId && locale.flowSteps && locale.flowSteps[flowId] && locale.flowSteps[flowId][stepId]) {
            return locale.flowSteps[flowId][stepId];
        }
        if (stepId && locale.steps[stepId]) {
            return locale.steps[stepId];
        }
        return '';
    }

    function resolveLocalizedStepLabel(data, lang, locale) {
        if (lang !== 'ja') {
            var clientLabel = pickClientStepLabel(data, locale);
            if (clientLabel) {
                return clientLabel;
            }
            return locale.defaultLabel;
        }
        var serverDetail = (data.detail_label && String(data.detail_label).trim()) ? data.detail_label : '';
        if (serverDetail) {
            return serverDetail;
        }
        var serverLabel = (data.label && String(data.label).trim()) ? data.label : '';
        if (serverLabel) {
            return serverLabel;
        }
        var fallback = pickClientStepLabel(data, locale);
        return fallback || locale.defaultLabel;
    }

    function localizeAgentDisplay(data, lang, locale) {
        var agentName = data.agent_name || '';
        if (!agentName) {
            return lang === 'ja' ? (data.agent_display || '') : '';
        }
        if (lang === 'ja') {
            return data.agent_display || ((locale.agentPrefix || '担当: ') + agentName);
        }
        var prefix = locale.agentPrefix || 'Agent: ';
        var displayName = (locale.agentNames && locale.agentNames[agentName]) || agentName;
        return prefix + displayName;
    }

    function localizeSlowHint(data, lang, locale) {
        if (lang === 'ja') {
            return data.slow_hint || '';
        }
        var stepId = data.step_id;
        var detailCode = data.detail_code || '';
        if (stepId && detailCode && locale.slowHints && locale.slowHints[stepId]) {
            return locale.slowHints[stepId][detailCode] || '';
        }
        return '';
    }

    function localizeStatusData(data) {
        if (!data || !data.active) {
            return data;
        }
        if (normalizeLang(data.language)) {
            lastApiLanguage = data.language;
            setProcessingLanguage(data.language);
        }
        var lang = getProcessingDisplayLang(data);
        var locale = getLocale(lang);
        var stepId = data.step_id;
        var displayLabel = resolveLocalizedStepLabel(data, lang, locale);
        return {
            active: true,
            step_id: stepId,
            label: displayLabel,
            detail_label: '',
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
            agent_description: data.agent_description || '',
            agent_display: localizeAgentDisplay(data, lang, locale),
            slow_hint: localizeSlowHint(data, lang, locale),
            locale: locale
        };
    }

    function statusKey(data) {
        if (!data || !data.active) return 'inactive';
        return [
            getProcessingDisplayLang(data), data.flow_id, data.step_id, data.detail_code,
            data.step, data.percent, data.label, data.agent_display || '',
            data.slow_hint || '', data.advice_preview || ''
        ].join(':');
    }

    function shouldShowTechnicalMeta(targetEl) {
        if (!targetEl) return false;
        if (targetEl.id === 'ai-processing-banner') return true;
        if (targetEl.closest && targetEl.closest('#ai-processing-banner')) return true;
        return false;
    }

    function resolveMascotState(data) {
        if (!data) {
            return 'idle';
        }
        var stepId = data.step_id || '';
        var detailCode = data.detail_code || '';

        if (stepId === 'emergency' || stepId === 'safety') {
            return 'alert';
        }
        if (stepId === 'symptom_analysis') {
            if (detailCode === 'llm_classify' || detailCode === 'symptom_extract') {
                return 'scan';
            }
            return 'think';
        }
        if (detailCode === 'symptom_check') {
            return 'think';
        }
        if (stepId === 'attributes' || stepId === 'counseling' || stepId === 'medicine_qa') {
            return 'think';
        }
        if (stepId === 'medicine_select') {
            if (
                detailCode === 'rule_match' ||
                detailCode === 'candidate_match' ||
                detailCode === 'ranking'
            ) {
                return 'spark';
            }
            if (detailCode === 'explanation') {
                return 'compose';
            }
            return 'focus';
        }
        if (stepId === 'usage_notes' || stepId === 'finalize') {
            return 'compose';
        }
        if (stepId === 'triage' || stepId === 'diagnosis') {
            return 'peek';
        }
        if (stepId === 'concierge' || stepId === 'store' || stepId === 'translate') {
            return 'calm';
        }
        return 'idle';
    }

    function ensureProcessingMetaSection(card) {
        if (!card) {
            return null;
        }
        var meta = card.querySelector('.processing-status-meta');
        if (meta) {
            return meta;
        }
        meta = document.createElement('div');
        meta.className = 'processing-status-meta';
        var track = card.querySelector('.processing-status-track');
        if (track) {
            card.insertBefore(meta, track);
        } else {
            card.appendChild(meta);
        }
        return meta;
    }

    function setAgentUserDisplay(el, text) {
        if (!el) {
            return;
        }
        el.textContent = '';
        var raw = String(text || '').trim();
        if (!raw) {
            return;
        }
        var sep = raw.indexOf(': ');
        if (sep > 0) {
            var tagEl = document.createElement('span');
            tagEl.className = 'processing-status-agent-user__tag';
            tagEl.textContent = raw.slice(0, sep);
            var nameEl = document.createElement('span');
            nameEl.className = 'processing-status-agent-user__name';
            nameEl.textContent = raw.slice(sep + 2);
            el.appendChild(tagEl);
            el.appendChild(nameEl);
            return;
        }
        el.textContent = raw;
    }

    function createAgentUserElement(text) {
        var agentUserEl = document.createElement('div');
        agentUserEl.className = 'processing-status-agent-user';
        setAgentUserDisplay(agentUserEl, text);
        return agentUserEl;
    }

    function createSlowHintElement(text) {
        var slowHintEl = document.createElement('p');
        slowHintEl.className = 'processing-status-slow-hint';
        slowHintEl.textContent = text;
        return slowHintEl;
    }

    function mountProcessingMeta(card, slowHint, agentDisplay) {
        if (!card) {
            return;
        }
        var metaSection = ensureProcessingMetaSection(card);
        var slowHintEl = card.querySelector('.processing-status-slow-hint');
        var agentUserEl = card.querySelector('.processing-status-agent-user');
        if (slowHintEl && slowHintEl.parentNode !== metaSection) {
            metaSection.appendChild(slowHintEl);
        }
        if (agentUserEl && agentUserEl.parentNode !== metaSection) {
            metaSection.appendChild(agentUserEl);
        }
        if (slowHint) {
            if (!slowHintEl) {
                slowHintEl = createSlowHintElement(slowHint);
                metaSection.appendChild(slowHintEl);
            } else {
                slowHintEl.textContent = slowHint;
            }
        } else if (slowHintEl) {
            slowHintEl.remove();
            slowHintEl = null;
        }
        if (agentDisplay) {
            if (!agentUserEl || agentUserEl.tagName === 'P') {
                if (agentUserEl) {
                    agentUserEl.remove();
                }
                agentUserEl = createAgentUserElement(agentDisplay);
                metaSection.appendChild(agentUserEl);
            } else {
                setAgentUserDisplay(agentUserEl, agentDisplay);
            }
        } else if (agentUserEl) {
            agentUserEl.remove();
            agentUserEl = null;
        }
        if (slowHintEl && agentUserEl) {
            metaSection.insertBefore(slowHintEl, agentUserEl);
        }
        if (!metaSection.childNodes.length) {
            metaSection.remove();
        }
    }

    function buildProcessingCardElement(label, step, total, percent, badge, progressAria, detailLabel, meta) {
        meta = meta || {};
        var locale = meta.locale || getLocale(getCurrentLang(null));
        var showTechnical = Boolean(meta.showTechnical);
        var safePercent = Math.min(100, Math.max(0, percent || 0));

        var card = document.createElement('div');
        card.className = 'processing-status-card';

        var header = document.createElement('div');
        header.className = 'processing-status-header';

        var badgeEl = document.createElement('span');
        badgeEl.className = 'processing-status-badge';
        badgeEl.textContent = badge || locale.badge;

        var pillEl = document.createElement('span');
        pillEl.className = 'processing-status-step-pill';
        pillEl.textContent = (step || 0) + ' / ' + (total || 14);

        header.appendChild(badgeEl);
        header.appendChild(pillEl);

        var mascotRow = null;
        if (!showTechnical) {
            mascotRow = document.createElement('div');
            mascotRow.className = 'processing-status-mascot-row';
            var mascotEl = document.createElement('span');
            mascotEl.className = 'processing-status-mascot processing-status-mascot--' + (meta.mascotState || 'idle');
            mascotEl.setAttribute('aria-hidden', 'true');
            mascotRow.appendChild(mascotEl);
            card.appendChild(header);
            card.appendChild(mascotRow);
        } else {
            card.appendChild(header);
        }

        var labelEl = document.createElement('p');
        labelEl.className = 'processing-status-label';
        labelEl.textContent = label || locale.defaultLabel;

        var track = document.createElement('div');
        track.className = 'processing-status-track';
        track.setAttribute('role', 'progressbar');
        track.setAttribute('aria-valuenow', String(safePercent));
        track.setAttribute('aria-valuemin', '0');
        track.setAttribute('aria-valuemax', '100');
        track.setAttribute('aria-label', progressAria || locale.progressAria);

        var fill = document.createElement('div');
        fill.className = 'processing-status-bar-fill';
        fill.style.width = safePercent + '%';

        track.appendChild(fill);
        if (mascotRow) {
            mascotRow.appendChild(labelEl);
        } else {
            card.appendChild(labelEl);
        }
        if (!showTechnical && (meta.slow_hint || meta.agent_display)) {
            mountProcessingMeta(card, meta.slow_hint || '', meta.agent_display || '');
        }
        if (showTechnical && detailLabel) {
            var detailEl = document.createElement('p');
            detailEl.className = 'processing-status-detail';
            detailEl.style.cssText = 'margin: 4px 0 0; font-size: 0.85em; color: #555;';
            detailEl.textContent = detailLabel;
            card.appendChild(detailEl);
        }
        if (showTechnical && meta.agent_name) {
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
        if (showTechnical && meta.agent_description) {
            var agentDescEl = document.createElement('p');
            agentDescEl.className = 'processing-status-agent-desc';
            agentDescEl.style.cssText = 'margin: 2px 0 0; font-size: 0.75em; color: #666;';
            agentDescEl.textContent = meta.agent_description;
            card.appendChild(agentDescEl);
        }
        if (showTechnical && meta.flow_description) {
            var flowEl = document.createElement('p');
            flowEl.className = 'processing-status-flow';
            flowEl.style.cssText = 'margin: 4px 0 0; font-size: 0.75em; color: #1565c0;';
            flowEl.textContent = (locale.flowPrefix || 'フロー: ') + meta.flow_description;
            card.appendChild(flowEl);
        }
        if (showTechnical && meta.flow_hint) {
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
        var lang = getProcessingDisplayLang(null);
        var locale = getLocale(lang);
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
            locale.progressAria,
            '',
            { locale: locale }
        ));
        var slowSlot = document.createElement('div');
        slowSlot.className = 'processing-slow-request-slot';
        bubble.appendChild(wrapper);
        bubble.appendChild(slowSlot);
        return bubble.outerHTML;
    }

    function patchProcessingStatusDom(targetEl, data) {
        if (!targetEl || !data) {
            return false;
        }
        var localized = localizeStatusData(Object.assign({}, data, { active: true }));
        if (!localized || !localized.active) {
            return false;
        }
        var root = targetEl.querySelector('.processing-status-wrapper') ||
            targetEl.querySelector('.processing-status-bubble') ||
            targetEl.querySelector('.message-content') ||
            targetEl;
        var labelEl = root.querySelector('.processing-status-label');
        var pillEl = root.querySelector('.processing-status-step-pill');
        var fillEl = root.querySelector('.processing-status-bar-fill');
        var trackEl = root.querySelector('.processing-status-track');
        var badgeEl = root.querySelector('.processing-status-badge');
        if (!labelEl && !pillEl) {
            return false;
        }
        var step = localized.step || 0;
        var total = localized.total || 14;
        var percent = Math.min(100, Math.max(0, localized.percent || 0));
        if (badgeEl && localized.badge) {
            badgeEl.textContent = localized.badge;
        }
        if (labelEl && localized.label) {
            labelEl.textContent = localized.label;
        }
        if (pillEl) {
            pillEl.textContent = step + ' / ' + total;
        }
        var mascotEl = root.querySelector('.processing-status-mascot');
        if (mascotEl) {
            var mascotState = resolveMascotState(localized);
            mascotEl.className = 'processing-status-mascot processing-status-mascot--' + mascotState;
        }
        if (fillEl) {
            fillEl.style.width = percent + '%';
        }
        if (trackEl) {
            trackEl.setAttribute('aria-valuenow', String(percent));
            if (localized.progressAria) {
                trackEl.setAttribute('aria-label', localized.progressAria);
            }
        }
        var card = root.querySelector('.processing-status-card');
        if (card && !shouldShowTechnicalMeta(targetEl)) {
            mountProcessingMeta(card, localized.slow_hint || '', localized.agent_display || '');
        }
        return true;
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
        var displayLocale = localized.locale || getLocale(getProcessingDisplayLang(localized));

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

        var showTechnical = shouldShowTechnicalMeta(targetEl);
        var meta = {
            showTechnical: showTechnical,
            locale: displayLocale,
            mascotState: resolveMascotState(localized),
            agent_display: localized.agent_display || '',
            slow_hint: localized.slow_hint || '',
            agent_name: showTechnical ? localized.agent_name : '',
            agent_role: showTechnical ? localized.agent_role : '',
            agent_description: showTechnical ? localized.agent_description : '',
            flow_description: showTechnical ? localized.flow_description : '',
            flow_hint: showTechnical ? localized.flow_hint : ''
        };
        if (!wrapper.querySelector('.processing-status-card')) {
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
        var card = wrapper.querySelector('.processing-status-card');
        if (!showTechnical) {
            var misplacedAgent = wrapper.querySelector('.processing-status-mascot-row .processing-status-agent-user');
            if (misplacedAgent) {
                misplacedAgent.remove();
            }
            var misplacedSlow = wrapper.querySelector('.processing-status-mascot-row .processing-status-slow-hint');
            if (misplacedSlow) {
                misplacedSlow.remove();
            }
            mountProcessingMeta(card, localized.slow_hint || '', localized.agent_display || '');
        } else {
            var metaSection = card && card.querySelector('.processing-status-meta');
            if (metaSection) {
                metaSection.remove();
            }
        }
        if (showTechnical && detailLabel) {
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
        if (!showTechnical) {
            if (agentEl) agentEl.remove();
            if (flowEl) flowEl.remove();
            var hintEl = wrapper.querySelector('.processing-status-flow-hint');
            var agentDescEl = wrapper.querySelector('.processing-status-agent-desc');
            if (hintEl) hintEl.remove();
            if (agentDescEl) agentDescEl.remove();
        } else {
            if (agentEl && meta.agent_name) {
                agentEl.textContent = '【' + meta.agent_name + '】' + (meta.agent_role ? ' ' + meta.agent_role : '');
            }
            if (flowEl && meta.flow_description) {
                var flowLocale = meta.locale || getLocale(getCurrentLang(null));
                flowEl.textContent = (flowLocale.flowPrefix || 'フロー: ') + meta.flow_description;
            }
        }
        if (pillEl) pillEl.textContent = step + ' / ' + total;
        var mascotEl = wrapper.querySelector('.processing-status-mascot');
        if (mascotEl && meta.mascotState) {
            mascotEl.className = 'processing-status-mascot processing-status-mascot--' + meta.mascotState;
        }
        if (fillEl) fillEl.style.width = percent + '%';
        if (trackEl) {
            trackEl.setAttribute('aria-valuenow', String(percent));
            trackEl.setAttribute('aria-label', progressAria);
        }
        lastRenderedKey = key;
        patchProcessingStatusDom(targetEl, localized);
    }

    function shouldStopPollingForInactive() {
        if (pollRoot.keepAliveWhileLocked) {
            return false;
        }
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
        if (!pollRoot.timer || pollRoot.ssePaused) {
            return;
        }
        var gen = pollRoot.generation;
        var url = pollRoot.statusUrl || '/api/processing-status';
        if (pollRoot.useAdminSession && pollRoot.sessionId) {
            url += (url.indexOf('?') >= 0 ? '&' : '?') + 'session_id=' + encodeURIComponent(pollRoot.sessionId);
        }
        fetch(url, { credentials: 'include', headers: { 'Cache-Control': 'no-cache' } })
            .then(function (r) {
                if (r.status === 429 || r.status === 503) {
                    pollRoot.pollBackoffMs = Math.min(20000, Math.max(pollRoot.pollIntervalMs, pollRoot.pollBackoffMs * 2));
                    rescheduleProcessingPollInterval();
                    return null;
                }
                if (!r.ok) {
                    return null;
                }
                pollRoot.pollBackoffMs = pollRoot.pollIntervalMs;
                return r.json();
            })
            .then(function (data) {
                if (!pollRoot.timer || gen !== pollRoot.generation) {
                    return;
                }
                var raw = data || { active: false };
                if (raw.active) {
                    pollRoot.hasSeenActive = true;
                    pollRoot.inactiveStreak = 0;
                } else {
                    pollRoot.inactiveStreak += 1;
                }
                if (typeof pollRoot.onUpdate === 'function') {
                    pollRoot.onUpdate(raw);
                }
                if (!raw.active && shouldStopPollingForInactive()) {
                    finishPollingInactive();
                }
            })
            .catch(function () { /* ignore */ });
    }

    function rescheduleProcessingPollInterval() {
        if (!pollRoot.timer) {
            return;
        }
        clearInterval(pollRoot.timer);
        pollRoot.timer = setInterval(function () {
            pollRoot._pollCount = (pollRoot._pollCount || 0) + 1;
            if (pollRoot._pollCount >= (pollRoot._maxPolls || 72)) {
                finishPollingInactive();
                return;
            }
            pollOnce();
        }, pollRoot.pollBackoffMs);
    }

    function startProcessingPoll(options) {
        options = options || {};
        stopProcessingPoll();
        pollRoot.generation += 1;
        pollRoot.sessionId = options.sessionId || null;
        pollRoot.useAdminSession = Boolean(options.adminSession);
        pollRoot.onUpdate = options.onUpdate || null;
        pollRoot.onInactive = options.onInactive || null;
        pollRoot.statusUrl = options.statusUrl || '/api/processing-status';
        pollRoot.keepAliveWhileLocked = Boolean(options.keepAliveWhileLocked);
        pollRoot.hasSeenActive = false;
        pollRoot.inactiveStreak = 0;
        pollRoot.pollIntervalMs = options.interval || 2500;
        pollRoot.pollBackoffMs = pollRoot.pollIntervalMs;
        pollRoot.ssePaused = Boolean(options.ssePaused);
        var maxPolls = options.maxPolls || 72;
        pollRoot._maxPolls = maxPolls;
        pollRoot._pollCount = 0;
        lastRenderedKey = '';
        lastApiLanguage = null;
        pollOnce();
        pollRoot._pollCount = 1;
        pollRoot.timer = setInterval(function () {
            pollRoot._pollCount += 1;
            if (pollRoot._pollCount >= maxPolls) {
                finishPollingInactive();
                return;
            }
            pollOnce();
        }, pollRoot.pollBackoffMs);
    }

    function setProcessingPollSsePaused(paused) {
        pollRoot.ssePaused = Boolean(paused);
    }

    function isProcessingPollActive() {
        return !!pollRoot.timer;
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
        pollRoot.statusUrl = '/api/processing-status';
        pollRoot.keepAliveWhileLocked = false;
        pollRoot.hasSeenActive = false;
        pollRoot.inactiveStreak = 0;
        pollRoot.pollBackoffMs = pollRoot.pollIntervalMs || 2500;
        pollRoot.ssePaused = false;
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
        isProcessingPollActive: isProcessingPollActive,
        setProcessingPollSsePaused: setProcessingPollSsePaused,
        renderProcessingStatus: renderProcessingStatus,
        patchProcessingStatusDom: patchProcessingStatusDom,
        getTypingIndicatorHtml: getTypingIndicatorHtml,
        localizeStatusData: localizeStatusData,
        getCurrentLang: getCurrentLang,
        getProcessingDisplayLang: getProcessingDisplayLang,
        getUiLanguage: getUiLanguage,
        getProcessingLanguage: getProcessingLanguage,
        setProcessingLanguage: setProcessingLanguage,
        detectInputLanguage: detectInputLanguage
    };
})(typeof window !== 'undefined' ? window : this);
