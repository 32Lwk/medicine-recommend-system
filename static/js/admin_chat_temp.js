    <script>
        // 繧ｰ繝ｭ繝ｼ繝舌Ν繧ｨ繝ｩ繝ｼ繝上Φ繝峨Λ繝ｼ
        window.addEventListener('error', function(event) {
            console.error('閥 Global error:', event.error);
            console.error('閥 Error message:', event.message);
            console.error('閥 Error at:', event.filename, 'line', event.lineno);
        });
        
        window.addEventListener('unhandledrejection', function(event) {
            console.error('閥 Unhandled promise rejection:', event.reason);
        });
        
        console.log('塘 Script loaded successfully');
        
        let currentSessionId = null;
        let allSessions = [];
        let currentDetailedDiagnosis = null; // 邂｡逅・PI縺九ｉ縺ｮ隧ｳ邏ｰ險ｺ譁ｭ・医せ繧ｳ繧｢蜀・ｨｳ蜷ｫ繧・・
        let socket = null;

        // 繝壹・繧ｸ隱ｭ縺ｿ霎ｼ縺ｿ譎ゅ・蛻晄悄蛹・
        document.addEventListener('DOMContentLoaded', function() {
            console.log('噫 Admin page loaded, initializing...');
            
            // 髢｢謨ｰ縺悟ｮ夂ｾｩ縺輔ｌ縺ｦ縺・ｋ縺狗｢ｺ隱・
            console.log('剥 Function check:');
            console.log('  - refreshAIStatus:', typeof refreshAIStatus);
            console.log('  - refreshQueue:', typeof refreshQueue);
            console.log('  - refreshSessionList:', typeof refreshSessionList);
            console.log('  - renderSessionList:', typeof renderSessionList);
            console.log('  - selectSession:', typeof selectSession);
            
            // 蛻晄悄繝・・繧ｿ隱ｭ縺ｿ霎ｼ縺ｿ・医お繝ｩ繝ｼ繝上Φ繝峨Μ繝ｳ繧ｰ莉倥″・・
            try {
                console.log('藤 Calling refreshAIStatus...');
                refreshAIStatus();
            } catch (error) {
                console.error('笶・refreshAIStatus error:', error);
            }
            
            try {
                console.log('藤 Calling refreshQueue...');
                refreshQueue();
            } catch (error) {
                console.error('笶・refreshQueue error:', error);
            }
            
            try {
                console.log('藤 Calling refreshSessionList...');
                refreshSessionList();
            } catch (error) {
                console.error('笶・refreshSessionList error:', error);
            }
            
            // 邂｡逅・・繧ｿ繝ｳ縺ｮ繧､繝吶Φ繝医Μ繧ｹ繝翫・
            document.getElementById('aiControlBtn').addEventListener('click', function() {
                document.getElementById('aiControlModal').style.display = 'block';
            });
            
            document.getElementById('systemStatusBtn').addEventListener('click', function() {
                document.getElementById('systemStatusModal').style.display = 'block';
                loadSystemStatus();
            });
            
            document.getElementById('monitoringBtn').addEventListener('click', function() {
                document.getElementById('monitoringModal').style.display = 'block';
                loadMonitoringData();
            });
            
            document.getElementById('medicineChatBtn').addEventListener('click', function() {
                document.getElementById('medicineChatModal').style.display = 'block';
            });
            
            document.getElementById('clearLogsBtn').addEventListener('click', function() {
                if (confirm('縺吶∋縺ｦ縺ｮ繝ｭ繧ｰ繧偵け繝ｪ繧｢縺励∪縺吶°・・)) {
                    clearAllLogs();
                }
            });
            
            document.getElementById('feedbackReportsBtn').addEventListener('click', function() {
                document.getElementById('feedbackReportsModal').style.display = 'block';
                loadFeedbackReports();
            });
            
            // 繝｢繝ｼ繝繝ｫ縺ｮ髢峨§繧九・繧ｿ繝ｳ
            document.querySelectorAll('.close').forEach(function(closeBtn) {
                closeBtn.addEventListener('click', function() {
                    this.closest('.admin-modal').style.display = 'none';
                });
            });
            
            // 繝｢繝ｼ繝繝ｫ螟悶け繝ｪ繝・け縺ｧ髢峨§繧・
            window.addEventListener('click', function(event) {
                if (event.target.classList.contains('admin-modal')) {
                    event.target.style.display = 'none';
                }
            });
            
            // 繝√Ε繝・ヨ蜈･蜉帙・蛻ｶ蠕｡
            const chatInput = document.getElementById('chat-input');
            chatInput.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = Math.min(this.scrollHeight, 100) + 'px';
                
                // 騾∽ｿ｡繝懊ち繝ｳ縺ｮ譛牙柑/辟｡蜉ｹ繧貞・繧頑崛縺・
                updateSendButtonState();
            });
            
            // 謇句虚譖ｴ譁ｰ縺ｮ縺ｿ: 閾ｪ蜍墓峩譁ｰ繧堤┌蜉ｹ蛹・
            let updateTimer = null;
            
            // 蛻晄悄繝・・繧ｿ隱ｭ縺ｿ霎ｼ縺ｿ
            function loadInitialData() {
                // 繧ｭ繝･繝ｼ縺ｨ繧ｻ繝・す繝ｧ繝ｳ諠・ｱ繧剃ｸ蠎ｦ縺ｫ譖ｴ譁ｰ
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
                    console.log('笨・Initial data loaded successfully');
                    renderQueue(queueData);
                    updateStats(queueData);
                    
                    // API縺ｯ {sessions: [...]} 縺ｮ蠖｢蠑上〒霑斐☆縺溘ａ縲‥ata.sessions 縺ｫ繧｢繧ｯ繧ｻ繧ｹ
                    const sessionsArray = sessionsData.sessions || (Array.isArray(sessionsData) ? sessionsData : []);
                    renderCurrentSession(sessionsArray.length > 0 ? sessionsArray[0] : null);
                    
                    // 繧ｻ繝・す繝ｧ繝ｳ荳隕ｧ繧よ峩譁ｰ
                    allSessions = sessionsArray;
                    renderSessionList(allSessions);
                    document.getElementById('total-sessions').textContent = allSessions.length;
                })
                .catch(error => {
                    console.error('笶・Initial data load error:', error);
                });
            }
            
            // 蛻晄悄繝・・繧ｿ隱ｭ縺ｿ霎ｼ縺ｿ
            loadInitialData();
        });

        // 謇句虚譖ｴ譁ｰ髢｢謨ｰ・医げ繝ｭ繝ｼ繝舌Ν繧ｹ繧ｳ繝ｼ繝暦ｼ・
        function manualRefresh() {
            // 繧ｭ繝･繝ｼ縺ｨ繧ｻ繝・す繝ｧ繝ｳ諠・ｱ繧剃ｸ蠎ｦ縺ｫ譖ｴ譁ｰ
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
                renderQueue(queueData);
                updateStats(queueData);
                
                // API縺ｯ {sessions: [...]} 縺ｮ蠖｢蠑上〒霑斐☆縺溘ａ縲‥ata.sessions 縺ｫ繧｢繧ｯ繧ｻ繧ｹ
                const sessionsArray = sessionsData.sessions || (Array.isArray(sessionsData) ? sessionsData : []);
                renderCurrentSession(sessionsArray.length > 0 ? sessionsArray[0] : null);
                
                // 繧ｻ繝・す繝ｧ繝ｳ荳隕ｧ繧よ峩譁ｰ
                allSessions = sessionsArray;
                renderSessionList(allSessions);
                document.getElementById('total-sessions').textContent = allSessions.length;
                
                showNotification('繝・・繧ｿ繧呈峩譁ｰ縺励∪縺励◆', 'success');
            })
            .catch(error => {
                console.error('Manual refresh error:', error);
                showNotification('譖ｴ譁ｰ繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆', 'error');
            });
        }

        function initializeSocket() {
            // WebSocket讖溯・縺ｯ邁｡邏蛹悶＠縲∝ｮ壽悄逧・↑API蜻ｼ縺ｳ蜃ｺ縺励↓髮・ｸｭ
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
            if (mode === 'admin') {
                fetch('/api/admin_mode', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(res => res.json())
                .then(data => {
                    showNotification(data.message || '阮ｬ蜑､蟶ｫ蟇ｾ蠢懊Δ繝ｼ繝峨↓蛻・ｊ譖ｿ縺医∪縺励◆');
                    refreshAIStatus && refreshAIStatus();
                    refreshQueue && refreshQueue();
                })
                .catch((error) => {
                    console.error('阮ｬ蜑､蟶ｫ蟇ｾ蠢廣PI繧ｨ繝ｩ繝ｼ:', error);
                    showNotification('騾壻ｿ｡繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆: ' + (error && error.message ? error.message : error), 'error');
                });
                return;
            }
            fetch('/api/main_ai_control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({mode: mode})
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    showNotification(`繧ｨ繝ｩ繝ｼ: ${data.error}`, 'error');
                } else {
                    showNotification(data.message || `AI閾ｪ蜍募ｿ懃ｭ斐ｒ${mode === 'on' ? 'ON' : 'OFF'}縺ｫ縺励∪縺励◆`);
                    refreshAIStatus();
                    refreshQueue();
                }
            })
            .catch(error => {
                showNotification(`繧ｨ繝ｩ繝ｼ: ${error.message}`, 'error');
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
                    
                    if (data.ai_auto_reply) {
                        statusElement.className = 'ai-status on';
                        statusText.textContent = '泙 AI閾ｪ蜍募ｿ懃ｭ念N';
                        headerStatusText.textContent = '泙 AI閾ｪ蜍募ｿ懃ｭ念N';
                        onBtn.disabled = true;
                        offBtn.disabled = false;
                    } else {
                        statusElement.className = 'ai-status off';
                        statusText.textContent = '閥 AI閾ｪ蜍募ｿ懃ｭ念FF';
                        headerStatusText.textContent = '閥 AI閾ｪ蜍募ｿ懃ｭ念FF';
                        onBtn.disabled = false;
                        offBtn.disabled = true;
                    }
                })
                .catch(error => {
                    showNotification('AI迥ｶ諷句叙蠕励お繝ｩ繝ｼ', 'error');
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
                })
                .catch(error => {
                    showNotification('繧ｭ繝･繝ｼ蜿門ｾ励お繝ｩ繝ｼ', 'error');
                });
            
            // 迴ｾ蝨ｨ縺ｮ繧ｻ繝・す繝ｧ繝ｳ諠・ｱ繧ょ叙蠕暦ｼ・I閾ｪ蜍募ｿ懃ｭ念N縺ｧ繧り｡ｨ遉ｺ・・
            fetch('/api/main_sessions', {
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            })
                .then(res => res.json())
                .then(data => {
                    // API縺ｯ {sessions: [...]} 縺ｮ蠖｢蠑上〒霑斐☆縺溘ａ縲‥ata.sessions 縺ｫ繧｢繧ｯ繧ｻ繧ｹ
                    const sessionsArray = data.sessions || (Array.isArray(data) ? data : []);
                    renderCurrentSession(sessionsArray.length > 0 ? sessionsArray[0] : null);
                })
                .catch(error => {
                    console.error('Current session error:', error);
                });
        }

        function renderQueue(queue) {
            const content = document.getElementById('manual-reply-queue');
            
            if (!Array.isArray(queue) || queue.length === 0) {
                content.innerHTML = `
                    <div class="empty-state">
                        <div>働</div>
                        <p>謇句虚霑比ｿ｡蠕・■縺ｮ繝｡繝・そ繝ｼ繧ｸ縺後≠繧翫∪縺帙ｓ</p>
                    </div>
                `;
                return;
            }
            
            let html = '';
            queue.forEach((item, index) => {
                // 蜊ｱ讖溷ｯｾ蠢懊そ繝・す繝ｧ繝ｳ縺九←縺・°繧偵メ繧ｧ繝・け
                const isCrisisItem = item.status === 'crisis_detected' || item.priority === 'high';
                const itemClass = isCrisisItem ? 'queue-item crisis-queue-item' : 'queue-item';
                const crisisBadge = isCrisisItem ? '<span class="crisis-badge">圷 邱頑･</span>' : '';
                const crisisKeywords = isCrisisItem && item.crisis_keywords ? 
                    `<div class="crisis-keywords" style="background: #ffebee; padding: 8px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #e74c3c; font-size: 0.9em; color: #e74c3c;">
                        <strong>讀懷・繧ｭ繝ｼ繝ｯ繝ｼ繝・</strong> ${item.crisis_keywords.join(', ')}
                    </div>` : '';
                
                html += `
                    <div class="${itemClass}" onclick="selectSession(event, '${item.session_id}', ${index})">
                        <div class="queue-header">
                            <span class="session-id">繧ｻ繝・す繝ｧ繝ｳ: ${item.session_id} ${crisisBadge}</span>
                            <span class="timestamp">${item.timestamp}</span>
                        </div>
                        <div class="user-message">
                            <strong>側 繝ｦ繝ｼ繧ｶ繝ｼ:</strong> ${item.user_message}
                        </div>
                        ${crisisKeywords}
                        <div class="reply-section">
                            <textarea class="reply-input" id="reply-${index}" placeholder="霑比ｿ｡繝｡繝・そ繝ｼ繧ｸ繧貞・蜉帙＠縺ｦ縺上□縺輔＞..."></textarea>
                            <button class="reply-btn" onclick="sendReply('${item.session_id}', ${index}, event)">豆 霑比ｿ｡騾∽ｿ｡</button>
                        </div>
                    </div>
                `;
            });
            
            content.innerHTML = html;
            
            // 蜊ｱ讖溷ｯｾ蠢懊そ繝・す繝ｧ繝ｳ縺ｮ謨ｰ繧偵き繧ｦ繝ｳ繝医＠縺ｦ陦ｨ遉ｺ
            const crisisCount = queue.filter(item => item.status === 'crisis_detected' || item.priority === 'high').length;
            const crisisCountElement = document.getElementById('crisis-count');
            if (crisisCountElement) {
                if (crisisCount > 0) {
                    crisisCountElement.textContent = `圷 邱頑･: ${crisisCount}莉ｶ`;
                    crisisCountElement.style.background = '#ffebee';
                    crisisCountElement.style.color = '#e74c3c';
                } else {
                    crisisCountElement.textContent = '';
                }
            }
        }

        function updateStats(queue) {
            document.getElementById('queue-count').textContent = Array.isArray(queue) ? queue.length : 0;
        }

        function renderCurrentSession(sessionData) {
            const content = document.getElementById('manual-reply-queue');
            
            // 譌｢蟄倥・繧ｭ繝･繝ｼ諠・ｱ繧剃ｿ晄戟
            let existingContent = content.innerHTML;
            
            // 迴ｾ蝨ｨ縺ｮ繧ｻ繝・す繝ｧ繝ｳ諠・ｱ繧定ｿｽ蜉
            if (sessionData && sessionData.messages && sessionData.messages.length > 0) {
                const currentSessionHtml = `
                    <div class="queue-item current-session" onclick="selectSession(event, '${sessionData.session_id}', 'current')">
                        <div class="queue-header">
                            <span class="session-id">導 迴ｾ蝨ｨ縺ｮ繧ｻ繝・す繝ｧ繝ｳ: ${sessionData.session_id}</span>
                            <span class="timestamp">${sessionData.last_activity}</span>
                            <span style="background: #28a745; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8em;">繧｢繧ｯ繝・ぅ繝・/span>
                        </div>
                        <div class="user-message">
                            <strong>町 譛譁ｰ繝｡繝・そ繝ｼ繧ｸ:</strong> ${sessionData.messages[sessionData.messages.length - 1]?.content || '縺ｪ縺・}
                        </div>
                        <div style="margin-top: 10px; font-size: 0.9em; color: #6c757d;">
                            繝｡繝・そ繝ｼ繧ｸ謨ｰ: ${sessionData.messages_count} | 繧ｻ繝・す繝ｧ繝ｳ譛牙柑: ${sessionData.session_active ? '笨・ : '笶・}
                        </div>
                    </div>
                `;
                
                // 迴ｾ蝨ｨ縺ｮ繧ｻ繝・す繝ｧ繝ｳ繧呈怙蛻昴↓陦ｨ遉ｺ
                content.innerHTML = currentSessionHtml + existingContent;
            }
        }

        function loadChatHistory(sessionId) {
            // 繝ｭ繝ｼ繝・ぅ繝ｳ繧ｰ陦ｨ遉ｺ
            const chatMessages = document.getElementById('chat-messages');
            chatMessages.innerHTML = `
                <div class="empty-state">
                    <div>売</div>
                    <p>繝√Ε繝・ヨ螻･豁ｴ繧定ｪｭ縺ｿ霎ｼ縺ｿ荳ｭ...</p>
                </div>
            `;
            
            // 繧ｻ繝・す繝ｧ繝ｳ繧ｿ繧､繝医Ν繧呈峩譁ｰ
            const session = allSessions.find(s => s.session_id === sessionId);
            if (session) {
                document.getElementById('chat-title').textContent = `${session.username} (${sessionId})`;
                // 繝ｦ繝ｼ繧ｶ繝ｼ螻樊ｧ繝懊ち繝ｳ繧定｡ｨ遉ｺ
                document.getElementById('userAttributesBtn').style.display = 'block';
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
                    
                    // API縺ｯ {sessions: [...]} 縺ｮ蠖｢蠑上〒霑斐☆縺溘ａ縲‥ata.sessions 縺ｫ繧｢繧ｯ繧ｻ繧ｹ
                    const sessionsArray = data.sessions || (Array.isArray(data) ? data : []);
                    
                    // 謖・ｮ壹＆繧後◆繧ｻ繝・す繝ｧ繝ｳID縺ｮ繝・・繧ｿ繧呈爾縺・
                    const targetSession = sessionsArray.find(session => session.session_id === sessionId) || null;
                    
                    if (targetSession && targetSession.messages && Array.isArray(targetSession.messages)) {
                        // 邂｡逅・・ｰら畑縺ｮ隧ｳ邏ｰ險ｺ譁ｭ繧剃ｿ晄戟・域耳螂ｨ阮ｬ縺斐→縺ｮscore/score_breakdown繧貞性繧・・
                        currentDetailedDiagnosis = targetSession.detailed_diagnosis || null;
                        renderChatMessages(targetSession.messages);
                    } else {
                        renderChatMessages([]);
                    }
                })
                .catch(error => {
                    console.error('Chat history error:', error);
                    showNotification('繧ｻ繝・す繝ｧ繝ｳ諠・ｱ蜿門ｾ励お繝ｩ繝ｼ', 'error');
                    renderChatMessages([]);
                });
        }

        // 繝ｦ繝ｼ繧ｶ繝ｼ螻樊ｧ諠・ｱ繝｢繝ｼ繝繝ｫ繧定｡ｨ遉ｺ
        function showUserAttributesModal() {
            if (!currentSessionId) {
                showNotification('繧ｻ繝・す繝ｧ繝ｳ縺碁∈謚槭＆繧後※縺・∪縺帙ｓ', 'error');
                return;
            }
            
            document.getElementById('userAttributesModal').style.display = 'block';
            loadUserAttributes(currentSessionId);
        }

        // 繝ｦ繝ｼ繧ｶ繝ｼ螻樊ｧ諠・ｱ繝｢繝ｼ繝繝ｫ繧帝哩縺倥ｋ
        function closeUserAttributesModal() {
            document.getElementById('userAttributesModal').style.display = 'none';
        }

        // 繝ｦ繝ｼ繧ｶ繝ｼ螻樊ｧ諠・ｱ繧定ｪｭ縺ｿ霎ｼ縺ｿ
        function loadUserAttributes(sessionId) {
            const content = document.getElementById('userAttributesContent');
            content.innerHTML = `
                <div class="loading" style="text-align: center; padding: 40px; color: #666;">
                    <div style="font-size: 2em; margin-bottom: 10px;">竢ｳ</div>
                    <p>隱ｭ縺ｿ霎ｼ縺ｿ荳ｭ...</p>
                </div>
            `;
            
            // 繝・ヰ繝・げ諠・ｱ繧貞・蜉・
            console.log('loadUserAttributes called with sessionId:', sessionId);
            console.log('allSessions:', allSessions);
            
            // 繧ｻ繝・す繝ｧ繝ｳ諠・ｱ縺九ｉ繝ｦ繝ｼ繧ｶ繝ｼ螻樊ｧ繧貞叙蠕・
            const session = allSessions.find(s => s.session_id === sessionId);
            console.log('Found session:', session);
            
            if (session) {
                const userInfo = session.user_info || {};
                const attributes = session.attributes || {};
                console.log('userInfo:', userInfo);
                console.log('attributes:', attributes);
                
                // userInfo縺ｨattributes繧偵・繝ｼ繧ｸ・・ttributes縺悟━蜈茨ｼ・
                const mergedUserInfo = { ...userInfo, ...attributes };
                console.log('mergedUserInfo:', mergedUserInfo);
                
                let html = `
                    <div style="margin-bottom: 25px; background: white;">
                        <div style="display: flex; align-items: center; margin-bottom: 20px; background: white;">
                            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; width: 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.5em; margin-right: 15px;">
                                側
                            </div>
                            <div style="background: white;">
                                <h4 style="color: #2c3e50; margin: 0 0 5px 0; font-size: 1.3em; background: white;">${session.username || '荳肴・'}</h4>
                                <p style="color: #666; margin: 0; font-size: 0.9em; background: white;">繧ｻ繝・す繝ｧ繝ｳID: ${sessionId.substring(0, 20)}...</p>
                            </div>
                        </div>
                    </div>
                `;
                
                if (Object.keys(mergedUserInfo).length > 0) {
                    html += `
                        <div style="margin-bottom: 25px; background: white;">
                            <h4 style="color: #2c3e50; margin-bottom: 20px; font-size: 1.2em; display: flex; align-items: center; background: white;">
                                <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-size: 0.8em;">側</span>
                                <span style="background: white;">繝ｦ繝ｼ繧ｶ繝ｼ螻樊ｧ</span>
                            </h4>
                            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 20px; border-radius: 12px; border-left: 4px solid #28a745;">
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    `;
                    
                    // 繝ｦ繝ｼ繧ｶ繝ｼ諠・ｱ繧定｡ｨ遉ｺ・郁ｿｽ蜉雉ｪ蝠上→蜷後§鬆・岼・・
                    if (mergedUserInfo.age) {
                        html += `
                            <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="color: #28a745; font-weight: bold; margin-bottom: 5px; background: white;">獅 蟷ｴ鮨｢</div>
                                <div style="color: #2c3e50; font-size: 1.1em; background: white;">${mergedUserInfo.age}豁ｳ</div>
                            </div>
                        `;
                    }
                    if (mergedUserInfo.gender) {
                        html += `
                            <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="color: #28a745; font-weight: bold; margin-bottom: 5px; background: white;">笞･ 諤ｧ蛻･</div>
                                <div style="color: #2c3e50; font-size: 1.1em; background: white;">${mergedUserInfo.gender}</div>
                            </div>
                        `;
                    }
                    // 螯雁ｨ繝ｻ謗井ｹｳ迥ｶ諷具ｼ亥･ｳ諤ｧ縺ｮ蝣ｴ蜷医・縺ｿ陦ｨ遉ｺ・・
                    if (mergedUserInfo.gender === '螂ｳ諤ｧ' || mergedUserInfo.gender === '螂ｳ') {
                        if (mergedUserInfo.pregnant !== undefined && mergedUserInfo.pregnant !== null) {
                            const pregnancyStatus = mergedUserInfo.pregnant ? '螯雁ｨ荳ｭ' : '螯雁ｨ縺励※縺・↑縺・;
                            html += `
                                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                    <div style="color: #28a745; font-weight: bold; margin-bottom: 5px; background: white;">､ｱ 螯雁ｨ迥ｶ諷・/div>
                                    <div style="color: #2c3e50; font-size: 1.1em; background: white;">${pregnancyStatus}</div>
                                </div>
                            `;
                        }
                        if (mergedUserInfo.breastfeeding !== undefined && mergedUserInfo.breastfeeding !== null) {
                            const breastfeedingStatus = mergedUserInfo.breastfeeding ? '謗井ｹｳ荳ｭ' : '謗井ｹｳ縺励※縺・↑縺・;
                            html += `
                                <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                    <div style="color: #28a745; font-weight: bold; margin-bottom: 5px; background: white;">詐 謗井ｹｳ迥ｶ諷・/div>
                                    <div style="color: #2c3e50; font-size: 1.1em; background: white;">${breastfeedingStatus}</div>
                                </div>
                            `;
                        }
                    }
                    // 繧｢繝ｬ繝ｫ繧ｮ繝ｼ
                    if (mergedUserInfo.allergies && mergedUserInfo.allergies.length > 0) {
                        const allergyText = Array.isArray(mergedUserInfo.allergies) ? mergedUserInfo.allergies.join(', ') : mergedUserInfo.allergies;
                        html += `
                            <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="color: #28a745; font-weight: bold; margin-bottom: 5px; background: white;">笞・・繧｢繝ｬ繝ｫ繧ｮ繝ｼ</div>
                                <div style="color: #2c3e50; font-size: 1.1em; background: white;">${allergyText}</div>
                            </div>
                        `;
                    }
                    // 迴ｾ蝨ｨ譛咲畑荳ｭ縺ｮ阮ｬ・亥憶逕ｨ阮ｬ・・
                    const medicationText = (mergedUserInfo.current_medications && mergedUserInfo.current_medications.length > 0) 
                        ? (Array.isArray(mergedUserInfo.current_medications) ? mergedUserInfo.current_medications.join(', ') : mergedUserInfo.current_medications)
                        : '縺ｪ縺・;
                    html += `
                        <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="color: #28a745; font-weight: bold; margin-bottom: 5px; background: white;">抽 蜑ｯ逕ｨ阮ｬ・育樟蝨ｨ譛咲畑荳ｭ縺ｮ阮ｬ・・/div>
                            <div style="color: #2c3e50; font-size: 1.1em; background: white;">${medicationText}</div>
                        </div>
                    `;
                    // 逞・憾縺ｮ謖∫ｶ壽悄髢・
                    if (mergedUserInfo.symptom_duration_days !== undefined && mergedUserInfo.symptom_duration_days !== null) {
                        let durationText = '';
                        const days = mergedUserInfo.symptom_duration_days;
                        const today = new Date();
                        const startDate = new Date(today.getTime() - (days * 24 * 60 * 60 * 1000));
                        const dateStr = startDate.getFullYear() + '/' + 
                                      String(startDate.getMonth() + 1).padStart(2, '0') + '/' + 
                                      String(startDate.getDate()).padStart(2, '0');
                        
                        if (days === 0) {
                            durationText = '莉頑律縺九ｉ';
                        } else if (days === 1) {
                            durationText = '譏ｨ譌･縺九ｉ';
                        } else if (days < 7) {
                            durationText = `${days}譌･蜑阪°繧荏;
                        } else if (days < 30) {
                            const weeks = Math.floor(days / 7);
                            durationText = `${weeks}騾ｱ髢灘燕縺九ｉ`;
                        } else {
                            const months = Math.floor(days / 30);
                            durationText = `${months}繝ｶ譛亥燕縺九ｉ`;
                        }
                        
                        durationText += ` (${dateStr})`;
                        
                        html += `
                            <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <div style="color: #28a745; font-weight: bold; margin-bottom: 5px; background: white;">竢ｰ 逞・憾縺ｮ謖∫ｶ壽悄髢・/div>
                                <div style="color: #2c3e50; font-size: 1.1em; background: white;">${durationText}</div>
                            </div>
                        `;
                    }
                    // 譌｢蠕逞・
                    const historyText = (mergedUserInfo.medical_history && mergedUserInfo.medical_history.length > 0) 
                        ? (Array.isArray(mergedUserInfo.medical_history) ? mergedUserInfo.medical_history.join(', ') : mergedUserInfo.medical_history)
                        : '縺ｪ縺・;
                    html += `
                        <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="color: #28a745; font-weight: bold; margin-bottom: 5px; background: white;">唱 譌｢蠕逞・/div>
                            <div style="color: #2c3e50; font-size: 1.1em; background: white;">${historyText}</div>
                        </div>
                    `;
                    // 縺昴・莉紋ｼ昴∴縺溘＞縺薙→
                    const otherInfoText = mergedUserInfo.other_info || '縺ｪ縺・;
                    html += `
                        <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                            <div style="color: #28a745; font-weight: bold; margin-bottom: 5px; background: white;">統 縺昴・莉紋ｼ昴∴縺溘＞縺薙→</div>
                            <div style="color: #2c3e50; font-size: 1.1em; background: white;">${otherInfoText}</div>
                        </div>
                    `;
                    
                    html += `</div></div></div>`;
                } else {
                    html += `
                        <div style="margin-bottom: 25px; background: white;">
                            <h4 style="color: #2c3e50; margin-bottom: 20px; font-size: 1.2em; display: flex; align-items: center; background: white;">
                                <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 10px; font-size: 0.8em;">側</span>
                                <span style="background: white;">繝ｦ繝ｼ繧ｶ繝ｼ螻樊ｧ</span>
                            </h4>
                            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 30px; border-radius: 12px; border-left: 4px solid #ffc107; text-align: center;">
                                <div style="font-size: 3em; margin-bottom: 15px; background: transparent;">統</div>
                                <p style="color: #666; margin: 0; font-size: 1.1em; background: white; padding: 10px; border-radius: 8px;">繝ｦ繝ｼ繧ｶ繝ｼ螻樊ｧ諠・ｱ縺ｯ縺ｾ縺蜈･蜉帙＆繧後※縺・∪縺帙ｓ</p>
                            </div>
                        </div>
                    `;
                }
                
                content.innerHTML = html;
            } else {
                content.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #e74c3c; background: white;">
                        <div style="font-size: 3em; margin-bottom: 15px; background: white;">笶・/div>
                        <p style="font-size: 1.1em; background: white;">繧ｻ繝・す繝ｧ繝ｳ諠・ｱ縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ</p>
                    </div>
                `;
            }
        }

        // HTML繧ｳ繝ｳ繝・Φ繝・↓繧ｹ繧ｳ繧｢繝ｪ繝ｳ繧ｰ繧定ｿｽ蜉・育ｮ｡逅・・判髱｢逕ｨ・・
        function addScoringToHtmlContent(htmlContent, medicines) {
            if (!medicines || medicines.length === 0) {
                return htmlContent;
            }
            
            let modifiedContent = htmlContent;
            
            // 蜷・現阮ｬ蜩√・繧ｹ繧ｳ繧｢繝ｪ繝ｳ繧ｰ繧定ｿｽ蜉・域耳螂ｨ蛹ｻ阮ｬ蜩√そ繧ｯ繧ｷ繝ｧ繝ｳ縺ｮ縺ｿ・・
            medicines.forEach((medicine, index) => {
                if (medicine.score !== undefined) {
                    const scoreClass = medicine.score >= 0.7 ? 'admin-score-high' : medicine.score >= 0.5 ? 'admin-score-medium' : 'admin-score-low';
                    const scoreText = medicine.score >= 0.7 ? '鬮・ : medicine.score >= 0.5 ? '荳ｭ' : '菴・;
                    const scoringHtml = `<span class="admin-score-display ${scoreClass}" style="font-size: 0.75em;">投 譛驕ｩ蠎ｦ: ${(medicine.score * 100).toFixed(0)}% (${scoreText})</span>`;
                    
                    // 謗ｨ螂ｨ蛹ｻ阮ｬ蜩√そ繧ｯ繧ｷ繝ｧ繝ｳ蜀・・蛹ｻ阮ｬ蜩∝錐縺ｮ蠕後↓繧ｹ繧ｳ繧｢繝ｪ繝ｳ繧ｰ繧定ｿｽ蜉
                    const medicineName = medicine.product_name || '';
                    if (medicineName) {
                        // 隧ｲ蠖楢｡後↓譌｢縺ｫ譛驕ｩ蠎ｦ縺御ｻ倥＞縺ｦ縺・↑縺・ｴ蜷医・縺ｿ霑ｽ蜉・亥酔荳陦悟・縺ｧ蛻､螳夲ｼ・
                        const namePattern = new RegExp(`(醇 ${index + 1}菴・\\s*${medicineName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})(?![^\\n]*譛驕ｩ蠎ｦ:)`, 'g');
                        modifiedContent = modifiedContent.replace(namePattern, `$1${scoringHtml}`);
                    }
                }
            });
            
            return modifiedContent;
        }

        // 笘・・笘・addScoringToMedicines 髢｢謨ｰ縺ｯ蜑企勁・亥虚逧ЗTML逕滓・縺ｫ螟画峩・・笘・・笘・

        function renderChatMessages(messages) {
            const chatMessages = document.getElementById('chat-messages');
            
            if (!messages || messages.length === 0) {
                chatMessages.innerHTML = `
                    <div class="empty-state">
                        <div>町</div>
                        <p>繝｡繝・そ繝ｼ繧ｸ螻･豁ｴ縺後≠繧翫∪縺帙ｓ</p>
                    </div>
                `;
                return;
            }
            
            console.log('鐙 Rendering chat messages:', messages.length, 'messages');
            
            let html = '';
            messages.forEach((msg, index) => {
                const messageClass = msg.type === 'user' ? 'user' : 'bot';
                let indicator = '';
                let timestamp = '';
                
                console.log(`Message ${index}:`, msg);
                
                // 騾∽ｿ｡譎ょ綾繧定ｿｽ蜉
                if (msg.timestamp) {
                    const date = new Date(msg.timestamp);
                    const timeStr = date.toLocaleTimeString('ja-JP', { 
                        hour: '2-digit', 
                        minute: '2-digit',
                        second: '2-digit'
                    });
                    timestamp = `<div class="message-timestamp" style="font-size: 0.7em; color: #666; margin-top: 4px; text-align: ${messageClass === 'user' ? 'left' : 'right'};">${timeStr}</div>`;
                } else {
                    // 繧ｿ繧､繝繧ｹ繧ｿ繝ｳ繝励′縺ｪ縺・ｴ蜷医・迴ｾ蝨ｨ譎ょ綾繧剃ｽｿ逕ｨ
                    const now = new Date();
                    const timeStr = now.toLocaleTimeString('ja-JP', { 
                        hour: '2-digit', 
                        minute: '2-digit',
                        second: '2-digit'
                    });
                    timestamp = `<div class="message-timestamp" style="font-size: 0.7em; color: #666; margin-top: 4px; text-align: ${messageClass === 'user' ? 'left' : 'right'};">${timeStr}</div>`;
                }
                
                // 邂｡逅・判髱｢逕ｨ縺ｮ繧､繝ｳ繧ｸ繧ｱ繝ｼ繧ｿ繝ｼ・夊脈蜑､蟶ｫ隕也せ縺ｧ陦ｨ遉ｺ
                if (msg.type === 'bot') {
                if (msg.crisis_support) {
                    indicator = '<span class="crisis-indicator" style="color: #e74c3c; font-weight: bold; background: #ffebee; padding: 2px 6px; border-radius: 4px;">圷 蜊ｱ讖溷ｯｾ蠢・/span><br>';
                    } else if (msg.manual_reply) {
                        indicator = '<span class="manual-reply-indicator">側 阮ｬ蜑､蟶ｫ霑比ｿ｡</span><br>';
                    } else {
                        indicator = '<span class="ai-indicator">､・AI霑比ｿ｡</span><br>';
                    }
                } else if (msg.type === 'user') {
                    indicator = '<span class="user-indicator" style="color: #007bff; font-weight: bold;">側 繝ｦ繝ｼ繧ｶ繝ｼ</span><br>';
                }
                
                let messageContentHtml = '';

                // 蜊ｱ讖溷ｯｾ蠢懊Γ繝・そ繝ｼ繧ｸ縺ｮ迚ｹ蛻･陦ｨ遉ｺ
                if (msg.crisis_support) {
                    messageContentHtml += `<div class="crisis-message-highlight">`;
                    messageContentHtml += `<h4 style="color: #e74c3c; margin-bottom: 10px;">圷 蜊ｱ讖溷ｯｾ蠢懊Γ繝・そ繝ｼ繧ｸ</h4>`;
                    messageContentHtml += `<p><strong>繧ｿ繧､繝医Ν:</strong> ${msg.crisis_title || '縺ゅ↑縺溘・豌玲戟縺｡繧貞､ｧ蛻・↓諤昴▲縺ｦ縺・∪縺・}</p>`;
                    messageContentHtml += `<p><strong>繝｡繝・そ繝ｼ繧ｸ:</strong> ${msg.content || '莉翫√→縺ｦ繧ゅ▽繧峨＞迥ｶ豕√°繧ゅ＠繧後∪縺帙ｓ縲・}</p>`;
                    
                    if (msg.resources && msg.resources.length > 0) {
                        messageContentHtml += `<h5 style="color: #e74c3c; margin-top: 15px;">逶ｸ隲・・諠・ｱ:</h5>`;
                        msg.resources.forEach(resource => {
                            messageContentHtml += `<div style="background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #e74c3c;">`;
                            messageContentHtml += `<strong>${resource.name}</strong><br>`;
                            messageContentHtml += `<small>${resource.organization}</small><br>`;
                            if (resource.phone) messageContentHtml += `到 ${resource.phone}<br>`;
                            if (resource.line) messageContentHtml += `町 <a href="${resource.line}" target="_blank">LINE縺ｧ逶ｸ隲・☆繧・/a><br>`;
                            if (resource.line_qr) messageContentHtml += `導 <img src="${resource.line_qr}" alt="LINE QR繧ｳ繝ｼ繝・ style="width: 80px; height: 80px; border: 1px solid #ddd; border-radius: 4px; margin: 5px 0;"><br>`;
                            if (resource.website) messageContentHtml += `倹 <a href="${resource.website}" target="_blank">繧ｦ繧ｧ繝悶し繧､繝・/a><br>`;
                            if (resource.hours) messageContentHtml += `竢ｰ ${resource.hours}<br>`;
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
                // 笘・・笘・謗ｨ螂ｨ蛹ｻ阮ｬ蜩√Γ繝・そ繝ｼ繧ｸ縺ｮ蛻､螳夲ｼ育ｰ｡邏蛹厄ｼ・笘・・笘・
                const isMedicineRecommendation = (msg) => {
                    // 繝・ヰ繝・げ繝ｭ繧ｰ
                    console.log('剥 Message analysis:', {
                        type: msg.type,
                        hasDiagnosis: !!(msg.diagnosis && msg.diagnosis.recommended_medicines),
                        hasContent: !!(msg.content && msg.content.includes('謗ｨ螂ｨ蛹ｻ阮ｬ蜩・)),
                        hasContentHtml: !!(msg.content && msg.content.includes('<div class="recommendation-result">')),
                        hasTrophy: !!(msg.content && msg.content.includes('醇'))
                    });
                    
                    return msg.type === 'bot' && (
                        (msg.diagnosis && msg.diagnosis.recommended_medicines) ||
                        (msg.content && (
                            msg.content.includes('謗ｨ螂ｨ蛹ｻ阮ｬ蜩・) ||
                            msg.content.includes('<div class="recommendation-result">') ||
                            msg.content.includes('醇')
                        ))
                    );
                };

                if (isMedicineRecommendation(msg)) {
                    // 隧ｳ邏ｰ險ｺ譁ｭ・育ｮ｡逅・・髄縺托ｼ峨ｒ蜆ｪ蜈・
                    const adminDiag = (currentDetailedDiagnosis && currentDetailedDiagnosis.session_id === currentSessionId && Array.isArray(currentDetailedDiagnosis.recommended_medicines))
                        ? currentDetailedDiagnosis
                        : (msg.diagnosis || {});
                    // 邂｡逅・・畑縺ｫ蜀肴緒逕ｻ縺ｧ縺阪ｋ謗ｨ螂ｨ蛹ｻ阮ｬ蜩√′蟄伜惠縺吶ｋ縺・
                    const hasAdminDiagMeds = !!(adminDiag && Array.isArray(adminDiag.recommended_medicines) && adminDiag.recommended_medicines.length > 0);

                    messageContentHtml += `<div class="recommendation-result">`;
                    messageContentHtml += `<h4 style="color: #1976d2; border-bottom: 2px solid #1976d2; padding-bottom: 8px;">剥 逞・憾蛻・梵邨先棡</h4>`;
                    
                    if (adminDiag.symptoms && adminDiag.symptoms.length > 0) {
                        messageContentHtml += `<p><strong>謗ｨ貂ｬ縺輔ｌ繧狗裸迥ｶ:</strong> ${adminDiag.symptoms.join(', ')}</p>`;
                    }
                    if (adminDiag.medicine_type) {
                        messageContentHtml += `<p><strong>蛹ｻ阮ｬ蜩√・遞ｮ鬘・</strong> ${adminDiag.medicine_type}</p>`;
                    }

                    messageContentHtml += `<div style="background: #e8f5e9; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #4caf50;">`;
                    messageContentHtml += `<h4 style="color: #2e7d32; margin-top: 0;">抽 謗ｨ螂ｨ蛹ｻ阮ｬ蜩・/h4>`;

                    if (adminDiag.recommended_medicines && adminDiag.recommended_medicines.length > 0) {
                        adminDiag.recommended_medicines.forEach((medicine, medIndex) => {
                            messageContentHtml += `<div class="medicine-item" style="padding: 10px 0; margin: 10px 0; border-bottom: 1px solid #ddd;">`;
                            messageContentHtml += `<h5 style="margin: 0 0 10px 0;">醇 ${medIndex + 1}菴・ ${escapeHtml(medicine.product_name || medicine.name || 'N/A')}`;

                            // --- 隧ｳ邏ｰ繧ｹ繧ｳ繧｢繝懊ち繝ｳ繧定ｿｽ蜉 ---
                            if (medicine.score !== undefined) {
                                const medicineId = `medicine_${medIndex + 1}`;
                                messageContentHtml += `<button class="score-detail-btn" onclick="showScoreModal('${medicineId}', ${medIndex})" style="margin-left: 10px; padding: 4px 8px; font-size: 0.7em; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background-color 0.3s;">投 隧ｳ邏ｰ繧ｹ繧ｳ繧｢</button>`;
                            }

                            messageContentHtml += `<span style="color: #666; font-size: 0.9em;"> (${escapeHtml(medicine.manufacturer || '')})</span></h5>`;

                            // --- 繧ｹ繧ｳ繧｢繝ｪ繝ｳ繧ｰ繝ｩ繝吶Ν縺ｨ繝・・繝ｫ繝√ャ繝暦ｼ育ｰ｡逡･陦ｨ遉ｺ・・---
                            if (medicine.score !== undefined) {
                                const score = medicine.score;
                                const scoreClass = score >= 0.7 ? 'admin-score-high' : score >= 0.5 ? 'admin-score-medium' : 'admin-score-low';
                                const scoreText = score >= 0.7 ? '鬮・ : score >= 0.5 ? '荳ｭ' : '菴・;
                                const breakdown = medicine.scores || medicine.score_breakdown || {};

                                // 繧ｹ繧ｳ繧｢險育ｮ励・繝ｫ繝代・
                                const pct = (v) => {
                                    if (v === undefined || v === null || isNaN(v)) return 0;
                                    return Math.max(0, Math.min(100, Math.round(v * 100)));
                                };
                                const riskToPct = (v) => {
                                    if (v === undefined || v === null || isNaN(v)) return 100;
                                    return Math.max(0, Math.min(100, Math.round((1 + v) * 100)));
                                };

                                // 蜷・せ繧ｳ繧｢謚ｽ蜃ｺ
                                const symptom = breakdown.symptom_match ?? breakdown.symptom_match_score ?? 0;
                                const efficacy = breakdown.efficacy_specificity ?? breakdown.efficacy_specificity_score ?? 0;
                                const age = breakdown.age_fit ?? breakdown.age_suitability_score ?? 0;
                                const usage = breakdown.usage_convenience ?? breakdown.dosage_convenience_score ?? 0;
                                const sideRisk = breakdown.side_effect_risk ?? breakdown.side_effect_risk_score ?? 0;
                                const interRisk = breakdown.interaction_risk ?? breakdown.interaction_risk_score ?? 0;

                                messageContentHtml += `<span class="admin-score-display ${scoreClass}" style="font-size: 0.75em;">投 譛驕ｩ蠎ｦ: ${(score * 100).toFixed(0)}% (${scoreText})</span>`;
                            }

                            messageContentHtml += `<span style="color: #666; font-size: 0.9em;"> (${escapeHtml(medicine.manufacturer || '')})</span></h5>`;
                            
                            if (medicine.explanation || medicine.reason) {
                                messageContentHtml += `<p style="margin: 5px 0;"><strong>謗ｨ螂ｨ逅・罰:</strong> ${escapeHtml(medicine.explanation || medicine.reason)}</p>`;
                            }
                            if (medicine.age_restriction) {
                                messageContentHtml += `<p style="margin: 5px 0;"><strong>蟷ｴ鮨｢蛻ｶ髯・</strong> ${escapeHtml(medicine.age_restriction)}</p>`;
                            }
                            if (medicine.efficacy) {
                                messageContentHtml += `<p style="margin: 5px 0;"><strong>蜉ｹ閭ｽ蜉ｹ譫・</strong> ${escapeHtml(medicine.efficacy.substring(0,100))}...</p>`;
                            }
                            messageContentHtml += `</div>`;
                        });
                    } else {
                        messageContentHtml += "<p>驕ｩ蛻・↑蛹ｻ阮ｬ蜩√′隕九▽縺九ｊ縺ｾ縺帙ｓ縺ｧ縺励◆縲・/p>";
                    }
                    messageContentHtml += `</div>`;

                    // 菴ｿ逕ｨ荳翫・豕ｨ諢上∝現蟶ｫ逶ｸ隲・↑縺ｩ
                    if (adminDiag.usage_notes) {
                        messageContentHtml += `<div style="background: #fff3e0; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #ff9800;">
                            <h4 style="color: #e65100; margin-top: 0;">笞・・菴ｿ逕ｨ荳翫・豕ｨ諢・/h4>
                            <div class="caution-content" style="white-space: pre-wrap;">${escapeHtml(adminDiag.usage_notes)}</div>
                        </div>`;
                    }
                    if (adminDiag.doctor_consultation) {
                        messageContentHtml += `<div style="background: #ffebee; padding: 20px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #f44336;">
                            <h4 style="color: #c62828; margin-top: 0;">唱 蛹ｻ蟶ｫ縺ｮ蜿苓ｨｺ縺悟ｿ・ｦ√↑蝣ｴ蜷・/h4>
                            <div class="advice-content" style="white-space: pre-wrap;">${escapeHtml(adminDiag.doctor_consultation)}</div>
                        </div>`;
                    }
                    if (adminDiag.additional_questions && adminDiag.additional_questions.length > 0) {
                        messageContentHtml += `<div style="background: #e8f5e9; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #4caf50;">
                            <h4 style="color: #388e3c; margin-top: 0;">笶・霑ｽ蜉縺ｧ縺贋ｼｺ縺・＠縺溘＞縺薙→</h4>
                            <ul>${adminDiag.additional_questions.map(q => `<li>${escapeHtml(q)}</li>`).join('')}</ul>
                        </div>`;
                    }

                    messageContentHtml += `</div>`;

                    // msg.content縺ｫHTML縺悟性縺ｾ繧後※縺・ｋ蝣ｴ蜷医・縲√・繧ｿ繝ｳ繧定ｿｽ蜉縺励※縺九ｉ陦ｨ遉ｺ
                    // 縺溘□縺励∫ｮ｡逅・・畑縺ｮ蜀肴緒逕ｻ・・asAdminDiagMeds・峨′蜿ｯ閭ｽ縺ｪ蝣ｴ蜷医・荳頑嶌縺阪＠縺ｪ縺・
                    if (!hasAdminDiagMeds && msg.content && msg.content.includes('<div class="recommendation-result">')) {
                        let modifiedContent = msg.content;
                        
                        // 隧ｳ邏ｰ險ｺ譁ｭ・育ｮ｡逅・・髄縺托ｼ峨ｒ蜆ｪ蜈・
                        const adminDiag = (currentDetailedDiagnosis && currentDetailedDiagnosis.session_id === currentSessionId && Array.isArray(currentDetailedDiagnosis.recommended_medicines))
                            ? currentDetailedDiagnosis
                            : (msg.diagnosis || {});
                        
                        if (adminDiag && adminDiag.recommended_medicines) {
                            // 蜷・現阮ｬ蜩√・繧ｹ繧ｳ繧｢繝ｪ繝ｳ繧ｰ繧定ｿｽ蜉
                            adminDiag.recommended_medicines.forEach((medicine, index) => {
                                if (medicine.score !== undefined) {
                                    // 隧ｳ邏ｰ繧ｹ繧ｳ繧｢繝懊ち繝ｳ繧定ｿｽ蜉
                                    const medicineId = `medicine_${index + 1}`;
                                    const scoreButton = `<button class="score-detail-btn" onclick="showScoreModal('${medicineId}', ${index})" style="margin-left: 10px; padding: 4px 8px; font-size: 0.7em; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; transition: background-color 0.3s;">投 隧ｳ邏ｰ繧ｹ繧ｳ繧｢</button>`;
                                    
                                    // 謗ｨ螂ｨ蛹ｻ阮ｬ蜩√そ繧ｯ繧ｷ繝ｧ繝ｳ蜀・・蛹ｻ阮ｬ蜩∝錐縺ｮ蠕後↓繝懊ち繝ｳ繧定ｿｽ蜉
                                    const medicineName = medicine.product_name || medicine.name || '';
                                    if (medicineName) {
                                        // 隧ｲ蠖楢｡後↓譌｢縺ｫ繝懊ち繝ｳ縺御ｻ倥＞縺ｦ縺・↑縺・ｴ蜷医・縺ｿ霑ｽ蜉・亥酔荳陦悟・縺ｧ蛻､螳夲ｼ・
                                        const namePattern = new RegExp(`(醇 ${index + 1}菴・\\s*${medicineName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})(?![^\\n]*隧ｳ邏ｰ繧ｹ繧ｳ繧｢)`, 'g');
                                        modifiedContent = modifiedContent.replace(namePattern, `$1${scoreButton}`);
                                    }
                                }
                            });
                        }
                        
                        // 謖ｿ蜈･縺梧・蜉溘＠縺溷ｴ蜷医・縺ｿ鄂ｮ縺肴鋤縺茨ｼ亥ｰ代↑縺上→繧・縺､縺ｮ繝懊ち繝ｳ縺悟・縺｣縺ｦ縺・ｋ縺具ｼ・
                        if (modifiedContent.includes('score-detail-btn')) {
                            messageContentHtml = modifiedContent;
                        }
                    } else if (!hasAdminDiagMeds) {
                        // 邂｡逅・・畑縺ｮ蜀肴緒逕ｻ縺後〒縺阪↑縺・ｴ蜷医・縺ｿ縲［sg.content繧偵◎縺ｮ縺ｾ縺ｾ菴ｿ逕ｨ
                        messageContentHtml = msg.content || '';
                    }

                // 笘・・笘・騾壼ｸｸ縺ｮ繝・く繧ｹ繝医Γ繝・そ繝ｼ繧ｸ 笘・・笘・
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
                
                // 繝｡繝・そ繝ｼ繧ｸ蜈ｨ菴薙・HTML逕滓・
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
            console.log('笨・Chat messages rendered');
            
            // 繧ｹ繧ｯ繝ｭ繝ｼ繝ｫ繧呈怙荳矩Κ縺ｫ
            setTimeout(() => {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 100);
        }
        
        // HTML繧ｨ繧ｹ繧ｱ繝ｼ繝鈴未謨ｰ・域里縺ｫ荳企Κ縺ｧ螳夂ｾｩ貂医∩・・
        // function escapeHtml(text) {
        //     const div = document.createElement('div');
        //     div.textContent = text;
        //     return div.innerHTML;
        // }
        
        // AI邂｡逅・ｩ溯・
        function setAIMode(mode) {
            fetch('/admin/ai_control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({mode: mode})
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    // 謌仙粥騾夂衍
                    const notification = document.createElement('div');
                    notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #4caf50; color: white; padding: 15px 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); z-index: 10000; animation: slideIn 0.3s ease-out;';
                    notification.innerHTML = `<strong>笨・${data.message}</strong>`;
                    document.body.appendChild(notification);
                    
                    setTimeout(() => {
                        notification.remove();
                    }, 3000);
                    
                    // 繝｢繝ｼ繝繝ｫ繧帝哩縺倥ｋ
                    document.getElementById('aiControlModal').style.display = 'none';
                } else {
                    alert('繧ｨ繝ｩ繝ｼ: ' + (data.message || '荳肴・縺ｪ繧ｨ繝ｩ繝ｼ'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('騾壻ｿ｡繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆: ' + error.message);
            });
        }
        
        // 繧ｷ繧ｹ繝・Β迥ｶ豕∝叙蠕・
        function loadMonitoringData() {
            // 繧｢繧ｯ繧ｻ繧ｹ邨ｱ險医・隱ｭ縺ｿ霎ｼ縺ｿ
            fetch('/admin/access_stats')
            .then(response => response.json())
            .then(data => {
                const accessStats = document.getElementById('accessStats');
                accessStats.innerHTML = `
                    <p style="color: #333333;"><strong>邱上い繧ｯ繧ｻ繧ｹ謨ｰ:</strong> ${data.total_accesses || 0}</p>
                    <p style="color: #333333;"><strong>蟷ｳ蝮・Ξ繧ｹ繝昴Φ繧ｹ譎る俣:</strong> ${(data.avg_response_time || 0).toFixed(2)}ms</p>
                    <p style="color: #333333;"><strong>譛邨よ峩譁ｰ:</strong> ${new Date().toLocaleString('ja-JP')}</p>
                `;
            })
            .catch(error => {
                document.getElementById('accessStats').innerHTML = '<p style="color: red;">繧ｨ繝ｩ繝ｼ: 繝・・繧ｿ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ螟ｱ謨励＠縺ｾ縺励◆</p>';
            });

            // 繝代ヵ繧ｩ繝ｼ繝槭Φ繧ｹ邨ｱ險医・隱ｭ縺ｿ霎ｼ縺ｿ
            fetch('/admin/performance_stats')
            .then(response => response.json())
            .then(data => {
                const performanceStats = document.getElementById('performanceStats');
                performanceStats.innerHTML = `
                    <p style="color: #333333;"><strong>邱上Μ繧ｯ繧ｨ繧ｹ繝域焚:</strong> ${data.total_requests || 0}</p>
                    <p style="color: #333333;"><strong>蟷ｳ蝮・Ξ繧ｹ繝昴Φ繧ｹ譎る俣:</strong> ${(data.avg_response_time || 0).toFixed(2)}ms</p>
                    <p style="color: #333333;"><strong>蟷ｳ蝮・Γ繝｢繝ｪ菴ｿ逕ｨ邇・</strong> ${(data.avg_memory_usage || 0).toFixed(1)}%</p>
                    <p style="color: #333333;"><strong>蟷ｳ蝮④PU菴ｿ逕ｨ邇・</strong> ${(data.avg_cpu_usage || 0).toFixed(1)}%</p>
                    <p style="color: #333333;"><strong>繧ｭ繝｣繝・す繝･繝偵ャ繝育紫:</strong> ${(data.avg_cache_hit_rate || 0).toFixed(1)}%</p>
                    <p style="color: #333333;"><strong>繧ｨ繝ｩ繝ｼ邇・</strong> ${(data.error_rate || 0).toFixed(1)}%</p>
                `;
            })
            .catch(error => {
                document.getElementById('performanceStats').innerHTML = '<p style="color: red;">繧ｨ繝ｩ繝ｼ: 繝・・繧ｿ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ螟ｱ謨励＠縺ｾ縺励◆</p>';
            });

            // 繝悶Λ繧ｦ繧ｶ蛻・ｸ・・隱ｭ縺ｿ霎ｼ縺ｿ
            fetch('/admin/browser_distribution')
            .then(response => response.json())
            .then(data => {
                const browserDistribution = document.getElementById('browserDistribution');
                let html = '';
                for (const [browser, stats] of Object.entries(data)) {
                    html += `<p style="color: #333333;"><strong>${browser}:</strong> ${stats.count}莉ｶ (${stats.percentage.toFixed(1)}%)</p>`;
                }
                browserDistribution.innerHTML = html || '<p style="color: #333333;">繝・・繧ｿ縺後≠繧翫∪縺帙ｓ</p>';
            })
            .catch(error => {
                document.getElementById('browserDistribution').innerHTML = '<p style="color: red;">繧ｨ繝ｩ繝ｼ: 繝・・繧ｿ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ螟ｱ謨励＠縺ｾ縺励◆</p>';
            });

            // OS蛻・ｸ・・隱ｭ縺ｿ霎ｼ縺ｿ
            fetch('/admin/os_distribution')
            .then(response => response.json())
            .then(data => {
                const osDistribution = document.getElementById('osDistribution');
                let html = '';
                for (const [os, stats] of Object.entries(data)) {
                    html += `<p style="color: #333333;"><strong>${os}:</strong> ${stats.count}莉ｶ (${stats.percentage.toFixed(1)}%)</p>`;
                }
                osDistribution.innerHTML = html || '<p style="color: #333333;">繝・・繧ｿ縺後≠繧翫∪縺帙ｓ</p>';
            })
            .catch(error => {
                document.getElementById('osDistribution').innerHTML = '<p style="color: red;">繧ｨ繝ｩ繝ｼ: 繝・・繧ｿ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ螟ｱ謨励＠縺ｾ縺励◆</p>';
            });

            // 繝・ヰ繧､繧ｹ蛻・ｸ・・隱ｭ縺ｿ霎ｼ縺ｿ
            fetch('/admin/device_distribution')
            .then(response => response.json())
            .then(data => {
                const deviceDistribution = document.getElementById('deviceDistribution');
                let html = '';
                for (const [device, stats] of Object.entries(data)) {
                    html += `<p style="color: #333333;"><strong>${device}:</strong> ${stats.count}莉ｶ (${stats.percentage.toFixed(1)}%)</p>`;
                }
                deviceDistribution.innerHTML = html || '<p style="color: #333333;">繝・・繧ｿ縺後≠繧翫∪縺帙ｓ</p>';
            })
            .catch(error => {
                document.getElementById('deviceDistribution').innerHTML = '<p style="color: red;">繧ｨ繝ｩ繝ｼ: 繝・・繧ｿ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ螟ｱ謨励＠縺ｾ縺励◆</p>';
            });

            // 繝ｪ繧｢繝ｫ繧ｿ繧､繝逶｣隕悶・隱ｭ縺ｿ霎ｼ縺ｿ
            fetch('/admin/realtime_monitoring')
            .then(response => response.json())
            .then(data => {
                const realtimeMonitoring = document.getElementById('realtimeMonitoring');
                realtimeMonitoring.innerHTML = `
                    <p style="color: #333333;"><strong>迴ｾ蝨ｨ縺ｮ繝｡繝｢繝ｪ菴ｿ逕ｨ邇・</strong> ${data.memory_usage_percent || 0}%</p>
                    <p style="color: #333333;"><strong>迴ｾ蝨ｨ縺ｮCPU菴ｿ逕ｨ邇・</strong> ${data.cpu_usage_percent || 0}%</p>
                    <p style="color: #333333;"><strong>迴ｾ蝨ｨ縺ｮ繝ｬ繧ｹ繝昴Φ繧ｹ譎る俣:</strong> ${data.response_time_ms || 0}ms</p>
                    <p style="color: #333333;"><strong>繧｢繧ｯ繝・ぅ繝悶そ繝・す繝ｧ繝ｳ:</strong> ${data.active_sessions || 0}</p>
                    <p style="color: #333333;"><strong>API蜻ｼ縺ｳ蜃ｺ縺怜屓謨ｰ:</strong> ${data.api_calls || 0}</p>
                    <p style="color: #333333;"><strong>繧ｭ繝｣繝・す繝･繝偵ャ繝育紫:</strong> ${(data.cache_hit_rate || 0).toFixed(1)}%</p>
                `;
            })
            .catch(error => {
                document.getElementById('realtimeMonitoring').innerHTML = '<p style="color: red;">繧ｨ繝ｩ繝ｼ: 繝・・繧ｿ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ螟ｱ謨励＠縺ｾ縺励◆</p>';
            });
        }

        function refreshMonitoringData() {
            loadMonitoringData();
        }

        function exportMonitoringData() {
            // 逶｣隕悶ョ繝ｼ繧ｿ縺ｮ繧ｨ繧ｯ繧ｹ繝昴・繝域ｩ溯・
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
                alert('繧ｨ繧ｯ繧ｹ繝昴・繝医↓螟ｱ謨励＠縺ｾ縺励◆: ' + error.message);
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
                        <h3 style="margin-bottom: 10px; color: #2c3e50; font-weight: 600;">投 繧ｷ繧ｹ繝・Β蜈ｨ菴・/h3>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">繧ｹ繝・・繧ｿ繧ｹ:</strong> ${data.status === 'ok' ? '笨・豁｣蟶ｸ' : '笶・繧ｨ繝ｩ繝ｼ'}</p>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">邱上そ繝・す繝ｧ繝ｳ謨ｰ:</strong> ${data.total_sessions}莉ｶ</p>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">繧｢繧ｯ繝・ぅ繝悶そ繝・す繝ｧ繝ｳ:</strong> ${data.active_sessions}莉ｶ</p>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">謇句虚霑比ｿ｡蠕・■:</strong> ${data.manual_reply_queue}莉ｶ</p>
                    </div>
                    
                    <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #c8e6c9;">
                        <h3 style="margin-bottom: 10px; color: #2c3e50; font-weight: 600;">､・AI險ｭ螳・/h3>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">AI閾ｪ蜍募ｿ懃ｭ・</strong> ${data.ai_auto_reply ? '笨・ON' : '笞・・OFF'}</p>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">邂｡逅・・Δ繝ｼ繝・</strong> ${data.admin_mode ? '笨・ON' : '笞ｪ OFF'}</p>
                    </div>
                    
                    <div style="background: #fff3e0; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #ffe0b2;">
                        <h3 style="margin-bottom: 10px; color: #2c3e50; font-weight: 600;">刀 CSV繝・・繧ｿ</h3>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">隱ｭ縺ｿ霎ｼ縺ｿ迥ｶ諷・</strong> ${csvStatus.success ? '笨・謌仙粥' : '笶・螟ｱ謨・}</p>
                        ${csvStatus.success ? `
                            <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">繧ｨ繝ｳ繧ｳ繝ｼ繝・ぅ繝ｳ繧ｰ:</strong> ${csvStatus.encoding || 'N/A'}</p>
                            <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">陦梧焚:</strong> ${csvStatus.row_count || 0}陦・/p>
                            <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">蛻玲焚:</strong> ${csvStatus.col_count || 0}蛻・/p>
                        ` : `
                            <p style="color: #c62828; margin: 8px 0;"><strong style="color: #495057;">繧ｨ繝ｩ繝ｼ:</strong> ${csvStatus.error || '荳肴・縺ｪ繧ｨ繝ｩ繝ｼ'}</p>
                        `}
                    </div>
                    
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; border: 1px solid #bbdefb;">
                        <h3 style="margin-bottom: 10px; color: #2c3e50; font-weight: 600;">嶋 繝代ヵ繧ｩ繝ｼ繝槭Φ繧ｹ邨ｱ險・/h3>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">邱上Μ繧ｯ繧ｨ繧ｹ繝域焚:</strong> ${perfStats.total_requests || 0}莉ｶ</p>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">謌仙粥:</strong> ${perfStats.successful_requests || 0}莉ｶ</p>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">螟ｱ謨・</strong> ${perfStats.failed_requests || 0}莉ｶ</p>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">蟷ｳ蝮・ｿ懃ｭ疲凾髢・</strong> ${(perfStats.average_response_time || 0).toFixed(2)}遘・/p>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">邱上ヨ繝ｼ繧ｯ繝ｳ菴ｿ逕ｨ驥・</strong> ${perfStats.total_tokens_used || 0}</p>
                        <p style="color: #333; margin: 8px 0;"><strong style="color: #495057;">莉頑律縺ｮAPI蜻ｼ縺ｳ蜃ｺ縺・</strong> ${perfStats.api_calls_today || 0}蝗・/p>
                    </div>
                    
                    <p style="margin-top: 15px; text-align: center; color: #666;"><small>譛邨よ峩譁ｰ: ${new Date().toLocaleString('ja-JP')}</small></p>
                `;
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('systemStatusContent').innerHTML = `
                    <div style="background: #ffebee; padding: 15px; border-radius: 8px; color: #c62828;">
                        <p><strong>笶・繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆</strong></p>
                        <p>${error.message || '繧ｷ繧ｹ繝・Β迥ｶ豕√・蜿門ｾ励↓螟ｱ謨励＠縺ｾ縺励◆'}</p>
                    </div>
                `;
            });
        }
        
        // 蛹ｻ阮ｬ蜩∫嶌隲・ユ繧ｹ繝・
        function sendMedicineChat() {
            const input = document.getElementById('medicineChatInput').value;
            if (!input.trim()) {
                alert('繝｡繝・そ繝ｼ繧ｸ繧貞・蜉帙＠縺ｦ縺上□縺輔＞');
                return;
            }
            
            const resultDiv = document.getElementById('medicineChatResult');
            resultDiv.innerHTML = `
                <div style="text-align: center; padding: 30px 0;">
                    <div style="display: inline-block; width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                    <p style="color: #666; margin-top: 15px;">蜃ｦ逅・ｸｭ...</p>
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
                    const medicineType = data.medicine_type || 'AI謗ｨ螂ｨ';
                    const recommendation = data.recommendation || {};
                    
                    resultDiv.innerHTML = `
                        <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #c8e6c9;">
                            <h4 style="color: #2c3e50; margin-bottom: 10px; font-weight: 600;">笨・${data.message}</h4>
                            
                            <div style="background: white; padding: 12px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #e0e0e0;">
                                <p style="color: #333; margin-bottom: 8px;"><strong style="color: #495057;">謚ｽ蜃ｺ縺輔ｌ縺溽裸迥ｶ:</strong></p>
                                <p style="color: #555; line-height: 1.6;">${symptoms.length > 0 ? symptoms.join('縲・) : '逞・憾縺ｪ縺・}</p>
                            </div>
                            
                            <div style="background: white; padding: 12px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #e0e0e0;">
                                <p style="color: #333;"><strong style="color: #495057;">蛹ｻ阮ｬ蜩√ち繧､繝・</strong> <span style="color: #1976d2; font-weight: 600;">${medicineType}</span></p>
                            </div>
                            
                            ${recommendation.recommended_medicines && recommendation.recommended_medicines.length > 0 ? `
                                <div style="background: white; padding: 12px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #e0e0e0;">
                                    <p style="color: #333; margin-bottom: 10px;"><strong style="color: #495057;">謗ｨ螂ｨ蛹ｻ阮ｬ蜩・</strong> <span style="color: #2e7d32; font-weight: 600;">${recommendation.recommended_medicines.length}莉ｶ</span></p>
                                    <ul style="margin: 10px 0; padding-left: 20px; color: #333;">
                                        ${recommendation.recommended_medicines.slice(0, 5).map((med, index) => {
                                            const medName = med.product_name || med.name || med['蝠・刀蜷・] || 'N/A';
                                            const manufacturer = med.manufacturer || med['繝｡繝ｼ繧ｫ繝ｼ蜷・] || '';
                                            const score = med.score ? ` (繧ｹ繧ｳ繧｢: ${(med.score * 100).toFixed(0)}%)` : '';
                                            return `<li style="margin-bottom: 8px; color: #333;">
                                                <strong style="color: #1976d2;">${index + 1}. ${medName}</strong>
                                                ${manufacturer ? `<span style="color: #666; font-size: 0.9em;"> - ${manufacturer}</span>` : ''}
                                                ${score ? `<span style="color: #4caf50; font-size: 0.85em;">${score}</span>` : ''}
                                            </li>`;
                                        }).join('')}
                                    </ul>
                                </div>
                            ` : '<div style="background: #fff3e0; padding: 12px; border-radius: 5px; margin-bottom: 10px; border: 1px solid #ffe0b2;"><p style="color: #f57c00;">謗ｨ螂ｨ蛹ｻ阮ｬ蜩√′隕九▽縺九ｊ縺ｾ縺帙ｓ縺ｧ縺励◆</p></div>'}
                            
                            <details style="margin-top: 15px;">
                                <summary style="cursor: pointer; color: #1976d2; padding: 10px; background: #f5f5f5; border-radius: 5px; user-select: none; font-weight: 600;">搭 隧ｳ邏ｰ邨先棡繧定｡ｨ遉ｺ・・SON・・/summary>
                                <div style="margin-top: 10px; max-height: 400px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 5px;">
                                    <pre style="background: #263238; color: #aed581; padding: 15px; margin: 0; font-size: 11px; font-family: 'Courier New', monospace; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word;">${JSON.stringify(data, null, 2)}</pre>
                                </div>
                            </details>
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `
                        <div style="background: #ffebee; padding: 15px; border-radius: 8px; border: 1px solid #ef9a9a;">
                            <p style="color: #c62828; font-weight: 600; margin-bottom: 8px;"><strong>笶・繧ｨ繝ｩ繝ｼ</strong></p>
                            <p style="color: #d32f2f;">${data.message || '荳肴・縺ｪ繧ｨ繝ｩ繝ｼ'}</p>
                            ${data.error ? `<p style="font-size: 12px; margin-top: 10px; color: #e64a19;">隧ｳ邏ｰ: ${data.error}</p>` : ''}
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                resultDiv.innerHTML = `
                    <div style="background: #ffebee; padding: 15px; border-radius: 8px; border: 1px solid #ef9a9a;">
                        <p style="color: #c62828; font-weight: 600; margin-bottom: 8px;"><strong>笶・騾壻ｿ｡繧ｨ繝ｩ繝ｼ</strong></p>
                        <p style="color: #d32f2f;">${error.message || '繧ｵ繝ｼ繝舌・縺ｨ縺ｮ騾壻ｿ｡縺ｫ螟ｱ謨励＠縺ｾ縺励◆'}</p>
                    </div>
                `;
            });
        }
        
        // 繝ｭ繧ｰ繧ｯ繝ｪ繧｢讖溯・
        function clearAllLogs() {
            fetch('/clear_logs', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                // 謌仙粥騾夂衍繧定｡ｨ遉ｺ
                const notification = document.createElement('div');
                notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #4caf50; color: white; padding: 15px 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); z-index: 10000;';
                notification.innerHTML = `<strong>笨・${data.message || '繝ｭ繧ｰ繧偵け繝ｪ繧｢縺励∪縺励◆'}</strong>`;
                document.body.appendChild(notification);
                
                setTimeout(() => {
                    notification.remove();
                }, 3000);
                
                // 謇句虚霑比ｿ｡蠕・■繧ｭ繝･繝ｼ繧偵け繝ｪ繧｢
                const queueDiv = document.getElementById('manual-reply-queue');
                if (queueDiv) {
                    queueDiv.innerHTML = `
                        <div class="empty-state" style="text-align: center; color: #888; font-size: 0.9em; padding: 50px 0;">
                            <div style="font-size: 3em;">働</div>
                            <p style="margin-top: 10px;">謇句虚霑比ｿ｡蠕・■縺ｪ縺・/p>
                        </div>
                    `;
                }
                
                // 邱頑･莉ｶ謨ｰ繧ｫ繧ｦ繝ｳ繧ｿ繝ｼ繧偵Μ繧ｻ繝・ヨ
                const crisisCountElement = document.getElementById('crisis-count');
                if (crisisCountElement) {
                    crisisCountElement.textContent = '';
                    crisisCountElement.style.background = '#e3f2fd';
                    crisisCountElement.style.color = '#1976d2';
                }
                
                // 繧ｻ繝・す繝ｧ繝ｳ荳隕ｧ繧呈峩譁ｰ
                if (typeof loadSessions === 'function') {
                    loadSessions();
                }
                
                // 邨ｱ險域ュ蝣ｱ繧呈峩譁ｰ
                document.getElementById('queue-count').textContent = '0';
                document.getElementById('total-sessions').textContent = '0';
            })
            .catch(error => {
                console.error('Error:', error);
                alert('繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆: ' + error.message);
            });
        }

        function formatDiagnosisMessage(diagnosis) {
            let content = '';
            
            // 繝・ヰ繝・げ諠・ｱ繧定ｿｽ蜉・磯幕逋ｺ譎ゅ・縺ｿ・・
            console.log('Formatting diagnosis:', diagnosis);
            
            if (diagnosis.error) {
                content = `逕ｳ縺苓ｨｳ縺斐＊縺・∪縺帙ｓ縲・{diagnosis.error}`;
            } else {
                // 逞・憾諠・ｱ縺ｮ陦ｨ遉ｺ
                if (diagnosis.symptoms) {
                    content += `<div style="margin-bottom: 10px;"><strong>剥 逞・憾:</strong><br>${diagnosis.symptoms.join(', ')}</div>`;
                }
                
                if (diagnosis.symptom_pairs) {
                    content += `<div style="margin-bottom: 10px;"><strong>剥 謗ｨ螳壹＆繧後◆逞・憾:</strong><br>${diagnosis.symptom_pairs.join(', ')}</div>`;
                }
                
                // 蛹ｻ阮ｬ蜩√・遞ｮ鬘・
                if (diagnosis.medicine_type) {
                    content += `<div style="margin-bottom: 10px;"><strong>抽 蛹ｻ阮ｬ蜩√・遞ｮ鬘・</strong><br>${diagnosis.medicine_type}</div>`;
                }
                
                // 謗ｨ螂ｨ蛹ｻ阮ｬ蜩√・隧ｳ邏ｰ陦ｨ遉ｺ
                if (diagnosis.recommended_medicines && diagnosis.recommended_medicines.length > 0) {
                    content += `<div style="margin-bottom: 15px;"><strong>抽 謗ｨ螂ｨ蛹ｻ阮ｬ蜩・</strong></div>`;
                    diagnosis.recommended_medicines.forEach((medicine, index) => {
                        content += `<div style="margin-bottom: 10px; padding: 10px; border: 1px solid #e0e0e0; border-radius: 5px; background: #f9f9f9;">`;
                        content += `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">`;
                        content += `<div style="font-weight: bold; color: #2c3e50;">${index + 1}. ${medicine.product_name || '陬ｽ蜩∝錐荳肴・'}</div>`;
                        // 繧ｹ繧ｳ繧｢繝ｪ繝ｳ繧ｰ陦ｨ遉ｺ・育ｮ｡逅・・判髱｢縺ｮ縺ｿ・・
                        if (medicine.score !== undefined) {
                            console.log('剥 Medicine score:', medicine.score, 'for', medicine.product_name);
                            const scoreClass = medicine.score >= 0.7 ? 'admin-score-high' : medicine.score >= 0.5 ? 'admin-score-medium' : 'admin-score-low';
                            const scoreText = medicine.score >= 0.7 ? '鬮・ : medicine.score >= 0.5 ? '荳ｭ' : '菴・;
                            content += `<div class="admin-score-display ${scoreClass}">
                                投 譛驕ｩ蠎ｦ: ${(medicine.score * 100).toFixed(0)}% (${scoreText})
                            </div>`;
                        }
                        content += `</div>`;
                        if (medicine.manufacturer) {
                            content += `<div style="font-size: 0.9em; color: #666;">繝｡繝ｼ繧ｫ繝ｼ: ${medicine.manufacturer}</div>`;
                        }
                        if (medicine.efficacy) {
                            content += `<div style="font-size: 0.9em; color: #666;">蜉ｹ閭ｽ蜉ｹ譫・ ${medicine.efficacy}</div>`;
                        }
                        if (medicine.ingredients) {
                            content += `<div style="font-size: 0.9em; color: #666;">謌仙・: ${medicine.ingredients}</div>`;
                        }
                        if (medicine.usage_notes) {
                            // 菴ｿ逕ｨ荳翫・豕ｨ諢上ｒ鬆・岼縺斐→縺ｫ謾ｹ陦後＠縺ｦ陦ｨ遉ｺ
                            const usageNotes = medicine.usage_notes;
                            content += `<div style="margin-top: 8px; padding: 8px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #e74c3c;">`;
                            content += `<div style="font-size: 0.9em; color: #e74c3c; font-weight: bold; margin-bottom: 6px;">搭 菴ｿ逕ｨ荳翫・豕ｨ諢・/div>`;
                            
                            // 菴ｿ逕ｨ荳翫・豕ｨ諢上ｒ謾ｹ陦後〒蛻・牡縺励※陦ｨ遉ｺ
                            const notesArray = usageNotes
                                .split(/\r?\n/)
                                .map(note => note.trim())
                                .filter(note => note && note !== '');
                            
                            if (notesArray.length > 0) {
                                notesArray.forEach(note => {
                                    content += `<div style="margin-bottom: 4px; font-size: 0.85em; color: #333;">窶｢ ${note}</div>`;
                                });
                            } else {
                                // 謾ｹ陦後′縺ｪ縺・ｴ蜷医・縺昴・縺ｾ縺ｾ陦ｨ遉ｺ
                                content += `<div style="margin-bottom: 4px; font-size: 0.85em; color: #333;">窶｢ ${usageNotes}</div>`;
                            }
                            content += `</div>`;
                        }
                        if (medicine.doping_prohibited) {
                            content += `<div style="font-size: 0.9em; color: #f39c12;"><strong>繝峨・繝斐Φ繧ｰ隕丞宛:</strong> ${medicine.doping_prohibited}</div>`;
                        }
                        content += `</div>`;
                    });
                }
                
                // 蠕捺擂縺ｮmedicines驟榊・・亥ｾ梧婿莠呈鋤諤ｧ・・
                if (diagnosis.medicines) {
                    content += `<div style="margin-bottom: 10px;"><strong>抽 蟶りｲｩ阮ｬ蛟呵｣・</strong><br>${diagnosis.medicines.join(', ')}</div>`;
                }
                
                // 菴ｿ逕ｨ荳翫・豕ｨ諢・
                if (diagnosis.usage_notes) {
                    content += `<div style="margin-bottom: 10px;"><strong>笞・・菴ｿ逕ｨ荳翫・豕ｨ諢・</strong><br>${diagnosis.usage_notes}</div>`;
                }
                
                // 蛹ｻ蟶ｫ逶ｸ隲・・繧｢繝峨ヰ繧､繧ｹ
                if (diagnosis.doctor_consultation) {
                    content += `<div style="margin-bottom: 10px;"><strong>捉窶坂囎・・蛹ｻ蟶ｫ逶ｸ隲・</strong><br>${diagnosis.doctor_consultation}</div>`;
                }
                
                // 豕ｨ諢冗せ
                if (diagnosis.cautions) {
                    content += `<div style="margin-bottom: 10px;"><strong>笞・・豕ｨ諢冗せ:</strong><br>${diagnosis.cautions.join('<br>')}</div>`;
                }
                
                // 阮ｬ縺ｮ驕ｸ縺ｳ譁ｹ繧｢繝峨ヰ繧､繧ｹ
                if (diagnosis.combination_advice) {
                    content += `<div style="margin-bottom: 10px;"><strong>庁 阮ｬ縺ｮ驕ｸ縺ｳ譁ｹ繧｢繝峨ヰ繧､繧ｹ:</strong><br>${diagnosis.combination_advice}</div>`;
                }
                
                // 雉ｪ蝠乗｡亥・
                if ((diagnosis.symptoms || diagnosis.symptom_pairs) && !diagnosis.error) {
                    content += `<div style="margin-top: 10px; font-style: italic; color: #666;"><strong>笶・莉悶↓縺碑ｳｪ蝠上・縺ゅｊ縺ｾ縺吶°・・/strong><br>阮ｬ縺ｮ鬟ｲ縺ｿ譁ｹ縲∝憶菴懃畑縲∽ｻ悶・逞・憾縺ｨ縺ｮ髢｢菫ゅ↑縺ｩ縲√♀豌苓ｻｽ縺ｫ縺願◇縺阪￥縺縺輔＞縲・/div>`;
                }
            }
            
            // 蜀・ｮｹ縺後↑縺・ｴ蜷医・險ｺ譁ｭ邨先棡縺ｮ隧ｳ邏ｰ繧定｡ｨ遉ｺ
            if (!content) {
                content = `<div style="color: #666; font-style: italic;">險ｺ譁ｭ邨先棡縺ｮ隧ｳ邏ｰ諠・ｱ縺後≠繧翫∪縺帙ｓ縲・/div>`;
            }
            
            return content;
        }

        function handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendReply();
            }
        }

        function sendReply() {
            if (!currentSessionId) {
                showNotification('繧ｻ繝・す繝ｧ繝ｳ繧帝∈謚槭＠縺ｦ縺上□縺輔＞', 'warning');
                return;
            }
            
            const chatInput = document.getElementById('chat-input');
            const replyMessage = chatInput.value.trim();
            
            if (!replyMessage) {
                showNotification('霑比ｿ｡繝｡繝・そ繝ｼ繧ｸ繧貞・蜉帙＠縺ｦ縺上□縺輔＞', 'warning');
                return;
            }
            
            // 蜈･蜉帑ｸｭ陦ｨ遉ｺ
            const typingIndicator = document.getElementById('typing-indicator');
            typingIndicator.classList.add('show');
            
            // 騾∽ｿ｡繝懊ち繝ｳ繧堤┌蜉ｹ蛹・
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
                    showNotification(`繧ｨ繝ｩ繝ｼ: ${data.error}`, 'error');
                    sendBtn.disabled = false;
                } else {
                    showNotification(`霑比ｿ｡繧帝∽ｿ｡縺励∪縺励◆ (繧ｻ繝・す繝ｧ繝ｳ: ${data.target_session_id})`, 'success');
                    chatInput.value = '';
                    chatInput.style.height = 'auto';
                    
                    console.log('Manual reply sent successfully:', data);
                    
                    // 蜊ｳ蠎ｧ縺ｫ繝√Ε繝・ヨ螻･豁ｴ繧呈峩譁ｰ・・蝗槭・縺ｿ・・
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
                                // API縺ｯ {sessions: [...]} 縺ｮ蠖｢蠑上〒霑斐☆縺溘ａ縲‥ata.sessions 縺ｫ繧｢繧ｯ繧ｻ繧ｹ
                                const sessionsArray = sessionsData.sessions || (Array.isArray(sessionsData) ? sessionsData : []);
                                const targetSession = sessionsArray.find(s => s.session_id === currentSessionId);
                                if (targetSession) {
                                    console.log('Target session after reply:', targetSession);
                                    renderChatMessages(targetSession.messages);
                                    
                                    // 繧ｻ繝・す繝ｧ繝ｳ荳隕ｧ繧よ峩譁ｰ
                                    allSessions = sessionsArray;
                                    renderSessionList(allSessions);
                                    document.getElementById('total-sessions').textContent = allSessions.length;
                                }
                            })
                            .catch(error => {
                                console.error('Session refresh error:', error);
                            })
                            .finally(() => {
                                // 譖ｴ譁ｰ螳御ｺ・ｾ後↓騾∽ｿ｡繝懊ち繝ｳ縺ｮ迥ｶ諷九ｒ譖ｴ譁ｰ
                                updateSendButtonState();
                            });
                    }, 200);
                }
            })
            .catch(error => {
                typingIndicator.classList.remove('show');
                sendBtn.disabled = false;
                showNotification(`繧ｨ繝ｩ繝ｼ: ${error.message}`, 'error');
            });
        }

        // 騾∽ｿ｡繝懊ち繝ｳ縺ｮ迥ｶ諷九ｒ譖ｴ譁ｰ縺吶ｋ髢｢謨ｰ
        function updateSendButtonState() {
            const chatInput = document.getElementById('chat-input');
            const sendBtn = document.getElementById('send-btn');
            const hasText = chatInput.value.trim().length > 0;
            const hasSession = currentSessionId !== null;
            sendBtn.disabled = !hasText || !hasSession;
        }

        // 繧ｵ繧､繝峨ヰ繝ｼ縺ｫ蜈ｨ繧ｻ繝・す繝ｧ繝ｳ荳隕ｧ繧定｡ｨ遉ｺ
        function refreshSessionList() {
            console.log('Refreshing session list...');
            fetch('/api/main_sessions')
                .then(res => res.json())
                .then(data => {
                    console.log('Sessions data received:', data);
                    // API縺ｯ {sessions: [...]} 縺ｮ蠖｢蠑上〒霑斐☆縺溘ａ縲‥ata.sessions 縺ｫ繧｢繧ｯ繧ｻ繧ｹ
                    const sessionsArray = data.sessions || (Array.isArray(data) ? data : []);
                    console.log('Sessions count:', sessionsArray.length);
                    
                    allSessions = sessionsArray;
                    
                    // 蜷・そ繝・す繝ｧ繝ｳ縺ｮ隧ｳ邏ｰ繧偵Ο繧ｰ蜃ｺ蜉・
                    allSessions.forEach((session, index) => {
                        console.log(`Session ${index + 1}:`, {
                            session_id: session.session_id,
                            username: session.username,
                            messages_count: session.messages_count,
                            has_messages: session.messages && session.messages.length > 0
                        });
                    });
                    
                    renderSessionList(allSessions);
                    
                    // 邨ｱ險域ュ蝣ｱ繧よ峩譁ｰ
                    document.getElementById('total-sessions').textContent = allSessions.length;
                    
                    console.log('Session list refresh completed');
                })
                .catch(error => {
                    console.error('Session list error:', error);
                    renderSessionList([]);
                    document.getElementById('total-sessions').textContent = '0';
                });
        }

        // 繧ｻ繝・す繝ｧ繝ｳ讀懃ｴ｢讖溯・
        function filterSessions() {
            const searchTerm = document.getElementById('session-search').value.toLowerCase();
            const filteredSessions = allSessions.filter(session => {
                const username = (session.username || '').toLowerCase();
                const sessionId = (session.session_id || '').toLowerCase();
                return username.includes(searchTerm) || sessionId.includes(searchTerm);
            });
            renderSessionList(filteredSessions);
        }

        // 繧ｻ繝・す繝ｧ繝ｳ讀懃ｴ｢繧ｯ繝ｪ繧｢
        function clearSessionFilter() {
            document.getElementById('session-search').value = '';
            renderSessionList(allSessions);
        }

        // HTML繧ｨ繧ｹ繧ｱ繝ｼ繝鈴未謨ｰ
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function renderSessionList(sessions) {
            const sidebar = document.getElementById('session-list');
            if (!sidebar) return;
            
            console.log('Rendering sessions:', sessions);
            
            if (!Array.isArray(sessions) || sessions.length === 0) {
                sidebar.innerHTML = '<div style="padding: 24px; color: #888; text-align: center;">繧ｻ繝・す繝ｧ繝ｳ縺後≠繧翫∪縺帙ｓ</div>';
                return;
            }
            
            let html = '';
            sessions.forEach((session, idx) => {
                // 繝ｦ繝ｼ繧ｶ繝ｼ蜷阪・蜿門ｾ励ｒ謾ｹ蝟・
                let username = '荳肴・縺ｪ繝ｦ繝ｼ繧ｶ繝ｼ';
                if (session.username && session.username.trim()) {
                    username = session.username;
                } else if (session.session_id) {
                    // 繧ｻ繝・す繝ｧ繝ｳID縺九ｉ繝ｦ繝ｼ繧ｶ繝ｼ蜷阪ｒ逕滓・
                    username = `繝ｦ繝ｼ繧ｶ繝ｼ${session.session_id.slice(-4)}`;
                } else {
                    username = `繝ｦ繝ｼ繧ｶ繝ｼ${idx + 1}`;
                }
                
                const messageCount = session.messages_count || 0;
                const isSelected = currentSessionId === session.session_id;
                
                // 譛蠕後・繝｡繝・そ繝ｼ繧ｸ繧貞叙蠕暦ｼ・TML繧ｿ繧ｰ繧帝勁蜴ｻ・・
                let lastMessage = '繝｡繝・そ繝ｼ繧ｸ縺ｪ縺・;
                if (session.messages && session.messages.length > 0) {
                    const lastMsg = session.messages[session.messages.length - 1];
                    let content = lastMsg.content || '';
                    // HTML繧ｿ繧ｰ繧帝勁蜴ｻ
                    const tempDiv = document.createElement('div');
                    tempDiv.innerHTML = content;
                    const textContent = tempDiv.textContent || tempDiv.innerText || '';
                    lastMessage = textContent.substring(0, 30);
                    if (textContent.length > 30) {
                        lastMessage += '...';
                    }
                }
                
                // 譛邨よ峩譁ｰ譎ょ綾繧定ｨ育ｮ・
                let lastUpdate = '荳肴・';
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
                        // 繧ｿ繧､繝繧ｹ繧ｿ繝ｳ繝励′縺ｪ縺・ｴ蜷医・迴ｾ蝨ｨ譎ょ綾繧剃ｽｿ逕ｨ
                        lastUpdate = new Date().toLocaleString('ja-JP', {
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit'
                        });
                    }
                }
                
                // 蜊ｱ讖溷ｯｾ蠢懊そ繝・す繝ｧ繝ｳ縺九←縺・°繧偵メ繧ｧ繝・け
                const isCrisisSession = session.crisis_detected === true;
                
                // 繝｡繝・そ繝ｼ繧ｸ謨ｰ縺ｫ蠢懊§縺溯牡蛻・￠
                let messageCountColor = '#3498db';
                if (messageCount > 10) messageCountColor = '#e74c3c';
                else if (messageCount > 5) messageCountColor = '#f39c12';
                
                // 繧ｻ繝・す繝ｧ繝ｳID縺ｮ遏ｭ邵ｮ陦ｨ遉ｺ
                const shortSessionId = session.session_id ? session.session_id.substring(0, 8) + '...' : 'unknown';
                
                // 蜊ｱ讖溷ｯｾ蠢懊そ繝・す繝ｧ繝ｳ縺ｮ蝣ｴ蜷医・迚ｹ蛻･縺ｪ繧ｹ繧ｿ繧､繝ｫ繧帝←逕ｨ
                const sessionClass = isCrisisSession ? 'session-item crisis-session' : 'session-item';
                const sessionStyle = isCrisisSession ? 
                    'padding: 15px; cursor: pointer; border-bottom: 1px solid #e0e0e0; margin-bottom: 5px; border-radius: 8px; background: linear-gradient(135deg, #ffebee, #ffcdd2); color: #e74c3c;' :
                    `padding: 15px; cursor: pointer; border-bottom: 1px solid #e0e0e0; margin-bottom: 5px; border-radius: 8px; ${isSelected ? 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;' : 'background: #f8f9fa;'}`;
                
                html += `
                    <div class="${sessionClass}" 
                         style="${sessionStyle}" 
                         onclick="selectSession(event, '${session.session_id}', '${username}')">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                            <div style="flex: 1;">
                                <div style="font-weight: bold; font-size: 1.1em; margin-bottom: 4px; color: ${isCrisisSession ? '#e74c3c' : (isSelected ? 'white' : '#2c3e50')};">
                                    ${username}
                                    ${isCrisisSession ? '<span class="crisis-badge">圷 邱頑･</span>' : ''}
                                </div>
                                <div style="font-size: 0.75em; color: ${isCrisisSession ? '#e74c3c' : (isSelected ? '#e0e0e0' : '#888')}; margin-bottom: 4px;">ID: ${shortSessionId}</div>
                                <div style="font-size: 0.7em; color: ${isCrisisSession ? '#e74c3c' : (isSelected ? '#e0e0e0' : '#999')};">譛邨よ峩譁ｰ: ${lastUpdate}</div>
                            </div>
                            <div style="text-align: right;">
                                <span style="background: ${isCrisisSession ? '#e74c3c' : (isSelected ? 'rgba(255,255,255,0.3)' : messageCountColor)}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.8em; font-weight: bold;">
                                    ${messageCount}莉ｶ
                                </span>
                            </div>
                        </div>
                        <div style="font-size: 0.85em; color: ${isCrisisSession ? '#e74c3c' : (isSelected ? '#e0e0e0' : '#666')}; line-height: 1.3;">
                            ${escapeHtml(lastMessage)}
                        </div>
                    </div>
                `;
            });
            sidebar.innerHTML = html;
        }

        function selectSession(event, sessionId, username) {
            currentSessionId = sessionId;
            
            // 驕ｸ謚樒憾諷九ｒ譖ｴ譁ｰ
            document.querySelectorAll('.session-item').forEach(item => {
                item.style.background = '#f8f9fa';
                item.style.color = '#2c3e50';
            });
            event.currentTarget.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            event.currentTarget.style.color = 'white';
            
            // 繝√Ε繝・ヨ繧ｿ繧､繝医Ν繧呈峩譁ｰ
            document.getElementById('chat-title').textContent = `${username} (${sessionId.substring(0, 8)}...)`;
            
            // 繝√Ε繝・ヨ蜈･蜉帙お繝ｪ繧｢繧呈怏蜉ｹ蛹・
            const chatInput = document.getElementById('chat-input');
            const sendBtn = document.getElementById('send-btn');
            const micBtn = document.getElementById('mic-btn');
            chatInput.disabled = false;
            chatInput.placeholder = `${username} 縺ｫ霑比ｿ｡繝｡繝・そ繝ｼ繧ｸ繧貞・蜉帙＠縺ｦ縺上□縺輔＞...`;
            micBtn.disabled = false;
            
            // 騾∽ｿ｡繝懊ち繝ｳ縺ｮ迥ｶ諷九ｒ譖ｴ譁ｰ
            updateSendButtonState();
            
            // 驕ｸ謚槭＠縺溘そ繝・す繝ｧ繝ｳ縺ｮ繝｡繝・そ繝ｼ繧ｸ螻･豁ｴ繧貞叙蠕・
            loadChatHistory(sessionId);
            
            // 驕ｸ謚槭＠縺溘そ繝・す繝ｧ繝ｳ繧偵ワ繧､繝ｩ繧､繝・
            showNotification(`${username} 縺ｮ繧ｻ繝・す繝ｧ繝ｳ繧帝∈謚槭＠縺ｾ縺励◆`, 'success');
            
            // 繝√Ε繝・ヨ繧ｨ繝ｪ繧｢繧偵せ繧ｯ繝ｭ繝ｼ繝ｫ縺励※陦ｨ遉ｺ
            document.querySelector('.chat-area').scrollIntoView({ behavior: 'smooth' });
        }

        // 謇句虚霑比ｿ｡繝懊ち繝ｳ縺ｮ讖溯・
        function openManualReply(messageIndex) {
            if (!currentSessionId) {
                showNotification('繧ｻ繝・す繝ｧ繝ｳ繧帝∈謚槭＠縺ｦ縺上□縺輔＞', 'warning');
                return;
            }
            
            const replyMessage = prompt(`繝｡繝・そ繝ｼ繧ｸ${messageIndex + 1}縺ｫ蟇ｾ縺吶ｋ謇句虚霑比ｿ｡繧貞・蜉帙＠縺ｦ縺上□縺輔＞:`);
            if (replyMessage && replyMessage.trim()) {
                sendManualReply(replyMessage.trim());
            }
        }

        // 謇句虚霑比ｿ｡繧帝∽ｿ｡
        function sendManualReply(replyMessage) {
            if (!currentSessionId) {
                showNotification('繧ｻ繝・す繝ｧ繝ｳ繧帝∈謚槭＠縺ｦ縺上□縺輔＞', 'warning');
                return;
            }
            
            // 蜈･蜉帑ｸｭ陦ｨ遉ｺ
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
                    showNotification(`繧ｨ繝ｩ繝ｼ: ${data.error}`, 'error');
                } else {
                    showNotification(`謇句虚霑比ｿ｡繧帝∽ｿ｡縺励∪縺励◆`, 'success');
                    
                    // 繝√Ε繝・ヨ螻･豁ｴ繧呈峩譁ｰ
                    setTimeout(() => {
                        loadChatHistory(currentSessionId);
                    }, 500);
                }
            })
            .catch(error => {
                typingIndicator.classList.remove('show');
                showNotification(`繧ｨ繝ｩ繝ｼ: ${error.message}`, 'error');
            });
        }

        // 髻ｳ螢ｰ隱崎ｭ俶ｩ溯・
        let recognition = null;
        let isRecording = false;

        function initVoiceRecognition() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                console.log('髻ｳ螢ｰ隱崎ｭ連PI縺ｯ縺薙・繝悶Λ繧ｦ繧ｶ縺ｧ縺ｯ繧ｵ繝昴・繝医＆繧後※縺・∪縺帙ｓ');
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
                console.error('髻ｳ螢ｰ隱崎ｭ倥お繝ｩ繝ｼ:', event.error);
                stopVoiceInput();
                
                let errorMessage = '';
                switch(event.error) {
                    case 'not-allowed':
                        errorMessage = '繝槭う繧ｯ縺ｮ菴ｿ逕ｨ縺瑚ｨｱ蜿ｯ縺輔ｌ縺ｦ縺・∪縺帙ｓ縲ゅい繝峨Ξ繧ｹ繝舌・蟾ｦ蛛ｴ縺ｮ繧｢繧､繧ｳ繝ｳ縺九ｉ繝槭う繧ｯ繧偵瑚ｨｱ蜿ｯ縲阪↓螟画峩縺励※縺上□縺輔＞縲・;
                        break;
                    case 'no-speech':
                        // 辟｡髻ｳ縺ｮ蝣ｴ蜷医・菴輔ｂ縺励↑縺・
                        return;
                    case 'audio-capture':
                        errorMessage = '繝槭う繧ｯ縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ縲ゅ・繧､繧ｯ縺梧磁邯壹＆繧後※縺・ｋ縺狗｢ｺ隱阪＠縺ｦ縺上□縺輔＞縲・;
                        break;
                    case 'network':
                        errorMessage = '繝阪ャ繝医Ρ繝ｼ繧ｯ繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆縲・;
                        break;
                    default:
                        errorMessage = '髻ｳ螢ｰ隱崎ｭ倥お繝ｩ繝ｼ: ' + event.error;
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
                    showNotification('縺薙・繝悶Λ繧ｦ繧ｶ縺ｯ髻ｳ螢ｰ隱崎ｭ倥↓蟇ｾ蠢懊＠縺ｦ縺・∪縺帙ｓ', 'error');
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
                micBtn.title = '骭ｲ髻ｳ荳ｭ... (繧ｯ繝ｪ繝・け縺ｧ蛛懈ｭ｢)';
                showNotification('髻ｳ螢ｰ隱崎ｭ倥ｒ髢句ｧ九＠縺ｾ縺励◆', 'success');
            } catch (error) {
                console.error('髻ｳ螢ｰ隱崎ｭ倬幕蟋九お繝ｩ繝ｼ:', error);
                showNotification('髻ｳ螢ｰ隱崎ｭ倥・髢句ｧ九↓螟ｱ謨励＠縺ｾ縺励◆', 'error');
            }
        }

        function stopVoiceInput() {
            if (recognition) {
                recognition.stop();
            }
            isRecording = false;
            const micBtn = document.getElementById('mic-btn');
            micBtn.classList.remove('recording');
            micBtn.title = '髻ｳ螢ｰ蜈･蜉・;
        }
        
        // 繧ｻ繧ｭ繝･繝ｪ繝・ぅ隧ｳ邏ｰ陦ｨ遉ｺ讖溯・
        function showSecurityDetails(securityInfo) {
            const securityPanel = document.getElementById('security-panel');
            const securityDetails = document.getElementById('security-details');
            
            if (!securityInfo || !securityInfo.risk_score) {
                securityPanel.style.display = 'none';
                return;
            }
            
            // 繝ｪ繧ｹ繧ｯ繧ｹ繧ｳ繧｢縺ｫ蠢懊§縺溘け繝ｩ繧ｹ險ｭ螳・
            let riskClass = 'low';
            if (securityInfo.risk_score >= 80) {
                riskClass = 'high';
            } else if (securityInfo.risk_score >= 60) {
                riskClass = 'medium';
            }
            
            // 謾ｻ謦・ヱ繧ｿ繝ｼ繝ｳ縺ｮ陦ｨ遉ｺ
            let attackPatternsHtml = '';
            if (securityInfo.detected_patterns && securityInfo.detected_patterns.length > 0) {
                attackPatternsHtml = `
                    <div class="attack-patterns">
                        <strong>讀懷・縺輔ｌ縺滓判謦・ヱ繧ｿ繝ｼ繝ｳ:</strong><br>
                        ${securityInfo.detected_patterns.map(pattern => `窶｢ ${pattern}`).join('<br>')}
                    </div>
                `;
            }
            
            // 隴ｦ蜻翫Γ繝・そ繝ｼ繧ｸ縺ｮ陦ｨ遉ｺ
            let warningsHtml = '';
            if (securityInfo.warnings && securityInfo.warnings.length > 0) {
                warningsHtml = `
                    <div class="security-alert">
                        <strong>隴ｦ蜻・</strong><br>
                        ${securityInfo.warnings.map(warning => `窶｢ ${warning}`).join('<br>')}
                    </div>
                `;
            }
            
            // 繧ｻ繧ｭ繝･繝ｪ繝・ぅ隧ｳ邏ｰ縺ｮHTML逕滓・
            securityDetails.innerHTML = `
                <div class="security-info">
                    <strong>繝ｪ繧ｹ繧ｯ繧ｹ繧ｳ繧｢:</strong> 
                    <span class="risk-score ${riskClass}">${securityInfo.risk_score}/100</span>
                </div>
                <div class="security-info">
                    <strong>讀懆ｨｼ邨先棡:</strong> 
                    ${securityInfo.is_safe ? '笨・螳牙・' : '笶・蜊ｱ髯ｺ'}
                </div>
                <div class="security-info">
                    <strong>蜈･蜉帙ユ繧ｭ繧ｹ繝・</strong> 
                    <span style="font-family: monospace; background: #f8f9fa; padding: 2px 4px; border-radius: 3px;">
                        ${securityInfo.input_text ? securityInfo.input_text.substring(0, 100) + (securityInfo.input_text.length > 100 ? '...' : '') : 'N/A'}
                    </span>
                </div>
                <div class="security-info">
                    <strong>繧ｵ繝九ち繧､繧ｺ貂医∩繝・く繧ｹ繝・</strong> 
                    <span style="font-family: monospace; background: #f8f9fa; padding: 2px 4px; border-radius: 3px;">
                        ${securityInfo.sanitized_text ? securityInfo.sanitized_text.substring(0, 100) + (securityInfo.sanitized_text.length > 100 ? '...' : '') : 'N/A'}
                    </span>
                </div>
                <div class="security-info">
                    <strong>讀懆ｨｼ譎ょ綾:</strong> 
                    ${securityInfo.timestamp ? new Date(securityInfo.timestamp).toLocaleString('ja-JP') : 'N/A'}
                </div>
                ${attackPatternsHtml}
                ${warningsHtml}
            `;
            
            securityPanel.style.display = 'block';
        }
        
        // 繧ｻ繧ｭ繝･繝ｪ繝・ぅ隧ｳ邏ｰ繧帝國縺・
        function hideSecurityDetails() {
            const securityPanel = document.getElementById('security-panel');
            securityPanel.style.display = 'none';
        }
        
        // 繝｡繝・そ繝ｼ繧ｸ繧ｯ繝ｪ繝・け譎ゅ・繧ｻ繧ｭ繝･繝ｪ繝・ぅ隧ｳ邏ｰ陦ｨ遉ｺ
        function showMessageSecurityDetails(message) {
            if (message.security_info) {
                showSecurityDetails(message.security_info);
            } else {
                hideSecurityDetails();
            }
        }
        
        // 繧ｰ繝ｭ繝ｼ繝舌Ν繧ｨ繝ｩ繝ｼ繝上Φ繝峨Λ繝ｼ・・hrome諡｡蠑ｵ讖溯・繧ｨ繝ｩ繝ｼ繧堤┌隕厄ｼ・
        window.addEventListener('error', function(event) {
            // Chrome諡｡蠑ｵ讖溯・縺ｮ繧ｨ繝ｩ繝ｼ繧堤┌隕・
            if (event.filename && event.filename.includes('chrome-extension://')) {
                return;
            }
            
            // 繝｡繝・そ繝ｼ繧ｸ繝昴・繝医お繝ｩ繝ｼ縺ｯ辟｡隕・
            if (event.error && event.error.message && 
                event.error.message.includes('message port closed')) {
                return;
            }
            
            // 縺昴・莉悶・繧ｨ繝ｩ繝ｼ縺ｮ縺ｿ繝ｭ繧ｰ蜃ｺ蜉・
            console.log('JavaScript繧ｨ繝ｩ繝ｼ繧偵く繝｣繝・メ:', event.error);
        });

        window.addEventListener('unhandledrejection', function(event) {
            // Chrome諡｡蠑ｵ讖溯・縺ｮ繧ｨ繝ｩ繝ｼ繧堤┌隕・
            if (event.reason && event.reason.stack && 
                event.reason.stack.includes('chrome-extension://')) {
                event.preventDefault();
                return;
            }
            
            // 繝｡繝・そ繝ｼ繧ｸ繝昴・繝医お繝ｩ繝ｼ縺ｯ辟｡隕・
            if (event.reason && event.reason.message && 
                event.reason.message.includes('message port closed')) {
                event.preventDefault();
                return;
            }
            
            // 縺昴・莉悶・繧ｨ繝ｩ繝ｼ縺ｮ縺ｿ繝ｭ繧ｰ蜃ｺ蜉・
            console.log('譛ｪ蜃ｦ逅・・Promise諡貞凄繧偵く繝｣繝・メ:', event.reason);
        });

        // 荳榊・蜷亥ｱ蜻企未騾｣縺ｮ髢｢謨ｰ
        function loadFeedbackReports() {
            const unresolvedOnly = document.getElementById('unresolvedOnly').checked;
            
            // 邨ｱ險育畑縺ｫ蟶ｸ縺ｫ蜈ｨ繝・・繧ｿ繧貞叙蠕・
            fetch(`/api/get_feedback_reports?unresolved_only=false&t=${Date.now()}` , {
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            })
            .then(response => response.json())
            .then(allData => {
                if (allData.error) {
                    document.getElementById('feedbackReportsContent').innerHTML = 
                        `<p style="color: red; text-align: center; padding: 20px;">繧ｨ繝ｩ繝ｼ: ${allData.error}</p>`;
                    return;
                }
                
                // 邨ｱ險医・蜈ｨ繝・・繧ｿ縺九ｉ險育ｮ・
                updateFeedbackStats(allData.reports || []);
                
                // 陦ｨ遉ｺ逕ｨ繝・・繧ｿ繧貞叙蠕・
                const displayUrl = `/api/get_feedback_reports?unresolved_only=${unresolvedOnly}&t=${Date.now()}`;
                return fetch(displayUrl, {
                    headers: {
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache'
                    }
                });
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    document.getElementById('feedbackReportsContent').innerHTML = 
                        `<p style="color: red; text-align: center; padding: 20px;">繧ｨ繝ｩ繝ｼ: ${data.error}</p>`;
                    return;
                }
                
                const reports = data.reports || [];
                // 荳榊・蜷亥ｱ蜻翫・縺ｿ繧定｡ｨ遉ｺ・・i_positive縺ｯ髯､螟厄ｼ・
                const filteredReports = reports.filter(report => report.report_type !== 'ai_positive');
                renderFeedbackReports(filteredReports);
            })
            .catch(error => {
                console.error('Feedback reports fetch error:', error);
                document.getElementById('feedbackReportsContent').innerHTML = 
                    `<p style="color: red; text-align: center; padding: 20px;">騾壻ｿ｡繧ｨ繝ｩ繝ｼ: ${error.message}</p>`;
            });
        }
        
        function renderFeedbackReports(reports) {
            const content = document.getElementById('feedbackReportsContent');
            
            if (reports.length === 0) {
                content.innerHTML = '<p style="text-align: center; padding: 20px; color: #666;">蝣ｱ蜻翫・縺ゅｊ縺ｾ縺帙ｓ</p>';
                return;
            }
            
            let html = `
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                    <thead>
                        <tr style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">
                            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">蝣ｱ蜻頑律譎・/th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">繧ｿ繧､繝・/th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">繝ｦ繝ｼ繧ｶ繝ｼ</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">繝ｦ繝ｼ繧ｶ繝ｼ繝｡繝・そ繝ｼ繧ｸ</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">AI蠢懃ｭ・隴ｦ蜻・/th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">繧ｹ繧ｳ繧｢</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">繝輔ぅ繝ｼ繝峨ヰ繝・け</th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">迥ｶ諷・/th>
                            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6; color: #000; background-color: #f8f9fa;">謫堺ｽ・/th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            reports.forEach(report => {
                const reportTypeText = {
                    'ai_positive': 'AI隧穂ｾ｡・磯←蛻・ｼ・,
                    'ai_negative': 'AI隧穂ｾ｡・井ｸ埼←蛻・ｼ・,
                    'security_warning': '繧ｻ繧ｭ繝･繝ｪ繝・ぅ隴ｦ蜻・
                }[report.report_type] || report.report_type;
                
                const statusText = report.resolved ? '隗｣豎ｺ貂医∩' : '譛ｪ隗｣豎ｺ';
                const statusColor = report.resolved ? '#28a745' : '#dc3545';
                
                // HTML繧ｿ繧ｰ繧貞炎髯､縺励※繝励Ξ繝ｼ繝ｳ繝・く繧ｹ繝亥喧
                let plainAiResponse = report.ai_response || '-';
                
                // HTML繧ｿ繧ｰ繧貞ｮ悟・縺ｫ蜑企勁・医ｈ繧雁ｼｷ蜉帙↑蜃ｦ逅・ｼ・
                plainAiResponse = plainAiResponse
                    .replace(/<script[^>]*>.*?<\/script>/gi, '')  // script繧ｿ繧ｰ繧貞炎髯､
                    .replace(/<style[^>]*>.*?<\/style>/gi, '')    // style繧ｿ繧ｰ繧貞炎髯､
                    .replace(/<[^>]*>/g, '')  // 谿九ｊ縺ｮHTML繧ｿ繧ｰ繧貞炎髯､
                    .replace(/&lt;/g, '<')   // HTML繧ｨ繝ｳ繝・ぅ繝・ぅ繧偵ョ繧ｳ繝ｼ繝・
                    .replace(/&gt;/g, '>')
                    .replace(/&amp;/g, '&')
                    .replace(/&quot;/g, '"')
                    .replace(/&#39;/g, "'")
                    .replace(/&#x27;/g, "'")
                    .replace(/&nbsp;/g, ' ')
                    .replace(/&apos;/g, "'")
                    .replace(/&hellip;/g, '...')
                    .replace(/&mdash;/g, '窶・)
                    .replace(/&ndash;/g, '窶・)
                    .replace(/&amp;#39;/g, "'")  // 霑ｽ蜉縺ｮHTML繧ｨ繝ｳ繝・ぅ繝・ぅ
                    .replace(/&amp;lt;/g, '<')
                    .replace(/&amp;gt;/g, '>')
                    .replace(/&amp;quot;/g, '"')
                    .replace(/&amp;amp;/g, '&')
                    .replace(/\r?\n/g, ' ') // 謾ｹ陦後ｒ繧ｹ繝壹・繧ｹ縺ｫ
                    .replace(/\s+/g, ' ')  // 隍・焚縺ｮ遨ｺ逋ｽ繧・縺､縺ｫ
                    .replace(/^\s+|\s+$/g, '')  // 蜑榊ｾ後・遨ｺ逋ｽ繧貞炎髯､
                    .trim();
                
                // 50譁・ｭ苓ｶ・・繝懊ち繝ｳ縺ｮ縺ｿ陦ｨ遉ｺ・亥・譁・・繝｢繝ｼ繝繝ｫ・・
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
                                    <button onclick="openAiResponseModal(this)" data-full-text="${plainAiResponse.replace(/"/g, '&quot;')}" class="admin-btn" style="padding: 6px 12px; font-size: 0.8em; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">隧ｳ邏ｰ繧定｡ｨ遉ｺ</button>
                                 </div>`
                            : ''}
                        </td>
                        <td style="padding: 10px; border: 1px solid #dee2e6; color: #333;">${report.security_score ? report.security_score.toFixed(1) : '-'}</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6; max-width: 200px; word-wrap: break-word; color: #333;">${report.feedback_text || '-'}</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6; color: ${statusColor}; font-weight: bold;">${statusText}</td>
                        <td style="padding: 10px; border: 1px solid #dee2e6;">
                            <div style="display:flex; gap:8px; align-items:center; justify-content:center;">
                                ${!report.resolved ? `<button onclick="resolveFeedback(${report.id})" class="admin-btn" style="padding: 6px 10px; font-size: 0.8em;">隗｣豎ｺ貂医∩</button>` : ''}
                                <button onclick="deleteFeedback(${report.id})" class="admin-btn" style="padding: 6px 10px; font-size: 0.8em; background:#dc3545; color:#fff;">蜑企勁</button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            content.innerHTML = html;
        }
        
        function updateFeedbackStats(reports) {
            // 荳榊・蜷亥ｱ蜻翫・縺ｿ繧貞ｯｾ雎｡・・i_positive 縺ｯ邨ｱ險医°繧蛾勁螟厄ｼ・
            const bugReports = (reports || []).filter(r => r.report_type !== 'ai_positive');
            
            // 蜈ｨ蝣ｱ蜻頑焚・医ユ繝ｼ繝悶Ν陦ｨ遉ｺ縺ｨ荳閾ｴ縺輔○繧九◆繧∽ｸ榊・蜷亥ｱ蜻翫・縺ｿ・・
            const totalReports = bugReports.length;
            
            // 隗｣豎ｺ貂医∩繝ｻ譛ｪ隗｣豎ｺ縺ｮ謨ｰ・井ｸ榊・蜷亥ｱ蜻翫・縺ｿ・・
            const resolvedCount = bugReports.filter(r => r.resolved === true).length;
            const unresolvedCount = totalReports - resolvedCount;
            
            // 驕ｩ蛻・・荳埼←蛻・・謨ｰ・・i_positive縺ｨai_negative縺ｮ縺ｿ・・
            const positiveCount = reports.filter(r => r.report_type === 'ai_positive').length;
            const negativeCount = reports.filter(r => r.report_type === 'ai_negative').length;
            const totalFeedback = positiveCount + negativeCount;
            
            // 驕ｩ蛻・紫繝ｻ荳埼←蛻・紫縺ｮ險育ｮ暦ｼ磯←蛻・ｂ繧ｫ繧ｦ繝ｳ繝医↓蜷ｫ繧√ｋ・・
            const positiveRatio = totalFeedback > 0 ? ((positiveCount / totalFeedback) * 100).toFixed(1) : '0.0';
            const negativeRatio = totalFeedback > 0 ? ((negativeCount / totalFeedback) * 100).toFixed(1) : '0.0';
            
            // 邨ｱ險医ョ繝ｼ繧ｿ繧定｡ｨ遉ｺ
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
            // 邵ｮ蟆剰｡ｨ遉ｺ
            const truncatedText = fullText.length > 200 ? fullText.substring(0, 200) + '...' : fullText;
            element.textContent = truncatedText;
            element.style.maxHeight = '80px';
            element.style.overflow = 'hidden';
            element.style.whiteSpace = 'pre-wrap';
            element.setAttribute('data-expanded', 'false');
            if (button) {
                button.textContent = '繧ゅ▲縺ｨ隕九ｋ';
                button.style.backgroundColor = '#007bff';
                button.style.color = 'white';
            }
        } else {
            // 諡｡螟ｧ陦ｨ遉ｺ・医・繝ｬ繝ｼ繝ｳ繝・く繧ｹ繝医→縺励※・・
            element.textContent = fullText;
            element.style.maxHeight = 'none';
            element.style.overflow = 'visible';
            element.style.whiteSpace = 'pre-wrap';
            element.setAttribute('data-expanded', 'true');
            if (button) {
                button.textContent = '髢峨§繧・;
                button.style.backgroundColor = '#6c757d';
                button.style.color = 'white';
            }
        }
    }
        
        // HTML繧ｨ繝ｳ繝・ぅ繝・ぅ繧貞・縺ｮ繧ｿ繧ｰ縺ｫ謌ｻ縺咎未謨ｰ
        function decodeHTMLEntities(text) {
            const textarea = document.createElement('textarea');
            textarea.innerHTML = text;
            return textarea.value;
        }
        
        function resolveFeedback(feedbackId) {
            if (!confirm('縺薙・蝣ｱ蜻翫ｒ隗｣豎ｺ貂医∩縺ｫ繝槭・繧ｯ縺励∪縺吶°・・)) {
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
                    showNotification('蝣ｱ蜻翫ｒ隗｣豎ｺ貂医∩縺ｫ繝槭・繧ｯ縺励∪縺励◆', 'success');
                    loadFeedbackReports(); // 荳隕ｧ繧呈峩譁ｰ
                } else {
                    showNotification(`繧ｨ繝ｩ繝ｼ: ${data.error}`, 'error');
                }
            })
            .catch(error => {
                console.error('Resolve feedback error:', error);
                showNotification(`繧ｨ繝ｩ繝ｼ: ${error.message}`, 'error');
            });
        }

        function deleteFeedback(feedbackId) {
            if (!confirm('縺薙・蝣ｱ蜻翫ｒ蜑企勁縺励∪縺吶°・・)) {
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
                    showNotification('蝣ｱ蜻翫ｒ蜑企勁縺励∪縺励◆', 'success');
                    loadFeedbackReports(); // 荳隕ｧ縺ｨ邨ｱ險医ｒ譖ｴ譁ｰ
                } else {
                    showNotification(`繧ｨ繝ｩ繝ｼ: ${data.error}`, 'error');
                }
            })
            .catch(error => {
                console.error('Delete feedback error:', error);
                showNotification(`繧ｨ繝ｩ繝ｼ: ${error.message}`, 'error');
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
                    showNotification(`繧ｨ繝ｩ繝ｼ: ${data.error}`, 'error');
                    return;
                }
                
                const reports = data.reports || [];
                const csvContent = generateCSV(reports);
                downloadCSV(csvContent, 'feedback_reports.csv');
            })
            .catch(error => {
                console.error('Export feedback reports error:', error);
                showNotification(`繧ｨ繝ｩ繝ｼ: ${error.message}`, 'error');
            });
        }
        
        function generateCSV(reports) {
            const headers = ['蝣ｱ蜻頑律譎・, '繧ｿ繧､繝・, '繝ｦ繝ｼ繧ｶ繝ｼ', '繝ｦ繝ｼ繧ｶ繝ｼ繝｡繝・そ繝ｼ繧ｸ', 'AI蠢懃ｭ・隴ｦ蜻・, '繧ｹ繧ｳ繧｢', '繝輔ぅ繝ｼ繝峨ヰ繝・け', '迥ｶ諷・];
            let csv = headers.join(',') + '\n';
            
            reports.forEach(report => {
                const reportTypeText = {
                    'ai_positive': 'AI隧穂ｾ｡・磯←蛻・ｼ・,
                    'ai_negative': 'AI隧穂ｾ｡・井ｸ埼←蛻・ｼ・,
                    'security_warning': '繧ｻ繧ｭ繝･繝ｪ繝・ぅ隴ｦ蜻・
                }[report.report_type] || report.report_type;
                
                const statusText = report.resolved ? '隗｣豎ｺ貂医∩' : '譛ｪ隗｣豎ｺ';
                
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

        // 荳榊・蜷亥ｱ蜻・ AI蠢懃ｭ泌・譁・Δ繝ｼ繝繝ｫ
        function openAiResponseModal(buttonEl) {
            const fullText = buttonEl.getAttribute('data-full-text') || '';
            const modal = document.getElementById('aiFullTextModal');
            const body = document.getElementById('aiFullTextBody');
            if (modal && body) {
                body.textContent = fullText; // 繝励Ξ繝ｼ繝ｳ繝・く繧ｹ繝医→縺励※螳牙・縺ｫ陦ｨ遉ｺ
                modal.style.display = 'block';
            }
        }
        function closeAiResponseModal() {
            const modal = document.getElementById('aiFullTextModal');
            if (modal) modal.style.display = 'none';
        }

        // 繧ｹ繧ｳ繧｢隧ｳ邏ｰ繝｢繝ｼ繝繝ｫ髢｢騾｣縺ｮ髢｢謨ｰ
        function showScoreModal(medicineId, medicineIndex) {
            // 迴ｾ蝨ｨ縺ｮ繧ｻ繝・す繝ｧ繝ｳ縺ｮ隧ｳ邏ｰ險ｺ譁ｭ繝・・繧ｿ繧貞叙蠕・
            const adminDiag = (currentDetailedDiagnosis && currentDetailedDiagnosis.session_id === currentSessionId && Array.isArray(currentDetailedDiagnosis.recommended_medicines))
                ? currentDetailedDiagnosis
                : null;
            
            if (!adminDiag || !adminDiag.recommended_medicines || !adminDiag.recommended_medicines[medicineIndex]) {
                alert('繧ｹ繧ｳ繧｢諠・ｱ縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ縲・);
                return;
            }
            
            const medicine = adminDiag.recommended_medicines[medicineIndex];
            const scoreHtml = generateScoreDetailHtml(medicine);
            
            // 繝｢繝ｼ繝繝ｫ縺ｫ陦ｨ遉ｺ
            document.getElementById('scoreModalContent').innerHTML = scoreHtml;
            document.getElementById('scoreModal').style.display = 'block';
        }

        // 繧ｻ繝・す繝ｧ繝ｳ邂｡逅・ｩ溯・
        function openSessionManagement() {
            document.getElementById('sessionManagementModal').style.display = 'block';
            refreshSessionManagement();
        }
        
        function closeSessionManagement() {
            document.getElementById('sessionManagementModal').style.display = 'none';
        }
        
        function refreshSessionManagement() {
            const listContainer = document.getElementById('session-management-list');
            listContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: #888;">隱ｭ縺ｿ霎ｼ縺ｿ荳ｭ...</div>';
            
            fetch('/api/admin/sessions')
                .then(response => response.json())
                .then(data => {
                    if (data.sessions && data.sessions.length > 0) {
                        renderSessionManagementList(data.sessions);
                    } else {
                        listContainer.innerHTML = '<div style="text-align: center; padding: 50px; color: #888;"><div style="font-size: 3em;">働</div><p style="margin-top: 10px;">繧ｻ繝・す繝ｧ繝ｳ縺後≠繧翫∪縺帙ｓ</p></div>';
                    }
                })
                .catch(error => {
                    console.error('Error loading sessions:', error);
                    listContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: red;">繧ｨ繝ｩ繝ｼ: 繧ｻ繝・す繝ｧ繝ｳ諠・ｱ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ螟ｱ謨励＠縺ｾ縺励◆</div>';
                });
        }
        
        function renderSessionManagementList(sessions) {
            const listContainer = document.getElementById('session-management-list');
            let html = '<div style="display: grid; gap: 10px;">';
            
            sessions.forEach(session => {
                const lastActivity = session.last_activity ? new Date(session.last_activity * 1000).toLocaleString('ja-JP') : '荳肴・';
                const sessionActive = session.session_active !== false ? '笨・繧｢繧ｯ繝・ぅ繝・ : '笶・邨ゆｺ・;
                const messageCount = session.messages ? session.messages.length : 0;
                
                html += `
                    <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: white;">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                            <div style="flex: 1;">
                                <div style="font-weight: bold; font-size: 1.1em; margin-bottom: 5px;">${escapeHtml(session.username || 'Unknown')}</div>
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 3px;">ID: <code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px;">${escapeHtml(session.session_id)}</code></div>
                                <div style="font-size: 0.85em; color: #666; margin-bottom: 3px;">${sessionActive} | 繝｡繝・そ繝ｼ繧ｸ謨ｰ: ${messageCount}</div>
                                <div style="font-size: 0.85em; color: #666;">譛邨ゅい繧ｯ繝・ぅ繝薙ユ繧｣: ${lastActivity}</div>
                                ${session.client_ip ? `<div style="font-size: 0.85em; color: #666;">IP: ${escapeHtml(session.client_ip)}</div>` : ''}
                            </div>
                            <div style="display: flex; gap: 5px; flex-direction: column;">
                                <button class="btn btn-danger" onclick="deleteSession('${session.session_id}')" style="padding: 5px 10px; font-size: 0.8em;">卵・・蜑企勁</button>
                                <button class="btn btn-info" onclick="editSession('${session.session_id}')" style="padding: 5px 10px; font-size: 0.8em;">笨擾ｸ・邱ｨ髮・/button>
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
            if (!confirm(`繧ｻ繝・す繝ｧ繝ｳ縲・{sessionId}縲阪ｒ蜑企勁縺励※繧ゅｈ繧阪＠縺・〒縺吶°・歔)) {
                return;
            }
            
            fetch(`/api/admin/sessions/${sessionId}`, {
                method: 'DELETE'
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert('笨・' + data.message);
                        refreshSessionManagement();
                    } else {
                        alert('笶・繧ｨ繝ｩ繝ｼ: ' + (data.message || '蜑企勁縺ｫ螟ｱ謨励＠縺ｾ縺励◆'));
                    }
                })
                .catch(error => {
                    console.error('Error deleting session:', error);
                    alert('笶・騾壻ｿ｡繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆');
                });
        }
        
        function deleteAllSessions() {
            if (!confirm('笞・・縺吶∋縺ｦ縺ｮ繧ｻ繝・す繝ｧ繝ｳ繧貞炎髯､縺励※繧ゅｈ繧阪＠縺・〒縺吶°・歃n縺薙・謫堺ｽ懊・蜿悶ｊ豸医○縺ｾ縺帙ｓ縲・)) {
                return;
            }
            
            if (!confirm('笞・・譛ｬ蠖薙↓蜑企勁縺励∪縺吶°・・)) {
                return;
            }
            
            fetch('/api/admin/sessions/delete_all', {
                method: 'DELETE'
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        alert(`笨・${data.deleted_count || 0}莉ｶ縺ｮ繧ｻ繝・す繝ｧ繝ｳ繧貞炎髯､縺励∪縺励◆`);
                        refreshSessionManagement();
                    } else {
                        alert('笶・繧ｨ繝ｩ繝ｼ: ' + (data.message || '蜑企勁縺ｫ螟ｱ謨励＠縺ｾ縺励◆'));
                    }
                })
                .catch(error => {
                    console.error('Error deleting all sessions:', error);
                    alert('笶・騾壻ｿ｡繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆');
                });
        }
        
        function editSession(sessionId) {
            // 繧ｻ繝・す繝ｧ繝ｳ邱ｨ髮・ｩ溯・・育ｰ｡譏鍋沿・・
            fetch(`/api/admin/sessions`)
                .then(response => response.json())
                .then(data => {
                    const session = data.sessions.find(s => s.session_id === sessionId);
                    if (!session) {
                        alert('繧ｻ繝・す繝ｧ繝ｳ縺瑚ｦ九▽縺九ｊ縺ｾ縺帙ｓ');
                        return;
                    }
                    
                    const newUsername = prompt('譁ｰ縺励＞繝ｦ繝ｼ繧ｶ繝ｼ蜷阪ｒ蜈･蜉帙＠縺ｦ縺上□縺輔＞:', session.username || 'Unknown');
                    if (newUsername === null) return;
                    
                    const newActive = confirm('繧ｻ繝・す繝ｧ繝ｳ繧偵い繧ｯ繝・ぅ繝悶↓縺励∪縺吶°・歃n・・K: 繧｢繧ｯ繝・ぅ繝悶√く繝｣繝ｳ繧ｻ繝ｫ: 邨ゆｺ・ｼ・);
                    
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
                                alert('笨・' + data.message);
                                refreshSessionManagement();
                            } else {
                                alert('笶・繧ｨ繝ｩ繝ｼ: ' + (data.message || '譖ｴ譁ｰ縺ｫ螟ｱ謨励＠縺ｾ縺励◆'));
                            }
                        })
                        .catch(error => {
                            console.error('Error updating session:', error);
                            alert('笶・騾壻ｿ｡繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆');
                        });
                })
                .catch(error => {
                    console.error('Error loading session:', error);
                    alert('笶・繧ｻ繝・す繝ｧ繝ｳ諠・ｱ縺ｮ隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ螟ｱ謨励＠縺ｾ縺励◆');
                });
        }
        
        function closeScoreModal() {
            document.getElementById('scoreModal').style.display = 'none';
        }

        function generateScoreDetailHtml(medicine) {
            if (!medicine.score) {
                return '<p>繧ｹ繧ｳ繧｢諠・ｱ縺後≠繧翫∪縺帙ｓ縲・/p>';
            }
            
            const breakdown = medicine.scores || medicine.score_breakdown || {};
            const score = medicine.score;
            const scoreClass = score >= 0.7 ? 'high' : score >= 0.5 ? 'medium' : 'low';
            
            // 繧ｹ繧ｳ繧｢險育ｮ励・繝ｫ繝代・
            const pct = (v) => {
                if (v === undefined || v === null || isNaN(v)) return 0;
                return Math.max(0, Math.min(100, Math.round(v * 100)));
            };
            const riskToPct = (v) => {
                if (v === undefined || v === null || isNaN(v)) return 100;
                return Math.max(0, Math.min(100, Math.round((1 + v) * 100)));
            };

            // 蜷・せ繧ｳ繧｢謚ｽ蜃ｺ
            const symptom = breakdown.symptom_match ?? breakdown.symptom_match_score ?? 0;
            const efficacy = breakdown.efficacy_specificity ?? breakdown.efficacy_specificity_score ?? 0;
            const age = breakdown.age_fit ?? breakdown.age_suitability_score ?? 0;
            const usage = breakdown.usage_convenience ?? breakdown.dosage_convenience_score ?? 0;
            const sideRisk = breakdown.side_effect_risk ?? breakdown.side_effect_risk_score ?? 0;
            const interRisk = breakdown.interaction_risk ?? breakdown.interaction_risk_score ?? 0;

            return `
                <div class="score-detail">
                    <h4>${escapeHtml(medicine.product_name || medicine.name || 'N/A')}</h4>
                    <div class="overall-score">
                        <div class="score-circle ${scoreClass}">
                            ${(score * 100).toFixed(0)}%
                        </div>
                        <p style="margin-top: 10px; font-size: 18px;">譛驕ｩ蠎ｦ: ${score >= 0.7 ? '鬮・ : score >= 0.5 ? '荳ｭ' : '菴・}</p>
                    </div>
                    
                    <div class="score-breakdown">
                        <h5>6隕∫ｴ繧ｹ繧ｳ繧｢繝ｪ繝ｳ繧ｰ隧ｳ邏ｰ</h5>
                        <div class="score-items">
                            <div class="score-item">
                                <span class="score-label">逞・憾驕ｩ蜷亥ｺｦ</span>
                                <div class="score-bar">
                                    <div class="score-fill" style="width: ${pct(symptom)}%; background: #4CAF50;"></div>
                                </div>
                                <span class="score-value">${pct(symptom)}%</span>
                            </div>
                            <div class="score-item">
                                <span class="score-label">蜉ｹ閭ｽ迚ｹ逡ｰ諤ｧ</span>
                                <div class="score-bar">
                                    <div class="score-fill" style="width: ${pct(efficacy)}%; background: #2196F3;"></div>
                                </div>
                                <span class="score-value">${pct(efficacy)}%</span>
                            </div>
                            <div class="score-item">
                                <span class="score-label">蟷ｴ鮨｢驕ｩ蜷域ｧ</span>
                                <div class="score-bar">
                                    <div class="score-fill" style="width: ${pct(age)}%; background: #9C27B0;"></div>
                                </div>
                                <span class="score-value">${pct(age)}%</span>
                            </div>
                            <div class="score-item">
                                <span class="score-label">逕ｨ豕慕ｰ｡萓ｿ諤ｧ</span>
                                <div class="score-bar">
                                    <div class="score-fill" style="width: ${pct(usage)}%; background: #FF9800;"></div>
                                </div>
                                <span class="score-value">${pct(usage)}%</span>
                            </div>
                            <div class="score-item">
                                <span class="score-label">蜑ｯ菴懃畑繝ｪ繧ｹ繧ｯ</span>
                                <div class="score-bar">
                                    <div class="score-fill" style="width: ${riskToPct(sideRisk)}%; background: #F44336;"></div>
                                </div>
                                <span class="score-value">${riskToPct(sideRisk)}%</span>
                            </div>
                            <div class="score-item">
                                <span class="score-label">逶ｸ莠剃ｽ懃畑繝ｪ繧ｹ繧ｯ</span>
                                <div class="score-bar">
                                    <div class="score-fill" style="width: ${riskToPct(interRisk)}%; background: #795548;"></div>
                                </div>
                                <span class="score-value">${riskToPct(interRisk)}%</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
