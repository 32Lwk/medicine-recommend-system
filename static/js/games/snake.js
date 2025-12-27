/**
 * スネークゲーム
 * Canvas実装（解像度スケーリング、ダブルバッファリング、ダーティ矩形最適化）
 */

// グローバルバッファ（Canvas最適化用）
let canvasBuffer = null;
let gameState = null;
let gameLoop = null;

/**
 * Canvas最適化のセットアップ
 * @param {HTMLCanvasElement} canvas - Canvas要素
 * @param {number} gridSize - グリッドサイズ
 * @returns {object} Canvasコンテキストとバッファ、調整されたサイズ
 */
function setupOptimizedCanvas(canvas, gridSize) {
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    
    // 初期サイズを取得
    const rect = canvas.getBoundingClientRect();
    const initialWidth = rect.width;
    const initialHeight = rect.height;
    
    // グリッドに合わせてサイズを調整（グリッドサイズで割り切れるように）
    const tileCountX = Math.floor(initialWidth / gridSize);
    const tileCountY = Math.floor(initialHeight / gridSize);
    const adjustedWidth = tileCountX * gridSize;
    const adjustedHeight = tileCountY * gridSize;
    
    // Canvasのスタイルサイズを調整（グリッドに合わせる）
    canvas.style.width = adjustedWidth + 'px';
    canvas.style.height = adjustedHeight + 'px';
    
    // 解像度スケーリング（調整後のサイズを使用）
    canvas.width = adjustedWidth * dpr;
    canvas.height = adjustedHeight * dpr;
    ctx.scale(dpr, dpr);
    
    // ダブルバッファリング（オフスクリーンキャンバス）
    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = canvas.width;
    offscreenCanvas.height = canvas.height;
    const offscreenCtx = offscreenCanvas.getContext('2d');
    offscreenCtx.scale(dpr, dpr);
    
    // グローバルバッファに保存
    canvasBuffer = { ctx, offscreenCtx, canvas, offscreenCanvas };
    
    return { 
        ctx, 
        offscreenCtx, 
        adjustedWidth, 
        adjustedHeight, 
        tileCountX, 
        tileCountY 
    };
}

/**
 * スネークゲームの初期化
 */
export function initSnakeGame() {
    // モーダルを作成
    const modal = createSnakeModal();
    document.body.appendChild(modal);
    modal.style.display = 'block';
    
    const canvas = document.getElementById('snakeCanvas');
    if (!canvas) return;
    
    // ゲーム状態の初期化（ローカル変数で管理）
    const gridSize = 20;
    
    // Canvasをグリッドに合わせて調整（根本解決）
    const { ctx, offscreenCtx, adjustedWidth, adjustedHeight, tileCountX, tileCountY } = setupOptimizedCanvas(canvas, gridSize);
    
    // 中心位置を計算（グリッド座標系、0からtileCount-1の範囲）
    const centerX = Math.floor(tileCountX / 2);
    const centerY = Math.floor(tileCountY / 2);
    
    console.log('[Snake Game] Adjusted Canvas:', adjustedWidth, 'x', adjustedHeight);
    console.log('[Snake Game] Tiles:', tileCountX, 'x', tileCountY);
    console.log('[Snake Game] Center:', centerX, ',', centerY);
    console.log('[Snake Game] Max position:', tileCountX - 1, ',', tileCountY - 1);
    
    gameState = {
        snake: [{ x: centerX, y: centerY }],
        food: { x: Math.min(centerX + 5, tileCountX - 1), y: centerY },
        dx: 0,
        dy: 0,
        score: 0,
        gridSize,
        tileCount: tileCountX, // X方向のタイル数（正方形を想定）
        tileCountX,
        tileCountY,
        logicalWidth: adjustedWidth, // Canvasサイズ = 描画範囲（完全一致）
        logicalHeight: adjustedHeight, // Canvasサイズ = 描画範囲（完全一致）
        canvasWidth: adjustedWidth, // Canvasの実際のサイズ（グリッドに合わせて調整済み）
        canvasHeight: adjustedHeight, // Canvasの実際のサイズ（グリッドに合わせて調整済み）
        offsetX: 0, // オフセット不要（完全一致）
        offsetY: 0, // オフセット不要（完全一致）
        gameOver: false
    };
    
    // 初期描画
    render();
    
    // スマホ/タブレット判定とコントロール表示
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || 
                     (window.matchMedia && window.matchMedia('(max-width: 768px)').matches);
    const controlsDiv = document.getElementById('snakeControls');
    if (controlsDiv) {
        if (isMobile) {
            controlsDiv.style.display = 'flex';
        } else {
            controlsDiv.style.display = 'none';
        }
    }
    
    // イベントリスナーの設定
    setupSnakeControls(canvas);
    
    // モーダルにフォーカスを当てる（PCのキーボード操作のため）
    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
        modalContent.setAttribute('tabindex', '-1');
        modalContent.focus();
    }
    
    // ゲームループ開始
    gameLoop = requestAnimationFrame(update);
    
    // モーダルの閉じ方設定
    setupSnakeModalCloseHandlers();
}

/**
 * スネークゲームモーダルの作成
 */
function createSnakeModal() {
    // 現在の言語を取得
    const currentLang = typeof currentLanguage !== 'undefined' ? currentLanguage : 'ja';
    const t = typeof translations !== 'undefined' && translations[currentLang] ? translations[currentLang] : {
        easterEggSnakeGame: '🐍 スネークゲーム',
        easterEggSnakeScore: 'スコア: ',
        easterEggSnakeControls: '操作方法: 方向キーまたは画面のボタン',
        close: '閉じる'
    };
    
    const modal = document.createElement('div');
    modal.id = 'snakeModal';
    modal.className = 'modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'snakeModalTitle');
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 600px; text-align: center;">
            <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; padding: 15px 20px; border-bottom: 2px solid #e0e0e0; background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 100%);">
                <h3 id="snakeModalTitle" style="margin: 0; color: #4CAF50; font-size: 20px; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">${t.easterEggSnakeGame || '🐍 スネークゲーム'}</h3>
                <div style="display: flex; gap: 12px; align-items: center;">
                    <span id="snakeHeaderScore" style="font-size: 16px; font-weight: bold; color: #2196F3; background: #E3F2FD; padding: 6px 12px; border-radius: 20px; min-width: 80px; text-align: center;">${t.easterEggSnakeScore || 'スコア: '}0</span>
                    <button onclick="restartSnakeGame()" style="padding: 8px 12px; font-size: 16px; background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%); color: white; border: none; border-radius: 6px; cursor: pointer; box-shadow: 0 2px 4px rgba(33,150,243,0.3); transition: all 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'" aria-label="再戦" title="再戦">▶️ 再戦</button>
                    <span class="close-modal" onclick="closeSnakeModal()" aria-label="${t.close || '閉じる'}" style="cursor: pointer; font-size: 28px; line-height: 1; color: #666; transition: color 0.2s; padding: 4px 8px; border-radius: 4px;" onmouseover="this.style.color='#f44336'; this.style.background='#ffebee'" onmouseout="this.style.color='#666'; this.style.background='transparent'">&times;</span>
                </div>
            </div>
            <div class="modal-body" style="padding: 20px;">
                <canvas id="snakeCanvas" width="400" height="400" style="border: 2px solid #4CAF50; border-radius: 8px; background: #000; max-width: 100%; display: block; margin: 0 auto;" aria-label="${t.easterEggSnakeGame || 'スネークゲーム'}"></canvas>
                <div style="margin-top: 15px;">
                    <p style="font-size: 14px; color: #666; margin-top: 10px;">
                        ${t.easterEggSnakeControls || '操作方法: 方向キーまたは画面のボタン'}
                    </p>
                </div>
                <div id="snakeControls" class="snake-controls-mobile" style="margin-top: 15px; display: none; justify-content: center; gap: 10px; flex-wrap: wrap;">
                    <button onclick="snakeMove('up')" style="padding: 10px 20px; font-size: 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; touch-action: manipulation;">↑</button>
                    <div style="display: flex; flex-direction: column; gap: 5px;">
                        <button onclick="snakeMove('left')" style="padding: 10px 20px; font-size: 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; touch-action: manipulation;">←</button>
                        <button onclick="snakeMove('right')" style="padding: 10px 20px; font-size: 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; touch-action: manipulation;">→</button>
                    </div>
                    <button onclick="snakeMove('down')" style="padding: 10px 20px; font-size: 20px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer; touch-action: manipulation;">↓</button>
                </div>
            </div>
        </div>
    `;
    return modal;
}

/**
 * スネークゲームの操作設定
 */
let keyHandler = null; // クリーンアップ用に保存

function setupSnakeControls(canvas) {
    // 既存のハンドラーを削除（重複防止）
    if (keyHandler) {
        document.removeEventListener('keydown', keyHandler);
    }
    
    // キーボード操作（方向キー）- PCのみ
    keyHandler = (e) => {
        // モーダルが表示されていない場合は無視
        const modal = document.getElementById('snakeModal');
        if (!modal || modal.style.display !== 'block') {
            return;
        }
        
        if (gameState && gameState.gameOver) return;
        
        // モーダル内の入力フィールドなどでない場合のみ処理
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        switch (e.key) {
            case 'ArrowUp':
                e.preventDefault();
                if (gameState.dy === 0) {
                    gameState.dx = 0;
                    gameState.dy = -1;
                }
                break;
            case 'ArrowDown':
                e.preventDefault();
                if (gameState.dy === 0) {
                    gameState.dx = 0;
                    gameState.dy = 1;
                }
                break;
            case 'ArrowLeft':
                e.preventDefault();
                if (gameState.dx === 0) {
                    gameState.dx = -1;
                    gameState.dy = 0;
                }
                break;
            case 'ArrowRight':
                e.preventDefault();
                if (gameState.dx === 0) {
                    gameState.dx = 1;
                    gameState.dy = 0;
                }
                break;
        }
    };
    
    document.addEventListener('keydown', keyHandler);
    
    // グローバルに公開（ボタン操作用）
    window.snakeMove = (direction) => {
        if (gameState.gameOver) return;
        
        switch (direction) {
            case 'up':
                if (gameState.dy === 0) {
                    gameState.dx = 0;
                    gameState.dy = -1;
                }
                break;
            case 'down':
                if (gameState.dy === 0) {
                    gameState.dx = 0;
                    gameState.dy = 1;
                }
                break;
            case 'left':
                if (gameState.dx === 0) {
                    gameState.dx = -1;
                    gameState.dy = 0;
                }
                break;
            case 'right':
                if (gameState.dx === 0) {
                    gameState.dx = 1;
                    gameState.dy = 0;
                }
                break;
        }
    };
}

/**
 * ゲーム更新ループ
 */
let lastTime = 0;
const gameSpeed = 150; // ミリ秒

function update(currentTime) {
    if (gameState.gameOver) {
        showGameOver();
        return;
    }
    
    if (currentTime - lastTime < gameSpeed) {
        gameLoop = requestAnimationFrame(update);
        return;
    }
    
    lastTime = currentTime;
    
    // スネークの移動（dx/dyが0の場合は移動しない）
    if (gameState.dx === 0 && gameState.dy === 0) {
        // まだ移動していない場合は描画のみ
        render();
        gameLoop = requestAnimationFrame(update);
        return;
    }
    
    const head = {
        x: gameState.snake[0].x + gameState.dx,
        y: gameState.snake[0].y + gameState.dy
    };
    
    // 壁との衝突チェック（X方向とY方向を別々にチェック）
    if (head.x < 0 || head.x >= gameState.tileCountX || 
        head.y < 0 || head.y >= gameState.tileCountY) {
        gameState.gameOver = true;
        showGameOver();
        return;
    }
    
    // 自分自身との衝突チェック（頭以外の部分とチェック）
    for (let i = 1; i < gameState.snake.length; i++) {
        if (head.x === gameState.snake[i].x && head.y === gameState.snake[i].y) {
            gameState.gameOver = true;
            showGameOver();
            return;
        }
    }
    
    gameState.snake.unshift(head);
    
    // 食べ物との衝突チェック
    if (head.x === gameState.food.x && head.y === gameState.food.y) {
        gameState.score++;
        updateScore();
        generateFood();
    } else {
        gameState.snake.pop();
    }
    
    // 描画
    render();
    
    gameLoop = requestAnimationFrame(update);
}

/**
 * 描画（ダブルバッファリング）
 */
function render() {
    if (!canvasBuffer || !gameState) return;
    
    const { ctx, offscreenCtx, canvas, offscreenCanvas } = canvasBuffer;
    
    // 1. オフスクリーン（裏側）に描画
    // 背景をクリア（Canvas全体を黒で塗りつぶし）
    offscreenCtx.fillStyle = '#000';
    offscreenCtx.fillRect(0, 0, gameState.canvasWidth, gameState.canvasHeight);
    
    // 食べ物（🍎）を描画（オフセット不要、Canvasサイズ = 描画範囲）
    const foodGridX = gameState.food.x * gameState.gridSize;
    const foodGridY = gameState.food.y * gameState.gridSize;
    const foodX = foodGridX + gameState.gridSize / 2;
    const foodY = foodGridY + gameState.gridSize / 2;
    
    // フォントサイズを大きくして見やすくする（gridSizeに合わせる）
    const fontSize = gameState.gridSize;
    offscreenCtx.save();
    offscreenCtx.font = `${fontSize}px Arial, "Apple Color Emoji", "Segoe UI Emoji", sans-serif`;
    offscreenCtx.textAlign = 'center';
    offscreenCtx.textBaseline = 'middle';
    // 絵文字を描画
    offscreenCtx.fillText('🍎', foodX, foodY);
    offscreenCtx.restore();
    
    // スネークを描画（オフセット不要、Canvasサイズ = 描画範囲）
    offscreenCtx.fillStyle = '#0f0';
    for (const segment of gameState.snake) {
        // グリッド位置からピクセル位置を計算（直接計算、オフセット不要）
        // グリッド座標は0からtileCount-1の範囲
        const x = segment.x * gameState.gridSize;
        const y = segment.y * gameState.gridSize;
        
        // 描画範囲内か確認（Canvasサイズ以内）
        if (x >= 0 && x < gameState.canvasWidth && y >= 0 && y < gameState.canvasHeight) {
            // マージンを1px追加して見やすくする
            const margin = 1;
            const size = gameState.gridSize - (margin * 2);
            // 描画範囲を超えないように調整
            const drawWidth = Math.min(size, gameState.canvasWidth - x - margin);
            const drawHeight = Math.min(size, gameState.canvasHeight - y - margin);
            if (drawWidth > 0 && drawHeight > 0) {
                offscreenCtx.fillRect(
                    x + margin,
                    y + margin,
                    drawWidth,
                    drawHeight
                );
            }
        }
    }
    
    // 2. メインCanvas（表側）に一気に転送（フリッカー防止）
    // 実際のCanvasサイズ（物理ピクセル）でクリア
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    // オフスクリーンCanvasを転送（スケールは既に適用済み）
    ctx.drawImage(offscreenCanvas, 0, 0);
}

/**
 * 食べ物の生成
 */
function generateFood() {
    gameState.food = {
        x: Math.floor(Math.random() * gameState.tileCountX),
        y: Math.floor(Math.random() * gameState.tileCountY)
    };
    
    // スネークの体と重ならないように
    for (const segment of gameState.snake) {
        if (gameState.food.x === segment.x && gameState.food.y === segment.y) {
            generateFood();
            return;
        }
    }
}

/**
 * スコアの更新
 */
function updateScore() {
    // ヘッダーのスコアを更新
    const headerScoreElement = document.getElementById('snakeHeaderScore');
    if (headerScoreElement) {
        // 現在の言語を取得
        const currentLang = typeof currentLanguage !== 'undefined' ? currentLanguage : 'ja';
        const t = typeof translations !== 'undefined' && translations[currentLang] ? translations[currentLang] : {
            easterEggSnakeScore: 'スコア: '
        };
        headerScoreElement.textContent = `${t.easterEggSnakeScore || 'スコア: '}${gameState.score}`;
    }
}

/**
 * ゲームオーバーの表示
 */
function showGameOver() {
    const modal = document.getElementById('snakeModal');
    if (!modal) return;
    
    // 現在の言語を取得
    const currentLang = typeof currentLanguage !== 'undefined' ? currentLanguage : 'ja';
    const t = typeof translations !== 'undefined' && translations[currentLang] ? translations[currentLang] : {
        easterEggSnakeGameOver: 'ゲームオーバー！',
        easterEggSnakeScore: 'スコア: ',
        close: '閉じる'
    };
    
    const gameOverDiv = document.createElement('div');
    gameOverDiv.id = 'snakeGameOver';
    gameOverDiv.style.cssText = `
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0, 0, 0, 0.9);
        color: white;
        padding: 30px;
        border-radius: 10px;
        text-align: center;
        z-index: 10000;
    `;
    gameOverDiv.innerHTML = `
        <h2 style="margin: 0 0 15px 0;">${t.easterEggSnakeGameOver || 'ゲームオーバー！'}</h2>
        <p style="font-size: 18px; margin: 0 0 20px 0;">${t.easterEggSnakeScore || 'スコア: '}${gameState.score}</p>
        <div style="display: flex; gap: 10px; justify-content: center;">
            <button onclick="restartSnakeGame()" style="padding: 10px 20px; font-size: 16px; background: #2196F3; color: white; border: none; border-radius: 5px; cursor: pointer;">▶️ 再戦</button>
            <button onclick="closeSnakeModal()" style="padding: 10px 20px; font-size: 16px; background: #4CAF50; color: white; border: none; border-radius: 5px; cursor: pointer;">${t.close || '閉じる'}</button>
        </div>
    `;
    modal.querySelector('.modal-body').appendChild(gameOverDiv);
}

/**
 * スネークモーダルの閉じ方設定
 */
function setupSnakeModalCloseHandlers() {
    const modal = document.getElementById('snakeModal');
    if (!modal) return;
    
    // Escapeキー（グローバルハンドラーを使用）
    // 既にeaster-eggs.jsでグローバルハンドラーが設定されている場合はスキップ
    
    // モーダル外クリック
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeSnakeModal();
        }
    });
}

/**
 * スネークゲームの再戦
 */
function restartSnakeGame() {
    // ゲームオーバー表示を削除
    const gameOverDiv = document.getElementById('snakeGameOver');
    if (gameOverDiv) {
        gameOverDiv.remove();
    }
    
    // ゲームループを停止
    if (gameLoop) {
        cancelAnimationFrame(gameLoop);
        gameLoop = null;
    }
    
    // ゲーム状態をリセット
    const canvas = document.getElementById('snakeCanvas');
    if (!canvas || !gameState) return;
    
    // Canvasを再調整（グリッドに合わせる）
    const { adjustedWidth, adjustedHeight, tileCountX, tileCountY } = setupOptimizedCanvas(canvas, gameState.gridSize);
    
    // 中心位置を計算（グリッド座標系、0からtileCount-1の範囲）
    const centerX = Math.floor(tileCountX / 2);
    const centerY = Math.floor(tileCountY / 2);
    
    gameState = {
        snake: [{ x: centerX, y: centerY }],
        food: { x: Math.min(centerX + 5, tileCountX - 1), y: centerY },
        dx: 0,
        dy: 0,
        score: 0,
        gridSize: gameState.gridSize,
        tileCount: tileCountX,
        tileCountX,
        tileCountY,
        logicalWidth: adjustedWidth, // Canvasサイズ = 描画範囲（完全一致）
        logicalHeight: adjustedHeight, // Canvasサイズ = 描画範囲（完全一致）
        canvasWidth: adjustedWidth, // Canvasの実際のサイズ（グリッドに合わせて調整済み）
        canvasHeight: adjustedHeight, // Canvasの実際のサイズ（グリッドに合わせて調整済み）
        offsetX: 0, // オフセット不要（完全一致）
        offsetY: 0, // オフセット不要（完全一致）
        gameOver: false
    };
    
    // 初期描画
    render();
    
    // スコアをリセット
    updateScore();
    
    // ゲームループを再開
    lastTime = 0;
    gameLoop = requestAnimationFrame(update);
}

/**
 * スネークモーダルを閉じる
 */
function closeSnakeModal() {
    const modal = document.getElementById('snakeModal');
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
    
    // イベントリスナーを削除
    if (keyHandler) {
        document.removeEventListener('keydown', keyHandler);
        keyHandler = null;
    }
    
    if (window.snakeMove) {
        delete window.snakeMove;
    }
    
    // イースターエッグを終了
    if (window.finishEasterEgg) {
        window.finishEasterEgg();
    }
}

// グローバルに公開
if (typeof window !== 'undefined') {
    window.closeSnakeModal = closeSnakeModal;
    window.restartSnakeGame = restartSnakeGame;
}

