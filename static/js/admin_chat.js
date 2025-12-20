// グローバルエラーハンドラー
window.addEventListener('error', function(event) {
    console.error('🔴 Global error:', event.error);
    console.error('🔴 Error message:', event.message);
    console.error('🔴 Error at:', event.filename, 'line', event.lineno);
});

window.addEventListener('unhandledrejection', function(event) {
    console.error('🔴 Unhandled promise rejection:', event.reason);
});

console.log('📄 Script loaded successfully');

let currentSessionId = null;
let allSessions = [];
let currentDetailedDiagnosis = null; // 管理APIからの詳細診断（スコア内訳含む）
let currentMessages = []; // 現在のセッションのメッセージ（診断情報のフォールバック用）
let socket = null;

// ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Admin page loaded, initializing...');
    
    // 関数が定義されているか確認
    console.log('🔍 Function check:');
    console.log('  - refreshAIStatus:', typeof refreshAIStatus);
    console.log('  - refreshQueue:', typeof refreshQueue);
    console.log('  - refreshSessionList:', typeof refreshSessionList);
    console.log('  - renderSessionList:', typeof renderSessionList);
    console.log('  - selectSession:', typeof selectSession);
    
    // 初期データ読み込み（エラーハンドリング付き）
    try {
        console.log('📡 Calling refreshAIStatus...');
        refreshAIStatus();
    } catch (error) {
        console.error('❌ refreshAIStatus error:', error);
    }
    
    try {
        console.log('📡 Calling refreshQueue...');
        refreshQueue();
    } catch (error) {
        console.error('❌ refreshQueue error:', error);
    }
    
    try {
        console.log('📡 Calling refreshSessionList...');
        refreshSessionList();
    } catch (error) {
        console.error('❌ refreshSessionList error:', error);
    }
    
    // レスポンシブ要素の初期化
    try {
        // 関数が定義されているか確認
        if (typeof toggleMobileElements === 'function') {
            toggleMobileElements();
        }
        if (typeof initPanelResize === 'function') {
            initPanelResize();
        }
    } catch (error) {
        console.error('❌ Responsive initialization error:', error);
    }
    
    // 管理ボタンのイベントリスナー
    // グローバルスコープのshowModal関数を使用（関数宣言はホイスティングされるため直接呼び出し可能）
    
    document.getElementById('aiControlBtn').addEventListener('click', function() {
        showModal('aiControlModal');
        // モーダル表示時にメッセージを読み込む
        loadManualReplyMessage();
    });
    
    document.getElementById('systemStatusBtn').addEventListener('click', function() {
        showModal('systemStatusModal');
        loadSystemStatus();
    });
    
    document.getElementById('monitoringBtn').addEventListener('click', function() {
        showModal('monitoringModal');
        loadMonitoringData();
    });
    
    document.getElementById('medicineChatBtn').addEventListener('click', function() {
        showModal('medicineChatModal');
    });
    
    document.getElementById('clearLogsBtn').addEventListener('click', function() {
        if (confirm('すべてのログをクリアしますか？')) {
            clearAllLogs();
        }
    });
    
    // 不具合報告ボタンのイベントリスナー
    const feedbackReportsBtn = document.getElementById('feedbackReportsBtn');
    if (feedbackReportsBtn) {
        feedbackReportsBtn.addEventListener('click', function() {
            console.log('🔵 feedbackReportsBtn clicked');
            showModal('feedbackReportsModal');
            // モーダルが表示された後にデータを読み込む
            setTimeout(() => {
                loadFeedbackReports();
            }, 100);
        });
    }
    
    // モバイルメニューの不具合報告ボタン
    const feedbackReportsBtnMobile = document.getElementById('feedbackReportsBtnMobile');
    if (feedbackReportsBtnMobile) {
        feedbackReportsBtnMobile.addEventListener('click', function() {
            console.log('🔵 feedbackReportsBtnMobile clicked');
            showModal('feedbackReportsModal');
            toggleMobileMenu();
            // モーダルが表示された後にデータを読み込む
            setTimeout(() => {
                loadFeedbackReports();
            }, 100);
        });
    }
    
    // ユーザー属性ボタンのイベントリスナー
    const userAttributesBtn = document.getElementById('userAttributesBtn');
    if (userAttributesBtn) {
        userAttributesBtn.addEventListener('click', function() {
            console.log('🔵 userAttributesBtn clicked via addEventListener');
            if (typeof showUserAttributesModal === 'function') {
                showUserAttributesModal();
            } else {
                console.error('❌ showUserAttributesModal function not found');
            }
        });
    }
    
    // モーダルの閉じるボタン
    document.querySelectorAll('.close').forEach(function(closeBtn) {
        closeBtn.addEventListener('click', function() {
            const modal = this.closest('.admin-modal') || this.closest('.modal');
            if (modal) {
                // userAttributesModalの場合は専用の閉じる関数を使用
                if (modal.id === 'userAttributesModal') {
                    console.log('🔴 Close button clicked for userAttributesModal');
                    closeUserAttributesModal();
                } else {
                    modal.style.display = 'none';
                    modal.classList.remove('show');
                }
            }
        });
    });
    
    // モーダル外クリックで閉じる
    window.addEventListener('click', function(event) {
        // モーダル要素自体をクリックした場合のみ閉じる（コンテンツ内のクリックは無視）
        const modal = event.target.closest('.admin-modal') || event.target.closest('.modal');
        if (modal && event.target === modal) {
            // userAttributesModalの場合は専用の閉じる関数を使用
            if (modal.id === 'userAttributesModal') {
                console.log('🔴 Clicked outside userAttributesModal (on backdrop), closing...');
                closeUserAttributesModal();
            } else {
                modal.style.display = 'none';
                modal.classList.remove('show');
            }
        }
    });
    
    // チャット入力の制御
    const chatInput = document.getElementById('chat-input');
    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 100) + 'px';
        
        // 送信ボタンの有効/無効を切り替え
        updateSendButtonState();
    });
    
    // 手動更新のみ: 自動更新を無効化
    let updateTimer = null;
    
    // 初期データ読み込み
    function loadInitialData() {
        // キューとセッション情報を一度に更新
        Promise.all([
            fetch('/api/main_manual_reply_queue', {
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            }).then(res => res.json()),
            fetch('/api/main_sessions', {
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            }).then(res => res.json())
        ])
        .then(([queueData, sessionsData]) => {
            console.log('✅ Initial data loaded successfully');
            renderQueue(queueData);
            updateStats(queueData);
            
            // APIは {sessions: [...]} の形式で返すため、data.sessions にアクセス
            const sessionsArray = sessionsData.sessions || (Array.isArray(sessionsData) ? sessionsData : []);
            renderCurrentSession(sessionsArray.length > 0 ? sessionsArray[0] : null);
            
            // セッション一覧も更新
            allSessions = sessionsArray;
            renderSessionList(allSessions);
            const totalSessionsEl = document.getElementById('total-sessions') || document.getElementById('session-count');
            if (totalSessionsEl) {
                totalSessionsEl.textContent = allSessions.length;
            }
            
            // 初期データ読み込み後にmanual-reply-queueの高さを調整
            setTimeout(() => {
                adjustManualReplyQueueHeight();
            }, 200);
        })
        .catch(error => {
            console.error('❌ Initial data load error:', error);
        });
    }
    
    // 初期データ読み込み
    loadInitialData();
    
    // パネルリサイザーの初期化
    initPanelResizers();
    
    // 初期化時にmanual-reply-queueの高さを調整
    setTimeout(() => {
        if (typeof adjustManualReplyQueueHeight === 'function') {
            adjustManualReplyQueueHeight();
        }
    }, 500);
    
    // 統計情報アコーディオンをデフォルトで開く
    const statsAccordion = document.getElementById('stats-accordion');
    if (statsAccordion) {
        statsAccordion.classList.add('open');
        const icon = document.getElementById('stats-accordion-icon');
        if (icon) icon.classList.add('rotated');
    }
    
    // AI管理アコーディオンをデフォルトで開く
    const aiAccordion = document.getElementById('ai-management-accordion');
    if (aiAccordion) {
        aiAccordion.classList.add('open');
        const icon = document.getElementById('ai-management-accordion-icon');
        if (icon) icon.classList.add('rotated');
    }
});

// 手動更新関数（グローバルスコープ）
// モバイルメニューのトグル
function toggleMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    if (menu) {
        menu.classList.toggle('show');
    }
}

// アコーディオンのトグル
function toggleAccordion(id) {
    const content = document.getElementById(id);
    const icon = document.getElementById(id + '-icon');
    
    if (content) {
        const isOpen = content.classList.contains('open');
        if (isOpen) {
            content.classList.remove('open');
            content.classList.add('closed');
        } else {
            content.classList.remove('closed');
            content.classList.add('open');
        }
        
        if (icon) {
            icon.classList.toggle('rotated');
        }
        
        // アコーディオン開閉後にmanual-reply-queueの高さを調整
        setTimeout(() => {
            adjustManualReplyQueueHeight();
        }, 350); // アニメーション完了を待つ（0.3s + 0.05s余裕）
    }
}

// manual-reply-queueの高さを調整する関数
function adjustManualReplyQueueHeight() {
    const rightPanel = document.getElementById('right-panel');
    const manualReplyQueue = document.getElementById('manual-reply-queue');
    const infoSection = manualReplyQueue?.closest('.info-section');
    
    if (!rightPanel || !manualReplyQueue || !infoSection) return;
    
    // 右パネルの高さを取得
    const rightPanelHeight = rightPanel.clientHeight;
    
    // ヘッダーの高さを取得
    const panelHeader = rightPanel.querySelector('.panel-header');
    const headerHeight = panelHeader ? panelHeader.offsetHeight : 0;
    
    // アコーディオンの高さを取得
    const accordion = rightPanel.querySelector('.accordion');
    let accordionHeight = 0;
    if (accordion) {
        const accordionHeader = accordion.querySelector('.accordion-header');
        const accordionContent = accordion.querySelector('.accordion-content');
        accordionHeight = (accordionHeader ? accordionHeader.offsetHeight : 0) + 
                         (accordionContent && accordionContent.classList.contains('open') ? accordionContent.scrollHeight : 0);
    }
    
    // info-sectionの他の要素の高さを取得（タイトル、ボタンなど）
    const infoSectionChildren = Array.from(infoSection.children);
    let otherElementsHeight = 0;
    infoSectionChildren.forEach(child => {
        if (child !== manualReplyQueue) {
            otherElementsHeight += child.offsetHeight;
        }
    });
    
    // paddingとborderを考慮
    const paddingTop = parseFloat(getComputedStyle(infoSection).paddingTop) || 0;
    const paddingBottom = parseFloat(getComputedStyle(infoSection).paddingBottom) || 0;
    const borderBottom = parseFloat(getComputedStyle(infoSection).borderBottomWidth) || 0;
    
    // 利用可能な高さを計算
    const availableHeight = rightPanelHeight - headerHeight - accordionHeight - otherElementsHeight - paddingTop - paddingBottom - borderBottom;
    
    // min-heightとmax-heightを考慮して設定
    const minHeight = 200;
    const calculatedHeight = Math.max(minHeight, availableHeight);
    
    // 高さを設定
    manualReplyQueue.style.height = `${calculatedHeight}px`;
    manualReplyQueue.style.maxHeight = 'none';
}

// パネルリサイズ機能
let isResizing = false;
let currentResizer = null;
let startX = 0;
let startLeftWidth = 0;
let startRightWidth = 0;

function initPanelResizers() {
    const leftResizer = document.getElementById('left-resizer');
    const centerResizer = document.getElementById('center-resizer');
    
    if (leftResizer) {
        leftResizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            currentResizer = 'left';
            startX = e.clientX;
            const leftPanel = document.getElementById('left-panel');
            const rightPanel = document.getElementById('right-panel');
            startLeftWidth = leftPanel.offsetWidth;
            startRightWidth = rightPanel.offsetWidth;
            document.addEventListener('mousemove', handleResize);
            document.addEventListener('mouseup', stopResize);
            leftResizer.classList.add('active');
            e.preventDefault();
        });
    }
    
    if (centerResizer) {
        centerResizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            currentResizer = 'center';
            startX = e.clientX;
            const leftPanel = document.getElementById('left-panel');
            const rightPanel = document.getElementById('right-panel');
            startLeftWidth = leftPanel.offsetWidth;
            startRightWidth = rightPanel.offsetWidth;
            document.addEventListener('mousemove', handleResize);
            document.addEventListener('mouseup', stopResize);
            centerResizer.classList.add('active');
            e.preventDefault();
        });
    }
}

function handleResize(e) {
    if (!isResizing) return;
    
    const deltaX = e.clientX - startX;
    const main = document.querySelector('main');
    const mainRect = main.getBoundingClientRect();
    const totalWidth = mainRect.width;
    const resizerWidth = 4; // リサイザーの幅
    const minLeftWidth = 200;
    const maxLeftWidth = 600;
    const minCenterWidth = 300;
    const minRightWidth = 200;
    const maxRightWidth = 600;
    
    if (currentResizer === 'left') {
        // 左リサイザーを動かす: 左パネルの幅を変更
        // 右パネルの右端は固定なので、左パネルの幅を変更すると中央パネルが自動調整される
        // 制約: 最小幅200px、最大幅600px、かつ中央パネルと右パネルの最小幅を確保
        const maxAllowedLeftWidth = Math.min(
            maxLeftWidth,
            totalWidth - minCenterWidth - startRightWidth - resizerWidth * 2
        );
        const newLeftWidth = Math.max(minLeftWidth, Math.min(maxAllowedLeftWidth, startLeftWidth + deltaX));
        // 中央パネルは1frで自動調整されるため、固定幅を指定しない
        main.style.gridTemplateColumns = `${newLeftWidth}px ${resizerWidth}px 1fr ${resizerWidth}px ${startRightWidth}px`;
    } else if (currentResizer === 'center') {
        // 中央リサイザーを動かす: 右パネルの幅を変更
        // 左パネルの左端は固定なので、右パネルの幅を変更すると中央パネルが自動調整される
        // 制約: 最小幅200px、最大幅600px、かつ中央パネルと左パネルの最小幅を確保
        const maxAllowedRightWidth = Math.min(
            maxRightWidth,
            totalWidth - startLeftWidth - minCenterWidth - resizerWidth * 2
        );
        const newRightWidth = Math.max(minRightWidth, Math.min(maxAllowedRightWidth, startRightWidth - deltaX));
        // 中央パネルは1frで自動調整されるため、固定幅を指定しない
        main.style.gridTemplateColumns = `${startLeftWidth}px ${resizerWidth}px 1fr ${resizerWidth}px ${newRightWidth}px`;
    }
}

function stopResize() {
    isResizing = false;
    currentResizer = null;
    document.removeEventListener('mousemove', handleResize);
    document.removeEventListener('mouseup', stopResize);
    
    const leftResizer = document.getElementById('left-resizer');
    const centerResizer = document.getElementById('center-resizer');
    if (leftResizer) leftResizer.classList.remove('active');
    if (centerResizer) centerResizer.classList.remove('active');
}

// モーダル表示関数（グローバル）
function showModal(modalId) {
    console.log('🔵 showModal called with modalId:', modalId);
    
    // 他のモーダルを閉じる
    const allModals = document.querySelectorAll('.admin-modal, .modal');
    allModals.forEach(modal => {
        if (modal.id !== modalId) {
            modal.style.display = 'none';
            modal.classList.remove('show');
        }
    });
    
    const modal = document.getElementById(modalId);
    if (modal) {
        // モーダルをbodyの直接の子要素として移動（確実にレンダリングされるように）
        if (modal.parentElement !== document.body) {
            console.log('🔵 Moving modal to body');
            document.body.appendChild(modal);
        }
        
        // 既存のインラインスタイルをクリアしてCSSに任せる
        modal.style.cssText = '';
        
        // showクラスを追加（CSSで #feedbackReportsModal.show のスタイルが適用される）
        modal.classList.add('show');
        
        // 強制的にレイアウトを再計算
        modal.offsetHeight;
        
        console.log('🔵 Modal shown:', modalId);
        console.log('🔵 Modal classes:', modal.className);
        console.log('🔵 Modal parent:', modal.parentElement.tagName);
        
        // 少し遅延してサイズを確認
        setTimeout(() => {
            const rect = modal.getBoundingClientRect();
            const computed = window.getComputedStyle(modal);
            console.log('🔵 Modal rect:', rect);
            console.log('🔵 Modal computed display:', computed.display);
            console.log('🔵 Modal computed width:', computed.width);
            console.log('🔵 Modal computed height:', computed.height);
        }, 50);
    } else {
        console.error('❌ Modal element not found:', modalId);
    }
}

// グローバルスコープに明示的に割り当て（onclick属性から呼び出せるように）
// DOMContentLoadedの前に設定するため、即座に実行
window.showModal = showModal;

// メニュー外クリックで閉じる
document.addEventListener('click', function(event) {
    const menu = document.getElementById('mobile-menu');
    const toggleBtn = document.getElementById('menu-toggle-btn');
    if (menu && toggleBtn && !menu.contains(event.target) && !toggleBtn.contains(event.target)) {
        menu.classList.remove('show');
    }
});

function manualRefresh() {
    // キューとセッション情報を一度に更新
    Promise.all([
        fetch('/api/main_manual_reply_queue', {
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        }).then(res => {
            if (!res.ok) {
                throw new Error(`キュー取得エラー: ${res.status} ${res.statusText}`);
            }
            return res.json();
        }),
        fetch('/api/main_sessions', {
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        }).then(res => {
            if (!res.ok) {
                throw new Error(`セッション取得エラー: ${res.status} ${res.statusText}`);
            }
            return res.json();
        })
    ])
    .then(([queueData, sessionsData]) => {
        renderQueue(queueData);
        updateStats(queueData);
        
        // APIは {sessions: [...]} の形式で返すため、data.sessions にアクセス
        const sessionsArray = sessionsData.sessions || (Array.isArray(sessionsData) ? sessionsData : []);
        renderCurrentSession(sessionsArray.length > 0 ? sessionsArray[0] : null);
        
        // セッション一覧も更新
        allSessions = sessionsArray;
        renderSessionList(allSessions);
        const totalSessionsEl = document.getElementById('total-sessions');
        if (totalSessionsEl) {
            totalSessionsEl.textContent = allSessions.length;
        } else {
            // session-countが存在する場合はそれを使用
            const sessionCountEl = document.getElementById('session-count');
            if (sessionCountEl) {
                sessionCountEl.textContent = allSessions.length;
            }
        }
        
        // manual-reply-queueの高さを調整
        setTimeout(() => {
            if (typeof adjustManualReplyQueueHeight === 'function') {
                adjustManualReplyQueueHeight();
            }
        }, 100);
        
        showNotification('データを更新しました', 'success');
    })
    .catch(error => {
        console.error('Manual refresh error:', error);
        const errorMessage = error.message || '更新エラーが発生しました';
        showNotification(errorMessage, 'error');
    });
}

function initializeSocket() {
    // WebSocket機能は簡素化し、定期的なAPI呼び出しに集中
    console.log('Admin chat initialized');
}

function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.classList.add('show');
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

function setAIMode(mode) {
    console.log('🔵 setAIMode called with mode:', mode);
    
    // modeが未定義またはnullの場合のエラーハンドリング
    if (!mode) {
        console.error('❌ setAIMode: mode is undefined or null');
        showNotification('エラー: モードが指定されていません', 'error');
        return;
    }
    
    if (mode === 'admin') {
        fetch('/api/admin_mode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(res => res.json())
        .then(data => {
            showNotification(data.message || '薬剤師対応モードに切り替えました');
            refreshAIStatus && refreshAIStatus();
            refreshQueue && refreshQueue();
        })
        .catch((error) => {
            console.error('薬剤師対応APIエラー:', error);
            showNotification('通信エラーが発生しました: ' + (error && error.message ? error.message : error), 'error');
        });
        return;
    }
    
    // 'on'/'off'を'auto'/'manual'に変換（後方互換性のため）
    let normalizedMode = mode;
    if (mode === 'on') {
        normalizedMode = 'auto';
    } else if (mode === 'off') {
        normalizedMode = 'manual';
    }
    
    // 有効なモードかチェック
    if (normalizedMode !== 'auto' && normalizedMode !== 'manual') {
        console.error('❌ setAIMode: invalid mode:', mode, '-> normalized:', normalizedMode);
        showNotification(`エラー: 無効なモードです (${mode})`, 'error');
        return;
    }
    
    console.log('🔵 Sending request with normalizedMode:', normalizedMode);
    
    fetch('/api/main_ai_control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({mode: normalizedMode})
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(data => {
                throw new Error(data.error || `HTTP error! status: ${res.status}`);
            });
        }
        return res.json();
    })
    .then(data => {
        console.log('✅ setAIMode response:', data);
        if (data.error) {
            showNotification(`エラー: ${data.error}`, 'error');
        } else {
            // 通知メッセージの表示（normalizedModeまたは元のmodeに基づいて）
            const displayMode = normalizedMode === 'auto' ? 'ON' : 'OFF';
            showNotification(data.message || `AI自動応答を${displayMode}にしました`);
            refreshAIStatus();
            refreshQueue();
        }
    })
    .catch(error => {
        console.error('❌ setAIMode error:', error);
        showNotification(`エラー: ${error.message}`, 'error');
    });
}

function refreshAIStatus() {
    fetch('/api/main_ai_control', {
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
        .then(res => res.json())
        .then(data => {
            const statusElement = document.getElementById('ai-status');
            const statusText = document.getElementById('status-text');
            const onBtn = document.getElementById('ai-on-btn');
            const offBtn = document.getElementById('ai-off-btn');
            const headerStatusText = document.getElementById('ai-status-text');
            const statusBadge = document.getElementById('ai-status-badge');
            
            // メッセージフィールドを更新（モーダルが開いている場合のみ）
            // ただし、保存直後（5秒以内）は更新しない（保存した値が上書きされないように）
            const messageField = document.getElementById('manualReplyMessage');
            const aiControlModal = document.getElementById('aiControlModal');
            const timeSinceLastSave = Date.now() - (lastMessageSaveTime || 0);
            const shouldSkipUpdate = timeSinceLastSave < 5000; // 5秒以内は更新しない
            
            if (messageField && data.manual_reply_message && aiControlModal && aiControlModal.classList.contains('show')) {
                // モーダルが開いている場合のみ更新
                // ただし、保存直後でないこと、ユーザーが編集中でないことを確認
                if (!shouldSkipUpdate && document.activeElement !== messageField) {
                    messageField.value = data.manual_reply_message;
                } else if (shouldSkipUpdate) {
                    console.log('⏭️ Skipping message field update (recently saved,', Math.round(timeSinceLastSave / 1000), 'seconds ago)');
                }
            }
            
            if (data.ai_auto_reply) {
                if (statusElement) statusElement.className = 'ai-status on';
                if (statusText) statusText.textContent = 'AI自動応答ON';
                if (headerStatusText) headerStatusText.textContent = 'AI自動応答ON';
                if (statusBadge) {
                    statusBadge.className = 'status-badge on';
                    statusBadge.innerHTML = '<i class="fa-solid fa-robot"></i><span id="ai-status-text">AI自動応答ON</span>';
                }
                if (onBtn) onBtn.disabled = true;
                if (offBtn) offBtn.disabled = false;
            } else {
                if (statusElement) statusElement.className = 'ai-status off';
                if (statusText) statusText.textContent = 'AI自動応答OFF';
                if (headerStatusText) headerStatusText.textContent = 'AI自動応答OFF';
                if (statusBadge) {
                    statusBadge.className = 'status-badge off';
                    statusBadge.innerHTML = '<i class="fa-solid fa-robot"></i><span id="ai-status-text">AI自動応答OFF</span>';
                }
                if (onBtn) onBtn.disabled = false;
                if (offBtn) offBtn.disabled = true;
            }
        })
        .catch(error => {
            console.error('AI状態取得エラー:', error);
            showNotification('AI状態取得エラー', 'error');
        });
}

function refreshQueue() {
    fetch('/api/main_manual_reply_queue', {
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
        .then(res => res.json())
        .then(data => {
            renderQueue(data);
            updateStats(data);
            // キュー更新後に高さを調整
            setTimeout(() => {
                adjustManualReplyQueueHeight();
            }, 100);
        })
        .catch(error => {
            showNotification('キュー取得エラー', 'error');
        });
    
    // 現在のセッション情報も取得（AI自動応答ONでも表示）
    fetch('/api/main_sessions', {
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
        .then(res => res.json())
        .then(data => {
            // APIは {sessions: [...]} の形式で返すため、data.sessions にアクセス
            const sessionsArray = data.sessions || (Array.isArray(data) ? data : []);
            renderCurrentSession(sessionsArray.length > 0 ? sessionsArray[0] : null);
        })
        .catch(error => {
            console.error('Current session error:', error);
        });
}

// 現在のセッション情報を保持する変数
let currentSessionData = null;

function renderQueue(queue) {
    const content = document.getElementById('manual-reply-queue');
    
    if (!content) return;
    
    // 現在のセッション情報を保持
    const existingCurrentSession = content.querySelector('.current-session');
    const currentSessionHtml = existingCurrentSession ? existingCurrentSession.outerHTML : '';
    
    if (!Array.isArray(queue) || queue.length === 0) {
        // 現在のセッション情報があれば表示
        if (currentSessionHtml) {
            content.innerHTML = currentSessionHtml;
        } else {
            content.innerHTML = `
                <div class="empty-state">
                    <i class="fa-regular fa-inbox"></i>
                    <p>手動返信待ちのメッセージがありません</p>
                </div>
            `;
        }
        return;
    }
    
    let html = '';
    queue.forEach((item, index) => {
        // 危機対応セッションかどうかをチェック
        const isCrisisItem = item.status === 'crisis_detected' || item.priority === 'high';
        const itemClass = isCrisisItem ? 'queue-item crisis-queue-item' : 'queue-item';
        const crisisBadge = isCrisisItem ? '<span class="crisis-badge">🚨 緊急</span>' : '';
        const accordionId = `queue-accordion-${index}`;
        const accordionContentId = `queue-accordion-content-${index}`;
        
        // メッセージを短縮表示（30文字まで）
        const shortMessage = item.user_message && item.user_message.length > 30 
            ? item.user_message.substring(0, 30) + '...' 
            : (item.user_message || 'メッセージなし');
        
        // セッションIDを短縮表示（8文字まで）
        const shortSessionId = item.session_id ? item.session_id.substring(0, 8) + '...' : '不明';
        
        const crisisKeywords = isCrisisItem && item.crisis_keywords ? 
            `<div class="crisis-keywords" style="background: #ffebee; padding: 8px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #e74c3c; font-size: 0.9em; color: #e74c3c;">
                <strong>検出キーワード:</strong> ${item.crisis_keywords.join(', ')}
            </div>` : '';
        
        html += `
            <div class="${itemClass} queue-accordion-item">
                <div class="queue-accordion-header" onclick="toggleQueueAccordion('${accordionId}', '${accordionContentId}')">
                    <div style="flex: 1; min-width: 0;">
                        <span class="session-id" style="font-size: 0.8rem; font-weight: 600; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px;">${shortSessionId} ${crisisBadge}</span>
                        <div style="font-size: 0.75rem; color: #666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${shortMessage}</div>
                    </div>
                    <i class="fa-solid fa-chevron-down queue-accordion-icon" id="${accordionId}-icon" style="flex-shrink: 0; margin-left: 4px;"></i>
                </div>
                <div class="queue-accordion-content" id="${accordionContentId}" style="max-height: 0; overflow: hidden; transition: max-height 0.3s ease;">
                    <div style="padding: 4px 8px; background: #f8f9fa; border-top: 1px solid #dee2e6;">
                        <div class="user-message" style="margin-bottom: 6px; font-size: 0.75rem;">
                            <strong>👤 ユーザー:</strong> ${item.user_message || 'メッセージなし'}
                        </div>
                        ${crisisKeywords}
                        <div style="display: flex; flex-wrap: wrap; gap: 8px; font-size: 0.7rem; color: #666; margin-bottom: 6px;">
                            <span><strong>🕐</strong> ${item.timestamp || '不明'}</span>
                        </div>
                        <div style="font-size: 0.65rem; color: #999; margin-bottom: 6px; word-break: break-all;">
                            ID: ${item.session_id || '不明'}
                        </div>
                        <div class="reply-section" style="margin-top: 6px;">
                            <textarea class="reply-input" id="reply-${index}" placeholder="返信メッセージを入力..." style="width: 100%; padding: 6px; border: 1px solid #dee2e6; border-radius: 4px; font-size: 0.8rem; resize: vertical; min-height: 50px; max-height: 100px;"></textarea>
                            <div style="display: flex; gap: 6px; margin-top: 6px;">
                                <button class="reply-btn" onclick="sendReplyFromQueue('${item.session_id}', ${index}, event)" style="flex: 1; padding: 6px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                                    <i class="fa-solid fa-paper-plane"></i> 送信
                                </button>
                                <button class="btn btn-info" onclick="selectSession(event, '${item.session_id}', ${index}); event.stopPropagation();" style="flex: 1; padding: 6px; background: #17a2b8; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                                    <i class="fa-solid fa-comments"></i> 移動
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    // 現在のセッション情報があれば最初に追加
    if (currentSessionHtml) {
        content.innerHTML = currentSessionHtml + html;
    } else {
        content.innerHTML = html;
    }
    
    // 危機対応セッションの数をカウントして表示
    const crisisCount = queue.filter(item => item.status === 'crisis_detected' || item.priority === 'high').length;
    const crisisCountElement = document.getElementById('crisis-count');
    if (crisisCountElement) {
        if (crisisCount > 0) {
            crisisCountElement.textContent = `🚨 緊急: ${crisisCount}件`;
            crisisCountElement.style.background = '#ffebee';
            crisisCountElement.style.color = '#e74c3c';
        } else {
            crisisCountElement.textContent = '';
        }
    }
}

// キューアコーディオンの開閉
function toggleQueueAccordion(accordionId, contentId) {
    const content = document.getElementById(contentId);
    const icon = document.getElementById(accordionId + '-icon');
    
    if (content.style.maxHeight === '0px' || content.style.maxHeight === '') {
        content.style.maxHeight = content.scrollHeight + 'px';
        if (icon) icon.style.transform = 'rotate(180deg)';
    } else {
        content.style.maxHeight = '0px';
        if (icon) icon.style.transform = 'rotate(0deg)';
    }
}

function updateStats(queue) {
    const queueCount = Array.isArray(queue) ? queue.length : 0;
    const queueCountEl = document.getElementById('queue-count');
    if (queueCountEl) queueCountEl.textContent = queueCount;
    
    // モバイル用統計情報も更新
    if (isMobile()) {
        const mobileQueueCount = document.getElementById('mobile-queue-count');
        if (mobileQueueCount) mobileQueueCount.textContent = queueCount;
    }
    
    // タブレット/デスクトップ用統計情報も更新
    const tabletQueueCount = document.getElementById('tablet-queue-count');
    if (tabletQueueCount) tabletQueueCount.textContent = queueCount;
}

function renderCurrentSession(sessionData) {
    const content = document.getElementById('manual-reply-queue');
    
    if (!content) return;
    
    // セッションデータを保持
    currentSessionData = sessionData;
    
    // 既存のキュー情報を保持（現在のセッション以外）
    const existingQueueItems = Array.from(content.querySelectorAll('.queue-item:not(.current-session)'));
    const existingQueueHtml = existingQueueItems.map(item => item.outerHTML).join('');
    
    // 現在のセッション情報を追加
    if (sessionData && sessionData.messages && sessionData.messages.length > 0) {
        const accordionId = 'current-session-accordion';
        const accordionContentId = 'current-session-accordion-content';
        const lastMessage = sessionData.messages[sessionData.messages.length - 1]?.content || 'なし';
        const shortMessage = lastMessage.length > 30 ? lastMessage.substring(0, 30) + '...' : lastMessage;
        const shortSessionId = sessionData.session_id ? sessionData.session_id.substring(0, 8) + '...' : '不明';
        
        const currentSessionHtml = `
            <div class="queue-item current-session queue-accordion-item">
                <div class="queue-accordion-header" onclick="toggleQueueAccordion('${accordionId}', '${accordionContentId}')">
                    <div style="flex: 1; min-width: 0;">
                        <span class="session-id" style="font-size: 0.8rem; font-weight: 600; color: #28a745; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px;">
                            📱 ${shortSessionId} <span style="background: #28a745; color: white; padding: 1px 4px; border-radius: 8px; font-size: 0.65rem; font-weight: 600; margin-left: 4px;">アクティブ</span>
                        </span>
                        <div style="font-size: 0.75rem; color: #666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${shortMessage}</div>
                    </div>
                    <i class="fa-solid fa-chevron-down queue-accordion-icon" id="${accordionId}-icon" style="flex-shrink: 0; margin-left: 4px;"></i>
                </div>
                <div class="queue-accordion-content" id="${accordionContentId}" style="max-height: 0; overflow: hidden; transition: max-height 0.3s ease;">
                    <div style="padding: 4px 8px; background: #f8f9fa; border-top: 1px solid #dee2e6;">
                        <div class="user-message" style="margin-bottom: 6px; font-size: 0.75rem;">
                            <strong>💬 最新:</strong> ${lastMessage.length > 60 ? lastMessage.substring(0, 60) + '...' : lastMessage}
                        </div>
                        <div style="display: flex; flex-wrap: wrap; gap: 8px; font-size: 0.7rem; color: #666;">
                            <span><strong>📊 件数:</strong> ${sessionData.messages_count || sessionData.messages.length || 0}</span>
                            <span><strong>${sessionData.session_active ? '✅' : '❌'}</strong> ${sessionData.session_active ? '有効' : '無効'}</span>
                        </div>
                        <div style="font-size: 0.65rem; color: #999; margin-top: 4px; word-break: break-all;">
                            ID: ${sessionData.session_id || '不明'} | ${sessionData.last_activity || '不明'}
                        </div>
                        <div style="margin-top: 6px;">
                            <button class="btn btn-info" onclick="selectSession(event, '${sessionData.session_id}', 'current'); event.stopPropagation();" style="width: 100%; padding: 6px; background: #17a2b8; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                                <i class="fa-solid fa-comments"></i> チャットに移動
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 現在のセッションを最初に表示し、既存のキュー情報を保持
        content.innerHTML = currentSessionHtml + existingQueueHtml;
    } else {
        // セッションデータがない場合は、既存のキュー情報のみ表示
        if (existingQueueHtml) {
            content.innerHTML = existingQueueHtml;
        }
    }
}

function loadChatHistory(sessionId) {
    // ローディング表示
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.innerHTML = `
        <div class="empty-state">
            <div>🔄</div>
            <p>チャット履歴を読み込み中...</p>
        </div>
    `;
    
    // セッションタイトルを更新
    const session = allSessions.find(s => s.session_id === sessionId);
    if (session) {
        document.getElementById('chat-title').textContent = `${session.username} (${sessionId})`;
        // ユーザー属性ボタンを表示
        const userAttributesBtn = document.getElementById('userAttributesBtn');
        if (userAttributesBtn) {
            userAttributesBtn.style.display = 'flex';
        }
    } else {
        // セッションが見つからない場合はボタンを非表示
        const userAttributesBtn = document.getElementById('userAttributesBtn');
        if (userAttributesBtn) {
            userAttributesBtn.style.display = 'none';
        }
    }
    
    fetch('/api/main_sessions', {
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
        .then(res => res.json())
        .then(data => {
            console.log('All sessions data:', data);
            
            // APIは {sessions: [...]} の形式で返すため、data.sessions にアクセス
            const sessionsArray = data.sessions || (Array.isArray(data) ? data : []);
            
            // 指定されたセッションIDのデータを探す
            const targetSession = sessionsArray.find(session => session.session_id === sessionId) || null;
            
            if (targetSession && targetSession.messages && Array.isArray(targetSession.messages)) {
                // 管理者専用の詳細診断を保持（推奨薬ごとのscore/score_breakdownを含む）
                currentDetailedDiagnosis = targetSession.detailed_diagnosis || null;
                // メッセージも保持（診断情報のフォールバック用）
                currentMessages = targetSession.messages || [];
                renderChatMessages(targetSession.messages);
            } else {
                currentMessages = [];
                renderChatMessages([]);
            }
        })
        .catch(error => {
            console.error('Chat history error:', error);
            showNotification('セッション情報取得エラー', 'error');
            renderChatMessages([]);
        });
}

// ユーザー属性情報モーダルを表示
function showUserAttributesModal() {
    console.log('🔵 showUserAttributesModal called');
    console.log('🔵 currentSessionId:', currentSessionId);
    
    if (!currentSessionId) {
        showNotification('セッションが選択されていません', 'error');
        return;
    }
    
    // 他のモーダルを閉じる
    const allModals = document.querySelectorAll('.admin-modal, .modal');
    allModals.forEach(modal => {
        if (modal.id !== 'userAttributesModal') {
            modal.style.display = 'none';
            modal.classList.remove('show');
        }
    });
    
    // モーダル要素を取得
    let modal = document.getElementById('userAttributesModal');
    
    if (!modal) {
        console.error('❌ userAttributesModal element not found');
        showNotification('モーダルの要素が見つかりません', 'error');
        return;
    }
    
    // モーダルがbodyの直接の子要素でない場合、bodyに移動（親要素のスタイルの影響を避けるため）
    if (modal.parentElement !== document.body) {
        console.log('🔵 Modal is not a direct child of body, moving it...');
        const parent = modal.parentElement;
        console.log('🔵 Current parent:', parent, 'Parent classes:', parent.className);
        console.log('🔵 Parent computed display:', window.getComputedStyle(parent).display);
        console.log('🔵 Parent computed overflow:', window.getComputedStyle(parent).overflow);
        console.log('🔵 Parent computed position:', window.getComputedStyle(parent).position);
        
        // モーダルをbodyに移動
        document.body.appendChild(modal);
        console.log('✅ Modal moved to body');
    }
    
    console.log('✅ Modal element found:', modal);
    console.log('🔵 Modal parent:', modal.parentElement);
    console.log('🔵 Modal classes before:', modal.className);
    console.log('🔵 Modal inline style before:', modal.getAttribute('style'));
    console.log('🔵 Modal computed display before:', window.getComputedStyle(modal).display);
    
    // showクラスを先に追加（CSSの優先順位を利用）
    modal.classList.add('show');
    
    // インラインスタイルを完全に削除してから、確実に表示用のスタイルを設定
    modal.removeAttribute('style');
    
    // setPropertyで!importantを使用して確実に表示（インラインスタイルの優先度を最大化）
    modal.style.setProperty('display', 'flex', 'important');
    modal.style.setProperty('position', 'fixed', 'important');
    modal.style.setProperty('z-index', '1051', 'important');
    modal.style.setProperty('visibility', 'visible', 'important');
    modal.style.setProperty('opacity', '1', 'important');
    modal.style.setProperty('left', '0', 'important');
    modal.style.setProperty('top', '0', 'important');
    modal.style.setProperty('width', '100%', 'important');
    modal.style.setProperty('height', '100%', 'important');
    modal.style.setProperty('background-color', 'rgba(0, 0, 0, 0.5)', 'important');
    modal.style.setProperty('backdrop-filter', 'blur(5px)', 'important');
    modal.style.setProperty('align-items', 'center', 'important');
    modal.style.setProperty('justify-content', 'center', 'important');
    
    // モーダルコンテンツも確認し、スタイルを確実に設定
    const modalContent = modal.querySelector('.admin-modal-content');
    if (modalContent) {
        console.log('✅ Modal content found:', modalContent);
        // モーダルコンテンツのopacityを確実に1に設定
        modalContent.style.setProperty('opacity', '1', 'important');
        modalContent.style.setProperty('visibility', 'visible', 'important');
        modalContent.style.setProperty('display', 'block', 'important');
        console.log('✅ Modal content styles set');
    } else {
        console.warn('⚠️ Modal content not found!');
    }
    
    // 少し待ってから表示状態を確認（レンダリングの完了を待つ）
    setTimeout(() => {
        const computedStyle = window.getComputedStyle(modal);
        console.log('✅ Modal classes after:', modal.className);
        console.log('✅ Modal inline style after:', modal.getAttribute('style'));
        console.log('✅ Modal computed display after:', computedStyle.display);
        console.log('✅ Modal computed visibility:', computedStyle.visibility);
        console.log('✅ Modal computed opacity:', computedStyle.opacity);
        console.log('✅ Modal computed position:', computedStyle.position);
        console.log('✅ Modal computed z-index:', computedStyle.zIndex);
        console.log('✅ Modal computed left:', computedStyle.left);
        console.log('✅ Modal computed top:', computedStyle.top);
        console.log('✅ Modal computed width:', computedStyle.width);
        console.log('✅ Modal computed height:', computedStyle.height);
        console.log('✅ Modal computed background-color:', computedStyle.backgroundColor);
        
        // モーダルコンテンツの状態も確認
        if (modalContent) {
            const contentStyle = window.getComputedStyle(modalContent);
            console.log('✅ Modal content display:', contentStyle.display);
            console.log('✅ Modal content visibility:', contentStyle.visibility);
            console.log('✅ Modal content opacity:', contentStyle.opacity);
            console.log('✅ Modal content width:', contentStyle.width);
            console.log('✅ Modal content height:', contentStyle.height);
        }
        
        // モーダルが実際に表示されているか再確認
        const finalDisplay = computedStyle.display;
        if (finalDisplay !== 'flex' && finalDisplay !== 'block') {
            console.warn('⚠️ Modal is not displayed! Final display:', finalDisplay);
            // フォールバック: より強力な方法で表示
            modal.style.cssText = 'display: flex !important; position: fixed !important; z-index: 1051 !important; visibility: visible !important; opacity: 1 !important; left: 0 !important; top: 0 !important; width: 100% !important; height: 100% !important; background-color: rgba(0, 0, 0, 0.5) !important; backdrop-filter: blur(5px) !important; align-items: center !important; justify-content: center !important;';
        }
        
        // モーダルの位置とサイズを再確認
        const rect = modal.getBoundingClientRect();
        console.log('✅ Modal bounding rect:', {
            top: rect.top,
            left: rect.left,
            width: rect.width,
            height: rect.height,
            visible: rect.width > 0 && rect.height > 0
        });
        
        // モーダルが画面外にある場合の警告と修正
        if (rect.width === 0 || rect.height === 0) {
            console.warn('⚠️ Modal has zero size! Attempting to fix...');
            // モーダルコンテンツのopacityを再度設定
            if (modalContent) {
                modalContent.style.setProperty('opacity', '1', 'important');
                modalContent.style.setProperty('visibility', 'visible', 'important');
            }
            // モーダルのスタイルを再設定
            modal.style.setProperty('display', 'flex', 'important');
            modal.style.setProperty('opacity', '1', 'important');
            modal.style.setProperty('visibility', 'visible', 'important');
        }
        if (rect.top < -1000 || rect.top > window.innerHeight + 1000) {
            console.warn('⚠️ Modal is outside viewport! Top:', rect.top);
        }
    }, 50);
    
    // アニメーション完了後（300ms後）にもう一度確認
    setTimeout(() => {
        if (modalContent) {
            const contentStyle = window.getComputedStyle(modalContent);
            if (parseFloat(contentStyle.opacity) < 1) {
                console.warn('⚠️ Modal content opacity still not 1 after animation, forcing...');
                modalContent.style.setProperty('opacity', '1', 'important');
            }
        }
        const rect = modal.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) {
            console.warn('⚠️ Modal still has zero size after animation! Forcing display...');
            
            // モーダルがbodyの直接の子要素でない場合、確実に移動
            if (modal.parentElement !== document.body) {
                console.log('🔵 Moving modal to body as fallback...');
                document.body.appendChild(modal);
            }
            
            // 強制的にスタイルを設定
            modal.style.cssText = 'display: flex !important; position: fixed !important; z-index: 1051 !important; visibility: visible !important; opacity: 1 !important; left: 0 !important; top: 0 !important; width: 100vw !important; height: 100vh !important; background-color: rgba(0, 0, 0, 0.5) !important; backdrop-filter: blur(5px) !important; align-items: center !important; justify-content: center !important; margin: 0 !important; padding: 0 !important;';
            
            if (modalContent) {
                modalContent.style.cssText = 'opacity: 1 !important; visibility: visible !important; display: block !important; position: relative !important;';
            }
            
            // 再確認
            setTimeout(() => {
                const newRect = modal.getBoundingClientRect();
                console.log('✅ Modal bounding rect after force:', {
                    top: newRect.top,
                    left: newRect.left,
                    width: newRect.width,
                    height: newRect.height,
                    visible: newRect.width > 0 && newRect.height > 0
                });
                if (newRect.width === 0 || newRect.height === 0) {
                    console.error('❌ Modal still has zero size after all fixes!');
                } else {
                    console.log('✅ Modal is now visible!');
                }
            }, 100);
        }
    }, 350);
    
    // コンテンツを読み込む
    loadUserAttributes(currentSessionId);
}

// ユーザー属性情報モーダルを閉じる
function closeUserAttributesModal() {
    console.log('🔴 closeUserAttributesModal called');
    const modal = document.getElementById('userAttributesModal');
    if (modal) {
        console.log('🔴 Modal found, closing...');
        console.log('🔴 Modal classes before close:', modal.className);
        
        // showクラスを削除
        modal.classList.remove('show');
        
        // displayをnoneに設定
        modal.style.display = 'none';
        
        console.log('✅ Modal classes after close:', modal.className);
        console.log('✅ Modal computed display after close:', window.getComputedStyle(modal).display);
        console.log('✅ Modal closed successfully');
    } else {
        console.error('❌ userAttributesModal element not found when closing');
    }
}

// グローバルスコープに明示的に割り当て（onclick属性から呼び出せるように）
window.showUserAttributesModal = showUserAttributesModal;
window.closeUserAttributesModal = closeUserAttributesModal;

// 手動返信メッセージの読み込み
function loadManualReplyMessage() {
    console.log('🔵 loadManualReplyMessage called');
    
    // 保存直後（5秒以内）の場合は更新をスキップ（保存した値が上書きされないように）
    const timeSinceLastSave = Date.now() - (lastMessageSaveTime || 0);
    if (timeSinceLastSave < 5000) {
        console.log('⏭️ Skipping loadManualReplyMessage (recently saved,', Math.round(timeSinceLastSave / 1000), 'seconds ago)');
        return;
    }
    
    fetch('/api/manual_reply_message', {
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
    .then(res => {
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
    })
    .then(data => {
        console.log('✅ Manual reply message loaded:', data);
        const messageField = document.getElementById('manualReplyMessage');
        if (messageField) {
            // 再度確認（保存直後に呼ばれた可能性があるため）
            const timeSinceLastSave2 = Date.now() - (lastMessageSaveTime || 0);
            if (timeSinceLastSave2 < 5000) {
                console.log('⏭️ Skipping message field update (recently saved)');
                return;
            }
            
            if (data.message) {
                messageField.value = data.message;
                console.log('✅ Message field updated:', data.message.substring(0, 50) + '...');
            } else {
                console.warn('⚠️ No message in response');
            }
        } else {
            console.warn('⚠️ Message field not found');
        }
    })
    .catch(error => {
        console.error('❌ メッセージ読み込みエラー:', error);
        showNotification('メッセージの読み込みに失敗しました', 'error');
    });
}

// 手動返信メッセージの保存
// 保存時刻を記録（refreshAIStatusでメッセージフィールドを更新しないようにするため）
let lastMessageSaveTime = 0;

function saveManualReplyMessage() {
    console.log('🔵 saveManualReplyMessage called');
    const messageField = document.getElementById('manualReplyMessage');
    if (!messageField) {
        console.error('❌ Message field not found');
        showNotification('メッセージフィールドが見つかりません', 'error');
        return;
    }
    
    // フィールドの値を取得（先に取得してからtrim）
    const rawValue = messageField.value;
    console.log('🔵 Raw message field value length:', rawValue ? rawValue.length : 0);
    console.log('🔵 Raw message field value:', rawValue ? rawValue.substring(0, 100) + '...' : '(empty)');
    
    const message = rawValue.trim();
    if (!message) {
        showNotification('メッセージを入力してください', 'error');
        return;
    }
    
    console.log('🔵 Saving message (trimmed length:', message.length, '):', message.substring(0, 100) + (message.length > 100 ? '...' : ''));
    lastMessageSaveTime = Date.now(); // 保存時刻を記録
    
    fetch('/api/manual_reply_message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message })
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(data => {
                throw new Error(data.error || `HTTP error! status: ${res.status}`);
            });
        }
        return res.json();
    })
    .then(data => {
        console.log('✅ Message saved:', data);
        if (data.error) {
            showNotification(`エラー: ${data.error}`, 'error');
        } else {
            showNotification(data.message || 'メッセージを保存しました', 'success');
            // 保存した値を直接フィールドに設定（サーバーから返された値を使用）
            const messageField = document.getElementById('manualReplyMessage');
            if (messageField) {
                // サーバーから返された値を使用（優先）
                if (data.manual_reply_message) {
                    messageField.value = data.manual_reply_message;
                    console.log('✅ Message field updated directly from saved value:', data.manual_reply_message.substring(0, 50) + '...');
                } else if (message) {
                    // フォールバック: 保存したメッセージを使用
                    messageField.value = message;
                    console.log('✅ Message field updated from local value:', message.substring(0, 50) + '...');
                }
                // 保存直後の自動再読み込みは行わない（保存した値が正しく反映されているため）
            }
        }
    })
    .catch(error => {
        console.error('❌ Save error:', error);
        showNotification(`エラー: ${error.message}`, 'error');
    });
}

// 手動返信メッセージのリセット
function resetManualReplyMessage() {
    const messageField = document.getElementById('manualReplyMessage');
    if (!messageField) {
        return;
    }
    
    const defaultMessage = '申し訳ございません。現在、AI自動応答が一時停止されています。担当者が確認次第、回答いたします。';
    messageField.value = defaultMessage;
}

// グローバルスコープに割り当て
window.saveManualReplyMessage = saveManualReplyMessage;
window.resetManualReplyMessage = resetManualReplyMessage;
window.loadManualReplyMessage = loadManualReplyMessage;

// ユーザー属性情報を読み込み
function loadUserAttributes(sessionId) {
    const content = document.getElementById('userAttributesContent');
    content.innerHTML = `
        <div class="loading-state">
            <i class="fa-solid fa-spinner fa-spin"></i>
            <p>読み込み中...</p>
        </div>
    `;
    
    // デバッグ情報を出力
    console.log('loadUserAttributes called with sessionId:', sessionId);
    console.log('allSessions:', allSessions);
    
    // セッション情報からユーザー属性を取得
    const session = allSessions.find(s => s.session_id === sessionId);
    console.log('Found session:', session);
    
    if (session) {
        // すべての属性情報を取得（user_info、attributes、user_attributesなど）
        const userInfo = session.user_info || {};
        const attributes = session.attributes || {};
        const userAttributes = session.user_attributes || {};
        
        // すべての属性情報をマージ（後から来たものが優先）
        const allAttributes = { ...userInfo, ...attributes, ...userAttributes };
        
        // セッションオブジェクト全体から属性情報を抽出（既知のフィールド以外）
        const knownFields = ['session_id', 'username', 'messages', 'last_activity', 'message_count', 
                            'user_info', 'attributes', 'user_attributes', 'detailed_diagnosis'];
        const additionalFields = {};
        for (const key in session) {
            if (!knownFields.includes(key) && typeof session[key] !== 'object' && typeof session[key] !== 'function') {
                additionalFields[key] = session[key];
            }
        }
        
        console.log('userInfo:', userInfo);
        console.log('attributes:', attributes);
        console.log('userAttributes:', userAttributes);
        console.log('allAttributes:', allAttributes);
        console.log('additionalFields:', additionalFields);
        
        let html = `
            <div class="user-info-section">
                <div class="user-info-header">
                    <div class="user-avatar">
                        <i class="fa-solid fa-user"></i>
                    </div>
                    <div class="user-info-text">
                        <h4>${escapeHtml(session.username || '不明')}</h4>
                        <p>セッションID: ${sessionId.substring(0, 20)}...</p>
                    </div>
                </div>
            </div>
        `;
        
        // 属性情報の表示用関数
        function formatAttributeValue(value) {
            if (value === null || value === undefined) {
                return '未設定';
            }
            if (Array.isArray(value)) {
                return value.length > 0 ? value.join(', ') : 'なし';
            }
            if (typeof value === 'boolean') {
                return value ? 'はい' : 'いいえ';
            }
            if (typeof value === 'object') {
                return JSON.stringify(value, null, 2);
            }
            return String(value);
        }
        
        function getAttributeLabel(key) {
            const labels = {
                'age': '🎂 年齢',
                'gender': '⚥ 性別',
                'pregnant': '🤱 妊娠状態',
                'breastfeeding': '🍼 授乳状態',
                'allergies': '⚠️ アレルギー',
                'current_medications': '💊 現在服用中の薬',
                'symptom_duration_days': '⏰ 症状の持続期間',
                'medical_history': '🏥 既往症',
                'other_info': '📝 その他伝えたいこと'
            };
            return labels[key] || `📋 ${key}`;
        }
        
        // 属性情報を表示
        // current_medicationsは空の場合でも表示するため、フィルタリングから除外
        const attributeKeys = Object.keys(allAttributes).filter(key => {
            // current_medicationsは常に表示する
            if (key === 'current_medications') {
                return true;
            }
            const value = allAttributes[key];
            return value !== null && value !== undefined && value !== '' && 
                   !(Array.isArray(value) && value.length === 0);
        });
        
        if (attributeKeys.length > 0 || Object.keys(additionalFields).length > 0) {
            html += `
                <div class="attributes-section">
                    <h4 class="attributes-section-title">
                        <i class="fa-solid fa-user-circle"></i>
                        <span>ユーザー属性情報</span>
                    </h4>
                    <div class="attributes-grid">
            `;
            
            // 既知の属性を優先的に表示（特別なフォーマット）
            const priorityFields = ['age', 'gender', 'pregnant', 'breastfeeding', 'allergies', 
                                   'current_medications', 'symptom_duration_days', 'medical_history', 'other_info'];
            
            priorityFields.forEach(key => {
                // current_medicationsは空の場合でも「なし」と表示する
                if (key === 'current_medications') {
                    let displayValue = 'なし';
                    if (allAttributes[key] !== null && allAttributes[key] !== undefined) {
                        const medications = allAttributes[key];
                        if (Array.isArray(medications) && medications.length > 0) {
                            displayValue = medications.join('、');
                        } else if (typeof medications === 'string' && medications.trim()) {
                            displayValue = medications;
                        }
                    }
                    html += `
                        <div class="attribute-card">
                            <div class="attribute-label">${escapeHtml(getAttributeLabel(key))}</div>
                            <div class="attribute-value">${escapeHtml(displayValue)}</div>
                        </div>
                    `;
                    return; // 次のフィールドへ
                }
                
                if (allAttributes[key] !== null && allAttributes[key] !== undefined) {
                    let displayValue = formatAttributeValue(allAttributes[key]);
                    
                    // 特別なフォーマット処理
                    if (key === 'age') {
                        displayValue = `${allAttributes[key]}歳`;
                    } else if (key === 'pregnant') {
                        displayValue = allAttributes[key] ? '妊娠中' : '妊娠していない';
                    } else if (key === 'breastfeeding') {
                        displayValue = allAttributes[key] ? '授乳中' : '授乳していない';
                    } else if (key === 'symptom_duration_days') {
                        const days = allAttributes[key];
                        const today = new Date();
                        const startDate = new Date(today.getTime() - (days * 24 * 60 * 60 * 1000));
                        const dateStr = startDate.getFullYear() + '/' + 
                                      String(startDate.getMonth() + 1).padStart(2, '0') + '/' + 
                                      String(startDate.getDate()).padStart(2, '0');
                        
                        let durationText = '';
                        if (days === 0) {
                            durationText = '今日から';
                        } else if (days === 1) {
                            durationText = '昨日から';
                        } else if (days < 7) {
                            durationText = `${days}日前から`;
                        } else if (days < 30) {
                            const weeks = Math.floor(days / 7);
                            durationText = `${weeks}週間前から`;
                        } else {
                            const months = Math.floor(days / 30);
                            durationText = `${months}ヶ月前から`;
                        }
                        displayValue = `${durationText} (${dateStr})`;
                    }
                    
                    html += `
                        <div class="attribute-card">
                            <div class="attribute-label">${escapeHtml(getAttributeLabel(key))}</div>
                            <div class="attribute-value">${escapeHtml(displayValue)}</div>
                        </div>
                    `;
                }
            });
            
            // その他の属性情報を表示
            attributeKeys.filter(key => !priorityFields.includes(key)).forEach(key => {
                const displayValue = formatAttributeValue(allAttributes[key]);
                html += `
                    <div class="attribute-card">
                        <div class="attribute-label">${escapeHtml(getAttributeLabel(key))}</div>
                        <div class="attribute-value">${escapeHtml(displayValue)}</div>
                    </div>
                `;
            });
            
            // 追加フィールドを表示
            Object.keys(additionalFields).forEach(key => {
                const displayValue = formatAttributeValue(additionalFields[key]);
                html += `
                    <div class="attribute-card">
                        <div class="attribute-label">📋 ${escapeHtml(key)}</div>
                        <div class="attribute-value">${escapeHtml(displayValue)}</div>
                    </div>
                `;
            });
            
            html += `</div></div>`;
        } else {
            html += `
                <div class="attributes-section">
                    <h4 class="attributes-section-title">
                        <i class="fa-solid fa-user-circle"></i>
                        <span>ユーザー属性</span>
                    </h4>
                    <div class="empty-state-section">
                        <i class="fa-regular fa-file-lines"></i>
                        <p>ユーザー属性情報はまだ入力されていません</p>
                    </div>
                </div>
            `;
        }
        
        content.innerHTML = html;
    } else {
        content.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #e74c3c; background: white;">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 3em; margin-bottom: 15px; color: #e74c3c; background: white;"></i>
                <p style="font-size: 1.1em; background: white;">セッション情報が見つかりません</p>
            </div>
        `;
    }
}

// 正規化後のスコアを計算する関数（グローバル）
// medicine.scoreは既に正規化後のスコア、raw_scoreが存在する場合はそれから計算
function calculateNormalizedScore(medicine) {
        // normalization_infoが存在する場合は、既に正規化済みのスコアを使用
        const normalizationInfo = medicine.normalization_info || (medicine.scores || medicine.score_breakdown || {}).normalization_info;
        if (normalizationInfo && medicine.score !== undefined && medicine.score !== null) {
            return Math.max(0.0, Math.min(1.0, parseFloat(medicine.score) || 0.0));
        }
        
        // raw_scoreが存在する場合は、それから正規化計算を行う
        if (medicine.raw_score !== undefined && medicine.raw_score !== null) {
            const rawScore = parseFloat(medicine.raw_score) || 0.0;
            if (rawScore <= 0.5) {
                return 0.0;
            } else if (normalizationInfo && normalizationInfo.score_range > 0) {
                // Min-Max正規化: (raw_score - min) / (max - min)
                const minMaxNormalized = (rawScore - normalizationInfo.min_raw_score) / normalizationInfo.score_range;
                return Math.min(1.0, Math.sqrt(minMaxNormalized));
            } else {
                // フォールバック: 旧方式
                const normalizedRange = (rawScore - 0.5) / 0.5;
                const sqrtResult = Math.sqrt(normalizedRange);
                return Math.min(1.0, sqrtResult);
            }
        } else {
            // raw_scoreが存在しない場合は、medicine.scoreが既に正規化後のスコアとして使用
            return Math.max(0.0, Math.min(1.0, parseFloat(medicine.score) || 0.0));
        }
}

// HTMLコンテンツにスコアリングを追加（管理者画面用）
function addScoringToHtmlContent(htmlContent, medicines) {
    if (!medicines || medicines.length === 0) {
        return htmlContent;
    }
    
    let modifiedContent = htmlContent;
    
    // 各医薬品のスコアリングを追加（推奨医薬品セクションのみ）
    medicines.forEach((medicine, index) => {
        if (medicine.score !== undefined && medicine.score !== null) {
            // 正規化後のスコアを計算
            const normalizedScore = calculateNormalizedScore(medicine);
            const scoreClass = normalizedScore >= 0.7 ? 'admin-score-high' : normalizedScore >= 0.5 ? 'admin-score-medium' : 'admin-score-low';
            const scoreText = normalizedScore >= 0.7 ? '高' : normalizedScore >= 0.5 ? '中' : '低';
            const scoringHtml = `<span class="admin-score-display ${scoreClass}" style="font-size: 0.75em;">📊 最適度: ${(normalizedScore * 100).toFixed(0)}% (${scoreText})</span>`;
            
            // 推奨医薬品セクション内の医薬品名の後にスコアリングを追加
            const medicineName = medicine.product_name || '';
            if (medicineName) {
                // 該当行に既に最適度が付いていない場合のみ追加（同一行内で判定）
                const namePattern = new RegExp(`(🏆 ${index + 1}位:\\s*${medicineName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})(?![^\\n]*最適度:)`, 'g');
                modifiedContent = modifiedContent.replace(namePattern, `$1${scoringHtml}`);
            }
        }
    });
    
    return modifiedContent;
}

// ★★★ addScoringToMedicines 関数は削除（動的HTML生成に変更） ★★★

function renderChatMessages(messages) {
    const chatMessages = document.getElementById('chat-messages');
    
    if (!messages || messages.length === 0) {
        chatMessages.innerHTML = `
            <div class="empty-state">
                <div>💬</div>
                <p>メッセージ履歴がありません</p>
            </div>
        `;
        return;
    }
    
    console.log('📨 Rendering chat messages:', messages.length, 'messages');
    
    let html = '';
    messages.forEach((msg, index) => {
        const messageClass = msg.type === 'user' ? 'user' : 'bot';
        let indicator = '';
        let timestamp = '';
        
        console.log(`Message ${index}:`, msg);
        
        // 送信時刻を追加
        if (msg.timestamp) {
            const date = new Date(msg.timestamp);
            const timeStr = date.toLocaleTimeString('ja-JP', { 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            });
            timestamp = `<div class="message-timestamp" style="font-size: 0.7em; color: #666; margin-top: 4px; text-align: ${messageClass === 'user' ? 'left' : 'right'};">${timeStr}</div>`;
        } else {
            // タイムスタンプがない場合は現在時刻を使用
            const now = new Date();
            const timeStr = now.toLocaleTimeString('ja-JP', { 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            });
            timestamp = `<div class="message-timestamp" style="font-size: 0.7em; color: #666; margin-top: 4px; text-align: ${messageClass === 'user' ? 'left' : 'right'};">${timeStr}</div>`;
        }
        
        // 管理画面用のインジケーター：薬剤師視点で表示
        if (msg.type === 'bot') {
        if (msg.crisis_support) {
            indicator = '<span class="crisis-indicator" style="color: #e74c3c; font-weight: bold; background: #ffebee; padding: 2px 6px; border-radius: 4px;">🚨 危機対応</span><br>';
            } else if (msg.manual_reply) {
                indicator = '<span class="manual-reply-indicator">👤 薬剤師返信</span><br>';
            } else {
                indicator = '<span class="ai-indicator">🤖 AI返信</span><br>';
            }
        } else if (msg.type === 'user') {
            indicator = '<span class="user-indicator" style="color: #007bff; font-weight: bold;">👤 ユーザー</span><br>';
        }
        
        let messageContentHtml = '';

        // 危機対応メッセージの特別表示
        if (msg.crisis_support) {
            messageContentHtml += `<div class="crisis-message-highlight">`;
            messageContentHtml += `<h4 style="color: #e74c3c; margin-bottom: 10px;">🚨 危機対応メッセージ</h4>`;
            messageContentHtml += `<p><strong>タイトル:</strong> ${msg.crisis_title || 'あなたの気持ちを大切に思っています'}</p>`;
            messageContentHtml += `<p><strong>メッセージ:</strong> ${msg.content || '今、とてもつらい状況かもしれません。'}</p>`;
            
            if (msg.resources && msg.resources.length > 0) {
                messageContentHtml += `<h5 style="color: #e74c3c; margin-top: 15px;">相談先情報:</h5>`;
                msg.resources.forEach(resource => {
                    messageContentHtml += `<div style="background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #e74c3c;">`;
                    messageContentHtml += `<strong>${resource.name}</strong><br>`;
                    messageContentHtml += `<small>${resource.organization}</small><br>`;
                    if (resource.phone) messageContentHtml += `📞 ${resource.phone}<br>`;
                    if (resource.line) messageContentHtml += `💬 <a href="${resource.line}" target="_blank">LINEで相談する</a><br>`;
                    if (resource.line_qr) messageContentHtml += `📱 <img src="${resource.line_qr}" alt="LINE QRコード" style="width: 80px; height: 80px; border: 1px solid #ddd; border-radius: 4px; margin: 5px 0;"><br>`;
                    if (resource.website) messageContentHtml += `🌐 <a href="${resource.website}" target="_blank">ウェブサイト</a><br>`;
                    if (resource.hours) messageContentHtml += `⏰ ${resource.hours}<br>`;
                    messageContentHtml += `<small>${resource.description}</small>`;
                    messageContentHtml += `</div>`;
                });
            }
            
            if (msg.emergency_message) {
                messageContentHtml += `<div style="background: #e74c3c; color: white; padding: 10px; margin-top: 10px; border-radius: 4px; text-align: center; font-weight: bold;">`;
                messageContentHtml += `${msg.emergency_message}`;
                messageContentHtml += `</div>`;
            }
            
            messageContentHtml += `</div>`;
        }
        // ★★★ 推奨医薬品メッセージの判定（簡素化） ★★★
        const isMedicineRecommendation = (msg) => {
            // デバッグログ
            console.log('🔍 Message analysis:', {
                type: msg.type,
                hasDiagnosis: !!(msg.diagnosis && msg.diagnosis.recommended_medicines),
                hasContent: !!(msg.content && msg.content.includes('推奨医薬品')),
                hasContentHtml: !!(msg.content && msg.content.includes('<div class="recommendation-result">')),
                hasTrophy: !!(msg.content && msg.content.includes('🏆'))
            });
            
            return msg.type === 'bot' && (
                (msg.diagnosis && msg.diagnosis.recommended_medicines) ||
                (msg.content && (
                    msg.content.includes('推奨医薬品') ||
                    msg.content.includes('<div class="recommendation-result">') ||
                    msg.content.includes('🏆')
                ))
            );
        };

        if (isMedicineRecommendation(msg)) {
            // 詳細診断（管理者向け）を優先
            const adminDiag = (currentDetailedDiagnosis && currentDetailedDiagnosis.session_id === currentSessionId && Array.isArray(currentDetailedDiagnosis.recommended_medicines))
                ? currentDetailedDiagnosis
                : (msg.diagnosis || {});
            // 管理者用に再描画できる推奨医薬品が存在するか
            const hasAdminDiagMeds = !!(adminDiag && Array.isArray(adminDiag.recommended_medicines) && adminDiag.recommended_medicines.length > 0);

            messageContentHtml += `<div class="recommendation-result">`;
            messageContentHtml += `<h4 style="color: #1976d2; border-bottom: 2px solid #1976d2; padding-bottom: 8px;">🔍 症状分析結果</h4>`;
            
            if (adminDiag.symptoms && adminDiag.symptoms.length > 0) {
                messageContentHtml += `<p><strong>推測される症状:</strong> ${adminDiag.symptoms.join(', ')}</p>`;
            }
            if (adminDiag.medicine_type) {
                messageContentHtml += `<p><strong>医薬品の種類:</strong> ${adminDiag.medicine_type}</p>`;
            }

            messageContentHtml += `<div style="background: #e8f5e9; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #4caf50;">`;
            messageContentHtml += `<h4 style="color: #2e7d32; margin-top: 0;">💊 推奨医薬品</h4>`;

            if (adminDiag.recommended_medicines && adminDiag.recommended_medicines.length > 0) {
                adminDiag.recommended_medicines.forEach((medicine, medIndex) => {
                    messageContentHtml += `<div class="medicine-item" style="padding: 10px 0; margin: 10px 0; border-bottom: 1px solid #ddd;">`;
                    messageContentHtml += `<h5 style="margin: 0 0 10px 0;">🏆 ${medIndex + 1}位: ${escapeHtml(medicine.product_name || medicine.name || 'N/A')}`;

                    // --- 詳細スコアボタンを追加 ---
                    if (medicine.score !== undefined) {
                        const medicineId = `medicine_${medIndex + 1}`;
                        messageContentHtml += `<button class="score-detail-btn" onclick="showScoreModal('${medicineId}', ${medIndex})" style="margin-left: 10px; padding: 4px 8px; font-size: 0.7em; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background-color 0.3s;">📊 詳細スコア</button>`;
                    }

                    messageContentHtml += `<span style="color: #666; font-size: 0.9em;"> (${escapeHtml(medicine.manufacturer || '')})</span></h5>`;

                    // --- スコアリングラベルとツールチップ（簡略表示） ---
                    if (medicine.score !== undefined && medicine.score !== null) {
                        // 正規化後のスコアを計算
                        const normalizedScore = calculateNormalizedScore(medicine);
                        const scoreClass = normalizedScore >= 0.7 ? 'admin-score-high' : normalizedScore >= 0.5 ? 'admin-score-medium' : 'admin-score-low';
                        const scoreText = normalizedScore >= 0.7 ? '高' : normalizedScore >= 0.5 ? '中' : '低';
                        const breakdown = medicine.scores || medicine.score_breakdown || {};

                        // スコア計算ヘルパー
                        const pct = (v) => {
                            if (v === undefined || v === null || isNaN(v)) return 0;
                            return Math.max(0, Math.min(100, Math.round(v * 100)));
                        };
                        const riskToPct = (v) => {
                            if (v === undefined || v === null || isNaN(v)) return 100;
                            return Math.max(0, Math.min(100, Math.round((1 + v) * 100)));
                        };

                        // 各スコア抽出
                        const symptom = breakdown.symptom_match ?? breakdown.symptom_match_score ?? 0;
                        const efficacy = breakdown.efficacy_specificity ?? breakdown.efficacy_specificity_score ?? 0;
                        const age = breakdown.age_fit ?? breakdown.age_suitability_score ?? 0;
                        const usage = breakdown.usage_convenience ?? breakdown.dosage_convenience_score ?? 0;
                        const sideRisk = breakdown.side_effect_risk ?? breakdown.side_effect_risk_score ?? 0;
                        const interRisk = breakdown.interaction_risk ?? breakdown.interaction_risk_score ?? 0;

                        messageContentHtml += `<span class="admin-score-display ${scoreClass}" style="font-size: 0.75em;">📊 最適度: ${(normalizedScore * 100).toFixed(0)}% (${scoreText})</span>`;
                    }

                    messageContentHtml += `<span style="color: #666; font-size: 0.9em;"> (${escapeHtml(medicine.manufacturer || '')})</span></h5>`;
                    
                    if (medicine.explanation || medicine.reason) {
                        messageContentHtml += `<p style="margin: 5px 0;"><strong>推奨理由:</strong> ${escapeHtml(medicine.explanation || medicine.reason)}</p>`;
                    }
                    if (medicine.age_restriction) {
                        messageContentHtml += `<p style="margin: 5px 0;"><strong>年齢制限:</strong> ${escapeHtml(medicine.age_restriction)}</p>`;
                    }
                    if (medicine.efficacy) {
                        messageContentHtml += `<p style="margin: 5px 0;"><strong>効能効果:</strong> ${escapeHtml(medicine.efficacy.substring(0,100))}...</p>`;
                    }
                    messageContentHtml += `</div>`;
                });
            } else {
                messageContentHtml += "<p>適切な医薬品が見つかりませんでした。</p>";
            }
            messageContentHtml += `</div>`;

            // 使用上の注意、医師相談など
            if (adminDiag.usage_notes) {
                messageContentHtml += `<div style="background: #fff3e0; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ff9800;">
                    <h4 style="color: #e65100; margin-top: 0;">⚠️ 使用上の注意</h4>
                    <div class="caution-content" style="white-space: pre-wrap;">${escapeHtml(adminDiag.usage_notes)}</div>
                </div>`;
            }
            if (adminDiag.doctor_consultation) {
                messageContentHtml += `<div style="background: #ffebee; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #f44336;">
                    <h4 style="color: #c62828; margin-top: 0;">🏥 医師の受診が必要な場合</h4>
                    <div class="advice-content" style="white-space: pre-wrap;">${escapeHtml(adminDiag.doctor_consultation)}</div>
                </div>`;
            }
            if (adminDiag.additional_questions && adminDiag.additional_questions.length > 0) {
                messageContentHtml += `<div style="background: #e8f5e9; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #4caf50;">
                    <h4 style="color: #388e3c; margin-top: 0;">❓ 追加でお伺いしたいこと</h4>
                    <ul>${adminDiag.additional_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}</ul>
                </div>`;
            }

            messageContentHtml += `</div>`;

            // msg.contentにHTMLが含まれている場合は、ボタンを追加してから表示
            // ただし、管理者用の再描画（hasAdminDiagMeds）が可能な場合は上書きしない
            if (!hasAdminDiagMeds && msg.content && msg.content.includes('<div class="recommendation-result">')) {
                let modifiedContent = msg.content;
                
                // 詳細診断（管理者向け）を優先
                const adminDiag = (currentDetailedDiagnosis && currentDetailedDiagnosis.session_id === currentSessionId && Array.isArray(currentDetailedDiagnosis.recommended_medicines))
                    ? currentDetailedDiagnosis
                    : (msg.diagnosis || {});
                
                if (adminDiag && adminDiag.recommended_medicines) {
                    // 各医薬品のスコアリングを追加
                    adminDiag.recommended_medicines.forEach((medicine, index) => {
                        if (medicine.score !== undefined) {
                            // 詳細スコアボタンを追加
                            const medicineId = `medicine_${index + 1}`;
                            const scoreButton = `<button class="score-detail-btn" onclick="showScoreModal('${medicineId}', ${index})" style="margin-left: 10px; padding: 4px 8px; font-size: 0.7em; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background-color 0.3s;">📊 詳細スコア</button>`;
                            
                            // 推奨医薬品セクション内の医薬品名の後にボタンを追加
                            const medicineName = medicine.product_name || medicine.name || '';
                            if (medicineName) {
                                // 該当行に既にボタンが付いていない場合のみ追加（同一行内で判定）
                                const namePattern = new RegExp(`(🏆 ${index + 1}位:\\s*${medicineName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})(?![^\\n]*詳細スコア)`, 'g');
                                modifiedContent = modifiedContent.replace(namePattern, `$1${scoreButton}`);
                            }
                        }
                    });
                }
                
                // 挿入が成功した場合のみ置き換え（少なくとも1つのボタンが入っているか）
                if (modifiedContent.includes('score-detail-btn')) {
                    messageContentHtml = modifiedContent;
                }
            } else if (!hasAdminDiagMeds) {
                // 管理者用の再描画ができない場合のみ、msg.contentをそのまま使用
                messageContentHtml = msg.content || '';
            }

        // ★★★ 通常のテキストメッセージ ★★★
        } else {
            let contentText = msg.content || '';
            if (msg.type === 'user') {
                messageContentHtml = escapeHtml(contentText);
            } else if (msg.type === 'bot') {
                if (contentText.includes('<div class="chat-response">')) {
                    messageContentHtml = contentText;
                } else {
                    messageContentHtml = escapeHtml(contentText);
                }
            } else {
                messageContentHtml = escapeHtml(contentText);
            }
        }
        
        // メッセージ全体のHTML生成
        html += `
            <div class="message ${messageClass}" style="margin-bottom: 20px; display: flex; ${messageClass === 'user' ? 'justify-content: flex-start;' : 'justify-content: flex-end;'}">
                <div class="message-content" style="max-width: 80%; padding: 12px 16px; border-radius: 18px; word-wrap: break-word; line-height: 1.4; ${
                    messageClass === 'user'
                        ? 'background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; border-bottom-left-radius: 4px; box-shadow: 0 2px 8px rgba(0, 123, 255, 0.3);'
                        : 'background: white; color: #333; border: 1px solid #ddd; text-align: left;'
                }">
                    ${indicator}
                    <div class="message-text">${messageContentHtml}</div>
                    ${timestamp}
                </div>
            </div>
        `;
    });
    
    chatMessages.innerHTML = html;
    console.log('✅ Chat messages rendered');
    
    // スクロールを最下部に
    setTimeout(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 100);
}

// HTMLエスケープ関数（既に上部で定義済み）
// function escapeHtml(text) {
//     const div = document.createElement('div');
//     div.textContent = text;
//     return div.innerHTML;
// }

// 重複したsetAIMode関数は削除（425行目の実装を使用）

// システム状況取得
function loadMonitoringData() {
    // アクセス統計の読み込み
    fetch('/admin/access_stats')
    .then(response => response.json())
    .then(data => {
        const accessStats = document.getElementById('accessStats');
        accessStats.innerHTML = `
            <p style="color: #333333;"><strong>総アクセス数:</strong> ${data.total_accesses || 0}</p>
            <p style="color: #333333;"><strong>平均レスポンス時間:</strong> ${(data.avg_response_time || 0).toFixed(2)}ms</p>
            <p style="color: #333333;"><strong>最終更新:</strong> ${new Date().toLocaleString('ja-JP')}</p>
        `;
    })
    .catch(error => {
        document.getElementById('accessStats').innerHTML = '<p style="color: red;">エラー: データの読み込みに失敗しました</p>';
    });

    // パフォーマンス統計の読み込み
    fetch('/admin/performance_stats')
    .then(response => response.json())
    .then(data => {
        const performanceStats = document.getElementById('performanceStats');
        performanceStats.innerHTML = `
            <p style="color: #333333;"><strong>総リクエスト数:</strong> ${data.total_requests || 0}</p>
            <p style="color: #333333;"><strong>平均レスポンス時間:</strong> ${(data.avg_response_time || 0).toFixed(2)}ms</p>
            <p style="color: #333333;"><strong>平均メモリ使用率:</strong> ${(data.avg_memory_usage || 0).toFixed(1)}%</p>
            <p style="color: #333333;"><strong>平均CPU使用率:</strong> ${(data.avg_cpu_usage || 0).toFixed(1)}%</p>
            <p style="color: #333333;"><strong>キャッシュヒット率:</strong> ${(data.avg_cache_hit_rate || 0).toFixed(1)}%</p>
            <p style="color: #333333;"><strong>エラー率:</strong> ${(data.error_rate || 0).toFixed(1)}%</p>
        `;
    })
    .catch(error => {
        document.getElementById('performanceStats').innerHTML = '<p style="color: red;">エラー: データの読み込みに失敗しました</p>';
    });

    // ブラウザ分布の読み込み
    fetch('/admin/browser_distribution')
    .then(response => response.json())
    .then(data => {
        const browserDistribution = document.getElementById('browserDistribution');
        let html = '';
        for (const [browser, stats] of Object.entries(data)) {
            html += `<p style="color: #333333;"><strong>${browser}:</strong> ${stats.count}件 (${stats.percentage.toFixed(1)}%)</p>`;
        }
        browserDistribution.innerHTML = html || '<p style="color: #333333;">データがありません</p>';
    })
    .catch(error => {
        document.getElementById('browserDistribution').innerHTML = '<p style="color: red;">エラー: データの読み込みに失敗しました</p>';
    });

    // OS分布の読み込み
    fetch('/admin/os_distribution')
    .then(response => response.json())
    .then(data => {
        const osDistribution = document.getElementById('osDistribution');
        let html = '';
        for (const [os, stats] of Object.entries(data)) {
            html += `<p style="color: #333333;"><strong>${os}:</strong> ${stats.count}件 (${stats.percentage.toFixed(1)}%)</p>`;
        }
        osDistribution.innerHTML = html || '<p style="color: #333333;">データがありません</p>';
    })
    .catch(error => {
        document.getElementById('osDistribution').innerHTML = '<p style="color: red;">エラー: データの読み込みに失敗しました</p>';
    });

    // デバイス分布の読み込み
    fetch('/admin/device_distribution')
    .then(response => response.json())
    .then(data => {
        const deviceDistribution = document.getElementById('deviceDistribution');
        let html = '';
        for (const [device, stats] of Object.entries(data)) {
            html += `<p style="color: #333333;"><strong>${device}:</strong> ${stats.count}件 (${stats.percentage.toFixed(1)}%)</p>`;
        }
        deviceDistribution.innerHTML = html || '<p style="color: #333333;">データがありません</p>';
    })
    .catch(error => {
        document.getElementById('deviceDistribution').innerHTML = '<p style="color: red;">エラー: データの読み込みに失敗しました</p>';
    });

    // リアルタイム監視の読み込み
    fetch('/admin/realtime_monitoring')
    .then(response => response.json())
    .then(data => {
        const realtimeMonitoring = document.getElementById('realtimeMonitoring');
        realtimeMonitoring.innerHTML = `
            <p style="color: #333333;"><strong>現在のメモリ使用率:</strong> ${data.memory_usage_percent || 0}%</p>
            <p style="color: #333333;"><strong>現在のCPU使用率:</strong> ${data.cpu_usage_percent || 0}%</p>
            <p style="color: #333333;"><strong>現在のレスポンス時間:</strong> ${data.response_time_ms || 0}ms</p>
            <p style="color: #333333;"><strong>アクティブセッション:</strong> ${data.active_sessions || 0}</p>
            <p style="color: #333333;"><strong>API呼び出し回数:</strong> ${data.api_calls || 0}</p>
            <p style="color: #333333;"><strong>キャッシュヒット率:</strong> ${(data.cache_hit_rate || 0).toFixed(1)}%</p>
        `;
    })
    .catch(error => {
        document.getElementById('realtimeMonitoring').innerHTML = '<p style="color: red;">エラー: データの読み込みに失敗しました</p>';
    });
}

function refreshMonitoringData() {
    loadMonitoringData();
}

function exportMonitoringData() {
    // 監視データのエクスポート機能
    fetch('/admin/export_monitoring_data')
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `monitoring_data_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    })
    .catch(error => {
        alert('エクスポートに失敗しました: ' + error.message);
    });
}

function loadSystemStatus() {
    fetch('/admin/system_status')
    .then(response => response.json())
    .then(data => {
        const content = document.getElementById('systemStatusContent');
        const csvStatus = data.csv_load_status || {};
        const perfStats = data.performance_stats || {};
        
        content.innerHTML = `
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #dee2e6;">
                <h3 style="margin-bottom: 10px; color: #2c3e50; font-weight: 600;">📊 システム全体</h3>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">ステータス:</strong> ${data.status === 'ok' ? '✅ 正常' : '❌ エラー'}</p>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">総セッション数:</strong> ${data.total_sessions}件</p>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">アクティブセッション:</strong> ${data.active_sessions}件</p>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">手動返信待ち:</strong> ${data.manual_reply_queue}件</p>
            </div>
            
            <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #c8e6c9;">
                <h3 style="margin-bottom: 10px; color: #2c3e50; font-weight: 600;">🤖 AI設定</h3>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">AI自動応答:</strong> ${data.ai_auto_reply ? '✅ ON' : '⚠️ OFF'}</p>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">管理者モード:</strong> ${data.admin_mode ? '✅ ON' : '⚪ OFF'}</p>
            </div>
            
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #ffe0b2;">
                <h3 style="margin-bottom: 10px; color: #2c3e50; font-weight: 600;">📁 CSVデータ</h3>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">読み込み状態:</strong> ${csvStatus.success ? '✅ 成功' : '❌ 失敗'}</p>
                ${csvStatus.success ? `
                    <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">エンコーディング:</strong> ${csvStatus.encoding || 'N/A'}</p>
                    <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">行数:</strong> ${csvStatus.row_count || 0}行</p>
                    <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">列数:</strong> ${csvStatus.col_count || 0}列</p>
                ` : `
                    <p style="color: #c62828; margin: 8px 0;"><strong style="color: #495057;">エラー:</strong> ${csvStatus.error || '不明なエラー'}</p>
                `}
            </div>
            
            <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; border: 1px solid #bbdefb;">
                <h3 style="margin-bottom: 10px; color: #2c3e50; font-weight: 600;">📈 パフォーマンス統計</h3>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">総リクエスト数:</strong> ${perfStats.total_requests || 0}件</p>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">成功:</strong> ${perfStats.successful_requests || 0}件</p>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">失敗:</strong> ${perfStats.failed_requests || 0}件</p>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">平均応答時間:</strong> ${(perfStats.average_response_time || 0).toFixed(2)}秒</p>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">総トークン使用量:</strong> ${perfStats.total_tokens_used || 0}</p>
                <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">今日のAPI呼び出し:</strong> ${perfStats.api_calls_today || 0}回</p>
            </div>
            
            <p style="margin-top: 15px; text-align: center; color: #666;"><small>最終更新: ${new Date().toLocaleString('ja-JP')}</small></p>
        `;
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('systemStatusContent').innerHTML = `
            <div style="background: #ffebee; padding: 15px; border-radius: 8px; color: #c62828;">
                <p><strong>❌ エラーが発生しました</strong></p>
                <p>${error.message || 'システム状況の取得に失敗しました'}</p>
            </div>
        `;
    });
}

// 医薬品相談テスト
function sendMedicineChat() {
    const input = document.getElementById('medicineChatInput').value;
    if (!input.trim()) {
        alert('メッセージを入力してください');
        return;
    }
    
    const resultDiv = document.getElementById('medicineChatResult');
    resultDiv.innerHTML = `
        <div style="text-align: center; padding: 30px 0;">
            <div style="display: inline-block; width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite;"></div>
            <p style="color: #666; margin-top: 15px;">処理中...</p>
        </div>
        <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    `;
    
    fetch('/admin/medicine_chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({message: input})
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            const symptoms = data.symptoms || [];
            const medicineType = data.medicine_type || 'AI推奨';
            const recommendation = data.recommendation || {};
            
            resultDiv.innerHTML = `
                <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #c8e6c9;">
                    <h4 style="color: #2c3e50; margin-bottom: 10px; font-weight: 600;">✅ ${data.message}</h4>
                    
                    <div style="background: white; padding: 12px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #e0e0e0;">
                        <p style="color: #333; margin-bottom: 8px;"><strong style="color: #495057;">抽出された症状:</strong></p>
                        <p style="color: #555; line-height: 1.6;">${symptoms.length > 0 ? symptoms.join('、') : '症状なし'}</p>
                    </div>
                    
                    <div style="background: white; padding: 12px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #e0e0e0;">
                        <p style="color: #333;"><strong style="color: #495057;">医薬品タイプ:</strong> <span style="color: #1976d2; font-weight: 600;">${medicineType}</span></p>
                    </div>
                    
                    ${recommendation.recommended_medicines && recommendation.recommended_medicines.length > 0 ? `
                        <div style="background: white; padding: 12px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #e0e0e0;">
                            <p style="color: #333; margin-bottom: 10px;"><strong style="color: #495057;">推奨医薬品:</strong> <span style="color: #2e7d32; font-weight: 600;">${recommendation.recommended_medicines.length}件</span></p>
                            <ul style="margin: 10px 0; padding-left: 20px; color: #333;">
                                ${recommendation.recommended_medicines.slice(0, 5).map((med, index) => {
                                    const medName = med.product_name || med.name || med['商品名'] || 'N/A';
                                    const manufacturer = med.manufacturer || med['メーカー名'] || '';
                                    // 正規化後のスコアを計算
                                    let normalizedScore = null;
                                    if (med.score !== undefined && med.score !== null) {
                                        if (med.raw_score !== undefined && med.raw_score !== null) {
                                            // raw_scoreが存在する場合は、それから正規化計算を行う
                                            const rawScore = parseFloat(med.raw_score) || 0.0;
                                            if (rawScore <= 0.5) {
                                                normalizedScore = 0.0;
                                            } else {
                                                const normalizedRange = (rawScore - 0.5) / 0.5;
                                                const sqrtResult = Math.sqrt(normalizedRange);
                                                normalizedScore = Math.min(1.0, sqrtResult);
                                            }
                                        } else {
                                            // raw_scoreが存在しない場合は、med.scoreが既に正規化後のスコアとして使用
                                            normalizedScore = Math.max(0.0, Math.min(1.0, parseFloat(med.score) || 0.0));
                                        }
                                    }
                                    const score = normalizedScore !== null ? ` (スコア: ${(normalizedScore * 100).toFixed(0)}%)` : '';
                                    return `<li style="margin-bottom: 8px; color: #333;">
                                        <strong style="color: #1976d2;">${index + 1}. ${medName}</strong>
                                        ${manufacturer ? `<span style="color: #666; font-size: 0.9em;"> - ${manufacturer}</span>` : ''}
                                        ${score ? `<span style="color: #4caf50; font-size: 0.85em;">${score}</span>` : ''}
                                    </li>`;
                                }).join('')}
                            </ul>
                        </div>
                    ` : '<div style="background: #fff3e0; padding: 12px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #ffe0b2;"><p style="color: #f57c00;">推奨医薬品が見つかりませんでした</p></div>'}
                    
                    <details style="margin-top: 15px;">
                        <summary style="cursor: pointer; color: #1976d2; padding: 10px; background: #f5f5f5; border-radius: 5px; user-select: none; font-weight: 600;">📋 詳細結果を表示（JSON）</summary>
                        <div style="margin-top: 10px; max-height: 400px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 5px;">
                            <pre style="background: #263238; color: #aed581; padding: 15px; margin: 0; font-size: 11px; font-family: 'Courier New', monospace; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word;">${JSON.stringify(data, null, 2)}</pre>
                        </div>
                    </details>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `
                <div style="background: #ffebee; padding: 15px; border-radius: 8px; border: 1px solid #ef9a9a;">
                    <p style="color: #c62828; font-weight: 600; margin-bottom: 8px;"><strong>❌ エラー</strong></p>
                    <p style="color: #d32f2f;">${data.message || '不明なエラー'}</p>
                    ${data.error ? `<p style="font-size: 12px; margin-top: 10px; color: #e64a19;">詳細: ${data.error}</p>` : ''}
                </div>
            `;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        resultDiv.innerHTML = `
            <div style="background: #ffebee; padding: 15px; border-radius: 8px; border: 1px solid #ef9a9a;">
                <p style="color: #c62828; font-weight: 600; margin-bottom: 8px;"><strong>❌ 通信エラー</strong></p>
                <p style="color: #d32f2f;">${error.message || 'サーバーとの通信に失敗しました'}</p>
            </div>
        `;
    });
}

// ログクリア機能
function clearAllLogs() {
    fetch('/clear_logs', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        // 成功通知を表示
        const notification = document.createElement('div');
        notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #4caf50; color: white; padding: 15px 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); z-index: 10000;';
        notification.innerHTML = `<strong>✅ ${data.message || 'ログをクリアしました'}</strong>`;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
        
        // 手動返信待ちキューをクリア
        const queueDiv = document.getElementById('manual-reply-queue');
        if (queueDiv) {
            queueDiv.innerHTML = `
                <div class="empty-state" style="text-align: center; color: #888; font-size: 0.9em; padding: 50px 0;">
                    <div style="font-size: 3em;">📭</div>
                    <p style="margin-top: 10px;">手動返信待ちなし</p>
                </div>
            `;
        }
        
        // 緊急件数カウンターをリセット
        const crisisCountElement = document.getElementById('crisis-count');
        if (crisisCountElement) {
            crisisCountElement.textContent = '';
            crisisCountElement.style.background = '#e3f2fd';
            crisisCountElement.style.color = '#1976d2';
        }
        
        // セッション一覧を更新
        if (typeof loadSessions === 'function') {
            loadSessions();
        }
        
        // 統計情報を更新
        const queueCountEl = document.getElementById('queue-count');
        if (queueCountEl) queueCountEl.textContent = '0';
        const totalSessionsEl = document.getElementById('total-sessions') || document.getElementById('session-count');
        if (totalSessionsEl) totalSessionsEl.textContent = '0';
    })
    .catch(error => {
        console.error('Error:', error);
        alert('エラーが発生しました: ' + error.message);
    });
}

function formatDiagnosisMessage(diagnosis) {
    let content = '';
    
    // デバッグ情報を追加（開発時のみ）
    console.log('Formatting diagnosis:', diagnosis);
    
    if (diagnosis.error) {
        content = `申し訳ございません。${diagnosis.error}`;
    } else {
        // 症状情報の表示
        if (diagnosis.symptoms) {
            content += `<div style="margin-bottom: 10px;"><strong>🔍 症状:</strong><br>${diagnosis.symptoms.join(', ')}</div>`;
        }
        
        if (diagnosis.symptom_pairs) {
            content += `<div style="margin-bottom: 10px;"><strong>🔍 推定された症状:</strong><br>${diagnosis.symptom_pairs.join(', ')}</div>`;
        }
        
        // 医薬品の種類
        if (diagnosis.medicine_type) {
            content += `<div style="margin-bottom: 10px;"><strong>💊 医薬品の種類:</strong><br>${diagnosis.medicine_type}</div>`;
        }
        
        // 推奨医薬品の詳細表示
        if (diagnosis.recommended_medicines && diagnosis.recommended_medicines.length > 0) {
            content += `<div style="margin-bottom: 15px;"><strong>💊 推奨医薬品:</strong></div>`;
            diagnosis.recommended_medicines.forEach((medicine, index) => {
                content += `<div style="margin-bottom: 10px; padding: 10px; border: 1px solid #e0e0e0; border-radius: 5px; background: #f9f9f9;">`;
                content += `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">`;
                content += `<div style="font-weight: bold; color: #2c3e50;">${index + 1}. ${medicine.product_name || '製品名不明'}</div>`;
                // スコアリング表示（管理者画面のみ）
                if (medicine.score !== undefined && medicine.score !== null) {
                    // 正規化後のスコアを計算
                    let normalizedScore;
                    if (medicine.raw_score !== undefined && medicine.raw_score !== null) {
                        // raw_scoreが存在する場合は、それから正規化計算を行う
                        const rawScore = parseFloat(medicine.raw_score) || 0.0;
                        if (rawScore <= 0.5) {
                            normalizedScore = 0.0;
                        } else {
                            const normalizedRange = (rawScore - 0.5) / 0.5;
                            const sqrtResult = Math.sqrt(normalizedRange);
                            normalizedScore = Math.min(1.0, sqrtResult);
                        }
                    } else {
                        // raw_scoreが存在しない場合は、medicine.scoreが既に正規化後のスコアとして使用
                        normalizedScore = Math.max(0.0, Math.min(1.0, parseFloat(medicine.score) || 0.0));
                    }
                    console.log('🔍 Medicine score:', normalizedScore, 'raw:', medicine.raw_score, 'for', medicine.product_name);
                    const scoreClass = normalizedScore >= 0.7 ? 'admin-score-high' : normalizedScore >= 0.5 ? 'admin-score-medium' : 'admin-score-low';
                    const scoreText = normalizedScore >= 0.7 ? '高' : normalizedScore >= 0.5 ? '中' : '低';
                    content += `<div class="admin-score-display ${scoreClass}">
                        📊 最適度: ${(normalizedScore * 100).toFixed(0)}% (${scoreText})
                    </div>`;
                }
                content += `</div>`;
                if (medicine.manufacturer) {
                    content += `<div style="font-size: 0.9em; color: #666;">メーカー: ${medicine.manufacturer}</div>`;
                }
                if (medicine.efficacy) {
                    content += `<div style="font-size: 0.9em; color: #666;">効能効果: ${medicine.efficacy}</div>`;
                }
                if (medicine.ingredients) {
                    content += `<div style="font-size: 0.9em; color: #666;">成分: ${medicine.ingredients}</div>`;
                }
                if (medicine.usage_notes) {
                    // 使用上の注意を項目ごとに改行して表示
                    const usageNotes = medicine.usage_notes;
                    content += `<div style="margin-top: 8px; padding: 8px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #e74c3c;">`;
                    content += `<div style="font-size: 0.9em; color: #e74c3c; font-weight: bold; margin-bottom: 6px;">📋 使用上の注意</div>`;
                    
                    // 使用上の注意を改行で分割して表示
                    const notesArray = usageNotes
                        .split(/\r?\n/)
                        .map(note => note.trim())
                        .filter(note => note && note !== '');
                    
                    if (notesArray.length > 0) {
                        notesArray.forEach(note => {
                            content += `<div style="margin-bottom: 4px; font-size: 0.85em; color: #333;">• ${note}</div>`;
                        });
                    } else {
                        // 改行がない場合はそのまま表示
                        content += `<div style="margin-bottom: 4px; font-size: 0.85em; color: #333;">• ${usageNotes}</div>`;
                    }
                    content += `</div>`;
                }
                if (medicine.doping_prohibited) {
                    content += `<div style="font-size: 0.9em; color: #f39c12;"><strong>ドーピング規制:</strong> ${medicine.doping_prohibited}</div>`;
                }
                content += `</div>`;
            });
        }
        
        // 従来のmedicines配列（後方互換性）
        if (diagnosis.medicines) {
            content += `<div style="margin-bottom: 10px;"><strong>💊 市販薬候補:</strong><br>${diagnosis.medicines.join(', ')}</div>`;
        }
        
        // 使用上の注意
        if (diagnosis.usage_notes) {
            content += `<div style="margin-bottom: 10px;"><strong>⚠️ 使用上の注意:</strong><br>${diagnosis.usage_notes}</div>`;
        }
        
        // 医師相談のアドバイス
        if (diagnosis.doctor_consultation) {
            content += `<div style="margin-bottom: 10px;"><strong>👨‍⚕️ 医師相談:</strong><br>${diagnosis.doctor_consultation}</div>`;
        }
        
        // 注意点
        if (diagnosis.cautions) {
            content += `<div style="margin-bottom: 10px;"><strong>⚠️ 注意点:</strong><br>${diagnosis.cautions.join('<br>')}</div>`;
        }
        
        // 薬の選び方アドバイス
        if (diagnosis.combination_advice) {
            content += `<div style="margin-bottom: 10px;"><strong>💡 薬の選び方アドバイス:</strong><br>${diagnosis.combination_advice}</div>`;
        }
        
        // 質問案内
        if ((diagnosis.symptoms || diagnosis.symptom_pairs) && !diagnosis.error) {
            content += `<div style="margin-top: 10px; font-style: italic; color: #666;"><strong>❓ 他にご質問はありますか？</strong><br>薬の飲み方、副作用、他の症状との関係など、お気軽にお聞きください。</div>`;
        }
    }
    
    // 内容がない場合は診断結果の詳細を表示
    if (!content) {
        content = `<div style="color: #666; font-style: italic;">診断結果の詳細情報がありません。</div>`;
    }
    
    return content;
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendReplyFromChat();
    }
}

// 通常のチャット画面からの返信送信（グローバルスコープに公開）
window.sendReplyFromChat = function() {
    if (!currentSessionId) {
        showNotification('セッションを選択してください', 'warning');
        return;
    }
    
    const chatInput = document.getElementById('chat-input');
    if (!chatInput) {
        showNotification('返信入力欄が見つかりません', 'error');
        return;
    }
    const replyMessage = chatInput.value.trim();
    
    if (!replyMessage) {
        showNotification('返信メッセージを入力してください', 'warning');
        return;
    }
    
    // 入力中表示
    const typingIndicator = document.getElementById('typing-indicator');
    typingIndicator.classList.add('show');
    
    // 送信ボタンを無効化
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;
    
    fetch('/api/main_manual_reply_queue', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'reply',
            session_id: currentSessionId,
            reply_message: replyMessage
        })
    })
    .then(res => res.json())
    .then(data => {
        typingIndicator.classList.remove('show');
        
        if (data.error) {
            showNotification(`エラー: ${data.error}`, 'error');
            sendBtn.disabled = false;
        } else {
            showNotification(`返信を送信しました (セッション: ${data.target_session_id})`, 'success');
            chatInput.value = '';
            chatInput.style.height = 'auto';
            
            console.log('Manual reply sent successfully:', data);
            
            // 即座にチャット履歴を更新（1回のみ）
            setTimeout(() => {
                fetch('/api/main_sessions', {
                    headers: {
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    }
                })
                    .then(res => res.json())
                    .then(sessionsData => {
                        console.log('Updated sessions data after reply:', sessionsData);
                        // APIは {sessions: [...]} の形式で返すため、data.sessions にアクセス
                        const sessionsArray = sessionsData.sessions || (Array.isArray(sessionsData) ? sessionsData : []);
                        const targetSession = sessionsArray.find(s => s.session_id === currentSessionId);
                        if (targetSession) {
                            console.log('Target session after reply:', targetSession);
                            renderChatMessages(targetSession.messages);
                            
                            // セッション一覧も更新
                            allSessions = sessionsArray;
                            renderSessionList(allSessions);
                            const totalSessionsEl = document.getElementById('total-sessions') || document.getElementById('session-count');
            if (totalSessionsEl) {
                totalSessionsEl.textContent = allSessions.length;
            }
                        }
                    })
                    .catch(error => {
                        console.error('Session refresh error:', error);
                    })
                    .finally(() => {
                        // 更新完了後に送信ボタンの状態を更新
                        updateSendButtonState();
                    });
            }, 200);
        }
    })
    .catch(error => {
        typingIndicator.classList.remove('show');
        sendBtn.disabled = false;
        showNotification(`エラー: ${error.message}`, 'error');
    });
}

// 送信ボタンの状態を更新する関数
function updateSendButtonState() {
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const hasText = chatInput.value.trim().length > 0;
    const hasSession = currentSessionId !== null;
    sendBtn.disabled = !hasText || !hasSession;
}

// サイドバーに全セッション一覧を表示
function refreshSessionList() {
    console.log('Refreshing session list...');
    fetch('/api/main_sessions')
        .then(res => res.json())
        .then(data => {
            console.log('Sessions data received:', data);
            // APIは {sessions: [...]} の形式で返すため、data.sessions にアクセス
            const sessionsArray = data.sessions || (Array.isArray(data) ? data : []);
            console.log('Sessions count:', sessionsArray.length);
            
            allSessions = sessionsArray;
            
            // 各セッションの詳細をログ出力
            allSessions.forEach((session, index) => {
                console.log(`Session ${index + 1}:`, {
                    session_id: session.session_id,
                    username: session.username,
                    messages_count: session.messages_count,
                    has_messages: session.messages && session.messages.length > 0
                });
            });
            
            renderSessionList(allSessions);
            
            // モバイルでcenter-panelにチャットカードを表示
            if (isMobile() && !currentSessionId) {
                renderMobileChatListInCenterPanel(allSessions);
            }
            
            // 統計情報も更新
            const totalSessions = allSessions.length;
            const totalSessionsEl = document.getElementById('total-sessions');
            if (totalSessionsEl) totalSessionsEl.textContent = totalSessions;
            
            // モバイル用統計情報も更新
            if (isMobile()) {
                const mobileTotalSessions = document.getElementById('mobile-total-sessions');
                if (mobileTotalSessions) mobileTotalSessions.textContent = totalSessions;
            }
            
            // タブレット/デスクトップ用統計情報も更新
            const tabletTotalSessions = document.getElementById('tablet-total-sessions');
            if (tabletTotalSessions) tabletTotalSessions.textContent = totalSessions;
            
            console.log('Session list refresh completed');
        })
        .catch(error => {
            console.error('Session list error:', error);
            renderSessionList([]);
            document.getElementById('total-sessions').textContent = '0';
        });
}

// セッション検索機能
function filterSessions() {
    const searchTerm = document.getElementById('session-search').value.toLowerCase();
    const filteredSessions = allSessions.filter(session => {
        const username = (session.username || '').toLowerCase();
        const sessionId = (session.session_id || '').toLowerCase();
        return username.includes(searchTerm) || sessionId.includes(searchTerm);
    });
    renderSessionList(filteredSessions);
}

// セッション検索クリア
function clearSessionFilter() {
    document.getElementById('session-search').value = '';
    renderSessionList(allSessions);
}

// HTMLエスケープ関数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderSessionList(sessions) {
    const sidebar = document.getElementById('session-list');
    const sessionCount = document.getElementById('session-count');
    if (!sidebar) return;
    
    console.log('Rendering sessions:', sessions);
    
    // セッションカウントを更新
    if (sessionCount) {
        sessionCount.textContent = Array.isArray(sessions) ? sessions.length : 0;
    }
    
    // モバイルの場合、center-panelにもチャットカードを表示
    if (isMobile() && !currentSessionId) {
        renderMobileChatListInCenterPanel(sessions);
    }
    
    if (!Array.isArray(sessions) || sessions.length === 0) {
        sidebar.innerHTML = '<div class="empty-state"><i class="fa-regular fa-users"></i><p>セッションがありません</p></div>';
        if (isMobile() && !currentSessionId) {
            const centerChatMessages = document.getElementById('chat-messages');
            if (centerChatMessages) {
                centerChatMessages.innerHTML = '<div class="empty-state"><i class="fa-regular fa-comments"></i><p>セッションがありません</p></div>';
            }
        }
        return;
    }
    
    let html = '';
    sessions.forEach((session, idx) => {
        // ユーザー名の取得を改善
        let username = '不明なユーザー';
        if (session.username && session.username.trim()) {
            username = session.username;
        } else if (session.session_id) {
            // セッションIDからユーザー名を生成
            username = `ユーザー${session.session_id.slice(-4)}`;
        } else {
            username = `ユーザー${idx + 1}`;
        }
        
        const messageCount = session.messages_count || 0;
        const isSelected = currentSessionId === session.session_id;
        
        // 最後のメッセージを取得（HTMLタグを除去）
        let lastMessage = 'メッセージなし';
        if (session.messages && session.messages.length > 0) {
            const lastMsg = session.messages[session.messages.length - 1];
            let content = lastMsg.content || '';
            // HTMLタグを除去
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = content;
            const textContent = tempDiv.textContent || tempDiv.innerText || '';
            lastMessage = textContent.substring(0, 30);
            if (textContent.length > 30) {
                lastMessage += '...';
            }
        }
        
        // 最終更新時刻を計算
        let lastUpdate = '不明';
        if (session.messages && session.messages.length > 0) {
            const lastMsg = session.messages[session.messages.length - 1];
            if (lastMsg.timestamp) {
                const date = new Date(lastMsg.timestamp);
                lastUpdate = date.toLocaleString('ja-JP', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            } else {
                // タイムスタンプがない場合は現在時刻を使用
                lastUpdate = new Date().toLocaleString('ja-JP', {
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            }
        }
        
        // 危機対応セッションかどうかをチェック
        const isCrisisSession = session.crisis_detected === true;
        
        // メッセージ数に応じた色分け
        let messageCountColor = '#3498db';
        if (messageCount > 10) messageCountColor = '#e74c3c';
        else if (messageCount > 5) messageCountColor = '#f39c12';
        
        // セッションIDの短縮表示
        const shortSessionId = session.session_id ? session.session_id.substring(0, 8) + '...' : 'unknown';
        
        // 危機対応セッションの場合は特別なスタイルを適用
        const sessionClass = isCrisisSession ? 'session-item crisis' : (isSelected ? 'session-item active' : 'session-item');
        
        html += `
            <div class="${sessionClass}" onclick="selectSession(event, '${session.session_id}', '${username}')">
                <div class="session-meta">
                    <span class="session-time">${lastUpdate}</span>
                    <span style="background: ${isCrisisSession ? 'var(--danger)' : messageCountColor}; color: white; padding: 0.125rem 0.5rem; border-radius: var(--radius-full); font-size: 0.7rem; font-weight: 600;">${messageCount}件</span>
                </div>
                <div class="session-user">
                    ${isCrisisSession ? '<i class="fa-solid fa-triangle-exclamation" style="color: var(--danger); margin-right: 0.25rem;"></i>' : ''}
                    ${escapeHtml(username)}
                </div>
                <div class="session-preview">${escapeHtml(lastMessage)}</div>
            </div>
        `;
    });
    sidebar.innerHTML = html;
}

function selectSession(event, sessionId, username) {
    // モバイル/タブレット判定
    if (isMobile()) {
        openMobileChat(sessionId);
        return;
    } else if (isTablet()) {
        openTabletChat(sessionId);
        return;
    }
    
    currentSessionId = sessionId;
    
    // 選択状態を更新（新しいDOM構造に対応）
    document.querySelectorAll('.session-item').forEach(item => {
        item.classList.remove('active');
    });
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }
    
    // チャットタイトルを更新
    const chatTitle = document.getElementById('chat-title');
    if (chatTitle) {
        chatTitle.textContent = `${username} (${sessionId.substring(0, 8)}...)`;
    }
    
    // チャット入力エリアを有効化
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const micBtn = document.getElementById('mic-btn');
    if (chatInput) {
        chatInput.disabled = false;
        chatInput.placeholder = `${username} に返信メッセージを入力してください...`;
    }
    if (micBtn) micBtn.disabled = false;
    
    // 送信ボタンの状態を更新
    updateSendButtonState();
    
    // 選択したセッションのメッセージ履歴を取得
    loadChatHistory(sessionId);
    
    // 選択したセッションをハイライト
    showNotification(`${username} のセッションを選択しました`, 'success');
}

// 手動返信ボタンの機能
function openManualReply(messageIndex) {
    if (!currentSessionId) {
        showNotification('セッションを選択してください', 'warning');
        return;
    }
    
    const replyMessage = prompt(`メッセージ${messageIndex + 1}に対する手動返信を入力してください:`);
    if (replyMessage && replyMessage.trim()) {
        sendManualReply(replyMessage.trim());
    }
}

// キューアイテムからの返信送信（グローバルスコープに配置）
window.sendReplyFromQueue = function(sessionId, index, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    const replyInput = document.getElementById(`reply-${index}`);
    if (!replyInput) {
        showNotification('返信入力欄が見つかりません', 'error');
        return;
    }
    
    const replyMessage = replyInput.value.trim();
    if (!replyMessage) {
        showNotification('返信メッセージを入力してください', 'warning');
        return;
    }
    
    // ボタンを無効化
    const replyBtn = event ? event.target.closest('.reply-btn') : null;
    if (replyBtn) {
        replyBtn.disabled = true;
        replyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 送信中...';
    }
    
    fetch('/api/main_manual_reply_queue', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'reply',
            session_id: sessionId,
            reply_message: replyMessage
        })
    })
    .then(res => {
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
    })
    .then(data => {
        if (replyBtn) {
            replyBtn.disabled = false;
            replyBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> 返信送信';
        }
        
        if (data.error || data.status === 'error') {
            showNotification(`エラー: ${data.error || data.message || '送信に失敗しました'}`, 'error');
        } else {
            showNotification(`返信を送信しました`, 'success');
            replyInput.value = '';
            
            // キューを更新
            setTimeout(() => {
                refreshQueue();
            }, 500);
        }
    })
    .catch(error => {
        if (replyBtn) {
            replyBtn.disabled = false;
            replyBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> 返信送信';
        }
        showNotification(`エラー: ${error.message}`, 'error');
    });
};

// 手動返信を送信（チャットエリア用）
function sendManualReply(replyMessage) {
    if (!currentSessionId) {
        showNotification('セッションを選択してください', 'warning');
        return;
    }
    
    // 入力中表示
    const typingIndicator = document.getElementById('typing-indicator');
    typingIndicator.classList.add('show');
    
    fetch('/api/main_manual_reply_queue', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'reply',
            session_id: currentSessionId,
            reply_message: replyMessage
        })
    })
    .then(res => res.json())
    .then(data => {
        typingIndicator.classList.remove('show');
        
        if (data.error) {
            showNotification(`エラー: ${data.error}`, 'error');
        } else {
            showNotification(`手動返信を送信しました`, 'success');
            
            // チャット履歴を更新
            setTimeout(() => {
                loadChatHistory(currentSessionId);
            }, 500);
        }
    })
    .catch(error => {
        typingIndicator.classList.remove('show');
        showNotification(`エラー: ${error.message}`, 'error');
    });
}

// 音声認識機能
let recognition = null;
let isRecording = false;

function initVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.log('音声認識APIはこのブラウザではサポートされていません');
        return false;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'ja-JP';
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }

        const chatInput = document.getElementById('chat-input');
        if (finalTranscript) {
            chatInput.value += finalTranscript;
            updateSendButtonState();
        }
    };

    recognition.onerror = (event) => {
        console.error('音声認識エラー:', event.error);
        stopVoiceInput();
        
        let errorMessage = '';
        switch(event.error) {
            case 'not-allowed':
                errorMessage = 'マイクの使用が許可されていません。アドレスバー左側のアイコンからマイクを「許可」に変更してください。';
                break;
            case 'no-speech':
                // 無音の場合は何もしない
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
        showNotification(errorMessage, 'error');
    };

    recognition.onend = () => {
        if (isRecording) {
            recognition.start();
        }
    };

    return true;
}

function toggleVoiceInput() {
    if (!recognition) {
        if (!initVoiceRecognition()) {
            showNotification('このブラウザは音声認識に対応していません', 'error');
            return;
        }
    }

    if (isRecording) {
        stopVoiceInput();
    } else {
        startVoiceInput();
    }
}

function startVoiceInput() {
    try {
        recognition.start();
        isRecording = true;
        const micBtn = document.getElementById('mic-btn');
        micBtn.classList.add('recording');
        micBtn.title = '録音中... (クリックで停止)';
        showNotification('音声認識を開始しました', 'success');
    } catch (error) {
        console.error('音声認識開始エラー:', error);
        showNotification('音声認識の開始に失敗しました', 'error');
    }
}

function stopVoiceInput() {
    if (recognition) {
        recognition.stop();
    }
    isRecording = false;
    const micBtn = document.getElementById('mic-btn');
    micBtn.classList.remove('recording');
    micBtn.title = '音声入力';
}

// セキュリティ詳細表示機能
function showSecurityDetails(securityInfo) {
    const securityPanel = document.getElementById('security-panel');
    const securityDetails = document.getElementById('security-details');
    
    if (!securityInfo || !securityInfo.risk_score) {
        securityPanel.style.display = 'none';
        return;
    }
    
    // リスクスコアに応じたクラス設定
    let riskClass = 'low';
    if (securityInfo.risk_score >= 80) {
        riskClass = 'high';
    } else if (securityInfo.risk_score >= 60) {
        riskClass = 'medium';
    }
    
    // 攻撃パターンの表示
    let attackPatternsHtml = '';
    if (securityInfo.detected_patterns && securityInfo.detected_patterns.length > 0) {
        attackPatternsHtml = `
            <div class="attack-patterns">
                <strong>検出された攻撃パターン:</strong><br>
                ${securityInfo.detected_patterns.map(pattern => `• ${pattern}`).join('<br>')}
            </div>
        `;
    }
    
    // 警告メッセージの表示
    let warningsHtml = '';
    if (securityInfo.warnings && securityInfo.warnings.length > 0) {
        warningsHtml = `
            <div class="security-alert">
                <strong>警告:</strong><br>
                ${securityInfo.warnings.map(warning => `• ${warning}`).join('<br>')}
            </div>
        `;
    }
    
    // セキュリティ詳細のHTML生成
    securityDetails.innerHTML = `
        <div class="security-info">
            <strong>リスクスコア:</strong> 
            <span class="risk-score ${riskClass}">${securityInfo.risk_score}/100</span>
        </div>
        <div class="security-info">
            <strong>検証結果:</strong> 
            ${securityInfo.is_safe ? '✅ 安全' : '❌ 危険'}
        </div>
        <div class="security-info">
            <strong>入力テキスト:</strong> 
            <span style="font-family: monospace; background: #f8f9fa; padding: 2px 4px; border-radius: 3px;">
                ${securityInfo.input_text ? securityInfo.input_text.substring(0, 100) + (securityInfo.input_text.length > 100 ? '...' : '') : 'N/A'}
            </span>
        </div>
        <div class="security-info">
            <strong>サニタイズ済みテキスト:</strong> 
            <span style="font-family: monospace; background: #f8f9fa; padding: 2px 4px; border-radius: 3px;">
                ${securityInfo.sanitized_text ? securityInfo.sanitized_text.substring(0, 100) + (securityInfo.sanitized_text.length > 100 ? '...' : '') : 'N/A'}
            </span>
        </div>
        <div class="security-info">
            <strong>検証時刻:</strong> 
            ${securityInfo.timestamp ? new Date(securityInfo.timestamp).toLocaleString('ja-JP') : 'N/A'}
        </div>
        ${attackPatternsHtml}
        ${warningsHtml}
    `;
    
    securityPanel.style.display = 'block';
}

// セキュリティ詳細を隠す
function hideSecurityDetails() {
    const securityPanel = document.getElementById('security-panel');
    securityPanel.style.display = 'none';
}

// メッセージクリック時のセキュリティ詳細表示
function showMessageSecurityDetails(message) {
    if (message.security_info) {
        showSecurityDetails(message.security_info);
    } else {
        hideSecurityDetails();
    }
}

// グローバルエラーハンドラー（Chrome拡張機能エラーを無視）
window.addEventListener('error', function(event) {
    // Chrome拡張機能のエラーを無視
    if (event.filename && event.filename.includes('chrome-extension://')) {
        return;
    }
    
    // メッセージポートエラーは無視
    if (event.error && event.error.message && 
        event.error.message.includes('message port closed')) {
        return;
    }
    
    // その他のエラーのみログ出力
    console.log('JavaScriptエラーをキャッチ:', event.error);
});

window.addEventListener('unhandledrejection', function(event) {
    // Chrome拡張機能のエラーを無視
    if (event.reason && event.reason.stack && 
        event.reason.stack.includes('chrome-extension://')) {
        event.preventDefault();
        return;
    }
    
    // メッセージポートエラーは無視
    if (event.reason && event.reason.message && 
        event.reason.message.includes('message port closed')) {
        event.preventDefault();
        return;
    }
    
    // その他のエラーのみログ出力
    console.log('未処理のPromise拒否をキャッチ:', event.reason);
});

// 不具合報告関連の関数
function loadFeedbackReports() {
    const unresolvedOnly = document.getElementById('unresolvedOnly') ? document.getElementById('unresolvedOnly').checked : false;
    const contentElement = document.getElementById('feedbackReportsContent');
    
    if (!contentElement) {
        console.error('❌ feedbackReportsContent element not found');
        return;
    }
    
    // 読み込み中メッセージを表示
    contentElement.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">読み込み中...</p>';
    
    // エラーメッセージを表示するヘルパー関数
    const showError = (errorMessage) => {
        try {
            updateFeedbackStats([]);
        } catch (e) {
            console.error('❌ updateFeedbackStats error:', e);
        }
        contentElement.innerHTML = 
            `<div style="padding: 20px; text-align: center;">
                <p style="color: #dc3545; font-weight: 600; margin-bottom: 10px;">⚠️ データベースに接続できません</p>
                <p style="color: #666; font-size: 0.9rem;">${errorMessage}</p>
                <p style="color: #666; font-size: 0.85rem; margin-top: 10px;">ローカル環境ではデータベース接続が必要です。</p>
            </div>`;
    };
    
    // 統計用に常に全データを取得
    fetch(`/api/get_feedback_reports?unresolved_only=false&t=${Date.now()}` , {
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
    .then(response => {
        // HTTPステータスコードをチェック
        if (!response.ok) {
            return response.json().catch(() => {
                // JSON解析に失敗した場合
                return { error: `HTTP ${response.status}: ${response.statusText}` };
            }).then(errData => {
                showError(errData.error || `HTTP ${response.status}: ${response.statusText}`);
                // エラーを投げずに、処理を停止するための特別な値を返す
                return { _stopProcessing: true };
            });
        }
        return response.json();
    })
    .then(allData => {
        // エラーで処理が停止された場合は何もしない
        if (!allData || allData._stopProcessing) {
            return null;
        }
        
        if (allData.error) {
            showError(allData.error);
            return null;
        }
        
        // 統計は全データから計算
        try {
            updateFeedbackStats(allData.reports || []);
        } catch (e) {
            console.error('❌ updateFeedbackStats error:', e);
        }
        
        // 表示用データを取得
        const displayUrl = `/api/get_feedback_reports?unresolved_only=${unresolvedOnly}&t=${Date.now()}`;
        return fetch(displayUrl, {
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
    })
    .then(response => {
        // 前の処理でエラーが発生した場合は何もしない
        if (!response) {
            return null;
        }
        
        // HTTPステータスコードをチェック
        if (!response.ok) {
            return response.json().catch(() => {
                // JSON解析に失敗した場合
                return { error: `HTTP ${response.status}: ${response.statusText}` };
            }).then(errData => {
                contentElement.innerHTML = 
                    `<div style="padding: 20px; text-align: center;">
                        <p style="color: #dc3545; font-weight: 600; margin-bottom: 10px;">⚠️ エラーが発生しました</p>
                        <p style="color: #666; font-size: 0.9rem;">${errData.error || `HTTP ${response.status}: ${response.statusText}`}</p>
                    </div>`;
                // エラーを投げずに、処理を停止するための特別な値を返す
                return { _stopProcessing: true };
            });
        }
        return response.json();
    })
    .then(data => {
        // データがない場合、またはエラーで処理が停止された場合は何もしない
        if (!data || data._stopProcessing) {
            return;
        }
        
        if (data.error) {
            contentElement.innerHTML = 
                `<div style="padding: 20px; text-align: center;">
                    <p style="color: #dc3545; font-weight: 600; margin-bottom: 10px;">⚠️ エラーが発生しました</p>
                    <p style="color: #666; font-size: 0.9rem;">${data.error}</p>
                </div>`;
            return;
        }
        
        const reports = data.reports || [];
        // negative_feedbackとbug_reportのみを表示
        const filteredReports = reports.filter(report => 
            report.report_type === 'negative_feedback' || 
            report.report_type === 'bug_report' ||
            report.report_type === 'ai_negative'  // 後方互換性のため
        );
        try {
            renderFeedbackReports(filteredReports);
        } catch (e) {
            console.error('❌ renderFeedbackReports error:', e);
            contentElement.innerHTML = 
                `<div style="padding: 20px; text-align: center;">
                    <p style="color: #dc3545; font-weight: 600; margin-bottom: 10px;">⚠️ 表示エラー</p>
                    <p style="color: #666; font-size: 0.9rem;">データの表示に失敗しました</p>
                </div>`;
        }
    })
    .catch(error => {
        console.error('❌ Feedback reports fetch error:', error);
        // エラーでも統計を初期化して表示
        try {
            updateFeedbackStats([]);
        } catch (e) {
            console.error('❌ updateFeedbackStats error:', e);
        }
        contentElement.innerHTML = 
            `<div style="padding: 20px; text-align: center;">
                <p style="color: #dc3545; font-weight: 600; margin-bottom: 10px;">⚠️ 通信エラー</p>
                <p style="color: #666; font-size: 0.9rem;">${error.message || 'データの取得に失敗しました'}</p>
            </div>`;
    });
}

function renderFeedbackReports(reports) {
    const content = document.getElementById('feedbackReportsContent');
    
    if (reports.length === 0) {
        content.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">報告はありません</p>';
        return;
    }
    
    let html = `
        <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
            <thead>
                <tr style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                    <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">報告日時</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">タイプ</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">ユーザー</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">ユーザーメッセージ</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">AI応答/警告</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">スコア</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">フィードバック</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">状態</th>
                    <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">操作</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    reports.forEach(report => {
        const reportTypeText = {
            'ai_positive': 'AI評価（適切）',
            'ai_negative': 'AI評価（不適切）',
            'negative_feedback': 'AI評価（不適切）',
            'bug_report': '不具合報告',
            'security_warning': 'セキュリティ警告'
        }[report.report_type] || report.report_type;
        
        const statusText = report.resolved ? '解決済み' : '未解決';
        const statusColor = report.resolved ? '#28a745' : '#dc3545';
        
        // HTMLタグを削除してプレーンテキスト化
        let plainAiResponse = report.ai_response || '-';
        
        // HTMLタグを完全に削除（より強力な処理）
        plainAiResponse = plainAiResponse
            .replace(/<script[^>]*>.*?<\/script>/gi, '')  // scriptタグを削除
            .replace(/<style[^>]*>.*?<\/style>/gi, '')    // styleタグを削除
            .replace(/<[^>]*>/g, '')  // 残りのHTMLタグを削除
            .replace(/&lt;/g, '<')   // HTMLエンティティをデコード
            .replace(/&gt;/g, '>')
            .replace(/&amp;/g, '&')
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            .replace(/&#x27;/g, "'")
            .replace(/&nbsp;/g, ' ')
            .replace(/&apos;/g, "'")
            .replace(/&hellip;/g, '...')
            .replace(/&mdash;/g, '—')
            .replace(/&ndash;/g, '–')
            .replace(/&amp;#39;/g, "'")  // 追加のHTMLエンティティ
            .replace(/&amp;lt;/g, '<')
            .replace(/&amp;gt;/g, '>')
            .replace(/&amp;quot;/g, '"')
            .replace(/&amp;amp;/g, '&')
            .replace(/\r?\n/g, ' ') // 改行をスペースに
            .replace(/\s+/g, ' ')  // 複数の空白を1つに
            .replace(/^\s+|\s+$/g, '')  // 前後の空白を削除
            .trim();
        
        // 50文字超はボタンのみ表示（全文はモーダル）
        const threshold = 50;
        const isLong = plainAiResponse.length > threshold;
        
        html += `
            <tr style="border-bottom: 1px solid #dee2e6;">
                <td style="padding: 10px; border: 1px solid #dee2e6; font-size: 0.9em; color: #333;">${new Date(report.created_at).toLocaleString('ja-JP')}</td>
                <td style="padding: 10px; border: 1px solid #dee2e6; color: #333;">${reportTypeText}</td>
                <td style="padding: 10px; border: 1px solid #dee2e6; color: #333;">${report.username || 'Unknown'}</td>
                <td style="padding: 10px; border: 1px solid #dee2e6; max-width: 200px; word-wrap: break-word; color: #333;">${report.user_message || '-'}</td>
                <td style="padding: 10px; border: 1px solid #dee2e6; max-width: 200px; word-wrap: break-word; color: #333; font-size: 0.75rem; line-height: 1.4;">
                    <div id="ai-response-${report.id}" style="max-height: 80px; overflow: hidden; position: relative; white-space: normal; font-size: 0.75rem; line-height: 1.4;" data-expanded="false" data-full-text="${plainAiResponse.replace(/"/g, '&quot;')}">
                        ${isLong ? '' : escapeHtml(plainAiResponse)}
                    </div>
                    ${isLong ? 
                        `<div style="display:flex; align-items:center; justify-content:center; min-height:40px;">
                            <button onclick="openAiResponseModal(this)" data-full-text="${plainAiResponse.replace(/"/g, '&quot;')}" data-security-score="${report.security_score !== null && report.security_score !== undefined ? report.security_score.toFixed(1) : ''}" class="admin-btn" style="padding: 6px 12px; font-size: 0.8em; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">詳細を表示</button>
                         </div>`
                    : ''}
                </td>
                <td style="padding: 10px; border: 1px solid #dee2e6; color: #333;">
                    ${report.security_score !== null && report.security_score !== undefined 
                        ? report.security_score.toFixed(1) 
                        : '-'}
                </td>
                <td style="padding: 10px; border: 1px solid #dee2e6; max-width: 200px; word-wrap: break-word; color: #333;">${report.feedback_text || '-'}</td>
                <td style="padding: 10px; border: 1px solid #dee2e6; color: ${statusColor}; font-weight: bold;">${statusText}</td>
                <td style="padding: 10px; border: 1px solid #dee2e6;">
                    <div style="display:flex; gap:8px; align-items:center; justify-content:center;">
                        ${!report.resolved ? `<button onclick="resolveFeedback(${report.id})" class="admin-btn" style="padding: 6px 10px; font-size: 0.8em;">解決済み</button>` : ''}
                        <button onclick="deleteFeedback(${report.id})" class="admin-btn" style="padding: 6px 10px; font-size: 0.8em; background:#dc3545; color:#fff;">削除</button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    content.innerHTML = html;
}

function updateFeedbackStats(reports) {
    // negative_feedbackとbug_reportのみを対象（テーブル表示と一致させるため）
    const bugReports = (reports || []).filter(r => 
        r.report_type === 'negative_feedback' || 
        r.report_type === 'bug_report' ||
        r.report_type === 'ai_negative'  // 後方互換性のため
    );
    
    // 全報告数（テーブル表示と一致させるため）
    const totalReports = bugReports.length;
    
    // 解決済み・未解決の数
    const resolvedCount = bugReports.filter(r => r.resolved === true).length;
    const unresolvedCount = totalReports - resolvedCount;
    
    // 適切・不適切の数（全データからai_positiveとai_negative/negative_feedbackをカウント）
    const positiveCount = reports.filter(r => r.report_type === 'ai_positive').length;
    const negativeCount = reports.filter(r => 
        r.report_type === 'ai_negative' || r.report_type === 'negative_feedback'
    ).length;
    const totalFeedback = positiveCount + negativeCount;
    
    // デバッグログ（開発時のみ）
    if (totalFeedback > 0) {
        console.log(`📊 適切率計算: 適切=${positiveCount}, 不適切=${negativeCount}, 合計=${totalFeedback}`);
    }
    
    // 適切率・不適切率の計算（適切もカウントに含める）
    const positiveRatio = totalFeedback > 0 ? ((positiveCount / totalFeedback) * 100).toFixed(1) : '0.0';
    const negativeRatio = totalFeedback > 0 ? ((negativeCount / totalFeedback) * 100).toFixed(1) : '0.0';
    
    // 統計データを表示
    document.getElementById('totalReports').textContent = totalReports;
    document.getElementById('resolvedReports').textContent = resolvedCount;
    document.getElementById('unresolvedReports').textContent = unresolvedCount;
    document.getElementById('positiveRatio').textContent = `${positiveRatio}%`;
    document.getElementById('negativeRatio').textContent = `${negativeRatio}%`;
}

    function showAIDetails(id) {
const element = document.getElementById(`ai-response-${id}`);
const button = element.parentElement.querySelector('button');
const fullText = element.getAttribute('data-full-text');

if (element.getAttribute('data-expanded') === 'true') {
    // 縮小表示
    const truncatedText = fullText.length > 200 ? fullText.substring(0, 200) + '...' : fullText;
    element.textContent = truncatedText;
    element.style.maxHeight = '80px';
    element.style.overflow = 'hidden';
    element.style.whiteSpace = 'pre-wrap';
    element.setAttribute('data-expanded', 'false');
    if (button) {
        button.textContent = 'もっと見る';
        button.style.backgroundColor = '#007bff';
        button.style.color = 'white';
    }
} else {
    // 拡大表示（プレーンテキストとして）
    element.textContent = fullText;
    element.style.maxHeight = 'none';
    element.style.overflow = 'visible';
    element.style.whiteSpace = 'pre-wrap';
    element.setAttribute('data-expanded', 'true');
    if (button) {
        button.textContent = '閉じる';
        button.style.backgroundColor = '#6c757d';
        button.style.color = 'white';
    }
}
    }

// HTMLエンティティを元のタグに戻す関数
function decodeHTMLEntities(text) {
    const textarea = document.createElement('textarea');
    textarea.innerHTML = text;
    return textarea.value;
}

function resolveFeedback(feedbackId) {
    if (!confirm('この報告を解決済みにマークしますか？')) {
        return;
    }
    
    fetch(`/api/resolve_feedback/${feedbackId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification('報告を解決済みにマークしました', 'success');
            loadFeedbackReports(); // 一覧を更新
        } else {
            showNotification(`エラー: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Resolve feedback error:', error);
        showNotification(`エラー: ${error.message}`, 'error');
    });
}

function deleteFeedback(feedbackId) {
    if (!confirm('この報告を削除しますか？')) {
        return;
    }
    fetch(`/api/delete_feedback/${feedbackId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification('報告を削除しました', 'success');
            loadFeedbackReports(); // 一覧と統計を更新
        } else {
            showNotification(`エラー: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        console.error('Delete feedback error:', error);
        showNotification(`エラー: ${error.message}`, 'error');
    });
}

function exportFeedbackReports() {
    const unresolvedOnly = document.getElementById('unresolvedOnly').checked;
    const url = `/api/get_feedback_reports?unresolved_only=${unresolvedOnly}`;
    
    fetch(url, {
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showNotification(`エラー: ${data.error}`, 'error');
            return;
        }
        
        const reports = data.reports || [];
        const csvContent = generateCSV(reports);
        downloadCSV(csvContent, 'feedback_reports.csv');
    })
    .catch(error => {
        console.error('Export feedback reports error:', error);
        showNotification(`エラー: ${error.message}`, 'error');
    });
}

function generateCSV(reports) {
    const headers = ['報告日時', 'タイプ', 'ユーザー', 'ユーザーメッセージ', 'AI応答/警告', 'スコア', 'フィードバック', '状態'];
    let csv = headers.join(',') + '\n';
    
    reports.forEach(report => {
        const reportTypeText = {
            'ai_positive': 'AI評価（適切）',
            'ai_negative': 'AI評価（不適切）',
            'negative_feedback': 'AI評価（不適切）',
            'bug_report': '不具合報告',
            'security_warning': 'セキュリティ警告'
        }[report.report_type] || report.report_type;
        
        const statusText = report.resolved ? '解決済み' : '未解決';
        
        const row = [
            new Date(report.created_at).toLocaleString('ja-JP'),
            reportTypeText,
            report.username || 'Unknown',
            `"${(report.user_message || '').replace(/"/g, '""')}"`,
            `"${(report.ai_response || '').replace(/"/g, '""')}"`,
            report.security_score ? report.security_score.toFixed(1) : '',
            `"${(report.feedback_text || '').replace(/"/g, '""')}"`,
            statusText
        ];
        csv += row.join(',') + '\n';
    });
    
    return csv;
}

function downloadCSV(content, filename) {
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 不具合報告: AI応答全文モーダル
function openAiResponseModal(buttonEl) {
    const fullText = buttonEl.getAttribute('data-full-text') || '';
    const securityScore = buttonEl.getAttribute('data-security-score') || '';
    const modal = document.getElementById('aiFullTextModal');
    const body = document.getElementById('aiFullTextBody');
    if (modal && body) {
        // モーダルをbodyの直接の子要素として移動（確実にレンダリングされるように）
        if (modal.parentElement !== document.body) {
            document.body.appendChild(modal);
        }
        
        // セキュリティスコアがある場合は表示
        let displayText = fullText;
        if (securityScore && securityScore !== '' && securityScore !== 'null' && securityScore !== 'undefined') {
            displayText = `セキュリティスコア: ${securityScore}\n\n${fullText}`;
        }
        
        body.textContent = displayText; // プレーンテキストとして安全に表示
        
        // 既存のインラインスタイルをクリアしてCSSに任せる
        modal.style.cssText = '';
        
        // showクラスを追加（CSSで .admin-modal.show のスタイルが適用される）
        modal.classList.add('show');
        
        // 強制的にレイアウトを再計算
        modal.offsetHeight;
    }
}
function closeAiResponseModal() {
    const modal = document.getElementById('aiFullTextModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
}

// スコア詳細モーダル関連の関数
function showScoreModal(medicineId, medicineIndex) {
    // 現在のセッションの詳細診断データを取得
    let adminDiag = (currentDetailedDiagnosis && currentDetailedDiagnosis.session_id === currentSessionId && Array.isArray(currentDetailedDiagnosis.recommended_medicines))
        ? currentDetailedDiagnosis
        : null;
    
    // currentDetailedDiagnosisがない場合、messagesから最新の診断情報を取得
    if (!adminDiag && currentMessages && currentMessages.length > 0) {
        // 最新のbotメッセージでdiagnosisがあるものを探す
        for (let i = currentMessages.length - 1; i >= 0; i--) {
            const msg = currentMessages[i];
            if (msg.type === 'bot' && msg.diagnosis && msg.diagnosis.recommended_medicines && Array.isArray(msg.diagnosis.recommended_medicines)) {
                // session_idを付与（フロントの一致判定用）
                adminDiag = Object.assign({}, msg.diagnosis, { session_id: currentSessionId });
                console.log('📋 メッセージから診断情報を取得しました:', adminDiag);
                break;
            }
        }
    }
    
    if (!adminDiag || !adminDiag.recommended_medicines || !adminDiag.recommended_medicines[medicineIndex]) {
        alert('スコア情報が見つかりません。');
        console.error('❌ スコア情報が見つかりません:', {
            hasAdminDiag: !!adminDiag,
            hasRecommendedMedicines: !!(adminDiag && adminDiag.recommended_medicines),
            medicineIndex: medicineIndex,
            recommendedMedicinesLength: adminDiag ? adminDiag.recommended_medicines.length : 0,
            currentSessionId: currentSessionId,
            currentDetailedDiagnosis: currentDetailedDiagnosis,
            currentMessagesLength: currentMessages.length
        });
        return;
    }
    
    const medicine = adminDiag.recommended_medicines[medicineIndex];
    
    // スコア情報が存在するか確認
    if (medicine.score === undefined && medicine.score === null && !medicine.scores && !medicine.score_breakdown) {
        alert('この医薬品にはスコア情報がありません。');
        return;
    }
    
    const scoreHtml = generateScoreDetailHtml(medicine);
    
    // モーダルに表示
    const modal = document.getElementById('scoreModal');
    if (modal) {
        // モーダルをbodyの直接の子要素として移動（確実にレンダリングされるように）
        if (modal.parentElement !== document.body) {
            document.body.appendChild(modal);
        }
        
        document.getElementById('scoreModalContent').innerHTML = scoreHtml;
        
        // 既存のインラインスタイルをクリアしてCSSに任せる
        modal.style.cssText = '';
        
        // showクラスを追加（CSSで .admin-modal.show のスタイルが適用される）
        modal.classList.add('show');
        
        // 強制的にレイアウトを再計算
        modal.offsetHeight;
    }
}

// セッション管理機能
function openSessionManagement() {
    const modal = document.getElementById('sessionManagementModal');
    if (modal) {
        modal.style.display = 'flex';
        modal.classList.add('show');
        refreshSessionManagement();
    }
}

function closeSessionManagement() {
    const modal = document.getElementById('sessionManagementModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
}

function refreshSessionManagement() {
    const listContainer = document.getElementById('session-management-list');
    listContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #888;">読み込み中...</div>';
    
    fetch('/api/admin/sessions')
        .then(response => response.json())
        .then(data => {
            if (data.sessions && data.sessions.length > 0) {
                renderSessionManagementList(data.sessions);
            } else {
                listContainer.innerHTML = '<div style="text-align: center; padding: 50px; color: #888;"><i class="fa-regular fa-inbox" style="font-size: 3em; display: block; margin-bottom: 10px; opacity: 0.5;"></i><p style="margin-top: 10px;">セッションがありません</p></div>';
            }
        })
        .catch(error => {
            console.error('Error loading sessions:', error);
            listContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: red;">エラー: セッション情報の読み込みに失敗しました</div>';
        });
}

function renderSessionManagementList(sessions) {
    const listContainer = document.getElementById('session-management-list');
    let html = '<div style="display: grid; gap: 10px;">';
    
    sessions.forEach(session => {
        const lastActivity = session.last_activity ? new Date(session.last_activity * 1000).toLocaleString('ja-JP') : '不明';
        const sessionActive = session.session_active !== false ? '✅ アクティブ' : '❌ 終了';
        const messageCount = session.messages ? session.messages.length : 0;
        
        html += `
            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: white;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <div style="font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">${escapeHtml(session.username || 'Unknown')}</div>
                        <div style="font-size: 0.85em; color: #666; margin-bottom: 3px;">ID: <code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">${escapeHtml(session.session_id)}</code></div>
                        <div style="font-size: 0.85em; color: #666; margin-bottom: 3px;">${sessionActive} | メッセージ数: ${messageCount}</div>
                        <div style="font-size: 0.85em; color: #666;">最終アクティビティ: ${lastActivity}</div>
                        ${session.client_ip ? `<div style="font-size: 0.85em; color: #666;">IP: ${escapeHtml(session.client_ip)}</div>` : ''}
                    </div>
                    <div style="display: flex; gap: 5px; flex-direction: column;">
                        <button class="btn btn-danger" onclick="deleteSession('${session.session_id}')" style="padding: 5px 10px; font-size: 0.8em;">🗑️ 削除</button>
                        <button class="btn btn-info" onclick="editSession('${session.session_id}')" style="padding: 5px 10px; font-size: 0.8em;">✏️ 編集</button>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    listContainer.innerHTML = html;
}

function filterSessionManagement() {
    const searchInput = document.getElementById('session-search-input').value.toLowerCase();
    const sessionItems = document.querySelectorAll('#session-management-list > div > div');
    
    sessionItems.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchInput)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

function deleteSession(sessionId) {
    if (!confirm(`セッション「${sessionId}」を削除してもよろしいですか？`)) {
        return;
    }
    
    fetch(`/api/admin/sessions/${sessionId}`, {
        method: 'DELETE'
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('✅ ' + data.message);
                refreshSessionManagement();
            } else {
                alert('❌ エラー: ' + (data.message || '削除に失敗しました'));
            }
        })
        .catch(error => {
            console.error('Error deleting session:', error);
            alert('❌ 通信エラーが発生しました');
        });
}

function deleteAllSessions() {
    if (!confirm('⚠️ すべてのセッションを削除してもよろしいですか？\nこの操作は取り消せません。')) {
        return;
    }
    
    if (!confirm('⚠️ 本当に削除しますか？')) {
        return;
    }
    
    fetch('/api/admin/sessions/delete_all', {
        method: 'DELETE'
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert(`✅ ${data.deleted_count || 0}件のセッションを削除しました`);
                refreshSessionManagement();
            } else {
                alert('❌ エラー: ' + (data.message || '削除に失敗しました'));
            }
        })
        .catch(error => {
            console.error('Error deleting all sessions:', error);
            alert('❌ 通信エラーが発生しました');
        });
}

function editSession(sessionId) {
    // セッション編集機能（簡易版）
    fetch(`/api/admin/sessions`)
        .then(response => response.json())
        .then(data => {
            const session = data.sessions.find(s => s.session_id === sessionId);
            if (!session) {
                alert('セッションが見つかりません');
                return;
            }
            
            const newUsername = prompt('新しいユーザー名を入力してください:', session.username || 'Unknown');
            if (newUsername === null) return;
            
            const newActive = confirm('セッションをアクティブにしますか？\n（OK: アクティブ、キャンセル: 終了）');
            
            fetch(`/api/admin/sessions/${sessionId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: newUsername,
                    session_active: newActive
                })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert('✅ ' + data.message);
                        refreshSessionManagement();
                    } else {
                        alert('❌ エラー: ' + (data.message || '更新に失敗しました'));
                    }
                })
                .catch(error => {
                    console.error('Error updating session:', error);
                    alert('❌ 通信エラーが発生しました');
                });
        })
        .catch(error => {
            console.error('Error loading session:', error);
            alert('❌ セッション情報の読み込みに失敗しました');
        });
}

function closeScoreModal() {
    const modal = document.getElementById('scoreModal');
    if (modal) {
        modal.classList.remove('show');
        modal.style.display = 'none';
    }
}

function generateScoreDetailHtml(medicine) {
    if (medicine.score === undefined || medicine.score === null) {
        return '<p>スコア情報がありません。</p>';
    }
    
    const breakdown = medicine.scores || medicine.score_breakdown || {};
    // スコアを0.0-1.0の範囲に制限（表示用、正規化後のスコアは後で計算）
    const score = Math.max(0.0, Math.min(1.0, parseFloat(medicine.score) || 0.0));
    const relativeScore = medicine.relative_score !== undefined ? medicine.relative_score : score;
    
    // スコア計算ヘルパー
    const pct = (v) => {
        if (v === undefined || v === null || isNaN(v)) return 0;
        return Math.max(0, Math.min(100, Math.round(v * 100)));
    };
    const riskToPct = (v) => {
        if (v === undefined || v === null || isNaN(v)) return 100;
        return Math.max(0, Math.min(100, Math.round((1 + v) * 100)));
    };
    const formatValue = (v) => {
        if (v === undefined || v === null || isNaN(v)) return '0.000';
        return v.toFixed(3);
    };
    const formatPercent = (v) => {
        if (v === undefined || v === null || isNaN(v)) return '0.0';
        return (v * 100).toFixed(1);
    };

    // 各スコア抽出（基本6要素）
    const symptom = breakdown.symptom_match ?? breakdown.symptom_match_score ?? 0;
    const efficacy = breakdown.efficacy_specificity ?? breakdown.efficacy_specificity_score ?? 0;
    const age = breakdown.age_fit ?? breakdown.age_suitability_score ?? 0;
    const usage = breakdown.usage_convenience ?? breakdown.dosage_convenience_score ?? 0;
    const sideRisk = breakdown.side_effect_risk ?? breakdown.side_effect_risk_score ?? 0;
    const interRisk = breakdown.interaction_risk ?? breakdown.interaction_risk_score ?? 0;
    
    // ボーナス/ペナルティ抽出
    const symptomSpecificityPenalty = breakdown.symptom_specificity_penalty ?? 0;
    const riskIngredientPenalty = breakdown.risk_ingredient_penalty ?? 0;
    const throatBonus = breakdown.throat_bonus ?? 0;
    const symptomBoost = breakdown.symptom_specific_boost ?? 0;
    const multiSymptomBonus = breakdown.multi_symptom_bonus ?? 0;  // MULTI_SYMPTOM_COMBINATIONSのボーナス
    const allergyPenalty = breakdown.allergy_penalty ?? 0;
    const allergyBoost = breakdown.allergy_boost ?? 0;
    const kampoAdjustment = breakdown.kampo_adjustment ?? 0;
    
    // 計算過程のスコア
    const baseScore = breakdown.base_score;
    const adjustedBaseScore = breakdown.adjusted_base_score;
    const adjustmentScore = breakdown.adjustment_score;
    
    // 重み付け（ENHANCED_SCORING_WEIGHTSから）
    const weights = {
        symptom: 0.30,
        efficacy: 0.20,
        age: 0.12,
        usage: 0.03,
        sideRisk: 0.10,   // 正の値（リスクスコアが負なので、掛け算で負の値になる）
        interRisk: 0.05   // 正の値（リスクスコアが負なので、掛け算で負の値になる）
    };
    
    // 基本スコアの計算（重み付け適用）
    const weightedSymptom = symptom * weights.symptom;
    const weightedEfficacy = efficacy * weights.efficacy;
    const weightedAge = age * weights.age;
    const weightedUsage = usage * weights.usage;
    const weightedSideRisk = sideRisk * weights.sideRisk;
    const weightedInterRisk = interRisk * weights.interRisk;
    const calculatedBaseScore = weightedSymptom + weightedEfficacy + weightedAge + weightedUsage + weightedSideRisk + weightedInterRisk;
    
    // 調整スコアの計算（MULTI_SYMPTOM_COMBINATIONSのボーナスを分離）
    // symptomBoostにはmultiSymptomBonusが含まれているので、表示用に分離
    const symptomBoostWithoutMulti = symptomBoost - multiSymptomBonus;
    const calculatedAdjustment = symptomSpecificityPenalty + riskIngredientPenalty + throatBonus + symptomBoost + allergyPenalty + allergyBoost;
    
    // 最終スコアの計算過程
    let calculationSteps = [];
    calculationSteps.push(`基本スコア = 症状適合度×${weights.symptom} + 効能特異性×${weights.efficacy} + 年齢適合性×${weights.age} + 用法簡便性×${weights.usage} + 副作用リスク×${weights.sideRisk} + 相互作用リスク×${weights.interRisk}`);
    calculationSteps.push(`= ${formatValue(symptom)}×${weights.symptom} + ${formatValue(efficacy)}×${weights.efficacy} + ${formatValue(age)}×${weights.age} + ${formatValue(usage)}×${weights.usage} + ${formatValue(sideRisk)}×${weights.sideRisk} + ${formatValue(interRisk)}×${weights.interRisk}`);
    calculationSteps.push(`= ${formatValue(weightedSymptom)} + ${formatValue(weightedEfficacy)} + ${formatValue(weightedAge)} + ${formatValue(weightedUsage)} + ${formatValue(weightedSideRisk)} + ${formatValue(weightedInterRisk)}`);
    calculationSteps.push(`= ${formatValue(calculatedBaseScore)}`);
    
    if (adjustedBaseScore !== undefined && adjustedBaseScore !== calculatedBaseScore) {
        calculationSteps.push(`調整後の基本スコア = ${formatValue(adjustedBaseScore)}（底上げ/補間適用）`);
    }
    
    calculationSteps.push(`調整スコア = 症状特異性ペナルティ + リスク成分ペナルティ + のどボーナス + 症状特化型ブースト + 複数症状ボーナス + アレルギーペナルティ + アレルギーブースト`);
    calculationSteps.push(`= ${formatValue(symptomSpecificityPenalty)} + ${formatValue(riskIngredientPenalty)} + ${formatValue(throatBonus)} + ${formatValue(symptomBoostWithoutMulti)} + ${formatValue(multiSymptomBonus)} + ${formatValue(allergyPenalty)} + ${formatValue(allergyBoost)}`);
    if (multiSymptomBonus > 0) {
        calculationSteps.push(`= ${formatValue(symptomSpecificityPenalty + riskIngredientPenalty + throatBonus + symptomBoostWithoutMulti)} + ${formatValue(multiSymptomBonus)}（複数症状ボーナス） + ${formatValue(allergyPenalty + allergyBoost)}`);
    }
    calculationSteps.push(`= ${formatValue(calculatedAdjustment)}`);
    
    if (kampoAdjustment !== 0) {
        calculationSteps.push(`漢方薬調整 = ${formatValue(kampoAdjustment)}（係数0.8倍適用）`);
    }
    
    const finalScore = baseScore !== undefined ? baseScore : calculatedBaseScore;
    const finalAdjustment = adjustmentScore !== undefined ? adjustmentScore : calculatedAdjustment;
    const totalBeforeKampo = (adjustedBaseScore !== undefined ? adjustedBaseScore : finalScore) + finalAdjustment;
    const totalAfterKampo = kampoAdjustment !== 0 ? totalBeforeKampo * 0.8 : totalBeforeKampo;
    
    // rawScoreは計算された値を使用（medicine.raw_scoreが存在する場合はそれを使用）
    const rawScore = medicine.raw_score !== undefined ? medicine.raw_score : totalAfterKampo;
    
    // 正規化情報を取得（Min-Max正規化用）
    const normalizationInfo = medicine.normalization_info || breakdown.normalization_info;
    const minRawScore = normalizationInfo?.min_raw_score;
    const maxRawScore = normalizationInfo?.max_raw_score;
    const scoreRange = normalizationInfo?.score_range;
    
    // 正規化後のスコアを計算（rawScoreから）
    // medicine.scoreが既に正規化済みの場合はそれを使用、そうでない場合は計算
    let normalizedScore;
    if (medicine.score !== undefined && medicine.score !== null && normalizationInfo === undefined) {
        // normalization_infoが存在しない場合は、既に正規化済みのスコアを使用
        normalizedScore = Math.max(0.0, Math.min(1.0, parseFloat(medicine.score) || 0.0));
    } else if (rawScore <= 0.5) {
        normalizedScore = 0.0;
    } else if (normalizationInfo && scoreRange > 0) {
        // Min-Max正規化: (raw_score - min) / (max - min)
        const minMaxNormalized = (rawScore - minRawScore) / scoreRange;
        // 非線形変換（平方根）で差を拡大
        normalizedScore = Math.min(1.0, Math.sqrt(minMaxNormalized));
    } else {
        // フォールバック: 旧方式
        const normalizedRange = (rawScore - 0.5) / 0.5;
        const sqrtResult = Math.sqrt(normalizedRange);
        normalizedScore = Math.min(1.0, sqrtResult);
    }
    
    // scoreClassも正規化後のスコアで判定
    const scoreClass = normalizedScore >= 0.7 ? 'high' : normalizedScore >= 0.5 ? 'medium' : 'low';
    
    calculationSteps.push(`最終スコア = ${formatValue(adjustedBaseScore !== undefined ? adjustedBaseScore : finalScore)} + ${formatValue(finalAdjustment)}`);
    if (kampoAdjustment !== 0) {
        calculationSteps.push(`= ${formatValue(totalBeforeKampo)} × 0.8（漢方薬調整）`);
    }
    calculationSteps.push(`= ${formatValue(totalAfterKampo)}`);
    calculationSteps.push(`元のスコア（クリップ前） = ${formatValue(rawScore)}`);
    
    // 正規化と非線形変換の説明（表示用、normalizedScoreは既に計算済み）
    if (rawScore <= 0.5) {
        calculationSteps.push(`正規化変換 = ${formatValue(rawScore)} ≤ 0.5 のため 0.0 にマッピング`);
        calculationSteps.push(`最終スコア（正規化後） = ${formatValue(normalizedScore)}（推奨対象外）`);
    } else if (normalizationInfo && scoreRange > 0) {
        // Min-Max正規化の説明
        const minMaxNormalized = (rawScore - minRawScore) / scoreRange;
        const sqrtResult = Math.sqrt(minMaxNormalized);
        calculationSteps.push(`Min-Max正規化 = (${formatValue(rawScore)} - ${formatValue(minRawScore)}) / ${formatValue(scoreRange)} = ${formatValue(minMaxNormalized)}`);
        calculationSteps.push(`非線形変換（平方根） = √${formatValue(minMaxNormalized)} = ${formatValue(sqrtResult)}`);
        calculationSteps.push(`最終スコア（正規化後） = ${formatValue(normalizedScore)}（範囲: [${formatValue(minRawScore)}, ${formatValue(maxRawScore)}] → [0.0, 1.0]）`);
    } else {
        // フォールバック: 旧方式
        const normalizedRange = (rawScore - 0.5) / 0.5;
        const sqrtResult = Math.sqrt(normalizedRange);
        calculationSteps.push(`正規化変換 = (${formatValue(rawScore)} - 0.5) / 0.5 = ${formatValue(normalizedRange)}`);
        calculationSteps.push(`非線形変換（平方根） = √${formatValue(normalizedRange)} = ${formatValue(sqrtResult)}`);
        if (sqrtResult > 1.0) {
            calculationSteps.push(`クリップ処理 = ${formatValue(sqrtResult)} > 1.0 のため 1.0 に制限`);
        }
        calculationSteps.push(`最終スコア（正規化後） = ${formatValue(normalizedScore)}（0.5超の範囲を0.0-1.0に非線形変換）`);
    }

    return `
        <div class="score-detail" style="padding: 20px;">
            <h4 style="margin-bottom: 20px; color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px;">
                ${escapeHtml(medicine.product_name || medicine.name || 'N/A')}
            </h4>
            
            <!-- 総合スコア表示 -->
            <div class="overall-score" style="text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; color: white;">
                <div class="score-circle ${scoreClass}" style="width: 120px; height: 120px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; margin: 0 auto; font-size: 36px; font-weight: bold; border: 4px solid white;">
                    ${(normalizedScore * 100).toFixed(0)}%
                </div>
                <p style="margin-top: 15px; font-size: 20px; font-weight: bold;">最適度: ${normalizedScore >= 0.7 ? '高' : normalizedScore >= 0.5 ? '中' : '低'}</p>
                ${rawScore !== normalizedScore ? `<p style="margin-top: 5px; font-size: 14px; opacity: 0.9;">元のスコア: ${(rawScore * 100).toFixed(1)}% → 正規化後: ${(normalizedScore * 100).toFixed(1)}%</p>` : ''}
                ${relativeScore !== normalizedScore ? `<p style="margin-top: 5px; font-size: 14px; opacity: 0.9;">相対スコア: ${(relativeScore * 100).toFixed(1)}%</p>` : ''}
            </div>
            
            <!-- 基本6要素スコアリング -->
            <div class="score-breakdown" style="margin-bottom: 30px;">
                <h5 style="color: #333; margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-left: 4px solid #007bff; border-radius: 4px;">
                    📊 基本6要素スコアリング
                </h5>
                <div class="score-items" style="display: grid; gap: 15px;">
                    <div class="score-item" data-score-type="symptom" style="display: flex; align-items: center; gap: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                        <span class="score-label" style="flex: 0 0 140px; font-weight: 500;">症状適合度</span>
                        <div class="score-bar" style="flex: 1; height: 24px; background: #e0e0e0; border-radius: 12px; overflow: hidden; position: relative;">
                            <div class="score-fill" style="width: ${pct(symptom)}%; height: 100%; background: linear-gradient(90deg, #4CAF50, #66BB6A); transition: width 0.3s;"></div>
                        </div>
                        <span class="score-value" style="flex: 0 0 80px; text-align: right; font-weight: bold; color: #4CAF50;">${pct(symptom)}%</span>
                        <span style="flex: 0 0 100px; text-align: right; font-size: 0.85em; color: #666;">重み: ${weights.symptom} → ${formatValue(weightedSymptom)}</span>
                    </div>
                    <div class="score-item" data-score-type="efficacy" style="display: flex; align-items: center; gap: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                        <span class="score-label" style="flex: 0 0 140px; font-weight: 500;">効能特異性</span>
                        <div class="score-bar" style="flex: 1; height: 24px; background: #e0e0e0; border-radius: 12px; overflow: hidden;">
                            <div class="score-fill" style="width: ${pct(efficacy)}%; height: 100%; background: linear-gradient(90deg, #2196F3, #42A5F5);"></div>
                        </div>
                        <span class="score-value" style="flex: 0 0 80px; text-align: right; font-weight: bold; color: #2196F3;">${pct(efficacy)}%</span>
                        <span style="flex: 0 0 100px; text-align: right; font-size: 0.85em; color: #666;">重み: ${weights.efficacy} → ${formatValue(weightedEfficacy)}</span>
                    </div>
                    <div class="score-item" data-score-type="age" style="display: flex; align-items: center; gap: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                        <span class="score-label" style="flex: 0 0 140px; font-weight: 500;">年齢適合性</span>
                        <div class="score-bar" style="flex: 1; height: 24px; background: #e0e0e0; border-radius: 12px; overflow: hidden;">
                            <div class="score-fill" style="width: ${pct(age)}%; height: 100%; background: linear-gradient(90deg, #9C27B0, #BA68C8);"></div>
                        </div>
                        <span class="score-value" style="flex: 0 0 80px; text-align: right; font-weight: bold; color: #9C27B0;">${pct(age)}%</span>
                        <span style="flex: 0 0 100px; text-align: right; font-size: 0.85em; color: #666;">重み: ${weights.age} → ${formatValue(weightedAge)}</span>
                    </div>
                    <div class="score-item" data-score-type="usage" style="display: flex; align-items: center; gap: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                        <span class="score-label" style="flex: 0 0 140px; font-weight: 500;">用法簡便性</span>
                        <div class="score-bar" style="flex: 1; height: 24px; background: #e0e0e0; border-radius: 12px; overflow: hidden;">
                            <div class="score-fill" style="width: ${pct(usage)}%; height: 100%; background: linear-gradient(90deg, #FF9800, #FFB74D);"></div>
                        </div>
                        <span class="score-value" style="flex: 0 0 80px; text-align: right; font-weight: bold; color: #FF9800;">${pct(usage)}%</span>
                        <span style="flex: 0 0 100px; text-align: right; font-size: 0.85em; color: #666;">重み: ${weights.usage} → ${formatValue(weightedUsage)}</span>
                    </div>
                    <div class="score-item" data-score-type="side-effect" style="display: flex; align-items: center; gap: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                        <span class="score-label" style="flex: 0 0 140px; font-weight: 500;">副作用リスク</span>
                        <div class="score-bar" style="flex: 1; height: 24px; background: #e0e0e0; border-radius: 12px; overflow: hidden;">
                            <div class="score-fill" style="width: ${riskToPct(sideRisk)}%; height: 100%; background: linear-gradient(90deg, #F44336, #EF5350);"></div>
                        </div>
                        <span class="score-value" style="flex: 0 0 80px; text-align: right; font-weight: bold; color: #F44336;">${riskToPct(sideRisk)}%</span>
                        <span style="flex: 0 0 100px; text-align: right; font-size: 0.85em; color: #666;">重み: ${weights.sideRisk} → ${formatValue(weightedSideRisk)}</span>
                    </div>
                    <div class="score-item" data-score-type="interaction" style="display: flex; align-items: center; gap: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                        <span class="score-label" style="flex: 0 0 140px; font-weight: 500;">相互作用リスク</span>
                        <div class="score-bar" style="flex: 1; height: 24px; background: #e0e0e0; border-radius: 12px; overflow: hidden;">
                            <div class="score-fill" style="width: ${riskToPct(interRisk)}%; height: 100%; background: linear-gradient(90deg, #795548, #A1887F);"></div>
                        </div>
                        <span class="score-value" style="flex: 0 0 80px; text-align: right; font-weight: bold; color: #795548;">${riskToPct(interRisk)}%</span>
                        <span style="flex: 0 0 100px; text-align: right; font-size: 0.85em; color: #666;">重み: ${weights.interRisk} → ${formatValue(weightedInterRisk)}</span>
                    </div>
                </div>
            </div>
            
            <!-- ボーナス/ペナルティ表示 -->
            <div class="bonus-penalty-section" style="margin-bottom: 30px;">
                <h5 style="color: #333; margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-left: 4px solid #FF9800; border-radius: 4px;">
                    ⚡ ボーナス・ペナルティ
                </h5>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <!-- ボーナス -->
                    <div style="padding: 15px; background: #e8f5e9; border-radius: 8px; border-left: 4px solid #4CAF50;">
                        <h6 style="margin: 0 0 10px 0; color: #2e7d32; font-size: 14px; font-weight: bold;">✅ ボーナス</h6>
                        <div style="display: flex; flex-direction: column; gap: 8px;">
                            ${throatBonus !== 0 ? `
                                <div style="display: flex; justify-content: space-between; padding: 6px; background: white; border-radius: 4px;">
                                    <span style="font-size: 0.9em;">のどボーナス</span>
                                    <span style="font-weight: bold; color: #4CAF50;">+${formatValue(throatBonus)}</span>
                                </div>
                            ` : ''}
                            ${symptomBoostWithoutMulti !== 0 ? `
                                <div style="display: flex; justify-content: space-between; padding: 6px; background: white; border-radius: 4px;">
                                    <span style="font-size: 0.9em;">症状特化型ブースト</span>
                                    <span style="font-weight: bold; color: #4CAF50;">+${formatValue(symptomBoostWithoutMulti)}</span>
                                </div>
                            ` : ''}
                            ${multiSymptomBonus !== 0 ? `
                                <div style="display: flex; justify-content: space-between; padding: 6px; background: white; border-radius: 4px;">
                                    <span style="font-size: 0.9em;">複数症状ボーナス（MULTI_SYMPTOM_COMBINATIONS）</span>
                                    <span style="font-weight: bold; color: #4CAF50;">+${formatValue(multiSymptomBonus)}</span>
                                </div>
                            ` : ''}
                            ${allergyBoost !== 0 ? `
                                <div style="display: flex; justify-content: space-between; padding: 6px; background: white; border-radius: 4px;">
                                    <span style="font-size: 0.9em;">アレルギーブースト</span>
                                    <span style="font-weight: bold; color: #4CAF50;">+${formatValue(allergyBoost)}</span>
                                </div>
                            ` : ''}
                            ${(throatBonus === 0 && symptomBoostWithoutMulti === 0 && multiSymptomBonus === 0 && allergyBoost === 0) ? '<div style="color: #999; font-size: 0.9em;">ボーナスなし</div>' : ''}
                        </div>
                    </div>
                    <!-- ペナルティ -->
                    <div style="padding: 15px; background: #ffebee; border-radius: 8px; border-left: 4px solid #F44336;">
                        <h6 style="margin: 0 0 10px 0; color: #c62828; font-size: 14px; font-weight: bold;">⚠️ ペナルティ</h6>
                        <div style="display: flex; flex-direction: column; gap: 8px;">
                            ${symptomSpecificityPenalty !== 0 ? `
                                <div style="display: flex; justify-content: space-between; padding: 6px; background: white; border-radius: 4px;">
                                    <span style="font-size: 0.9em;">症状特異性ペナルティ</span>
                                    <span style="font-weight: bold; color: #F44336;">${formatValue(symptomSpecificityPenalty)}</span>
                                </div>
                            ` : ''}
                            ${riskIngredientPenalty !== 0 ? `
                                <div style="display: flex; justify-content: space-between; padding: 6px; background: white; border-radius: 4px;">
                                    <span style="font-size: 0.9em;">リスク成分ペナルティ</span>
                                    <span style="font-weight: bold; color: #F44336;">${formatValue(riskIngredientPenalty)}</span>
                                </div>
                            ` : ''}
                            ${allergyPenalty !== 0 ? `
                                <div style="display: flex; justify-content: space-between; padding: 6px; background: white; border-radius: 4px;">
                                    <span style="font-size: 0.9em;">アレルギーペナルティ</span>
                                    <span style="font-weight: bold; color: #F44336;">${formatValue(allergyPenalty)}</span>
                                </div>
                            ` : ''}
                            ${kampoAdjustment !== 0 ? `
                                <div style="display: flex; justify-content: space-between; padding: 6px; background: white; border-radius: 4px;">
                                    <span style="font-size: 0.9em;">漢方薬優先度調整</span>
                                    <span style="font-weight: bold; color: #F44336;">${formatValue(kampoAdjustment)}</span>
                                </div>
                            ` : ''}
                            ${(symptomSpecificityPenalty === 0 && riskIngredientPenalty === 0 && allergyPenalty === 0 && kampoAdjustment === 0) ? '<div style="color: #999; font-size: 0.9em;">ペナルティなし</div>' : ''}
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 計算過程表示 -->
            <div class="calculation-process" style="margin-bottom: 20px;">
                <h5 style="color: #333; margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-left: 4px solid #9C27B0; border-radius: 4px;">
                    🧮 スコア計算過程
                </h5>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; font-family: 'Courier New', monospace; font-size: 0.9em; line-height: 1.8;">
                    ${calculationSteps.map((step, index) => `
                        <div style="padding: 4px 0; ${index === calculationSteps.length - 1 ? 'font-weight: bold; color: #9C27B0; border-top: 2px solid #9C27B0; margin-top: 8px; padding-top: 8px;' : ''}">
                            ${index < calculationSteps.length - 1 ? '→ ' : '= '}${step}
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <!-- 中間スコア表示 -->
            ${(baseScore !== undefined || adjustedBaseScore !== undefined || adjustmentScore !== undefined) ? `
            <div class="intermediate-scores" style="margin-bottom: 20px;">
                <h5 style="color: #333; margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-left: 4px solid #607D8B; border-radius: 4px;">
                    📈 中間スコア（デバッグ用）
                </h5>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                    ${baseScore !== undefined ? `
                        <div style="padding: 10px; background: white; border: 1px solid #ddd; border-radius: 6px;">
                            <div style="font-size: 0.85em; color: #666; margin-bottom: 4px;">基本スコア</div>
                            <div style="font-size: 1.2em; font-weight: bold; color: #333;">${formatValue(baseScore)}</div>
                        </div>
                    ` : ''}
                    ${adjustedBaseScore !== undefined ? `
                        <div style="padding: 10px; background: white; border: 1px solid #ddd; border-radius: 6px;">
                            <div style="font-size: 0.85em; color: #666; margin-bottom: 4px;">調整後基本スコア</div>
                            <div style="font-size: 1.2em; font-weight: bold; color: #333;">${formatValue(adjustedBaseScore)}</div>
                        </div>
                    ` : ''}
                    ${adjustmentScore !== undefined ? `
                        <div style="padding: 10px; background: white; border: 1px solid #ddd; border-radius: 6px;">
                            <div style="font-size: 0.85em; color: #666; margin-bottom: 4px;">調整スコア</div>
                            <div style="font-size: 1.2em; font-weight: bold; color: ${adjustmentScore >= 0 ? '#4CAF50' : '#F44336'};">${adjustmentScore >= 0 ? '+' : ''}${formatValue(adjustmentScore)}</div>
                        </div>
                    ` : ''}
                </div>
            </div>
            ` : ''}
        </div>
    `;
}

// ============================================
// レスポンシブ機能
// ============================================

// 画面サイズ検出関数
function isMobile() {
    return window.innerWidth <= 480;
}

function isTablet() {
    return window.innerWidth > 480 && window.innerWidth <= 768;
}

function isDesktop() {
    return window.innerWidth > 768;
}

// モバイル用要素の表示/非表示を切り替え
function toggleMobileElements() {
    const isMobileView = isMobile();
    const mobileContentArea = document.getElementById('mobile-content-area');
    const centerPanel = document.getElementById('center-panel');
    
    if (isMobileView) {
        // モバイル表示
        if (mobileContentArea) {
            mobileContentArea.style.display = 'flex';
            mobileContentArea.style.flexShrink = '0';
        }
        // セッションが選択されていない場合はcenter-panelを表示（チャットカードリスト用）
        if (centerPanel) {
            centerPanel.style.display = 'flex';
            centerPanel.style.flexDirection = 'column';
            centerPanel.style.height = 'calc(100vh - 50px)';
            
            if (currentSessionId) {
                // チャット画面を表示
                loadChatHistory(currentSessionId);
                const chatInputArea = centerPanel.querySelector('.chat-input-area');
                if (chatInputArea) chatInputArea.style.display = 'flex';
            } else {
                // チャットカードリストを表示
                if (allSessions.length > 0) {
                    renderMobileChatListInCenterPanel(allSessions);
                }
                const chatInputArea = centerPanel.querySelector('.chat-input-area');
                if (chatInputArea) chatInputArea.style.display = 'none';
                const chatTitle = document.getElementById('chat-title');
                if (chatTitle) chatTitle.textContent = 'セッションを選択';
            }
        }
    } else {
        // デスクトップ/タブレット表示
        if (mobileContentArea) mobileContentArea.style.display = 'none';
        if (centerPanel && !isTablet()) {
            centerPanel.style.display = 'flex';
            centerPanel.style.flexDirection = 'column';
        }
    }
}

// ウィンドウリサイズ時の処理
window.addEventListener('resize', function() {
    toggleMobileElements();
    // タブレット/デスクトップに切り替わった場合、チャット一覧を復元
    if (!isMobile() && currentSessionId) {
        const centerPanel = document.getElementById('center-panel');
        if (centerPanel) centerPanel.style.display = 'flex';
    }
    
    // デスクトップ表示時にmanual-reply-queueの高さを調整
    if (!isMobile() && !isTablet()) {
        setTimeout(() => {
            adjustManualReplyQueueHeight();
        }, 100);
    }
});

// モバイル用横スライダーのスクロール
function scrollQueueSlider(direction) {
    const slider = document.getElementById('mobile-queue-slider');
    if (!slider) return;
    
    const items = slider.querySelectorAll('.queue-slider-item');
    if (items.length === 0) return;
    
    const itemWidth = items[0].offsetWidth;
    const gap = 8; // gap spacing
    const scrollAmount = itemWidth + gap;
    const currentScroll = slider.scrollLeft;
    const maxScroll = slider.scrollWidth - slider.clientWidth;
    
    // 循環スクロールの実装
    if (direction > 0) {
        // 右にスクロール（最後の複製に到達した場合、最初の実際のアイテムにジャンプ）
        slider.scrollBy({
            left: scrollAmount,
            behavior: 'smooth'
        });
        
        // スクロール完了後にチェック
        setTimeout(() => {
            if (slider.scrollLeft >= maxScroll - 10) {
                const firstRealItem = slider.querySelector('.queue-slider-item[data-index="0"]');
                if (firstRealItem) {
                    firstRealItem.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'center' });
                }
            }
        }, 300);
    } else {
        // 左にスクロール（最初の複製に到達した場合、最後の実際のアイテムにジャンプ）
        slider.scrollBy({
            left: -scrollAmount,
            behavior: 'smooth'
        });
        
        // スクロール完了後にチェック
        setTimeout(() => {
            if (slider.scrollLeft <= 10) {
                const items = slider.querySelectorAll('.queue-slider-item');
                const lastRealIndex = items.length - 3; // 最後の複製を除く
                const lastRealItem = slider.querySelector(`.queue-slider-item[data-index="${lastRealIndex}"]`);
                if (lastRealItem) {
                    lastRealItem.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'center' });
                }
            }
        }, 300);
    }
}

// スワイプ検出（横スライダー用）
let touchStartX = 0;
let touchEndX = 0;

document.addEventListener('DOMContentLoaded', function() {
    const mobileQueueSlider = document.getElementById('mobile-queue-slider');
    if (mobileQueueSlider) {
        mobileQueueSlider.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
        });
        
        mobileQueueSlider.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        });
    }
});

function handleSwipe() {
    const swipeThreshold = 50;
    const slider = document.getElementById('mobile-queue-slider');
    if (!slider) return;
    
    if (touchEndX < touchStartX - swipeThreshold) {
        scrollQueueSlider(1); // 右にスクロール
    } else if (touchEndX > touchStartX + swipeThreshold) {
        scrollQueueSlider(-1); // 左にスクロール
    }
    
    // 循環チェック（スワイプ後）
    setTimeout(() => {
        const items = slider.querySelectorAll('.queue-slider-item');
        if (items.length <= 2) return; // 複製がない場合はスキップ
        
        const maxScroll = slider.scrollWidth - slider.clientWidth;
        if (slider.scrollLeft >= maxScroll - 10) {
            // 最後の複製に到達した場合、最初の実際のアイテムにジャンプ
            const firstRealItem = slider.querySelector('.queue-slider-item[data-index="0"]');
            if (firstRealItem) {
                firstRealItem.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'start' });
            }
        } else if (slider.scrollLeft <= 10) {
            // 最初の複製に到達した場合、最後の実際のアイテムにジャンプ
            const lastRealIndex = items.length - 3;
                const lastRealItem = slider.querySelector(`.queue-slider-item[data-index="${lastRealIndex}"]`);
                if (lastRealItem) {
                    lastRealItem.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'center' });
                }
        }
    }, 300);
    
    // 循環チェック（スワイプ後）
    setTimeout(() => {
        const items = slider.querySelectorAll('.queue-slider-item');
        if (items.length <= 2) return; // 複製がない場合はスキップ
        
        const maxScroll = slider.scrollWidth - slider.clientWidth;
        if (slider.scrollLeft >= maxScroll - 10) {
            // 最後の複製に到達した場合、最初の実際のアイテムにジャンプ
            const firstRealItem = slider.querySelector('.queue-slider-item[data-index="0"]');
            if (firstRealItem) {
                firstRealItem.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'start' });
            }
        } else if (slider.scrollLeft <= 10) {
            // 最初の複製に到達した場合、最後の実際のアイテムにジャンプ
            const lastRealItem = slider.querySelector(`.queue-slider-item[data-index="${items.length - 3}"]`);
            if (lastRealItem) {
                lastRealItem.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'start' });
            }
        }
    }, 300);
}

// モバイル用チャット一覧をカード形式でレンダリング（削除：center-panelに統合）
// function renderMobileChatList(sessions) {
//     // この関数は削除されました。代わりにrenderMobileChatListInCenterPanelを使用してください。
// }

// モバイルでcenter-panelにチャットカードを表示
function renderMobileChatListInCenterPanel(sessions) {
    const centerChatMessages = document.getElementById('chat-messages');
    if (!centerChatMessages || !isMobile() || currentSessionId) return;
    
    if (!Array.isArray(sessions) || sessions.length === 0) {
        centerChatMessages.innerHTML = `
            <div class="empty-state">
                <i class="fa-regular fa-comments"></i>
                <p>セッションがありません</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    sessions.forEach(session => {
        let lastMessage = session.last_message || session.messages?.[session.messages.length - 1]?.content || 'メッセージなし';
        
        // HTMLタグを削除してテキストのみを抽出
        if (typeof lastMessage === 'string') {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = lastMessage;
            lastMessage = tempDiv.textContent || tempDiv.innerText || '';
        }
        
        const shortMessage = lastMessage.length > 50 ? lastMessage.substring(0, 50) + '...' : lastMessage;
        const username = session.username || '匿名';
        const timeStr = session.last_activity ? new Date(session.last_activity).toLocaleString('ja-JP', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '';
        const messageCount = session.messages_count || session.messages?.length || 0;
        
        html += `
            <div class="chat-card" onclick="openMobileChatModal('${session.session_id}', '${username.replace(/'/g, "\\'")}')" 
                 role="button" tabindex="0" 
                 onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();openMobileChatModal('${session.session_id}', '${username.replace(/'/g, "\\'")}')}">
                <div class="chat-card-meta">
                    <span>${escapeHtml(timeStr)}</span>
                    <span>${messageCount}件</span>
                </div>
                <div class="session-user">${escapeHtml(username)}</div>
                <div class="chat-card-preview">${escapeHtml(shortMessage)}</div>
            </div>
        `;
    });
    
    centerChatMessages.innerHTML = html;
}

// モバイルでチャットをモーダルで開く
function openMobileChatModal(sessionId, username) {
    if (!isMobile()) {
        // デスクトップ/タブレットの場合は通常のselectSessionを呼び出す
        const session = allSessions.find(s => s.session_id === sessionId);
        if (session) {
            selectSession(null, sessionId, session.username);
        } else {
            selectSession(null, sessionId, username || 'ユーザー');
        }
        return;
    }
    
    currentSessionId = sessionId;
    const session = allSessions.find(s => s.session_id === sessionId);
    const displayUsername = username || session?.username || 'ユーザー';
    
    // セッションの詳細情報を取得
    const messageCount = session ? (session.messages_count || session.messages?.length || 0) : 0;
    const lastActivity = session ? (session.last_activity || '不明') : '不明';
    const lastMessage = session && session.messages && session.messages.length > 0 
        ? session.messages[session.messages.length - 1].content || 'メッセージなし'
        : 'メッセージなし';
    
    // HTMLタグを削除
    let lastMessageText = lastMessage;
    if (typeof lastMessage === 'string') {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = lastMessage;
        lastMessageText = tempDiv.textContent || tempDiv.innerText || '';
    }
    const shortLastMessage = lastMessageText.length > 50 ? lastMessageText.substring(0, 50) + '...' : lastMessageText;
    
    // 日時をフォーマット
    let formattedDate = '不明';
    if (lastActivity && lastActivity !== '不明') {
        try {
            const date = new Date(lastActivity);
            formattedDate = date.toLocaleString('ja-JP', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (e) {
            formattedDate = lastActivity;
        }
    }
    
    // モーダルを作成または取得
    let modal = document.getElementById('mobile-chat-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'mobile-chat-modal';
        modal.className = 'admin-modal mobile-chat-modal';
        document.body.appendChild(modal);
    }
    
    // モーダルの内容を更新
    modal.innerHTML = `
        <div class="admin-modal-content mobile-chat-modal-content">
            <div class="mobile-chat-header">
                <button class="mobile-chat-close-btn" onclick="closeMobileChatModal()" aria-label="閉じる">
                    <i class="fa-solid fa-times"></i>
                </button>
                <div class="mobile-chat-title-wrapper">
                    <span class="mobile-chat-title" id="mobile-chat-title">${escapeHtml(displayUsername)}</span>
                    <div class="mobile-chat-details" id="mobile-chat-details">
                        <div class="mobile-chat-detail-item">
                            <span class="detail-label">ID:</span>
                            <span class="detail-value">${escapeHtml(sessionId)}</span>
                        </div>
                        <div class="mobile-chat-detail-item">
                            <span class="detail-label">更新日時:</span>
                            <span class="detail-value">${escapeHtml(formattedDate)}</span>
                        </div>
                        <div class="mobile-chat-detail-item">
                            <span class="detail-label">メッセージ数:</span>
                            <span class="detail-value">${messageCount}件</span>
                        </div>
                        <div class="mobile-chat-detail-item full-width">
                            <span class="detail-label">最新メッセージ:</span>
                            <span class="detail-value">${escapeHtml(shortLastMessage)}</span>
                        </div>
                    </div>
                </div>
                <button class="mobile-chat-attributes-btn" onclick="showUserAttributesModal()" id="mobile-chat-attributes-btn" aria-label="ユーザー属性">
                    <i class="fa-solid fa-user-circle"></i>
                </button>
            </div>
            <div class="mobile-chat-messages" id="mobile-chat-messages"></div>
            <div class="mobile-chat-input-area">
                <textarea class="mobile-chat-input" id="mobile-chat-input" placeholder="メッセージを入力..." rows="1" onkeydown="handleMobileChatKeyDown(event)"></textarea>
                <button class="mobile-chat-send-btn" id="mobile-chat-send-btn" onclick="sendMobileChatMessage()" aria-label="送信">
                    <i class="fa-solid fa-paper-plane"></i>
                </button>
            </div>
        </div>
    `;
    
    // モーダルを表示
    modal.style.display = 'flex';
    modal.classList.add('show');
    
    // チャット履歴を読み込む
    loadMobileChatHistory(sessionId);
}

// モバイルチャット履歴を読み込む
function loadMobileChatHistory(sessionId) {
    const chatMessages = document.getElementById('mobile-chat-messages');
    if (!chatMessages) return;
    
    chatMessages.innerHTML = `
        <div class="empty-state">
            <div>🔄</div>
            <p>チャット履歴を読み込み中...</p>
        </div>
    `;
    
    fetch('/api/main_sessions', {
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
    .then(res => res.json())
    .then(data => {
        const sessionsArray = data.sessions || (Array.isArray(data) ? data : []);
        const targetSession = sessionsArray.find(session => session.session_id === sessionId) || null;
        
        if (targetSession && targetSession.messages && Array.isArray(targetSession.messages)) {
            currentDetailedDiagnosis = targetSession.detailed_diagnosis || null;
            currentMessages = targetSession.messages || [];
            renderMobileChatMessages(targetSession.messages);
        } else {
            currentMessages = [];
            renderMobileChatMessages([]);
        }
    })
    .catch(error => {
        console.error('Error loading mobile chat history:', error);
        chatMessages.innerHTML = `
            <div class="empty-state">
                <p>エラーが発生しました</p>
            </div>
        `;
    });
}

// モバイルチャットメッセージをレンダリング（デスクトップと同じUI）
function renderMobileChatMessages(messages) {
    const chatMessages = document.getElementById('mobile-chat-messages');
    if (!chatMessages) return;
    
    // デスクトップと同じrenderChatMessagesを使用
    const originalChatMessages = document.getElementById('chat-messages');
    if (originalChatMessages) {
        originalChatMessages.id = 'chat-messages-temp';
    }
    
    chatMessages.id = 'chat-messages';
    renderChatMessages(messages);
    chatMessages.id = 'mobile-chat-messages';
    
    if (originalChatMessages) {
        originalChatMessages.id = 'chat-messages';
    }
}

// モバイルチャットメッセージを送信
function sendMobileChatMessage() {
    const input = document.getElementById('mobile-chat-input');
    if (!input || !input.value.trim() || !currentSessionId) return;
    
    const message = input.value.trim();
    const sendBtn = document.getElementById('mobile-chat-send-btn');
    
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    }
    
    input.value = '';
    
    fetch('/api/main_manual_reply_queue', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'reply',
            session_id: currentSessionId,
            reply_message: message
        })
    })
    .then(res => res.json())
    .then(data => {
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i>';
        }
        
        if (data.success) {
            // チャット履歴を再読み込み
            loadMobileChatHistory(currentSessionId);
            // キューを更新
            refreshQueue();
        } else {
            showNotification(data.error || '送信に失敗しました', 'error');
        }
    })
    .catch(error => {
        console.error('Error sending mobile chat message:', error);
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i>';
        }
        showNotification('送信エラーが発生しました', 'error');
    });
}

// モバイルチャットのキーボードイベントハンドラ
function handleMobileChatKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMobileChatMessage();
    }
    
    // 入力に応じて送信ボタンの状態を更新
    const sendBtn = document.getElementById('mobile-chat-send-btn');
    if (sendBtn) {
        sendBtn.disabled = !event.target.value.trim() || !currentSessionId;
    }
}

// モバイルチャットモーダルを閉じる
function closeMobileChatModal() {
    const modal = document.getElementById('mobile-chat-modal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('show');
    }
    currentSessionId = null;
}

// モバイルでチャットを開く（インライン表示）- 後方互換性のため残す
function openMobileChat(sessionId) {
    const session = allSessions.find(s => s.session_id === sessionId);
    const username = session ? session.username : 'ユーザー';
    openMobileChatModal(sessionId, username);
}

// モバイル用戻るボタンの追加（チャット画面のpanel-header内、ユーザー名の左側）
function addMobileBackButton() {
    const panelHeader = document.querySelector('#center-panel .panel-header');
    if (!panelHeader || panelHeader.querySelector('.mobile-chat-back-btn')) return;
    
    const chatTitle = document.getElementById('chat-title');
    if (!chatTitle) return;
    
    const backBtn = document.createElement('button');
    backBtn.className = 'mobile-chat-back-btn';
    backBtn.innerHTML = '<i class="fa-solid fa-arrow-left"></i>';
    backBtn.onclick = closeMobileChat;
    backBtn.title = '戻る';
    backBtn.setAttribute('aria-label', 'チャット一覧に戻る');
    backBtn.setAttribute('tabindex', '0');
    
    // ユーザー名の左側に挿入
    panelHeader.insertBefore(backBtn, chatTitle);
}

// モバイルでチャットを閉じる
function closeMobileChat() {
    if (!isMobile()) return;
    
    // チャット画面を非表示にして、チャットカードリストを表示
    const centerPanel = document.getElementById('center-panel');
    if (centerPanel) {
        centerPanel.style.display = 'flex';
        // チャットカードリストを再表示
        renderMobileChatListInCenterPanel(allSessions);
    }
    
  // モバイルコンテンツエリアを表示
  const mobileContentArea = document.getElementById('mobile-content-area');
  if (mobileContentArea) mobileContentArea.style.display = 'flex';
    
    // 戻るボタンを削除
    const backBtn = document.querySelector('.mobile-chat-back-btn');
    if (backBtn) backBtn.remove();
    
    // ユーザー属性情報ボタンを非表示
    const userAttributesBtn = document.getElementById('userAttributesBtn');
    if (userAttributesBtn) {
        userAttributesBtn.style.display = 'none';
    }
    
    // チャット入力をクリア
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.value = '';
        chatInput.disabled = true;
        chatInput.placeholder = 'メッセージを入力...';
    }
    
    // 送信ボタンを無効化
    const sendBtn = document.getElementById('send-btn');
    if (sendBtn) sendBtn.disabled = true;
    
    // チャットタイトルをリセット
    const chatTitle = document.getElementById('chat-title');
    if (chatTitle) {
        chatTitle.textContent = 'セッションを選択';
    }
    
    currentSessionId = null;
}

// モバイル用手動返信待ちキューのレンダリング
function renderMobileQueueSlider(queue) {
    const slider = document.getElementById('mobile-queue-slider');
    if (!slider || !isMobile()) return;
    
    if (!Array.isArray(queue) || queue.length === 0) {
        slider.innerHTML = '<div class="empty-state"><p>手動返信待ちなし</p></div>';
        return;
    }
    
    // 循環スライダーのために、最後のアイテムを最初に、最初のアイテムを最後に複製
    const itemsToRender = queue.length > 1 ? [...queue] : queue;
    
    let html = '';
    
    // 最初のアイテムが中央に来るようにスペーサーを追加
    // アイテム幅は最大300px、画面幅から120px（矢印ボタン用）を引いた値の小さい方
    const viewportWidth = window.innerWidth || 400;
    const itemMaxWidth = 300;
    const itemWidth = Math.min(viewportWidth - 120, itemMaxWidth);
    const spacerWidth = Math.max(0, (viewportWidth - itemWidth) / 2 - 60);
    if (spacerWidth > 0) {
        html += `<div class="slider-spacer" style="flex: 0 0 ${spacerWidth}px; min-width: ${spacerWidth}px; max-width: ${spacerWidth}px; scroll-snap-align: start;"></div>`;
    }
    
    // 最後のアイテムを最初に複製（循環用）
    if (itemsToRender.length > 1) {
        const lastItem = itemsToRender[itemsToRender.length - 1];
        const isCrisisItem = lastItem.status === 'crisis_detected' || lastItem.priority === 'high';
        const crisisBadge = isCrisisItem ? '<span class="crisis-badge">🚨 緊急</span>' : '';
        const shortSessionId = lastItem.session_id ? lastItem.session_id.substring(0, 8) + '...' : '不明';
        const shortMessage = lastItem.user_message && lastItem.user_message.length > 30 
            ? lastItem.user_message.substring(0, 30) + '...' 
            : (lastItem.user_message || 'メッセージなし');
        const session = allSessions.find(s => s.session_id === lastItem.session_id);
        const username = session ? session.username : 'ユーザー';
        
        html += `
            <div class="queue-slider-item" data-clone="last" role="article" aria-label="手動返信待ちキューアイテム ${itemsToRender.length}" 
                 onclick="event.stopPropagation(); openMobileChatModal('${lastItem.session_id}', '${username.replace(/'/g, "\\'")}');" 
                 style="cursor: pointer; touch-action: manipulation;">
                <div style="font-size: 0.8rem; font-weight: 600; margin-bottom: 4px;">
                    ${shortSessionId} ${crisisBadge}
                </div>
                <div style="font-size: 0.75rem; color: #666; margin-bottom: 8px;">
                    ${shortMessage}
                </div>
                <div style="font-size: 0.7rem; color: #999;">
                    ${username}
                </div>
            </div>
        `;
    }
    
    // 通常のアイテム
    itemsToRender.forEach((item, index) => {
        const isCrisisItem = item.status === 'crisis_detected' || item.priority === 'high';
        const crisisBadge = isCrisisItem ? '<span class="crisis-badge">🚨 緊急</span>' : '';
        const shortSessionId = item.session_id ? item.session_id.substring(0, 8) + '...' : '不明';
        const shortMessage = item.user_message && item.user_message.length > 30 
            ? item.user_message.substring(0, 30) + '...' 
            : (item.user_message || 'メッセージなし');
        
        // セッション情報を取得
        const session = allSessions.find(s => s.session_id === item.session_id);
        const username = session ? session.username : 'ユーザー';
        
        html += `
            <div class="queue-slider-item" data-index="${index}" role="article" aria-label="手動返信待ちキューアイテム ${index + 1}" 
                 onclick="event.stopPropagation(); openMobileChatModal('${item.session_id}', '${username.replace(/'/g, "\\'")}');" 
                 style="cursor: pointer; touch-action: manipulation;">
                <div style="font-size: 0.8rem; font-weight: 600; margin-bottom: 4px;">
                    ${shortSessionId} ${crisisBadge}
                </div>
                <div style="font-size: 0.75rem; color: #666; margin-bottom: 8px;">
                    ${shortMessage}
                </div>
                <div style="font-size: 0.7rem; color: #999;">
                    ${username}
                </div>
            </div>
        `;
    });
    
    // 最初のアイテムを最後に複製（循環用）
    if (itemsToRender.length > 1) {
        const firstItem = itemsToRender[0];
        const isCrisisItem = firstItem.status === 'crisis_detected' || firstItem.priority === 'high';
        const crisisBadge = isCrisisItem ? '<span class="crisis-badge">🚨 緊急</span>' : '';
        const shortSessionId = firstItem.session_id ? firstItem.session_id.substring(0, 8) + '...' : '不明';
        const shortMessage = firstItem.user_message && firstItem.user_message.length > 30 
            ? firstItem.user_message.substring(0, 30) + '...' 
            : (firstItem.user_message || 'メッセージなし');
        const session = allSessions.find(s => s.session_id === firstItem.session_id);
        const username = session ? session.username : 'ユーザー';
        
        html += `
            <div class="queue-slider-item" data-clone="first" role="article" aria-label="手動返信待ちキューアイテム 1" 
                 onclick="event.stopPropagation(); openMobileChatModal('${firstItem.session_id}', '${username.replace(/'/g, "\\'")}');" 
                 style="cursor: pointer; touch-action: manipulation;">
                <div style="font-size: 0.8rem; font-weight: 600; margin-bottom: 4px;">
                    ${shortSessionId} ${crisisBadge}
                </div>
                <div style="font-size: 0.75rem; color: #666; margin-bottom: 8px;">
                    ${shortMessage}
                </div>
                <div style="font-size: 0.7rem; color: #999;">
                    ${username}
                </div>
            </div>
        `;
    }
    
    // 最後のアイテムが中央に来るようにスペーサーを追加
    if (spacerWidth > 0) {
        html += `<div class="slider-spacer" style="flex: 0 0 ${spacerWidth}px; min-width: ${spacerWidth}px; max-width: ${spacerWidth}px; scroll-snap-align: end;"></div>`;
    }
    
    slider.innerHTML = html;
    
    // 最初の実際のアイテムにスクロール（複製をスキップ、中央に配置）
    if (itemsToRender.length > 1) {
        setTimeout(() => {
            const firstRealItem = slider.querySelector('.queue-slider-item[data-index="0"]');
            if (firstRealItem) {
                firstRealItem.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'center' });
            }
        }, 0);
    } else if (itemsToRender.length === 1) {
        // アイテムが1つの場合も中央に配置
        setTimeout(() => {
            const firstItem = slider.querySelector('.queue-slider-item[data-index="0"]');
            if (firstItem) {
                firstItem.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'center' });
            }
        }, 0);
    }
    
    // mobile-content-areaの高さをmobile-queue-sliderの下端までに調整
    setTimeout(() => {
        const mobileContentArea = document.getElementById('mobile-content-area');
        const mobileStats = document.getElementById('mobile-stats');
        const mobileQueueSliderContainer = document.getElementById('mobile-queue-slider-container');
        
        if (mobileContentArea && mobileStats && mobileQueueSliderContainer) {
            const statsHeight = mobileStats.offsetHeight;
            const sliderContainerHeight = mobileQueueSliderContainer.offsetHeight;
            const totalHeight = statsHeight + sliderContainerHeight;
            mobileContentArea.style.height = `${totalHeight}px`;
        }
    }, 100);
}

// タブレットでチャットを開く（左パネルを置き換え）
function openTabletChat(sessionId) {
    if (!isTablet()) {
        // デスクトップの場合は通常のselectSessionを呼び出す
        const session = allSessions.find(s => s.session_id === sessionId);
        if (session) {
            selectSession(null, sessionId, session.username);
        } else {
            selectSession(null, sessionId, 'ユーザー');
        }
        return;
    }
    
    // セッション情報を取得
    const session = allSessions.find(s => s.session_id === sessionId);
    const username = session ? session.username : 'ユーザー';
    
    currentSessionId = sessionId;
    
    const leftPanel = document.getElementById('left-panel');
    if (!leftPanel) return;
    
    // 左パネルの内容を保存
    const originalContent = leftPanel.innerHTML;
    leftPanel.dataset.originalContent = originalContent;
    
    // 左パネルをチャット画面に変更
    leftPanel.innerHTML = `
        <div class="panel-header">
            <button class="action-btn" onclick="closeTabletChat()" title="戻る" style="min-width: 44px; min-height: 44px;" aria-label="チャット一覧に戻る">
                <i class="fa-solid fa-arrow-left"></i>
            </button>
            <span class="panel-title" id="tablet-chat-title">${username} (${sessionId.substring(0, 8)}...)</span>
            <button class="action-btn" id="tablet-user-attributes-btn" onclick="showUserAttributesModal()" title="ユーザー属性情報" style="min-width: 44px; min-height: 44px; margin-left: auto;" aria-label="ユーザー属性情報">
                <i class="fa-solid fa-user-circle"></i>
            </button>
        </div>
        <div class="chat-area">
            <div class="chat-messages" id="tablet-chat-messages"></div>
            <div class="chat-input-area">
                <div class="input-wrapper">
                    <textarea class="chat-input" id="tablet-chat-input" placeholder="${username} に返信メッセージを入力してください..." rows="1" onkeydown="handleTabletKeyDown(event)"></textarea>
                    <button class="action-btn send-btn" onclick="sendTabletReply()" style="min-width: 44px; min-height: 44px;" id="tablet-send-btn">
                        <i class="fa-solid fa-paper-plane"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    // チャットを読み込む
    loadTabletChatHistory(sessionId);
}

// タブレットでチャットを閉じる
function closeTabletChat() {
    if (!isTablet()) return;
    
    const leftPanel = document.getElementById('left-panel');
    if (!leftPanel || !leftPanel.dataset.originalContent) return;
    
    // 元の内容を復元
    leftPanel.innerHTML = leftPanel.dataset.originalContent;
    delete leftPanel.dataset.originalContent;
    
    // セッション一覧を再読み込み
    refreshSessionList();
    
    currentSessionId = null;
}

// タブレット用チャット履歴の読み込み
function loadTabletChatHistory(sessionId) {
    const chatMessages = document.getElementById('tablet-chat-messages');
    if (!chatMessages) return;
    
    chatMessages.innerHTML = `
        <div class="empty-state">
            <div>🔄</div>
            <p>チャット履歴を読み込み中...</p>
        </div>
    `;
    
    // デスクトップと同じAPIを使用
    fetch('/api/main_sessions', {
        headers: {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
    })
    .then(res => res.json())
    .then(data => {
        const sessionsArray = data.sessions || (Array.isArray(data) ? data : []);
        const targetSession = sessionsArray.find(session => session.session_id === sessionId) || null;
        
        if (targetSession && targetSession.messages && Array.isArray(targetSession.messages)) {
            // 管理者専用の詳細診断を保持
            currentDetailedDiagnosis = targetSession.detailed_diagnosis || null;
            currentMessages = targetSession.messages || [];
            renderTabletChatMessages(targetSession.messages);
            currentSessionId = sessionId;
            
            // 送信ボタンを有効化
            const sendBtn = document.getElementById('tablet-send-btn');
            if (sendBtn) sendBtn.disabled = false;
        } else {
            currentMessages = [];
            renderTabletChatMessages([]);
        }
    })
    .catch(error => {
        console.error('Error loading tablet chat history:', error);
        chatMessages.innerHTML = `
            <div class="empty-state">
                <p>エラーが発生しました</p>
            </div>
        `;
    });
}

// タブレット用チャットメッセージのレンダリング（デスクトップと同じUI）
function renderTabletChatMessages(messages) {
    // デスクトップと同じrenderChatMessagesを使用
    // 一時的にchat-messagesのIDを変更して使用
    const tabletChatMessages = document.getElementById('tablet-chat-messages');
    if (!tabletChatMessages) return;
    
    // 一時的にchat-messagesのIDを保存
    const originalChatMessages = document.getElementById('chat-messages');
    if (originalChatMessages) {
        originalChatMessages.id = 'chat-messages-temp';
    }
    
    // tablet-chat-messagesをchat-messagesに変更
    tabletChatMessages.id = 'chat-messages';
    
    // renderChatMessagesを呼び出し
    renderChatMessages(messages);
    
    // IDを戻す
    tabletChatMessages.id = 'tablet-chat-messages';
    if (originalChatMessages) {
        originalChatMessages.id = 'chat-messages';
    }
}

// タブレット用返信送信
function sendTabletReply() {
    const input = document.getElementById('tablet-chat-input');
    if (!input || !input.value.trim() || !currentSessionId) return;
    
    const message = input.value.trim();
    const sendBtn = document.getElementById('tablet-send-btn');
    
    // ボタンを無効化
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    }
    
    input.value = '';
    
    fetch('/api/main_manual_reply_queue', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'reply',
            session_id: currentSessionId,
            reply_message: message
        })
    })
    .then(res => res.json())
    .then(data => {
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i>';
        }
        
        if (data.success || data.status === 'success') {
            loadTabletChatHistory(currentSessionId);
            refreshQueue();
            showNotification('返信を送信しました', 'success');
        } else {
            showNotification('返信の送信に失敗しました', 'error');
        }
    })
    .catch(error => {
        console.error('Error sending tablet reply:', error);
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i>';
        }
        showNotification('返信の送信に失敗しました', 'error');
    });
}

// タブレット用キーダウン処理
function handleTabletKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendTabletReply();
    }
    
    // 入力に応じて送信ボタンの状態を更新
    const sendBtn = document.getElementById('tablet-send-btn');
    if (sendBtn) {
        sendBtn.disabled = !event.target.value.trim() || !currentSessionId;
    }
}

// パネルリサイズ機能の条件付き無効化
function initPanelResize() {
    if (isMobile() || isTablet()) {
        // モバイル/タブレットでは無効化
        const resizers = document.querySelectorAll('.panel-resizer');
        resizers.forEach(resizer => {
            resizer.style.pointerEvents = 'none';
            resizer.style.display = 'none';
        });
        
        // パネルリサイズボタンも無効化
        const resizeBtns = document.querySelectorAll('.panel-resize-btn');
        resizeBtns.forEach(btn => {
            btn.style.display = 'none';
        });
        return;
    }
    
    // デスクトップでのみ有効化（既存のリサイズ機能を使用）
    const resizers = document.querySelectorAll('.panel-resizer');
    resizers.forEach(resizer => {
        resizer.style.pointerEvents = 'auto';
        resizer.style.display = 'block';
    });
    
    const resizeBtns = document.querySelectorAll('.panel-resize-btn');
    resizeBtns.forEach(btn => {
        btn.style.display = 'flex';
    });
}

// 既存のrenderQueue関数を拡張してモバイル用スライダーも更新
const originalRenderQueue = renderQueue;
renderQueue = function(queue) {
    originalRenderQueue(queue);
    renderMobileQueueSlider(queue);
    
    // モバイル用統計情報を更新
    if (isMobile()) {
        const queueCount = Array.isArray(queue) ? queue.length : 0;
        const mobileQueueCount = document.getElementById('mobile-queue-count');
        if (mobileQueueCount) mobileQueueCount.textContent = queueCount;
    }
};

// 既存のrenderSessionList関数を拡張してモバイル用チャット一覧も更新（削除：center-panelに統合）
// const originalRenderSessionList = renderSessionList;
// renderSessionList = function(sessions) {
//     originalRenderSessionList(sessions);
//     // renderMobileChatList(sessions); // 削除：center-panelに統合
//     
//     // モバイル用統計情報を更新
//     if (isMobile()) {
//         const totalSessions = Array.isArray(sessions) ? sessions.length : 0;
//         const mobileTotalSessions = document.getElementById('mobile-total-sessions');
//         if (mobileTotalSessions) mobileTotalSessions.textContent = totalSessions;
//     }
// };

// ページ読み込み時のモバイル要素の表示/非表示は、最初のDOMContentLoadedイベントリスナーで処理される
