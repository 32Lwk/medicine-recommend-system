/**
 * 絵文字キャッチゲーム
 * Canvas実装（解像度スケーリング、ダブルバッファリング、ダーティ矩形最適化）
 */

// グローバルバッファ（Canvas最適化用）
let canvasBuffer = null;
let gameState = null;
let gameLoop = null;

/**
 * Canvas最適化のセットアップ
 * @param {HTMLCanvasElement} canvas - Canvas要素
 * @returns {object} Canvasコンテキストとバッファ
 */
function setupOptimizedCanvas(canvas) {
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    
    // 解像度スケーリング
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    
    // ダブルバッファリング（オフスクリーンキャンバス）
    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = canvas.width;
    offscreenCanvas.height = canvas.height;
    const offscreenCtx = offscreenCanvas.getContext('2d');
    offscreenCtx.scale(dpr, dpr);
    
    // グローバルバッファに保存
    canvasBuffer = { ctx, offscreenCtx, canvas, offscreenCanvas };
    
    return { ctx, offscreenCtx };
}

/**
 * 絵文字キャッチゲームの初期化
 */
export function initEmojiGame() {
    // モーダルを作成
    const modal = createEmojiModal();
    document.body.appendChild(modal);
    modal.style.display = 'block';
    
    const canvas = document.getElementById('emojiCanvas');
    if (!canvas) return;
    
    const { ctx, offscreenCtx } = setupOptimizedCanvas(canvas);
    
    // ゲーム状態の初期化（ローカル変数で管理）
    const emojis = ['🎉', '🎊', '🎈', '🎁', '⭐', '🌟', '✨', '💫'];
    
    gameState = {
        emojis: [],
        score: 0,
        canvasWidth: canvas.width / (window.devicePixelRatio || 1),
        canvasHeight: canvas.height / (window.devicePixelRatio || 1),
        emojiList: emojis,
        gameOver: false
    };
    
    // 初期の絵文字を生成
    for (let i = 0; i < 5; i++) {
        generateEmoji();
    }
    
    // イベントリスナーの設定
    setupEmojiControls(canvas);
    
    // ゲームループ開始
    gameLoop = requestAnimationFrame(update);
    
    // モーダルの閉じ方設定
    setupEmojiModalCloseHandlers();
}

/**
 * 絵文字キャッチゲームモーダルの作成
 */
function createEmojiModal() {
    // 現在の言語を取得
    const currentLang = typeof currentLanguage !== 'undefined' ? currentLanguage : 'ja';
    const t = typeof translations !== 'undefined' && translations[currentLang] ? translations[currentLang] : {
        easterEggEmojiGame: '🎯 絵文字キャッチゲーム',
        easterEggEmojiScore: 'スコア: ',
        easterEggEmojiControls: '操作方法: タッチまたはクリックで絵文字をキャッチ！',
        close: '閉じる'
    };
    
    const modal = document.createElement('div');
    modal.id = 'emojiModal';
    modal.className = 'modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'emojiModalTitle');
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 600px; text-align: center;">
            <div class="modal-header">
                <h3 id="emojiModalTitle" style="margin: 0; color: #4CAF50;">${t.easterEggEmojiGame || '🎯 絵文字キャッチゲーム'}</h3>
                <span class="close-modal" onclick="closeEmojiModal()" aria-label="${t.close || '閉じる'}">&times;</span>
            </div>
            <div class="modal-body" style="padding: 20px;">
                <canvas id="emojiCanvas" width="400" height="400" style="border: 2px solid #4CAF50; border-radius: 8px; background: linear-gradient(to bottom, #87CEEB, #E0F6FF); max-width: 100%; touch-action: none;" aria-label="${t.easterEggEmojiGame || '絵文字キャッチゲーム'}"></canvas>
                <div style="margin-top: 15px;">
                    <p id="emojiScore" style="font-size: 18px; font-weight: bold; color: #4CAF50;">${t.easterEggEmojiScore || 'スコア: '}0</p>
                    <p style="font-size: 14px; color: #666; margin-top: 10px;">
                        ${t.easterEggEmojiControls || '操作方法: タッチまたはクリックで絵文字をキャッチ！'}
                    </p>
                </div>
            </div>
        </div>
    `;
    return modal;
}

/**
 * 絵文字キャッチゲームの操作設定
 */
function setupEmojiControls(canvas) {
    // タッチ/クリック操作
    const handleClick = (e) => {
        if (gameState.gameOver) return;
        
        const rect = canvas.getBoundingClientRect();
        const scale = canvas.width / (window.devicePixelRatio || 1) / rect.width;
        const x = (e.clientX || e.touches?.[0]?.clientX || 0) - rect.left;
        const y = (e.clientY || e.touches?.[0]?.clientY || 0) - rect.top;
        
        // 絵文字との衝突判定
        for (let i = gameState.emojis.length - 1; i >= 0; i--) {
            const emoji = gameState.emojis[i];
            const distance = Math.sqrt(
                Math.pow(x - emoji.x, 2) + Math.pow(y - emoji.y, 2)
            );
            
            if (distance < emoji.size / 2) {
                // キャッチ成功
                gameState.score++;
                updateScore();
                gameState.emojis.splice(i, 1);
                generateEmoji();
                break;
            }
        }
    };
    
    // タッチイベントの最適化（preventDefault + touchEvents）
    canvas.addEventListener('touchstart', (e) => {
        e.preventDefault();
        handleClick(e);
    }, { passive: false });
    
    canvas.addEventListener('click', handleClick);
}

/**
 * 絵文字の生成
 */
function generateEmoji() {
    const emoji = gameState.emojiList[Math.floor(Math.random() * gameState.emojiList.length)];
    gameState.emojis.push({
        emoji,
        x: Math.random() * gameState.canvasWidth,
        y: -30,
        vy: 2 + Math.random() * 3,
        size: 30 + Math.random() * 20,
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.1
    });
}

/**
 * ゲーム更新ループ
 */
function update() {
    if (gameState.gameOver) {
        return;
    }
    
    // 絵文字の移動
    for (let i = gameState.emojis.length - 1; i >= 0; i--) {
        const emoji = gameState.emojis[i];
        emoji.y += emoji.vy;
        emoji.rotation += emoji.rotationSpeed;
        
        // 画面外に出たら削除して新しい絵文字を生成
        if (emoji.y > gameState.canvasHeight + 50) {
            gameState.emojis.splice(i, 1);
            generateEmoji();
        }
    }
    
    // 描画
    render();
    
    gameLoop = requestAnimationFrame(update);
}

/**
 * 描画（ダブルバッファリング）
 */
function render() {
    const { ctx, offscreenCtx, canvas, offscreenCanvas } = canvasBuffer;
    
    // 1. オフスクリーン（裏側）に描画
    // 背景
    const gradient = offscreenCtx.createLinearGradient(0, 0, 0, gameState.canvasHeight);
    gradient.addColorStop(0, '#87CEEB');
    gradient.addColorStop(1, '#E0F6FF');
    offscreenCtx.fillStyle = gradient;
    offscreenCtx.fillRect(0, 0, gameState.canvasWidth, gameState.canvasHeight);
    
    // 絵文字を描画
    for (const emojiObj of gameState.emojis) {
        offscreenCtx.save();
        offscreenCtx.translate(emojiObj.x, emojiObj.y);
        offscreenCtx.rotate(emojiObj.rotation);
        offscreenCtx.font = `${emojiObj.size}px Arial`;
        offscreenCtx.textAlign = 'center';
        offscreenCtx.textBaseline = 'middle';
        offscreenCtx.fillText(emojiObj.emoji, 0, 0);
        offscreenCtx.restore();
    }
    
    // 2. メインCanvas（表側）に一気に転送（フリッカー防止）
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(offscreenCanvas, 0, 0);
}

/**
 * スコアの更新
 */
function updateScore() {
    const scoreElement = document.getElementById('emojiScore');
    if (scoreElement) {
        // 現在の言語を取得
        const currentLang = typeof currentLanguage !== 'undefined' ? currentLanguage : 'ja';
        const t = typeof translations !== 'undefined' && translations[currentLang] ? translations[currentLang] : {
            easterEggEmojiScore: 'スコア: '
        };
        scoreElement.textContent = `${t.easterEggEmojiScore || 'スコア: '}${gameState.score}`;
    }
}

/**
 * 絵文字モーダルの閉じ方設定
 */
function setupEmojiModalCloseHandlers() {
    const modal = document.getElementById('emojiModal');
    if (!modal) return;
    
    // Escapeキー（グローバルハンドラーを使用）
    // 既にeaster-eggs.jsでグローバルハンドラーが設定されている場合はスキップ
    
    // モーダル外クリック
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeEmojiModal();
        }
    });
}

/**
 * 絵文字モーダルを閉じる
 */
function closeEmojiModal() {
    const modal = document.getElementById('emojiModal');
    if (modal) {
        modal.remove();
    }
    
    // ゲームループを停止
    if (gameLoop) {
        cancelAnimationFrame(gameLoop);
        gameLoop = null;
    }
    
    // リソースをクリーンアップ（即座にクリーンアップ）
    if (canvasBuffer) {
        // オフスクリーンCanvasを解放
        if (canvasBuffer.offscreenCanvas) {
            canvasBuffer.offscreenCanvas = null;
        }
        canvasBuffer = null;
    }
    gameState = null;
    
    // イースターエッグを終了
    if (window.finishEasterEgg) {
        window.finishEasterEgg();
    }
}

// グローバルに公開
if (typeof window !== 'undefined') {
    window.closeEmojiModal = closeEmojiModal;
}

