    // 多言語翻訳データ
    const translations = {
        ja: {
            title: "💊 チャット型医薬品相談ツール(β版)",
            titleShort: "医薬品相談ツール",
            description: "症状に合う市販薬をご案内します。",
            userInfoBtn: "👤 ユーザー情報登録",
            clearBtn: "🗑️ 履歴クリア",
            newSessionBtn: "🔄 新セッション",
            adminRequestBtn: "👨‍⚕️ 薬剤師要請",
            placeholder: "症状を入力してください...",
            send: "送信",
            processing: "AI処理中です",
            recommendedMedicines: "推奨医薬品",
            usageNotes: "使用上の注意",
            doctorConsultation: "医師にご相談ください",
            feedbackPositive: "👍 適切",
            feedbackNegative: "👎 不適切",
            reportBug: "🐛 不具合報告",
            age: "年齢",
            gender: "性別",
            male: "男性",
            female: "女性",
            pregnant: "妊娠中",
            breastfeeding: "授乳中",
            allergies: "アレルギー",
            currentMedications: "服用中の薬",
            medicalHistory: "既往症",
            otherInfo: "その他情報",
            save: "保存",
            cancel: "キャンセル",
            
            // 初期メッセージ
            initialGreeting: "こんにちは！どのような症状でお困りでしょうか？",
            initialExamples: "例：「頭痛がする」「喉が痛い」「熱がある」など",
            
            // システムメッセージ
            chatEnded: "チャットを終了しました。不明点がございましたら、お気軽にお近くの登録販売者にご相談ください。",
            aiPaused: "申し訳ございません。現在、AI自動応答が一時停止されています。担当者が確認次第、回答いたします。",
            
            // エラーメッセージ
            systemError: "申し訳ございません。システムエラーが発生しました",
            processingError: "処理中にエラーが発生しました",
            networkError: "ネットワークエラーが発生しました",
            loadError: "メッセージ読み込みエラー",
            
            // 確認メッセージ
            confirmClearChat: "チャット履歴をクリアしますか？",
            confirmNewSession: "新しいセッションを開始しますか？現在の会話は保存されません。",
            
            // 評価・フィードバック
            feedbackQuestion: "この回答はいかがでしたか？",
            feedbackQuestionRecommendation: "この推奨結果はいかがでしたか？",
            feedbackQuestionNotice: "この重要な注意事項はいかがでしたか？",
            feedbackThankYou: "フィードバックありがとうございます！",
            
            // イースターエッグ
            easterEggThanks: "🎉 ありがとうございます！",
            easterEggThanksMessage: "お役に立てて嬉しいです！",
            easterEggThanksResponse: "他にご質問がございましたら、お気軽にお聞かせください。",
            easterEggSnakeGame: "🐍 スネークゲーム",
            easterEggSnakeScore: "スコア: ",
            easterEggSnakeControls: "操作方法: 方向キーまたは画面のボタン",
            easterEggSnakeGameOver: "ゲームオーバー！",
            easterEggEmojiGame: "🎯 絵文字キャッチゲーム",
            easterEggEmojiScore: "スコア: ",
            easterEggEmojiControls: "操作方法: タッチまたはクリックで絵文字をキャッチ！",
            
            // 不具合報告
            bugReportPrompt: "不具合の内容を詳しく説明してください",
            bugReportSubmitted: "不具合報告を送信しました",
            bugReportFailed: "不具合報告の送信に失敗しました",
            
            // 危機対応メッセージ
            crisisSupportTitle: "あなたの気持ちを大切に思っています",
            crisisSupportMessage: "今、とてもつらい状況かもしれません。一人で抱え込まず、信頼できる相談先があります。",
            crisisEmergency: "緊急の場合は、すぐに119番（救急）または110番（警察）に連絡してください。",
            
            // モーダル関連
            infoButton: "アプリ情報",
            appInfo: "アプリ概要・運営者情報",
            appInfoDesc: "アプリの機能と特徴について",
            disclaimer: "免責事項・利用規約",
            disclaimerDesc: "利用規約と免責事項について",
            privacy: "プライバシーポリシー",
            privacyDesc: "個人情報の取り扱いについて",
            usage: "使い方・FAQ",
            usageDesc: "アプリの使い方と安全に利用するための注意",
            consultation: "医薬品相談先",
            consultationDesc: "公的機関の相談窓口情報",
            siteAboutTitle: "詳しい説明",
            siteAboutDesc: "ウェブ上の説明サイト（概要・規約・プライバシー等）へ移動します",
            settingsTitle: "設定",
            settingsDesc: "文字サイズなどの表示設定",
            faq: "よくある質問（FAQ）",
            faqDesc: "よくある質問と回答",
            back: "← 戻る",
            close: "×",
            skipOnboarding: "スキップして始める",
            onboardingLastUpdatedLabel: "最終更新日",
            onboardingLastUpdatedIso: "2026-05-20",
            onboardingLastUpdated: "2026年5月20日",
            onboarding: [
                {
                    production: {
                        title: "チャット型医薬品相談ツール(β版)",
                        visual: "🤝💊",
                        visualAlt: "薬剤師がスマートフォン越しに相談を受けるイメージ",
                        subtitle: "β版（試験運用）— より安全で分かりやすい情報提供に向けて改善を続けています",
                        body: [
                            "症状を入力すると、市販薬の候補と受診の目安をAIが案内します。医療診断の代わりではありません。"
                        ],
                        details: [
                            {
                                summary: "現在開発中の主な内容",
                                itemsChecklist: true,
                                items: [
                                    { text: "Flask→Fast APIへの大規模移行", defaultChecked: true },
                                    { text: "GPT-5系モデル（トリアージ・NLU・説明等）", defaultChecked: true },
                                    { text: "マルチエージェント振り分け（ChatOrchestrator）", defaultChecked: true },
                                    "潜在空間によるスコアリングの大規模改修",
                                    "UI・導線の最適化",
                                    "カルーセル型UIの導入",
                                    "LINE連携（Messaging API）",
                                    "画像の導入",
                                    "セキュリティ向上",
                                    "音声入力の向上",
                                    "体調推定の実装（計画中）",
                                    "パーソナライズ機能の実装（計画中）"
                                ]
                            }
                        ],
                        links: [
                            {
                                text: "🔗 開発環境を別タブで開く",
                                url: "https://medicine-recommend-dev-340042923793.asia-northeast1.run.app/",
                                ariaLabel: "開発環境を新しいタブで開く"
                            },
                            {
                                text: "📝 ご意見・不具合の報告",
                                url: "https://forms.gle/UB8kZHd4VHenmRUN6",
                                ariaLabel: "Googleフォームでご意見・不具合を送る"
                            }
                        ],
                        buttonText: "次へ",
                        buttonAria: "次のステップへ進む"
                    },
                    development: {
                        title: "🛠️ 開発環境(dev)へようこそ",
                        visual: "🚧💊",
                        visualAlt: "開発中の薬剤師相談ツールのアイコン",
                        subtitle: '<span class="onboarding-env-badge">🛠️ ここは開発環境(dev)です</span>',
                        body: [
                            'このページは<span class="onboarding-env-here">テスター・開発者向けの開発環境(dev)</span>です。本番とは別サーバーで最新機能を試せますが、表示崩れ・エラー・データリセットがある場合があります。',
                            "一般の方は本番環境（安定版）をご利用ください。"
                        ],
                        details: [
                            {
                                summary: "現在開発中の主な内容",
                                itemsChecklist: true,
                                items: [
                                    { text: "Flask→Fast APIへの大規模移行", defaultChecked: true },
                                    { text: "GPT-5系モデル（トリアージ・NLU・説明等）", defaultChecked: true },
                                    { text: "マルチエージェント振り分け（ChatOrchestrator）", defaultChecked: true },
                                    "潜在空間によるスコアリングの大規模改修",
                                    "UI・導線の最適化",
                                    "カルーセル型UIの導入",
                                    "LINE連携（Messaging API）",
                                    "画像の導入",
                                    "セキュリティ向上",
                                    "音声入力の向上",
                                    "体調推定の実装（計画中）",
                                    "パーソナライズ機能の実装（計画中）"
                                ]
                            }
                        ],
                        links: [
                            {
                                text: "🌐 本番環境(安定版)を開く",
                                url: "https://medicine.yutok.dev/",
                                ariaLabel: "本番環境(安定版)を新しいタブで開く"
                            },
                            {
                                text: "📝 クレーム・ご意見",
                                url: "https://forms.gle/UB8kZHd4VHenmRUN6",
                                ariaLabel: "Googleフォームでクレーム・ご意見を送る"
                            }
                        ],
                        buttonText: "次へ",
                        buttonAria: "次のステップへ進む"
                    }
                },
                {
                    title: "🩺 ステップ1：今の症状を伝える",
                    visual: "💬🎤",
                    visualAlt: "症状入力のUIを表すアイコン",
                    body: [
                        "「頭が痛い」「咳が止まらない」など、感じている症状を自由に入力してください。",
                        "テキストと音声入力に対応し、左上のボタンから英語・中国語・韓国語へ切り替えられます。",
                        "※AIの返信は、送信した文章の言語を自動検出し、日本語以外（英語・中国語・韓国語など）と判定された場合に自動翻訳されます。左上の切替は主に画面の文言表示です。"
                    ],
                    buttonText: "次へ",
                    buttonAria: "ステップ2へ進む"
                },
                {
                    title: "👤 ステップ2：あなたに合わせた回答を",
                    visual: "🧬✨",
                    visualAlt: "パーソナライズされた回答を表すアイコン",
                    body: [
                        "「ユーザー情報登録」でアレルギーや服薬歴を登録すると、AIがあなたの体質や状況を考慮した回答を行います。",
                        "状況確認のために、追加で質問をさせていただくことがあります。"
                    ],
                    buttonText: "次へ",
                    buttonAria: "ステップ3へ進む"
                },
                {
                    title: "👩‍⚕️ ステップ3：専門家とつながる安心を",
                    visual: "📞👨‍⚕️",
                    visualAlt: "薬剤師とつながることを表すアイコン",
                    body: [
                        "AIの回答に迷ったら「薬剤師要請」から専門家に直接相談できます。",
                        "右上の ℹ️ ボタンから使い方ガイドやFAQをいつでも確認できます。"
                    ],
                    buttonText: "次へ",
                    buttonAria: "次のステップへ進む"
                },
                {
                    title: "🎮 イースターエッグ機能について",
                    visual: "🎉✨",
                    visualAlt: "イースターエッグ機能を表すアイコン",
                    body: [
                        "本アプリには、特定のキーワードやメッセージで発動する楽しい隠し機能「イースターエッグ」が実装されています。",
                        "感謝のメッセージを送るとパーティクル効果が表示されたり、特定のキーワードで画面が変形したり、絵文字のみを送信すると特別な効果が表示されたりします。",
                        "ぜひ試してみてください！"
                    ],
                    bullets: [
                        "感謝メッセージ（「ありがとう」など）でパーティクル効果",
                        "画面変形（「回転」「揺れる」などのキーワード）",
                        "絵文字のみの送信",
                        "季節イベント対応（新年、クリスマスなど）"
                    ],
                    buttonText: "次へ",
                    buttonAria: "次のステップへ進む"
                },
                {
                    title: "📚 本アプリケーションの資料",
                    visual: "📄📊",
                    visualAlt: "資料を表すアイコン",
                    body: [
                        "本アプリケーションに関する詳細資料をご用意しています。",
                        "以下のリンクから、技術的資料、パワーポイント、解説動画、プロトタイプを確認できます。"
                    ],
                    links: [
                        {
                            text: "📄 技術的資料",
                            url: "https://drive.google.com/file/d/19CTRYV4moDikaLKXgC2Z_70wRXeCwKbx/view?usp=sharing",
                            ariaLabel: "技術的資料をGoogle Driveで開く"
                        },
                        {
                            text: "📊 パワーポイント",
                            url: "https://drive.google.com/file/d/1FhdB7aUWlhYHRdhMLjDrNU0bvGyjdZ1F/view?usp=sharing",
                            ariaLabel: "パワーポイントをGoogle Driveで開く"
                        },
                        {
                            text: "🎥 解説動画",
                            url: "https://youtu.be/O1ptrH1q7S4",
                            ariaLabel: "解説動画をYouTubeで開く"
                        },
                        {
                            text: "🎨 プロトタイプ (Marvel)",
                            url: "https://marvelapp.com/prototype/350fehf6",
                            ariaLabel: "Marvelプロトタイプを開く"
                        }
                    ],
                    isBetaOnly: true,
                    hidden: true,
                    buttonText: "次へ",
                    buttonAria: "最終ステップへ進む"
                },
                {
                    title: "⚠️ ご利用前の大切なお知らせ",
                    visual: "⚠️",
                    visualAlt: "注意アイコン",
                    body: [
                        "利用を開始する前に、以下の注意事項をご確認ください。"
                    ],
                    bullets: [
                        "本ツールは医療行為（診断）を行うものではありません。",
                        "市販薬の選択をサポートする情報提供ツールです。",
                        "重い症状や判断に迷う場合は、必ず医療機関を受診してください。"
                    ],
                    details: [
                        {
                            summary: "📄 免責事項・利用規約を表示",
                            policyKey: 'disclaimer'
                        },
                        {
                            summary: "🔒 プライバシーポリシーを表示",
                            policyKey: 'privacy'
                        }
                    ],
                    checkboxLabel: "上記に同意する",
                    startButtonText: "上記に同意して利用を開始",
                    startButtonAria: "同意してチャットを開始する"
                }
            ]
        },
        en: {
            title: "💊 Chat Pharmaceutical Consultation Tool",
            titleShort: "OTC Consultation",
            description: "OTC medicine guidance for your symptoms.",
            userInfoBtn: "👤 User Info",
            clearBtn: "🗑️ Clear History",
            newSessionBtn: "🔄 New Session",
            adminRequestBtn: "👨‍⚕️ Request Pharmacist",
            placeholder: "Please enter your symptoms...",
            send: "Send",
            processing: "AI is processing...",
            recommendedMedicines: "Recommended Medicines",
            usageNotes: "Usage Notes",
            doctorConsultation: "Please consult a doctor",
            feedbackPositive: "👍 Appropriate",
            feedbackNegative: "👎 Inappropriate",
            reportBug: "🐛 Report Bug",
            age: "Age",
            gender: "Gender",
            male: "Male",
            female: "Female",
            pregnant: "Pregnant",
            breastfeeding: "Breastfeeding",
            allergies: "Allergies",
            currentMedications: "Current Medications",
            medicalHistory: "Medical History",
            otherInfo: "Other Information",
            save: "Save",
            cancel: "Cancel",
            
            // 初期メッセージ
            initialGreeting: "Hello! What symptoms are you experiencing?",
            initialExamples: "Examples: \"I have a headache\", \"My throat hurts\", \"I have a fever\"",
            
            // システムメッセージ
            chatEnded: "Chat ended. If you have any questions, please feel free to consult your local pharmacist.",
            aiPaused: "We apologize. AI auto-response is currently paused. We will respond once confirmed by staff.",
            
            // エラーメッセージ
            systemError: "We apologize. A system error has occurred",
            processingError: "An error occurred during processing",
            networkError: "A network error occurred",
            loadError: "Error loading messages",
            
            // 確認メッセージ
            confirmClearChat: "Clear chat history?",
            confirmNewSession: "Start a new session? Current conversation will not be saved.",
            
            // 評価・フィードバック
            feedbackQuestion: "How was this response?",
            feedbackQuestionRecommendation: "How was this recommendation?",
            feedbackQuestionNotice: "How was this important notice?",
            feedbackThankYou: "Thank you for your feedback!",
            
            // 不具合報告
            bugReportPrompt: "Please describe the issue in detail",
            bugReportSubmitted: "Bug report submitted",
            bugReportFailed: "Failed to submit bug report",
            
            // 危機対応メッセージ
            crisisSupportTitle: "Your feelings matter",
            crisisSupportMessage: "Professional support is available. Please contact a crisis counselor.",
            crisisEmergency: "In emergency, call 119 (ambulance) or 110 (police) immediately.",
            
            // モーダル関連
            infoButton: "App Info",
            appInfo: "App Overview",
            appInfoDesc: "About app features and characteristics",
            disclaimer: "Disclaimer & Terms",
            disclaimerDesc: "About terms of use and disclaimers",
            privacy: "Privacy Policy",
            privacyDesc: "About personal information handling",
            usage: "How to Use",
            usageDesc: "App usage and safety precautions",
            consultation: "Consultation Info",
            consultationDesc: "Public institution consultation information",
            siteAboutTitle: "Detailed info (website)",
            siteAboutDesc: "Open the web-based about pages (overview, terms, privacy, etc.)",
            settingsTitle: "Settings",
            settingsDesc: "Display options such as text size",
            faq: "FAQ",
            faqDesc: "Frequently asked questions and answers",
            back: "← Back",
            close: "×",
            skipOnboarding: "Skip onboarding",
            onboardingLastUpdatedLabel: "Last updated",
            onboardingLastUpdatedIso: "2026-05-20",
            onboardingLastUpdated: "May 20, 2026",
            onboarding: [
                {
                    production: {
                        title: "Welcome to the Chat-based OTC Assistant (Beta)",
                        visual: "🤝💊",
                        visualAlt: "Illustration of a pharmacist supporting via smartphone",
                        subtitle: "Beta release — we keep improving clarity and safety.",
                        body: [
                            "Describe your symptoms; the AI suggests OTC options and when to seek care. It is not a medical diagnosis."
                        ],
                        details: [
                            {
                                summary: "What we are currently working on",
                                itemsChecklist: true,
                                items: [
                                    { text: "Large-scale migration from Flask to FastAPI", defaultChecked: true },
                                    { text: "GPT-5 class models (triage, NLU, explanations, etc.)", defaultChecked: true },
                                    { text: "Multi-agent routing (ChatOrchestrator)", defaultChecked: true },
                                    "Major scoring revamp using latent space",
                                    "UI and user-flow optimization",
                                    "Carousel-style UI",
                                    "LINE integration (Messaging API)",
                                    "Image support",
                                    "Security improvements",
                                    "Better voice input",
                                    "Health state estimation (planned)",
                                    "Personalization features (planned)"
                                ]
                            }
                        ],
                        links: [
                            {
                                text: "🔗 Open the development environment",
                                url: "https://medicine-recommend-dev-340042923793.asia-northeast1.run.app/",
                                ariaLabel: "Open the development environment in a new tab"
                            },
                            {
                                text: "📝 Feedback or bug reports",
                                url: "https://forms.gle/UB8kZHd4VHenmRUN6",
                                ariaLabel: "Submit feedback or report issues via Google Forms"
                            }
                        ],
                        buttonText: "Next",
                        buttonAria: "Go to the next step"
                    },
                    development: {
                        title: "🛠️ Welcome to the Dev environment",
                        visual: "🚧💊",
                        visualAlt: "Icon representing the OTC assistant under development",
                        subtitle: '<span class="onboarding-env-badge">🛠️ This is the DEV environment</span>',
                        body: [
                            'This is the <span class="onboarding-env-here">dev environment for testers and developers</span> on a separate server from production. Try the latest here; layouts, errors, or data resets may occur.',
                            "Regular users should use the production (stable) environment."
                        ],
                        details: [
                            {
                                summary: "What we are currently working on",
                                itemsChecklist: true,
                                items: [
                                    { text: "Large-scale migration from Flask to FastAPI", defaultChecked: true },
                                    { text: "GPT-5 class models (triage, NLU, explanations, etc.)", defaultChecked: true },
                                    { text: "Multi-agent routing (ChatOrchestrator)", defaultChecked: true },
                                    "Major scoring revamp using latent space",
                                    "UI and user-flow optimization",
                                    "Carousel-style UI",
                                    "LINE integration (Messaging API)",
                                    "Image support",
                                    "Security improvements",
                                    "Better voice input",
                                    "Health state estimation (planned)",
                                    "Personalization features (planned)"
                                ]
                            }
                        ],
                        links: [
                            {
                                text: "🌐 Open production (stable)",
                                url: "https://medicine.yutok.dev/",
                                ariaLabel: "Open the production (stable) environment in a new tab"
                            },
                            {
                                text: "📝 Feedback & claims",
                                url: "https://forms.gle/UB8kZHd4VHenmRUN6",
                                ariaLabel: "Submit feedback or claims via Google Forms"
                            }
                        ],
                        buttonText: "Next",
                        buttonAria: "Go to the next step"
                    }
                },
                {
                    title: "Step 1: Describe your symptoms",
                    visual: "💬🎤",
                    visualAlt: "Icons representing symptom input",
                    body: [
                        "Tell us anything such as “I have a headache” or “I can't stop coughing.”",
                        "Both text and voice input are supported. Use the button in the upper left to switch between Japanese, English, Chinese, and Korean.",
                        "* AI replies are translated when your message is detected as non-Japanese (e.g. English, Chinese, or Korean). The upper-left control mainly changes on-screen UI language."
                    ],
                    buttonText: "Next",
                    buttonAria: "Go to step 2"
                },
                {
                    title: "Step 2: Get answers tailored to you",
                    visual: "🧬✨",
                    visualAlt: "Icons representing personalized answers",
                    body: [
                        "Register allergies and current medications via “User Info” so the AI can personalize advice.",
                        "The assistant may ask follow-up questions to make sure the suggestions fit your situation."
                    ],
                    buttonText: "Next",
                    buttonAria: "Go to step 3"
                },
                {
                    title: "Step 3: Reach a pharmacist when needed",
                    visual: "📞👨‍⚕️",
                    visualAlt: "Icons showing a call with a pharmacist",
                    body: [
                        "If you are unsure about the AI's reply, tap “Request Pharmacist” to speak with a professional.",
                        "Use the ℹ️ button in the top right to open guides and FAQs whenever you like."
                    ],
                    buttonText: "Next",
                    buttonAria: "Go to the next step"
                },
                {
                    title: "🎮 About Easter Egg Features",
                    visual: "🎉✨",
                    visualAlt: "Icons representing Easter egg features",
                    body: [
                        "This app includes fun hidden features called \"Easter Eggs\" that activate with specific keywords or messages.",
                        "Sending a thank you message displays particle effects, specific keywords transform the screen, and sending only emojis displays special effects.",
                        "Please try them out!"
                    ],
                    bullets: [
                        "Particle effects with thank you messages (\"thank you\", etc.)",
                        "Screen transformations (keywords like \"rotate\", \"shake\", etc.)",
                        "Sending only emojis",
                        "Seasonal event support (New Year, Christmas, etc.)"
                    ],
                    buttonText: "Next",
                    buttonAria: "Go to the next step"
                },
                {
                    title: "📚 Application Documentation",
                    visual: "📄📊",
                    visualAlt: "Icons representing documentation",
                    body: [
                        "Detailed documentation about this application is available.",
                        "You can access technical documents, PowerPoint presentations, explanatory video, and prototype from the links below."
                    ],
                    links: [
                        {
                            text: "📄 Technical Documents",
                            url: "https://drive.google.com/file/d/19CTRYV4moDikaLKXgC2Z_70wRXeCwKbx/view?usp=sharing",
                            ariaLabel: "Open technical documents on Google Drive"
                        },
                        {
                            text: "📊 PowerPoint",
                            url: "https://drive.google.com/file/d/1FhdB7aUWlhYHRdhMLjDrNU0bvGyjdZ1F/view?usp=sharing",
                            ariaLabel: "Open PowerPoint on Google Drive"
                        },
                        {
                            text: "🎥 Explanatory Video",
                            url: "https://youtu.be/O1ptrH1q7S4",
                            ariaLabel: "Open explanatory video on YouTube"
                        },
                        {
                            text: "🎨 Prototype (Marvel)",
                            url: "https://marvelapp.com/prototype/350fehf6",
                            ariaLabel: "Open Marvel prototype"
                        }
                    ],
                    isBetaOnly: true,
                    hidden: true,
                    buttonText: "Next",
                    buttonAria: "Go to the final step"
                },
                {
                    title: "Important information before you start",
                    visual: "⚠️",
                    visualAlt: "Warning icon",
                    body: [
                        "Before we start, please review the notices below."
                    ],
                    bullets: [
                        "This tool does not provide medical diagnosis.",
                        "It offers information to support your OTC medicine selection.",
                        "If symptoms are severe or you are unsure, please consult a medical institution."
                    ],
                    details: [
                        {
                            summary: "📄 View Disclaimer & Terms",
                            policyKey: 'disclaimer'
                        },
                        {
                            summary: "🔒 View Privacy Policy",
                            policyKey: 'privacy'
                        }
                    ],
                    checkboxLabel: "I agree to the above",
                    startButtonText: "Agree and start using",
                    startButtonAria: "Agree and start the consultation"
                }
            ]
        },
        ko: {
            title: "💊 채팅형 의약품 상담 도구",
            titleShort: "의약품 상담",
            description: "증상에 맞는 일반의약품을 안내합니다.",
            userInfoBtn: "👤 사용자 정보",
            clearBtn: "🗑️ 기록 삭제",
            newSessionBtn: "🔄 새 세션",
            adminRequestBtn: "👨‍⚕️ 약사 요청",
            placeholder: "증상을 입력해주세요...",
            send: "전송",
            processing: "AI 처리 중입니다",
            recommendedMedicines: "추천 의약품",
            usageNotes: "사용상 주의사항",
            doctorConsultation: "의사와 상담하세요",
            feedbackPositive: "👍 적절함",
            feedbackNegative: "👎 부적절함",
            reportBug: "🐛 버그 신고",
            age: "나이",
            gender: "성별",
            male: "남성",
            female: "여성",
            pregnant: "임신 중",
            breastfeeding: "수유 중",
            allergies: "알레르기",
            currentMedications: "복용 중인 약",
            medicalHistory: "병력",
            otherInfo: "기타 정보",
            save: "저장",
            cancel: "취소",
            
            // 初期メッセージ
            initialGreeting: "안녕하세요! 어떤 증상으로 고민이 있으신가요?",
            initialExamples: "예: \"두통이 있어요\", \"목이 아파요\", \"열이 나요\"",
            
            // システムメッセージ
            chatEnded: "채팅이 종료되었습니다. 궁금하신 점이 있으시면 가까운 약사에게 상담하세요.",
            aiPaused: "죄송합니다. 현재 AI 자동 응답이 일시 중지되었습니다. 담당자 확인 후 답변드리겠습니다.",
            
            // エラーメッセージ
            systemError: "죄송합니다. 시스템 오류가 발생했습니다",
            processingError: "처리 중 오류가 발생했습니다",
            networkError: "네트워크 오류가 발생했습니다",
            loadError: "메시지 로드 오류",
            
            // 確認メッセージ
            confirmClearChat: "채팅 기록을 지우시겠습니까?",
            confirmNewSession: "새 세션을 시작하시겠습니까? 현재 대화는 저장되지 않습니다.",
            
            // 評価・フィードバック
            feedbackQuestion: "이 답변은 어떠셨나요?",
            feedbackQuestionRecommendation: "이 추천 결과는 어떠셨나요?",
            feedbackQuestionNotice: "이 중요한 주의사항은 어떠셨나요?",
            feedbackThankYou: "피드백 감사합니다!",
            
            // 不具合報告
            bugReportPrompt: "문제를 자세히 설명해주세요",
            bugReportSubmitted: "버그 신고가 제출되었습니다",
            bugReportFailed: "버그 신고 제출에 실패했습니다",
            
            // 危機対応メッセージ
            crisisSupportTitle: "당신의 마음을 소중히 생각합니다",
            crisisSupportMessage: "전문 상담사가 도움을 드릴 수 있습니다. 위기 상담원에게 연락하세요.",
            crisisEmergency: "응급상황 시 즉시 119(구급차) 또는 110(경찰)에 연락하세요.",
            
            // モーダル関連
            infoButton: "앱 정보",
            appInfo: "앱 개요",
            appInfoDesc: "앱 기능 및 특징에 대해",
            disclaimer: "약관 및 면책 조항",
            disclaimerDesc: "이용약관 및 면책조항에 대해",
            privacy: "개인정보 취급방침",
            privacyDesc: "개인정보 처리에 대해",
            usage: "사용 방법",
            usageDesc: "앱 사용 방법 및 안전하게 이용하기 위한 주의사항",
            consultation: "의약품 상담 정보",
            consultationDesc: "공공기관 상담창구 정보",
            siteAboutTitle: "자세한 설명",
            siteAboutDesc: "웹 설명 페이지(개요·약관·개인정보 등)로 이동합니다",
            settingsTitle: "설정",
            settingsDesc: "글자 크기 등 표시 설정",
            faq: "자주 묻는 질문 (FAQ)",
            faqDesc: "자주 묻는 질문과 답변",
            back: "← 뒤로",
            close: "×",
            skipOnboarding: "넘기고 시작하기",
            onboardingLastUpdatedLabel: "최종 업데이트",
            onboardingLastUpdatedIso: "2026-05-20",
            onboardingLastUpdated: "2026년 5월 20일",
            
            // イースターエッグ
            easterEggThanks: "🎉 감사합니다!",
            easterEggThanksMessage: "도움이 되어 기쁩니다!",
            easterEggThanksResponse: "다른 질문이 있으시면 언제든지 물어보세요.",
            easterEggSnakeGame: "🐍 스네이크 게임",
            easterEggSnakeScore: "점수: ",
            easterEggSnakeControls: "조작: 방향키 또는 화면 버튼",
            easterEggSnakeGameOver: "게임 오버!",
            easterEggEmojiGame: "🎯 이모지 캐치 게임",
            easterEggEmojiScore: "점수: ",
            easterEggEmojiControls: "조작: 터치 또는 클릭하여 이모지를 잡으세요!",
            onboarding: [
                {
                    production: {
                        title: "채팅형 의약품 상담 도구(베타)에 오신 것을 환영합니다",
                        visual: "🤝💊",
                        visualAlt: "약사가 스마트폰으로 상담하는 모습을 나타내는 아이콘",
                        subtitle: "베타(시험 운영) — 더 안전하고 이해하기 쉬운 안내를 위해 계속 개선합니다",
                        body: [
                            "증상을 알려주면 AI가 일반의약품 후보와 진료 시기를 안내합니다. 의료 진단을 대신하지 않습니다."
                        ],
                        details: [
                            {
                                summary: "현재 개발 중인 주요 내용",
                                itemsChecklist: true,
                                items: [
                                    { text: "Flask에서 FastAPI로의 대규모 이전", defaultChecked: true },
                                    "잠재 공간 기반 스코어링 대규모 개편",
                                    { text: "GPT-5 계열 모델(트리아지·NLU·설명 등)", defaultChecked: true },
                                    { text: "멀티 에이전트 라우팅(ChatOrchestrator)", defaultChecked: true },
                                    "UI·사용자 동선 최적화",
                                    "캐러셀형 UI 도입",
                                    "LINE 연동(Messaging API)",
                                    "이미지 도입",
                                    "보안 강화",
                                    "음성 입력 개선",
                                    "컨디션 추정 구현(계획)",
                                    "개인화 기능 구현(계획)"
                                ]
                            }
                        ],
                        links: [
                            {
                                text: "🔗 개발 환경 새 탭에서 열기",
                                url: "https://medicine-recommend-dev-340042923793.asia-northeast1.run.app/",
                                ariaLabel: "개발 환경을 새 탭에서 엽니다"
                            },
                            {
                                text: "📝 의견·오류 신고",
                                url: "https://forms.gle/UB8kZHd4VHenmRUN6",
                                ariaLabel: "Google 양식으로 의견·오류 신고"
                            }
                        ],
                        buttonText: "다음",
                        buttonAria: "다음 단계로 이동"
                    },
                    development: {
                        title: "🛠️ 개발 환경(dev)에 오신 것을 환영합니다",
                        visual: "🚧💊",
                        visualAlt: "개발 중인 의약품 상담 도구 아이콘",
                        subtitle: '<span class="onboarding-env-badge">🛠️ 여기는 개발 환경(dev)입니다</span>',
                        body: [
                            '이 페이지는 <span class="onboarding-env-here">테스터·개발자용 개발 환경(dev)</span>입니다. 운영과 별도 서버에서 최신 기능을 시험할 수 있으나, 레이아웃 깨짐·오류·데이터 리셋이 있을 수 있습니다.',
                            "일반 이용자는 운영 환경(안정판)을 이용해 주세요."
                        ],
                        details: [
                            {
                                summary: "현재 개발 중인 주요 내용",
                                itemsChecklist: true,
                                items: [
                                    { text: "Flask에서 FastAPI로의 대규모 이전", defaultChecked: true },
                                    "잠재 공간 기반 스코어링 대규모 개편",
                                    { text: "GPT-5 계열 모델(트리아지·NLU·설명 등)", defaultChecked: true },
                                    { text: "멀티 에이전트 라우팅(ChatOrchestrator)", defaultChecked: true },
                                    "UI·사용자 동선 최적화",
                                    "캐러셀형 UI 도입",
                                    "LINE 연동(Messaging API)",
                                    "이미지 도입",
                                    "보안 강화",
                                    "음성 입력 개선",
                                    "컨디션 추정 구현(계획)",
                                    "개인화 기능 구현(계획)"
                                ]
                            }
                        ],
                        links: [
                            {
                                text: "🌐 운영 환경(안정판) 열기",
                                url: "https://medicine.yutok.dev/",
                                ariaLabel: "운영 환경(안정판)을 새 탭에서 엽니다"
                            },
                            {
                                text: "📝 클레임·의견",
                                url: "https://forms.gle/UB8kZHd4VHenmRUN6",
                                ariaLabel: "Google 양식으로 클레임·의견 제출"
                            }
                        ],
                        buttonText: "다음",
                        buttonAria: "다음 단계로 이동"
                    }
                },
                {
                    title: "🩺 스텝 1: 현재 증상을 알려주세요",
                    visual: "💬🎤",
                    visualAlt: "증상 입력을 상징하는 아이콘",
                    body: [
                        "“머리가 아파요”, “기침이 멈추지 않아요”와 같이 자유롭게 입력하세요.",
                        "텍스트와 음성 입력을 모두 지원하며, 왼쪽 상단 버튼으로 일본어·영어·중국어·한국어를 전환할 수 있습니다.",
                        "* AI 답변은 보낸 문장의 언어를 자동 감지하여 일본어가 아닐 때(영어·중국어·한국어 등) 자동 번역됩니다. 왼쪽 상단 전환은 주로 화면 문구 표시용입니다."
                    ],
                    buttonText: "다음",
                    buttonAria: "스텝 2로 이동"
                },
                {
                    title: "👤 스텝 2: 당신에게 맞춘 답변",
                    visual: "🧬✨",
                    visualAlt: "맞춤형 답변을 상징하는 아이콘",
                    body: [
                        "“사용자 정보 등록”에서 알레르기와 복용 중인 약을 입력하면 AI가 체질과 상황을 고려합니다.",
                        "필요하면 상황을 더 정확히 파악하기 위해 추가 질문을 드릴 수 있습니다."
                    ],
                    buttonText: "다음",
                    buttonAria: "스텝 3로 이동"
                },
                {
                    title: "👩‍⚕️ 스텝 3: 전문가와 연결되는 안심",
                    visual: "📞👨‍⚕️",
                    visualAlt: "약사와 연결되는 모습을 나타내는 아이콘",
                    body: [
                        "AI 답변이 불확실하다면 “약사 요청”을 통해 전문가와 직접 상담하세요.",
                        "오른쪽 상단의 ℹ️ 버튼에서 언제든지 이용 가이드와 FAQ를 확인할 수 있습니다."
                    ],
                    buttonText: "다음",
                    buttonAria: "다음 단계로 이동"
                },
                {
                    title: "🎮 이스터 에그 기능에 대해",
                    visual: "🎉✨",
                    visualAlt: "이스터 에그 기능을 나타내는 아이콘",
                    body: [
                        "이 앱에는 특정 키워드나 메시지로 발동하는 재미있는 숨겨진 기능 \"이스터 에그\"가 구현되어 있습니다.",
                        "감사 메시지를 보내면 파티클 효과가 표시되거나, 특정 키워드로 화면이 변형되거나, 이모지만 보내면 특별한 효과가 표시됩니다.",
                        "꼭 시도해 보세요!"
                    ],
                    bullets: [
                        "감사 메시지(\"감사합니다\" 등)로 파티클 효과",
                        "화면 변형(\"회전\", \"흔들림\" 등의 키워드)",
                        "이모지만 보내기",
                        "계절 이벤트 지원(새해, 크리스마스 등)"
                    ],
                    buttonText: "다음",
                    buttonAria: "다음 단계로 이동"
                },
                {
                    title: "📚 본 애플리케이션 자료",
                    visual: "📄📊",
                    visualAlt: "자료를 나타내는 아이콘",
                    body: [
                        "본 애플리케이션에 대한 상세 자료를 준비했습니다.",
                        "아래 링크에서 기술 문서, 파워포인트, 설명 동영상, 프로토타입을 확인할 수 있습니다."
                    ],
                    links: [
                        {
                            text: "📄 기술 문서",
                            url: "https://drive.google.com/file/d/19CTRYV4moDikaLKXgC2Z_70wRXeCwKbx/view?usp=sharing",
                            ariaLabel: "Google Drive에서 기술 문서 열기"
                        },
                        {
                            text: "📊 파워포인트",
                            url: "https://drive.google.com/file/d/1FhdB7aUWlhYHRdhMLjDrNU0bvGyjdZ1F/view?usp=sharing",
                            ariaLabel: "Google Drive에서 파워포인트 열기"
                        },
                        {
                            text: "🎥 설명 동영상",
                            url: "https://youtu.be/O1ptrH1q7S4",
                            ariaLabel: "YouTube에서 설명 동영상 열기"
                        },
                        {
                            text: "🎨 프로토타입 (Marvel)",
                            url: "https://marvelapp.com/prototype/350fehf6",
                            ariaLabel: "Marvel 프로토타입 열기"
                        }
                    ],
                    isBetaOnly: true,
                    hidden: true,
                    buttonText: "다음",
                    buttonAria: "마지막 단계로 이동"
                },
                {
                    title: "⚠️ 시작 전 꼭 확인해주세요",
                    visual: "⚠️",
                    visualAlt: "주의 아이콘",
                    body: [
                        "서비스 이용 전에 아래 안내 사항을 확인해 주세요."
                    ],
                    bullets: [
                        "본 도구는 의료 행위(진단)을 제공하지 않습니다.",
                        "일반의약품 선택을 돕기 위한 정보 제공 도구입니다.",
                        "증상이 심하거나 판단이 어려울 경우 반드시 의료기관을 방문하세요."
                    ],
                    details: [
                        {
                            summary: "📄 면책 조항·이용약관 보기",
                            policyKey: 'disclaimer'
                        },
                        {
                            summary: "🔒 개인정보 처리방침 보기",
                            policyKey: 'privacy'
                        }
                    ],
                    checkboxLabel: "위 내용에 동의합니다",
                    startButtonText: "동의하고 이용을 시작하기",
                    startButtonAria: "동의하고 상담을 시작하기"
                }
            ]
        },
        zh: {
            title: "💊 聊天式药品咨询工具",
            titleShort: "药品咨询",
            description: "根据症状推荐合适的非处方药。",
            userInfoBtn: "👤 用户信息",
            clearBtn: "🗑️ 清除历史",
            newSessionBtn: "🔄 新会话",
            adminRequestBtn: "👨‍⚕️ 请求药师",
            placeholder: "请输入您的症状...",
            send: "发送",
            processing: "AI正在处理中...",
            recommendedMedicines: "推荐药品",
            usageNotes: "使用注意事项",
            doctorConsultation: "请咨询医生",
            feedbackPositive: "👍 合适",
            feedbackNegative: "👎 不合适",
            reportBug: "🐛 报告错误",
            age: "年龄",
            gender: "性别",
            male: "男性",
            female: "女性",
            pregnant: "怀孕中",
            breastfeeding: "哺乳中",
            allergies: "过敏",
            currentMedications: "正在服用的药物",
            medicalHistory: "病史",
            otherInfo: "其他信息",
            save: "保存",
            cancel: "取消",
            
            // 初期メッセージ
            initialGreeting: "您好！您有什么症状需要咨询吗？",
            initialExamples: "例如：「头痛」「喉咙痛」「发烧」等",
            
            // システムメッセージ
            chatEnded: "聊天已结束。如有疑问，请随时咨询附近的药剂师。",
            aiPaused: "抱歉，AI自动回复暂时暂停。确认后我们会回复。",
            
            // エラーメッセージ
            systemError: "抱歉，发生系统错误",
            processingError: "处理过程中发生错误",
            networkError: "发生网络错误",
            loadError: "消息加载错误",
            
            // 確認メッセージ
            confirmClearChat: "清除聊天记录？",
            confirmNewSession: "开始新会话？当前对话将不会保存。",
            
            // 評価・フィードバック
            feedbackQuestion: "这个回答怎么样？",
            feedbackQuestionRecommendation: "这个推荐结果怎么样？",
            feedbackQuestionNotice: "这个重要提示怎么样？",
            feedbackThankYou: "感谢您的反馈！",
            
            // 不具合報告
            bugReportPrompt: "请详细说明问题",
            bugReportSubmitted: "错误报告已提交",
            bugReportFailed: "错误报告提交失败",
            
            // 危機対応メッセージ
            crisisSupportTitle: "我们关心您的感受",
            crisisSupportMessage: "专业支持服务可用。请联系危机咨询师。",
            crisisEmergency: "紧急情况请立即拨打119（救护车）或110（警察）。",
            
            // モーダル関連
            infoButton: "应用信息",
            appInfo: "应用概述",
            appInfoDesc: "关于应用功能和特点",
            disclaimer: "免责声明和使用条款",
            disclaimerDesc: "关于使用条款和免责声明",
            privacy: "隐私政策",
            privacyDesc: "关于个人信息处理",
            usage: "使用方法",
            usageDesc: "应用使用方法和安全使用的注意事项",
            consultation: "药品咨询信息",
            consultationDesc: "公共机构咨询窗口信息",
            siteAboutTitle: "详细说明",
            siteAboutDesc: "前往网站版说明页（概览、条款、隐私等）",
            settingsTitle: "设置",
            settingsDesc: "字号等显示设置",
            faq: "常见问题 (FAQ)",
            faqDesc: "常见问题与回答",
            back: "返回",
            close: "×",
            skipOnboarding: "跳过并开始",
            onboardingLastUpdatedLabel: "最后更新",
            onboardingLastUpdatedIso: "2026-05-20",
            onboardingLastUpdated: "2026年5月20日",
            onboarding: [
                {
                    production: {
                        title: "欢迎使用聊天式药品咨询工具（测试版）",
                        visual: "🤝💊",
                        visualAlt: "药师通过手机提供咨询的示意图",
                        subtitle: "测试版（试运行）— 我们持续改进说明的清晰度与安全性",
                        body: [
                            "描述症状后，AI 会提示非处方药候选与就医建议，不能替代医疗诊断。"
                        ],
                        details: [
                            {
                                summary: "当前开发中的主要内容",
                                itemsChecklist: true,
                                items: [
                                    { text: "从 Flask 到 FastAPI 的大规模迁移", defaultChecked: true },
                                    "基于潜在空间的大规模评分改造",
                                    { text: "GPT-5 系列模型（分流、NLU、说明等）", defaultChecked: true },
                                    { text: "多智能体路由（ChatOrchestrator）", defaultChecked: true },
                                    "UI 与流程优化",
                                    "引入轮播式 UI",
                                    "LINE 对接（Messaging API）",
                                    "引入图片能力",
                                    "安全加固",
                                    "语音输入改进",
                                    "身体状况推断（规划中）",
                                    "个性化功能（规划中）"
                                ]
                            }
                        ],
                        links: [
                            {
                                text: "🔗 在新标签页打开开发环境",
                                url: "https://medicine-recommend-dev-340042923793.asia-northeast1.run.app/",
                                ariaLabel: "在新标签页中打开开发环境"
                            },
                            {
                                text: "📝 意见或问题反馈",
                                url: "https://forms.gle/UB8kZHd4VHenmRUN6",
                                ariaLabel: "通过 Google 表单提交意见或问题"
                            }
                        ],
                        buttonText: "下一步",
                        buttonAria: "前往下一步"
                    },
                    development: {
                        title: "🛠️ 欢迎来到开发环境(dev)",
                        visual: "🚧💊",
                        visualAlt: "开发中的药品咨询工具图标",
                        subtitle: '<span class="onboarding-env-badge">🛠️ 这里是开发环境(dev)</span>',
                        body: [
                            '本页面是<span class="onboarding-env-here">面向测试与开发者的开发环境(dev)</span>，与生产环境分属不同服务器，可抢先试用最新功能，但可能出现布局错乱、错误或数据重置。',
                            "普通用户请使用生产环境（稳定版）。"
                        ],
                        details: [
                            {
                                summary: "当前开发中的主要内容",
                                itemsChecklist: true,
                                items: [
                                    { text: "从 Flask 到 FastAPI 的大规模迁移", defaultChecked: true },
                                    "基于潜在空间的大规模评分改造",
                                    { text: "GPT-5 系列模型（分流、NLU、说明等）", defaultChecked: true },
                                    { text: "多智能体路由（ChatOrchestrator）", defaultChecked: true },
                                    "UI 与流程优化",
                                    "引入轮播式 UI",
                                    "LINE 对接（Messaging API）",
                                    "引入图片能力",
                                    "安全加固",
                                    "语音输入改进",
                                    "身体状况推断（规划中）",
                                    "个性化功能（规划中）"
                                ]
                            }
                        ],
                        links: [
                            {
                                text: "🌐 打开生产环境（稳定版）",
                                url: "https://medicine.yutok.dev/",
                                ariaLabel: "在新标签页中打开生产环境（稳定版）"
                            },
                            {
                                text: "📝 投诉与意见",
                                url: "https://forms.gle/UB8kZHd4VHenmRUN6",
                                ariaLabel: "通过 Google 表单提交投诉或意见"
                            }
                        ],
                        buttonText: "下一步",
                        buttonAria: "前往下一步"
                    }
                },
                {
                    title: "🩺 步骤1：告诉我们当前症状",
                    visual: "💬🎤",
                    visualAlt: "症状输入界面的图示",
                    body: [
                        "例如“头很痛”“咳嗽停不下来”等，可自由描述。",
                        "支持文字和语音输入，可通过左上角按钮切换日语、英语、韩语、中文。",
                        "* AI 的回复会根据您发送内容的语言自动检测；若判定为日语以外（如英语、中文、韩语），会进行自动翻译。左上角切换主要影响界面用语。"
                    ],
                    buttonText: "下一步",
                    buttonAria: "前往步骤2"
                },
                {
                    title: "👤 步骤2：获得专属回答",
                    visual: "🧬✨",
                    visualAlt: "个性化回答的图示",
                    body: [
                        "通过“用户信息”登记过敏和正在服用的药物，AI 会综合您的体质与状况。",
                        "必要时会提出追问，让建议更符合您的情况。"
                    ],
                    buttonText: "下一步",
                    buttonAria: "前往步骤3"
                },
                {
                    title: "👩‍⚕️ 步骤3：随时联系药师",
                    visual: "📞👨‍⚕️",
                    visualAlt: "与药师沟通的图示",
                    body: [
                        "如果对 AI 的回答仍感到不确定，可点击“请求药师”与专业人士对话。",
                        "右上角的 ℹ️ 按钮可以随时打开使用指南和常见问题。"
                    ],
                    buttonText: "下一步",
                    buttonAria: "前往下一步"
                },
                {
                    title: "🎮 关于彩蛋功能",
                    visual: "🎉✨",
                    visualAlt: "表示彩蛋功能的图标",
                    body: [
                        "本应用程序包含有趣的隐藏功能“彩蛋”，可通过特定关键词或消息触发。",
                        "发送感谢消息会显示粒子效果，特定关键词会使屏幕变形，仅发送表情符号会显示特殊效果。",
                        "请尝试一下！"
                    ],
                    bullets: [
                        "感谢消息（“谢谢”等）触发粒子效果",
                        "屏幕变形（“旋转”、“摇晃”等关键词）",
                        "仅发送表情符号",
                        "季节性活动支持（新年、圣诞节等）"
                    ],
                    buttonText: "下一步",
                    buttonAria: "前往下一步"
                },
                {
                    title: "📚 本应用程序资料",
                    visual: "📄📊",
                    visualAlt: "表示资料的图标",
                    body: [
                        "我们准备了有关本应用程序的详细资料。",
                        "您可以通过以下链接查看技术文档、PowerPoint、解说视频和原型。"
                    ],
                    links: [
                        {
                            text: "📄 技术文档",
                            url: "https://drive.google.com/file/d/19CTRYV4moDikaLKXgC2Z_70wRXeCwKbx/view?usp=sharing",
                            ariaLabel: "在Google Drive中打开技术文档"
                        },
                        {
                            text: "📊 PowerPoint",
                            url: "https://drive.google.com/file/d/1FhdB7aUWlhYHRdhMLjDrNU0bvGyjdZ1F/view?usp=sharing",
                            ariaLabel: "在Google Drive中打开PowerPoint"
                        },
                        {
                            text: "🎥 解说视频",
                            url: "https://youtu.be/O1ptrH1q7S4",
                            ariaLabel: "在YouTube中打开解说视频"
                        },
                        {
                            text: "🎨 原型 (Marvel)",
                            url: "https://marvelapp.com/prototype/350fehf6",
                            ariaLabel: "打开Marvel原型"
                        }
                    ],
                    isBetaOnly: true,
                    hidden: true,
                    buttonText: "下一步",
                    buttonAria: "前往最后一步"
                },
                {
                    title: "⚠️ 开始使用前的重点提醒",
                    visual: "⚠️",
                    visualAlt: "注意图示",
                    body: [
                        "开始前，请先阅读以下注意事项。"
                    ],
                    bullets: [
                        "本工具不提供医疗行为（诊断）。",
                        "它是辅助选择非处方药的信息服务。",
                        "若症状严重或无法判断，请务必就医。"
                    ],
                    details: [
                        {
                            summary: "📄 查看免责声明与使用条款",
                            policyKey: 'disclaimer'
                        },
                        {
                            summary: "🔒 查看隐私政策",
                            policyKey: 'privacy'
                        }
                    ],
                    checkboxLabel: "我同意以上内容",
                    startButtonText: "同意并开始使用",
                    startButtonAria: "同意并开始咨询"
                }
            ]
        }
    };

    const DEFAULT_LANGUAGE = 'ja';
    const ONBOARDING_SWIPE_THRESHOLD = 48;

    let onboardingState = {
        initialized: false,
        currentSlide: 0,
        totalSlides: 0,
        touchStartX: 0
    };

    function isSageUi() {
        return document.body && document.body.getAttribute('data-ui-variant') === 'sage';
    }

    function isSeasonDecorationEnabled() {
        const v = localStorage.getItem('seasonDecorationEnabled');
        return v === null || v === 'true';
    }

    function isParticleEffectsEnabled() {
        return localStorage.getItem('particleEffectsEnabled') === 'true';
    }

    function setSeasonDecorationEnabled(enabled) {
        localStorage.setItem('seasonDecorationEnabled', enabled ? 'true' : 'false');
        applySeasonDecorationVisibility();
    }

    function setParticleEffectsEnabled(enabled) {
        localStorage.setItem('particleEffectsEnabled', enabled ? 'true' : 'false');
        if (!enabled) {
            const snowContainer = document.getElementById('snowContainer');
            if (snowContainer) snowContainer.innerHTML = '';
        } else {
            createSeasonalParticles();
        }
    }

    function applySeasonDecorationVisibility() {
        const layer = document.querySelector('.season-decoration-layer');
        if (layer) {
            layer.style.display = isSeasonDecorationEnabled() ? '' : 'none';
        }
    }

    function injectSageDisplaySettings() {
        if (!isSageUi()) return;
        const detail = document.getElementById('detailContent');
        if (!detail || detail.querySelector('[data-sage-display-settings]')) return;
        const tUi = window.UiStrings ? window.UiStrings.t : function (k) { return k; };
        const seasonOn = isSeasonDecorationEnabled();
        const particleOn = isParticleEffectsEnabled();
        const block = document.createElement('div');
        block.setAttribute('data-sage-display-settings', 'true');
        block.className = 'info-section sage-display-settings';
        block.innerHTML =
            '<h3>🎨 ' + (tUi('settingsSeasonLabel') || '表示演出') + '</h3>' +
            '<div class="sage-setting-row" style="margin:16px 0;display:flex;align-items:center;justify-content:space-between;gap:12px;">' +
            '<div><strong>' + tUi('settingsSeasonLabel') + '</strong><p style="margin:4px 0 0;color:#666;font-size:0.9em;">' + tUi('settingsSeasonDesc') + '</p></div>' +
            '<label class="sage-toggle"><input type="checkbox" id="toggle-season-decoration"' + (seasonOn ? ' checked' : '') + '><span></span></label>' +
            '</div>' +
            '<div class="sage-setting-row" style="margin:16px 0;display:flex;align-items:center;justify-content:space-between;gap:12px;">' +
            '<div><strong>' + tUi('settingsParticleLabel') + '</strong><p style="margin:4px 0 0;color:#666;font-size:0.9em;">' + tUi('settingsParticleDesc') + '</p></div>' +
            '<label class="sage-toggle"><input type="checkbox" id="toggle-particle-effects"' + (particleOn ? ' checked' : '') + '><span></span></label>' +
            '</div>';
        detail.appendChild(block);
        const seasonCb = block.querySelector('#toggle-season-decoration');
        const particleCb = block.querySelector('#toggle-particle-effects');
        if (seasonCb) {
            seasonCb.addEventListener('change', function () {
                setSeasonDecorationEnabled(seasonCb.checked);
            });
        }
        if (particleCb) {
            particleCb.addEventListener('change', function () {
                setParticleEffectsEnabled(particleCb.checked);
            });
        }
    }

    function refreshSageSafetyRail(attrs) {
        if (!isSageUi() || !window.SageShell) return;
        if (attrs && window.SafetyRail && window.SafetyRail.normalizeAttrs) {
            attrs = window.SafetyRail.normalizeAttrs(attrs);
        }
        if (attrs) window.__lastUserAttributes = attrs;
        window.SageShell.refreshSafetyRail(attrs || window.__lastUserAttributes || {});
    }

    function getLatestRecommendationRoot() {
        return document.querySelector('.message--sage-reco .ui-bubble--reco') ||
            document.querySelector('.recommendation-result');
    }

    function enhanceSageRecommendationMessage(messageDiv, message) {
        if (!isSageUi() || !window.RecommendationRenderer || !message) return;
        window.RecommendationRenderer.mountSageRecommendation(messageDiv, message, {
            legacyHost: messageDiv.querySelector('.recommendation-result')
        });
    }

    window.setSeasonDecorationEnabled = setSeasonDecorationEnabled;
    window.setParticleEffectsEnabled = setParticleEffectsEnabled;

    let onboardingModalResizeObserver = null;

    function syncOnboardingModalHeightVar() {
        const container = document.getElementById('onboarding-container');
        if (!container || container.classList.contains('hidden')) {
            return;
        }
        const h = container.offsetHeight;
        if (h > 0) {
            container.style.setProperty('--onb-modal-height', h + 'px');
        }
    }

    function teardownOnboardingModalHeightTracking() {
        if (onboardingModalResizeObserver) {
            onboardingModalResizeObserver.disconnect();
            onboardingModalResizeObserver = null;
        }
        window.removeEventListener('resize', syncOnboardingModalHeightVar);
        const container = document.getElementById('onboarding-container');
        if (container) {
            container.style.removeProperty('--onb-modal-height');
        }
    }

    function setupOnboardingModalHeightTracking(container) {
        teardownOnboardingModalHeightTracking();
        if (!container) {
            return;
        }
        window.addEventListener('resize', syncOnboardingModalHeightVar);
        if (typeof ResizeObserver !== 'undefined') {
            onboardingModalResizeObserver = new ResizeObserver(function() {
                syncOnboardingModalHeightVar();
            });
            onboardingModalResizeObserver.observe(container);
        }
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                syncOnboardingModalHeightVar();
            });
        });
    }

    let onboardingDetailsToggleBound = false;

    function syncOnboardingDetailsDenseClass() {
        const scrollEl = document.querySelector('#onboarding-slides .onboarding-slide.active .onboarding-slide-scroll');
        if (!scrollEl) {
            return;
        }
        const openCount = scrollEl.querySelectorAll('details.onboarding-details[open]').length;
        scrollEl.classList.toggle('onboarding-details-dense', openCount >= 2);
    }

    function handleOnboardingDetailsToggleEvent(event) {
        const t = event.target;
        if (!t || typeof t.matches !== 'function' || !t.matches('details.onboarding-details')) {
            return;
        }
        syncOnboardingDetailsDenseClass();
    }

    function ensureOnboardingDetailsToggleListener() {
        const slides = document.getElementById('onboarding-slides');
        if (!slides || onboardingDetailsToggleBound) {
            return;
        }
        slides.addEventListener('toggle', handleOnboardingDetailsToggleEvent, true);
        onboardingDetailsToggleBound = true;
    }

    function teardownOnboardingDetailsToggleListener() {
        const slides = document.getElementById('onboarding-slides');
        if (!slides || !onboardingDetailsToggleBound) {
            return;
        }
        slides.removeEventListener('toggle', handleOnboardingDetailsToggleEvent, true);
        onboardingDetailsToggleBound = false;
    }

    /** オンボーディングの読み取り専用チェックリスト用。{ text, defaultChecked: true } で実装済み表示（コード側のみ変更可） */
    function normalizeOnboardingDetailItem(item) {
        if (item == null) {
            return { text: '', defaultChecked: false };
        }
        if (typeof item === 'string') {
            return { text: item, defaultChecked: false };
        }
        return {
            text: item.text != null ? String(item.text) : '',
            defaultChecked: !!item.defaultChecked
        };
    }

    function getActiveTranslations() {
        return translations[currentLanguage] || translations[DEFAULT_LANGUAGE];
    }

    // 開発環境かどうかを判定する
    // 優先順位: 1) サーバが埋め込んだ #app-runtime-config（本番判定の単一ソース）、2) body[data-env]、3) ホスト名フォールバック
    function isDevEnv() {
        try {
            const cfgEl = typeof document !== 'undefined' ? document.getElementById('app-runtime-config') : null;
            if (cfgEl && cfgEl.textContent) {
                const cfg = JSON.parse(cfgEl.textContent.trim());
                if (cfg && typeof cfg.isDevelopment === 'boolean') {
                    return cfg.isDevelopment;
                }
            }
        } catch (e) {
            // フォールスルー
        }
        try {
            if (typeof document !== 'undefined' && document.body) {
                const attr = (document.body.getAttribute('data-env') || document.body.dataset.env || '').toString().toLowerCase().trim();
                if (attr === 'dev' || attr === 'development') {
                    return true;
                }
                if (attr === 'prod' || attr === 'production') {
                    return false;
                }
            }
        } catch (e) {
            // フォールスルー
        }
        try {
            const host = (typeof location !== 'undefined' && location.hostname) ? location.hostname.toLowerCase() : '';
            if (!host) return false;
            return (
                host === 'localhost' ||
                host === '127.0.0.1' ||
                host.includes('-dev-') ||
                host.endsWith('.local') ||
                host.startsWith('dev.')
            );
        } catch (e) {
            return false;
        }
    }

    /**
     * onboarding[0] が { production, development } のとき、isDevEnv() に応じて実スライドを返す。
     * 従来の単一オブジェクトのままの onboarding[0] はそのまま返す（2〜枚目は常に通常スライド）。
     */
    function resolveOnboardingFirstSlide(firstSlide, locale, fallbackLocale) {
        if (!firstSlide || typeof firstSlide !== 'object') {
            return firstSlide;
        }
        const prod = firstSlide.production;
        const dev = firstSlide.development;
        if (prod && dev) {
            return isDevEnv() ? dev : prod;
        }
        if (prod || dev) {
            if (isDevEnv() && dev) {
                return dev;
            }
            if (prod) {
                return prod;
            }
            return dev;
        }
        if (isDevEnv()) {
            const legacy = (locale && locale.onboardingDevFirstSlide)
                || (fallbackLocale && fallbackLocale.onboardingDevFirstSlide);
            if (legacy) {
                return legacy;
            }
        }
        return firstSlide;
    }

    function getOnboardingData(lang) {
        const locale = translations[lang];
        const fallbackLocale = translations[DEFAULT_LANGUAGE];

        let baseSlides = null;
        if (locale && Array.isArray(locale.onboarding) && locale.onboarding.length > 0) {
            baseSlides = locale.onboarding;
        } else if (fallbackLocale && Array.isArray(fallbackLocale.onboarding)) {
            baseSlides = fallbackLocale.onboarding;
        }
        if (!baseSlides || !baseSlides.length) {
            return [];
        }

        const first = resolveOnboardingFirstSlide(baseSlides[0], locale, fallbackLocale);
        if (!first) {
            return baseSlides.slice(1);
        }
        return [first, ...baseSlides.slice(1)];
    }

    function getFilteredOnboardingSlides() {
        const slidesData = getOnboardingData(currentLanguage);
        if (!slidesData.length) {
            return [];
        }
        const isBetaVersion = isDevEnv() ||
            document.title.includes('β') || document.title.includes('Beta') ||
            (typeof translations !== 'undefined' && translations[currentLanguage] &&
                translations[currentLanguage].title &&
                (translations[currentLanguage].title.includes('β') || translations[currentLanguage].title.includes('Beta')));
        return slidesData.filter((slide) => {
            if (slide.hidden === true) {
                return false;
            }
            if (slide.isBetaOnly && !isBetaVersion) {
                return false;
            }
            return true;
        });
    }

    function syncOnboardingActiveVisual(slide) {
        const holder = document.getElementById('onboarding-active-visual');
        if (!holder) {
            return;
        }
        if (slide && slide.visual) {
            const alt = escapeHtml(String(slide.visualAlt || ''));
            holder.innerHTML = '<div class="onboarding-visual" role="img" aria-label="' + alt + '">' + slide.visual + '</div>';
            holder.removeAttribute('aria-hidden');
        } else {
            holder.innerHTML = '';
            holder.setAttribute('aria-hidden', 'true');
        }
    }

    function updateOnboardingSkipLabel() {
        const skipBtn = document.getElementById('onboarding-skip-btn');
        if (!skipBtn) {
            return;
        }
        const t = getActiveTranslations();
        if (t && t.skipOnboarding) {
            skipBtn.textContent = t.skipOnboarding;
            skipBtn.setAttribute('aria-label', t.skipOnboarding);
        }
    }

    function getOnboardingDetailContent(detail) {
        if (!detail) {
            return '';
        }

        if (detail.policyKey && typeof modalPages !== 'undefined') {
            const policy = modalPages[detail.policyKey];
            if (policy && policy.content) {
                const localized = policy.content[currentLanguage] || policy.content[DEFAULT_LANGUAGE];
                if (localized) {
                    return localized;
                }
            }
        }

        if (detail.content) {
            return detail.content;
        }

        return '';
    }

    function createOnboardingDetailsMarkup(slide) {
        if (!slide || !Array.isArray(slide.details) || !slide.details.length) {
            return '';
        }

        return slide.details.map(detail => {
            const summary = detail.summary || '';
            const content = getOnboardingDetailContent(detail);
            let itemsHtml = '';
            if (Array.isArray(detail.items) && detail.items.length) {
                if (detail.itemsChecklist) {
                    const lis = detail.items.map(function (item) {
                        const norm = normalizeOnboardingDetailItem(item);
                        const doneClass = norm.defaultChecked ? ' is-done' : '';
                        return (
                            '<li class="onboarding-checklist-item' + doneClass + '">' +
                            '<span class="onboarding-checklist-marker" aria-hidden="true"></span>' +
                            '<span class="onboarding-checklist-text">' + escapeHtml(norm.text) + '</span>' +
                            '</li>'
                        );
                    }).join('');
                    itemsHtml = '<ul class="onboarding-checklist onboarding-checklist-readonly" role="list">' + lis + '</ul>';
                } else {
                    itemsHtml = '<ul>' + detail.items.map(function (item) {
                        const t = typeof item === 'string' ? item : (item && item.text != null ? String(item.text) : '');
                        return '<li>' + t + '</li>';
                    }).join('') + '</ul>';
                }
            }
            const innerParts = [];
            if (itemsHtml) {
                innerParts.push(itemsHtml);
            }
            if (content) {
                innerParts.push(content);
            }
            const contentHtml = innerParts.length
                ? '<div class="onboarding-details-content">' + innerParts.join('') + '</div>'
                : '';

            return `
                <details class="onboarding-details">
                    <summary>${summary}</summary>
                    ${contentHtml}
                </details>
            `;
        }).join('');
    }

    function createOnboardingFinalActions(slide) {
        if (!slide || !slide.startButtonText) {
            return '';
        }
        const checkbox = slide.checkboxLabel
            ? `<label class="onboarding-agree"><input type="checkbox" id="agreeCheckbox" onchange="toggleAgreeButton()"> ${slide.checkboxLabel}</label>`
            : '';
        return `
            ${checkbox}
            <button type="button" class="onboarding-btn onboarding-btn-primary" id="startButton" onclick="completeOnboarding()" disabled aria-label="${slide.startButtonAria || slide.startButtonText}">${slide.startButtonText}</button>
        `;
    }

    function renderOnboardingSlides(activeIndex = 0) {
        const slidesContainer = document.getElementById('onboarding-slides');
        if (!slidesContainer) {
            return;
        }
        const filteredSlides = getFilteredOnboardingSlides();
        if (!filteredSlides.length) {
            slidesContainer.innerHTML = '';
            syncOnboardingActiveVisual(null);
            onboardingState.totalSlides = 0;
            onboardingState.currentSlide = 0;
            const indicator = document.getElementById('slide-indicator');
            if (indicator) {
                indicator.innerHTML = '';
            }
            return;
        }

        // フィルタリング後のスライド数に基づいてtargetIndexを計算
        const filteredTotal = filteredSlides.length;
        let targetIndex = Math.max(0, Math.min(activeIndex, filteredTotal - 1));
        onboardingState.totalSlides = filteredTotal;
        onboardingState.currentSlide = targetIndex;
        
        const html = filteredSlides
            .map((slide, filteredIndex, filteredArray) => {
                const isActive = filteredIndex === targetIndex;
                const bodyHtml = Array.isArray(slide.body)
                    ? slide.body.map(text => `<p>${text}</p>`).join('')
                    : (slide.body || '');
                const locale = getActiveTranslations();
                const lastUpdatedIso = locale.onboardingLastUpdatedIso || '2026-05-20';
                const lastUpdatedHtml = (filteredIndex === 0 && locale.onboardingLastUpdated)
                    ? `<p class="onboarding-last-updated">${locale.onboardingLastUpdatedLabel ? `<span class="onboarding-last-updated-label">${locale.onboardingLastUpdatedLabel}</span> ` : ''}<time datetime="${lastUpdatedIso}">${locale.onboardingLastUpdated}</time></p>`
                    : '';
                const listHtml = Array.isArray(slide.list)
                    ? `<ul>${slide.list.map(item => `<li>${item}</li>`).join('')}</ul>`
                    : '';
                const bulletsHtml = Array.isArray(slide.bullets)
                    ? `<ul>${slide.bullets.map(item => `<li>${item}</li>`).join('')}</ul>`
                    : '';
                const detailsHtml = createOnboardingDetailsMarkup(slide);
                
                // カスタムHTMLがある場合はそれを使用
                const customHtml = slide.customHtml || '';
                
                // リンクボタンがある場合はそれを使用
                let linksHtml = '';
                if (Array.isArray(slide.links) && slide.links.length > 0) {
                    linksHtml = '<div class="onboarding-links">' + 
                        slide.links.map(link => 
                            `<a href="${link.url}" target="_blank" rel="noopener noreferrer" class="onboarding-link-btn" aria-label="${link.ariaLabel || link.text}">${link.text}</a>`
                        ).join('') + 
                        '</div>';
                }
                
                const actionsHtml = (filteredIndex === filteredArray.length - 1)
                    ? createOnboardingFinalActions(slide)
                    : `<button type="button" class="onboarding-btn" onclick="nextOnboardingSlide()" aria-label="${slide.buttonAria || slide.buttonText}">${slide.buttonText}</button>`;
                const subtitleHtml = slide.subtitle ? `<p class="onboarding-subtitle">${slide.subtitle}</p>` : '';
                return `
                    <div class="onboarding-slide${isActive ? ' active' : ''}" role="tabpanel" data-slide-index="${filteredIndex}" aria-hidden="${isActive ? 'false' : 'true'}">
                        <div class="onboarding-slide-header">
                            <h2 class="onboarding-title">${slide.title}</h2>
                            ${subtitleHtml}
                        </div>
                        <div class="onboarding-slide-scroll">
                            <div class="onboarding-desc">
                                ${bodyHtml}
                                ${listHtml}
                                ${bulletsHtml}
                                ${customHtml}
                                ${linksHtml}
                            </div>
                            ${lastUpdatedHtml}
                            ${detailsHtml}
                        </div>
                        <div class="onboarding-slide-footer">
                            ${actionsHtml}
                        </div>
                    </div>
                `;
            }).join('');
        slidesContainer.innerHTML = html;
        syncOnboardingActiveVisual(filteredSlides[targetIndex] || null);
        updateOnboardingIndicator(targetIndex);
        updateOnboardingSkipLabel();
        onboardingState.touchStartX = 0;
        // 初期表示時にも要素を強調し、制御を設定（レイアウト確定後すぐ。100ms だとオーバーレイがクリック遮断になるまでに隙ができる）
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                setOnboardingStepControls(targetIndex);
                highlightOnboardingElements(targetIndex);
                syncOnboardingChatTabstops(getOnboardingInteractionMode(targetIndex));
                if (onboardingState.initialized) {
                    syncOnboardingModalHeightVar();
                    syncOnboardingDetailsDenseClass();
                }
            });
        });
    }

    function updateOnboardingIndicator(activeIndex) {
        const indicator = document.getElementById('slide-indicator');
        if (!indicator) {
            return;
        }
        const total = onboardingState.totalSlides;
        indicator.innerHTML = '';
        if (!total) {
            return;
        }
        for (let i = 0; i < total; i++) {
            const dot = document.createElement('button');
            dot.type = 'button';
            dot.className = 'slide-indicator-dot' + (i === activeIndex ? ' active' : '');
            dot.textContent = i === activeIndex ? '●' : '○';
            dot.setAttribute('aria-label', `${i + 1} / ${total}`);
            if (i === activeIndex) {
                dot.setAttribute('aria-current', 'step');
                dot.disabled = true;
            } else {
                dot.addEventListener('click', function() {
                    goToOnboardingSlide(i);
                });
            }
            indicator.appendChild(dot);
        }
    }

    function highlightOnboardingElements(slideIndex) {
        // すべての強調を解除
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
        });
        document.querySelectorAll('.onboarding-highlight-parent').forEach(el => {
            el.classList.remove('onboarding-highlight-parent');
        });

        // 各ステップに応じて要素を強調（言語 UI の強調はスライド0・1のみ）
        switch(slideIndex) {
            case 0: // ステップ0: 言語選択（視覚強調は末尾で共通適用）
                break;
            
            case 1: // ステップ1: 入力欄、マイクボタン、言語選択ボタン
                const messageInput = document.getElementById('messageInput');
                const micBtn = document.getElementById('micBtn');
                
                if (messageInput) {
                    const inputGroup = messageInput.closest('.input-group')
                        || messageInput.closest('.ui-input-row')
                        || messageInput.closest('.message-input-field');
                    if (inputGroup) {
                        inputGroup.classList.add('onboarding-highlight');
                    } else {
                        messageInput.classList.add('onboarding-highlight');
                    }
                }
                if (micBtn) {
                    micBtn.classList.add('onboarding-highlight');
                }
                break;
            
            case 2: // ステップ2: ユーザー情報（Sage は安全レール CTA）
                if (isSageUi()) {
                    const safetyCta = document.getElementById('safetyRailCta');
                    if (safetyCta) {
                        safetyCta.classList.add('onboarding-highlight');
                    }
                } else {
                    const userInfoBtn = document.getElementById('userInfoBtn');
                    if (userInfoBtn) {
                        userInfoBtn.classList.add('onboarding-highlight');
                    }
                }
                break;
            
            case 3: // ステップ3: 薬剤師要請・情報
                if (isSageUi()) {
                    const sageAdminBtn = document.getElementById('sage-admin-request-btn');
                    const sageInfoBtn = document.getElementById('sage-info-btn');
                    if (sageAdminBtn) {
                        sageAdminBtn.classList.add('onboarding-highlight');
                    }
                    if (sageInfoBtn) {
                        sageInfoBtn.classList.add('onboarding-highlight');
                    }
                } else {
                    const adminRequestBtn = document.getElementById('admin-request-btn');
                    const infoBtn = document.getElementById('infoBtn');
                    const infoSelector = document.querySelector('.info-selector');
                    
                    if (adminRequestBtn) {
                        adminRequestBtn.classList.add('onboarding-highlight');
                    }
                    if (infoBtn) {
                        infoBtn.classList.add('onboarding-highlight');
                        if (infoSelector) {
                            infoSelector.classList.add('onboarding-highlight-parent');
                        }
                    }
                }
                break;
            
            default:
                break;
        }

        if (slideIndex === 0 || slideIndex === 1) {
            const langToggleAlways = document.querySelector('.lang-toggle');
            const languageSelectorAlways = document.querySelector('.language-selector');
            if (langToggleAlways) {
                langToggleAlways.classList.add('onboarding-highlight');
            }
            if (languageSelectorAlways) {
                languageSelectorAlways.classList.add('onboarding-highlight-parent');
            }
        }
    }

    function getOnboardingInteractionMode(slideIndex) {
        if (typeof slideIndex !== 'number' || slideIndex < 0) {
            return 'locked';
        }
        if (slideIndex >= 4) {
            return 'locked';
        }
        return String(slideIndex);
    }

    const ONBOARDING_TAB_STASH = 'data-onb-tabindex-stash';

    function restoreAllOnboardingChatTabstops() {
        const chat = document.querySelector('.chat-container');
        if (!chat) {
            return;
        }
        chat.querySelectorAll('[' + ONBOARDING_TAB_STASH + ']').forEach(function(el) {
            const prev = el.getAttribute(ONBOARDING_TAB_STASH);
            el.removeAttribute(ONBOARDING_TAB_STASH);
            if (prev === '__default__') {
                el.removeAttribute('tabindex');
            } else {
                el.setAttribute('tabindex', prev);
            }
        });
    }

    function isChatElementAllowedInOnboardingInteraction(el, interactionMode) {
        const chat = document.querySelector('.chat-container');
        if (!chat || !chat.contains(el)) {
            return false;
        }
        if (el.closest('.language-selector')) {
            return true;
        }
        if (interactionMode === 'locked') {
            return false;
        }
        if (interactionMode === '0') {
            return false;
        }
        if (interactionMode === '1') {
            return false;
        }
        if (interactionMode === '2') {
            return false;
        }
        if (interactionMode === '3') {
            return false;
        }
        return false;
    }

    function syncOnboardingChatTabstops(interactionMode) {
        const chat = document.querySelector('.chat-container');
        if (!chat || !document.body.classList.contains('onboarding-open')) {
            return;
        }
        restoreAllOnboardingChatTabstops();
        const sel = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [contenteditable="true"], [tabindex]';
        chat.querySelectorAll(sel).forEach(function(el) {
            if (!isChatElementAllowedInOnboardingInteraction(el, interactionMode)) {
                if (!el.hasAttribute(ONBOARDING_TAB_STASH)) {
                    const had = el.hasAttribute('tabindex');
                    const prev = had ? el.getAttribute('tabindex') : '__default__';
                    el.setAttribute(ONBOARDING_TAB_STASH, prev);
                    el.tabIndex = -1;
                }
            }
        });
        const ae = document.activeElement;
        if (ae && chat.contains(ae) && !isChatElementAllowedInOnboardingInteraction(ae, interactionMode)) {
            try {
                ae.blur();
            } catch (eBlur) {
                /* noop */
            }
            const modal = document.getElementById('onboarding-container');
            if (modal && typeof modal.focus === 'function') {
                modal.focus({ preventScroll: true });
            }
        }
    }

    let onboardingChatGuardAttached = false;
    const ONBOARDING_TOUCH_GUARD_OPTS = { capture: true, passive: false };

    function onboardingChatInteractionGuardHandler(event) {
        if (!document.body.classList.contains('onboarding-open')) {
            return;
        }
        const mode = document.body.getAttribute('data-onboarding-interaction');
        if (mode === null || mode === '') {
            return;
        }
        let raw = event.target;
        if (!raw) {
            return;
        }
        if (raw.nodeType === 3) {
            raw = raw.parentElement;
        }
        if (!(raw instanceof Element)) {
            return;
        }
        const chat = document.querySelector('.chat-container');
        if (!chat || !chat.contains(raw)) {
            return;
        }
        if (isChatElementAllowedInOnboardingInteraction(raw, mode)) {
            return;
        }
        if (event.cancelable) {
            event.preventDefault();
        }
        event.stopPropagation();
        if (typeof event.stopImmediatePropagation === 'function') {
            event.stopImmediatePropagation();
        }
    }

    function attachOnboardingChatInteractionGuard() {
        if (onboardingChatGuardAttached) {
            return;
        }
        onboardingChatGuardAttached = true;
        document.addEventListener('pointerdown', onboardingChatInteractionGuardHandler, true);
        document.addEventListener('click', onboardingChatInteractionGuardHandler, true);
        document.addEventListener('touchstart', onboardingChatInteractionGuardHandler, ONBOARDING_TOUCH_GUARD_OPTS);
    }

    function detachOnboardingChatInteractionGuard() {
        if (!onboardingChatGuardAttached) {
            return;
        }
        onboardingChatGuardAttached = false;
        document.removeEventListener('pointerdown', onboardingChatInteractionGuardHandler, true);
        document.removeEventListener('click', onboardingChatInteractionGuardHandler, true);
        document.removeEventListener('touchstart', onboardingChatInteractionGuardHandler, ONBOARDING_TOUCH_GUARD_OPTS);
    }

    function setOnboardingStepControls(index) {
        const overlay = document.getElementById('onboarding-overlay');
        if (overlay) {
            overlay.setAttribute('data-step', index);
        }
        document.body.setAttribute('data-onboarding-step', index);
        document.body.setAttribute('data-onboarding-interaction', getOnboardingInteractionMode(index));

        // クリック可否は CSS（body.onboarding-open .chat-container * + ステップ別許可）に任せ、ここでは見た目の淡色のみ制御
        const disabledButtons = [
            '#infoBtn',
            '#micBtn',
            '#chatForm button[type="submit"]',
            '#userInfoBtn',
            '#clearBtn',
            '#new-session-btn',
            '#admin-request-btn'
        ];
        const disabledElements = [
            '#chatForm',
            '#messageInput'
        ];

        disabledButtons.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                el.style.opacity = '0.6';
            });
        });

        disabledElements.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                el.style.opacity = '0.6';
            });
        });

        const languageSelectorDim = document.querySelector('.language-selector');
        const langToggleDim = document.querySelector('.lang-toggle');
        if (languageSelectorDim) {
            languageSelectorDim.style.opacity = '1';
        }
        if (langToggleDim) {
            langToggleDim.style.opacity = '1';
        }

        const inputGroupDim = document.querySelector('.input-group');
        if (inputGroupDim) {
            inputGroupDim.style.opacity = index === 1 ? '1' : '0.6';
        }

        switch(index) {
            case 0:
                break;

            case 1: {
                const messageInput = document.getElementById('messageInput');
                const micBtn = document.getElementById('micBtn');
                const sendButton = document.querySelector('#chatForm button[type="submit"]');
                const chatForm = document.getElementById('chatForm');
                if (messageInput) {
                    messageInput.style.opacity = '1';
                }
                if (micBtn) {
                    micBtn.style.opacity = '1';
                }
                if (sendButton) {
                    sendButton.style.opacity = '1';
                }
                if (chatForm) {
                    chatForm.style.opacity = '1';
                }
                break;
            }

            case 2: {
                const userInfoBtn = document.getElementById('userInfoBtn');
                if (userInfoBtn) {
                    userInfoBtn.style.opacity = '1';
                }
                break;
            }

            case 3: {
                const adminRequestBtn = document.getElementById('admin-request-btn');
                const infoBtnStep3 = document.getElementById('infoBtn');
                if (adminRequestBtn) {
                    adminRequestBtn.style.opacity = '1';
                }
                if (infoBtnStep3) {
                    infoBtnStep3.style.opacity = '1';
                }
                break;
            }
        }
    }

    function goToOnboardingSlide(index) {
        if (!onboardingState.initialized) {
            return;
        }
        if (index < 0 || index >= onboardingState.totalSlides) {
            return;
        }
        const slides = document.querySelectorAll('.onboarding-slide');
        slides.forEach(function(slide, idx) {
            if (idx === index) {
                slide.classList.add('active');
                slide.setAttribute('aria-hidden', 'false');
            } else {
                slide.classList.remove('active');
                slide.setAttribute('aria-hidden', 'true');
            }
        });
        onboardingState.currentSlide = index;
        const filtered = getFilteredOnboardingSlides();
        syncOnboardingActiveVisual(filtered[index] || null);
        updateOnboardingIndicator(index);
        setOnboardingStepControls(index);
        highlightOnboardingElements(index);
        syncOnboardingChatTabstops(getOnboardingInteractionMode(index));
        const slidesRoot = document.getElementById('onboarding-slides');
        if (slidesRoot) {
            const scrollArea = slidesRoot.querySelector('.onboarding-slide.active .onboarding-slide-scroll');
            if (scrollArea) {
                scrollArea.scrollTop = 0;
            }
        }
    }

    function nextOnboardingSlide() {
        if (!onboardingState.initialized) {
            return;
        }
        const nextIndex = onboardingState.currentSlide + 1;
        if (nextIndex < onboardingState.totalSlides) {
            goToOnboardingSlide(nextIndex);
            return;
        }
        const startButton = document.getElementById('startButton');
        if (startButton && startButton.disabled) {
            const checkbox = document.getElementById('agreeCheckbox');
            if (checkbox) {
                checkbox.focus({ preventScroll: true });
            }
            return;
        }
        completeOnboarding();
    }

    function previousOnboardingSlide() {
        if (!onboardingState.initialized) {
            return;
        }
        const prevIndex = onboardingState.currentSlide - 1;
        if (prevIndex >= 0) {
            goToOnboardingSlide(prevIndex);
        }
    }

    function toggleAgreeButton() {
        const checkbox = document.getElementById('agreeCheckbox');
        const button = document.getElementById('startButton');
        if (!button) {
            return;
        }
        button.disabled = !(checkbox && checkbox.checked);
    }

    function hideOnboardingOverlay() {
        detachOnboardingChatInteractionGuard();
        const overlay = document.getElementById('onboarding-overlay');
        const container = document.getElementById('onboarding-container');
        const slidesContainer = document.getElementById('onboarding-slides');
        if (overlay) {
            overlay.classList.add('hidden');
            overlay.setAttribute('aria-hidden', 'true');
            overlay.removeAttribute('data-step');
        }
        if (container) {
            container.classList.add('hidden');
            container.setAttribute('aria-hidden', 'true');
            container.removeEventListener('keydown', handleOnboardingKeydown);
            teardownOnboardingModalHeightTracking();
            teardownOnboardingDetailsToggleListener();
        }
        restoreAllOnboardingChatTabstops();
        document.body.classList.remove('onboarding-open');
        document.body.removeAttribute('data-onboarding-step');
        document.body.removeAttribute('data-onboarding-interaction');
        if (slidesContainer) {
            slidesContainer.removeEventListener('touchstart', handleOnboardingTouchStart);
            slidesContainer.removeEventListener('touchend', handleOnboardingTouchEnd);
        }
        // すべての強調を解除
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
        });
        document.querySelectorAll('.onboarding-highlight-parent').forEach(el => {
            el.classList.remove('onboarding-highlight-parent');
        });
        // すべての要素の制限を解除
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            if (el.style.pointerEvents === 'none' || el.style.opacity === '0.6') {
                el.style.pointerEvents = '';
                el.style.opacity = '';
                el.style.cursor = '';
            }
        });
        onboardingState.initialized = false;
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.focus({ preventScroll: true });
        }
    }

    function completeOnboarding() {
        try {
            localStorage.setItem('onboardingCompleted', 'true');
        } catch (error) {
            console.warn('Failed to persist onboarding completion:', error);
        }
        hideOnboardingOverlay();
    }

    function skipOnboarding() {
        try {
            localStorage.setItem('onboardingCompleted', 'true');
        } catch (error) {
            console.warn('Failed to persist onboarding skip:', error);
        }
        try {
            sessionStorage.setItem('quickStartGuideClosed', 'true');
        } catch (error) {
            console.warn('Failed to persist quick start preference:', error);
        }
        hideOnboardingOverlay();
    }

    function initOnboarding() {
        const overlay = document.getElementById('onboarding-overlay');
        const container = document.getElementById('onboarding-container');
        if (!overlay || !container) {
            return;
        }
        onboardingState.initialized = true;
        onboardingState.currentSlide = 0;
        overlay.classList.remove('hidden');
        overlay.setAttribute('aria-hidden', 'false');
        overlay.setAttribute('data-step', '0');
        container.classList.remove('hidden');
        container.setAttribute('aria-hidden', 'false');
        document.body.classList.add('onboarding-open');
        attachOnboardingChatInteractionGuard();
        setOnboardingStepControls(0);
        syncOnboardingChatTabstops(getOnboardingInteractionMode(0));
        renderOnboardingSlides(0);
        setupOnboardingModalHeightTracking(container);
        ensureOnboardingDetailsToggleListener();
        container.addEventListener('keydown', handleOnboardingKeydown);
        const slidesContainer = document.getElementById('onboarding-slides');
        if (slidesContainer) {
            slidesContainer.addEventListener('touchstart', handleOnboardingTouchStart, { passive: true });
            slidesContainer.addEventListener('touchend', handleOnboardingTouchEnd);
        }
        updateOnboardingSkipLabel();
        setTimeout(function() {
            const skipBtn = document.getElementById('onboarding-skip-btn');
            if (skipBtn) {
                skipBtn.focus({ preventScroll: true });
            } else {
                container.focus({ preventScroll: true });
            }
        }, 0);
    }

    function handleOnboardingTouchStart(event) {
        if (!event.changedTouches || !event.changedTouches.length) {
            return;
        }
        onboardingState.touchStartX = event.changedTouches[0].clientX;
    }

    function handleOnboardingTouchEnd(event) {
        if (!event.changedTouches || !event.changedTouches.length) {
            return;
        }
        const endX = event.changedTouches[0].clientX;
        const diff = endX - onboardingState.touchStartX;
        if (Math.abs(diff) < ONBOARDING_SWIPE_THRESHOLD) {
            return;
        }
        if (diff < 0) {
            nextOnboardingSlide();
        } else {
            previousOnboardingSlide();
        }
    }

    function handleOnboardingKeydown(event) {
        if (!onboardingState.initialized) {
            return;
        }
        if (event.key === 'ArrowRight') {
            event.preventDefault();
            nextOnboardingSlide();
        } else if (event.key === 'ArrowLeft') {
            event.preventDefault();
            previousOnboardingSlide();
        } else if (event.key === 'Escape') {
            event.preventDefault();
            skipOnboarding();
        }
    }

    function updateOnboardingLanguage() {
        updateOnboardingSkipLabel();
        if (!onboardingState.initialized) {
            return;
        }
        const filtered = getFilteredOnboardingSlides();
        let targetIndex = onboardingState.currentSlide;
        if (targetIndex >= filtered.length) {
            targetIndex = filtered.length ? filtered.length - 1 : 0;
        }
        renderOnboardingSlides(targetIndex);
    }

    window.skipOnboarding = skipOnboarding;
    window.nextOnboardingSlide = nextOnboardingSlide;
    window.completeOnboarding = completeOnboarding;
    window.toggleAgreeButton = toggleAgreeButton;

    // 現在の言語設定
    let currentLanguage = sessionStorage.getItem('language') || 'ja';
    window.currentLanguage = currentLanguage;
    const GOOGLE_FORM_URL = 'https://forms.gle/UB8kZHd4VHenmRUN6';
    let currentFeedbackData = null;
    let feedbackTriggerElement = null;

    // モーダル管理
    let currentModalPage = 'list';
    const modalPages = {
        'app-overview': {
            title: 'アプリ概要・運営者情報',
            content: {
                ja: `
                    <div class="info-section">
                        <h3>📱 アプリ概要（β版・限定公開）</h3>
                        <p>本アプリは現在、研究開発中のβ版（試験運用版）として運用されています。<br>
                        対象は、企業・行政関係者・薬剤師・登録販売者など、限られた専門関係者に限定されており、非営利かつ学術的な目的で公開しています。</p>
                        <p>独自のアルゴリズムと大規模言語モデルを組み合わせることで、ユーザーの症状・体調・生活状況に基づいて、一般用医薬品（OTC薬）をチャット形式で安全かつ柔軟に提案し、誰もが安心してセルフメディケーションを行える環境の実現を目指し、本研究ではその有効性を検証します。</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 開発背景</h3>
                        <p>少子高齢化や訪日外国人観光客の増加、ECサイトの普及により、セルフメディケーションの需要は年々高まっています。しかし、言語の壁や人材不足により、利用者が適切な医薬品を選べず、安全性が懸念されているのが現状です。</p>
                        <p>開発者自身がドラッグストア勤務の経験から、高齢者の聴力・理解力の差や外国人との言語障壁に直面したことをきっかけに、薬学的知識と大規模言語モデル(NLU)を融合したチャット型相談ツールとして本システムを構想しました。</p>
                        <p>本β版は、これらの課題解決に向けた実証的研究・検証を目的とした限定的運用です。</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 利用目的</h3>
                        <p><strong>【本β版の目的】</strong> 本β版は、AIを用いた医薬品相談のUI/UXや、本ツールに実装された独自の選定アルゴリズムの有効性について、開発にご協力いただく専門家の皆様からフィードバックをいただくことを目的としています。</p>
                        <p>本アプリは、利用者が自身の症状を正しく理解し、適切な一般用医薬品を安全に選択できるよう支援することを目的としています。<br>
                        チャット形式による対話を通じて、症状に合った市販薬の候補や受診の目安を提示し、セルフメディケーションの推進を図ります。</p>
                        <p>また、薬局来店前やオンライン購入前の参考情報としての活用を目的とし、医療機関への早期受診判断を助ける機能を持ちます。<br>
                        本アプリは医師・薬剤師の診断や指導を代替するものではなく、利用者の安全な判断を補助するための情報提供ツールです。</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>👥 対象者</h3>
                        <p><strong>【本β版の対象者（テスター）】</strong></p>
                        <ul>
                            <li>薬剤師・登録販売者などの医薬専門職</li>
                            <li>医療・行政・研究機関に所属する関係者</li>
                            <li>医薬品販売やセルフメディケーション支援に関心のある企業担当者</li>
                        </ul>
                        
                        <p style="margin-top: 20px;"><strong>【ユーザーヒアリングの実施について】</strong></p>
                        <p>本β版の専門家向けテストとは別に、研究の一環として、将来の想定利用者（一般消費者、訪日外国人の方など）の一部に対しても、別途ユーザーヒアリングのご協力を依頼する場合がございます。<br>
                        （これは本β版システムを一般公開するものではなく、あくまで開発プロセスにおけるインタビュー調査等を想定しています）</p>
                        
                        <p style="margin-top: 20px;"><strong>【将来的な（本実装時の）想定利用者】</strong><br>
                        （※本研究が実用化された場合、以下のような方々の支援を想定しています）</p>
                        <ul>
                            <li>どの薬を選べばよいかわからない一般消費者</li>
                            <li>忙しくて薬局に行けない人や過疎地域の住民</li>
                            <li>言語の壁で相談が難しい訪日外国人</li>
                            <li>高齢者や聴覚・理解力に個人差のある方</li>
                            <li>ECサイトやオンライン薬局で購入を検討する利用者</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 主な特徴</h3>
                        <ol>
                            <li><strong>自然なチャット形式での相談</strong><br>専門知識がなくても、会話形式で症状を入力するだけで薬の候補を提示します。</li>
                            <li><strong>AI × 薬学知識による安全性の担保</strong><br>医薬品データベース・薬学的知識・AIモデルを組み合わせ、誤情報を抑制した安全設計。</li>
                            <li><strong>受診勧奨システムの導入</strong><br>危険な症状や重篤な疾患が疑われる場合には、AIが自動的に医療機関受診を推奨します。</li>
                            <li><strong>多言語・多環境対応</strong><br>日本語・英語・中国語などの多言語対応を予定。<br>スマートフォン、タブレット、PCなど、あらゆる端末・環境（iOS / Android / Windows / macOS / Chrome / Safari など）から利用可能です。</li>
                            <li><strong>データの安全管理</strong><br>入力情報は匿名化され、薬提案以外の目的では利用しません。<br>ユーザーのプライバシーを最優先に設計されています。</li>
                        </ol>
                    </div>
                    
                    <div class="info-section">
                        <h3>💪 アプリの強み・差別化ポイント</h3>
                        <ul>
                            <li>AIと独自アルゴリズムの併用による安全性と柔軟性の両立</li>
                            <li>薬学的根拠に基づいた提案と自然言語理解の融合</li>
                            <li>現場課題（人手不足・言語の壁・情報格差）への直接的アプローチ</li>
                            <li>誰でも使いやすいUI設計による導入の容易さ</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>⚙️ 独自のアルゴリズム</h3>
                        <p>本アプリの心臓部となる「医薬品選定アルゴリズム」は、大規模言語モデルによる柔軟な言語理解と、薬効・禁忌・ユーザー属性情報・症状などの要素を統合的に評価する独自のアルゴリズムで構成されています。<br>
                        これにより、単なるAI応答ではなく、根拠に基づいた薬選びを実現しています。また、AIによる回答には常に「出典情報」や「注意喚起」を付与し、利用者が自ら判断できる設計としています。</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🧩 開発・運用体制（β版）</h3>
                        <ul>
                            <li><strong>運用形態：</strong>非営利・学術研究目的</li>
                            <li><strong>公開範囲：</strong>医療・行政・研究機関・薬剤師などの限られた関係者(一部ユーザーヒアリングを行う)</li>
                            <li><strong>目的：</strong>実証実験・検証・フィードバック収集</li>
                            <li><strong>バージョン管理：</strong>Git（GitHub）</li>
                            <li><strong>CI/CD：</strong>Google Cloud Build（GCP）</li>
                            <li><strong>ログ管理：</strong>JSONL形式の構造化ログ、リアルタイム監視機能</li>
                            <li><strong>運用監視：</strong>アクセス分析、パフォーマンス監視、セキュリティ監視</li>
                            <li><strong>将来的展開：</strong>一般公開に向けた改良検討</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🛠️ 開発環境・使用ツール</h3>
                        <ul>
                            <li><strong>バックエンド:</strong> Python 3.9+、<strong>FastAPI</strong>（本番のWeb/API・ASGI）、Jinja2（テンプレート）、MeCab（日本語形態素解析）</li>
                            <li><strong>AI/NLP:</strong> OpenAI API（GPT-5.4-mini・GPT-5.5 等）、ルールベースNLU（ハイブリッド推奨システム）</li>
                            <li><strong>翻訳API:</strong> DeepL API（多言語対応：日本語・英語・中国語・韓国語、高速翻訳）</li>
                            <li><strong>データベース:</strong> PostgreSQL（フィードバック永続化・セッション管理・マルチインスタンス対応）</li>
                            <li><strong>データ処理:</strong> Pandas、NumPy</li>
                            <li><strong>フロントエンド:</strong> HTML5, CSS3, JavaScript（ES6+）、バニラJavaScript（フレームワーク不使用）、レスポンシブデザイン</li>
                            <li><strong>デプロイ環境:</strong> <strong>Google Cloud</strong>（Cloud Run 等）、<strong>Gunicorn + uvicorn.workers.UvicornWorker</strong>（ASGIワーカー）</li>
                            <li><strong>監視・ログ:</strong> psutil, JSONL形式記録（構造化ログ）、アクセス分析、パフォーマンス監視</li>
                            <li><strong>バージョン管理:</strong> Git（GitHub）</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🚀 今後の展望</h3>
                        <p>今後は薬局・医療機関・自治体などとの連携を強化し、地域医療のデジタル支援基盤としての活用を目指します。</p>
                        <p>また、ECサイトとの統合やLINEとの連携など、利用者と販売者双方に価値を提供する拡張も予定しています。</p>
                        <p>最終的には、<strong>「誰もがどこでも安心して薬を選べる社会」</strong>を実現することが本アプリの目標です。</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>📚 医薬品データベース出典元</h3>
                        <ul>
                            <li><a href="http://www.fpmaj.gr.jp" target="_blank" rel="noopener noreferrer">日本製薬団体連合会</a> (http://www.fpmaj.gr.jp)</li>
                            <li><a href="https://www.japic.or.jp" target="_blank" rel="noopener noreferrer">日本医薬情報センター</a> (https://www.japic.or.jp)</li>
                            <li><a href="https://www.pmda.go.jp" target="_blank" rel="noopener noreferrer">医薬品医療機器総合機構</a> (https://www.pmda.go.jp)</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎨 使用画像の著作権</h3>
                        <p>本アプリで使用しているイラストの著作権は、<strong><a href="https://soco-st.com/" target="_blank" rel="noopener noreferrer">ソコスト(運営者個人)</a></strong>、<strong><a href="https://tegakisozai.com" target="_blank" rel="noopener noreferrer">てがきっず</a></strong>、および<strong><a href="https://shigureni.com/" target="_blank" rel="noopener noreferrer">shigureni</a></strong>に帰属します。</p>
                    </div>
                    
                    <div class="warning-box">
                        <h4>⚠️ 重要な注意事項</h4>
                        <ul style="margin-top: 10px;">
                            <li>本アプリはβ版の研究・検証目的であり、医療行為・商用利用を目的としていません。</li>
                            <li>提供する内容は医療アドバイスではなく、情報提供に限られます。</li>
                            <li>医薬品の使用に際しては、必ず薬剤師または医師にご相談ください。</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>📮 お問い合わせ・試験運用</h3>
                        <p>本ツールは研究・検証目的のβ版（試験運用）です。運営者の氏名・所属など個人を特定できる情報は開示していません。</p>
                        
                        <div class="contact-info">
                            <h4>お問い合わせ</h4>
                            <p><strong>E-mail：</strong> weary-scoots.7y@icloud.com</p>
                            <p><strong>不具合・お問い合わせフォーム：</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>技術情報</h4>
                            <p><strong>開発言語・技術：</strong> Python 3.9+ / FastAPI（本番ASGI）/ MeCab / OpenAI API（GPT-5.4-mini・GPT-5.5 等）/ DeepL API / PostgreSQL / Pandas / NumPy / HTML5 / CSS3 / JavaScript（ES6+）</p>
                            <p><strong>開発リポジトリ：</strong> <a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></p>
                            <p><strong>デプロイ環境：</strong> Google Cloud（Cloud Run 等）/ Gunicorn + UvicornWorker（ASGI）</p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>公開目的</h4>
                            <p>一般用医薬品の選定支援、安全でわかりやすい薬選びを促すこと</p>
                        </div>
                    </div>
                `,
                en: `
                    <div class="info-section">
                        <h3>📱 App Overview</h3>
                        <p>This app is an AI-assisted pharmaceutical consultation tool that recommends over-the-counter (OTC) medicines in a chat format based on users' symptoms, physical condition, and lifestyle.</p>
                        <p>By combining proprietary algorithms with large language models, we aim to safely and flexibly recommend appropriate over-the-counter medicines for symptoms, creating an environment where everyone can practice self-medication with confidence.</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 Development Background</h3>
                        <p>With aging population, increasing foreign tourists, and the spread of e-commerce sites, the demand for self-medication is growing year by year. However, language barriers and staff shortages prevent users from selecting appropriate medicines, raising safety concerns. Having worked at a drugstore myself, I have faced challenges with elderly people's varying hearing and comprehension abilities and language barriers for foreigners. To solve these issues, I developed a unique chat-based consultation tool that combines large language models with pharmaceutical knowledge.</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 Purpose</h3>
                        <p>This app aims to help users correctly understand their symptoms and safely select appropriate over-the-counter medicines.</p>
                        <p>Through chat-based dialogue, we present over-the-counter medicine candidates and consultation guidelines for symptoms to promote self-medication.</p>
                        <p>It is also designed to be used as reference information before visiting pharmacies or making online purchases, and plays a role in helping with early medical consultation decisions.</p>
                        <p>This app does not replace diagnosis or guidance by doctors or pharmacists, but is positioned as a tool to assist users in making safe decisions.</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>👥 Target Users</h3>
                        <ul>
                            <li>General consumers who don't know which medicine to choose</li>
                            <li>People who are too busy to visit pharmacies or residents of remote areas</li>
                            <li>Foreign visitors who have difficulty consulting due to language barriers</li>
                            <li>Elderly people and those with varying hearing and comprehension abilities</li>
                            <li>Users considering purchases on e-commerce sites or online pharmacies</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 Key Features</h3>
                        <ol>
                            <li><strong>Natural Chat-based Consultation</strong><br>Even without specialized knowledge, simply input symptoms in conversation format to get medicine recommendations.</li>
                            <li><strong>Safety Assurance through AI × Pharmaceutical Knowledge</strong><br>Combines pharmaceutical databases, pharmaceutical knowledge, and AI models for safe design that suppresses misinformation.</li>
                            <li><strong>Medical Consultation Recommendation System</strong><br>When dangerous symptoms or serious diseases are suspected, AI automatically recommends medical consultation.</li>
                            <li><strong>Multi-language and Multi-environment Support</strong><br>Planned support for Japanese, English, Chinese, and other languages.<br>Available on smartphones, tablets, PCs, and all devices and environments (iOS/Android/Windows/macOS/Chrome/Safari, etc.).</li>
                            <li><strong>Secure Data Management</strong><br>Input information is anonymized and not used for purposes other than medicine recommendations.<br>User privacy is the top priority in design.</li>
                        </ol>
                    </div>
                    
                    <div class="info-section">
                        <h3>💪 App Strengths & Differentiators</h3>
                        <ul>
                            <li>Balance of safety and flexibility through combined use of AI and proprietary algorithms</li>
                            <li>Fusion of evidence-based recommendations and natural language understanding (LLM) dialogue capabilities</li>
                            <li>Direct solution to on-site challenges such as staff shortages, language barriers, and information gaps</li>
                            <li>Operability that anyone can use without confusion through simple UI design and easy introduction</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>⚙️ Proprietary Algorithm</h3>
                        <p>The "Medicine Selection Algorithm," which is the heart of this app, consists of a proprietary algorithm that flexibly understands language through large language models and comprehensively evaluates elements such as drug efficacy, contraindications, user attribute information, and symptoms.</p>
                        <p>This enables evidence-based medicine selection rather than simple AI responses. AI responses always include "source information" and "warnings" to allow users to make their own judgments.</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🛠️ Development Environment & Tools</h3>
                        <ul>
                            <li><strong>Backend:</strong> Python 3.9+, <strong>FastAPI</strong> (production web/API, ASGI), Jinja2 (templates), MeCab (Japanese morphological analysis)</li>
                            <li><strong>AI/NLP:</strong> OpenAI API (GPT-5.4-mini, GPT-5.5, etc.), rule-based NLU (hybrid recommendation system)</li>
                            <li><strong>Translation API:</strong> DeepL API (Multi-language support: Japanese, English, Chinese, Korean, high-speed translation)</li>
                            <li><strong>Database:</strong> PostgreSQL (Feedback persistence, session management, multi-instance support)</li>
                            <li><strong>Data Processing:</strong> Pandas, NumPy</li>
                            <li><strong>Frontend:</strong> HTML5, CSS3, JavaScript (ES6+), Vanilla JavaScript (no framework), Responsive Design</li>
                            <li><strong>Deployment:</strong> <strong>Google Cloud</strong> (e.g. Cloud Run); <strong>Gunicorn + uvicorn.workers.UvicornWorker</strong> (ASGI workers)</li>
                            <li><strong>Monitoring & Logging:</strong> psutil, JSONL format (structured logs), access analysis, performance monitoring</li>
                            <li><strong>Version Control:</strong> Git (GitHub)</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🚀 Future Outlook</h3>
                        <p>We aim to strengthen collaboration with pharmacies, medical institutions, and local governments to utilize this as a digital support platform for regional healthcare.</p>
                        <p>We also plan expansions such as e-commerce site integration and medication guidance support functions to provide value to both users and sellers.</p>
                        <p>Ultimately, the goal of this app is to realize a society where "everyone can safely choose medicines anywhere."</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>📚 Pharmaceutical Database Sources</h3>
                        <p>The pharmaceutical information used in this app references databases from the following public institutions:</p>
                        <ul>
                            <li><a href="http://www.fpmaj.gr.jp" target="_blank" rel="noopener noreferrer">Japan Pharmaceutical Manufacturers Association</a> (http://www.fpmaj.gr.jp)</li>
                            <li><a href="https://www.japic.or.jp" target="_blank" rel="noopener noreferrer">Japan Pharmaceutical Information Center (JAPIC)</a> (https://www.japic.or.jp)</li>
                            <li><a href="https://www.pmda.go.jp" target="_blank" rel="noopener noreferrer">Pharmaceuticals and Medical Devices Agency (PMDA)</a> (https://www.pmda.go.jp)</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎨 Image Copyright</h3>
                        <p>The copyright of illustrations used in this app belongs to <strong><a href="https://soco-st.com/" target="_blank" rel="noopener noreferrer">Sofukore (Individual Operator)</a></strong>, <strong><a href="https://tegakisozai.com" target="_blank" rel="noopener noreferrer">Tegakiz (てがきっず)</a></strong>, and <strong><a href="https://shigureni.com/" target="_blank" rel="noopener noreferrer">shigureni</a></strong>.</p>
                    </div>
                    
                    <div class="warning-box">
                        <strong>⚠️ Important Notice</strong><br>
                        This app is for informational purposes only and is not medical advice. Please consult with a pharmacist or doctor when using medicines.
                    </div>
                    
                    <div class="info-section">
                        <h3>📮 Contact & Beta Operation</h3>
                        <p>This tool is a beta version for research and validation. We do not disclose personally identifiable operator details such as name or affiliation.</p>
                        
                        <div class="contact-info">
                            <h4>Contact</h4>
                            <p><strong>Contact Email:</strong> weary-scoots.7y@icloud.com</p>
                            <p><strong>Bug Report & Inquiry Form:</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>Technical Information</h4>
                            <p><strong>Development Languages & Technologies:</strong> Python 3.9+ / FastAPI (production ASGI) / MeCab (Japanese morphological analysis) / OpenAI API (GPT-5.4-mini, GPT-5.5, etc.) / DeepL API / PostgreSQL / Pandas / NumPy / HTML5 / CSS3 / JavaScript (ES6+)</p>
                            <p><strong>Development Repository:</strong> <a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></p>
                            <p><strong>Deployment:</strong> Google Cloud (e.g. Cloud Run) / Gunicorn + UvicornWorker (ASGI)</p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>Publication Purpose</h4>
                            <p>To support over-the-counter medicine selection and promote safe and easy medicine selection</p>
                        </div>
                    </div>
                `,
                ko: `
                    <div class="info-section">
                        <h3>📱 앱 개요</h3>
                        <p>이 앱은 사용자의 증상, 체조건, 생활 상황을 바탕으로 일반의약품(OTC 약품)을 채팅 형태로 제안하는 AI 지원 의약품 상담 도구입니다.</p>
                        <p>독자적인 알고리즘과 대규모 언어 모델을 결합하여 증상에 적합한 일반의약품을 안전하고 유연하게 제안하며, 누구나 안심하고 셀프메디케이션을 할 수 있는 환경 구현을 목표로 합니다.</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 개발 배경</h3>
                        <p>저출산 고령화와 방일 외국인 관광객 증가, EC 사이트 보급으로 셀프메디케이션 수요가 해마다 증가하고 있습니다. 하지만 언어의 벽과 인력 부족으로 이용자가 적절한 의약품을 선택하지 못하고 안전성에 대한 우려가 현재 상황입니다. 저도 드럭스토어에서 근무하며 고령자의 청력·이해력 차이와 외국인의 언어 장벽을 직면했습니다. 이러한 과제를 해결하기 위해 대규모 언어 모델과 약학 지식을 결합한 독자적인 채팅형 상담 도구를 개발했습니다.</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 이용 목적</h3>
                        <p>이 앱은 이용자가 자신의 증상을 올바르게 이해하고 적절한 일반의약품을 안전하게 선택할 수 있도록 지원하는 것을 목적으로 합니다.</p>
                        <p>채팅 형태의 대화를 통해 증상에 맞는 일반의약품 후보나 진료 기준을 제시하여 셀프메디케이션 촉진을 도모합니다.</p>
                        <p>또한 약국 방문 전이나 온라인 구매 전 참고 정보로 활용할 수 있도록 설계되어 있으며, 의료기관 조기 진료 판단을 돕는 역할도 담당합니다.</p>
                        <p>이 앱은 의사·약사진의 진단이나 지도를 대체하는 것이 아니라, 이용자가 안전하게 판단할 수 있는 환경을 보조하는 도구로 위치하고 있습니다.</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>👥 대상자</h3>
                        <ul>
                            <li>어떤 약을 선택해야 할지 모르는 일반 소비자</li>
                            <li>바빠서 약국에 갈 수 없는 사람이나 과소지역 주민</li>
                            <li>언어의 벽으로 상담이 어려운 방일 외국인</li>
                            <li>고령자나 청각·이해력에 개인차가 있는 분</li>
                            <li>EC 사이트나 온라인 약국에서 구매를 검토하는 이용자</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 주요 특징</h3>
                        <ol>
                            <li><strong>자연스러운 채팅 형태의 상담</strong><br>전문 지식이 없어도 대화 형태로 증상을 입력하기만 하면 약 후보를 제시합니다.</li>
                            <li><strong>AI × 약학 지식에 의한 안전성 보장</strong><br>의약품 데이터베이스·약학 지식·AI 모델을 결합하여 오정보를 억제한 안전 설계.</li>
                            <li><strong>진료 권장 시스템 도입</strong><br>위험한 증상이나 중증 질환이 의심되는 경우 AI가 자동으로 의료기관 진료를 권장합니다.</li>
                            <li><strong>다국어·다환경 대응</strong><br>일본어·영어·중국어 등의 다국어 대응을 예정.<br>스마트폰, 태블릿, PC 등 모든 단말·환경(iOS/Android/Windows/macOS/Chrome/Safari 등)에서 이용 가능합니다.</li>
                            <li><strong>데이터의 안전 관리</strong><br>입력 정보는 익명화되어 약 제안 외의 목적으로는 이용하지 않습니다.<br>이용자의 프라이버시를 최우선으로 설계되어 있습니다.</li>
                        </ol>
                    </div>
                    
                    <div class="info-section">
                        <h3>💪 앱의 강점·차별화 포인트</h3>
                        <ul>
                            <li>AI와 독자 알고리즘의 병용에 의한 안전성과 유연성의 양립</li>
                            <li>약학적 근거에 기반한 제안과 자연어 이해(LLM)의 대화력 융합</li>
                            <li>인력 부족·언어의 벽·정보 격차 등 현장에서 현저화되는 과제를 직접 해결</li>
                            <li>UI 설계의 간결함·도입의 용이함에 의해 누구나 혼란 없이 이용할 수 있는 조작성</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>⚙️ 독자적인 알고리즘</h3>
                        <p>이 앱의 심장부가 되는 "의약품 선정 알고리즘"은 대규모 언어 모델에 의한 유연한 언어 이해와 약효·금기·이용자 속성 정보·증상 등의 요소를 통합적으로 평가하는 독자적인 알고리즘으로 구성되어 있습니다.</p>
                        <p>이에 의해 단순한 AI 응답이 아닌 근거에 기반한 약 선택을 실현하고 있습니다. 또한 AI에 의한 답변에는 항상 "출전 정보"나 "주의 환기"를 부여하여 이용자가 스스로 판단할 수 있는 설계로 하고 있습니다.</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🛠️ 개발 환경·사용 도구</h3>
                        <ul>
                            <li><strong>백엔드:</strong> Python 3.9+, <strong>FastAPI</strong>(프로덕션 Web/API·ASGI), Jinja2(템플릿), MeCab(일본어 형태소)</li>
                            <li><strong>AI/NLP:</strong> OpenAI API(GPT-5.4-mini, GPT-5.5 등), 룰 베이스 NLU(하이브리드 추천 시스템)</li>
                            <li><strong>번역 API:</strong> DeepL API(다국어 지원: 일본어·영어·중국어·한국어, 고속 번역)</li>
                            <li><strong>데이터베이스:</strong> PostgreSQL(피드백 영속화·세션 관리·멀티 인스턴스 지원)</li>
                            <li><strong>데이터 처리:</strong> Pandas, NumPy</li>
                            <li><strong>프론트엔드:</strong> HTML5, CSS3, JavaScript(ES6+), 바닐라 JavaScript(프레임워크 미사용), 반응형 디자인</li>
                            <li><strong>배포 환경:</strong> <strong>Google Cloud</strong>(Cloud Run 등), <strong>Gunicorn + uvicorn.workers.UvicornWorker</strong>(ASGI 워커)</li>
                            <li><strong>모니터링·로그:</strong> psutil, JSONL 형태 기록(구조화 로그), 액세스 분석, 성능 모니터링</li>
                            <li><strong>버전 관리:</strong> Git(GitHub)</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🚀 향후 전망</h3>
                        <p>향후 약국·의료기관·자치단체 등과의 연계를 강화하여 지역 의료의 디지털 지원 기반으로서의 활용을 목표로 합니다.</p>
                        <p>또한 EC 사이트와의 통합이나 복용 지도 지원 기능 등 이용자와 판매자 양쪽에 가치를 제공하는 확장도 예정하고 있습니다.</p>
                        <p>궁극적으로는 "누구나 어디서나 안심하고 약을 선택할 수 있는 사회"를 실현하는 것이 이 앱의 목표입니다.</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>📚 의약품 데이터베이스 출전원</h3>
                        <p>이 앱에서 사용하는 의약품 정보는 다음 공공 기관의 데이터베이스를 참조하고 있습니다:</p>
                        <ul>
                            <li><a href="http://www.fpmaj.gr.jp" target="_blank" rel="noopener noreferrer">일본제약단체연합회</a> (http://www.fpmaj.gr.jp)</li>
                            <li><a href="https://www.japic.or.jp" target="_blank" rel="noopener noreferrer">(일반재단법인)일본의약정보센터</a> (https://www.japic.or.jp)</li>
                            <li><a href="https://www.pmda.go.jp" target="_blank" rel="noopener noreferrer">(독립행정법인)의약품의료기기종합기구</a> (https://www.pmda.go.jp)</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎨 사용 이미지 저작권</h3>
                        <p>이 앱에서 사용하는 일러스트의 저작권은 <strong><a href="https://soco-st.com/" target="_blank" rel="noopener noreferrer">소후코레(운영자 개인)</a></strong>, <strong><a href="https://tegakisozai.com" target="_blank" rel="noopener noreferrer">테가키즈(てがきっず)</a></strong>, 및 <strong><a href="https://shigureni.com/" target="_blank" rel="noopener noreferrer">shigureni</a></strong>에 귀속됩니다.</p>
                    </div>
                    
                    <div class="warning-box">
                        <strong>⚠️ 중요한 주의사항</strong><br>
                        이 앱은 정보 제공만을 목적으로 하며 의료 조언이 아닙니다. 의약품 사용 시에는 반드시 약사 또는 의사에게 상담하세요.
                    </div>
                    
                    <div class="info-section">
                        <h3>📮 문의·시험 운용</h3>
                        <p>본 도구는 연구·검증 목적의 β판(시험 운용)입니다. 운영자의 성명·소속 등 개인을 특정할 수 있는 정보는 공개하지 않습니다.</p>
                        
                        <div class="contact-info">
                            <h4>문의</h4>
                            <p><strong>연락처 메일:</strong> weary-scoots.7y@icloud.com</p>
                            <p><strong>불구·문의 폼:</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>기술 정보</h4>
                            <p><strong>개발 언어·기술:</strong> Python 3.9+ / FastAPI(프로덕션 ASGI) / MeCab(일본어 형태소) / OpenAI API(GPT-5.4-mini, GPT-5.5 등) / DeepL API / PostgreSQL / Pandas / NumPy / HTML5 / CSS3 / JavaScript (ES6+)</p>
                            <p><strong>개발 리포지토리:</strong> <a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></p>
                            <p><strong>배포 환경:</strong> Google Cloud(Cloud Run 등) / Gunicorn + UvicornWorker(ASGI)</p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>공개 목적</h4>
                            <p>일반의약품 선정 지원, 안전하고 이해하기 쉬운 약 선택을 촉진</p>
                        </div>
                    </div>
                `,
                zh: `
                    <div class="info-section">
                        <h3>📱 应用概述</h3>
                        <p>本应用是基于用户症状、身体状况、生活情况，以聊天形式推荐非处方药（OTC药品）的AI辅助药品咨询工具。</p>
                        <p>通过结合独创算法和大规模语言模型，安全灵活地推荐适合症状的非处方药，旨在实现任何人都能安心进行自我药疗的环境。</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 开发背景</h3>
                        <p>随着少子老龄化、访日外国游客增加、电商网站普及，自我药疗需求逐年增长。然而，语言障碍和人员不足导致用户无法选择适当的药品，安全性令人担忧。我本人也在药店工作，面临老年人听力理解力差异和外国人语言障碍。为了解决这些课题，开发了结合大规模语言模型和药学知识的独创聊天式咨询工具。</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 使用目的</h3>
                        <p>本应用旨在帮助用户正确理解自身症状，安全选择适当的非处方药。</p>
                        <p>通过聊天形式对话，提供适合症状的非处方药候选和就诊标准，促进自我药疗。</p>
                        <p>同时设计为可在药店访问前或在线购买前作为参考信息使用，也承担帮助医疗机构早期就诊判断的作用。</p>
                        <p>本应用不替代医生·药师的诊断或指导，而是定位为辅助用户安全判断环境的工具。</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>👥 目标用户</h3>
                        <ul>
                            <li>不知道选择哪种药品的一般消费者</li>
                            <li>忙碌无法去药店的人或偏远地区居民</li>
                            <li>因语言障碍难以咨询的访日外国人</li>
                            <li>老年人和听力理解力存在个人差异的人</li>
                            <li>考虑在电商网站或在线药店购买的用户</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎯 主要特点</h3>
                        <ol>
                            <li><strong>自然聊天形式咨询</strong><br>即使没有专业知识，只需以对话形式输入症状即可提供药品候选。</li>
                            <li><strong>AI × 药学知识保障安全性</strong><br>结合药品数据库·药学知识·AI模型，抑制错误信息的安全设计。</li>
                            <li><strong>引入就诊推荐系统</strong><br>当怀疑危险症状或严重疾病时，AI自动推荐医疗机构就诊。</li>
                            <li><strong>多语言·多环境对应</strong><br>计划支持日语·英语·中文等多语言。<br>可在智能手机、平板、PC等所有终端·环境（iOS/Android/Windows/macOS/Chrome/Safari等）使用。</li>
                            <li><strong>数据安全管理</strong><br>输入信息匿名化，除药品推荐外不用于其他目的。<br>用户隐私优先设计。</li>
                        </ol>
                    </div>
                    
                    <div class="info-section">
                        <h3>💪 应用优势·差异化要点</h3>
                        <ul>
                            <li>通过AI和独创算法并用，实现安全性和灵活性的平衡</li>
                            <li>基于药学依据的推荐与自然语言理解（LLM）对话能力融合</li>
                            <li>直接解决现场显现的人员不足·语言障碍·信息差距等课题</li>
                            <li>通过UI设计简洁·导入容易，实现任何人都能无困惑使用的操作性</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>⚙️ 独创算法</h3>
                        <p>作为本应用核心的"药品选择算法"，由通过大规模语言模型灵活理解语言，综合评估药效·禁忌·用户属性信息·症状等要素的独创算法构成。</p>
                        <p>由此实现基于依据的药品选择而非简单AI回答。同时AI回答始终附加"出处信息"和"注意提醒"，让用户能够自主判断。</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>🛠️ 开发环境·使用工具</h3>
                        <ul>
                            <li><strong>后端:</strong> Python 3.9+、<strong>FastAPI</strong>（生产环境 Web/API、ASGI）、Jinja2（模板）、MeCab（日语形态素解析）</li>
                            <li><strong>AI/NLP:</strong> OpenAI API（GPT-5.4-mini、GPT-5.5 等）、规则基础 NLU（混合推荐系统）</li>
                            <li><strong>翻译API:</strong> DeepL API（多语言支持：日语·英语·中文·韩语、高速翻译）</li>
                            <li><strong>数据库:</strong> PostgreSQL（反馈持久化·会话管理·多实例支持）</li>
                            <li><strong>数据处理:</strong> Pandas、NumPy</li>
                            <li><strong>前端:</strong> HTML5、CSS3、JavaScript（ES6+）、纯 JavaScript（无框架）、响应式设计</li>
                            <li><strong>部署环境:</strong> <strong>Google Cloud</strong>（Cloud Run 等）、<strong>Gunicorn + uvicorn.workers.UvicornWorker</strong>（ASGI 工作进程）</li>
                            <li><strong>监控·日志:</strong> psutil、JSONL 格式记录（结构化日志）、访问分析、性能监控</li>
                            <li><strong>版本管理:</strong> Git（GitHub）</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🚀 未来展望</h3>
                        <p>今后将加强与药店·医疗机构·自治体等的合作，作为地区医疗数字支持平台活用。</p>
                        <p>同时计划电商网站整合、用药指导支持功能等为用户和销售者双方提供价值的扩展。</p>
                        <p>最终目标是实现"任何人都能安心选择药品的社会"。</p>
                    </div>
                    
                    <div class="info-section">
                        <h3>📚 药品数据库出处</h3>
                        <p>本应用使用的药品信息参考以下公共机构数据库：</p>
                        <ul>
                            <li><a href="http://www.fpmaj.gr.jp" target="_blank" rel="noopener noreferrer">日本制药团体联合会</a> (http://www.fpmaj.gr.jp)</li>
                            <li><a href="https://www.japic.or.jp" target="_blank" rel="noopener noreferrer">(一般财团法人)日本医药信息中心</a> (https://www.japic.or.jp)</li>
                            <li><a href="https://www.pmda.go.jp" target="_blank" rel="noopener noreferrer">(独立行政法人)药品医疗器械综合机构</a> (https://www.pmda.go.jp)</li>
                        </ul>
                    </div>
                    
                    <div class="info-section">
                        <h3>🎨 使用图像版权</h3>
                        <p>本应用使用的插图的版权归<strong><a href="https://soco-st.com/" target="_blank" rel="noopener noreferrer">ソコスト(运营者个人)</a></strong>、<strong><a href="https://tegakisozai.com" target="_blank" rel="noopener noreferrer">てがきっず</a></strong>和<strong><a href="https://shigureni.com/" target="_blank" rel="noopener noreferrer">shigureni</a></strong>所有。</p>
                    </div>
                    
                    <div class="warning-box">
                        <strong>⚠️ 重要注意事项</strong><br>
                        本应用仅用于信息提供，非医疗建议。使用药品时请务必咨询药师或医生。
                    </div>
                    
                    <div class="info-section">
                        <h3>📮 联系与试运行</h3>
                        <p>本工具为研究·验证目的的β版（试运行）。不公开运营者姓名、所属等可识别个人的信息。</p>
                        
                        <div class="contact-info">
                            <h4>联系方式</h4>
                            <p><strong>联系邮箱：</strong> weary-scoots.7y@icloud.com</p>
                            <p><strong>故障·咨询表单：</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>技术信息</h4>
                            <p><strong>开发语言·技术：</strong> Python 3.9+ / FastAPI（生产 ASGI）/ MeCab（日语形态素解析）/ OpenAI API（GPT-5.4-mini、GPT-5.5 等）/ DeepL API / PostgreSQL / Pandas / NumPy / HTML5 / CSS3 / JavaScript (ES6+)</p>
                            <p><strong>开发仓库：</strong> <a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></p>
                            <p><strong>部署环境：</strong> Google Cloud（Cloud Run 等）/ Gunicorn + UvicornWorker（ASGI）</p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>公开目的</h4>
                            <p>支持非处方药选择，促进安全易懂的药品选择</p>
                        </div>
                    </div>
                `
            }
        },
        
        usage: {
            title: '使い方',
            content: {
                ja: `
                    <div class="info-section">
                        <h3>📖 使い方ガイド</h3>
                        <p>「チャット型医薬品相談ツール」のご利用ありがとうございます。このガイドでは、アプリの詳しい使い方と機能についてご説明します。</p>
                        
                        <div class="info-section">
                            <h4 style="color: #4CAF50; border-bottom: 2px solid #4CAF50; padding-bottom: 8px; margin-bottom: 20px;">1. 基本的な使い方</h4>
                            
                            <h5>① 症状を入力する</h5>
                            <p>画面下の入力欄に、「頭が痛い」「咳が止まらない」など、お困りの症状を具体的にお話しください。</p>
                            <p>🎤 マイクアイコンをタップすると、音声での入力も可能です。</p>
                            
                            <h5>② AIの回答を確認する</h5>
                            <p>症状を送信すると、AIが分析結果を返します。</p>
                            <ul>
                                <li><strong>おすすめの市販薬候補:</strong> 最大3件の候補を表示します。</li>
                                <li><strong>成分・効能:</strong> 各候補の詳しい情報を確認できます。</li>
                                <li><strong>注意点と受診の目安:</strong> 安全にご利用いただくための情報や、医療機関の受診を推奨する基準をご案内します。</li>
                            </ul>
                            
                            <h5>③ さらに詳しく相談する</h5>
                            <p>AIがより詳しい情報を必要とする場合（例：腹痛や頭痛など、原因が多岐にわたる場合）は、AIから追加の質問をすることがあります。</p>
                            <p>また、AIの回答に対して、あなたが疑問に思うことをそのままチャットで聞き返すこともできます。</p>
                        </div>
                        
                        <div class="info-section">
                            <h4 style="color: #4CAF50; border-bottom: 2px solid #4CAF50; padding-bottom: 8px; margin-bottom: 20px;">2. より便利に使うための機能</h4>
                            
                            <h5>👤 ユーザー情報の登録</h5>
                            <p>「ユーザー情報登録」ボタンから、年齢、性別、アレルギー、既往歴、妊娠・授乳の有無などをあらかじめ登録できます。</p>
                            <p>この情報を登録することで、AIがそれらを考慮した、より安全で精度の高い提案を行います。（入力後もメニューから更新可能です）</p>
                            
                            <h5>👨‍⚕️ 薬剤師への相談</h5>
                            <p>AIの回答だけでは不安な場合や、専門家（薬剤師）に直接判断を仰ぎたい場合は、「薬剤師要請」ボタンをご利用ください。</p>
                            <p>専門家（薬剤師）にチャット相談を引き継ぐことができます。</p>

                            <p>※「薬剤師要請」機能は、将来的な実装を想定したデモ機能であり、実際に薬剤師が応答・返信する体制は現在稼働しておりません。そのため、ボタンを押しても実際の相談員には繋がりませんことを、あらかじめご了承ください。</p>
                            
                            <h5>🌏 多言語対応</h5>
                            <p>画面左上の国旗ボタン（または言語ボタン）から、表示言語を切り替えられます。</p>
                            <p>日本語、英語、韓国語、中国語に対応しています。</p>
                            <p>※現在β版の制限により、AIの返信は日本語のみとなっています。</p>
                            
                            <h5>会話の管理</h5>
                            <ul>
                                <li><strong>🔄 新セッション:</strong> 現在の会話をリセットし、新しい相談を開始します。</li>
                                <li><strong>🗑️ 履歴クリア:</strong> 過去の会話履歴をすべて消去します。別の症状について相談を始める際にご利用ください。なお、ユーザー情報のリセットは行われません。</li>
                            </ul>
                        </div>
                        
                        <div class="info-section">
                            <h4 style="color: #4CAF50; border-bottom: 2px solid #4CAF50; padding-bottom: 8px; margin-bottom: 20px;">3. アプリの主な特徴</h4>
                            
                            <h5>🔬 ハイブリッド推奨と安全性</h5>
                            <p>このアプリは、独自のアルゴリズムと大規模言語モデルによる柔軟な回答を組み合わせ、最適な候補を自動で選択します。</p>
                            <p><strong>例：</strong>高熱がありインフルエンザが疑われる場合、アスピリン系の薬剤を除外するなど</p>
                            <p>また、ご登録いただいたユーザー情報（年齢制限、アレルギー、妊娠・授乳など）や、医薬品の相互作用（飲み合わせ）をAIが自動でチェックし、該当する場合は警告表示や医師の受診を促します。</p>
                            <p><strong>年齢に応じた薬の選択：</strong>年齢に応じた薬の選択も自動で行います。</p>
                            <p><strong>例：</strong>15歳未満のお子様には小児用の薬を優先的に提案します。</p>

                            <h5>📝 フィードバック</h5>
                            <p>AIの回答の品質向上のため、回答の評価（👍 👎 など）やフィードバックフォームからの改善要望にご協力をお願いいたします。</p>
                        </div>
                        
                        <div class="warning-box">
                            <h4>4. ⚠️ 安全に使うために（必ずお読みください）</h4>
                            
                            <h5>🚫 本ツールは医療行為ではありません</h5>
                            <p>本ツール（AIおよび薬剤師の回答を含む）は、診断、治療、または医療的アドバイスを行うものではありません。</p>
                            <p>提供する情報は、あくまで市販薬を選択する上での参考情報です。</p>
                            <p><strong>症状が重い、長引いている、または判断に迷う場合は、ご自身の判断で市販薬を使用せず、必ず医療機関（医師）の診察を受けてください。</strong></p>
                            
                            <h5>🆘 危機対応について</h5>
                            <p>深刻な精神的危機を示す表現をAIが検出した場合、本ツールは直ちに医薬品推奨を停止し、専門の相談窓口（公的機関など）の情報を案内し、薬剤師や医療機関への連絡を強く促します。</p>
                            
                            <h5>🔒 個人情報の管理</h5>
                            <p>ご登録いただいた個人情報は、推奨の品質向上と安全確認の目的のみに利用します。</p>
                            <p>個人情報の管理について、より詳しくは <a href="javascript:void(0);" onclick="closeInfoModal(); setTimeout(function(){openInfoModal(); showDetailPage('privacy');}, 100);" style="color: #4CAF50; text-decoration: underline; font-weight: bold;">ℹ️ ボタン内の「🔒 プライバシーポリシー」</a> をご確認ください。</p>
                        </div>
                        
                        <div class="info-section" style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #e0e0e0;">
                            <h4>💬 よくある質問（FAQ）</h4>
                            <p>ご不明な点がございましたら、<a href="javascript:void(0);" onclick="closeInfoModal(); setTimeout(function(){openInfoModal(); showDetailPage('faq');}, 100);" style="color: #4CAF50; text-decoration: underline; font-weight: bold;">こちら</a>からよくある質問をご確認ください。</p>
                        </div>
                    </div>
                `,
                en: `
                    <div class="info-section">
                        <h3>📖 How to Use the App</h3>
                        
                        <div class="info-section">
                            <h4>Step 1: Enter Your Symptoms</h4>
                            <p>Enter your symptoms in text or click the 🎤 button for voice input.</p>
                            <p>Examples: "I have a headache", "My cough won't stop", "I have a fever", etc.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>Step 2: Review AI Response</h4>
                            <p>The AI will suggest over-the-counter medicines suitable for your symptoms. Review the recommendation reasons, usage instructions, and side effect information for each medicine.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>Step 3: Request Pharmacist Consultation (If Needed)</h4>
                            <p>If you need more detailed information or professional consultation, click the 👨‍⚕️ button to consult directly with a pharmacist.</p>
                        </div>
                        
                        <div class="warning-box">
                            <strong>⚠️ Safety Precautions</strong>
                            <ul style="margin-top: 10px;">
                                <li>This app is for informational purposes only and is not medical advice</li>
                                <li>If symptoms are severe or require emergency care, seek medical attention immediately</li>
                                <li>Please consult with a pharmacist or doctor when using medicines</li>
                                <li>If you have allergies or chronic conditions, be sure to enter that information</li>
                                <li>If you are currently taking medications, consult with a pharmacist before combining them</li>
                            </ul>
                        </div>
                    </div>
                `,
                ko: `
                    <div class="info-section">
                        <h3>📖 앱 사용 방법</h3>
                        
                        <div class="info-section">
                            <h4>1단계: 증상 입력</h4>
                            <p>느끼는 증상을 텍스트로 입력하거나 🎤 버튼을 클릭하여 음성 입력하세요.</p>
                            <p>예: "머리가 아프다", "기침이 멈추지 않는다", "열이 있다" 등</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>2단계: AI 답변 확인</h4>
                            <p>AI가 증상에 적합한 일반의약품 후보를 제안합니다. 각 의약품의 권장 이유, 사용상 주의사항, 부작용 정보 등을 확인하세요.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>3단계: 약사 요청 (필요한 경우)</h4>
                            <p>더 자세히 알고 싶거나 더 전문적인 상담이 필요한 경우 👨‍⚕️ 버튼을 클릭하여 약사에게 직접 상담할 수 있습니다.</p>
                        </div>
                        
                        <div class="warning-box">
                            <strong>⚠️ 안전하게 이용하기 위한 주의사항</strong>
                            <ul style="margin-top: 10px;">
                                <li>본 앱은 정보 제공만을 목적으로 하며 의료 조언이 아닙니다</li>
                                <li>증상이 중증이거나 응급을 요하는 경우 신속히 의료기관을 방문하세요</li>
                                <li>의약품 사용 시에는 반드시 약사 또는 의사에게 상담하세요</li>
                                <li>알레르기나 기저질환이 있는 경우 반드시 그 정보를 입력하세요</li>
                                <li>현재 복용 중인 약이 있는 경우 병용 전에 약사에게 상담하세요</li>
                            </ul>
                        </div>
                    </div>
                `,
                zh: `
                    <div class="info-section">
                        <h3>📖 应用使用方法</h3>
                        
                        <div class="info-section">
                            <h4>步骤1: 输入症状</h4>
                            <p>用文本输入感受到的症状，或点击🎤按钮进行语音输入。</p>
                            <p>示例："头痛"、"咳嗽不停"、"发烧"等</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>步骤2: 查看AI回答</h4>
                            <p>AI会建议适合症状的非处方药候选。请确认各药品的推荐理由、使用注意事项、副作用信息等。</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>步骤3: 请求药师咨询（必要时）</h4>
                            <p>如需更详细信息或需要更专业的咨询，可点击👨‍⚕️按钮直接咨询药师。</p>
                        </div>
                        
                        <div class="warning-box">
                            <strong>⚠️ 安全使用的注意事项</strong>
                            <ul style="margin-top: 10px;">
                                <li>本应用仅用于信息提供，非医疗建议</li>
                                <li>症状严重或需要紧急处理时，请迅速前往医疗机构就诊</li>
                                <li>使用药品时请务必咨询药师或医生</li>
                                <li>如有过敏或既往症，请务必输入该信息</li>
                                <li>如正在服用其他药物，合并使用前请咨询药师</li>
                            </ul>
                        </div>
                    </div>
                `
            }
        },
        
        disclaimer: {
            title: '免責事項・利用規約',
            content: {
                ja: `
                    <div class="info-section">
                        <h3>🧾 免責事項・利用規約（β版）</h3>
                        
                        <h4>第1条（目的と適用範囲）</h4>
                        <p>本アプリ「チャット型医薬品相談ツール」（以下、「本アプリ」といいます。）は、一般用医薬品を症状に基づいて参考提示するシステムです。現在はテスター限定の試験運用（β版）として公開されており、正式な医療サービスではありません。本アプリを利用することにより、利用者は本規約に同意したものとみなします。</p>
                        
                        <h4>第2条（試験運用について）</h4>
                        <ol>
                            <li>本アプリは、動作確認・機能検証・改善提案を目的として、一部のテスターに限定公開しています。</li>
                            <li>本アプリは試験段階にあるため、表示内容の正確性・安全性・安定性について保証できません。</li>
                            <li>テスト期間中に収集された利用データは、サービス改善のために匿名的かつ統計的に利用されます。</li>
                        </ol>
                        
                        <h4>第3条（免責事項）</h4>
                        <ol>
                            <li>本アプリの情報は、あくまで一般的な参考情報であり、医師・薬剤師・登録販売者など専門家の判断を代替するものではありません。</li>
                            <li>利用者が本アプリの情報に基づいて行った行動や判断により生じた損害について、運営者は一切の責任を負いません。</li>
                            <li>本アプリの機能停止、障害、改変、削除等により利用者に不利益が生じても、運営者は責任を負いません。</li>
                        </ol>
                        
                        <h4>第4条（禁止事項）</h4>
                        <p>テスターは、次の行為を行ってはなりません。</p>
                        <ol>
                            <li>他者にURLを転送し、非許可の第三者に利用させる行為</li>
                            <li>不正アクセスやリバースエンジニアリング行為</li>
                            <li>本アプリの内容を外部に無断公開・転載する行為</li>
                            <li>虚偽の情報を入力する行為</li>
                            <li>本アプリを商業目的で不正利用する行為</li>
                            <li>本アプリの運営を妨げる行為</li>
                            <li>法令または公序良俗に反する行為</li>
                        </ol>
                        
                        <h4>第5条（試験内容の変更・終了）</h4>
                        <p>運営者は、事前通知なく本アプリの内容を変更・停止・終了することがあります。</p>
                        
                        <h4>第6条（知的財産権）</h4>
                        <p>本アプリに関する著作権、プログラム、デザインなどの知的財産権は、運営者または正当な権利者に帰属します。</p>
                        
                        <h4>第7条（連絡先）</h4>
                        <p>本アプリの不具合や問い合わせは、以下のフォームにてご連絡ください。</p>
                        <ul>
                            <li>不具合報告フォーム：<a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></li>
                            <li>運営者ホームページ：<a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></li>
                        </ul>
                        
                        <h4>第8条（準拠法・管轄）</h4>
                        <p>本規約の解釈および運営者とテスター間の紛争については、日本法を準拠法、同法に従って解釈されるものとします。本アプリに関して紛争が生じた場合には、運営者所在地を管轄する地方裁判所を第一審の専属的合意管轄裁判所とします。</p>
                    </div>
                `,
                en: `
                    <div class="info-section">
                        <h3>🧾 Disclaimer & Terms of Use (Beta Version)</h3>
                        
                        <h4>Article 1 (Purpose and Scope of Application)</h4>
                        <p>This app "Chat-based Medicine Consultation Tool" (hereinafter referred to as "this app") is a system that provides reference information for over-the-counter medicines based on symptoms. It is currently released as a limited beta test for testers only and is not an official medical service. By using this app, users are deemed to have agreed to these terms.</p>
                        
                        <h4>Article 2 (About Beta Testing)</h4>
                        <ol>
                            <li>This app is limited to a select group of testers for the purpose of operation verification, function testing, and improvement proposals.</li>
                            <li>Since this app is in the testing phase, we cannot guarantee the accuracy, safety, or stability of the displayed content.</li>
                            <li>Usage data collected during the testing period will be used anonymously and statistically for service improvement.</li>
                        </ol>
                        
                        <h4>Article 3 (Disclaimer)</h4>
                        <ol>
                            <li>The information in this app is for general reference only and does not replace the judgment of medical professionals such as doctors, pharmacists, or registered sellers.</li>
                            <li>The operator assumes no responsibility for any damages arising from actions or judgments made by users based on information from this app.</li>
                            <li>The operator is not responsible for any disadvantages to users due to app suspension, malfunctions, modifications, or deletion.</li>
                        </ol>
                        
                        <h4>Article 4 (Prohibited Activities)</h4>
                        <p>Testers must not engage in the following activities:</p>
                        <ol>
                            <li>Forwarding URLs to others and allowing unauthorized third parties to use the app</li>
                            <li>Unauthorized access or reverse engineering</li>
                            <li>Unauthorized publication or reproduction of app content externally</li>
                            <li>Inputting false information</li>
                            <li>Misusing the app for commercial purposes</li>
                            <li>Activities that interfere with app operation</li>
                            <li>Activities that violate laws or public order and morals</li>
                        </ol>
                        
                        <h4>Article 5 (Changes and Termination of Beta Content)</h4>
                        <p>The operator may change, suspend, or terminate the app content without prior notice.</p>
                        
                        <h4>Article 6 (Intellectual Property Rights)</h4>
                        <p>Intellectual property rights such as copyrights, programs, and designs related to this app belong to the operator or rightful owners.</p>
                        
                        <h4>Article 7 (Contact Information)</h4>
                        <p>Please contact us through the following form or email for app issues or inquiries:</p>
                        <ul>
                            <li>Bug Report Form: <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></li>
                            <li>Contact Email: weary-scoots.7y@icloud.com</li>
                            <li>Operator Homepage: <a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></li>
                        </ul>
                        
                        <h4>Article 8 (Governing Law and Jurisdiction)</h4>
                        <p>These terms shall be interpreted in accordance with Japanese law. Any disputes arising from this app shall be subject to the exclusive jurisdiction of the district court with jurisdiction over the operator's location as the court of first instance.</p>
                    </div>
                `,
                ko: `
                    <div class="info-section">
                        <h3>🧾 면책조항·이용약관 (시험운용판)</h3>
                        
                        <h4>제1조 (목적 및 적용범위)</h4>
                        <p>본 앱 "채팅형 의약품 상담 도구"(이하 "본 앱"이라 함)는 증상에 따라 일반의약품을 참고 제시하는 시스템입니다. 현재는 테스터 한정 시험운용(β판)으로 공개되어 있으며, 정식 의료 서비스가 아닙니다. 본 앱을 이용함으로써 이용자는 본 약관에 동의한 것으로 간주됩니다.</p>
                        
                        <h4>제2조 (시험운용에 대해)</h4>
                        <ol>
                            <li>본 앱은 동작 확인·기능 검증·개선 제안을 목적으로 일부 테스터에게 한정 공개하고 있습니다.</li>
                            <li>본 앱은 시험 단계에 있으므로 표시 내용의 정확성·안전성·안정성에 대해 보장할 수 없습니다.</li>
                            <li>테스트 기간 중 수집된 이용 데이터는 서비스 개선을 위해 익명적이고 통계적으로 이용됩니다.</li>
                        </ol>
                        
                        <h4>제3조 (면책사항)</h4>
                        <ol>
                            <li>본 앱의 정보는 어디까지나 일반적인 참고 정보이며, 의사·약사·등록판매자 등 전문가의 판단을 대체하는 것이 아닙니다.</li>
                            <li>이용자가 본 앱의 정보에 기반하여 행한 행동이나 판단으로 인해 발생한 손해에 대해 운영자는 일체의 책임을 지지 않습니다.</li>
                            <li>본 앱의 기능 정지, 장애, 개변, 삭제 등으로 이용자에게 불이익이 발생해도 운영자는 책임을 지지 않습니다.</li>
                        </ol>
                        
                        <h4>제4조 (금지사항)</h4>
                        <p>테스터는 다음 행위를 해서는 안 됩니다.</p>
                        <ol>
                            <li>타인에게 URL을 전송하여 비허가 제3자에게 이용시키는 행위</li>
                            <li>부정 접근이나 리버스 엔지니어링 행위</li>
                            <li>본 앱의 내용을 외부에 무단 공개·전재하는 행위</li>
                            <li>허위 정보를 입력하는 행위</li>
                            <li>본 앱을 상업 목적으로 부정 이용하는 행위</li>
                            <li>본 앱의 운영을 방해하는 행위</li>
                            <li>법령 또는 공서양속에 반하는 행위</li>
                        </ol>
                        
                        <h4>제5조 (시험 내용의 변경·종료)</h4>
                        <p>운영자는 사전 통지 없이 본 앱의 내용을 변경·중지·종료할 수 있습니다.</p>
                        
                        <h4>제6조 (지적재산권)</h4>
                        <p>본 앱에 관한 저작권, 프로그램, 디자인 등의 지적재산권은 운영자 또는 정당한 권리자에 귀속됩니다.</p>
                        
                        <h4>제7조 (연락처)</h4>
                        <p>본 앱의 불구나 문의는 다음 폼 또는 메일로 연락해 주세요.</p>
                        <ul>
                            <li>불구 신고 폼: <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></li>
                            <li>연락처 메일 주소: weary-scoots.7y@icloud.com</li>
                            <li>운영자 홈페이지: <a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></li>
                        </ul>
                        
                        <h4>제8조 (준거법·관할)</h4>
                        <p>본 약관의 해석 및 운영자와 테스터 간의 분쟁에 대해서는 일본법을 준거법으로 하여 동법에 따라 해석되는 것으로 합니다. 본 앱에 관해 분쟁이 발생한 경우에는 운영자 소재지를 관할하는 지방법원을 제1심의 전속적 합의 관할 법원으로 합니다.</p>
                    </div>
                `,
                zh: `
                    <div class="info-section">
                        <h3>🧾 免责声明和使用条款（测试版）</h3>
                        
                        <h4>第1条（目的和适用范围）</h4>
                        <p>本应用"聊天式药品咨询工具"（以下简称"本应用"）是基于症状提供非处方药参考信息的系统。目前作为测试者限定的测试运营（β版）公开，非正式医疗服务。使用本应用即视为用户同意本条款。</p>
                        
                        <h4>第2条（关于测试运营）</h4>
                        <ol>
                            <li>本应用为动作确认·功能验证·改进提案目的，限定向部分测试者公开。</li>
                            <li>本应用处于测试阶段，无法保证显示内容的准确性·安全性·稳定性。</li>
                            <li>测试期间收集的使用数据将匿名且统计性地用于服务改进。</li>
                        </ol>
                        
                        <h4>第3条（免责事项）</h4>
                        <ol>
                            <li>本应用信息仅为一般参考信息，不替代医生·药师·注册销售者等专家的判断。</li>
                            <li>用户基于本应用信息采取的行动或判断造成的损害，运营者不承担任何责任。</li>
                            <li>因本应用功能停止、故障、修改、删除等对用户造成不利影响，运营者不承担责任。</li>
                        </ol>
                        
                        <h4>第4条（禁止事项）</h4>
                        <p>测试者不得进行以下行为：</p>
                        <ol>
                            <li>向他人转发URL，让未授权第三方使用</li>
                            <li>非法访问或逆向工程行为</li>
                            <li>未经授权对外公开·转载本应用内容</li>
                            <li>输入虚假信息</li>
                            <li>为商业目的非法使用本应用</li>
                            <li>妨碍本应用运营的行为</li>
                            <li>违反法令或公序良俗的行为</li>
                        </ol>
                        
                        <h4>第5条（测试内容变更·终止）</h4>
                        <p>运营者可无事先通知变更·停止·终止本应用内容。</p>
                        
                        <h4>第6条（知识产权）</h4>
                        <p>本应用相关的著作权、程序、设计等知识产权归运营者或正当权利人所有。</p>
                        
                        <h4>第7条（联系方式）</h4>
                        <p>本应用故障或咨询请通过以下表单或邮件联系：</p>
                        <ul>
                            <li>故障报告表单：<a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></li>
                            <li>联系邮箱：weary-scoots.7y@icloud.com</li>
                            <li>运营者主页：<a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></li>
                        </ul>
                        
                        <h4>第8条（准据法·管辖）</h4>
                        <p>本条款解释及运营者与测试者间争议以日本法为准据法，按该法解释。本应用相关争议发生时，以运营者所在地管辖地方法院为第一审专属合意管辖法院。</p>
                    </div>
                `
            }
        },
        
        privacy: {
            title: 'プライバシーポリシー',
            content: {
                ja: `
                    <div class="info-section">
                        <h3>🔒 プライバシーポリシー（β版）</h3>
                        
                        <h4>第1条（基本方針）</h4>
                        <p>本アプリ「チャット型医薬品相談ツール」は、試験運用（βテスト）段階において、テスターから得られた情報を適切に取り扱い、個人情報保護法および関連法令を遵守します。テスターのプライバシーを尊重し、安全で信頼できる環境の提供に努めます。</p>
                        
                        <h4>第2条（取得する情報）</h4>
                        <p>本アプリでは、試験運用の目的で以下の情報を収集する場合があります。</p>
                        <ol>
                            <li>ユーザー入力情報（症状、年齢層、性別など）</li>
                            <li>利用履歴・アクセスログ・利用日時・エラー情報等</li>
                            <li>アンケートやフィードバックフォームへの回答内容</li>
                        </ol>
                        <p><strong>※いずれの情報も、氏名や住所など「個人を直接特定できる情報」は収集しません。</strong></p>
                        
                        <h4>第3条（利用目的）</h4>
                        <p>収集した情報は、次の目的に限り利用します。</p>
                        <ul>
                            <li>本アプリの精度向上・不具合修正・機能改善のため</li>
                            <li>テスト結果の分析および開発報告資料の作成のため</li>
                            <li>運営上必要な連絡（バグ報告、改善依頼など）のため</li>
                        </ul>
                        
                        <h4>第4条（第三者提供）</h4>
                        <p>運営者は、以下の場合を除き、取得情報を第三者に提供しません。</p>
                        <ul>
                            <li>法令に基づく場合</li>
                            <li>本人の明確な同意がある場合</li>
                        </ul>
                        
                        <h4>第5条（情報の管理と削除）</h4>
                        <p>取得情報は安全な環境で管理し、第三者が不正にアクセスできないよう適切な措置を講じます。</p>
                        <ol>
                            <li>取得情報は安全な環境で管理し、不正アクセス・漏洩・改ざん等が起こらないよう適切な技術的・組織的措置を講じます。</li>
                            <li>テスト期間終了後、個人を特定できる情報は速やかに削除または匿名化します。</li>
                        </ol>
                        
                        <h4>第6条（匿名加工情報の取り扱い）</h4>
                        <ol>
                            <li>運営者は、利用者から取得した情報のうち、個人を特定できないように加工した「匿名加工情報」を作成する場合があります。</li>
                            <li>匿名加工情報は、個人を特定できない形式で統計処理・サービス改善・学術的検討などの目的で利用することがあります。</li>
                            <li>匿名加工情報を第三者に提供する場合は、再識別できない形式を維持し、適切な安全管理措置を講じます。</li>
                            <li>匿名加工情報の作成および提供に関する方針が変更された場合には、本ポリシー内で速やかに公表します。</li>
                        </ol>
                        
                        <h4>第7条（テスターの権利）</h4>
                        <p>テスターは、自身に関する情報の開示・訂正・削除を運営者に請求できます。希望する場合は、以下の連絡先までお問い合わせください。</p>
                        <ul>
                            <li>運営者名：川嶋 宥翔（Kawashima Yuto）</li>
                            <li><strong>お問い合わせ：</strong> <a href="https://forms.gle/myzACX7eT59dkrLx8" target="_blank">https://forms.gle/myzACX7eT59dkrLx8</a></li>
                        </ul>
                        
                        <h4>第8条（改定）</h4>
                        <p>本ポリシーは、必要に応じて内容を変更する場合があります。改定後の内容は、本アプリ上に掲示された時点から効力を有します。</p>
                    </div>
                `,
                en: `
                    <div class="info-section">
                        <h3>🔒 Privacy Policy (Beta Version)</h3>
                        
                        <h4>Article 1 (Basic Policy)</h4>
                        <p>This app "Chat-based Medicine Consultation Tool" appropriately handles information obtained from testers during the beta testing phase, complying with the Personal Information Protection Act and related laws. We respect tester privacy and strive to provide a safe and trustworthy environment.</p>
                        
                        <h4>Article 2 (Information Collected)</h4>
                        <p>This app may collect the following information for beta testing purposes:</p>
                        <ol>
                            <li>User input information (symptoms, age group, gender, etc.)</li>
                            <li>Usage history, access logs, usage times, error information, etc.</li>
                            <li>Survey and feedback form responses</li>
                        </ol>
                        <p><strong>※We do not collect "personally identifiable information" such as names or addresses.</strong></p>
                        
                        <h4>Article 3 (Purpose of Use)</h4>
                        <p>Collected information is used only for the following purposes:</p>
                        <ul>
                            <li>To improve app accuracy, fix bugs, and enhance functionality</li>
                            <li>To analyze test results and create development reports</li>
                            <li>For necessary operational communications (bug reports, improvement requests, etc.)</li>
                        </ul>
                        
                        <h4>Article 4 (Third-Party Disclosure)</h4>
                        <p>The operator will not provide collected information to third parties except in the following cases:</p>
                        <ul>
                            <li>When required by law</li>
                            <li>When there is clear consent from the individual</li>
                        </ul>
                        
                        <h4>Article 5 (Information Management and Deletion)</h4>
                        <p>Collected information is managed in a secure environment with appropriate measures to prevent unauthorized access by third parties.</p>
                        <ol>
                            <li>We implement appropriate technical and organizational measures to manage collected information securely and prevent unauthorized access, leakage, or tampering.</li>
                            <li>After the testing period ends, personally identifiable information is promptly deleted or anonymized.</li>
                        </ol>
                        
                        <h4>Article 6 (Handling of Anonymized Information)</h4>
                        <ol>
                            <li>The operator may create "anonymized information" by processing information obtained from users so that individuals cannot be identified.</li>
                            <li>Anonymized information may be used for statistical processing, service improvement, academic research, and other purposes in a format that cannot identify individuals.</li>
                            <li>When providing anonymized information to third parties, we maintain a format that cannot be re-identified and implement appropriate security management measures.</li>
                            <li>When policies regarding the creation and provision of anonymized information change, we will promptly announce them within this policy.</li>
                        </ol>
                        
                        <h4>Article 7 (Tester Rights)</h4>
                        <p>Testers can request disclosure, correction, or deletion of their information from the operator. Please contact us at the following address if you wish to do so:</p>
                        <ul>
                            <li>Operator Name: Kawashima Yuto</li>
                            <li>Email Address: weary-scoots.7y@icloud.com</li>
                        </ul>
                        
                        <h4>Article 8 (Revisions)</h4>
                        <p>This policy may be revised as necessary. Revised content takes effect from the time it is posted on this app.</p>
                    </div>
                `,
                ko: `
                    <div class="info-section">
                        <h3>🔒 개인정보 취급방침 (시험운용판)</h3>
                        
                        <h4>제1조 (기본방침)</h4>
                        <p>본 앱 "채팅형 의약품 상담 도구"는 시험운용(β테스트) 단계에서 테스터로부터 얻은 정보를 적절히 취급하며, 개인정보보호법 및 관련 법령을 준수합니다. 테스터의 프라이버시를 존중하고 안전하고 신뢰할 수 있는 환경 제공에 노력합니다.</p>
                        
                        <h4>제2조 (수집하는 정보)</h4>
                        <p>본 앱에서는 시험운용 목적으로 다음 정보를 수집할 수 있습니다.</p>
                        <ol>
                            <li>사용자 입력 정보 (증상, 연령층, 성별 등)</li>
                            <li>이용 이력·접근 로그·이용 일시·오류 정보 등</li>
                            <li>설문이나 피드백 폼에 대한 답변 내용</li>
                        </ol>
                        <p><strong>※어떤 정보도 성명이나 주소 등 "개인을 직접 특정할 수 있는 정보"는 수집하지 않습니다.</strong></p>
                        
                        <h4>제3조 (이용 목적)</h4>
                        <p>수집한 정보는 다음 목적으로만 이용합니다.</p>
                        <ul>
                            <li>본 앱의 정확도 향상·불구 수정·기능 개선을 위해</li>
                            <li>테스트 결과 분석 및 개발 보고 자료 작성을 위해</li>
                            <li>운영상 필요한 연락 (버그 신고, 개선 요청 등)을 위해</li>
                        </ul>
                        
                        <h4>제4조 (제3자 제공)</h4>
                        <p>운영자는 다음 경우를 제외하고 수집 정보를 제3자에게 제공하지 않습니다.</p>
                        <ul>
                            <li>법령에 근거한 경우</li>
                            <li>본인의 명확한 동의가 있는 경우</li>
                        </ul>
                        
                        <h4>제5조 (정보의 관리와 삭제)</h4>
                        <p>수집 정보는 안전한 환경에서 관리하며, 제3자가 부정하게 접근할 수 없도록 적절한 조치를 취합니다.</p>
                        <ol>
                            <li>수집 정보는 안전한 환경에서 관리하며, 부정 접근·누설·변조 등이 일어나지 않도록 적절한 기술적·조직적 조치를 취합니다.</li>
                            <li>테스트 기간 종료 후, 개인을 특정할 수 있는 정보는 신속히 삭제하거나 익명화합니다.</li>
                        </ol>
                        
                        <h4>제6조 (익명가공정보의 취급)</h4>
                        <ol>
                            <li>운영자는 이용자로부터 얻은 정보 중 개인을 특정할 수 없도록 가공한 "익명가공정보"를 작성할 수 있습니다.</li>
                            <li>익명가공정보는 개인을 특정할 수 없는 형태로 통계 처리·서비스 개선·학술적 검토 등의 목적으로 이용할 수 있습니다.</li>
                            <li>익명가공정보를 제3자에게 제공하는 경우, 재식별할 수 없는 형태를 유지하고 적절한 안전 관리 조치를 취합니다.</li>
                            <li>익명가공정보의 작성 및 제공에 관한 방침이 변경된 경우에는 본 정책 내에서 신속히 공표합니다.</li>
                        </ol>
                        
                        <h4>제7조 (테스터의 권리)</h4>
                        <p>테스터는 자신에 관한 정보의 공개·정정·삭제를 운영자에게 요청할 수 있습니다. 희망하는 경우 다음 연락처로 문의해 주세요.</p>
                        <ul>
                            <li>운영자명: 가와시마 유토 (Kawashima Yuto)</li>
                            <li>메일 주소: weary-scoots.7y@icloud.com</li>
                        </ul>
                        
                        <h4>제8조 (개정)</h4>
                        <p>본 정책은 필요에 따라 내용을 변경할 수 있습니다. 개정된 내용은 본 앱에 게시된 시점부터 효력을 가집니다.</p>
                    </div>
                `,
                zh: `
                    <div class="info-section">
                        <h3>🔒 隐私政策（测试版）</h3>
                        
                        <h4>第1条（基本方针）</h4>
                        <p>本应用"聊天式药品咨询工具"在测试运营（β测试）阶段适当处理从测试者获得的信息，遵守个人信息保护法及相关法令。尊重测试者隐私，努力提供安全可信的环境。</p>
                        
                        <h4>第2条（收集信息）</h4>
                        <p>本应用可能为测试运营目的收集以下信息：</p>
                        <ol>
                            <li>用户输入信息（症状、年龄层、性别等）</li>
                            <li>使用历史·访问日志·使用时间·错误信息等</li>
                            <li>问卷调查和反馈表单的回答内容</li>
                        </ol>
                        <p><strong>※任何信息都不收集姓名或地址等"可直接识别个人的信息"。</strong></p>
                        
                        <h4>第3条（使用目的）</h4>
                        <p>收集的信息仅用于以下目的：</p>
                        <ul>
                            <li>提高应用准确性·修复故障·功能改进</li>
                            <li>分析测试结果及制作开发报告资料</li>
                            <li>运营必要联系（故障报告、改进请求等）</li>
                        </ul>
                        
                        <h4>第4条（第三方提供）</h4>
                        <p>运营者除以下情况外不向第三方提供收集信息：</p>
                        <ul>
                            <li>基于法令的情况</li>
                            <li>本人明确同意的情况</li>
                        </ul>
                        
                        <h4>第5条（信息管理与删除）</h4>
                        <p>收集信息在安全环境中管理，采取适当措施防止第三方非法访问。</p>
                        <ol>
                            <li>在安全环境中管理收集信息，采取适当技术·组织措施防止非法访问·泄露·篡改等。</li>
                            <li>测试期间结束后，可识别个人的信息将迅速删除或匿名化。</li>
                        </ol>
                        
                        <h4>第6条（匿名加工信息处理）</h4>
                        <ol>
                            <li>运营者可能将用户获得的信息加工为无法识别个人的"匿名加工信息"。</li>
                            <li>匿名加工信息可能以无法识别个人的形式用于统计处理·服务改进·学术研究等目的。</li>
                            <li>向第三方提供匿名加工信息时，维持无法重新识别的形式，采取适当安全管理措施。</li>
                            <li>匿名加工信息制作及提供相关方针变更时，将在本政策内迅速公布。</li>
                        </ol>
                        
                        <h4>第7条（测试者权利）</h4>
                        <p>测试者可向运营者请求自身相关信息的公开·订正·删除。希望时请通过以下联系方式咨询：</p>
                        <ul>
                            <li>运营者名：川嶋宥翔（Kawashima Yuto）</li>
                            <li>邮箱地址：weary-scoots.7y@icloud.com</li>
                        </ul>
                        
                        <h4>第8条（修订）</h4>
                        <p>本政策可能根据需要变更内容。修订后内容自在本应用上公布时起生效。</p>
                    </div>
                `
            }
        },
        
        operator: {
            title: 'お問い合わせ・試験運用',
            content: {
                ja: `
                    <div class="info-section">
                        <h3>📮 お問い合わせ・試験運用</h3>
                        <p>本ツールは研究・検証目的のβ版（試験運用）です。運営者の氏名・所属など個人を特定できる情報は開示していません。</p>
                        
                        <div class="contact-info">
                            <h4>お問い合わせ</h4>
                            <p><strong>E-mail：</strong> weary-scoots.7y@icloud.com</p>
                            <p><strong>不具合・お問い合わせフォーム：</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>技術情報</h4>
                            <p><strong>開発言語・技術：</strong> Python 3.9+ / FastAPI（本番ASGI）/ MeCab / OpenAI API（GPT-5.4-mini・GPT-5.5 等）/ DeepL API / PostgreSQL / Pandas / NumPy / HTML5 / CSS3 / JavaScript（ES6+）</p>
                            <p><strong>開発リポジトリ：</strong> <a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></p>
                            <p><strong>デプロイ環境：</strong> Google Cloud（Cloud Run 等）/ Gunicorn + UvicornWorker（ASGI）</p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>公開目的</h4>
                            <p>一般用医薬品の選定支援、安全でわかりやすい薬選びを促すこと</p>
                        </div>
                    </div>
                `,
                en: `
                    <div class="info-section">
                        <h3>📮 Contact & Beta Operation</h3>
                        <p>This tool is a beta version for research and validation. We do not disclose personally identifiable operator details such as name or affiliation.</p>
                        
                        <div class="contact-info">
                            <h4>Contact</h4>
                            <p><strong>Contact Email:</strong> weary-scoots.7y@icloud.com</p>
                            <p><strong>Bug Report & Inquiry Form:</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>Technical Information</h4>
                            <p><strong>Development Languages & Technologies:</strong> Python 3.9+ / FastAPI (production ASGI) / MeCab (Japanese morphological analysis) / OpenAI API (GPT-5.4-mini, GPT-5.5, etc.) / DeepL API / PostgreSQL / Pandas / NumPy / HTML5 / CSS3 / JavaScript (ES6+)</p>
                            <p><strong>Development Repository:</strong> <a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></p>
                            <p><strong>Deployment:</strong> Google Cloud (e.g. Cloud Run) / Gunicorn + UvicornWorker (ASGI)</p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>Publication Purpose</h4>
                            <p>To support over-the-counter medicine selection and promote safe and easy medicine selection</p>
                        </div>
                    </div>
                `,
                ko: `
                    <div class="info-section">
                        <h3>📮 문의·시험 운용</h3>
                        <p>본 도구는 연구·검증 목적의 β판(시험 운용)입니다. 운영자의 성명·소속 등 개인을 특정할 수 있는 정보는 공개하지 않습니다.</p>
                        
                        <div class="contact-info">
                            <h4>문의</h4>
                            <p><strong>연락처 메일:</strong> weary-scoots.7y@icloud.com</p>
                            <p><strong>불구·문의 폼:</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>기술 정보</h4>
                            <p><strong>개발 언어·기술:</strong> Python 3.9+ / FastAPI(프로덕션 ASGI) / MeCab(일본어 형태소) / OpenAI API(GPT-5.4-mini, GPT-5.5 등) / DeepL API / PostgreSQL / Pandas / NumPy / HTML5 / CSS3 / JavaScript (ES6+)</p>
                            <p><strong>개발 리포지토리:</strong> <a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></p>
                            <p><strong>배포 환경:</strong> Google Cloud(Cloud Run 등) / Gunicorn + UvicornWorker(ASGI)</p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>공개 목적</h4>
                            <p>일반의약품 선정 지원, 안전하고 이해하기 쉬운 약 선택을 촉진</p>
                        </div>
                    </div>
                `,
                zh: `
                    <div class="info-section">
                        <h3>📮 联系与试运行</h3>
                        <p>本工具为研究·验证目的的β版（试运行）。不公开运营者姓名、所属等可识别个人的信息。</p>
                        
                        <div class="contact-info">
                            <h4>联系方式</h4>
                            <p><strong>联系邮箱：</strong> weary-scoots.7y@icloud.com</p>
                            <p><strong>故障·咨询表单：</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>技术信息</h4>
                            <p><strong>开发语言·技术：</strong> Python 3.9+ / FastAPI（生产 ASGI）/ MeCab（日语形态素解析）/ OpenAI API（GPT-5.4-mini、GPT-5.5 等）/ DeepL API / PostgreSQL / Pandas / NumPy / HTML5 / CSS3 / JavaScript (ES6+)</p>
                            <p><strong>开发仓库：</strong> <a href="https://github.com/32Lwk" target="_blank">https://github.com/32Lwk</a></p>
                            <p><strong>部署环境：</strong> Google Cloud（Cloud Run 等）/ Gunicorn + UvicornWorker（ASGI）</p>
                        </div>
                        
                        <div class="contact-info">
                            <h4>公开目的</h4>
                            <p>支持非处方药选择，促进安全易懂的药品选择</p>
                        </div>
                    </div>
                `
            }
        },
        
        faq: {
            title: 'よくある質問（FAQ）',
            content: {
                ja: `
                    <div class="info-section">
                        <h3>💬 よくある質問（FAQ）</h3>
                        <p>本アプリについてよくいただく質問と回答をまとめました。ご不明な点がございましたら、こちらをご確認ください。</p>
                        
                        <div class="info-section">
                            <h4>🎤 機能・操作について</h4>
                            
                            <h5>Q1. 音声入力が動作しません</h5>
                            <p><strong>A:</strong> ブラウザのマイクアクセス許可を確認してください。ChromeやSafariでは、URLバーの左側のアイコンからマイクの許可状態を確認できます。また、HTTPS接続（またはlocalhost）でのみ音声入力が利用可能です。</p>
                            
                            <h5>Q2. 言語切替ボタンで表示言語を変えても、AIの返信が日本語のままです</h5>
                            <p><strong>A:</strong> 左上の切替は主にUI（画面のラベルや初期メッセージなど）の言語変更です。AIの返信は、送信テキストの言語を自動検出し、日本語以外と判定された場合に英語・中国語・韓国語へ翻訳して返します。日本語のみで入力していると、表示だけ英語等にしても返信は日本語のままです。</p>
                            
                            <h5>Q3. 複数の症状を同時に相談できますか？</h5>
                            <p><strong>A:</strong> はい、可能です。「頭が痛くて、咳も出る」のように、複数の症状を一度に入力できます。AIが総合的に判断して、適切な市販薬を提案します。</p>
                            
                            <h5>Q4. ユーザー情報を登録した後、変更したい場合はどうすればよいですか？</h5>
                            <p><strong>A:</strong> 「ユーザー情報登録」ボタンからいつでも情報を更新できます。変更内容は即座に反映され、以降のAIの提案に反映されます。</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>👨‍⚕️ 薬剤師要請について</h4>
                            
                            <h5>Q5. 「薬剤師要請」ボタンを押しても応答がありません。</h5>
                            <p><strong>A:</strong> ありがとうございます。本アプリは現在、非営利・学術的な研究目的で、企業や行政、薬剤師の皆様といった専門家向けに限定公開しているβ版です。</p>
                            <p>「薬剤師要請」機能は、将来的な実装を想定したデモ機能であり、実際に薬剤師が応答・返信する体制は現在稼働しておりません。そのため、ボタンを押しても実際の相談員には繋がりませんことを、あらかじめご了承ください。</p>
                            
                            <h5>Q6. 薬剤師要請機能の目的は何ですか？</h5>
                            <p><strong>A:</strong> 本機能は、AIによる回答で不安が残る場合に、専門家（薬剤師）へシームレスに相談を引き継ぐUI/UXの検証を目的として設置されています。β版の運用期間中、本機能を通じた実際の応答・課金は一切発生いたしません。</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>💊 薬の推奨について</h4>
                            
                            <h5>Q7. 年齢制限がある薬は自動で除外されますか？</h5>
                            <p><strong>A:</strong> はい、15歳未満のお子様には小児用の薬を優先的に提案し、年齢制限のある薬は自動で除外されます。また、ユーザー情報に年齢を登録いただくと、より適切な提案が可能になります。</p>
                            
                            <h5>Q8. 薬の相互作用（飲み合わせ）は自動でチェックされますか？</h5>
                            <p><strong>A:</strong> ユーザー情報に現在服用中の薬を登録していただくと、AIが自動で相互作用をチェックします。ただし、本機能はβ版であり、すべての相互作用を網羅・保証するものではありません。該当する場合は警告表示がされますが、最終的な服用の判断は、必ず医師や薬剤師にご相談ください。</p>
                            
                            <h5>Q9. アレルギーがある場合、該当する成分を含む薬は提案されませんか？</h5>
                            <p><strong>A:</strong> ユーザー情報にアレルギーを登録していただくと、該当する成分を含む薬は自動で除外され、警告表示がされます。ただし、本機能もβ版であり、情報の完璧性を保証するものではありません。市販薬をご利用の際は、ご自身でも必ず成分表をご確認ください。アレルギー情報がない場合は除外されないため、必ず事前に登録してください。</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>📱 データ・プライバシーについて</h4>
                            
                            <h5>Q10. 会話履歴は保存されますか？</h5>
                            <p><strong>A:</strong> セッション中は会話履歴が保持されますが、ブラウザを閉じると削除されます。</p>
                            
                            <h5>Q11. 個人情報は安全に管理されていますか？</h5>
                            <p><strong>A:</strong> はい、個人情報は匿名化され、推奨の品質向上と安全確認の目的のみに利用されます。詳細は <a href="javascript:void(0);" onclick="closeInfoModal(); setTimeout(function(){openInfoModal(); showDetailPage('privacy');}, 100);" style="color: #4CAF50; text-decoration: underline; font-weight: bold;">ℹ️ ボタン内の「🔒 プライバシーポリシー」</a> をご確認ください。</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>⚠️ エラー・不具合について</h4>
                            
                            <h5>Q12. エラーメッセージが表示されました</h5>
                            <p><strong>A:</strong> ページを再読み込みして再度お試しください。それでも解決しない場合は、「<a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank" style="color: #4CAF50; text-decoration: underline; font-weight: bold;">不具合報告ボタン</a>」から不具合報告フォームにご報告いただくか、運営者までご連絡ください。</p>
                            
                            <h5>Q13. AIの回答が適切でないと感じます</h5>
                            <p><strong>A:</strong> フィードバック機能（👍👎ボタン）からご意見をお寄せください。（本アプリはβ版です。皆様からのフィードバックが改善の助けとなります。）また、より詳細な報告が必要な場合は、「<a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank" style="color: #4CAF50; text-decoration: underline; font-weight: bold;">不具合報告フォーム</a>」からご報告いただけます。</p>
                        </div>
                        
                        <div class="warning-box">
                            <h4>📞 お問い合わせ</h4>
                            <p>上記で解決しない場合は、以下の連絡先までお問い合わせください。</p>
                            <ul>
                                <li><strong>不具合報告フォーム:</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></li>
                                <li><strong>お問い合わせフォーム：</strong> <a href="https://forms.gle/myzACX7eT59dkrLx8" target="_blank">https://forms.gle/myzACX7eT59dkrLx8</a></li>
                            </ul>
                        </div>
                    </div>
                `,
                en: `
                    <div class="info-section">
                        <h3>💬 Frequently Asked Questions (FAQ)</h3>
                        <p>Here are common questions and answers about this app. Please check here if you have any questions.</p>
                        
                        <div class="info-section">
                            <h4>🎤 About Functions & Operations</h4>
                            
                            <h5>Q1. Voice input is not working</h5>
                            <p><strong>A:</strong> Please check your browser's microphone permission. In Chrome or Safari, you can check the microphone permission status from the icon on the left side of the URL bar. Also, voice input is only available on HTTPS connections (or localhost).</p>
                            
                            <h5>Q2. Even after changing the display language with the language toggle button, the AI's reply remains in Japanese</h5>
                            <p><strong>A:</strong> The upper-left toggle mainly changes UI strings (labels, greeting, etc.). AI replies are translated when your <em>message text</em> is detected as non-Japanese (English, Chinese, or Korean). If you keep typing in Japanese, replies stay in Japanese even if the UI is in another language.</p>
                            
                            <h5>Q3. Can I consult about multiple symptoms at the same time?</h5>
                            <p><strong>A:</strong> Yes, you can. You can input multiple symptoms at once, such as "I have a headache and a cough." The AI will comprehensively evaluate and suggest appropriate over-the-counter medicines.</p>
                            
                            <h5>Q4. How can I update my user information after registering it?</h5>
                            <p><strong>A:</strong> You can update your information at any time from the "User Info" button. Changes are reflected immediately and will be included in subsequent AI recommendations.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>👨‍⚕️ About Pharmacist Consultation</h4>
                            
                            <h5>Q5. There is no response from the pharmacist request</h5>
                            <p><strong>A:</strong> Pharmacists will reply during weekday business hours. If urgent, please consult a medical institution or visit a nearby pharmacy. For emergencies, please call 119 or #7119 (Emergency Consultation Center).</p>
                            
                            <h5>Q6. Is the pharmacist consultation free?</h5>
                            <p><strong>A:</strong> Yes, it is currently free to use in the beta version. However, due to test operations, response time and content may be limited.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>💊 About Medicine Recommendations</h4>
                            
                            <h5>Q7. Are medicines with age restrictions automatically excluded?</h5>
                            <p><strong>A:</strong> Yes, medicines for children under 15 years old are prioritized, and medicines with age restrictions are automatically excluded. Also, registering your age in user information enables more appropriate recommendations.</p>
                            
                            <h5>Q8. Are drug interactions (drug combinations) automatically checked?</h5>
                            <p><strong>A:</strong> Yes, if you register your current medications in user information, the AI will automatically check for interactions. If applicable, a warning will be displayed and you will be prompted to consult a doctor.</p>
                            
                            <h5>Q9. If I have allergies, will medicines containing those ingredients not be recommended?</h5>
                            <p><strong>A:</strong> If you register your allergies in user information, medicines containing those ingredients will be automatically excluded and a warning will be displayed. However, if allergy information is not registered, they may not be excluded, so please register in advance.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>📱 About Data & Privacy</h4>
                            
                            <h5>Q10. Is conversation history saved?</h5>
                            <p><strong>A:</strong> Conversation history is maintained during the session, but is deleted when you close the browser. User information (age, gender, allergies, etc.) is saved in the browser's local storage and can be used on your next visit.</p>
                            
                            <h5>Q11. Is personal information managed securely?</h5>
                            <p><strong>A:</strong> Yes, personal information is anonymized and used only for the purpose of improving recommendation quality and safety checks. For details, please check the "🔒 Privacy Policy" in the ℹ️ button.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>⚠️ About Errors & Issues</h4>
                            
                            <h5>Q12. An error message was displayed</h5>
                            <p><strong>A:</strong> Please reload the page and try again. If the problem persists, please report it using the 🐛 bug report form or contact us at weary-scoots.7y@icloud.com.</p>
                            
                            <h5>Q13. I feel the AI's response is inappropriate</h5>
                            <p><strong>A:</strong> Please share your feedback using the feedback function (👍👎 buttons). If more detailed reporting is needed, you can report it through the bug report form.</p>
                        </div>
                        
                        <div class="warning-box">
                            <h4>📞 Contact</h4>
                            <p>If the above does not resolve your issue, please contact us at the following:</p>
                            <ul>
                                <li><strong>Bug Report Form:</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></li>
                                <li><strong>Email Address:</strong> weary-scoots.7y@icloud.com</li>
                            </ul>
                        </div>
                    </div>
                `,
                ko: `
                    <div class="info-section">
                        <h3>💬 자주 묻는 질문 (FAQ)</h3>
                        <p>본 앱에 대한 자주 묻는 질문과 답변을 정리했습니다. 궁금한 점이 있으시면 여기를 확인해 주세요.</p>
                        
                        <div class="info-section">
                            <h4>🎤 기능·조작에 대해</h4>
                            
                            <h5>Q1. 음성 입력이 작동하지 않습니다</h5>
                            <p><strong>A:</strong> 브라우저의 마이크 액세스 허용을 확인해 주세요. Chrome이나 Safari에서는 URL 바의 왼쪽 아이콘에서 마이크 허용 상태를 확인할 수 있습니다. 또한 HTTPS 연결(또는 localhost)에서만 음성 입력을 사용할 수 있습니다.</p>
                            
                            <h5>Q2. 언어 전환 버튼으로 표시 언어를 바꿔도 AI의 답변이 일본어로 남아 있습니다</h5>
                            <p><strong>A:</strong> 왼쪽 상단 전환은 주로 UI(화면 문구·초기 메시지 등) 언어 변경입니다. AI 답변은 보낸 메시지의 언어를 자동 감지하여 일본어가 아닐 때 영어·중국어·한국어로 번역해 반환합니다. 일본어로만 입력하면 UI만 영어 등으로 바꿔도 답변은 일본어로 유지됩니다.</p>
                            
                            <h5>Q3. 여러 증상을 동시에 상담할 수 있나요?</h5>
                            <p><strong>A:</strong> 네, 가능합니다. "머리가 아프고 기침도 나온다"와 같이 여러 증상을 한 번에 입력할 수 있습니다. AI가 종합적으로 판단하여 적절한 일반의약품을 제안합니다.</p>
                            
                            <h5>Q4. 사용자 정보를 등록한 후 변경하고 싶은 경우 어떻게 해야 하나요?</h5>
                            <p><strong>A:</strong> "사용자 정보 등록" 버튼에서 언제든지 정보를 업데이트할 수 있습니다. 변경 내용은 즉시 반영되며 이후 AI 제안에 반영됩니다.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>👨‍⚕️ 약사 요청에 대해</h4>
                            
                            <h5>Q5. 약사 요청의 응답이 없습니다</h5>
                            <p><strong>A:</strong> 약사는 평일 영업 시간 내에 답변합니다. 급한 경우 의료기관을 방문하거나 가까운 약국에 직접 상담하세요. 응급의 경우 119번 또는 #7119(구급 상담 센터)를 이용하세요.</p>
                            
                            <h5>Q6. 약사 요청은 무료인가요?</h5>
                            <p><strong>A:</strong> 네, 현재 β판에서는 무료로 이용할 수 있습니다. 다만 시험 운영 중이므로 응답 시간이나 대응 내용은 제한적일 수 있습니다.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>💊 약 추천에 대해</h4>
                            
                            <h5>Q7. 연령 제한이 있는 약은 자동으로 제외되나요?</h5>
                            <p><strong>A:</strong> 네, 15세 미만의 어린이에게는 소아용 약을 우선적으로 제안하며, 연령 제한이 있는 약은 자동으로 제외됩니다. 또한 사용자 정보에 연령을 등록하시면 더 적절한 제안이 가능합니다.</p>
                            
                            <h5>Q8. 약의 상호작용(복용 조합)은 자동으로 확인되나요?</h5>
                            <p><strong>A:</strong> 네, 사용자 정보에 현재 복용 중인 약을 등록하시면 AI가 자동으로 상호작용을 확인합니다. 해당하는 경우 경고 표시가 되며 의사의 진찰을 권하는 메시지가 표시됩니다.</p>
                            
                            <h5>Q9. 알레르기가 있는 경우 해당 성분을 포함한 약은 제안되지 않나요?</h5>
                            <p><strong>A:</strong> 사용자 정보에 알레르기를 등록하시면 해당 성분을 포함한 약은 자동으로 제외되고 경고 표시가 됩니다. 다만 알레르기 정보가 없는 경우 제외되지 않을 수 있으므로 반드시 사전에 등록하세요.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>📱 데이터·프라이버시에 대해</h4>
                            
                            <h5>Q10. 대화 기록은 저장되나요?</h5>
                            <p><strong>A:</strong> 세션 중에는 대화 기록이 유지되지만 브라우저를 닫으면 삭제됩니다. 사용자 정보(연령, 성별, 알레르기 등)는 브라우저의 로컬 스토리지에 저장되어 다음 접속 시에도 이용할 수 있습니다.</p>
                            
                            <h5>Q11. 개인정보는 안전하게 관리되나요?</h5>
                            <p><strong>A:</strong> 네, 개인정보는 익명화되어 추천 품질 향상과 안전 확인 목적으로만 이용됩니다. 자세한 내용은 ℹ️ 버튼 내의 "🔒 개인정보 처리방침"을 확인해 주세요.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>⚠️ 오류·불구에 대해</h4>
                            
                            <h5>Q12. 오류 메시지가 표시되었습니다</h5>
                            <p><strong>A:</strong> 페이지를 다시 로드하여 다시 시도해 주세요. 그래도 해결되지 않으면 🐛 버튼에서 불구 신고 양식에 보고하거나 weary-scoots.7y@icloud.com로 연락해 주세요.</p>
                            
                            <h5>Q13. AI의 답변이 적절하지 않다고 느껴집니다</h5>
                            <p><strong>A:</strong> 피드백 기능(👍👎 버튼)에서 의견을 보내 주세요. 또한 더 자세한 보고가 필요한 경우 불구 신고 양식에서 보고할 수 있습니다.</p>
                        </div>
                        
                        <div class="warning-box">
                            <h4>📞 문의</h4>
                            <p>위에서 해결되지 않는 경우 다음 연락처로 문의해 주세요.</p>
                            <ul>
                                <li><strong>불구 신고 양식:</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></li>
                                <li><strong>메일 주소:</strong> weary-scoots.7y@icloud.com</li>
                            </ul>
                        </div>
                    </div>
                `,
                zh: `
                    <div class="info-section">
                        <h3>💬 常见问题 (FAQ)</h3>
                        <p>这里整理了关于本应用的常见问题与回答。如有疑问，请查看此处。</p>
                        
                        <div class="info-section">
                            <h4>🎤 关于功能与操作</h4>
                            
                            <h5>Q1. 语音输入无法使用</h5>
                            <p><strong>A:</strong> 请检查浏览器的麦克风访问权限。Chrome或Safari中，可从地址栏左侧图标确认麦克风权限状态。另外，语音输入仅在HTTPS连接（或localhost）下可用。</p>
                            
                            <h5>Q2. 即使通过语言切换按钮更改显示语言，AI的回复仍然是日语</h5>
                            <p><strong>A:</strong> 左上角切换主要改变界面用语（标签、欢迎语等）。AI回复会根据您<strong>发送的正文</strong>检测语言；若判定为日语以外（英语、中文、韩语等），会翻译后返回。若您一直用日语输入，即使界面设为其他语言，回复仍可能保持日语。</p>
                            
                            <h5>Q3. 可以同时咨询多个症状吗？</h5>
                            <p><strong>A:</strong> 可以。您可以一次输入多个症状，例如“头痛且咳嗽”。AI会综合判断并推荐合适的非处方药。</p>
                            
                            <h5>Q4. 注册用户信息后如何修改？</h5>
                            <p><strong>A:</strong> 可随时通过“用户信息”按钮更新信息。更改会立即生效，并在后续AI推荐中反映。</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>👨‍⚕️ 关于药师咨询</h4>
                            
                            <h5>Q5. 药师请求没有回复</h5>
                            <p><strong>A:</strong> 药师会在工作日营业时间内回复。如紧急，请就医或前往附近药房咨询。紧急情况请拨打119或#7119（急救咨询中心）。</p>
                            
                            <h5>Q6. 药师咨询免费吗？</h5>
                            <p><strong>A:</strong> 是的，测试版目前可免费使用。但由于测试运行，回复时间和内容可能有限。</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>💊 关于药品推荐</h4>
                            
                            <h5>Q7. 有年龄限制的药品会自动排除吗？</h5>
                            <p><strong>A:</strong> 是的，15岁以下儿童会优先推荐儿童用药，有年龄限制的药品会自动排除。在用户信息中登记年龄后，可获得更合适的推荐。</p>
                            
                            <h5>Q8. 药品相互作用（配伍）会自动检查吗？</h5>
                            <p><strong>A:</strong> 是的，在用户信息中登记当前正在服用的药物后，AI会自动检查相互作用。如存在，会显示警告并提示咨询医生。</p>
                            
                            <h5>Q9. 如果有过敏，包含该成分的药品不会被推荐吗？</h5>
                            <p><strong>A:</strong> 在用户信息中登记过敏后，包含该成分的药品会自动排除并显示警告。但如未登记过敏信息，可能不会被排除，请务必事先登记。</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>📱 关于数据与隐私</h4>
                            
                            <h5>Q10. 对话历史会被保存吗？</h5>
                            <p><strong>A:</strong> 会话期间会保留对话历史，但关闭浏览器后会删除。用户信息（年龄、性别、过敏等）保存在浏览器本地存储中，下次访问时仍可使用。</p>
                            
                            <h5>Q11. 个人信息是否安全管理？</h5>
                            <p><strong>A:</strong> 是的，个人信息会被匿名化，仅用于提高推荐质量和安全确认。详情请查看 ℹ️ 按钮内的“🔒 隐私政策”。</p>
                        </div>
                        
                        <div class="info-section">
                            <h4>⚠️ 关于错误与故障</h4>
                            
                            <h5>Q12. 显示了错误消息</h5>
                            <p><strong>A:</strong> 请刷新页面后重试。如仍未解决，请通过🐛错误报告表单报告，或联系weary-scoots.7y@icloud.com。</p>
                            
                            <h5>Q13. 感觉AI的回答不恰当</h5>
                            <p><strong>A:</strong> 请通过反馈功能（👍👎按钮）提供意见。如需更详细的报告，可通过错误报告表单报告。</p>
                        </div>
                        
                        <div class="warning-box">
                            <h4>📞 联系</h4>
                            <p>如上述方法无法解决，请通过以下方式联系我们：</p>
                            <ul>
                                <li><strong>错误报告表单:</strong> <a href="https://forms.gle/UB8kZHd4VHenmRUN6" target="_blank">https://forms.gle/UB8kZHd4VHenmRUN6</a></li>
                                <li><strong>电子邮件地址:</strong> weary-scoots.7y@icloud.com</li>
                            </ul>
                        </div>
                    </div>
                `
            }
        },
        
        consultation: {
            title: '医薬品相談先',
            content: {
                ja: `
                    <div class="info-section">
                        <h3>💊 医薬品・健康相談窓口（公的情報）</h3>
                        <p>以下の公的機関の情報も参考にしてください。</p>
                        
                        <div class="contact-info">
                            <h4>独立行政法人 医薬品医療機器総合機構（PMDA）</h4>
                            <ul>
                                <li><strong>一般用医薬品の安全性や副作用情報</strong><br>
                                    🔗 <a href="https://www.pmda.go.jp/index.html" target="_blank">https://www.pmda.go.jp/index.html</a></li>
                                <li><strong>副作用情報</strong><br>
                                    🔗 <a href="https://www.info.pmda.go.jp/fsearchnew/jsp/menu_fukusayou_base.jsp" target="_blank">https://www.info.pmda.go.jp/fsearchnew/jsp/menu_fukusayou_base.jsp</a></li>
                                <li><strong>添付文書検索（OTC医薬品）</strong><br>
                                    🔗 <a href="https://www.pmda.go.jp/PmdaSearch/otcSearch/" target="_blank">https://www.pmda.go.jp/PmdaSearch/otcSearch/</a></li>
                            </ul>
                        </div>
                        
                        <div class="contact-info">
                            <h4>厚生労働省</h4>
                            <ul>
                                <li><strong>「要指導・一般用医薬品」情報</strong><br>
                                    🔗 <a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000092787.html" target="_blank">https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000092787.html</a></li>
                                <li><strong>医薬品等安全性関連情報</strong><br>
                                    🔗 <a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/iyaku/index.html" target="_blank">https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/iyaku/index.html</a></li>
                                <li><strong>救急安心センター（#7119）</strong><br>
                                    🔗 <a href="https://kakarikata.mhlw.go.jp/kakaritsuke/7119.html" target="_blank">https://kakarikata.mhlw.go.jp/kakaritsuke/7119.html</a></li>
                                <li><strong>医療機関・薬局検索（医療情報ネット）</strong><br>
                                    🔗 <a href="https://www.iryou.teikyouseido.mhlw.go.jp/znk-web/juminkanja/S2300/initialize" target="_blank">https://www.iryou.teikyouseido.mhlw.go.jp/znk-web/juminkanja/S2300/initialize</a></li>
                            </ul>
                        </div>
                        
                        <div class="emergency-box">
                            <h4>🚨 緊急時</h4>
                            <p><strong>救急車:</strong> 119番</p>
                            <p><strong>救急安心センター:</strong> #7119</p>
                            <p>症状が重篤な場合や緊急を要する場合は、速やかに医療機関を受診してください。</p>
                        </div>
                        
                        <div class="warning-box">
                            <h4>⚠️ 重要な注意</h4>
                            <p>本アプリは情報提供のみを目的としており、医療アドバイスではありません。医薬品の使用に際しては、必ず薬剤師または医師にご相談ください。</p>
                        </div>
                    </div>
                `,
                en: `
                    <div class="info-section">
                        <h3>💊 Medicine & Health Consultation Services (Public Information)</h3>
                        <p>Please also refer to the following public institution information.</p>
                        
                        <div class="contact-info">
                            <h4>Pharmaceuticals and Medical Devices Agency (PMDA)</h4>
                            <ul>
                                <li><strong>Over-the-counter Medicine Safety and Side Effect Information</strong><br>
                                    🔗 <a href="https://www.pmda.go.jp/index.html" target="_blank">https://www.pmda.go.jp/index.html</a></li>
                                <li><strong>Side Effect Information</strong><br>
                                    🔗 <a href="https://www.info.pmda.go.jp/fsearchnew/jsp/menu_fukusayou_base.jsp" target="_blank">https://www.info.pmda.go.jp/fsearchnew/jsp/menu_fukusayou_base.jsp</a></li>
                                <li><strong>Package Insert Search (OTC Medicines)</strong><br>
                                    🔗 <a href="https://www.pmda.go.jp/PmdaSearch/otcSearch/" target="_blank">https://www.pmda.go.jp/PmdaSearch/otcSearch/</a></li>
                            </ul>
                        </div>
                        
                        <div class="contact-info">
                            <h4>Ministry of Health, Labour and Welfare</h4>
                            <ul>
                                <li><strong>"Guidance-Required and Over-the-Counter Medicines" Information</strong><br>
                                    🔗 <a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000092787.html" target="_blank">https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000092787.html</a></li>
                                <li><strong>Medicine Safety-Related Information</strong><br>
                                    🔗 <a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/iyaku/index.html" target="_blank">https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/iyaku/index.html</a></li>
                                <li><strong>Emergency Consultation Center (#7119)</strong><br>
                                    🔗 <a href="https://kakarikata.mhlw.go.jp/kakaritsuke/7119.html" target="_blank">https://kakarikata.mhlw.go.jp/kakaritsuke/7119.html</a></li>
                                <li><strong>Medical Institution & Pharmacy Search (Medical Information Network)</strong><br>
                                    🔗 <a href="https://www.iryou.teikyouseido.mhlw.go.jp/znk-web/juminkanja/S2300/initialize" target="_blank">https://www.iryou.teikyouseido.mhlw.go.jp/znk-web/juminkanja/S2300/initialize</a></li>
                            </ul>
                        </div>
                        
                        <div class="emergency-box">
                            <h4>🚨 Emergency</h4>
                            <p><strong>Ambulance:</strong> 119</p>
                            <p><strong>Emergency Consultation Center:</strong> #7119</p>
                            <p>If symptoms are severe or require emergency care, please seek medical attention immediately.</p>
                        </div>
                        
                        <div class="warning-box">
                            <h4>⚠️ Important Notice</h4>
                            <p>This app is for informational purposes only and is not medical advice. Please consult with a pharmacist or doctor when using medicines.</p>
                        </div>
                    </div>
                `,
                ko: `
                    <div class="info-section">
                        <h3>💊 의약품·건강 상담 창구 (공공 정보)</h3>
                        <p>다음 공공기관 정보도 참고해 주세요.</p>
                        
                        <div class="contact-info">
                            <h4>독립행정법인 의약품의료기기총합기구 (PMDA)</h4>
                            <ul>
                                <li><strong>일반의약품의 안전성 및 부작용 정보</strong><br>
                                    🔗 <a href="https://www.pmda.go.jp/index.html" target="_blank">https://www.pmda.go.jp/index.html</a></li>
                                <li><strong>부작용 정보</strong><br>
                                    🔗 <a href="https://www.info.pmda.go.jp/fsearchnew/jsp/menu_fukusayou_base.jsp" target="_blank">https://www.info.pmda.go.jp/fsearchnew/jsp/menu_fukusayou_base.jsp</a></li>
                                <li><strong>첨부문서 검색 (OTC 의약품)</strong><br>
                                    🔗 <a href="https://www.pmda.go.jp/PmdaSearch/otcSearch/" target="_blank">https://www.pmda.go.jp/PmdaSearch/otcSearch/</a></li>
                            </ul>
                        </div>
                        
                        <div class="contact-info">
                            <h4>후생노동성</h4>
                            <ul>
                                <li><strong>"요지도·일반의약품" 정보</strong><br>
                                    🔗 <a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000092787.html" target="_blank">https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000092787.html</a></li>
                                <li><strong>의약품 등 안전성 관련 정보</strong><br>
                                    🔗 <a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/iyaku/index.html" target="_blank">https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/iyaku/index.html</a></li>
                                <li><strong>응급안심센터 (#7119)</strong><br>
                                    🔗 <a href="https://kakarikata.mhlw.go.jp/kakaritsuke/7119.html" target="_blank">https://kakarikata.mhlw.go.jp/kakaritsuke/7119.html</a></li>
                                <li><strong>의료기관·약국 검색 (의료정보넷)</strong><br>
                                    🔗 <a href="https://www.iryou.teikyouseido.mhlw.go.jp/znk-web/juminkanja/S2300/initialize" target="_blank">https://www.iryou.teikyouseido.mhlw.go.jp/znk-web/juminkanja/S2300/initialize</a></li>
                            </ul>
                        </div>
                        
                        <div class="emergency-box">
                            <h4>🚨 응급시</h4>
                            <p><strong>구급차:</strong> 119번</p>
                            <p><strong>응급안심센터:</strong> #7119</p>
                            <p>증상이 중증이거나 응급을 요하는 경우 신속히 의료기관을 방문하세요.</p>
                        </div>
                        
                        <div class="warning-box">
                            <h4>⚠️ 중요한 주의사항</h4>
                            <p>본 앱은 정보 제공만을 목적으로 하며 의료 조언이 아닙니다. 의약품 사용 시에는 반드시 약사 또는 의사에게 상담하세요.</p>
                        </div>
                    </div>
                `,
                zh: `
                    <div class="info-section">
                        <h3>💊 药品·健康咨询窗口（公共信息）</h3>
                        <p>请参考以下公共机构信息。</p>
                        
                        <div class="contact-info">
                            <h4>独立行政法人 药品医疗器械综合机构（PMDA）</h4>
                            <ul>
                                <li><strong>非处方药安全性和副作用信息</strong><br>
                                    🔗 <a href="https://www.pmda.go.jp/index.html" target="_blank">https://www.pmda.go.jp/index.html</a></li>
                                <li><strong>副作用信息</strong><br>
                                    🔗 <a href="https://www.info.pmda.go.jp/fsearchnew/jsp/menu_fukusayou_base.jsp" target="_blank">https://www.info.pmda.go.jp/fsearchnew/jsp/menu_fukusayou_base.jsp</a></li>
                                <li><strong>说明书检索（OTC药品）</strong><br>
                                    🔗 <a href="https://www.pmda.go.jp/PmdaSearch/otcSearch/" target="_blank">https://www.pmda.go.jp/PmdaSearch/otcSearch/</a></li>
                            </ul>
                        </div>
                        
                        <div class="contact-info">
                            <h4>厚生劳动省</h4>
                            <ul>
                                <li><strong>"需指导·非处方药"信息</strong><br>
                                    🔗 <a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000092787.html" target="_blank">https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000092787.html</a></li>
                                <li><strong>药品等安全性相关信息</strong><br>
                                    🔗 <a href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/iyaku/index.html" target="_blank">https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/iyaku/index.html</a></li>
                                <li><strong>急救安心中心（#7119）</strong><br>
                                    🔗 <a href="https://kakarikata.mhlw.go.jp/kakaritsuke/7119.html" target="_blank">https://kakarikata.mhlw.go.jp/kakaritsuke/7119.html</a></li>
                                <li><strong>医疗机构·药店检索（医疗信息网）</strong><br>
                                    🔗 <a href="https://www.iryou.teikyouseido.mhlw.go.jp/znk-web/juminkanja/S2300/initialize" target="_blank">https://www.iryou.teikyouseido.mhlw.go.jp/znk-web/juminkanja/S2300/initialize</a></li>
                            </ul>
                        </div>
                        
                        <div class="emergency-box">
                            <h4>🚨 紧急时</h4>
                            <p><strong>救护车：</strong> 119号</p>
                            <p><strong>急救安心中心：</strong> #7119</p>
                            <p>症状严重或需要紧急处理时，请迅速前往医疗机构就诊。</p>
                        </div>
                        
                        <div class="warning-box">
                            <h4>⚠️ 重要注意事项</h4>
                            <p>本应用仅用于信息提供，非医疗建议。使用药品时请务必咨询药师或医生。</p>
                        </div>
                    </div>
                `
            }
        },
        'settings': {
            title: '設定',
            content: {
                ja: `
                    <div class="info-section">
                        <h3>⚙️ 表示設定</h3>
                        <div style="margin: 20px 0;">
                            <h4 style="margin-bottom: 15px;">文字サイズ</h4>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                                <button class="font-size-btn" data-size="small" onclick="setFontSize('small')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">小</button>
                                <button class="font-size-btn" data-size="normal" onclick="setFontSize('normal')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 16px;">標準</button>
                                <button class="font-size-btn" data-size="large" onclick="setFontSize('large')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 20px;">大</button>
                                <button class="font-size-btn" data-size="extra-large" onclick="setFontSize('extra-large')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 24px;">特大</button>
                            </div>
                            <p style="margin-top: 15px; color: #666; font-size: 0.9em;">文字サイズを変更すると、ページ全体の文字が大きくなります。設定は保存され、次回アクセス時も適用されます。</p>
                        </div>
                        <div style="margin: 20px 0;">
                            <h4 style="margin-bottom: 15px;">音声読み上げ速度</h4>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                                <button onclick="setVoiceReadSpeed(0.75)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">遅い</button>
                                <button onclick="setVoiceReadSpeed(1.0)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">標準</button>
                                <button onclick="setVoiceReadSpeed(1.25)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">速い</button>
                            </div>
                            <p style="margin-top: 15px; color: #666; font-size: 0.9em;">音声読み上げの速度を調整できます。設定は保存され、次回アクセス時も適用されます。</p>
                        </div>
                    </div>
                `,
                en: `
                    <div class="info-section">
                        <h3>⚙️ Display Settings</h3>
                        <div style="margin: 20px 0;">
                            <h4 style="margin-bottom: 15px;">Font Size</h4>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                                <button class="font-size-btn" data-size="small" onclick="setFontSize('small')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">Small</button>
                                <button class="font-size-btn" data-size="normal" onclick="setFontSize('normal')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 16px;">Normal</button>
                                <button class="font-size-btn" data-size="large" onclick="setFontSize('large')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 20px;">Large</button>
                                <button class="font-size-btn" data-size="extra-large" onclick="setFontSize('extra-large')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 24px;">Extra Large</button>
                            </div>
                            <p style="margin-top: 15px; color: #666; font-size: 0.9em;">Changing the font size will make all text on the page larger. Settings are saved and will be applied on your next visit.</p>
                        </div>
                        <div style="margin: 20px 0;">
                            <h4 style="margin-bottom: 15px;">Voice Reading Speed</h4>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                                <button onclick="setVoiceReadSpeed(0.75)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">Slow</button>
                                <button onclick="setVoiceReadSpeed(1.0)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">Normal</button>
                                <button onclick="setVoiceReadSpeed(1.25)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">Fast</button>
                            </div>
                            <p style="margin-top: 15px; color: #666; font-size: 0.9em;">You can adjust the voice reading speed. Settings are saved and will be applied on your next visit.</p>
                        </div>
                    </div>
                `,
                ko: `
                    <div class="info-section">
                        <h3>⚙️ 표시 설정</h3>
                        <div style="margin: 20px 0;">
                            <h4 style="margin-bottom: 15px;">글자 크기</h4>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                                <button class="font-size-btn" data-size="small" onclick="setFontSize('small')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">작게</button>
                                <button class="font-size-btn" data-size="normal" onclick="setFontSize('normal')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 16px;">보통</button>
                                <button class="font-size-btn" data-size="large" onclick="setFontSize('large')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 20px;">크게</button>
                                <button class="font-size-btn" data-size="extra-large" onclick="setFontSize('extra-large')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 24px;">아주 크게</button>
                            </div>
                            <p style="margin-top: 15px; color: #666; font-size: 0.9em;">글자 크기를 변경하면 페이지의 모든 텍스트가 커집니다. 설정은 저장되며 다음 방문 시에도 적용됩니다.</p>
                        </div>
                        <div style="margin: 20px 0;">
                            <h4 style="margin-bottom: 15px;">음성 읽기 속도</h4>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                                <button onclick="setVoiceReadSpeed(0.75)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">느리게</button>
                                <button onclick="setVoiceReadSpeed(1.0)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">보통</button>
                                <button onclick="setVoiceReadSpeed(1.25)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">빠르게</button>
                            </div>
                            <p style="margin-top: 15px; color: #666; font-size: 0.9em;">음성 읽기 속도를 조정할 수 있습니다. 설정은 저장되며 다음 방문 시에도 적용됩니다.</p>
                        </div>
                    </div>
                `,
                zh: `
                    <div class="info-section">
                        <h3>⚙️ 显示设置</h3>
                        <div style="margin: 20px 0;">
                            <h4 style="margin-bottom: 15px;">字体大小</h4>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                                <button class="font-size-btn" data-size="small" onclick="setFontSize('small')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">小</button>
                                <button class="font-size-btn" data-size="normal" onclick="setFontSize('normal')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 16px;">标准</button>
                                <button class="font-size-btn" data-size="large" onclick="setFontSize('large')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 20px;">大</button>
                                <button class="font-size-btn" data-size="extra-large" onclick="setFontSize('extra-large')" style="padding: 10px 20px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 24px;">特大</button>
                            </div>
                            <p style="margin-top: 15px; color: #666; font-size: 0.9em;">更改字体大小将使页面上的所有文本变大。设置将被保存，并在下次访问时应用。</p>
                        </div>
                        <div style="margin: 20px 0;">
                            <h4 style="margin-bottom: 15px;">语音朗读速度</h4>
                            <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
                                <button onclick="setVoiceReadSpeed(0.75)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">慢</button>
                                <button onclick="setVoiceReadSpeed(1.0)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">标准</button>
                                <button onclick="setVoiceReadSpeed(1.25)" style="padding: 8px 16px; border: 2px solid #4CAF50; border-radius: 8px; background: white; color: #4CAF50; cursor: pointer; font-size: 14px;">快</button>
                            </div>
                            <p style="margin-top: 15px; color: #666; font-size: 0.9em;">您可以调整语音朗读速度。设置将被保存，并在下次访问时应用。</p>
                        </div>
                    </div>
                `
            }
        }
    };
    
    // モーダルを開く
    function openInfoModal() {
        document.getElementById('infoModal').style.display = 'block';
        showListPage();
    }

    // モーダルを閉じる
    function closeInfoModal() {
        document.getElementById('infoModal').style.display = 'none';
        currentModalPage = 'list';
    }

    // 一覧ページを表示
    function showListPage() {
        currentModalPage = 'list';
        const t = translations[currentLanguage];
        document.getElementById('modalTitle').textContent = isSageUi() ? t.infoButton : t.appInfo;
        document.getElementById('listPage').style.display = 'block';
        document.getElementById('detailPage').style.display = 'none';
        const backButton = document.getElementById('back-button');
        if (backButton) {
            backButton.style.display = 'none';
            backButton.setAttribute('aria-hidden', 'true');
        }
    }

    // 詳細ページを表示
    function showDetailPage(pageId) {
        currentModalPage = pageId;
        const page = modalPages[pageId];
        
        if (!page) return;
        
        // タイトル更新（翻訳対応）
        const t = translations[currentLanguage];
        let translatedTitle = page.title;
        if (pageId === 'app-overview') translatedTitle = t.appInfo;
        else if (pageId === 'usage') translatedTitle = t.usage || '使い方';
        else if (pageId === 'disclaimer') translatedTitle = t.disclaimer;
        else if (pageId === 'privacy') translatedTitle = t.privacy;
        else if (pageId === 'consultation') translatedTitle = t.consultation;
        else if (pageId === 'faq') translatedTitle = t.faq || 'よくある質問（FAQ）';
        else if (pageId === 'settings') translatedTitle = '設定';
        
        document.getElementById('modalTitle').textContent = translatedTitle;
        
        // 一覧ページを非表示、詳細ページを表示
        document.getElementById('listPage').style.display = 'none';
        document.getElementById('detailPage').style.display = 'block';
        const backButton = document.getElementById('back-button');
        if (backButton) {
            backButton.style.display = 'inline-flex';
            backButton.setAttribute('aria-hidden', 'false');
        }
        
        // 詳細コンテンツ更新（言語対応）
        let content = page.content;
        if (typeof content === 'object' && content[currentLanguage]) {
            content = content[currentLanguage];
        }
        document.getElementById('detailContent').innerHTML = content;
        
        // 設定ページの場合、現在の設定を反映
        if (pageId === 'settings') {
            updateSettingsPage();
            injectSageDisplaySettings();
        }
        
        // スクロール位置を一番上にリセット
        const detailPage = document.getElementById('detailPage');
        const modalBody = detailPage.closest('.modal-body');
        const modalContent = detailPage.closest('.modal-content');
        
        // コンテンツ更新後に少し遅延を入れてスクロール位置をリセット
        setTimeout(() => {
            if (modalBody) {
                modalBody.scrollTop = 0;
            }
            if (modalContent) {
                modalContent.scrollTop = 0;
            }
            if (detailPage) {
                detailPage.scrollTop = 0;
            }
            // モーダル全体のスクロール位置もリセット（親要素も含む）
            const detailContent = document.getElementById('detailContent');
            if (detailContent) {
                detailContent.scrollTop = 0;
            }
        }, 10);
    }

    // モーダル外クリックで閉じる
    window.onclick = function(event) {
        const modal = document.getElementById('infoModal');
        if (event.target === modal) {
            closeInfoModal();
        }
    }

    // ESCキーでモーダルを閉じる
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeInfoModal();
        }
    });

    // 言語切り替え機能
    function toggleLanguageMenu() {
        const dropdown = document.getElementById('langDropdown');
        const toggle = document.querySelector('.lang-toggle');
        
        if (dropdown.classList.contains('show')) {
            dropdown.classList.remove('show');
            toggle.classList.remove('open');
        } else {
            dropdown.classList.add('show');
            toggle.classList.add('open');
        }
    }
    
    // 言語選択
    function selectLanguage(lang) {
        currentLanguage = lang;
        window.currentLanguage = lang;
        sessionStorage.setItem('language', lang);
        
        // サーバーに言語設定を送信
        fetch('/api/set_language', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                language: lang
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log(`Language set to ${lang}`);
            } else {
                console.error('Failed to set language:', data.error);
            }
        })
        .catch(error => {
            console.error('Error setting language:', error);
        });
        
        // UI更新
        updateUI();

        if (isSageUi() && window.SafetyRail) {
            refreshSageSafetyRail(window.__lastUserAttributes || {});
        }
        
        // ドロップダウンを閉じる
        const dropdown = document.getElementById('langDropdown');
        const toggle = document.querySelector('.lang-toggle');
        if (dropdown) dropdown.classList.remove('show');
        if (toggle) toggle.classList.remove('open');
        
        // アクティブな言語オプションを更新
        document.querySelectorAll('.lang-option').forEach(option => {
            option.classList.remove('active');
        });
        document.querySelector(`[data-lang="${lang}"]`).classList.add('active');
        
        // フラグを更新
        const flag = document.querySelector(`[data-lang="${lang}"]`).dataset.flag;
        document.getElementById('currentFlag').textContent = flag;
    }
    
    // 初期メッセージを更新する関数
    function updateInitialMessage() {
        const t = translations[currentLanguage];
        
        const greetingElement = document.getElementById('initial-greeting');
        const examplesElement = document.getElementById('initial-examples');
        
        if (greetingElement) {
            greetingElement.textContent = t.initialGreeting;
        }
        if (examplesElement) {
            examplesElement.textContent = t.initialExamples;
        }
    }
    
    // 開発環境のときタイトル中の「β版」相当表記を「dev」に置換する
    // β版表記が無い場合は末尾に " (dev)" を追加する
    function transformTitleForEnv(rawTitle) {
        if (!isDevEnv() || !rawTitle) return rawTitle;
        const betaPatterns = [
            { re: /\(β版\)/g, replacement: '(dev)' },
            { re: /\(Beta\)/gi, replacement: '(dev)' },
            { re: /\(베타\)/g, replacement: '(dev)' },
            { re: /（测试版）/g, replacement: '(dev)' },
            { re: /\(测试版\)/g, replacement: '(dev)' },
        ];
        let result = rawTitle;
        let replaced = false;
        for (const { re, replacement } of betaPatterns) {
            if (re.test(result)) {
                result = result.replace(re, replacement);
                replaced = true;
            }
        }
        if (!replaced) {
            result = rawTitle + ' (dev)';
        }
        return result;
    }

    function parseAppTitleParts(title) {
        if (!title) {
            return { emoji: '', core: '', env: '' };
        }
        let rest = String(title).trim();
        let emoji = '';
        const emojiMatch = rest.match(/^(\p{Extended_Pictographic}\uFE0F?)\s+/u);
        if (emojiMatch) {
            emoji = emojiMatch[1];
            rest = rest.slice(emojiMatch[0].length);
        }
        let env = '';
        const envMatch = rest.match(/\s*(\([^)]+\))\s*$/);
        if (envMatch) {
            env = envMatch[1];
            rest = rest.slice(0, -envMatch[0].length).trimEnd();
        }
        return { emoji, core: rest.trim(), env };
    }

    function renderAppTitle(rawTitle, shortCore) {
        const el = document.getElementById('appTitle');
        if (!el) return;

        const parts = parseAppTitleParts(transformTitleForEnv(rawTitle));
        const ariaFull = [parts.emoji, parts.core, parts.env].filter(Boolean).join(' ');
        el.setAttribute('aria-label', ariaFull);
        el.replaceChildren();

        if (parts.emoji) {
            const emojiSpan = document.createElement('span');
            emojiSpan.className = 'app-title-emoji';
            emojiSpan.setAttribute('aria-hidden', 'true');
            emojiSpan.textContent = parts.emoji + '\u00a0';
            el.appendChild(emojiSpan);
        }

        const coreSpan = document.createElement('span');
        coreSpan.className = 'app-title-core';
        coreSpan.textContent = parts.core;
        el.appendChild(coreSpan);

        const compactCore = (shortCore || '').trim();
        if (compactCore && compactCore !== parts.core) {
            const shortSpan = document.createElement('span');
            shortSpan.className = 'app-title-core--short';
            shortSpan.setAttribute('aria-hidden', 'true');
            shortSpan.textContent = compactCore;
            el.appendChild(shortSpan);
        }

        if (parts.env) {
            const envSpan = document.createElement('span');
            envSpan.className = 'app-title-env';
            envSpan.textContent = '\u00a0' + parts.env;
            el.appendChild(envSpan);
        }
    }

    function updateUI() {
        const t = translations[currentLanguage];
        
        // ヘッダー要素の更新
        renderAppTitle(t.title, t.titleShort);
        const appDesc = document.getElementById('appDescription');
        if (appDesc) {
            appDesc.textContent = t.description;
        }
        document.getElementById('userInfoBtn').textContent = t.userInfoBtn;
        document.getElementById('clearBtn').textContent = t.clearBtn;
        document.getElementById('new-session-btn').textContent = t.newSessionBtn;
        document.getElementById('admin-request-btn').textContent = t.adminRequestBtn;
        const sageClearBtn = document.getElementById('sage-clear-btn');
        if (sageClearBtn) {
            const clearLabel = t.clearBtn || '履歴クリア';
            sageClearBtn.title = clearLabel;
            sageClearBtn.setAttribute('aria-label', clearLabel);
        }
        
        // 情報ボタンのタイトル更新
        document.getElementById('infoBtn').title = t.infoButton;
        
        // モーダル内の一覧項目の翻訳更新
        updateModalListItems();
        
        // 戻るボタンの翻訳更新
        const backButton = document.getElementById('back-button');
        if (backButton) {
            backButton.textContent = t.back;
        }
        
        // 入力フィールドの更新
        document.getElementById('messageInput').placeholder = t.placeholder;
        setChatSendButtonState(getChatSubmitButton(), 'idle');
        
        // 初期メッセージの更新（新規追加）
        updateInitialMessage();

        // オンボーディングの言語更新
        updateOnboardingLanguage();
    }
    
    // モーダル内の一覧項目を翻訳
    function updateModalListItems() {
        const t = translations[currentLanguage];
        
        // 各項目のタイトルと説明を更新
        const items = [
            { id: 'site-about', title: t.siteAboutTitle, desc: t.siteAboutDesc },
            { id: 'app-overview', title: t.appInfo, desc: t.appInfoDesc },
            { id: 'usage', title: t.usage || '使い方・FAQ', desc: t.usageDesc || 'アプリの使い方と安全に利用するための注意' },
            { id: 'disclaimer', title: t.disclaimer, desc: t.disclaimerDesc },
            { id: 'privacy', title: t.privacy, desc: t.privacyDesc },
            { id: 'consultation', title: t.consultation, desc: t.consultationDesc },
            { id: 'settings', title: t.settingsTitle, desc: t.settingsDesc },
        ];
        
        items.forEach(item => {
            const titleElement = document.getElementById(`list-${item.id}-title`);
            const descElement = document.getElementById(`list-${item.id}-desc`);
            
            if (titleElement) titleElement.textContent = item.title;
            if (descElement) descElement.textContent = item.desc;
        });
    }
    
    // 季節パーティクル（サーバプロファイル + prefers-reduced-motion 対応）
    function updateSnowContainerHeight() {
        const snowContainer = document.getElementById('snowContainer');
        const chatMessages = document.getElementById('chatMessages');

        if (!snowContainer || !chatMessages) return;

        const clientHeight = chatMessages.clientHeight;
        if (!clientHeight) return;

        // レイアウト高さは CSS の height:100% のみ（px 指定や --snow-container-height を
        // レイアウトに使うと scrollHeight が膨らみ、下端に大きな余白ができる）
        snowContainer.style.removeProperty('height');

        const contentScrollHeight = chatMessages.scrollHeight;
        const animationHeight = Math.max(contentScrollHeight, clientHeight);
        snowContainer.style.setProperty('--snow-container-height', animationHeight + 'px');
    }

    /** 入力欄の実高さを CSS 変数に反映（将来のレイアウト調整用） */
    function syncChatInputHeight() {
        const chatInput = document.querySelector('.chat-input');
        if (!chatInput) return;
        const height = Math.ceil(chatInput.getBoundingClientRect().height);
        if (!height) return;
        document.documentElement.style.setProperty('--chat-input-height', height + 'px');
        updateSnowContainerHeight();
    }

    function resizeMessageInput(textarea) {
        if (!textarea) return;
        textarea.style.height = 'auto';
        const maxHeight = parseInt(window.getComputedStyle(textarea).maxHeight, 10) || 100;
        textarea.style.height = Math.min(textarea.scrollHeight, maxHeight) + 'px';
        syncChatInputHeight();
    }

    let chatInputResizeObserver = null;

    function initSeasonDecorationLayout() {
        if (!isSeasonDecorationEnabled()) {
            return;
        }
        document.querySelectorAll('.season-decoration').forEach((img) => {
            const onReady = () => syncChatInputHeight();
            if (img.complete) {
                onReady();
            } else {
                img.addEventListener('load', onReady, { once: true });
                img.addEventListener('error', onReady, { once: true });
            }
        });
    }

    function initChatInputLayout() {
        const chatInput = document.querySelector('.chat-input');
        const messageInput = document.getElementById('messageInput');
        if (!chatInput) return;

        initSeasonDecorationLayout();
        syncChatInputHeight();

        if (typeof ResizeObserver !== 'undefined') {
            if (chatInputResizeObserver) {
                chatInputResizeObserver.disconnect();
            }
            chatInputResizeObserver = new ResizeObserver(() => {
                syncChatInputHeight();
            });
            chatInputResizeObserver.observe(chatInput);
        }

        if (messageInput) {
            resizeMessageInput(messageInput);
        }
    }

    function readParticleProfile() {
        const el = document.getElementById('particle-profile');
        if (!el || !String(el.textContent || '').trim()) return null;
        try {
            return JSON.parse(el.textContent);
        } catch (e) {
            console.warn('particle-profile JSON の解析に失敗しました', e);
            return null;
        }
    }

    function particleStaticUrl(relativePath) {
        if (!relativePath) return '';
        const clean = String(relativePath).replace(/^\/+/, '');
        return mainAppPath('/static/' + clean);
    }

    /** スプライト配列要素を { path, weight } に正規化（文字列 path のみも可） */
    function normalizeSpriteEntry(entry) {
        if (!entry) return null;
        if (typeof entry === 'string') {
            const p = entry.trim();
            return p ? { path: p, weight: 1 } : null;
        }
        if (typeof entry === 'object' && entry.path) {
            const w = Number(entry.weight);
            return { path: String(entry.path).trim(), weight: w > 0 ? w : 1 };
        }
        return null;
    }

    function pickWeightedSpritePath(sprites) {
        const list = (Array.isArray(sprites) ? sprites : [])
            .map(normalizeSpriteEntry)
            .filter(Boolean);
        if (!list.length) return '';
        let total = 0;
        for (let i = 0; i < list.length; i++) total += list[i].weight;
        let r = Math.random() * total;
        for (let i = 0; i < list.length; i++) {
            r -= list[i].weight;
            if (r <= 0) return list[i].path;
        }
        return list[list.length - 1].path;
    }

    /** sRGB #rrggbb の相対輝度（WCAG）。極端に暗い色は粒子に使わない */
    function particleRelativeLuminance(hex) {
        const h = String(hex || '').trim();
        const m = /^#?([0-9a-f]{6})$/i.exec(h);
        if (!m) return 0;
        const n = parseInt(m[1], 16);
        const rs = (n >> 16) & 255;
        const gs = (n >> 8) & 255;
        const bs = n & 255;
        const lin = function (v) {
            v /= 255;
            return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
        };
        return 0.2126 * lin(rs) + 0.7152 * lin(gs) + 0.0722 * lin(bs);
    }

    function sanitizeParticleColor(hex) {
        const h = String(hex || '').trim();
        const lower = h.toLowerCase();
        if (lower === '#000' || lower === '#000000' || lower === 'rgb(0,0,0)') {
            return '#eceff1';
        }
        const lum = particleRelativeLuminance(h.startsWith('#') ? h : '#' + h);
        if (lum < 0.55) {
            return '#eceff1';
        }
        return h.startsWith('#') ? h : '#' + h;
    }

    function createSeasonalParticles() {
        const snowContainer = document.getElementById('snowContainer');
        if (!snowContainer) return;

        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;

        snowContainer.innerHTML = '';

        if (!isParticleEffectsEnabled()) {
            return;
        }

        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }

        const profile = readParticleProfile();
        if (!profile || profile.enabled === false) {
            return;
        }

        const glyphs = Array.isArray(profile.glyphs) ? profile.glyphs.filter(Boolean) : [];
        const sprites = Array.isArray(profile.sprites) ? profile.sprites : [];
        if (!glyphs.length && !sprites.length) {
            return;
        }

        updateSnowContainerHeight();

        const density = profile.density || 'medium';
        const capByDensity = { low: 10, medium: 22, high: 34 };
        const cap = capByDensity[density] != null ? capByDensity[density] : 18;
        const snowflakeCount = Math.min(cap, Math.floor(window.innerWidth / 28));

        const amin = typeof profile.angleDegMin === 'number' ? profile.angleDegMin : -18;
        const amax = typeof profile.angleDegMax === 'number' ? profile.angleDegMax : 18;
        const dmin = typeof profile.driftPxMin === 'number' ? profile.driftPxMin : -55;
        const dmax = typeof profile.driftPxMax === 'number' ? profile.driftPxMax : 55;
        const durMin = typeof profile.durationSecMin === 'number' ? profile.durationSecMin : 9;
        const durMax = typeof profile.durationSecMax === 'number' ? profile.durationSecMax : 26;
        const delayMax = typeof profile.delaySecMax === 'number' ? profile.delaySecMax : 5;
        const particleColor = sanitizeParticleColor(profile.particleColor || '#ffffff');
        const vw = window.innerWidth || 800;
        const vh = window.innerHeight || 600;
        const driftScale = Math.min(1.12, Math.max(0.72, Math.min(vw, vh) / 720));

        for (let i = 0; i < snowflakeCount; i++) {
            const orbit = document.createElement('div');
            orbit.className = 'particle-orbit';
            const left = Math.random() * 100;
            orbit.style.left = left + '%';
            orbit.style.top = Math.random() * 100 + '%';
            const angle = amin + Math.random() * (amax - amin);
            orbit.style.setProperty('--orbit-angle', angle + 'deg');

            const inner = document.createElement('div');
            inner.className = 'snowflake-inner';
            inner.style.color = particleColor;
            inner.style.fontSize = (0.55 + Math.random() * 0.45) + 'em';

            const useSprite = sprites.length > 0 && Math.random() < 0.35;
            const relSprite = useSprite ? pickWeightedSpritePath(sprites) : '';
            if (relSprite) {
                const img = document.createElement('img');
                img.alt = '';
                img.className = 'particle-sprite';
                img.style.width = '1em';
                img.style.height = '1em';
                img.style.objectFit = 'contain';
                img.style.verticalAlign = 'middle';
                img.src = particleStaticUrl(relSprite);
                img.loading = 'lazy';
                img.onerror = function () {
                    img.replaceWith(document.createTextNode(glyphs.length ? glyphs[Math.floor(Math.random() * glyphs.length)] : '✨'));
                };
                inner.appendChild(img);
            } else {
                inner.textContent = glyphs[Math.floor(Math.random() * glyphs.length)] || '✨';
            }

            const animationDuration = durMin + Math.random() * Math.max(0.1, durMax - durMin);
            // 負の delay で落下のランダム位相から開始し、読み込み直後に上辺へ溜まらないようにする
            const delay = -Math.random() * (animationDuration + delayMax);
            const drift = (dmin + Math.random() * (dmax - dmin)) * driftScale;

            inner.style.animationDuration = animationDuration + 's';
            inner.style.animationDelay = delay + 's';
            inner.style.setProperty('--drift', drift + 'px');

            orbit.appendChild(inner);
            snowContainer.appendChild(orbit);
        }
    }
    
    let resizeTimeout;
    function handleResize() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            syncChatInputHeight();
            createSeasonalParticles();
            updateSnowContainerHeight();
        }, 250);
    }

    // 開発環境のときヘッダーの DEV バッジを表示する
    function applyEnvBadge() {
        const badge = document.getElementById('envBadge');
        if (!badge) return;
        if (isDevEnv()) {
            badge.hidden = false;
            // フォールバックでホスト名から判定された場合に備え、data-env も同期する
            if (document.body && document.body.dataset && document.body.dataset.env !== 'dev') {
                document.body.dataset.env = 'dev';
            }
        } else {
            badge.hidden = true;
        }
    }

    // ページ読み込み時に言語設定を適用
    function initPage() {
        updateUI();
        applyEnvBadge();

        initChatInputLayout();
        applySeasonDecorationVisibility();
        createSeasonalParticles();
        window.addEventListener('resize', handleResize);
        
        // MutationObserver: チャット DOM 変化時に落下距離用 CSS 変数だけ更新する。
        // 粒子の createSeasonalParticles はここで呼ばない（innerHTML 全消しで毎回ちらつくため）。
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            let mutationLayoutTimeout;
            const observer = new MutationObserver(() => {
                clearTimeout(mutationLayoutTimeout);
                mutationLayoutTimeout = setTimeout(() => {
                    syncChatInputHeight();
                    updateSnowContainerHeight();
                }, 500);
            });

            observer.observe(chatMessages, {
                childList: true,
                subtree: true,
                attributes: false
            });
        }
        
        let onboardingCompleted = null;
        try {
            onboardingCompleted = localStorage.getItem('onboardingCompleted');
        } catch (error) {
            console.warn('Onboarding storage access failed:', error);
        }

        if (!onboardingCompleted) {
            initOnboarding();
        }
        
        // 言語オプションにイベントリスナーを追加
        const langOptions = document.querySelectorAll('.lang-option');
        langOptions.forEach(option => {
            option.addEventListener('click', function() {
                const lang = this.getAttribute('data-lang');
                selectLanguage(lang);
            });
        });
        
        // ドロップダウン外をクリックしたら閉じる
        document.addEventListener('click', function(e) {
            const selector = document.querySelector('.language-selector');
            if (!selector) {
                return;
            }
            if (!selector.contains(e.target)) {
                const dropdown = document.getElementById('langDropdown');
                const toggle = document.querySelector('.lang-toggle');
                if (dropdown) {
                    dropdown.classList.remove('show');
                }
                if (toggle) {
                    toggle.classList.remove('open');
                }
            }
        });
        
        // ユーザー情報モーダルの性別変更イベントを設定
        const userGenderSelect = document.getElementById('user_gender');
        if (userGenderSelect) {
            userGenderSelect.addEventListener('change', toggleUserPregnancyFields);
        }
    }
    
    // DOMContentLoadedイベントが既に発火しているかチェック
    if (document.readyState === 'loading') {
        // DOMContentLoadedイベントがまだ発火していない場合
        document.addEventListener('DOMContentLoaded', initPage);
    } else {
        // DOMContentLoadedイベントが既に発火している場合（defer属性で読み込まれた場合など）
        initPage();
    }
    
    // 送信中フラグ（グローバル変数）
    let isSubmitting = false;
    let chatSubmitGeneration = 0;
    const SUBMIT_DEBOUNCE_MS = 2500;
    let lastSubmitPayload = { message: '', at: 0 };
    let submitWatchdogTimer = null;
    let slowRequestTimerId = null;
    let streamingRecommendationEl = null;
    let streamingChatEl = null;
    let streamingQaEl = null;
    let chatStreamInProgress = false;
    /** 医薬品推奨 SSE: cards 受信後は部分表示せず done で一括描画 */
    let recommendationSseBulkMode = false;
    /** SSE done 後〜応答描画まで（この間は /api/sessions 同期を許可） */
    let awaitingPostResponse = false;
    /** 直近 POST の応答反映が完了したら true（ポーリング抑制用） */
    let postResponseResolved = false;
    const SUBMIT_WATCHDOG_MS = 120000;

    function shouldDeferSessionSync() {
        if (awaitingPostResponse) {
            return chatStreamInProgress || hasActiveStreamingContent();
        }
        return isSubmitting || chatStreamInProgress || hasActiveStreamingContent();
    }

    function markPostResponseResolved() {
        postResponseResolved = true;
        endAwaitingPostResponse();
        clearPersistentStatusMessages();
    }

    function shouldSuppressPostFetchError() {
        return postResponseResolved || isResponseVisibleInDom(null);
    }

    function resetPostResponseTracking() {
        postResponseResolved = false;
        awaitingPostResponse = false;
    }

    function endAwaitingPostResponse() {
        awaitingPostResponse = false;
    }

    function clearSubmitWatchdog() {
        if (submitWatchdogTimer) {
            clearTimeout(submitWatchdogTimer);
            submitWatchdogTimer = null;
        }
    }

    function armSubmitWatchdog() {
        clearSubmitWatchdog();
        submitWatchdogTimer = setTimeout(function () {
            if (!isSubmitting) {
                return;
            }
            console.warn('Submit watchdog: resetting stuck submitting state');
            endAwaitingPostResponse();
            dismissTypingIndicator(null, { force: true });
            removeProcessingMessage();
            removeStreamingAdviceBubble();
            removeStreamingMedicineCards();
                removeStreamingChatBubble();
                removeStreamingQaResponse();
            clearSlowRequestTimer();
            restoreSubmitButton();
            showErrorMessage('処理がタイムアウトしました。もう一度お試しください。');
        }, SUBMIT_WATCHDOG_MS);
    }

    function usesChatSse() {
        return window.CHAT_USE_SSE !== false && !!window.ChatSSE;
    }

    function getChatSubmitButton() {
        return document.querySelector('#chatForm button[type="submit"]');
    }

    function isSageSendButton(btn) {
        return !!(btn && btn.classList && btn.classList.contains('ui-send'));
    }

    function setChatSendButtonState(btn, mode) {
        if (!btn) return;
        const t = translations[currentLanguage] || translations[DEFAULT_LANGUAGE] || {};
        if (isSageSendButton(btn)) {
            if (mode === 'busy') {
                btn.textContent = '…';
                btn.setAttribute('aria-busy', 'true');
            } else {
                btn.textContent = '➤';
                btn.removeAttribute('aria-busy');
                btn.title = t.send || '送信';
                btn.setAttribute('aria-label', t.send || '送信');
            }
            return;
        }
        if (mode === 'busy') {
            btn.innerHTML = t.sendButton || '⏳ 処理中...';
        } else {
            btn.textContent = t.send || '送信';
        }
    }
    
    const chatFormEl = document.getElementById('chatForm');
    if (!chatFormEl) {
        console.error('chatForm element not found — message submit disabled');
    } else {
    chatFormEl.addEventListener('submit', function(e) {
        try {
            e.preventDefault();
            const input = document.getElementById('messageInput');
            if (!input) {
                console.error('messageInput element not found');
                return;
            }
            const message = input.value.trim();
            
            if (message === '') {
                return;
            }

            const nowMs = Date.now();
            if (
                message === lastSubmitPayload.message &&
                nowMs - lastSubmitPayload.at < SUBMIT_DEBOUNCE_MS
            ) {
                return;
            }
            lastSubmitPayload = { message: message, at: nowMs };
            
            // 送信処理中の場合
            if (isSubmitting) {
                showProcessingMessage();
                return;
            }
            
            // 送信処理開始
            isSubmitting = true;
            resetPostResponseTracking();
            armSubmitWatchdog();
            
            // 送信ボタンを無効化
            const submitBtn = getChatSubmitButton();
            if (submitBtn) {
                submitBtn.disabled = true;
                setChatSendButtonState(submitBtn, 'busy');
                submitBtn.style.background = isSageSendButton(submitBtn) ? '' : '#6c757d';
                submitBtn.style.cursor = 'not-allowed';
            }
            
            // 入力フィールドを無効化
            input.disabled = true;
            const tBusy = translations[currentLanguage] || translations[DEFAULT_LANGUAGE] || {};
            input.placeholder = tBusy.processingPlaceholder || 'AI処理中です。しばらくお待ちください...';

            // 直近のユーザーメッセージを保存（重複防止の補助や評価用）
            try {
                sessionStorage.setItem('lastUserMessage', message);
            } catch (e) {}

            // 進捗表示は UI 言語ではなく入力言語に合わせる
            if (window.ProcessingStatus && typeof ProcessingStatus.detectInputLanguage === 'function') {
                ProcessingStatus.setProcessingLanguage(
                    ProcessingStatus.detectInputLanguage(message, currentLanguage)
                );
            }
            
            // イースターエッグチェック（通常処理より優先）
            if (typeof checkEasterEggs === 'function' && checkEasterEggs(message)) {
                // イースターエッグ発動時は通常処理をスキップ
                // 入力フィールドをクリア（イースターエッグ発動時もクリアする）
                input.value = '';
                resizeMessageInput(input);
                isSubmitting = false;
                restoreSubmitButton();
                return;
            }
            
            // 入力フィールドをクリア
            input.value = '';
            resizeMessageInput(input);
            
            // ユーザーメッセージを即座に表示
            addUserMessage(message);
            
            // タイピングインジケーターを表示
            addTypingIndicator();
            
            // チャットを最下部にスクロール
            scrollToBottom();
            
            // フォームを送信
            submitForm(message);
        } catch (error) {
            // Chrome拡張機能関連のエラーを無視
            if (!error.message || !error.message.includes('chrome-extension')) {
                console.log('Form submit error:', error);
            }
            // 送信中フラグをリセット
            isSubmitting = false;
            restoreSubmitButton();
        }
    });
    }

    // 前回の送信中断などでボタンが無効のまま残っている場合に復旧
    restoreSubmitButton();

    function setupChatInputHandlers() {
        const input = document.getElementById('messageInput');
        const form = document.getElementById('chatForm');
        if (!input || !form) {
            console.error('chat input handlers skipped: messageInput or chatForm missing');
            return;
        }
        input.addEventListener('keydown', function (e) {
            try {
                if (e.key !== 'Enter' || e.isComposing) {
                    return;
                }
                if (e.altKey || e.ctrlKey) {
                    e.preventDefault();
                    if (typeof form.requestSubmit === 'function') {
                        form.requestSubmit();
                    } else {
                        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                    }
                }
            } catch (error) {
                if (!error.message || !error.message.includes('chrome-extension')) {
                    console.log('Keydown event error:', error);
                }
            }
        });
        input.addEventListener('input', function () {
            try {
                resizeMessageInput(this);
            } catch (error) {
                if (!error.message || !error.message.includes('chrome-extension')) {
                    console.log('Input event error:', error);
                }
            }
        });
    }
    setupChatInputHandlers();

    // ユーザーメッセージをチャット画面に追加
    function addUserMessage(message) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';
        messageDiv.setAttribute('data-message-id', pendingUserDomKey(message));
        messageDiv.setAttribute('data-temporary', 'true'); // 一時的なマーク
        messageDiv.innerHTML = `
            <div class="message-content">${escapeHtml(message)}</div>
        `;
        chatMessages.appendChild(messageDiv);
        // メッセージ追加後、雪のコンテナの高さを更新
        updateSnowContainerHeight();
    }

    // ボットメッセージをチャット画面に追加
    function addMessage(message, type, timestamp) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const timeStr = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
        
        // 改行を<br>タグに変換
        const formattedMessage = formatPlainBotText(message);
        
        messageDiv.innerHTML = `
            <div class="message-content">${formattedMessage}</div>
        `;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 危機対応相談先情報を表示する関数
    function displayCrisisSupportResources(message) {
        if (!message.crisis_support || !message.resources) {
            return '';
        }
        
        const t = translations[currentLanguage];
        let resourcesHtml = `
            <div class="crisis-support-card">
                <div class="crisis-support-title">${message.crisis_title || t.crisisSupportTitle}</div>
                <div class="crisis-support-message">${message.content || t.crisisSupportMessage}</div>
                <div class="crisis-support-message">信頼できる相談先をご紹介します：</div>
        `;
        
        message.resources.forEach(resource => {
            resourcesHtml += `
                <div class="resource-item">
                    <div class="resource-name">${resource.name}</div>
                    <div class="resource-org">${resource.organization}</div>
            `;
            
            if (resource.phone) {
                resourcesHtml += `<div class="resource-contact">📞 ${resource.phone}</div>`;
            }
            if (resource.line) {
                resourcesHtml += `<div class="resource-contact">💬 <a href="${resource.line}" target="_blank" class="resource-link">LINEで相談する</a></div>`;
            }
            if (resource.line_qr) {
                resourcesHtml += `<div class="resource-contact" style="margin-top: 10px;">
                    <div style="font-size: 14px; margin-bottom: 5px;">📱 QRコードで追加:</div>
                    <img src="${resource.line_qr}" alt="LINE QRコード" style="width: 120px; height: 120px; border: 1px solid #ddd; border-radius: 8px;">
                </div>`;
            }
            if (resource.website) {
                resourcesHtml += `<div class="resource-contact">🌐 <a href="${resource.website}" target="_blank" class="resource-link">ウェブサイト</a></div>`;
            }
            if (resource.hours) {
                resourcesHtml += `<div class="resource-contact">⏰ ${resource.hours}</div>`;
            }
            
            resourcesHtml += `<div class="resource-description">${resource.description}</div></div>`;
        });
        
        if (message.emergency_message) {
            resourcesHtml += `<div class="emergency-message">${message.emergency_message}</div>`;
        }
        
        resourcesHtml += '</div>';
        return resourcesHtml;
    }

    // staticテンプレート変数（{{ version }}）はJSファイル内では展開されないため、
    // index.html から注入された window.APP_VERSION を参照してキャッシュバスターを付与する。
    function normalizeInjectedAppVersion(v) {
        if (v === undefined || v === null) return '';
        let s = String(v).trim();
        if (!s) return '';
        if (/%7[bB]|%7[dD]/.test(s)) {
            try {
                const dec = decodeURIComponent(s.replace(/\+/g, ' '));
                if (dec) s = dec.trim();
            } catch (e) { /* ignore */ }
        }
        if (/^\{\{\s*version\s*\}\}$/i.test(s)) return '';
        if (s.includes('{{') && s.includes('}}')) return '';
        return s;
    }
    const APP_VERSION = normalizeInjectedAppVersion(window.APP_VERSION);

    function withVersion(url) {
        if (!APP_VERSION) return url;
        const sep = url.includes('?') ? '&' : '?';
        return `${url}${sep}v=${encodeURIComponent(APP_VERSION)}`;
    }

    /** メインチャット用パス（/test 配下では /test/clear など）。API (/api/...) には使わない。 */
    function mainAppPath(path) {
        const raw = (typeof window.APP_BASE_PATH === 'string') ? window.APP_BASE_PATH.trim() : '';
        const base = raw.replace(/\/$/, '');
        if (!path.startsWith('/')) {
            path = '/' + path;
        }
        if (path === '/') {
            return base ? base + '/' : '/';
        }
        return base + path;
    }

    // --- タブを開いている間のチャット履歴バックアップ（sessionStorage） ---
    const CHAT_CACHE_PREFIX = 'mrc_chat_cache:';
    const CHAT_RESTORE_DONE_PREFIX = 'mrc_restore_done:';
    /** 新セッション・履歴クリア直後はキャッシュ復元を無効化（reload 後も有効） */
    const SESSION_RESET_KEY = 'mrc_session_reset';
    const SID_COOKIE_NAME = 'sid';
    const SID_LOCAL_STORAGE_KEY = 'mrc_sid';
    let chatRestoreInFlight = false;
    let lastRenderedMessagesFingerprint = '';

    function getSidFromCookie() {
        const pattern = new RegExp('(?:^|;\\s*)' + SID_COOKIE_NAME + '=([^;]*)');
        const match = document.cookie.match(pattern);
        if (match) {
            return decodeURIComponent(match[1]);
        }
        return '';
    }

    function rememberSid(sid) {
        if (!sid) {
            return;
        }
        try {
            localStorage.setItem(SID_LOCAL_STORAGE_KEY, sid);
        } catch (e) { /* ignore */ }
    }

    function markSessionReset() {
        try {
            sessionStorage.setItem(SESSION_RESET_KEY, '1');
        } catch (e) { /* ignore */ }
    }

    function isSessionResetPending() {
        try {
            return sessionStorage.getItem(SESSION_RESET_KEY) === '1';
        } catch (e) {
            return false;
        }
    }

    function consumeSessionReset() {
        if (!isSessionResetPending()) {
            return false;
        }
        try {
            sessionStorage.removeItem(SESSION_RESET_KEY);
        } catch (e) { /* ignore */ }
        return true;
    }

    function chatCacheKey(sid) {
        const id = (sid || getSidFromCookie() || '').trim();
        if (!id) {
            return null;
        }
        return CHAT_CACHE_PREFIX + id;
    }

    function loadChatCache(sid) {
        const key = chatCacheKey(sid);
        if (!key) {
            return [];
        }
        try {
            const raw = sessionStorage.getItem(key);
            if (!raw) {
                return [];
            }
            const parsed = JSON.parse(raw);
            return Array.isArray(parsed.messages) ? parsed.messages : [];
        } catch (e) {
            console.warn('loadChatCache failed:', e);
            return [];
        }
    }

    function saveChatCache(sid, messages) {
        if (!messages || messages.length === 0 || isSessionResetPending()) {
            return;
        }
        const key = chatCacheKey(sid);
        if (!key) {
            return;
        }
        try {
            sessionStorage.setItem(
                key,
                JSON.stringify({ messages: messages, updatedAt: Date.now() })
            );
        } catch (e) {
            console.warn('saveChatCache failed:', e);
        }
    }

    function clearChatCache(sid) {
        const id = (sid || getSidFromCookie() || '').trim();
        if (id) {
            sessionStorage.removeItem(CHAT_CACHE_PREFIX + id);
            sessionStorage.removeItem(CHAT_RESTORE_DONE_PREFIX + id);
        }
        lastRenderedMessagesFingerprint = '';
    }

    const BLOCKED_USER_PLACEHOLDER = '（この入力はブロックされました）';

    /** サーバーに直近送信分の user が確定したら、楽観表示の一時バブルを除去してよい */
    function sessionHasResolvedUserMessage(messages) {
        const lastUser = (sessionStorage.getItem('lastUserMessage') || '').trim();
        if (!lastUser || !Array.isArray(messages) || messages.length === 0) {
            return false;
        }
        return messages.some(function (m) {
            if (!m || m.type !== 'user') {
                return false;
            }
            const content = String(m.content || '').trim();
            return content === lastUser || content === BLOCKED_USER_PLACEHOLDER;
        });
    }

    function stableMessageKey(message) {
        if (message && message.uuid) {
            return 'u:' + message.uuid;
        }
        if (message && message.message_id) {
            return 'm:' + message.message_id;
        }
        const ts = (message && message.timestamp) ? String(message.timestamp) : '';
        const type = (message && message.type) ? String(message.type) : '';
        const content = (message && message.content) ? String(message.content).slice(0, 200) : '';
        return 'c:' + type + ':' + ts + ':' + content;
    }

    /** 送信直後の楽観 user バブル用 DOM キー（サーバー uuid 確定前） */
    function pendingUserDomKey(text) {
        return 'pending-user:' + String(text || '').trim().slice(0, 200);
    }

    /** data-message-id と message.type（user/bot）が一致するノードのみ返す */
    function getMessageNodeByKey(chatMessages, messageKey, messageType) {
        if (!chatMessages || !messageKey || !messageType) {
            return null;
        }
        const node = chatMessages.querySelector('[data-message-id="' + CSS.escape(messageKey) + '"]');
        if (!node || !node.classList.contains('message') || !node.classList.contains(messageType)) {
            return null;
        }
        return node;
    }

    function isMessageNodeInDom(chatMessages, message, messageKey) {
        if (!chatMessages || !message || !message.type) {
            return false;
        }
        const key = messageKey || getMessageDomKey(message);
        return !!getMessageNodeByKey(chatMessages, key, message.type);
    }

    function takeExistingNodeForMessage(existingNodes, message) {
        if (!message || !message.type) {
            return null;
        }
        const key = getMessageDomKey(message);
        const node = existingNodes.get(key);
        if (!node) {
            return null;
        }
        if (!node.classList.contains(message.type)) {
            return null;
        }
        existingNodes.delete(key);
        if (node.parentNode) {
            node.remove();
        }
        return node;
    }

    function findLastUserMessageInList(messages) {
        const list = Array.isArray(messages) ? messages : [];
        for (let i = list.length - 1; i >= 0; i--) {
            if (list[i] && list[i].type === 'user') {
                return list[i];
            }
        }
        return null;
    }

    /** 直近ターンの user が DOM にあるか（楽観バブル・確定 uuid・直前 bot より後） */
    function isLatestUserMessageRendered(messages) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) {
            return false;
        }
        const lastUserMsg = findLastUserMessageInList(messages);
        const lastUserText = lastUserMsg
            ? String(lastUserMsg.content || '').trim()
            : (sessionStorage.getItem('lastUserMessage') || '').trim();
        if (!lastUserText) {
            return true;
        }
        if (lastUserMsg) {
            if (getMessageNodeByKey(chatMessages, stableMessageKey(lastUserMsg), 'user')) {
                return true;
            }
            if (getMessageNodeByKey(chatMessages, pendingUserDomKey(lastUserText), 'user')) {
                return true;
            }
        }
        const userNodes = chatMessages.querySelectorAll('.message.user');
        if (userNodes.length === 0) {
            return false;
        }
        const lastUserNode = userNodes[userNodes.length - 1];
        const nodeText = (lastUserNode.querySelector('.message-content')?.textContent || '').trim();
        if (nodeText !== lastUserText && nodeText !== BLOCKED_USER_PLACEHOLDER) {
            return false;
        }
        const lastBotMsg = findLastBotMessage(messages);
        if (!lastBotMsg) {
            return true;
        }
        const botKey = stableMessageKey(lastBotMsg);
        let lastBotNode = getMessageNodeByKey(chatMessages, botKey, 'bot');
        if (!lastBotNode) {
            const botNodes = chatMessages.querySelectorAll('.message.bot:not([data-initial-message="true"])');
            if (botNodes.length === 0) {
                return false;
            }
            lastBotNode = botNodes[botNodes.length - 1];
        }
        return !!(lastBotNode.compareDocumentPosition(lastUserNode) & Node.DOCUMENT_POSITION_FOLLOWING);
    }

    /** 直近ターン（user + bot）が DOM に揃っているか */
    function isLatestTurnRenderedInDom(messages) {
        if (!isBotResponseRendered(messages)) {
            return false;
        }
        return isLatestUserMessageRendered(messages);
    }

    function findLastBotMessage(messages) {
        const list = Array.isArray(messages) ? messages : [];
        for (let i = list.length - 1; i >= 0; i--) {
            const m = list[i];
            if (m && m.type === 'bot' && !m.error) {
                return m;
            }
        }
        return null;
    }

    function dedupeMessageList(messages) {
        const list = Array.isArray(messages) ? messages : [];
        const seen = new Set();
        const out = [];
        list.forEach(function(m) {
            const k = stableMessageKey(m);
            if (!m || seen.has(k)) {
                return;
            }
            seen.add(k);
            out.push(m);
        });
        return out;
    }

    function messagesFingerprint(messages) {
        return dedupeMessageList(messages).map(stableMessageKey).join('\n');
    }

    /** 最新 bot 応答がチャット DOM に既に描画されているか */
    function isBotResponseRendered(messages) {
        if (!isChatResponseComplete(messages)) {
            return false;
        }
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) {
            return false;
        }
        const lastBotMsg = findLastBotMessage(messages) || messages[messages.length - 1];
        if (!lastBotMsg || lastBotMsg.type !== 'bot') {
            return false;
        }
        const key = stableMessageKey(lastBotMsg);
        if (getMessageNodeByKey(chatMessages, key, 'bot')) {
            return true;
        }
        if (lastBotMsg.uuid || lastBotMsg.message_id) {
            return false;
        }
        if (lastBotMsg.store_inquiry) {
            const storeBots = chatMessages.querySelectorAll(
                '.message.bot:not(#currentTypingIndicator) .message-content'
            );
            for (let i = storeBots.length - 1; i >= 0; i--) {
                const html = storeBots[i].innerHTML || '';
                if (html.indexOf('store-inquiry') !== -1 || html.indexOf('トイレ') !== -1 || html.length > 80) {
                    return true;
                }
            }
        }
        const normalized = String(lastBotMsg.content || '').replace(/\s+/g, ' ').trim().slice(0, 120);
        if (!normalized) {
            return false;
        }
        const botNodes = chatMessages.querySelectorAll(
            '.message.bot:not([data-initial-message="true"]):not(#currentTypingIndicator)'
        );
        if (botNodes.length === 0) {
            return false;
        }
        const lastBotNode = botNodes[botNodes.length - 1];
        const text = (lastBotNode.textContent || '').replace(/\s+/g, ' ').trim();
        if (!text) {
            return false;
        }
        const snippet = normalized.slice(0, 80);
        return text.includes(snippet) || normalized.includes(text.slice(0, 80));
    }

    /** ストリーミングまたは確定 bot が画面上に見えているか */
    function isResponseVisibleInDom(messages) {
        if (hasActiveStreamingContent()) {
            return true;
        }
        if (messages && messages.length > 0 && isChatResponseComplete(messages)) {
            return isLatestTurnRenderedInDom(messages);
        }
        return isBotResponseRendered(messages);
    }

    /**
     * 処理バブルを除去（応答が見えるまで維持）。
     * @param {Array|null} messages - セッションメッセージ（任意）
     * @param {{force?: boolean}} options - force:true はエラー時など即除去
     */
    function dismissTypingIndicator(messages, options) {
        const opts = options || {};
        if (opts.force) {
            removeTypingIndicator();
            return;
        }
        if (isResponseVisibleInDom(messages)) {
            removeTypingIndicator();
            return;
        }
        if (messages && messages.length > 0) {
            removeTypingIndicatorWhenBotReady(messages);
            return;
        }
        if (hasActiveStreamingContent()) {
            removeTypingIndicator();
        }
    }

    /** ストリーミングチャンクを描画してからバブルを外す（先消しの空白を防ぐ） */
    function revealStreamingChunk(appendFn) {
        appendFn();
        requestAnimationFrame(function () {
            dismissTypingIndicator(null);
        });
    }

    let deferredRecoveryToken = 0;

    /**
     * 末尾が未応答の user（楽観表示）だけのとき修復し、bot を末尾に戻す。
     */
    function normalizeTurnTail(messages, botMsg, userMsg, lastUserText) {
        let msgs = dedupeMessageList(Array.isArray(messages) ? messages.slice() : []);
        if (!botMsg) {
            return msgs;
        }
        const botKey = stableMessageKey(botMsg);
        const lastUser = (lastUserText || '').trim();

        while (msgs.length > 0 && msgs[msgs.length - 1].type === 'user') {
            const tail = msgs[msgs.length - 1];
            const tailText = String(tail.content || '').trim();
            const isServerConfirmed = !!(tail.uuid || tail.message_id);
            const isPending =
                !isServerConfirmed &&
                ((lastUser && tailText === lastUser) ||
                    (userMsg && stableMessageKey(tail) === stableMessageKey(userMsg)));
            if (!isPending) {
                break;
            }
            msgs.pop();
        }

        const userCandidate =
            userMsg ||
            (lastUser
                ? { type: 'user', content: lastUser, timestamp: new Date().toISOString() }
                : null);

        if (userCandidate) {
            const uKey = stableMessageKey(userCandidate);
            if (!msgs.some(function (m) {
                return stableMessageKey(m) === uKey;
            })) {
                msgs.push(userCandidate);
            }
        }

        if (!msgs.some(function (m) {
            return stableMessageKey(m) === botKey;
        })) {
            msgs.push(botMsg);
        }

        return dedupeMessageList(msgs);
    }

    /** 重複送信などで末尾 user だけ残ったキャッシュを修復 */
    function repairOrphanPendingUser(messages, lastUserText) {
        const msgs = dedupeMessageList(Array.isArray(messages) ? messages.slice() : []);
        const lastUser = (lastUserText || '').trim();
        if (!lastUser || msgs.length === 0 || msgs[msgs.length - 1].type === 'bot') {
            return msgs;
        }
        const tail = msgs[msgs.length - 1];
        if (tail.type !== 'user' || String(tail.content || '').trim() !== lastUser) {
            return msgs;
        }
        if (tail.uuid || tail.message_id) {
            return msgs;
        }
        const without = msgs.slice(0, -1);
        if (without.length > 0 && without[without.length - 1].type === 'bot') {
            return without;
        }
        return msgs;
    }

    /** セッションを正規化して bot 応答を画面に反映できるなら true */
    function completePostResponseIfReady(sessionData, donePayload) {
        const lastUser = (sessionStorage.getItem('lastUserMessage') || '').trim();
        let merged = resolveSessionMessages(sessionData || {}, { allowRestore: false });

        if (donePayload && donePayload.bot_message) {
            merged = normalizeTurnTail(
                merged,
                donePayload.bot_message,
                donePayload.user_message,
                lastUser
            );
        } else {
            merged = repairOrphanPendingUser(merged, lastUser);
            const orphanBot = findLastBotMessage(merged);
            if (orphanBot && !isChatResponseComplete(merged)) {
                merged = normalizeTurnTail(merged, orphanBot, null, lastUser);
            }
        }

        if (!isChatResponseComplete(merged)) {
            return false;
        }

        const sid = (sessionData && sessionData.session_id) || getSidFromCookie();
        saveChatCache(sid, merged);
        const turnAlreadyVisible = isLatestTurnRenderedInDom(merged);
        const applied = applyBotResponseSession(
            { session_id: sid, messages: merged },
            {
                preserveStatusCards: false,
                forceRender: !turnAlreadyVisible,
            }
        );
        if (applied) {
            markPostResponseResolved();
        }
        return applied;
    }

    function mergeMessageLists(serverMsgs, localMsgs) {
        const server = Array.isArray(serverMsgs) ? serverMsgs : [];
        const local = Array.isArray(localMsgs) ? localMsgs : [];
        if (local.length === 0) {
            return dedupeMessageList(server);
        }
        if (server.length === 0) {
            return dedupeMessageList(local);
        }
        const seen = new Set();
        const merged = [];
        server.forEach(function(m) {
            const k = stableMessageKey(m);
            if (!m || seen.has(k)) {
                return;
            }
            seen.add(k);
            merged.push(m);
        });
        local.forEach(function(m) {
            const k = stableMessageKey(m);
            if (!m || seen.has(k)) {
                return;
            }
            seen.add(k);
            merged.push(m);
        });
        return dedupeMessageList(merged);
    }

    function maybeRestoreSessionToServer(messages, sid) {
        const sessionId = sid || getSidFromCookie();
        if (
            chatRestoreInFlight
            || isSessionResetPending()
            || !messages
            || messages.length === 0
            || !sessionId
        ) {
            return;
        }
        if (sessionStorage.getItem(CHAT_RESTORE_DONE_PREFIX + sessionId) === '1') {
            return;
        }
        chatRestoreInFlight = true;
        fetch(withVersion('/api/sessions/restore'), {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            body: JSON.stringify({ messages: dedupeMessageList(messages) })
        })
            .then(function(res) {
                return res.ok ? res.json() : null;
            })
            .then(function(data) {
                if (data && (data.restored || data.messages_count > 0)) {
                    sessionStorage.setItem(CHAT_RESTORE_DONE_PREFIX + sessionId, '1');
                }
            })
            .catch(function(err) {
                console.warn('session restore failed:', err);
            })
            .finally(function() {
                chatRestoreInFlight = false;
            });
    }

    function resolveSessionMessages(sessionData, options) {
        const opts = options || {};
        const sid = (sessionData && sessionData.session_id) || getSidFromCookie();
        const server = dedupeMessageList((sessionData && sessionData.messages) ? sessionData.messages : []);
        if (isSessionResetPending()) {
            return server;
        }
        const cached = dedupeMessageList(loadChatCache(sid));
        const merged = mergeMessageLists(server, cached);

        if (server.length === 0 && merged.length > 0 && opts.allowRestore !== false) {
            saveChatCache(sid, merged);
            maybeRestoreSessionToServer(merged, sid);
        } else if (merged.length > 0) {
            saveChatCache(sid, merged);
        }
        return merged;
    }

    function applySessionMessages(sessionData, options) {
        let opts = Object.assign({}, options || {});
        if (shouldDeferSessionSync() && !opts.allowWhileStreaming && !opts.periodicSync) {
            updateSessionSafetyBanners(sessionData);
            return;
        }
        const merged = resolveSessionMessages(sessionData || {}, {
            allowRestore: opts.allowRestore !== false
        });
        if (merged.length === 0) {
            return;
        }
        if (isChatResponseComplete(merged)) {
            opts = Object.assign({ suppressTypingIndicator: true }, opts);
        }
        const fp = messagesFingerprint(merged);
        const turnRendered = isLatestTurnRenderedInDom(merged);
        if (!opts.forceRender && fp === lastRenderedMessagesFingerprint) {
            if (opts.suppressTypingIndicator && isBotResponseRendered(merged)) {
                dismissTypingIndicator(merged);
            }
            if (turnRendered) {
                updateSessionSafetyBanners(sessionData);
                refreshSageSafetyRail((sessionData && sessionData.user_attributes) || {});
                return;
            }
            opts = Object.assign({ forceRender: true }, opts);
        }
        renderChatMessages(merged, opts);
        if (isLatestTurnRenderedInDom(merged)) {
            lastRenderedMessagesFingerprint = fp;
        }
        updateSessionSafetyBanners(sessionData);
        const attrs = (sessionData && sessionData.user_attributes) || {};
        if (attrs && Object.keys(attrs).length) {
            window.__lastUserAttributes = attrs;
        }
        refreshSageSafetyRail(attrs);
    }

    /** 10秒ポーリング・デバウンス復旧用: サーバーに応答があるのに DOM 未反映なら強制同期 */
    function applyPeriodicSessionSync(sessionData) {
        const merged = resolveSessionMessages(sessionData || {}, { allowRestore: false });
        if (merged.length === 0) {
            return;
        }
        const typingEl = document.getElementById('currentTypingIndicator');
        if (typingEl && (awaitingPostResponse || isSubmitting)) {
            if (completePostResponseIfReady(sessionData, null)) {
                return;
            }
        }
        if (isChatResponseComplete(merged) && !isLatestTurnRenderedInDom(merged)) {
            endAwaitingPostResponse();
            isSubmitting = false;
            clearPersistentStatusMessages();
            dismissTypingIndicator(merged, { force: true });
            restoreSubmitButton();
            applySessionMessages(sessionData, {
                allowRestore: false,
                forceRender: true,
                suppressTypingIndicator: true,
                periodicSync: true,
            });
            return;
        }
        if (!shouldDeferSessionSync()) {
            applySessionMessages(sessionData, {
                allowRestore: false,
                periodicSync: true,
            });
            return;
        }
        if (isChatResponseComplete(merged)) {
            applySessionMessages(sessionData, {
                allowRestore: false,
                forceRender: !isLatestTurnRenderedInDom(merged),
                suppressTypingIndicator: true,
                allowWhileStreaming: true,
                periodicSync: true,
            });
        }
    }

    /** bot / ストリーミングが DOM に載るまでバブルを維持 */
    function removeTypingIndicatorWhenBotReady(messages, attempt) {
        if (isResponseVisibleInDom(messages)) {
            removeTypingIndicator();
            return;
        }
        const next = (attempt || 0) + 1;
        if (next >= 48) {
            scheduleDeferredSessionRecovery(chatSubmitGeneration, 0);
            return;
        }
        requestAnimationFrame(function () {
            removeTypingIndicatorWhenBotReady(messages, next);
        });
    }

    function isInternalClientErrorMessage(message) {
        const msg = String(message || '').toLowerCase();
        return (
            msg.includes('assignment to constant')
            || msg.includes('typeerror')
            || msg.includes('referenceerror')
            || msg.includes('syntaxerror')
            || msg.includes('is not defined')
        );
    }

    /** SSE done 後に応答反映・バブル除去・送信ボタン復帰を試みる */
    function unlockPostResponseUI(donePayload) {
        try {
            const sid = getSidFromCookie();
            let payload = donePayload;
            if (payload && !payload.bot_message) {
                const cachedBot = findLastBotMessage(loadChatCache(sid));
                if (cachedBot) {
                    payload = Object.assign({}, payload, { bot_message: cachedBot });
                }
            }

            let resolved = completePostResponseIfReady(
                { session_id: sid, messages: loadChatCache(sid) },
                payload
            );

            if (!resolved) {
                const lastUser = (sessionStorage.getItem('lastUserMessage') || '').trim();
                let merged = repairOrphanPendingUser(
                    resolveSessionMessages({ session_id: sid, messages: loadChatCache(sid) }, { allowRestore: false }),
                    lastUser
                );
                const lastBot = findLastBotMessage(merged);
                if (lastBot && !isChatResponseComplete(merged)) {
                    merged = normalizeTurnTail(merged, lastBot, null, lastUser);
                    saveChatCache(sid, merged);
                    resolved = applyBotResponseSession(
                        { session_id: sid, messages: merged },
                        { preserveStatusCards: false, forceRender: true }
                    );
                }
            }

            if (!resolved && isResponseVisibleInDom(null)) {
                dismissTypingIndicator(null, { force: true });
                restoreSubmitButton();
                markPostResponseResolved();
                return true;
            }

            if (!resolved && !postResponseResolved) {
                scheduleDeferredSessionRecovery(chatSubmitGeneration, 0);
            }
            return resolved;
        } catch (err) {
            console.error('unlockPostResponseUI failed:', err);
            if (!postResponseResolved) {
                scheduleDeferredSessionRecovery(chatSubmitGeneration, 0);
            }
            return false;
        }
    }

    /** SSE done ペイロードの bot を即描画（/api/sessions 待ちの空白を短縮） */
    function applyInstantBotFromSseDone(donePayload) {
        return unlockPostResponseUI(donePayload);
    }

    /** 引継ぎ完了〜bot 描画まで処理バブルを維持し、ラベルのみ切り替える */
    function handoffFinalizeTypingIndicator() {
        const el = document.getElementById('currentTypingIndicator');
        if (!el) {
            return;
        }
        const label = el.querySelector('.processing-status-label');
        const fill = el.querySelector('.processing-status-bar-fill');
        const pill = el.querySelector('.processing-status-step-pill');
        const track = el.querySelector('.processing-status-track');
        const t = translations[currentLanguage] || translations[DEFAULT_LANGUAGE] || {};
        const text = t.handoffFinalizing || '回答を表示しています';
        if (label) {
            label.textContent = text;
        }
        if (pill) {
            const doneLabel =
                (translations[currentLanguage] || translations[DEFAULT_LANGUAGE] || {}).processingDone ||
                '完了';
            pill.textContent = doneLabel;
        }
        if (fill) {
            fill.style.width = '100%';
        }
        if (track) {
            track.setAttribute('aria-valuenow', '100');
        }
    }

    /** bot 応答が揃ったセッションを反映（typing 除去・送信状態復帰・DOM 全消しを避ける） */
    function applyBotResponseSession(sessionData, options) {
        const opts = options || {};
        const merged = resolveSessionMessages(sessionData || {}, {
            allowRestore: opts.allowRestore !== false,
        });
        if (!isChatResponseComplete(merged)) {
            return false;
        }
        markPostResponseResolved();
        clearPersistentStatusMessages();
        if (window.ProcessingStatus && ProcessingStatus.stopProcessingPoll) {
            ProcessingStatus.stopProcessingPoll();
        }
        restoreSubmitButton();
        const chatMessages = document.getElementById('chatMessages');
        const wasAtBottom = chatMessages
            ? chatMessages.scrollTop + chatMessages.clientHeight >= chatMessages.scrollHeight - 10
            : false;
        applySessionMessages(sessionData, {
            preserveStatusCards: opts.preserveStatusCards !== false,
            forceRender: opts.forceRender === true || !isLatestTurnRenderedInDom(merged),
            suppressTypingIndicator: true,
            allowRestore: opts.allowRestore,
        });
        dismissTypingIndicator(merged, { force: true });
        if (chatMessages && wasAtBottom) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        if (!shouldDeferSessionSync()) {
            removeOrphanedStreamingBubbles();
        }
        return true;
    }

    function touchSessionActivity() {
        fetch(withVersion('/api/sessions/activity'), {
            method: 'PATCH',
            credentials: 'include',
            headers: { 'Cache-Control': 'no-cache' }
        }).catch(function() {});
    }

    function restoreChatToInitialView() {
        const chatEl = document.getElementById('chatMessages');
        if (!chatEl) {
            return;
        }
        chatEl.querySelectorAll('.message:not([data-initial-message="true"])').forEach(function (node) {
            node.remove();
        });
        const typing = document.getElementById('currentTypingIndicator');
        if (typing) {
            typing.remove();
        }
        if (!chatEl.querySelector('[data-initial-message="true"]')) {
            renderChatMessages([], {});
        } else {
            updateInitialMessage();
        }
    }

    // メッセージを再読み込み（初回ロード用）
    function loadMessages() {
        const hadReset = consumeSessionReset();
        if (hadReset) {
            clearAllChatSessionStorage();
        }
        fetch(withVersion('/api/sessions'), {
            credentials: 'include',
            headers: { 'Cache-Control': 'no-cache' }
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data && data.session_id) {
                    rememberSid(data.session_id);
                }
                if (hadReset && data && Array.isArray(data.messages) && data.messages.length === 0) {
                    lastRenderedMessagesFingerprint = '';
                    updateSessionSafetyBanners(data);
                    refreshSageSafetyRail((data.user_attributes) || {});
                    restoreChatToInitialView();
                    return;
                }
                applySessionMessages(data);
            })
            .catch(error => {
                const t = translations[currentLanguage];
                console.error(t.loadError + ':', error);
                if (hadReset || isSessionResetPending()) {
                    return;
                }
                const cached = loadChatCache(getSidFromCookie());
                if (cached.length > 0) {
                    renderChatMessages(cached);
                    maybeRestoreSessionToServer(cached, getSidFromCookie());
                }
            });
    }

    // 送信ボタンを元の状態に復元
    function restoreSubmitButton() {
        const submitBtn = getChatSubmitButton();
        const input = document.getElementById('messageInput');
        
        isSubmitting = false;
        clearSubmitWatchdog();
        clearSlowRequestTimer();
        try {
            sessionStorage.removeItem('chatSubmitBaselineLength');
        } catch (e) { /* ignore */ }
        if (submitBtn) {
            submitBtn.disabled = false;
            setChatSendButtonState(submitBtn, 'idle');
            submitBtn.style.background = '';
            submitBtn.style.cursor = '';
        }
        
        if (input) {
            input.disabled = false;
            const t = translations[currentLanguage] || translations[DEFAULT_LANGUAGE] || {};
            input.placeholder = t.placeholder || '症状を入力してください...';
        }
    }

    // 処理中メッセージを表示する関数
    function showProcessingMessage() {
        const chatMessages = document.getElementById('chatMessages');
        
        // 既存の処理中メッセージを削除
        const existingMessage = document.getElementById('processingMessage');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        // 新しい処理中メッセージを作成
        const processingDiv = document.createElement('div');
        processingDiv.id = 'processingMessage';
        processingDiv.className = 'message bot processing-message';
        processingDiv.innerHTML = `
            <div class="message-content" style="background: #e3f2fd; color: #1976d2; border: 1px solid #bbdefb; padding: 15px; border-radius: 8px; position: relative;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div class="spinner" style="width: 20px; height: 20px; border: 2px solid #f3f3f3; border-top: 2px solid #1976d2; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                    <div>
                        <strong>⏳ AI処理中です</strong><br>
                        <span style="font-size: 14px; color: #666;">少々お待ちください。処理が完了するまで新しいメッセージは送信できません。</span>
                    </div>
                </div>
                <div class="feedback-buttons" style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #495057;">処理に時間がかかっている場合は報告してください</p>
                    <button class="report-bug-btn" 
                        onclick="reportProcessingIssue()" 
                        style="background: #ff9800; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; min-width: 120px;">
                        🐛 不具合報告
                    </button>
                </div>
            </div>
        `;
        
        chatMessages.appendChild(processingDiv);
        scrollToBottom();
    }

    // 処理中メッセージを削除
    function removeProcessingMessage() {
        const processingMessage = document.getElementById('processingMessage');
        if (processingMessage) {
            processingMessage.remove();
        }
    }

    // 処理中の不具合報告機能
    function reportProcessingIssue() {
        const reportData = {
            user_message: sessionStorage.getItem('lastUserMessage') || '',
            ai_response: 'AI処理が長時間実行中',
            report_type: 'processing_timeout',
            feedback_text: 'AI処理に時間がかかりすぎています'
        };
        
        currentFeedbackData = reportData;
        feedbackTriggerElement = window.event ? (window.event.currentTarget || window.event.target) : null;
        openFeedbackModal();
    }

    function prepareFeedbackPayload(source, defaultReportType) {
        const payload = {
            report_type: defaultReportType,
            user_message: sessionStorage.getItem('lastUserMessage') || '',
            ai_response: '',
            security_score: null,
            feedback_text: '',
            is_google_form: false
        };

        if (typeof source === 'string') {
            const stored = sessionStorage.getItem(`message_${source}`);
            if (stored) {
                try {
                    const parsed = JSON.parse(stored);
                    if (parsed.user_message) {
                        payload.user_message = decodeHtmlEntities(parsed.user_message);
                    }
                    if (parsed.ai_response) {
                        payload.ai_response = decodeHtmlEntities(parsed.ai_response);
                    }
                    if (Object.prototype.hasOwnProperty.call(parsed, 'security_score')) {
                        payload.security_score = parsed.security_score;
                    }
                } catch (error) {
                    console.error('Failed to parse stored message payload:', error);
                }
            }
            payload.message_id = source;
        } else if (source && typeof source === 'object') {
            if (Object.prototype.hasOwnProperty.call(source, 'user_message')) {
                payload.user_message = decodeHtmlEntities(source.user_message);
            }
            if (Object.prototype.hasOwnProperty.call(source, 'ai_response')) {
                payload.ai_response = decodeHtmlEntities(source.ai_response);
            }
            if (Object.prototype.hasOwnProperty.call(source, 'security_score')) {
                const score = Number(source.security_score);
                payload.security_score = Number.isFinite(score) ? score : null;
            }
            if (Object.prototype.hasOwnProperty.call(source, 'report_type') && source.report_type) {
                payload.report_type = source.report_type;
            }
            if (Object.prototype.hasOwnProperty.call(source, 'feedback_text')) {
                payload.feedback_text = decodeHtmlEntities(source.feedback_text);
            }
        }

        if (!payload.ai_response) {
            const sageReco = typeof getLatestRecommendationRoot === 'function' ? getLatestRecommendationRoot() : null;
            const lastBotMessage = sageReco || document.querySelector('#chatMessages .message.bot:last-of-type .message-content');
            if (lastBotMessage) {
                payload.ai_response = lastBotMessage.innerText.trim();
            }
        }

        return payload;
    }

    function submitFeedbackPayload(payload, options = {}) {
        const { showThankYou = true } = options;
        const requestBody = {
            report_type: payload.report_type,
            user_message: payload.user_message || '',
            ai_response: payload.ai_response || '',
            security_score: payload.security_score,
            feedback_text: payload.feedback_text || '',
            is_google_form: payload.is_google_form || false,
            negative_reason: payload.negative_reason || null
        };

        return fetch('/api/submit_feedback', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            body: JSON.stringify(requestBody)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status !== 'success') {
                throw new Error(data.error || 'feedback_submission_failed');
            }
            if (showThankYou) {
                showSuccessModal(translations[currentLanguage].feedbackThankYou || 'フィードバックありがとうございます！');
            }
            return data;
        });
    }

    function markFeedbackCompleted(triggerElement, message) {
        if (!triggerElement) {
            return;
        }
        const container = triggerElement.closest('.feedback-buttons');
        if (!container) {
            return;
        }
        container.querySelectorAll('button').forEach(button => {
            button.disabled = true;
            button.style.opacity = '0.6';
            button.style.cursor = 'not-allowed';
        });

        if (message) {
            let notice = container.querySelector('.feedback-complete-message');
            if (!notice) {
                notice = document.createElement('p');
                notice.className = 'feedback-complete-message';
                notice.style.margin = '10px 0 0';
                notice.style.fontWeight = 'bold';
                notice.style.color = '#28a745';
                container.appendChild(notice);
            }
            notice.textContent = message;
        }
    }

    function handlePositiveFeedback(source) {
        try {
            const trigger = window.event ? (window.event.currentTarget || window.event.target) : null;
            feedbackTriggerElement = trigger;
            const payload = prepareFeedbackPayload(source, 'positive_feedback');
            submitFeedbackPayload(payload)
                .then(() => {
                    markFeedbackCompleted(trigger, translations[currentLanguage].feedbackThankYou || 'フィードバックありがとうございます！');
                })
                .catch(error => {
                    console.error('Positive feedback submission failed:', error);
                    alert('フィードバックの送信に失敗しました。時間をおいて再度お試しください。');
                })
                .finally(() => {
                    feedbackTriggerElement = null;
                });
        } catch (error) {
            console.error('handlePositiveFeedback error:', error);
        }
    }

    function handleNegativeFeedback(source) {
        try {
            feedbackTriggerElement = window.event ? (window.event.currentTarget || window.event.target) : null;
            currentFeedbackData = prepareFeedbackPayload(source, 'negative_feedback');
            openFeedbackModal();
        } catch (error) {
            console.error('handleNegativeFeedback error:', error);
        }
    }

    function handleSecurityReportFromButton(button) {
        try {
            feedbackTriggerElement = button;
            // security_scoreを取得（空文字列の場合はnullに変換）
            let securityScore = button?.dataset?.securityScore;
            if (securityScore === '' || securityScore === undefined) {
                securityScore = null;
            } else if (securityScore !== null) {
                // 数値に変換を試みる
                const score = Number(securityScore);
                securityScore = Number.isFinite(score) ? score : null;
            }
            
            const payloadSource = {
                user_message: button?.dataset?.userMessage || '',
                ai_response: button?.dataset?.aiResponse || '',
                security_score: securityScore,
                report_type: 'bug_report'
            };
            currentFeedbackData = prepareFeedbackPayload(payloadSource, 'bug_report');
            openFeedbackModal();
        } catch (error) {
            console.error('handleSecurityReportFromButton error:', error);
        }
    }

    function openFeedbackModal() {
        const modal = document.getElementById('feedbackModal');
        if (!modal) {
            return;
        }
        const textarea = document.getElementById('feedbackText');
        if (textarea) {
            textarea.value = currentFeedbackData && currentFeedbackData.feedback_text ? currentFeedbackData.feedback_text : '';
            textarea.placeholder = translations[currentLanguage].bugReportPrompt || textarea.placeholder;
            textarea.focus();
        }
        modal.style.display = 'flex';
    }

    function closeFeedbackModal(resetState = true) {
        const modal = document.getElementById('feedbackModal');
        if (modal) {
            modal.style.display = 'none';
        }
        const textarea = document.getElementById('feedbackText');
        if (textarea) {
            textarea.value = '';
        }
        const noRec = document.getElementById('feedbackNoRecommendation');
        if (noRec) {
            noRec.checked = false;
        }
        if (resetState) {
            currentFeedbackData = null;
            feedbackTriggerElement = null;
        }
    }

    function submitFeedback() {
        if (!currentFeedbackData) {
            alert('送信対象のフィードバック情報が見つかりません。');
            return;
        }

        const textarea = document.getElementById('feedbackText');
        const feedbackText = textarea ? textarea.value.trim() : '';
        const noRec = document.getElementById('feedbackNoRecommendation');
        const payload = {
            ...currentFeedbackData,
            feedback_text: feedbackText
        };
        if (noRec && noRec.checked) {
            payload.negative_reason = 'no_recommendation';
        }

        submitFeedbackPayload(payload)
            .then(() => {
                closeFeedbackModal(false);
                markFeedbackCompleted(feedbackTriggerElement, translations[currentLanguage].feedbackThankYou || 'フィードバックありがとうございます！');
                currentFeedbackData = null;
                feedbackTriggerElement = null;
                if (textarea) {
                    textarea.value = '';
                }
            })
            .catch(error => {
                console.error('Feedback submission failed:', error);
                alert('フィードバックの送信に失敗しました。時間をおいて再度お試しください。');
            });
    }

    function openGoogleForm() {
        window.open(GOOGLE_FORM_URL, '_blank', 'noopener');
    }

    function showSuccessModal(message) {
        const modal = document.getElementById('successModal');
        const messageElement = document.getElementById('successMessage');
        if (!modal || !messageElement) {
            return;
        }
        messageElement.textContent = message;
        modal.style.display = 'flex';
        setTimeout(() => {
            modal.style.display = 'none';
        }, 2000);
    }

    window.toggleLanguageMenu = toggleLanguageMenu;
    window.selectLanguage = selectLanguage;
    
    // イースターエッグ機能用のグローバル関数を公開
    window.addUserMessage = addUserMessage;
    window.addMessage = addMessage;
    window.scrollToBottom = scrollToBottom;
    window.handlePositiveFeedback = handlePositiveFeedback;
    window.handleNegativeFeedback = handleNegativeFeedback;
    window.handleSecurityReportFromButton = handleSecurityReportFromButton;
    window.openFeedbackModal = openFeedbackModal;
    window.closeFeedbackModal = closeFeedbackModal;
    window.submitFeedback = submitFeedback;
    window.openGoogleForm = openGoogleForm;

    function applySseProcessingStatus(data) {
        if (!data || !window.ProcessingStatus || !isSubmitting || postResponseResolved) {
            return;
        }
        const el = document.getElementById('currentTypingIndicator');
        if (!el) {
            return;
        }
        const localized = ProcessingStatus.localizeStatusData({
            active: true,
            step_id: data.step_id,
            label: data.label,
            detail_code: data.detail_code,
            detail_label: data.detail_label,
            step: data.step,
            total: data.total || 14,
            percent: data.percent || 0,
            language: data.language,
            flow_id: data.flow_id,
            flow_description: data.flow_description,
            flow_hint: data.flow_hint,
            agent_name: data.agent_name,
            agent_role: data.agent_role,
            agent_description: data.agent_description,
            agent_display: data.agent_display,
            slow_hint: data.slow_hint,
        });
        ProcessingStatus.renderProcessingStatus(el, localized);
    }

    function updateSessionSafetyBanners(sessionData) {
        const host = document.getElementById('chatMessages');
        if (!host) return;
        let bar = document.getElementById('session-safety-banners');
        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'session-safety-banners';
            bar.className = 'session-safety-banners';
            bar.style.cssText = 'margin: 8px 12px; display: flex; flex-direction: column; gap: 8px;';
            host.insertBefore(bar, host.firstChild);
        }
        bar.innerHTML = '';
        const data = sessionData || {};
        if (data.medical_emergency_otc_locked && !data.otc_lock_released) {
            const box = document.createElement('div');
            box.className = 'chat-status-card chat-status-card--caution';
            box.setAttribute('role', 'alert');
            box.innerHTML =
                '<div class="chat-status-card__header"><span class="chat-status-card__icon" aria-hidden="true">🚑</span>' +
                '<h4 class="chat-status-card__title">緊急対応後のご案内</h4></div>' +
                '<p class="chat-status-card__subtitle">市販薬の自己判断での選択はお控えください。緊急でないと判断できる場合のみ、相談を再開できます。</p>' +
                '<div class="chat-status-card__actions">' +
                '<button type="button" class="chat-status-card__btn chat-status-card__btn--primary" id="otc-unlock-btn">緊急ではないので相談を再開する</button>' +
                '</div>';
            bar.appendChild(box);
            const btn = box.querySelector('#otc-unlock-btn');
            if (btn) {
                btn.onclick = function () {
                    fetch(withVersion('/api/chat/otc_unlock'), { method: 'POST', credentials: 'include' })
                        .then(function (r) { return r.json(); })
                        .then(function () {
                            fetch(withVersion('/api/sessions'), { credentials: 'include' })
                                .then(function (r) { return r.json(); })
                                .then(updateSessionSafetyBanners)
                                .catch(function () {});
                        })
                        .catch(function () { showErrorMessage('解除に失敗しました'); });
                };
            }
        }
        if (data.store_incident_soft_banner) {
            const box = document.createElement('div');
            box.className = 'chat-status-card chat-status-card--notice';
            box.setAttribute('role', 'region');
            box.innerHTML =
                '<div class="chat-status-card__header"><span class="chat-status-card__icon" aria-hidden="true">🏪</span>' +
                '<h4 class="chat-status-card__title">店舗での対応を優先してください</h4></div>' +
                '<p class="chat-status-card__subtitle">スタッフへの連絡後、症状の相談が必要な場合のみ市販薬の相談を続けられます。</p>' +
                '<div class="chat-status-card__actions">' +
                '<button type="button" class="chat-status-card__btn chat-status-card__btn--primary" id="store-otc-optin-btn">症状の相談を続ける</button>' +
                '</div>';
            bar.appendChild(box);
            const btn = box.querySelector('#store-otc-optin-btn');
            if (btn) {
                btn.onclick = function () {
                    fetch(withVersion('/api/chat/store_incident_ack'), { method: 'POST', credentials: 'include' })
                        .then(function (r) { return r.json(); })
                        .then(function () {
                            fetch(withVersion('/api/sessions'), { credentials: 'include' })
                                .then(function (r) { return r.json(); })
                                .then(updateSessionSafetyBanners)
                                .catch(function () {});
                        })
                        .catch(function () { showErrorMessage('操作に失敗しました'); });
                };
            }
        }
        if (!bar.children.length) {
            bar.remove();
        }
    }
    window.updateSessionSafetyBanners = updateSessionSafetyBanners;

    function buildProcessingPollOptions(onUpdate) {
        return {
            onUpdate: onUpdate,
            onInactive: function () {
                // 処理 API が inactive でもセッション保存前のことがある。
                // バブルは bot 応答同期まで維持し、ポーリングのみ止める。
                if (window.ProcessingStatus && ProcessingStatus.stopProcessingPoll) {
                    ProcessingStatus.stopProcessingPoll();
                }
            },
            interval: 1000,
        };
    }

    // タイピングインジケーターを追加
    function addTypingIndicator() {
        // 処理中メッセージが既に表示されている場合は追加しない
        if (document.getElementById('processingMessage')) {
            return;
        }
        
        const chatMessages = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot';
        typingDiv.id = 'currentTypingIndicator';
        if (window.ProcessingStatus && ProcessingStatus.getTypingIndicatorHtml) {
            typingDiv.innerHTML = ProcessingStatus.getTypingIndicatorHtml();
        } else {
            typingDiv.innerHTML = '<div class="message-content"><div class="typing-indicator"><span>AIが診断中...</span></div></div>';
        }
        chatMessages.appendChild(typingDiv);
        attachSlowRequestButtonToTypingIndicator();
        scrollToBottom();

        if (!usesChatSse() && window.ProcessingStatus && ProcessingStatus.startProcessingPoll) {
            ProcessingStatus.startProcessingPoll(buildProcessingPollOptions(function (data) {
                const el = document.getElementById('currentTypingIndicator');
                if (!el || !data || !data.active) return;
                ProcessingStatus.renderProcessingStatus(el, data);
            }));
        }
    }

    // HTMLエスケープ関数
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /** エスケープ済みプレーンテキスト内の URL・メールをクリック可能にする */
    function linkifyEscapedHtml(escaped) {
        if (!escaped) {
            return '';
        }
        return escaped
            .replace(
                /(https?:\/\/[^\s<]+)/g,
                '<a href="$1" class="chat-link" target="_blank" rel="noopener noreferrer">$1</a>'
            )
            .replace(
                /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g,
                '<a href="mailto:$1" class="chat-link">$1</a>'
            );
    }

    function formatPlainBotText(text) {
        const escaped = escapeHtml(text || '');
        return linkifyEscapedHtml(escaped.replace(/\n/g, '<br>'));
    }

    /** 推奨結果用の diagnosis オブジェクトか（診断名検出時の diagnosis_type 文字列と区別） */
    function isDiagnosisPayload(diagnosis) {
        return diagnosis !== null && typeof diagnosis === 'object' && !Array.isArray(diagnosis);
    }

    function isStatusCardHtml(content) {
        if (!content || typeof content !== 'string') {
            return false;
        }
        if (
            content.includes('chat-status-card') ||
            content.includes('class="chat-status-card') ||
            content.includes("class='chat-status-card")
        ) {
            return true;
        }
        return /<div[^>]*\bchat-status-card\b/i.test(content);
    }

    function looksLikeHtmlContent(content) {
        if (!content || typeof content !== 'string') {
            return false;
        }
        return /<(?:div|p|section|ul|ol|h[1-6]|span|button|details|form)\b/i.test(content);
    }

    /** サーバー生成のステータスカードを bot メッセージ用に一貫してラップ */
    function wrapBotStatusCardHtml(html) {
        const trimmed = (html || '').trim();
        if (!trimmed) {
            return '<div class="message-content message-content--status-card"></div>';
        }
        const temp = document.createElement('div');
        temp.innerHTML = trimmed;
        const card = temp.querySelector('.chat-status-card');
        const inner = card ? card.outerHTML : trimmed;
        return `<div class="message-content message-content--status-card">${inner}</div>`;
    }
    
    function decodeHtmlEntities(text) {
        if (!text) {
            return '';
        }
        const div = document.createElement('textarea');
        div.innerHTML = text;
        return div.value;
    }
    

    function resolveSecurityScore(riskScore) {
        if (riskScore !== null && riskScore !== undefined) {
            sessionStorage.setItem('lastRiskScore', riskScore.toString());
            return riskScore;
        }
        const lastRiskScore = sessionStorage.getItem('lastRiskScore');
        return lastRiskScore ? parseFloat(lastRiskScore) : null;
    }

    function mapToUserFriendlyError(rawMessage) {
        const msg = (rawMessage || '').trim();
        const lower = msg.toLowerCase();

        if (msg.includes('開発プレビュー')) {
            const isSecurity = msg.includes('警告') || msg.includes('セキュリティ');
            return {
                title: isSecurity ? 'セキュリティ上の注意' : 'ご案内',
                subtitle: msg,
                hints: ['本番環境では表示されません'],
            };
        }

        if (!msg || lower.includes('failed to fetch') || lower.includes('networkerror')) {
            return {
                title: '接続できませんでした',
                subtitle: 'サーバーに接続できませんでした。通信環境をご確認ください。',
                hints: [
                    'インターネット接続を確認してください',
                    'しばらく待ってからもう一度お試しください',
                    '問題が続く場合はページを再読み込みしてください',
                ],
            };
        }
        if (/server error:\s*\d+/i.test(msg) || /internal server error/i.test(msg)) {
            return {
                title: '一時的なエラーが発生しました',
                subtitle: 'サーバーで問題が発生しました。しばらく時間をおいてからもう一度お試しください。',
                hints: [
                    '入力内容を変えずに、もう一度送信してみてください',
                    'ページを再読み込みしてからお試しください',
                    '問題が続く場合は不具合を報告してください',
                ],
            };
        }
        if (msg.includes('応答の取得に時間がかか')) {
            return {
                title: '応答に時間がかかっています',
                subtitle: msg.split('\n')[0],
                hints: ['ページを再読み込みしてから、もう一度お試しください'],
            };
        }
        if (msg.includes('通信エラー')) {
            return {
                title: '通信エラーが発生しました',
                subtitle: 'メッセージの送信中に問題が発生しました。',
                hints: ['もう一度お試しください', '問題が続く場合は不具合を報告してください'],
            };
        }
        if (
            /assignment to constant/i.test(msg)
            || /typeerror/i.test(msg)
            || /referenceerror/i.test(msg)
            || /syntaxerror/i.test(msg)
            || /is not defined/i.test(msg)
        ) {
            return {
                title: '一時的な表示エラーが発生しました',
                subtitle: '応答の取得は完了している場合があります。表示が更新されないときはページを再読み込みしてください。',
                hints: ['しばらく待ってからもう一度お試しください', '問題が続く場合は不具合を報告してください'],
            };
        }

        const lines = msg.split('\n').map((l) => l.trim()).filter(Boolean);
        const userLines = lines.filter((l) => !l.startsWith('エラー詳細:'));
        return {
            title: 'ご案内',
            subtitle: userLines[0] || '申し訳ございません。処理中にエラーが発生しました。',
            hints: userLines.length > 1
                ? userLines.slice(1)
                : ['しばらく待ってからもう一度お試しください', '問題が続く場合は不具合を報告してください'],
        };
    }

    function buildStatusCardHTML(options) {
        const {
            variant = 'error',
            title,
            subtitle = '',
            hints = [],
            dismissible = true,
            showRetry = true,
            showReport = true,
            reportDataAttrs = '',
        } = options;

        const icons = { error: '⚠️', caution: '⚠️', notice: 'ℹ️', security: '🚨', critical: '⚠️' };
        const icon = icons[variant] || '⚠️';
        const hintsHtml = hints.length
            ? `<ul class="chat-status-card__hints">${hints.map((h) => `<li>${escapeHtml(h)}</li>`).join('')}</ul>`
            : '';
        const dismissBtn = dismissible
            ? `<button type="button" class="chat-status-card__dismiss" aria-label="閉じる" onclick="this.closest('.message').remove()">×</button>`
            : '';
        const dismissClass = dismissible ? ' chat-status-card--with-dismiss' : '';

        let actionsHtml = '';
        if (showRetry || showReport) {
            const retryBtn = showRetry
                ? '<button type="button" class="chat-status-card__btn chat-status-card__btn--primary" onclick="retryLastMessage()">もう一度試す</button>'
                : '';
            const reportBtn = showReport
                ? `<button type="button" class="chat-status-card__btn chat-status-card__btn--report report-bug-btn" ${reportDataAttrs} onclick="handleSecurityReportFromButton(this)">不具合を報告</button>`
                : '';
            actionsHtml = `<div class="chat-status-card__actions">${retryBtn}${reportBtn}</div>`;
        }

        return `
            <div class="message-content">
                <div class="chat-status-card chat-status-card--${variant}${dismissClass}" role="alert">
                    ${dismissBtn}
                    <div class="chat-status-card__header">
                        <span class="chat-status-card__icon" aria-hidden="true">${icon}</span>
                        <h4 class="chat-status-card__title">${escapeHtml(title)}</h4>
                    </div>
                    ${subtitle ? `<p class="chat-status-card__subtitle">${escapeHtml(subtitle)}</p>` : ''}
                    <div class="chat-status-card__body">
                        ${hintsHtml}
                        ${actionsHtml}
                    </div>
                </div>
            </div>`;
    }

    function insertStatusCardAfterAnchor(chatMessages, wrapper, anchorIndex) {
        const anchorNode = findMessageNodeByIndex(anchorIndex);
        if (anchorNode && anchorNode.parentNode === chatMessages) {
            let insertBefore = anchorNode.nextElementSibling;
            while (
                insertBefore
                && insertBefore.getAttribute('data-status-after-index') === String(anchorIndex)
            ) {
                insertBefore = insertBefore.nextElementSibling;
            }
            chatMessages.insertBefore(wrapper, insertBefore);
        } else {
            const typing = document.getElementById('currentTypingIndicator');
            if (typing) {
                chatMessages.insertBefore(wrapper, typing);
            } else {
                chatMessages.appendChild(wrapper);
            }
        }
    }

    function showStatusMessage(messageClass, variant, rawMessage, riskScore = null, anchorIndex = null) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) {
            return;
        }

        const securityScore = resolveSecurityScore(riskScore);
        const friendly = mapToUserFriendlyError(rawMessage);
        const reportAttrs = [
            `data-user-message="${escapeHtml(sessionStorage.getItem('lastUserMessage') || '')}"`,
            `data-ai-response="${escapeHtml(friendly.subtitle)}"`,
            `data-security-score="${securityScore !== null && securityScore !== undefined ? securityScore : ''}"`,
        ].join(' ');

        const wrapper = document.createElement('div');
        wrapper.className = `message bot ${messageClass}`;
        wrapper.setAttribute('data-persistent', 'true');
        wrapper.setAttribute('data-status-persistent', 'true');
        wrapper.setAttribute('data-message-id', `status-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`);
        if (anchorIndex !== null && anchorIndex !== undefined) {
            wrapper.setAttribute('data-status-after-index', String(anchorIndex));
        } else {
            wrapper.setAttribute('data-status-after-index', '__end__');
        }
        wrapper.innerHTML = buildStatusCardHTML({
            variant,
            title: friendly.title,
            subtitle: friendly.subtitle,
            hints: friendly.hints,
            showRetry: variant === 'error',
            showReport: true,
            reportDataAttrs: reportAttrs,
        });
        insertStatusCardAfterAnchor(chatMessages, wrapper, anchorIndex);
        scrollToBottom();
    }

    function showErrorMessage(message, riskScore = null, anchorIndex = null) {
        showStatusMessage('error-message', 'error', message, riskScore, anchorIndex);
    }

    function showWarningMessage(message, riskScore = null, anchorIndex = null) {
        showStatusMessage('warning-message', 'security', message, riskScore, anchorIndex);
    }

    function clearPersistentStatusMessages() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) {
            return;
        }
        chatMessages.querySelectorAll('[data-status-persistent="true"]').forEach((node) => node.remove());
    }

    function retryLastMessage() {
        const lastMessage = sessionStorage.getItem('lastUserMessage');
        if (!lastMessage) {
            return;
        }
        clearPersistentStatusMessages();
        const input = document.getElementById('messageInput');
        const form = document.getElementById('chatForm');
        if (input) {
            input.value = lastMessage;
            input.focus();
        }
        if (form && !isSubmitting) {
            form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        }
    }

    window.retryLastMessage = retryLastMessage;
    window.clearPersistentStatusMessages = clearPersistentStatusMessages;

    function setSlowRequestButtonLabel(slowBtn, text) {
        if (!slowBtn) return;
        const textEl = slowBtn.querySelector('.slow-request-btn-text');
        if (textEl) {
            textEl.textContent = text;
        } else {
            slowBtn.textContent = text;
        }
    }

    function getOrCreateSlowRequestButton() {
        let slowBtn = document.getElementById('slowRequestBtn');
        if (!slowBtn) {
            slowBtn = document.createElement('button');
            slowBtn.type = 'button';
            slowBtn.id = 'slowRequestBtn';
            slowBtn.className = 'slow-request-btn';
            slowBtn.setAttribute('aria-label', '処理に時間がかかっていることを運営に通知する');
            slowBtn.innerHTML =
                '<span class="slow-request-btn-icon" aria-hidden="true">⏱</span>' +
                '<span class="slow-request-btn-text">時間がかかっています</span>';
            slowBtn.addEventListener('click', notifySlowRequest);
        }
        return slowBtn;
    }

    function ensureSlowRequestSlot(bubble) {
        let slot = bubble.querySelector('.processing-slow-request-slot');
        if (!slot) {
            slot = document.createElement('div');
            slot.className = 'processing-slow-request-slot';
            bubble.appendChild(slot);
        }
        return slot;
    }

    function attachSlowRequestButtonToTypingIndicator() {
        const typing = document.getElementById('currentTypingIndicator');
        const slowBtn = getOrCreateSlowRequestButton();
        if (!typing) {
            return slowBtn;
        }
        const bubble =
            typing.querySelector('.processing-status-bubble') ||
            typing.querySelector('.message-content') ||
            typing;
        const slot = ensureSlowRequestSlot(bubble);
        if (slowBtn.parentElement !== slot) {
            slot.appendChild(slowBtn);
        }
        return slowBtn;
    }

    function resetSlowRequestButton(slowBtn) {
        if (!slowBtn) return;
        const slot = slowBtn.closest('.processing-slow-request-slot');
        if (slot) slot.classList.remove('is-visible');
        slowBtn.disabled = false;
        slowBtn.classList.remove('is-sent');
        setSlowRequestButtonLabel(slowBtn, '時間がかかっています');
    }

    function clearSlowRequestTimer() {
        if (slowRequestTimerId) {
            clearTimeout(slowRequestTimerId);
            slowRequestTimerId = null;
        }
        resetSlowRequestButton(document.getElementById('slowRequestBtn'));
    }

    function scheduleSlowRequestButton() {
        clearSlowRequestTimer();
        slowRequestTimerId = setTimeout(function () {
            if (!isSubmitting) return;
            const slowBtn = attachSlowRequestButtonToTypingIndicator();
            if (slowBtn) {
                const slot = slowBtn.closest('.processing-slow-request-slot');
                if (slot) slot.classList.add('is-visible');
                scrollToBottom();
            }
        }, 8000);
    }

    function notifySlowRequest() {
        const lastMessage = sessionStorage.getItem('lastUserMessage') || '';
        fetch(withVersion('/api/slow-request-notify'), {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ last_user_message: lastMessage }),
        }).catch(function (e) { console.warn('slow-request-notify failed', e); });
        const slowBtn = document.getElementById('slowRequestBtn');
        if (slowBtn) {
            slowBtn.disabled = true;
            slowBtn.classList.add('is-sent');
            setSlowRequestButtonLabel(slowBtn, '通知を送信しました');
        }
    }
    window.notifySlowRequest = notifySlowRequest;

    function removeTemporaryUserMessages() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) {
            return;
        }
        chatMessages.querySelectorAll('[data-temporary="true"]').forEach(function (n) {
            n.remove();
        });
    }

    function ensureStreamingChatBubble() {
        if (streamingChatEl && streamingChatEl.isConnected) {
            return streamingChatEl;
        }
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return null;
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot streaming-chat';
        messageDiv.setAttribute('data-streaming-chat', 'true');
        messageDiv.innerHTML =
            '<div class="message-content">' +
            '<span class="streaming-chat-text" style="white-space: pre-wrap;"></span>' +
            '</div>';
        chatMessages.appendChild(messageDiv);
        streamingChatEl = messageDiv;
        scrollToBottom();
        return streamingChatEl;
    }

    function ensureStreamingRecommendationResult() {
        if (streamingRecommendationEl && streamingRecommendationEl.isConnected) {
            return streamingRecommendationEl;
        }
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return null;
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot streaming-recommendation';
        messageDiv.setAttribute('data-streaming-recommendation', 'true');
        if (isSageUi() && window.RecommendationRenderer && window.RecommendationRenderer.buildStreamingSageSkeletonHtml) {
            messageDiv.innerHTML = window.RecommendationRenderer.buildStreamingSageSkeletonHtml();
        } else {
            messageDiv.innerHTML =
                '<div class="recommendation-result" data-streaming-skeleton="true">' +
                '<div class="warning-info streaming-advice-section" role="region" aria-label="あなたに合わせたアドバイス" style="padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #2196f3;">' +
                '<h4 style="color: #1976d2; margin-top: 0;">💡 あなたに合わせたアドバイス</h4>' +
                '<p class="streaming-personalized-advice" style="margin: 5px 0; line-height: 1.6; white-space: pre-wrap;"></p>' +
                '</div>' +
                '<div class="streaming-medicines-section" style="background: #e8f5e9; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #4caf50;">' +
                '<h4 style="color: #2e7d32; margin-top: 0;">💊 推奨医薬品</h4>' +
                '<div class="streaming-medicines-container"></div>' +
                '</div>' +
                '</div>';
        }
        chatMessages.appendChild(messageDiv);
        streamingRecommendationEl = messageDiv;
        scrollToBottom();
        return streamingRecommendationEl;
    }

    function buildStreamingMedicineScoreHtml(med) {
        let html = '';
        const scoreLevel = med.score_level || '中';
        const completenessPenalty = med.completeness_penalty || 0;
        if (med.display_score != null && med.display_score !== '') {
            const scorePercent = Math.round(Number(med.display_score) * 10) / 10;
            html += '<p style="margin: 5px 0;"><strong>📊 最適度:</strong> ' + scorePercent + '% <span style="color: #666;">(' + escapeHtml(scoreLevel) + ')</span></p>';
            if (completenessPenalty > 0) {
                const penaltyPercent = Math.round(Number(completenessPenalty) * 1000) / 10;
                html += '<p style="margin: 5px 0; color: #f57c00; font-size: 0.9em;"><strong>ℹ️ 情報:</strong> 年齢などの情報が入力されると、より正確な判定が可能です（不足情報により' + penaltyPercent + '%低下中）</p>';
            }
        } else if (med.relative_score != null && med.relative_score !== '') {
            const scorePercent = Math.round(Number(med.relative_score) * 100);
            html += '<p style="margin: 5px 0;"><strong>📊 最適度:</strong> ' + scorePercent + '% <span style="color: #666;">(' + escapeHtml(scoreLevel) + ')</span></p>';
        } else if (med.score != null && med.score !== '') {
            const scorePercent = Math.round(Number(med.score) * 100);
            html += '<p style="margin: 5px 0;"><strong>📊 最適度:</strong> ' + scorePercent + '%</p>';
        }
        return html;
    }

    function buildStreamingAgeRestrictionHtml(ageRestriction) {
        if (!ageRestriction || typeof ageRestriction !== 'string' || !ageRestriction.trim()) {
            return '';
        }
        if (ageRestriction.indexOf('15歳未満') >= 0) {
            return '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">15歳以上の方が対象です。</span></p>';
        }
        if (ageRestriction.indexOf('7歳未満') >= 0) {
            return '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">7歳以上の方が対象です。</span></p>';
        }
        if (ageRestriction.indexOf('12歳未満') >= 0) {
            return '<p><strong>年齢制限:</strong> <span style="color: #d32f2f;">12歳以上の方が対象です。</span></p>';
        }
        const match = ageRestriction.match(/(\d+)歳/);
        if (match) {
            return '<p><strong>年齢制限:</strong> ' + escapeHtml(ageRestriction) + '</p>';
        }
        return '';
    }

    function buildStreamingAuxiliaryNoteHtml(med) {
        const medicineType = med.medicine_type || '';
        if (medicineType.indexOf('外用薬（のど）') < 0) {
            return '';
        }
        const productNameLower = (med.product_name || '').toLowerCase();
        const isExternal = ['スプレー', 'トローチ', 'うがい', '含嗽', '噴射', '塗布'].some(function (kw) {
            return productNameLower.indexOf(kw) >= 0;
        });
        const isKampo = ['湯', '散', '丸', 'エキス'].some(function (kw) {
            return productNameLower.indexOf(kw) >= 0;
        });
        if (!isExternal || isKampo) {
            return '';
        }
        return '<p style="margin: 5px 0; padding: 8px; background: #f0f7ff; border-left: 3px solid #2196f3; font-size: 0.9em; color: #1976d2;">' +
            '💡 <strong>補助的な使用について</strong><br>' +
            'この外用薬は、内服薬と併用して喉を直接ケアする補助的な製品です。飲み薬にプラスして使うことで、喉の痛みをより和らげることができます。' +
            '</p>';
    }

    function buildStreamingMedicineItemHtml(med) {
        const rank = med.rank || 1;
        const name = med.product_name || '';
        const mfr = med.manufacturer || '';
        let html = '<div class="medicine-item" style="padding: 10px 0; margin: 10px 0; border-bottom: 1px solid #ddd;">';
        html += '<h5 style="margin: 0 0 10px 0;">🏆 ' + rank + 'つ目: ' + escapeHtml(name);
        if (mfr) {
            html += ' <span style="color: #666; font-size: 0.9em;">(' + escapeHtml(mfr) + ')</span>';
        }
        html += '</h5>';
        html += buildStreamingMedicineScoreHtml(med);
        if (med.explanation) {
            html += '<p style="margin: 5px 0;"><strong>推奨理由:</strong> ' + escapeHtml(med.explanation) + '</p>';
        }
        html += buildStreamingAuxiliaryNoteHtml(med);
        html += buildStreamingAgeRestrictionHtml(med.age_restriction);
        if (med.risk_warning) {
            html += '<p style="margin: 5px 0; color: #d32f2f;"><strong>⚠️ 注意:</strong> ' + escapeHtml(med.risk_warning) + '</p>';
        }
        if (med.low_score_warning) {
            html += '<p style="margin: 5px 0; color: #f57c00;"><strong>⚠️ 推奨スコアが低めです。</strong> 使用前に薬剤師または登録販売者にご相談ください。</p>';
        }
        if (med.efficacy) {
            html += '<p style="margin: 5px 0;"><strong>効能効果:</strong> ' + escapeHtml(med.efficacy) + '</p>';
        }
        html += '</div>';
        return html;
    }

    function appendAdviceDelta(text) {
        if (!text) return;
        const wrapper = ensureStreamingRecommendationResult();
        if (!wrapper) return;
        const el = wrapper.querySelector('.streaming-personalized-advice');
        if (el) {
            el.textContent += text;
            wrapper.classList.add('has-advice');
            scrollToBottom();
        }
    }

    function appendChatDelta(text) {
        if (!text) return;
        const wrapper = ensureStreamingChatBubble();
        if (!wrapper) return;
        const el = wrapper.querySelector('.streaming-chat-text');
        if (el) {
            el.textContent += text;
            scrollToBottom();
        }
    }

        function ensureStreamingQaResponse() {
        if (streamingQaEl && streamingQaEl.isConnected) {
            return streamingQaEl;
        }
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return null;
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot streaming-qa';
        messageDiv.setAttribute('data-streaming-qa', 'true');
        messageDiv.innerHTML =
            '<div class="chat-response" data-streaming-qa-skeleton="true">' +
            '<h4>💬 医薬品相談回答</h4>' +
            '<p class="qa-answer"><strong>回答:</strong><br><span class="streaming-qa-answer" style="white-space: pre-wrap;"></span></p>' +
            '<div class="streaming-qa-sections"></div>' +
            '</div>';
        chatMessages.appendChild(messageDiv);
        streamingQaEl = messageDiv;
        scrollToBottom();
        return streamingQaEl;
    }

function appendQaDelta(text, section) {
        if (!text) return;
        const wrapper = ensureStreamingQaResponse();
        if (!wrapper) return;
        const sec = section || 'answer';
        if (sec === 'answer') {
            const el = wrapper.querySelector('.streaming-qa-answer');
            if (el) {
                el.textContent += text;
                scrollToBottom();
            }
        }
    }

    function appendQaSectionHtml(section, html) {
        if (!html) return;
        const wrapper = ensureStreamingQaResponse();
        if (!wrapper) return;
        const chatResponse = wrapper.querySelector('.chat-response');
        if (chatResponse) {
            chatResponse.removeAttribute('data-streaming-qa-skeleton');
        }
        const container = wrapper.querySelector('.streaming-qa-sections');
        if (!container) return;
        const existing = container.querySelector('[data-qa-section="' + section + '"]');
        if (existing) {
            existing.outerHTML = html;
        } else {
            const tmp = document.createElement('div');
            tmp.innerHTML = html;
            while (tmp.firstChild) {
                container.appendChild(tmp.firstChild);
            }
        }
        scrollToBottom();
    }

    function removeStreamingQaResponse() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.querySelectorAll('[data-streaming-qa="true"]').forEach(function (n) { n.remove(); });
        }
        streamingQaEl = null;
    }

    function removeStreamingChatBubble() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.querySelectorAll('[data-streaming-chat="true"]').forEach(function (n) { n.remove(); });
        }
        streamingChatEl = null;
    }

    function removeStreamingRecommendation() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.querySelectorAll('[data-streaming-recommendation="true"]').forEach(function (n) { n.remove(); });
        }
        streamingRecommendationEl = null;
    }

    function removeStreamingAdviceBubble() {
        removeStreamingRecommendation();
    }

    function removeStreamingMedicineCards() {
        removeStreamingRecommendation();
    }

    function resetRecommendationSseBulkState() {
        recommendationSseBulkMode = false;
    }

    function startRecommendationSseBulkMode() {
        recommendationSseBulkMode = true;
    }

    function renderStreamingMedicineCards(medicines) {
        if (!medicines || !medicines.length) return;
        const wrapper = ensureStreamingRecommendationResult();
        if (!wrapper) return;
        if (isSageUi() && window.RecommendationRenderer && window.RecommendationRenderer.updateStreamingSageReco) {
            if (window.RecommendationRenderer.updateStreamingSageReco(wrapper, medicines)) {
                scrollToBottom();
                return;
            }
        }
        const container = wrapper.querySelector('.streaming-medicines-container');
        if (!container) return;
        if (isSageUi() && window.RecommendationRenderer) {
            const html = window.RecommendationRenderer.buildRecommendationMedicinesHtml(medicines);
            if (html) {
                container.innerHTML = html;
                window.RecommendationRenderer.bindRendered(container);
                wrapper.classList.add('has-medicines');
                scrollToBottom();
                return;
            }
        }
        container.innerHTML = medicines.map(buildStreamingMedicineItemHtml).join('');
        wrapper.classList.add('has-medicines');
        scrollToBottom();
    }

    function updateStreamingExplanations(items) {
        if (!items || !items.length) return;
        const wrapper = document.querySelector('[data-streaming-recommendation="true"]') || streamingRecommendationEl;
        if (!wrapper) return;
        if (isSageUi()) {
            items.forEach(function (item) {
                const exp = (item.explanation || '').trim();
                if (!exp) return;
                const rank = item.rank || 0;
                const name = (item.product_name || '').trim();
                const cards = wrapper.querySelectorAll('.ui-card--pro');
                cards.forEach(function (card, idx) {
                    const matchRank = rank && idx + 1 === rank;
                    const matchName = name && card.textContent.indexOf(name) >= 0;
                    if (!matchRank && !matchName) return;
                    const sections = card.querySelectorAll('.ui-card-section');
                    const reasonEl = sections.length > 1
                        ? sections[1].querySelector('.ui-card-text')
                        : card.querySelector('.ui-card-section .ui-card-text');
                    if (reasonEl) reasonEl.textContent = exp;
                });
            });
            scrollToBottom();
            return;
        }
        const medBlocks = wrapper.querySelectorAll('.streaming-medicines-container .medicine-item');
        items.forEach(function (item) {
            const exp = (item.explanation || '').trim();
            if (!exp) return;
            const rank = item.rank || 0;
            const name = (item.product_name || '').trim();
            let target = null;
            medBlocks.forEach(function (block, idx) {
                if (rank && idx + 1 === rank) target = block;
                else if (name && block.textContent.indexOf(name) >= 0) target = block;
            });
            if (!target) return;
            let p = target.querySelector('.streaming-explanation');
            if (!p) {
                p = document.createElement('p');
                p.className = 'streaming-explanation';
                p.style.margin = '5px 0';
                const h5 = target.querySelector('h5');
                if (h5 && h5.nextSibling) {
                    target.insertBefore(p, h5.nextSibling);
                } else {
                    target.appendChild(p);
                }
            }
            p.innerHTML = '<strong>推奨理由:</strong> ' + escapeHtml(exp);
        });
        scrollToBottom();
    }

    function hasActiveStreamingContent() {
        const chatText = document.querySelector('[data-streaming-chat="true"] .streaming-chat-text');
        if (chatText && chatText.textContent && chatText.textContent.trim()) {
            return true;
        }
        const rec = document.querySelector('[data-streaming-recommendation="true"]');
        if (rec) {
            const advice = rec.querySelector('.streaming-personalized-advice');
            if (advice && advice.textContent && advice.textContent.trim()) {
                return true;
            }
            if (rec.querySelector('.medicine-item')) {
                return true;
            }
        }
        const qaAnswer = document.querySelector('.streaming-qa-answer');
        if (qaAnswer && qaAnswer.textContent && qaAnswer.textContent.trim()) {
            return true;
        }
        if (document.querySelector('[data-streaming-qa="true"]')) {
            return true;
        }
        return false;
    }

    function streamingTextsMatch(streamed, finalText) {
        const a = (streamed || '').trim();
        const b = (finalText || '').trim();
        if (!a) {
            return !b;
        }
        if (!b) {
            return true;
        }
        if (a === b) {
            return true;
        }
        return b.indexOf(a) === 0 || a.indexOf(b) === 0;
    }

    function isSimplePlainBotMessage(message) {
        if (!message || message.type !== 'bot') {
            return false;
        }
        if (message.store_inquiry || message.emergency_detected || message.crisis_support) {
            return false;
        }
        const content = message.content || '';
        if (
            content.includes('recommendation-result') ||
            content.includes('chat-response') ||
            content.includes('emergency-response-modern') ||
            isStatusCardHtml(content) ||
            looksLikeHtmlContent(content)
        ) {
            return false;
        }
        if (isDiagnosisPayload(message.diagnosis)) {
            return false;
        }
        return true;
    }

    function getActiveStreamingChatBubble() {
        if (streamingChatEl && streamingChatEl.isConnected) {
            return streamingChatEl;
        }
        return document.querySelector('[data-streaming-chat="true"]');
    }

    function discardStreamingChatBubbleIfStatusCardFinal(message) {
        if (!message || !message.content || !isStatusCardHtml(message.content)) {
            return false;
        }
        const bubble = getActiveStreamingChatBubble();
        if (!bubble) {
            return false;
        }
        bubble.remove();
        streamingChatEl = null;
        return false;
    }

    function tryPromoteStreamingChatBubble(message, index) {
        if (!isSimplePlainBotMessage(message)) {
            return false;
        }
        const bubble = getActiveStreamingChatBubble();
        if (!bubble) {
            return false;
        }
        const span = bubble.querySelector('.streaming-chat-text');
        const streamed = (span ? span.textContent : bubble.textContent || '').trim();
        const finalContent = (message.content || '').trim();
        if (streamed && finalContent && !streamingTextsMatch(streamed, finalContent)) {
            return false;
        }
        const messageKey = getMessageDomKey(message);
        bubble.classList.remove('streaming-chat');
        bubble.removeAttribute('data-streaming-chat');
        bubble.className = 'message bot';
        bubble.setAttribute('data-message-id', messageKey);
        bubble.setAttribute('data-message-index', String(index));
        if (span) {
            if (finalContent && finalContent.length > streamed.length) {
                span.textContent = finalContent;
            }
            span.classList.remove('streaming-chat-text');
            span.removeAttribute('style');
        } else if (finalContent) {
            bubble.innerHTML = '<' + 'div class="message-content">' + formatPlainBotText(finalContent) + '</' + 'div>';
        }
        streamingChatEl = null;
        return true;
    }

    function tryPromoteStreamingQaResponse(message, index) {
        const diag = message && message.diagnosis;
        if (!diag || !diag.is_question) {
            return false;
        }
        const wrapper =
            streamingQaEl && streamingQaEl.isConnected
                ? streamingQaEl
                : document.querySelector('[data-streaming-qa="true"]');
        if (!wrapper) {
            return false;
        }
        const messageKey = getMessageDomKey(message);
        const serverHtml = (message.content || '').trim();
        const isServerError = serverHtml.indexOf('システムエラー') >= 0;
        if (!isServerError && serverHtml.includes('chat-response')) {
            wrapper.innerHTML = '<div class="message-content">' + serverHtml + '</div>';
        }
        wrapper.querySelectorAll('[data-streaming-qa-skeleton]').forEach(function (node) {
            node.removeAttribute('data-streaming-qa-skeleton');
        });
        wrapper.classList.remove('streaming-qa');
        wrapper.removeAttribute('data-streaming-qa');
        wrapper.className = 'message bot';
        wrapper.setAttribute('data-message-id', messageKey);
        wrapper.setAttribute('data-message-index', String(index));
        streamingQaEl = null;
        return true;
    }

    function removeOrphanedStreamingBubbles() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) {
            return;
        }
        chatMessages.querySelectorAll('[data-streaming-chat="true"]').forEach(function (node) {
            node.remove();
        });
        if (streamingChatEl && !streamingChatEl.isConnected) {
            streamingChatEl = null;
        } else if (streamingChatEl && !streamingChatEl.hasAttribute('data-streaming-chat')) {
            streamingChatEl = null;
        }
        chatMessages.querySelectorAll('[data-streaming-qa="true"]').forEach(function (node) {
            node.remove();
        });
        if (streamingQaEl && !streamingQaEl.isConnected) {
            streamingQaEl = null;
        }
        chatMessages.querySelectorAll('[data-streaming-recommendation="true"]').forEach(function (node) {
            node.remove();
        });
        if (streamingRecommendationEl && !streamingRecommendationEl.isConnected) {
            streamingRecommendationEl = null;
        }
    }

    function finalizeStreamingUiAfterPost() {
        endAwaitingPostResponse();
        dismissTypingIndicator(null);
        removeProcessingMessage();
        restoreSubmitButton();
        clearSlowRequestTimer();
    }

    function rememberLatestBotForFeedback(messages) {
        if (!messages || messages.length === 0) {
            return;
        }
        const latestMessage = messages[messages.length - 1];
        if (!latestMessage || latestMessage.type !== 'bot') {
            return;
        }
        let messageId = latestMessage.message_id;
        if (!messageId) {
            messageId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }
        sessionStorage.setItem(
            'message_' + messageId,
            JSON.stringify({
                user_message: sessionStorage.getItem('lastUserMessage') || '',
                ai_response: latestMessage.content || '',
                security_score: null,
                message_id: messageId,
            })
        );
    }

    function scheduleDeferredSessionRecovery(generation, attempt) {
        if (postResponseResolved) {
            return;
        }
        const tryNum = attempt || 0;
        const token = ++deferredRecoveryToken;
        const delayMs = tryNum === 0 ? 120 : Math.min(400, 80 + tryNum * 60);
        setTimeout(function () {
            if (generation !== chatSubmitGeneration || token !== deferredRecoveryToken || postResponseResolved) {
                return;
            }
            fetch(withVersion('/api/sessions'), {
                credentials: 'include',
                headers: { 'Cache-Control': 'no-cache' },
            })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error('HTTP ' + response.status);
                    }
                    return response.json();
                })
                .then(function (sessionData) {
                    if (generation !== chatSubmitGeneration || token !== deferredRecoveryToken) {
                        return;
                    }
                    const merged = resolveSessionMessages(sessionData || {}, { allowRestore: false });
                    if (!isChatResponseComplete(merged)) {
                        if (tryNum < 12) {
                            scheduleDeferredSessionRecovery(generation, tryNum + 1);
                        }
                        return;
                    }
                    clearPersistentStatusMessages();
                    removeProcessingMessage();
                    rememberLatestBotForFeedback(merged);
                    if (!completePostResponseIfReady(sessionData, null)) {
                        if (!isLatestTurnRenderedInDom(merged)) {
                            applySessionMessages(sessionData, {
                                allowRestore: false,
                                forceRender: true,
                                suppressTypingIndicator: true,
                                periodicSync: true,
                            });
                            if (isLatestTurnRenderedInDom(merged)) {
                                markPostResponseResolved();
                                restoreSubmitButton();
                                clearSlowRequestTimer();
                                return;
                            }
                        }
                        if (tryNum < 12) {
                            scheduleDeferredSessionRecovery(generation, tryNum + 1);
                        }
                        return;
                    }
                    clearSlowRequestTimer();
                })
                .catch(function () {
                    if (generation === chatSubmitGeneration && tryNum < 12) {
                        scheduleDeferredSessionRecovery(generation, tryNum + 1);
                    }
                });
        }, delayMs);
    }

    function fetchMessagesAfterPost(data, onComplete) {
        const postMeta = data || {};
        if (postMeta.skipFetch || postResponseResolved) {
            if (onComplete) {
                onComplete();
            }
            return;
        }
        if (postMeta.donePayload && postMeta.donePayload.bot_message) {
            if (unlockPostResponseUI(postMeta.donePayload)) {
                if (onComplete) {
                    onComplete();
                }
                return;
            }
        }
        let retryCount = 0;
        let fetchSeq = 0;
        const hasDoneBot = !!(postMeta.donePayload && postMeta.donePayload.bot_message);
        const maxRetries = postMeta.instantRendered
            ? 0
            : (postMeta.from_sse_done ? (hasDoneBot ? 1 : 3) : 5);
        const fetchTimeoutMs = postMeta.from_sse_done ? 5000 : 2000;

        function retryDelayMs() {
            if (!postMeta.from_sse_done) {
                return 400;
            }
            if (retryCount < 4) {
                return 60;
            }
            if (retryCount < 8) {
                return 150;
            }
            return 300;
        }

        const fetchMessages = function () {
            const seq = ++fetchSeq;
            let settled = false;
            const timeoutId = setTimeout(function () {
                if (settled || seq !== fetchSeq || shouldSuppressPostFetchError()) {
                    if (shouldSuppressPostFetchError()) {
                        dismissTypingIndicator(null, { force: true });
                        restoreSubmitButton();
                        clearSlowRequestTimer();
                        if (onComplete) onComplete();
                    }
                    return;
                }
                if (retryCount < maxRetries) {
                    retryCount++;
                    setTimeout(fetchMessages, retryDelayMs());
                } else {
                    if (unlockPostResponseUI(postMeta.donePayload || null) || shouldSuppressPostFetchError()) {
                        dismissTypingIndicator(null, { force: true });
                        removeProcessingMessage();
                        restoreSubmitButton();
                        clearSlowRequestTimer();
                        if (onComplete) onComplete();
                        return;
                    }
                    dismissTypingIndicator(null, { force: true });
                    removeProcessingMessage();
                    removeStreamingAdviceBubble();
                    removeStreamingMedicineCards();
                    removeStreamingChatBubble();
                    removeStreamingQaResponse();
                    showErrorMessage('申し訳ございません。応答の取得に時間がかかっています。ページを再読み込みしてください。');
                    restoreSubmitButton();
                    clearSlowRequestTimer();
                    if (onComplete) onComplete();
                }
            }, fetchTimeoutMs);

            fetch(withVersion('/api/sessions'), {
                credentials: 'include',
                headers: { 'Cache-Control': 'no-cache' },
            })
                .then(function (response) {
                    if (settled || seq !== fetchSeq) {
                        return null;
                    }
                    clearTimeout(timeoutId);
                    if (!response.ok) throw new Error('HTTP ' + response.status);
                    return response.json();
                })
                .then(function (sessionData) {
                    if (!sessionData || settled || seq !== fetchSeq) {
                        return;
                    }
                    settled = true;
                    clearTimeout(timeoutId);
                    if (shouldSuppressPostFetchError()) {
                        dismissTypingIndicator(null, { force: true });
                        restoreSubmitButton();
                        clearSlowRequestTimer();
                        if (onComplete) onComplete();
                        return;
                    }
                    const mergedAfterPost = resolveSessionMessages(sessionData || {});
                    if (mergedAfterPost.length > 0 && isChatResponseComplete(mergedAfterPost)) {
                        rememberLatestBotForFeedback(mergedAfterPost);
                        if (completePostResponseIfReady(sessionData, postMeta.donePayload || null)) {
                            removeProcessingMessage();
                            clearSlowRequestTimer();
                            if (onComplete) onComplete();
                            return;
                        }
                    }
                    if (postMeta.instantRendered && isChatResponseComplete(mergedAfterPost)) {
                        endAwaitingPostResponse();
                        dismissTypingIndicator(mergedAfterPost);
                        removeProcessingMessage();
                        clearSlowRequestTimer();
                        if (onComplete) onComplete();
                        return;
                    }

                    if (mergedAfterPost.length > 0 && !shouldDeferSessionSync()) {
                        applySessionMessages(sessionData, {
                            preserveStatusCards: true,
                            forceRender: false,
                        });
                    }

                    if (
                        postMeta.message_count > 0 &&
                        !isChatResponseComplete(mergedAfterPost) &&
                        retryCount < maxRetries
                    ) {
                        retryCount++;
                        setTimeout(fetchMessages, retryDelayMs());
                        return;
                    }

                    if (postMeta.message_count === 0 && (!sessionData.session_active || sessionData.messages_count === 0)) {
                        dismissTypingIndicator(mergedAfterPost, { force: true });
                        removeProcessingMessage();
                        restoreSubmitButton();
                        clearSlowRequestTimer();
                        if (onComplete) onComplete();
                        return;
                    }

                    if (retryCount < maxRetries) {
                        retryCount++;
                        setTimeout(fetchMessages, retryDelayMs());
                        return;
                    }

                    if (hasActiveStreamingContent()) {
                        finalizeStreamingUiAfterPost();
                        if (onComplete) onComplete();
                        return;
                    }

                    if (postMeta.from_sse_done) {
                        if (!postResponseResolved) {
                            unlockPostResponseUI(postMeta.donePayload || null);
                        }
                        dismissTypingIndicator(null, { force: true });
                        if (!postResponseResolved) {
                            scheduleDeferredSessionRecovery(chatSubmitGeneration, 0);
                        }
                        restoreSubmitButton();
                        clearSlowRequestTimer();
                        if (onComplete) onComplete();
                        return;
                    }

                    if (unlockPostResponseUI(postMeta.donePayload || null) || shouldSuppressPostFetchError()) {
                        dismissTypingIndicator(null, { force: true });
                        restoreSubmitButton();
                        clearSlowRequestTimer();
                        if (onComplete) onComplete();
                        return;
                    }
                    dismissTypingIndicator(mergedAfterPost, { force: true });
                    removeProcessingMessage();
                    removeStreamingAdviceBubble();
                    removeStreamingMedicineCards();
                    removeStreamingChatBubble();
                    removeStreamingQaResponse();
                    showErrorMessage('申し訳ございません。応答の取得に時間がかかっています。ページを再読み込みしてください。');
                    restoreSubmitButton();
                    clearSlowRequestTimer();
                    if (onComplete) onComplete();
                })
                .catch(function () {
                    if (settled || seq !== fetchSeq) {
                        return;
                    }
                    clearTimeout(timeoutId);
                    if (retryCount < maxRetries) {
                        retryCount++;
                        setTimeout(fetchMessages, retryDelayMs());
                    } else if (hasActiveStreamingContent()) {
                        finalizeStreamingUiAfterPost();
                        if (onComplete) onComplete();
                    } else if (postMeta.from_sse_done) {
                        if (!unlockPostResponseUI(postMeta.donePayload || null) && !shouldSuppressPostFetchError()) {
                            scheduleDeferredSessionRecovery(chatSubmitGeneration);
                        }
                        restoreSubmitButton();
                        clearSlowRequestTimer();
                        if (onComplete) onComplete();
                    } else {
                        dismissTypingIndicator(null, { force: true });
                        removeProcessingMessage();
                        removeStreamingMedicineCards();
                        removeStreamingChatBubble();
                        removeStreamingQaResponse();
                        if (!shouldSuppressPostFetchError()) {
                            showErrorMessage('通信エラーが発生しました。もう一度お試しください。');
                        }
                        restoreSubmitButton();
                        clearSlowRequestTimer();
                        if (onComplete) onComplete();
                    }
                });
        };
        fetchMessages();
    }

    function submitFormViaSse(message) {
        if (!window.ChatSSE) {
            return submitFormLegacy(message);
        }
        const gen = ++chatSubmitGeneration;
        chatStreamInProgress = true;
        resetRecommendationSseBulkState();
        let sseDoneHandled = false;
        scheduleSlowRequestButton();
        const lastEventId = sessionStorage.getItem('chatSseLastEventId') || null;

        function finalizeSsePost(donePayload) {
            if (gen !== chatSubmitGeneration || sseDoneHandled) {
                return;
            }
            sseDoneHandled = true;
            chatStreamInProgress = false;
            resetRecommendationSseBulkState();
            sessionStorage.removeItem('chatSseLastEventId');
            awaitingPostResponse = true;
            postResponseResolved = false;
            handoffFinalizeTypingIndicator();
            const messageCount = donePayload && typeof donePayload.message_count === 'number'
                ? donePayload.message_count
                : 0;
            let instantRendered = false;
            try {
                instantRendered = applyInstantBotFromSseDone(donePayload);
                if (!instantRendered && donePayload && donePayload.bot_message) {
                    requestAnimationFrame(function () {
                        if (!postResponseResolved) {
                            unlockPostResponseUI(donePayload);
                        }
                    });
                }
            } catch (err) {
                console.error('finalizeSsePost unlock failed:', err);
                if (!postResponseResolved) {
                    scheduleDeferredSessionRecovery(gen, 0);
                }
            }
            const postUnlockSafetyTimer = setTimeout(function () {
                if (gen !== chatSubmitGeneration) {
                    return;
                }
                if (!document.getElementById('currentTypingIndicator')) {
                    return;
                }
                unlockPostResponseUI(donePayload);
                dismissTypingIndicator(null, { force: true });
                endAwaitingPostResponse();
                restoreSubmitButton();
            }, 3000);
            fetchMessagesAfterPost(
                {
                    message_count: messageCount,
                    from_sse_done: true,
                    instantRendered: instantRendered,
                    donePayload: donePayload,
                    skipFetch: postResponseResolved,
                },
                function () {
                    clearTimeout(postUnlockSafetyTimer);
                    clearSubmitWatchdog();
                }
            );
        }

        return window.ChatSSE.submitStream({
            url: mainAppPath('/api/chat/stream'),
            message: message,
            withVersion: withVersion,
            lastEventId: lastEventId,
            onEvent: function (ev) {
                if (ev.id) {
                    sessionStorage.setItem('chatSseLastEventId', ev.id);
                }
                if (ev.event === 'status' && ev.data) {
                    applySseProcessingStatus(ev.data);
                }
                if (ev.event === 'done') {
                    finalizeSsePost(ev.data || null);
                }
                if (ev.event === 'chat_delta' && ev.data && ev.data.text) {
                    revealStreamingChunk(function () {
                        appendChatDelta(ev.data.text);
                    });
                }
                if (ev.event === 'qa_delta' && ev.data && ev.data.text) {
                    revealStreamingChunk(function () {
                        appendQaDelta(ev.data.text, ev.data.section);
                    });
                }
                if (ev.event === 'qa_section' && ev.data && ev.data.html) {
                    revealStreamingChunk(function () {
                        appendQaSectionHtml(ev.data.section, ev.data.html);
                    });
                }
                if (ev.event === 'cards' && ev.data && ev.data.medicines) {
                    startRecommendationSseBulkMode();
                    window.__pendingSseMedicines = ev.data.medicines;
                    if (isSageUi()) {
                        renderStreamingMedicineCards(ev.data.medicines);
                    }
                }
                if (ev.event === 'advice_delta' && ev.data && ev.data.text) {
                    if (recommendationSseBulkMode) {
                        return;
                    }
                    revealStreamingChunk(function () {
                        appendAdviceDelta(ev.data.text);
                    });
                }
                if (ev.event === 'explanations' && ev.data && ev.data.items) {
                    if (recommendationSseBulkMode) {
                        return;
                    }
                    updateStreamingExplanations(ev.data.items);
                }
                if (ev.event === 'bot_followup' && ev.data) {
                    if (ev.data.type === 'explanations_ready' && !shouldDeferSessionSync()) {
                        fetchMessagesAfterPost({ message_count: 0, from_sse_done: true }, null);
                    }
                }
                if (ev.event === 'error') {
                    const errCode = ev.data && ev.data.code;
                    if (errCode === 'stream_timeout' && hasActiveStreamingContent()) {
                        chatStreamInProgress = false;
                        resetRecommendationSseBulkState();
                        scheduleDeferredSessionRecovery(gen);
                        restoreSubmitButton();
                        clearSlowRequestTimer();
                        return;
                    }
                    chatStreamInProgress = false;
                    resetRecommendationSseBulkState();
                    sessionStorage.removeItem('chatSseLastEventId');
                    dismissTypingIndicator(null, { force: !hasActiveStreamingContent() });
                    removeProcessingMessage();
                    removeStreamingAdviceBubble();
                    removeStreamingMedicineCards();
                    removeStreamingChatBubble();
                    if (!hasActiveStreamingContent()) {
                        removeStreamingQaResponse();
                    }
                    clearSlowRequestTimer();
                    restoreSubmitButton();
                    if (!hasActiveStreamingContent()) {
                        showErrorMessage((ev.data && ev.data.message) || '');
                    }
                }
            },
            onDone: function (meta) {
                if (gen !== chatSubmitGeneration) {
                    return;
                }
                if (!sseDoneHandled) {
                    finalizeSsePost((meta && meta.done) || null);
                }
            },
            onError: function (err) {
                if (gen !== chatSubmitGeneration) {
                    return;
                }
                chatStreamInProgress = false;
                resetRecommendationSseBulkState();
                sessionStorage.removeItem('chatSseLastEventId');
                dismissTypingIndicator(null, { force: !hasActiveStreamingContent() });
                removeProcessingMessage();
                removeStreamingAdviceBubble();
                removeStreamingMedicineCards();
                removeStreamingChatBubble();
                removeStreamingQaResponse();
                clearSlowRequestTimer();
                if (hasActiveStreamingContent()) {
                    finalizeStreamingUiAfterPost();
                    fetchMessagesAfterPost({ message_count: 0, from_sse_done: true }, function () {
                        clearSubmitWatchdog();
                    });
                    return;
                }
                const errMsg = (err && err.message) || '';
                const isNetwork = !errMsg || /failed to fetch|networkerror|load failed/i.test(errMsg);
                const isSseHttpError = /^SSE HTTP [45]\d\d/i.test(errMsg);
                if (isNetwork || isSseHttpError || isInternalClientErrorMessage(errMsg)) {
                    if (!postResponseResolved) {
                        scheduleDeferredSessionRecovery(gen, 0);
                    }
                    restoreSubmitButton();
                    return;
                }
                restoreSubmitButton();
                showErrorMessage(errMsg);
                if (!postResponseResolved) {
                    scheduleDeferredSessionRecovery(gen, 0);
                }
            },
        });
    }

    function submitForm(message) {
        if (window.CHAT_USE_SSE !== false && window.ChatSSE) {
            return submitFormViaSse(message);
        }
        return submitFormLegacy(message);
    }

    // フォームを送信（従来 JSON POST）
    function submitFormLegacy(message) {
        scheduleSlowRequestButton();
        const formData = new FormData();
        formData.append('message', message);
        
        fetch(withVersion(mainAppPath('/')), {
            method: 'POST',
            credentials: 'include',
            body: formData,
            headers: {
                'Cache-Control': 'no-cache'
            }
        })
        .then(response => {
            console.log('POST response status:', response.status, response.statusText);
            console.log('POST response content-type:', response.headers.get('content-type'));
            
            if (!response.ok) {
                console.error('POST failed:', response.status, response.statusText);
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }
            
            // Content-Typeがapplication/jsonかどうかを確認
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            } else {
                // HTMLやその他の形式の場合
                console.error('Unexpected content-type:', contentType);
                return response.text().then(text => {
                    console.error('Response body:', text.substring(0, 500));
                    throw new Error('サーバーから予期しない形式のレスポンスが返されました');
                });
            }
        })
        .then((data) => {
            console.log('POST response:', data);
            
            // エラーまたは警告のチェック
            if (data.error) {
                console.error('Server error:', data.response);
                dismissTypingIndicator(null, { force: true });
                removeProcessingMessage();
                const errorAnchor = typeof data.message_count === 'number'
                    ? data.message_count - 1
                    : null;
                showErrorMessage(data.response, data.risk_score, errorAnchor);
                mergeSessionMessagesWithoutClearingStatus();
                restoreSubmitButton();
                return;
            }
            
            if (data.warning) {
                console.warn('Server warning:', data.response);
                dismissTypingIndicator(null, { force: true });
                removeProcessingMessage();
                const warningAnchor = typeof data.message_count === 'number'
                    ? data.message_count - 1
                    : null;
                showWarningMessage(data.response, data.risk_score, warningAnchor);
                mergeSessionMessagesWithoutClearingStatus();
                restoreSubmitButton();
                return;
            }
            
            // 少し待ってから最新のメッセージを取得（サーバー処理完了を待つ）
            // 最大3回リトライ（合計1.5秒）に短縮
            let retryCount = 0;
            const maxRetries = 3;
            const retryInterval = 500;
            
            const fetchMessages = () => {
                // タイムアウト処理を追加
                const timeoutId = setTimeout(() => {
                    console.warn('Fetch timeout, retrying...');
                    if (retryCount < maxRetries) {
                        retryCount++;
                        console.log(`Timeout retry... (${retryCount}/${maxRetries})`);
                        setTimeout(fetchMessages, retryInterval);
                    } else {
                        console.error('Max retries reached after timeout');
                        dismissTypingIndicator(null, { force: true });
                        removeProcessingMessage();
                        showErrorMessage('申し訳ございません。応答の取得に時間がかかっています。ページを再読み込みしてください。');
                        restoreSubmitButton();
                    }
                }, 2000); // 2秒でタイムアウト
                
                fetch(withVersion('/api/sessions'), {
                    credentials: 'include',
                    headers: { 'Cache-Control': 'no-cache' }
                })
                .then(response => {
                    clearTimeout(timeoutId);
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    return response.json();
                })
                .then(sessionData => {
                    clearTimeout(timeoutId);
                    console.log(`Session data received (attempt ${retryCount + 1}):`, sessionData);
                    console.log('Messages count:', sessionData?.messages?.length);
                    console.log('Expected message count:', data.message_count);
                    
                    const mergedAfterPost = resolveSessionMessages(sessionData || {});
                    if (mergedAfterPost.length > 0 && isChatResponseComplete(mergedAfterPost)) {
                        console.log('✓ All messages loaded, rendering...');
                        rememberLatestBotForFeedback(mergedAfterPost);
                        completePostResponseIfReady(sessionData, null);
                        removeProcessingMessage();
                    } else if (mergedAfterPost.length > 0) {
                        console.log('✓ Messages loaded (awaiting bot), rendering...');
                        applySessionMessages(sessionData, {
                            preserveStatusCards: false,
                            forceRender: false,
                        });
                        if (
                            data.message_count > 0 &&
                            !isChatResponseComplete(mergedAfterPost) &&
                            retryCount < maxRetries
                        ) {
                            retryCount++;
                            setTimeout(fetchMessages, retryInterval);
                            return;
                        }
                        removeProcessingMessage();
                    } else if (data.message_count === 0 && (!sessionData.session_active || sessionData.messages_count === 0)) {
                        console.log('✓ New session or inactive session, no retry needed');
                        dismissTypingIndicator(mergedAfterPost, { force: true });
                        removeProcessingMessage();
                        restoreSubmitButton();
                    } else if (retryCount < maxRetries) {
                        retryCount++;
                        console.log(`Retrying... (${retryCount}/${maxRetries})`);
                        setTimeout(fetchMessages, retryInterval);
                    } else {
                        console.error('Max retries reached, showing error');
                        dismissTypingIndicator(mergedAfterPost, { force: true });
                        removeProcessingMessage();
                        showErrorMessage('申し訳ございません。応答の取得に時間がかかっています。ページを再読み込みしてください。');
                        restoreSubmitButton();
                    }
                })
                .catch(error => {
                    clearTimeout(timeoutId);
                    console.error('Session fetch error:', error);
                    if (retryCount < maxRetries) {
                        retryCount++;
                        console.log(`Error retry... (${retryCount}/${maxRetries})`);
                        setTimeout(fetchMessages, retryInterval);
                    } else {
                        dismissTypingIndicator(null, { force: true });
                        removeProcessingMessage();
                        showErrorMessage('通信エラーが発生しました。もう一度お試しください。');
                        restoreSubmitButton();
                    }
                });
            };

            fetchMessages();
        })
        .catch(error => {
            console.error('POST Error details:', error);
            console.error('Error name:', error.name);
            console.error('Error message:', error.message);
            console.error('Error stack:', error.stack);
            
            dismissTypingIndicator(null, { force: true });
            removeProcessingMessage();
            restoreSubmitButton();
            showErrorMessage(error.message || '申し訳ございません。送信中にエラーが発生しました。');
        });
    }

    // タイピングインジケーターを削除（引継ぎ時は短いフェードでレイアウトの急変を抑える）
    function removeTypingIndicator() {
        if (window.ProcessingStatus && ProcessingStatus.stopProcessingPoll) {
            ProcessingStatus.stopProcessingPoll();
        }
        const typingIndicator = document.getElementById('currentTypingIndicator');
        if (!typingIndicator) {
            return;
        }
        if (typingIndicator.classList.contains('is-hiding')) {
            if (typingIndicator.parentNode) {
                typingIndicator.remove();
            }
            return;
        }
        const removeNode = function () {
            if (typingIndicator.parentNode) {
                typingIndicator.remove();
            }
        };
        typingIndicator.classList.add('is-hiding');
        typingIndicator.addEventListener('transitionend', removeNode, { once: true });
        setTimeout(removeNode, 180);
    }

    // チャットを最下部にスクロール
    function scrollToBottom() {
        const chatMessages = document.getElementById('chatMessages');
        // iOS Safariのキーボード表示時の高さ計算遅延に対応
        setTimeout(() => {
            requestAnimationFrame(() => {
                chatMessages.scrollTop = chatMessages.scrollHeight;
                // スクロール後、雪のコンテナの高さを更新
                updateSnowContainerHeight();
            });
        }, 200);
    }

    // ページ読み込み時の初期化
    window.onload = function() {
        if (window.ProcessingStatus && ProcessingStatus.stopProcessingPoll) {
            ProcessingStatus.stopProcessingPoll();
        }
        const orphanTyping = document.getElementById('currentTypingIndicator');
        if (orphanTyping) {
            orphanTyping.remove();
        }
        const input = document.getElementById('messageInput');
        if (input) {
            const pending = sessionStorage.getItem('pendingMessage');
            if (pending) {
                input.value = pending;
            }
        }
        // 文字サイズ設定を読み込み
        loadFontSize();
        // 音声読み上げ速度を読み込み
        const savedSpeed = parseFloat(localStorage.getItem('voiceReadSpeed')) || 1.0;
        voiceReadSpeed = savedSpeed;
        scrollToBottom();
        // 初回ロード時にAPIから現在の履歴を取得
        loadMessages();
        // セッション last_activity を維持（タブを開いている間のタイムアウト回避）
        touchSessionActivity();
        setInterval(touchSessionActivity, 120000);
    };

    // チャット履歴をクリアする関数
    function clearChat() {
        const t = translations[currentLanguage];
        if (confirm(t.confirmClearChat)) {
            markSessionReset();
            clearAllChatSessionStorage();
            clearChatCache();
            try {
                sessionStorage.removeItem('chatSseLastEventId');
            } catch (e) { /* ignore */ }
            fetch(withVersion(mainAppPath('/clear')), {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            }).then(() => {
                location.reload();
            });
        }
    }
    
    // 文字サイズ変更機能
    function setFontSize(level) {
        const root = document.documentElement;
        const sizeMap = {
            'small': { base: '0.75rem', lineHeight: '1.7' },
            'normal': { base: '1rem', lineHeight: '1.8' },
            'large': { base: '1.25rem', lineHeight: '1.75' },
            'extra-large': { base: '1.5rem', lineHeight: '1.7' }
        };
        
        const size = sizeMap[level] || sizeMap['normal'];
        root.style.setProperty('--font-size-base', size.base);
        root.style.setProperty('--line-height-base', size.lineHeight);
        
        // ボタンのアクティブ状態を更新
        document.querySelectorAll('.font-size-btn').forEach(btn => {
            btn.style.background = btn.dataset.size === level ? '#4CAF50' : 'white';
            btn.style.color = btn.dataset.size === level ? 'white' : '#4CAF50';
        });
        
        // localStorageに保存
        saveFontSize(level);
    }
    
    function setLineHeight(size) {
        const root = document.documentElement;
        const lineHeightMap = {
            'small': '1.7',
            'normal': '1.8',
            'large': '1.75',
            'extra-large': '1.7'
        };
        root.style.setProperty('--line-height-base', lineHeightMap[size] || '1.8');
    }
    
    function loadFontSize() {
        const savedSize = localStorage.getItem('fontSize') || 'normal';
        setFontSize(savedSize);
    }
    
    function saveFontSize(level) {
        localStorage.setItem('fontSize', level);
    }
    
    // 折りたたみ機能の初期化
    function initCollapsibleSections() {
        const sections = document.querySelectorAll('.collapsible-section[data-collapsible="true"]');
        
        sections.forEach(section => {
            // 既に初期化済みの場合はスキップ（data-initialized属性でチェック）
            if (section.hasAttribute('data-initialized')) {
                return;
            }
            
            const toggle = section.querySelector('.collapse-toggle');
            // collapse-contentを探す、なければボタンの次の要素（コンテンツ部分）を取得
            let content = section.querySelector('.collapse-content');
            if (!content && toggle) {
                // ボタンの次の要素を取得
                content = toggle.nextElementSibling;
            }
            
            // aria-controlsで指定されたIDの要素を探す
            if (!content && toggle) {
                const controlsId = toggle.getAttribute('aria-controls');
                if (controlsId) {
                    content = document.getElementById(controlsId);
                }
            }
            
            if (!toggle || !content) {
                console.warn('折りたたみセクションの初期化に失敗:', section);
                return;
            }
            
            // デフォルト状態を設定
            const defaultExpanded = section.getAttribute('data-default-expanded') === 'true';
            const isExpanded = defaultExpanded;
            
            // 初期状態を設定
            section.setAttribute('aria-expanded', isExpanded.toString());
            toggle.setAttribute('aria-expanded', isExpanded.toString());
            
            if (isExpanded) {
                content.style.display = 'block';
                toggle.setAttribute('aria-label', '閉じる');
                const icon = toggle.querySelector('.collapse-icon');
                if (icon) {
                    icon.style.transform = 'rotate(180deg)';
                }
            } else {
                content.style.display = 'none';
                toggle.setAttribute('aria-label', '詳細を見る');
            }
            
            // クリックイベントハンドラ（一度だけ追加）
            const clickHandler = function(e) {
                e.stopPropagation(); // イベントの伝播を防ぐ
                const currentExpanded = section.getAttribute('aria-expanded') === 'true';
                const newExpanded = !currentExpanded;
                
                // 状態を更新
                section.setAttribute('aria-expanded', newExpanded.toString());
                toggle.setAttribute('aria-expanded', newExpanded.toString());
                
                // コンテンツの表示/非表示を切り替え（アニメーションなし）
                if (newExpanded) {
                    content.style.display = 'block';
                    toggle.setAttribute('aria-label', '閉じる');
                    const icon = toggle.querySelector('.collapse-icon');
                    if (icon) {
                        icon.style.transform = 'rotate(180deg)';
                    }
                } else {
                    content.style.display = 'none';
                    toggle.setAttribute('aria-label', '詳細を見る');
                    const icon = toggle.querySelector('.collapse-icon');
                    if (icon) {
                        icon.style.transform = 'rotate(0deg)';
                    }
                }
            };
            
            // キーボード操作対応（Enter/Spaceキー）
            const keydownHandler = function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    e.stopPropagation();
                    clickHandler(e);
                }
            };
            
            toggle.addEventListener('click', clickHandler);
            toggle.addEventListener('keydown', keydownHandler);
            
            // 初期化済みフラグを設定
            section.setAttribute('data-initialized', 'true');
        });
    }

    function clearAllChatSessionStorage() {
        const prefixes = [CHAT_CACHE_PREFIX, CHAT_RESTORE_DONE_PREFIX];
        try {
            const keys = [];
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                if (!key) {
                    continue;
                }
                if (prefixes.some(function (p) { return key.indexOf(p) === 0; })) {
                    keys.push(key);
                }
            }
            keys.forEach(function (key) { sessionStorage.removeItem(key); });
        } catch (e) { /* ignore */ }
        try {
            sessionStorage.removeItem('lastUserMessage');
            sessionStorage.removeItem('chatSubmitBaselineLength');
        } catch (e) { /* ignore */ }
        lastRenderedMessagesFingerprint = '';
    }

    // 新しいセッションを開始する関数
    document.getElementById('new-session-btn').onclick = function() {
        const t = translations[currentLanguage];
        if (confirm(t.confirmNewSession)) {
            markSessionReset();
            const oldSid = getSidFromCookie();
            clearChatCache(oldSid);
            clearAllChatSessionStorage();
            try {
                sessionStorage.removeItem('chatSseLastEventId');
            } catch (e) { /* ignore */ }
            try {
                localStorage.removeItem(SID_LOCAL_STORAGE_KEY);
            } catch (e) { /* ignore */ }
            const abortCtrl = new AbortController();
            const abortTimer = setTimeout(function () { abortCtrl.abort(); }, 15000);
            fetch(withVersion(mainAppPath('/new_session')), {
                method: 'POST',
                credentials: 'include',
                signal: abortCtrl.signal,
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            })
            .then(function (response) {
                clearTimeout(abortTimer);
                if (!response.ok) {
                    alert('新しいセッションの開始に失敗しました');
                    return null;
                }
                return response.json().catch(function () { return {}; });
            })
            .then(function (data) {
                if (!data) {
                    return;
                }
                if (data.session_id) {
                    rememberSid(data.session_id);
                    clearChatCache(data.session_id);
                }
                try {
                    localStorage.removeItem('onboardingCompleted');
                    localStorage.removeItem(SID_LOCAL_STORAGE_KEY);
                } catch (error) {
                    console.warn('Failed to clear session-local flags:', error);
                }
                location.reload();
            })
            .catch(function (err) {
                clearTimeout(abortTimer);
                if (err && err.name === 'AbortError') {
                    alert('サーバーが応答しません。ターミナルで app.py を Ctrl+C で止めてから再起動してください。');
                } else {
                    alert('通信エラーが発生しました。サーバーがチャット処理で止まっている場合は再起動してください。');
                }
            });
        }
    };

    // 薬剤師対応を要請ボタン
    document.getElementById('admin-request-btn').onclick = function() {
        const message = '薬剤師対応を要請しますか？\n\n「薬剤師要請」機能は、将来的な実装を想定したデモ機能あり、実際に薬剤師が応答・返信する体制は現在稼働しておりません。そのため、ボタンを押しても実際の相談員には繋がりませんことを、あらかじめご了承ください。';
        if (confirm(message)) {
            fetch('/api/request_admin', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            })
            .then(response => {
                console.log('薬剤師要請レスポンス:', response.status, response.statusText);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('薬剤師要請データ:', data);
                if (data.status === 'ok') {
                    // サーバーからメッセージを再取得して表示（永続化されたメッセージを表示）
                    setTimeout(() => {
                        loadMessages();
                    }, 100);
                } else {
                    console.error('薬剤師要請エラー:', data);
                    alert('薬剤師対応の要請に失敗しました: ' + (data.message || '不明なエラー'));
                }
            })
            .catch(error => {
                console.error('薬剤師要請通信エラー:', error);
                alert('通信エラーが発生しました: ' + error.message);
            });
        }
    };

    function getMessageDomKey(message) {
        return stableMessageKey(message);
    }

    function findMessageNodeByIndex(index) {
        if (index === null || index === undefined || index < 0) {
            return null;
        }
        return document.querySelector(
            `#chatMessages [data-message-index="${String(index)}"]`
        );
    }

    function shouldPreserveStatusCards(messages) {
        if (!messages || messages.length === 0) {
            return true;
        }
        const last = messages[messages.length - 1];
        if (last && last.type === 'bot' && !last.error) {
            return false;
        }
        return true;
    }

    /** サーバー応答が確定したか（最後のメッセージが bot かつエラーでない） */
    function isChatResponseComplete(messages) {
        if (!messages || messages.length === 0) {
            return false;
        }
        const last = messages[messages.length - 1];
        return !!(last && last.type === 'bot' && !last.error);
    }

    /** 処理中バブル（#currentTypingIndicator）を表示し続けるべきか */
    function shouldShowTypingIndicator(messages, options) {
        if (options && options.suppressTypingIndicator) {
            return false;
        }
        if (!isSubmitting) {
            return false;
        }
        if (isChatResponseComplete(messages)) {
            return false;
        }
        return true;
    }

    function ensureTypingIndicatorElement() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) {
            return null;
        }
        let el = document.getElementById('currentTypingIndicator');
        if (el) {
            return el;
        }
        const newTypingDiv = document.createElement('div');
        newTypingDiv.className = 'message bot';
        newTypingDiv.id = 'currentTypingIndicator';
        if (window.ProcessingStatus && ProcessingStatus.getTypingIndicatorHtml) {
            newTypingDiv.innerHTML = ProcessingStatus.getTypingIndicatorHtml();
        } else {
            newTypingDiv.innerHTML = '<div class="message-content"><div class="typing-indicator">AIが診断中...</div></div>';
        }
        chatMessages.appendChild(newTypingDiv);
        attachSlowRequestButtonToTypingIndicator();
        return newTypingDiv;
    }

    function collectStatusCardsByAnchor(chatMessages, preserveStatusCards, messages) {
        const cardsByAnchor = new Map();
        if (!preserveStatusCards) {
            clearPersistentStatusMessages();
            return cardsByAnchor;
        }
        const currentKeys = collectMessageDomOrder(chatMessages);
        const targetKeys = buildTargetMessageKeys(messages || []);
        if (
            targetKeys.length === currentKeys.length &&
            targetKeys.every((key, index) => key === currentKeys[index])
        ) {
            return cardsByAnchor;
        }
        chatMessages.querySelectorAll('[data-status-persistent="true"]').forEach((node) => {
            const anchor = node.getAttribute('data-status-after-index');
            const key = anchor !== null && anchor !== '' ? anchor : '__end__';
            if (!cardsByAnchor.has(key)) {
                cardsByAnchor.set(key, []);
            }
            cardsByAnchor.get(key).push(node);
            node.remove();
        });
        return cardsByAnchor;
    }

    function collectMessageDomOrder(chatMessages) {
        const keys = [];
        if (!chatMessages) {
            return keys;
        }
        chatMessages.querySelectorAll('.message[data-message-id]').forEach((node) => {
            if (node.getAttribute('data-initial-message') === 'true') {
                return;
            }
            if (node.getAttribute('data-status-persistent') === 'true' || node.getAttribute('data-persistent') === 'true') {
                return;
            }
            if (node.id === 'currentTypingIndicator') {
                return;
            }
            const key = node.getAttribute('data-message-id');
            if (key) {
                keys.push(key);
            }
        });
        return keys;
    }

    function buildTargetMessageKeys(messages) {
        const keys = [];
        (messages || []).forEach((message) => {
            if (message) {
                keys.push(getMessageDomKey(message));
            }
        });
        return keys;
    }

    function syncChatMessageOrder(messages, cardsByAnchor, chatMessages) {
        const typingIndicator = document.getElementById('currentTypingIndicator');
        const insertBefore = typingIndicator || null;
        const currentKeys = collectMessageDomOrder(chatMessages);
        const targetKeys = buildTargetMessageKeys(messages);
        const messageOrderUnchanged =
            targetKeys.length === currentKeys.length &&
            targetKeys.every((key, index) => key === currentKeys[index]);
        if (messageOrderUnchanged) {
            if (typingIndicator && typingIndicator.parentNode === chatMessages && chatMessages.lastElementChild !== typingIndicator) {
                chatMessages.appendChild(typingIndicator);
            }
            return;
        }

        const existingNodes = new Map();

        chatMessages.querySelectorAll('.message[data-message-id]').forEach((node) => {
            if (node.getAttribute('data-initial-message') === 'true') {
                return;
            }
            if (node.getAttribute('data-status-persistent') === 'true' || node.getAttribute('data-persistent') === 'true') {
                return;
            }
            if (node.id === 'currentTypingIndicator') {
                return;
            }
            const key = node.getAttribute('data-message-id');
            if (key) {
                existingNodes.set(key, node);
            }
        });

        const pendingNodes = [];
        chatMessages.querySelectorAll('[data-temporary="true"]').forEach((node) => {
            pendingNodes.push(node);
            node.remove();
        });

        const ordered = [];
        (messages || []).forEach((message, index) => {
            const key = getMessageDomKey(message);
            const node = takeExistingNodeForMessage(existingNodes, message);
            if (node) {
                ordered.push(node);
            } else if (message && message.type === 'user') {
                const text = String(message.content || '').trim();
                const pendingKey = pendingUserDomKey(text);
                const pendingNode = existingNodes.get(pendingKey);
                if (pendingNode) {
                    existingNodes.delete(pendingKey);
                    if (pendingNode.parentNode) {
                        pendingNode.remove();
                    }
                    pendingNode.setAttribute('data-message-id', key);
                    pendingNode.removeAttribute('data-temporary');
                    const pendingIdx = pendingNodes.indexOf(pendingNode);
                    if (pendingIdx >= 0) {
                        pendingNodes.splice(pendingIdx, 1);
                    }
                    ordered.push(pendingNode);
                } else {
                const fallback = chatMessages.querySelectorAll('.message.user[data-message-id]');
                for (let i = fallback.length - 1; i >= 0; i--) {
                    const candidate = fallback[i];
                    const candidateKey = candidate.getAttribute('data-message-id');
                    if (!candidateKey || existingNodes.has(candidateKey)) {
                        continue;
                    }
                    const candidateText = (candidate.querySelector('.message-content')?.textContent || '').trim();
                    if (candidateText === text) {
                        existingNodes.delete(candidateKey);
                        if (candidate.parentNode) {
                            candidate.remove();
                        }
                        candidate.setAttribute('data-message-id', key);
                        ordered.push(candidate);
                        break;
                    }
                }
                }
            }
            const cards = cardsByAnchor.get(String(index)) || [];
            ordered.push(...cards);
            cardsByAnchor.delete(String(index));
        });

        // サーバー同期時は楽観表示の一時 user を再掲しない（ブロック時は文言がサーバーと一致しない）
        if (!sessionHasResolvedUserMessage(messages)) {
            pendingNodes.forEach((node) => {
                const text = (node.querySelector('.message-content')?.textContent || '').trim();
                const onServer = (messages || []).some(
                    (m) => m.type === 'user' && String(m.content || '').trim() === text
                );
                if (!onServer) {
                    ordered.push(node);
                }
            });
        }

        const endCards = cardsByAnchor.get('__end__') || [];
        ordered.push(...endCards);
        cardsByAnchor.forEach((cards) => {
            ordered.push(...cards);
        });

        existingNodes.forEach((node) => node.remove());

        ordered.forEach((node) => {
            if (node.id === 'snowContainer') {
                return;
            }
            if (insertBefore) {
                chatMessages.insertBefore(node, insertBefore);
            } else {
                chatMessages.appendChild(node);
            }
        });

        const snowContainer = document.getElementById('snowContainer');
        if (snowContainer && snowContainer.parentNode === chatMessages && chatMessages.firstChild !== snowContainer) {
            chatMessages.insertBefore(snowContainer, chatMessages.firstChild);
        }
    }

    function mergeSessionMessagesWithoutClearingStatus() {
        fetch(withVersion('/api/sessions'), {
            credentials: 'include',
            headers: { 'Cache-Control': 'no-cache' },
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then((sessionData) => {
                applySessionMessages(sessionData, {
                    preserveStatusCards: true,
                    forceRender: !shouldDeferSessionSync(),
                });
            })
            .catch((error) => {
                console.warn('mergeSessionMessagesWithoutClearingStatus failed:', error);
                const cached = loadChatCache(getSidFromCookie());
                if (cached.length > 0) {
                    renderChatMessages(cached, { preserveStatusCards: true });
                }
            });
    }

    function appendMessageNodeToChat(chatMessages, messageDiv) {
        const typingIndicator = document.getElementById('currentTypingIndicator');
        if (typingIndicator && typingIndicator.parentNode === chatMessages) {
            chatMessages.insertBefore(messageDiv, typingIndicator);
        } else {
            chatMessages.appendChild(messageDiv);
        }
    }

    /** 同期後に欠けている user/bot バブルを補完（型不一致キー等の取りこぼし対策） */
    function ensureSessionMessagesInDom(messages) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages || !Array.isArray(messages)) {
            return;
        }
        messages.forEach(function (message, index) {
            if (!message || (message.type !== 'user' && message.type !== 'bot')) {
                return;
            }
            const messageKey = getMessageDomKey(message);
            if (isMessageNodeInDom(chatMessages, message, messageKey)) {
                return;
            }
            const messageDiv = document.createElement('div');
            messageDiv.setAttribute('data-message-id', messageKey);
            messageDiv.setAttribute('data-message-index', String(index));
            if (message.type === 'user') {
                messageDiv.className = 'message user';
                messageDiv.innerHTML =
                    '<div class="message-content">' + escapeHtml(message.content || '') + '</div>';
            } else {
                messageDiv.className = 'message bot';
                if (message.store_inquiry && message.content) {
                    messageDiv.innerHTML = '<div class="message-content">' + message.content + '</div>';
                } else if (isStatusCardHtml(message.content)) {
                    messageDiv.innerHTML = wrapBotStatusCardHtml(message.content);
                } else if (message.content && looksLikeHtmlContent(message.content)) {
                    messageDiv.innerHTML = '<div class="message-content">' + message.content + '</div>';
                } else {
                    messageDiv.innerHTML =
                        '<div class="message-content">' + formatPlainBotText(message.content || '') + '</div>';
                }
            }
            appendMessageNodeToChat(chatMessages, messageDiv);
        });
    }

    function clearRenderedChatMessagesExceptInitial() {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) {
            return;
        }
        chatMessages.querySelectorAll('.message[data-message-id]').forEach(function (node) {
            if (node.getAttribute('data-initial-message') === 'true') {
                return;
            }
            if (node.getAttribute('data-status-persistent') === 'true' || node.getAttribute('data-persistent') === 'true') {
                return;
            }
            node.remove();
        });
    }

    function renderChatMessages(messages, options = {}) {
        // ログ出力を削減（デバッグ時のみ有効）
        // console.log('renderChatMessages called with:', messages ? messages.length : 0, 'messages');
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) {
            console.error('chatMessages element not found');
            return;
        }

        if (options.forceRender && !shouldDeferSessionSync()) {
            clearRenderedChatMessagesExceptInitial();
        }

        const keepTypingIndicator = shouldShowTypingIndicator(messages, options);
        
        // 既存メッセージのIDをチェック（重複防止・同一文言の再送は uuid で区別）
        const existingMessages = chatMessages.querySelectorAll('[data-message-id], [data-message-index]');
        const existingIds = new Set();
        existingMessages.forEach(msg => {
            const id = msg.getAttribute('data-message-id') || msg.getAttribute('data-message-index');
            if (id) existingIds.add(id);
        });
        
        // レイアウトの安定性を向上させるため、一括更新
        const fragment = document.createDocumentFragment();
        
        // 初期メッセージの重複チェック
        const hasInitialMessage = chatMessages.querySelector('[data-initial-message="true"]');
        if (!hasInitialMessage) {
            const t = translations[currentLanguage];
            const initialMessage = document.createElement('div');
            initialMessage.className = 'message bot';
            initialMessage.setAttribute('data-initial-message', 'true');
            initialMessage.innerHTML = `
                <div class="message-content">
                    <span id="initial-greeting">${t.initialGreeting}</span><br>
                    <span id="initial-examples">${t.initialExamples}</span>
                </div>
            `;
            fragment.appendChild(initialMessage);
        }
        
        messages.forEach((message, index) => {
            // 既存メッセージの場合はスキップ（重複防止）
            const messageKey = getMessageDomKey(message);
            if (isMessageNodeInDom(chatMessages, message, messageKey)) {
                return;
            }

            discardStreamingChatBubbleIfStatusCardFinal(message);

            if (tryPromoteStreamingChatBubble(message, index)) {
                existingIds.add(messageKey);
                return;
            }

            if (tryPromoteStreamingQaResponse(message, index)) {
                existingIds.add(messageKey);
                return;
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.setAttribute('data-message-id', messageKey);
            messageDiv.setAttribute('data-message-index', String(index));
            
            if (message.type === 'user') {
                messageDiv.className = 'message user';
                messageDiv.innerHTML = `<div class="message-content">${escapeHtml(message.content)}</div>`;
            } else if (message.type === 'bot') {
                messageDiv.className = 'message bot';
                
                // 店舗案内・遺失物関連のメッセージ（HTMLをそのまま表示）
                if (message.store_inquiry && message.content) {
                    // HTMLをそのまま表示（エスケープしない）
                    messageDiv.innerHTML = `<div class="message-content">${message.content}</div>`;
                }
                // ステータスカード（診断名通知・エラーUI等）
                else if (isStatusCardHtml(message.content)) {
                    messageDiv.innerHTML = wrapBotStatusCardHtml(message.content);
                }
                // message.contentにHTMLが直接含まれている場合（ルールベースアルゴリズムの結果）
                else if (message.content && (message.content.includes('<div class="recommendation-result') || 
                                       message.content.includes('class="chat-response') || 
                                       message.content.includes("class='chat-response"))) {
                    if (isStatusCardHtml(message.content)) {
                        messageDiv.innerHTML = wrapBotStatusCardHtml(message.content);
                    } else {
                    // 診断結果の場合は詳細を表示し、評価ボタンも表示
                    // 管理画面専用のスコア情報を除去
                    let cleanedContent = message.content;
                    
                    // 管理画面専用の要素を除去
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = cleanedContent;
                    
                    // admin-score-displayクラスを含む要素を除去
                    const adminScoreElements = tempDiv.querySelectorAll('.admin-score-display');
                    adminScoreElements.forEach(el => el.remove());
                    
                    // score-breakdownクラスを含む要素を除去（スコア内訳）
                    const scoreBreakdownElements = tempDiv.querySelectorAll('.score-breakdown');
                    scoreBreakdownElements.forEach(el => el.remove());
                    
                    // score-itemクラスを含む要素を除去（個別スコア項目）
                    const scoreItemElements = tempDiv.querySelectorAll('.score-item');
                    scoreItemElements.forEach(el => el.remove());
                    
                    // 推奨理由から詳細スコア情報を除去
                    const reasonElements = tempDiv.querySelectorAll('em');
                    reasonElements.forEach(el => {
                        if (el.textContent.includes('✅') || el.textContent.includes('⚠️') || el.textContent.includes('|')) {
                            // 詳細なスコア情報を含む推奨理由を簡潔化
                            el.textContent = '症状に適した医薬品です';
                        }
                    });
                    
                    // 管理者専用のスコア表示を除去
                    const adminScoreDisplayElements = tempDiv.querySelectorAll('[style*="background-color: #f8f9fa"]');
                    adminScoreDisplayElements.forEach(el => {
                        if (el.textContent.includes('スコア内訳') || el.textContent.includes('症状適合') || el.textContent.includes('効能特異性')) {
                            el.remove();
                        }
                    });
                    
                    cleanedContent = tempDiv.innerHTML;
                    
                    // cleanedContentが既にrecommendation-resultやchat-response、emergency-response-modernを含んでいる場合、
                    // それらは既に適切なコンテナなので、追加のmessage-contentラッパーは不要
                    // ただし、最上位の要素を確認して、既にdivでラップされている場合はそのまま使用
                    const firstElement = tempDiv.firstElementChild;
                    if (firstElement && (
                        firstElement.classList.contains('recommendation-result') || 
                        firstElement.classList.contains('chat-response') ||
                        firstElement.classList.contains('emergency-response-modern')
                    )) {
                        // 既に適切なコンテナがあるので、そのまま使用（message-contentラッパーは不要）
                        messageDiv.innerHTML = cleanedContent;
                    } else {
                        // message-contentクラスでラップしてHTMLを正しくレンダリング
                        messageDiv.innerHTML = `<div class="message-content">${cleanedContent}</div>`;
                    }
                    enhanceSageRecommendationMessage(messageDiv, message);
                    }
                }
                // 緊急事案メッセージの特別表示
                else if (message.emergency_detected && message.content) {
                    // HTMLを正しくパースするためにtempDivを使用
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = message.content;
                    
                    // emergency-response-modernが含まれている場合は、message-contentでラップしない
                    const firstElement = tempDiv.firstElementChild;
                    if (firstElement && firstElement.classList.contains('emergency-response-modern')) {
                        // 既に適切なコンテナがあるので、そのまま使用（message-contentラッパーは不要）
                        messageDiv.innerHTML = tempDiv.innerHTML;
                    } else {
                        // 念のため、emergency-response-modernが含まれていない場合は従来通り
                        messageDiv.innerHTML = `<div class="message-content">${tempDiv.innerHTML}</div>`;
                    }
                }
                // 危機対応メッセージの特別表示
                else if (message.crisis_support) {
                    messageDiv.innerHTML = displayCrisisSupportResources(message);
                }
                // 従来の形式
                else {
                    if (message.content && isStatusCardHtml(message.content)) {
                        messageDiv.innerHTML = wrapBotStatusCardHtml(message.content);
                        fragment.appendChild(messageDiv);
                        return;
                    }
                    if (message.content && looksLikeHtmlContent(message.content)) {
                        messageDiv.innerHTML = `<div class="message-content">${message.content}</div>`;
                        fragment.appendChild(messageDiv);
                        return;
                    }
                    let content = `<div class="message-content${message.manual_reply ? ' manual-reply' : ''}${message.style_class ? ' ' + message.style_class : ''}">`;
                    
                    if (message.manual_reply) {
                        content += `<span class="manual-reply-indicator">👤 薬剤師 返信</span><br><br>`;
                    }
                    
                    // 新しい推奨結果の形式に対応
                    if (isDiagnosisPayload(message.diagnosis)) {
                    // 医薬品相談回答の場合
                    if (message.diagnosis.is_question && message.diagnosis.chat_response) {
                        const chatResponse = message.diagnosis.chat_response;
                        content += `<div class="chat-response"><h4>💬 医薬品相談回答</h4>`;
                        content += `<div class="answer-section"><strong>回答:</strong><br>${chatResponse.answer || '回答を取得できませんでした'}</div>`;
                        content += `<div class="details-section">`;
                        content += `<h5>📋 医薬品詳細</h5><p>${chatResponse.medicine_details || '詳細情報を取得できませんでした'}</p>`;
                        content += `<h5>💊 飲み合わせ・相互作用</h5><p>${chatResponse.interactions || '飲み合わせ情報を取得できませんでした'}</p>`;
                        content += `<h5>🏃 ドーピング規制チェック</h5><p>${chatResponse.doping_check || 'ドーピング規制の確認ができませんでした'}</p>`;
                        content += `<h5>⚠️ 副作用・注意点</h5><p>${chatResponse.side_effects || '副作用情報を取得できませんでした'}</p>`;
                        content += `<h5>🏥 医師相談のアドバイス</h5><p>${chatResponse.consultation_advice || '医師にご相談ください'}</p>`;
                        content += `</div></div>`;
                    }
                    // 従来の推奨結果の場合
                    else if (message.diagnosis.symptoms) {
                        content += `<div class="diagnosis-result"><strong>🔍 推定された症状:</strong><br>${message.diagnosis.symptoms.join(', ')}</div>`;
                    }
                    if (message.diagnosis.recommended_medicines && message.diagnosis.recommended_medicines.length > 0) {
                        content += `<div class="medicine-list"><strong>💊 推奨医薬品:</strong><br>`;
                        message.diagnosis.recommended_medicines.forEach(medicine => {
                            content += `<div class="medicine-summary"><strong>${(() => {
    if (medicine.number === 1) return '1つ目';
    else if (medicine.number === 2) return '2つ目';
    else if (medicine.number === 3) return '3つ目';
    else return medicine.number + 'つ目';
})()}:</strong> ${medicine.product_name}<br><em>推奨理由:</em> ${medicine.reason}</div>`;
                        });
                        content += `</div>`;
                    }
                    if (message.diagnosis.usage_notes) {
                        content += `<div class="caution-box"><strong>⚠️ 使用上の注意:</strong><div class="caution-content" style="white-space: pre-line;">${message.diagnosis.usage_notes}</div></div>`;
                    }
                    if (message.diagnosis.doctor_consultation) {
                        content += `<div class="advice-box"><strong>🏥 医師の受診が必要な場合:</strong><br><div class="advice-content">${message.diagnosis.doctor_consultation}</div></div>`;
                    }
                    
                    // 追加質問の表示
                    if (message.diagnosis.additional_questions && message.diagnosis.additional_questions.length > 0) {
                        const priorityLabel = message.diagnosis.missing_priority === 'critical' ? '必須' :
                                             message.diagnosis.missing_priority === 'important' ? '重要' : '任意';
                        const priorityMessage = message.diagnosis.missing_priority === 'critical' ? 
                            'より適切な医薬品をご提案するため、以下の情報を教えてください：' :
                            message.diagnosis.missing_priority === 'important' ?
                            '安全のため、以下の情報を教えてください：' :
                            'より安全な使用のため、可能であれば以下の情報を教えてください：';
                        
                        content += `<div class="question-box" style="background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 10px 0;">
                            <strong>❓ 追加でお伺いしたいこと</strong>
                            <span style="color: #ff9800; font-weight: bold;">（優先度: ${priorityLabel}）</span><br>
                            <p style="margin: 5px 0;">${priorityMessage}</p>
                            <ul style="margin: 10px 0; padding-left: 20px;">`;
                        
                        message.diagnosis.additional_questions.forEach(question => {
                            content += `<li>${question}</li>`;
                        });
                        
                        content += `</ul>
                            <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
                                💡 上記の質問への回答や、その他伝えたいことがあれば、下の入力欄からお送りください。
                            </p>
                        </div>`;
                    }
                    
                    if (message.diagnosis.symptoms && !message.diagnosis.error) {
                        content += `<div class="question-prompt"><strong>❓ 他にご質問はありますか？</strong><br>薬の飲み方、副作用、他の症状との関係など、お気軽にお聞きください。</div>`;
                    }
                    } else {
                        // プレーンテキストのみ pre-line（HTML・ステータスカードは上で処理済み）
                        if (message.content) {
                            if (message.content.includes('\n') || message.escalation_required) {
                                content += `<div style="white-space: pre-line;">${formatPlainBotText(message.content)}</div>`;
                            } else {
                                content += formatPlainBotText(message.content);
                            }
                        }
                    }
                    content += `</div>`;
                    messageDiv.innerHTML = content;
                }
            }
            fragment.appendChild(messageDiv);
        });

        const hasNewMessages = fragment.children.length > 0;
        const shouldRecoverStuckSubmit = options.periodicSync
            || options.forceRender
            || (isChatResponseComplete(messages) && !isLatestTurnRenderedInDom(messages));
        if (isSubmitting && !hasNewMessages && !shouldRecoverStuckSubmit) {
            if (keepTypingIndicator || !isResponseVisibleInDom(messages)) {
                ensureTypingIndicatorElement();
            } else {
                dismissTypingIndicator(messages);
            }
            return;
        }
        
        // レイアウトの安定性を向上させるため、一括更新と固定レイアウト
        const currentScrollTop = chatMessages.scrollTop;
        const currentScrollHeight = chatMessages.scrollHeight;
        const isAtBottom = chatMessages.scrollTop + chatMessages.clientHeight >= chatMessages.scrollHeight - 10;
        
        const preserveStatusCards = options.preserveStatusCards !== undefined
            ? options.preserveStatusCards
            : shouldPreserveStatusCards(messages);
        const cardsByAnchor = collectStatusCardsByAnchor(chatMessages, preserveStatusCards, messages);

        const snowContainer = document.getElementById('snowContainer');

        // 新規メッセージのみ追加（既存メッセージは保持）
        if (hasNewMessages) {
            chatMessages.appendChild(fragment);
        }

        syncChatMessageOrder(messages, cardsByAnchor, chatMessages);

        ensureSessionMessagesInDom(messages);
        if (sessionHasResolvedUserMessage(messages)) {
            removeTemporaryUserMessages();
        }

        // 装飾レイヤーは常に先頭（メッセージ並べ替えの影響を受けない）
        if (snowContainer && snowContainer.parentNode === chatMessages && chatMessages.firstChild !== snowContainer) {
            chatMessages.insertBefore(snowContainer, chatMessages.firstChild);
        }
        if (!shouldDeferSessionSync()) {
            removeOrphanedStreamingBubbles();
        }
        
        // 評価ボタンを追加（削除済み - HTMLに直接組み込み）
        
        // 応答確定後は処理中バブルと bot 応答の二重表示を防ぐ
        if (options.suppressTypingIndicator) {
            /* applyBotResponseSession 側で dismissTypingIndicator */
        } else if (keepTypingIndicator || (isSubmitting && !isResponseVisibleInDom(messages))) {
            ensureTypingIndicatorElement();
        } else {
            dismissTypingIndicator(messages);
        }

        // AI応答メッセージに評価ボタンを追加（削除済み - HTMLに直接組み込み）
        
        // 折りたたみ機能を初期化
        initCollapsibleSections();
        
        // 音声読み上げボタンを表示（推奨結果がある場合）
        checkAndShowVoiceReadButton();
        
        requestAnimationFrame(() => {
            if (isAtBottom) {
                scrollToBottom();
            } else {
                const newScrollHeight = chatMessages.scrollHeight;
                const heightDifference = newScrollHeight - currentScrollHeight;
                chatMessages.scrollTop = currentScrollTop + heightDifference;
            }
            updateSnowContainerHeight();
        });

        saveChatCache(getSidFromCookie(), dedupeMessageList(messages));
    }

    // 定期的にメッセージ部分だけAPIで取得して再描画（間隔10秒）
    setInterval(function refreshMessagesPeriodically() {
        fetch(withVersion('/api/sessions'), {
            credentials: 'include',
            headers: { 'Cache-Control': 'no-cache' }
        })
        .then(response => response.json())
        .then(data => {
            applyPeriodicSessionSync(data || {});
        })
        .catch(error => {
            if (isSessionResetPending()) {
                return;
            }
            const cached = loadChatCache(getSidFromCookie());
            if (cached.length > 0) {
                renderChatMessages(cached);
            }
        });
    }, 10000);
    
    // モーダル関連の関数
    function openAttributeModal() {
        // 今日の日付をmaxに設定
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('attr_duration_date').max = today;
        
        // セッション情報から既存のユーザー属性を取得してフォームに設定
        fetch('/api/sessions')
            .then(response => response.json())
            .then(data => {
                const attrs = data.user_attributes || {};
                
                // 年齢を設定
                if (attrs.age) {
                    document.getElementById('attr_age').value = attrs.age;
                }
                
                // 性別を設定
                if (attrs.gender) {
                    document.getElementById('attr_gender').value = attrs.gender;
                    togglePregnancyFields(); // 性別に応じて妊娠・授乳フィールドを表示
                    
                    // 妊娠・授乳状態を設定（女性の場合のみ）
                    if (attrs.gender === '女性') {
                        if (attrs.pregnant !== undefined && attrs.pregnant !== null) {
                            document.getElementById('attr_pregnant').value = attrs.pregnant ? 'yes' : 'no';
                        }
                        if (attrs.breastfeeding !== undefined && attrs.breastfeeding !== null) {
                            document.getElementById('attr_breastfeeding').value = attrs.breastfeeding ? 'yes' : 'no';
                        }
                    }
                }
                
                // アレルギーを設定
                if (attrs.allergies && Array.isArray(attrs.allergies) && attrs.allergies.length > 0) {
                    document.getElementById('attr_allergies').value = attrs.allergies.join('、');
                } else if (attrs.allergies && typeof attrs.allergies === 'string') {
                    document.getElementById('attr_allergies').value = attrs.allergies;
                }
                
                // 服用中の薬を設定
                if (attrs.current_medications && Array.isArray(attrs.current_medications) && attrs.current_medications.length > 0) {
                    document.getElementById('attr_has_medications').value = 'yes';
                    toggleMedicationsField(); // 服用中の薬の詳細フィールドを表示
                    document.getElementById('attr_medications').value = attrs.current_medications.join('、');
                } else if (attrs.current_medications && typeof attrs.current_medications === 'string' && attrs.current_medications.trim()) {
                    document.getElementById('attr_has_medications').value = 'yes';
                    toggleMedicationsField();
                    document.getElementById('attr_medications').value = attrs.current_medications;
                } else {
                    document.getElementById('attr_has_medications').value = 'no';
                    toggleMedicationsField();
                }
                
                // 症状期間を設定（symptom_duration_daysから日付を逆算）
                if (attrs.symptom_duration_days !== undefined && attrs.symptom_duration_days !== null) {
                    const days = attrs.symptom_duration_days;
                    if (days > 0) {
                        const startDate = new Date();
                        startDate.setDate(startDate.getDate() - days);
                        const dateStr = startDate.toISOString().split('T')[0];
                        document.getElementById('attr_duration_date').value = dateStr;
                    }
                }
                
                // その他情報を設定
                if (attrs.other_info) {
                    document.getElementById('attr_other').value = attrs.other_info;
                }
            })
            .catch(error => {
                console.error('セッション情報の取得エラー:', error);
                // エラーが発生してもモーダルは開く
            });
        
        document.getElementById('attributeModal').style.display = 'block';
    }
    
    function closeAttributeModal() {
        document.getElementById('attributeModal').style.display = 'none';
    }
    
    // モーダル外をクリックで閉じる
    window.onclick = function(event) {
        const modal = document.getElementById('attributeModal');
        if (event.target === modal) {
            closeAttributeModal();
        }
    }
    
    // 性別選択時に妊娠・授乳の表示を切り替え
    function togglePregnancyFields() {
        const gender = document.getElementById('attr_gender').value;
        const pregnancyGroup = document.getElementById('pregnancy_group');
        const breastfeedingGroup = document.getElementById('breastfeeding_group');
        
        if (gender === '女性') {
            pregnancyGroup.style.display = 'block';
            breastfeedingGroup.style.display = 'block';
        } else {
            pregnancyGroup.style.display = 'none';
            breastfeedingGroup.style.display = 'none';
            document.getElementById('attr_pregnant').value = '';
            document.getElementById('attr_breastfeeding').value = '';
        }
    }
    
    // 服用中の薬の詳細表示を切り替え
    function toggleMedicationsField() {
        const hasMedications = document.getElementById('attr_has_medications').value;
        const medicationsDetailGroup = document.getElementById('medications_detail_group');
        
        if (hasMedications === 'yes') {
            medicationsDetailGroup.style.display = 'block';
        } else {
            medicationsDetailGroup.style.display = 'none';
            document.getElementById('attr_medications').value = '';
        }
    }
    
    // 属性フォームの送信
    function submitAttributes() {
        const age = document.getElementById('attr_age').value;
        const gender = document.getElementById('attr_gender').value;
        const pregnant = document.getElementById('attr_pregnant').value;
        const breastfeeding = document.getElementById('attr_breastfeeding').value;
        const allergies = document.getElementById('attr_allergies').value;
        const hasMedications = document.getElementById('attr_has_medications').value;
        const medications = document.getElementById('attr_medications').value;
        const durationDate = document.getElementById('attr_duration_date').value;
        const other = document.getElementById('attr_other').value;
        
        // 日付から期間を計算
        let duration = '';
        if (durationDate) {
            const startDate = new Date(durationDate);
            const today = new Date();
            const diffTime = Math.abs(today - startDate);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            if (diffDays === 0) {
                duration = '今日から';
            } else if (diffDays === 1) {
                duration = '昨日から';
            } else if (diffDays < 7) {
                duration = `${diffDays}日前から`;
            } else {
                const diffWeeks = Math.floor(diffDays / 7);
                duration = `${diffWeeks}週間前から`;
            }
        }
        
        // 回答を組み立てる
        let response = [];
        if (age) response.push(`${age}歳です`);
        if (gender) response.push(`${gender}です`);
        if (gender === '女性') {
            if (pregnant === 'no') response.push('妊娠していません');
            else if (pregnant === 'yes') response.push('妊娠中です');
            if (breastfeeding === 'no') response.push('授乳していません');
            else if (breastfeeding === 'yes') response.push('授乳中です');
        }
        if (allergies) response.push(`アレルギーは${allergies}です`);
        else response.push('アレルギーはありません');
        
        // 服用中の薬
        if (hasMedications === 'yes' && medications) {
            response.push(`現在${medications}を服用しています`);
        } else if (hasMedications === 'no') {
            response.push('他に服用している薬はありません');
        }
        
        if (duration) response.push(`症状は${duration}続いています`);
        if (other) response.push(other);

        // セッションに other_info を永続（嗜好 NLU 用）
        const attrPayload = {
            age: age ? parseInt(age, 10) : undefined,
            gender: gender || undefined,
            allergies: allergies ? allergies.split('、').map(a => a.trim()).filter(Boolean) : ['なし'],
            other_info: other || ''
        };
        if (gender === '女性') {
            attrPayload.pregnant = pregnant === 'yes';
            attrPayload.breastfeeding = breastfeeding === 'yes';
        }
        if (hasMedications === 'yes' && medications) {
            attrPayload.current_medications = medications.split('、').map(m => m.trim()).filter(Boolean);
        } else if (hasMedications === 'no') {
            attrPayload.current_medications = [];
        }
        fetch('/api/sessions', {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' },
            body: JSON.stringify({ user_attributes: attrPayload })
        }).catch(err => console.warn('属性 other_info 保存エラー:', err));
        
        // バックエンドで「追加情報モーダルからの送信」と確実に判定するためのプレフィックス
        const PREFIX = '[ADDITIONAL_INFO_SUBMIT]';
        const message = PREFIX + (response.join('。') + '。');
        
        console.log('属性フォーム送信:', message);
        
        // モーダルを閉じる
        closeAttributeModal();
        
        // フォームをリセット
        document.getElementById('attributeForm').reset();
        togglePregnancyFields(); // 妊娠・授乳フィールドを非表示に戻す
        
        // メッセージとして送信
        const input = document.getElementById('messageInput');
        input.value = message;
        document.getElementById('chatForm').dispatchEvent(new Event('submit'));
    }

    // ユーザー情報登録モーダル制御
    function openUserInfoModal() {
        document.getElementById('userInfoModal').style.display = 'flex';
        loadExistingUserInfo();
    }
    
    function closeUserInfoModal() {
        document.getElementById('userInfoModal').style.display = 'none';
    }
    
    // 情報を修正ボタン用の関数
    function editUserInfo() {
        openUserInfoModal();
    }
    
    // グローバルスコープに公開
    window.editUserInfo = editUserInfo;
    window.openUserInfoModal = openUserInfoModal;
    
    // 既存のユーザー情報を読み込む
    function loadExistingUserInfo() {
        fetch('/api/sessions', {
            credentials: 'include',
            headers: { 'Cache-Control': 'no-cache' }
        })
            .then(response => response.json())
            .then(data => {
                const raw = data.user_attributes || {};
                const attrs = (window.SafetyRail && window.SafetyRail.normalizeAttrs)
                    ? window.SafetyRail.normalizeAttrs(raw)
                    : raw;
                
                // 年齢を設定
                if (attrs.age != null && attrs.age !== '') {
                    document.getElementById('user_age').value = attrs.age;
                }
                
                // 性別を設定
                if (attrs.gender) {
                    document.getElementById('user_gender').value = attrs.gender;
                    toggleUserPregnancyFields(); // 性別に応じて妊娠・授乳フィールドを表示
                    
                    // 妊娠・授乳状態を設定（女性の場合のみ）
                    if (attrs.gender === '女性') {
                        if (attrs.pregnant !== undefined && attrs.pregnant !== null) {
                            document.getElementById('user_pregnant').value = attrs.pregnant ? 'true' : 'false';
                        }
                        if (attrs.breastfeeding !== undefined && attrs.breastfeeding !== null) {
                            document.getElementById('user_breastfeeding').value = attrs.breastfeeding ? 'true' : 'false';
                        }
                    }
                }
                
                // アレルギーを設定
                if (attrs.allergies) {
                    if (Array.isArray(attrs.allergies)) {
                        document.getElementById('user_allergies').value = attrs.allergies.join('、');
                    } else if (typeof attrs.allergies === 'string') {
                        document.getElementById('user_allergies').value = attrs.allergies;
                    }
                }
                
                // 服用中の薬を設定
                if (attrs.current_medications) {
                    if (Array.isArray(attrs.current_medications)) {
                        document.getElementById('user_medications').value = attrs.current_medications.join('、');
                    } else if (typeof attrs.current_medications === 'string') {
                        document.getElementById('user_medications').value = attrs.current_medications;
                    }
                }
                
                // 既往症を設定
                if (attrs.medical_history) {
                    if (Array.isArray(attrs.medical_history)) {
                        document.getElementById('user_medical_history').value = attrs.medical_history.join('、');
                    } else if (typeof attrs.medical_history === 'string') {
                        document.getElementById('user_medical_history').value = attrs.medical_history;
                    }
                }
                
                // その他情報を設定
                if (attrs.other_info) {
                    document.getElementById('user_other_info').value = attrs.other_info;
                }
            })
            .catch(error => {
                console.error('セッション情報の取得エラー:', error);
                // エラーが発生してもモーダルは開く
            });
    }
    
    // 性別選択時に妊娠・授乳フィールドを表示/非表示
    function toggleUserPregnancyFields() {
        const gender = document.getElementById('user_gender');
        if (!gender) return;
        
        const genderValue = gender.value;
        const pregnancyFields = document.getElementById('user_pregnancy_fields');
        
        if (genderValue === '女性' && pregnancyFields) {
            pregnancyFields.style.display = 'block';
        } else if (pregnancyFields) {
            pregnancyFields.style.display = 'none';
            const pregnantSelect = document.getElementById('user_pregnant');
            const breastfeedingSelect = document.getElementById('user_breastfeeding');
            if (pregnantSelect) pregnantSelect.value = '';
            if (breastfeedingSelect) breastfeedingSelect.value = '';
        }
    }
    
    // ユーザー情報を保存
    function saveUserInfo() {
        const age = document.getElementById('user_age').value;
        const gender = document.getElementById('user_gender').value;
        const pregnant = document.getElementById('user_pregnant')?.value === 'true';
        const breastfeeding = document.getElementById('user_breastfeeding')?.value === 'true';
        const allergies = document.getElementById('user_allergies').value;
        const medications = document.getElementById('user_medications').value;
        const medicalHistory = document.getElementById('user_medical_history').value;
        const otherInfo = document.getElementById('user_other_info').value;
        
        // 必須項目のチェック
        if (!age || !gender) {
            alert('年齢と性別は必須項目です。');
            return;
        }
        
        // ユーザー属性を構築
        const userAttributes = {
            age: parseInt(age),
            gender: gender,
            allergies: allergies ? allergies.split('、').map(a => a.trim()).filter(a => a) : [],
            current_medications: medications ? medications.split('、').map(m => m.trim()).filter(m => m) : [],
            medical_history: medicalHistory ? medicalHistory.split('、').map(h => h.trim()).filter(h => h) : [],
            other_info: otherInfo || ''
        };
        
        // 女性の場合のみ妊娠・授乳情報を追加
        if (gender === '女性') {
            userAttributes.pregnant = pregnant;
            userAttributes.breastfeeding = breastfeeding;
        }
        
        // サーバーに送信
        fetch('/api/sessions', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            body: JSON.stringify({
                user_attributes: userAttributes
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                window.__lastUserAttributes = userAttributes;
                refreshSageSafetyRail(userAttributes);
                alert('ユーザー情報を保存しました。');
                closeUserInfoModal();
            } else {
                alert('保存に失敗しました: ' + (data.message || '不明なエラー'));
            }
        })
        .catch(error => {
            console.error('ユーザー情報保存エラー:', error);
            alert('通信エラーが発生しました。もう一度お試しください。');
        });
    }
    
    // 音声読み上げ機能
    let isReading = false;
    let currentUtterance = null;
    let voiceReadSpeed = parseFloat(localStorage.getItem('voiceReadSpeed')) || 1.0;
    let voiceReadProgress = 0;
    
    // 音声読み上げのトグル機能
    function toggleVoiceRead() {
        if (isReading) {
            // 読み上げ中 → 停止
            speechSynthesis.cancel();
            updateVoiceReadButtonState(false);
            hideVoiceReadProgress();
            isReading = false;
        } else {
            // 停止中 → 開始
            speakFullRecommendation();
            updateVoiceReadButtonState(true);
            showVoiceReadProgress();
            isReading = true;
        }
    }
    
    // ボタンの状態を更新
    function updateVoiceReadButtonState(reading) {
        const buttons = document.querySelectorAll('.voice-read-main-btn');
        buttons.forEach(button => {
            if (reading) {
                button.innerHTML = '■ 読み上げを停止';
                button.classList.add('playing');
                button.setAttribute('aria-label', '読み上げを停止する');
            } else {
                button.innerHTML = '🔊 音声で聞く';
                button.classList.remove('playing');
                button.setAttribute('aria-label', '推奨結果を音声で読み上げる');
            }
        });
    }
    
    // 全文読み上げ
    function speakFullRecommendation() {
        const recommendationResult = getLatestRecommendationRoot();
        if (!recommendationResult) {
            alert('読み上げる内容が見つかりませんでした。');
            return;
        }
        
        // テキストを抽出（HTMLタグを除去）
        const text = recommendationResult.innerText || recommendationResult.textContent;
        if (!text || text.trim().length === 0) {
            alert('読み上げる内容がありません。');
            return;
        }
        
        // 既存の読み上げを停止
        speechSynthesis.cancel();
        
        // 新しい読み上げを開始
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'ja-JP';
        utterance.rate = voiceReadSpeed;
        utterance.volume = 1.0;
        utterance.pitch = 1.0;
        
        // 進行状況の更新
        utterance.onstart = function() {
            voiceReadProgress = 0;
            updateVoiceReadProgress(0);
        };
        
        // 進行状況をシミュレート（実際の進行状況は取得できないため）
        let progressInterval = null;
        progressInterval = setInterval(() => {
            if (isReading && voiceReadProgress < 95) {
                voiceReadProgress += 2;
                updateVoiceReadProgress(voiceReadProgress);
            } else {
                if (progressInterval) {
                    clearInterval(progressInterval);
                    progressInterval = null;
                }
            }
        }, 500);
        
        // 読み上げ終了時に100%に更新
        utterance.onend = function() {
            if (progressInterval) {
                clearInterval(progressInterval);
                progressInterval = null;
            }
            updateVoiceReadProgress(100);
            setTimeout(() => {
                updateVoiceReadButtonState(false);
                hideVoiceReadProgress();
                isReading = false;
                voiceReadProgress = 0;
            }, 300); // 100%表示を少し見せるため300ms待機
        };
        
        utterance.onerror = function(event) {
            console.error('音声読み上げエラー:', event);
            if (progressInterval) {
                clearInterval(progressInterval);
                progressInterval = null;
            }
            updateVoiceReadButtonState(false);
            hideVoiceReadProgress();
            isReading = false;
            voiceReadProgress = 0;
            alert('音声読み上げでエラーが発生しました。ブラウザの音声読み上げ機能が有効か確認してください。');
        };
        
        // 音声読み上げの準備ができているか確認
        if (typeof speechSynthesis === 'undefined' || !speechSynthesis) {
            alert('お使いのブラウザは音声読み上げ機能に対応していません。');
            updateVoiceReadButtonState(false);
            hideVoiceReadProgress();
            isReading = false;
            return;
        }
        
        // 音声が利用可能になるまで待機
        const speakWhenReady = () => {
            if (speechSynthesis.speaking) {
                // 既に読み上げ中の場合は停止
                speechSynthesis.cancel();
            }
            
            try {
                currentUtterance = utterance;
                speechSynthesis.speak(utterance);
                console.log('音声読み上げを開始しました');
            } catch (error) {
                console.error('音声読み上げの開始に失敗:', error);
                alert('音声読み上げの開始に失敗しました。ブラウザの音声読み上げ機能を確認してください。');
                updateVoiceReadButtonState(false);
                hideVoiceReadProgress();
                isReading = false;
            }
        };
        
        // 音声が利用可能か確認
        if (speechSynthesis.getVoices().length === 0) {
            // 音声リストがまだ読み込まれていない場合、イベントを待つ
            speechSynthesis.onvoiceschanged = () => {
                speakWhenReady();
            };
        } else {
            speakWhenReady();
        }
    }
    
    // 進行状況表示の更新
    function updateVoiceReadProgress(percentage) {
        const progressBars = document.querySelectorAll('#voice-read-progress-bar, #voice-read-progress-bar-inline');
        const percentageTexts = document.querySelectorAll('#voice-read-percentage, #voice-read-percentage-inline');
        
        progressBars.forEach(progressBar => {
            if (progressBar) {
                progressBar.style.width = percentage + '%';
            }
        });
        
        percentageTexts.forEach(percentageText => {
            if (percentageText) {
                percentageText.textContent = Math.round(percentage) + '%';
            }
        });
    }
    
    // 進行状況表示を表示
    function showVoiceReadProgress() {
        const containers = document.querySelectorAll('#voice-read-progress, #voice-read-progress-inline');
        containers.forEach(container => {
            if (container) {
                container.style.display = 'block';
            }
        });
    }
    
    // 進行状況表示を非表示
    function hideVoiceReadProgress() {
        const containers = document.querySelectorAll('#voice-read-progress, #voice-read-progress-inline');
        containers.forEach(container => {
            if (container) {
                container.style.display = 'none';
            }
        });
        updateVoiceReadProgress(0);
    }
    
    // 速度調整
    function setVoiceReadSpeed(speed) {
        voiceReadSpeed = speed;
        localStorage.setItem('voiceReadSpeed', speed.toString());
        
        // 読み上げ中の場合は再開
        if (isReading) {
            speechSynthesis.cancel();
            setTimeout(() => {
                speakFullRecommendation();
            }, 100);
        }
    }
    
    // 推奨結果が表示されたら音声読み上げボタンを表示（recommendation-result内のボタンを使用）
    function checkAndShowVoiceReadButton() {
        const recommendationResult = getLatestRecommendationRoot();
        const voiceReadContainer = document.getElementById('voice-read-container-inline');
        
        if (recommendationResult && voiceReadContainer) {
            voiceReadContainer.style.display = 'block';
        }
    }
    
    // 設定ページの状態を更新
    function updateSettingsPage() {
        // 現在の文字サイズを反映
        const currentSize = localStorage.getItem('fontSize') || 'normal';
        document.querySelectorAll('.font-size-btn').forEach(btn => {
            if (btn.dataset.size === currentSize) {
                btn.style.background = '#4CAF50';
                btn.style.color = 'white';
            } else {
                btn.style.background = 'white';
                btn.style.color = '#4CAF50';
            }
        });
        
        // 現在の速度設定を反映（速度ボタンがあれば）
        const currentSpeed = parseFloat(localStorage.getItem('voiceReadSpeed')) || 1.0;
        // 速度ボタンの状態更新は必要に応じて実装
    }
    
    // 音声入力機能
    let voiceRecognition = null;
    let isVoiceRecording = false;
    let voicePreviousValue = ''; // 音声認識開始時の既存値を保持
    
    function initVoiceRecognition() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            console.log('音声認識APIはこのブラウザではサポートされていません');
            alert('このブラウザは音声認識に対応していません。Chrome、Edge、Safariなど対応ブラウザをご利用ください。');
            return false;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        voiceRecognition = new SpeechRecognition();
        
        // 現在の言語設定に応じて言語を設定
        const langMap = {
            'ja': 'ja-JP',
            'en': 'en-US',
            'ko': 'ko-KR',
            'zh': 'zh-CN'
        };
        voiceRecognition.lang = langMap[currentLanguage] || 'ja-JP';
        voiceRecognition.continuous = false;
        voiceRecognition.interimResults = true; // 中間結果も取得してリアルタイム表示
        
        voiceRecognition.onresult = (event) => {
            const messageInput = document.getElementById('messageInput');
            if (!messageInput) {
                console.error('messageInput要素が見つかりません');
                return;
            }
            
            let finalTranscript = '';
            let interimTranscript = '';
            
            // すべての結果を処理
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // 最終結果がある場合は確定
            if (finalTranscript) {
                messageInput.value = (voicePreviousValue + ' ' + finalTranscript).trim();
                voicePreviousValue = messageInput.value; // 次の認識用に保存
                console.log('音声認識結果（確定）:', finalTranscript);
            } else if (interimTranscript) {
                // 中間結果は一時表示（確定部分 + 中間結果）
                messageInput.value = (voicePreviousValue + ' ' + interimTranscript).trim();
            }
            
            // textareaの高さを調整
            // inputイベントを発火して他のリスナーにも通知（resizeMessageInput も実行）
            const inputEvent = new Event('input', { bubbles: true, cancelable: true });
            messageInput.dispatchEvent(inputEvent);
        };
        
        voiceRecognition.onerror = (event) => {
            console.error('音声認識エラー:', event.error);
            stopVoiceInput();
            
            let errorMessage = '';
            switch(event.error) {
                case 'not-allowed':
                    errorMessage = 'マイクの使用が許可されていません。ブラウザの設定からマイクを許可してください。';
                    break;
                case 'no-speech':
                    // 無音の場合は自動停止のみ（メッセージは表示しない）
                    return;
                case 'audio-capture':
                    errorMessage = 'マイクが見つかりません。マイクが接続されているか確認してください。';
                    break;
                case 'network':
                    errorMessage = 'ネットワークエラーが発生しました。';
                    break;
                default:
                    errorMessage = '音声認識エラー: ' + event.error;
            }
            alert(errorMessage);
        };
        
        voiceRecognition.onend = () => {
            // 自動停止（1回の認識が終了したら）
            if (isVoiceRecording) {
                isVoiceRecording = false;
                const micBtn = document.getElementById('micBtn');
                if (micBtn) {
                    micBtn.classList.remove('recording');
                    micBtn.title = '音声入力';
                }
                
                // 最後の結果を確実に反映
                const messageInput = document.getElementById('messageInput');
                if (messageInput) {
                    // 値を正規化（余分な空白を削除）
                    messageInput.value = messageInput.value.trim();
                    voicePreviousValue = messageInput.value; // 値を更新
                    // inputイベントを発火
                    messageInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        };
        
        return true;
    }
    
    function toggleVoiceInput() {
        try {
            if (!voiceRecognition) {
                if (!initVoiceRecognition()) {
                    return;
                }
            }
            
            if (isVoiceRecording) {
                stopVoiceInput();
            } else {
                startVoiceInput();
            }
        } catch (error) {
            console.error('音声入力切替エラー:', error);
            alert('音声入力の切り替えに失敗しました: ' + error.message);
        }
    }
    
    function startVoiceInput() {
        try {
            if (!voiceRecognition) {
                if (!initVoiceRecognition()) {
                    return;
                }
            }
            
            // 既存の値を保持するために、認識開始時に現在の値を取得
            const messageInput = document.getElementById('messageInput');
            if (messageInput) {
                voicePreviousValue = messageInput.value || '';
            }
            
            voiceRecognition.start();
            isVoiceRecording = true;
            
            const micBtn = document.getElementById('micBtn');
            if (micBtn) {
                micBtn.classList.add('recording');
                micBtn.title = '録音中... (クリックで停止)';
            }
        } catch (error) {
            console.error('音声認識開始エラー:', error);
            isVoiceRecording = false;
            const micBtn = document.getElementById('micBtn');
            if (micBtn) {
                micBtn.classList.remove('recording');
                micBtn.title = '音声入力';
            }
            alert('音声認識の開始に失敗しました: ' + error.message);
        }
    }
    
    function stopVoiceInput() {
        if (voiceRecognition) {
            try {
                voiceRecognition.stop();
            } catch (error) {
                console.error('音声認識停止エラー:', error);
            }
        }
        isVoiceRecording = false;
        
        const micBtn = document.getElementById('micBtn');
        if (micBtn) {
            micBtn.classList.remove('recording');
            micBtn.title = '音声入力';
        }
    }
    
