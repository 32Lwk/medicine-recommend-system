/**
 * Sage アバター — コントローラー（感情・モーション・まばたき・リップシンク）
 *
 * レンダラー（SpriteAvatarRenderer / 将来の Cubism レンダラー）に依存しない層。
 * レンダラーは applyPose / setExpression / setEyes / setMouth を実装していればよい。
 *
 *   var avatar = new SageAvatar(renderer);
 *   avatar.setEmotion('worry');
 *   avatar.playMotion('nod');
 *   avatar.speak('[心配]それはおつらいですね。お大事にしてください。', { autoEmotion: true });
 */
(function (global) {
    'use strict';

    /* ---------- 感情: 表情 + 姿勢のかたより + 入りのモーション ---------- */

    var EMOTIONS = {
        neutral: { label: '通常', expr: 'neutral', bias: {} },
        smile: { label: '微笑み', expr: 'smile', bias: { angleZ: 2, angleY: 1 }, enter: 'nod' },
        thinking: { label: '思案', expr: 'thinking', bias: { angleZ: 7, angleX: 8, angleY: 6 } },
        empathy: { label: '共感', expr: 'empathy', bias: { angleZ: 4, angleY: -3, lean: 0.15 }, enter: 'nodSlow' },
        surprise: { label: '軽い驚き', expr: 'surprise', bias: { angleY: 5, lean: -0.1 }, enter: 'flinch' },
        relief: { label: '安心', expr: 'relief', bias: { angleY: 1, angleZ: -2 }, enter: 'nod' },
        worry: { label: '心配', expr: 'worry', bias: { angleZ: 5, angleY: -3, lean: 0.25 } },
        sorry: { label: '申し訳なさ', expr: 'sorry', bias: { angleY: -5, angleZ: -3 }, enter: 'bow' },
        serious: { label: '真剣', expr: 'serious', bias: { angleY: -2, lean: 0.3 } },
        cheer: { label: '励まし', expr: 'cheer', bias: { angleY: 3 }, enter: 'hop' },
        shy: { label: '照れ', expr: 'shy', bias: { angleX: -12, angleY: -5, angleZ: 6 } },
        confused: { label: '困惑', expr: 'confused', bias: { angleZ: -9, angleY: 3 } },
    };

    /* ---------- モーション: [秒, 値] のキーフレーム（待機の揺れに加算） ---------- */

    var MOTIONS = {
        nod: { label: 'うなずき', tracks: { angleY: [[0, 0], [0.18, -11], [0.38, 2], [0.55, -4], [0.75, 0]] } },
        nodDeep: {
            label: '深くうなずき',
            tracks: { angleY: [[0, 0], [0.3, -22], [0.65, 3], [0.95, 0]], lean: [[0, 0], [0.3, 0.15], [0.95, 0]] },
        },
        nodSlow: { label: 'ゆっくりうなずき', tracks: { angleY: [[0, 0], [0.4, -12], [0.9, 0], [1.3, -8], [1.8, 0]] } },
        tilt: {
            label: '首かしげ',
            tracks: { angleZ: [[0, 0], [0.45, 13], [1.8, 13], [2.3, 0]], angleX: [[0, 0], [0.45, 5], [1.8, 5], [2.3, 0]] },
        },
        shake: { label: '首を横に振る', tracks: { angleX: [[0, 0], [0.16, -16], [0.38, 16], [0.6, -13], [0.82, 9], [1.0, 0]] } },
        lookLeft: {
            label: '左を見る',
            tracks: { angleX: [[0, 0], [0.4, -20], [1.7, -20], [2.2, 0]], angleY: [[0, 0], [0.4, 2], [1.7, 2], [2.2, 0]] },
        },
        lookRight: {
            label: '右を見る',
            tracks: { angleX: [[0, 0], [0.4, 20], [1.7, 20], [2.2, 0]], angleY: [[0, 0], [0.4, 2], [1.7, 2], [2.2, 0]] },
        },
        lean: {
            label: '前のめり',
            tracks: { lean: [[0, 0], [0.5, 1], [2.3, 1], [2.9, 0]], angleY: [[0, 0], [0.5, -4], [2.3, -4], [2.9, 0]] },
        },
        bow: {
            label: 'お辞儀',
            tracks: { bow: [[0, 0], [0.5, 1], [1.2, 1], [1.8, 0]], angleY: [[0, 0], [0.5, -24], [1.2, -24], [1.8, 0]] },
        },
        hop: {
            label: '弾む',
            tracks: {
                hop: [[0, 0], [0.13, 22], [0.26, 0], [0.4, 14], [0.53, 0]],
                angleY: [[0, 0], [0.13, 4], [0.26, 0], [0.4, 3], [0.53, 0]],
            },
        },
        flinch: { label: 'のけぞり', tracks: { angleY: [[0, 0], [0.12, 8], [0.6, 0]], lean: [[0, 0], [0.12, -0.25], [0.6, 0]] } },
    };

    /* ---------- 台本: タグとキーワード ---------- */

    var EMOTION_TAGS = {
        通常: 'neutral', 微笑み: 'smile', 笑顔: 'smile', 思案: 'thinking', 考え中: 'thinking', 共感: 'empathy',
        驚き: 'surprise', 安心: 'relief', 心配: 'worry', 申し訳なさ: 'sorry', おわび: 'sorry', 謝罪: 'sorry',
        真剣: 'serious', 励まし: 'cheer', 照れ: 'shy', 困惑: 'confused',
    };
    var MOTION_TAGS = {
        うなずき: 'nod', 深くうなずき: 'nodDeep', 首かしげ: 'tilt', 首振り: 'shake', 左を見る: 'lookLeft',
        右を見る: 'lookRight', 前のめり: 'lean', お辞儀: 'bow', 弾む: 'hop',
    };
    // 上から順に評価し、最初に当たった感情を採用
    var EMOTION_KEYWORDS = [
        [/申し訳|すみません|すいません|ごめん|失礼いたしました/, 'sorry'],
        [/救急|すぐに?(医療機関|病院)|受診|医師|副作用|危険|使用を(中止|控え)|飲まないで|必ず|絶対に/, 'serious'],
        [/ご安心|安心して|よかった|良かった|ほっと|心配(は)?(いりません|ありません)|問題(は)?ありません/, 'relief'],
        [/お大事に|がんば|頑張|応援|きっと良く|元気になり/, 'cheer'],
        [/心配|おつらい|お辛い|つらい|辛い|苦しい|大丈夫ですか|痛み|痛い|熱が/, 'worry'],
        [/えっ|まさか|本当ですか|驚き/, 'surprise'],
        [/照れ|恥ずかし|褒めて/, 'shy'],
        [/どういう(こと|意味)|わかりません|分かりません|うーん|よく分から/, 'confused'],
        [/確認します|お調べ|調べます|少々お待ち|考えて/, 'thinking'],
        [/なるほど|わかります|分かります|そうなんですね|それは大変/, 'empathy'],
        [/こんにちは|こんばんは|おはよう|ありがとう|いらっしゃい/, 'smile'],
    ];
    var MOTION_KEYWORDS = [
        [/よろしくお願いします|ありがとうございました/, 'bow'],
        [/おすすめできません|お控えください|やめて/, 'shake'],
        [/^(はい|ええ|そうですね)/, 'nod'],
        [/[？?]\s*$/, 'tilt'],
    ];

    /* ---------- 口形 ---------- */

    // U+3041 (ぁ) .. U+3096 (ゖ) の母音。'-' は口を閉じる（っ・ん）
    var HIRAGANA_VOWELS =
        'aaiiuueeoo' + 'aaiiuueeoo' + 'aaiiuueeoo' + 'aaii-uueeoo' + 'aiueo' +
        'aaaiiiuuueeeooo' + 'aiueo' + 'aauuoo' + 'aiueo' + 'aaieo-uae';
    var RANDOM_VOWELS = ['a', 'i', 'u', 'e', 'o'];
    var VISEME_LEVEL = { a: 1, o: 0.8, e: 0.6, i: 0.4, u: 0.3 };

    var MORA_MS = 120;
    var MIN_VISEME_HOLD_MS = 70;
    var BIAS_RATE = 3.5; // 1/s — 感情の姿勢へ移る速さ

    function randomBetween(min, max) {
        return min + Math.random() * (max - min);
    }

    function textToVisemes(text) {
        var out = [];
        var last = null;
        for (var i = 0; i < text.length; i++) {
            var c = text.charCodeAt(i);
            var ch = text.charAt(i);
            var v;
            if (c >= 0x30a1 && c <= 0x30f6) c -= 0x60;
            if (c >= 0x3041 && c <= 0x3096) {
                v = HIRAGANA_VOWELS.charAt(c - 0x3041);
                out.push(v === '-' ? null : v);
            } else if (c === 0x30fc) {
                out.push(last);
            } else if (c >= 0x4e00 && c <= 0x9fff) {
                out.push(RANDOM_VOWELS[(c * 7) % 5], RANDOM_VOWELS[(c * 13) % 5]);
            } else if ('、。，．！？!?,.\n'.indexOf(ch) >= 0) {
                out.push(null, null, null);
            } else if ('aiueoAIUEO'.indexOf(ch) >= 0) {
                out.push(ch.toLowerCase());
            }
            if (out.length) last = out[out.length - 1];
        }
        return out;
    }

    function pickViseme(level, centroidHz) {
        if (level < 0.18) return null;
        if (level > 0.62) return centroidHz < 1000 ? 'o' : 'a';
        if (level > 0.38) {
            if (centroidHz > 1700) return 'e';
            return centroidHz < 900 ? 'o' : 'a';
        }
        return centroidHz > 1600 ? 'i' : 'u';
    }

    function sampleTrack(track, t) {
        if (t <= track[0][0]) return track[0][1];
        for (var i = 1; i < track.length; i++) {
            if (t <= track[i][0]) {
                var t0 = track[i - 1][0];
                var u = (t - t0) / (track[i][0] - t0);
                var s = u * u * (3 - 2 * u);
                return track[i - 1][1] + (track[i][1] - track[i - 1][1]) * s;
            }
        }
        return track[track.length - 1][1];
    }

    function motionDuration(def) {
        var d = 0;
        for (var k in def.tracks) {
            if (Object.prototype.hasOwnProperty.call(def.tracks, k)) {
                var tr = def.tracks[k];
                d = Math.max(d, tr[tr.length - 1][0]);
            }
        }
        return d;
    }

    /**
     * 台本を文ごとに分け、各文の感情・モーションを決める。
     * タグ（[心配] [お辞儀] など）が優先、なければキーワードから推定（autoEmotion 時）。
     */
    function parseScript(text, autoEmotion) {
        var sentences = String(text || '').match(/[^。！？!?\n]+[。！？!?\n]*/g) || [];
        var segs = [];
        for (var i = 0; i < sentences.length; i++) {
            var raw = sentences[i];
            var emotion = null;
            var motions = [];
            var body = raw.replace(/[\[［]([^\]］]+)[\]］]/g, function (_, name) {
                name = name.trim();
                if (EMOTION_TAGS[name] || EMOTIONS[name]) emotion = EMOTION_TAGS[name] || name;
                else if (MOTION_TAGS[name] || MOTIONS[name]) motions.push(MOTION_TAGS[name] || name);
                return '';
            }).trim();
            if (autoEmotion && body) {
                if (!emotion) {
                    for (var k = 0; k < EMOTION_KEYWORDS.length; k++) {
                        if (EMOTION_KEYWORDS[k][0].test(body)) { emotion = EMOTION_KEYWORDS[k][1]; break; }
                    }
                }
                if (!motions.length) {
                    for (var j = 0; j < MOTION_KEYWORDS.length; j++) {
                        if (MOTION_KEYWORDS[j][0].test(body)) { motions.push(MOTION_KEYWORDS[j][1]); break; }
                    }
                }
            }
            if (!body && !emotion && !motions.length) continue;
            segs.push({ text: body, emotion: emotion, motions: motions });
        }
        return segs;
    }

    /* ---------- SageAvatar ---------- */

    function SageAvatar(renderer, options) {
        var opts = options || {};
        this.renderer = renderer;
        this.lang = opts.lang || 'ja';
        this.ttsUrl = opts.ttsUrl || ((global.APP_BASE_PATH || '') + '/api/tts');
        this.useServerTts = opts.useServerTts !== false;
        this.onSpeakingChange = opts.onSpeakingChange || null;
        this.onEmotionChange = opts.onEmotionChange || null;
        this.onSegment = opts.onSegment || null;
        this.idleAmount = opts.idleAmount == null ? 1 : opts.idleAmount;

        this.emotion = 'neutral';
        this.speaking = false;
        this._token = 0;
        this._blinkTimer = null;
        this._blinking = false;
        this._audio = null;
        this._audioCtx = null;
        this._lipRaf = null;
        this._speechTimer = null;
        this._neutralTimer = null;

        this._bias = {};
        this._biasTarget = {};
        this._motions = [];
        this._mouthLevel = 0;
        this._mouthLevelSmooth = 0;
        this._lastTick = 0;
        this._raf = null;

        this._tick = this._tick.bind(this);
        this._raf = requestAnimationFrame(this._tick);
        if (opts.autoBlink !== false) this.startAutoBlink();
    }

    SageAvatar.EMOTIONS = EMOTIONS;
    SageAvatar.MOTIONS = MOTIONS;
    SageAvatar.parseScript = parseScript;
    SageAvatar.textToVisemes = textToVisemes;

    /* ---------- 姿勢ループ ---------- */

    SageAvatar.prototype._tick = function (now) {
        var dt = this._lastTick ? Math.min((now - this._lastTick) / 1000, 0.1) : 0;
        this._lastTick = now;
        var t = now / 1000;
        var ia = this.idleAmount;
        var pose = {
            angleX: ia * (3.5 * Math.sin(t * 0.37) + 1.5 * Math.sin(t * 0.91 + 0.5)),
            angleY: ia * (2 * Math.sin(t * 0.53 + 1) + 0.8 * Math.sin(t * 1.3)),
            angleZ: ia * (1.2 * Math.sin(t * 0.29 + 2)),
            bodyAngleZ: ia * (0.6 * Math.sin(t * 0.23 + 0.3)),
            lean: 0,
            bow: 0,
            hop: 0,
            breath: (Math.sin(t * 2 * Math.PI / 4.2) + 1) / 2,
        };

        var k = 1 - Math.exp(-dt * BIAS_RATE);
        var keys = ['angleX', 'angleY', 'angleZ', 'bodyAngleZ', 'lean'];
        for (var i = 0; i < keys.length; i++) {
            var name = keys[i];
            var cur = this._bias[name] || 0;
            cur += ((this._biasTarget[name] || 0) - cur) * k;
            this._bias[name] = cur;
            pose[name] += cur;
        }

        var alive = [];
        for (var m = 0; m < this._motions.length; m++) {
            var mo = this._motions[m];
            var el = (now - mo.start) / 1000;
            if (el > mo.duration) continue;
            alive.push(mo);
            for (var p in mo.def.tracks) {
                if (Object.prototype.hasOwnProperty.call(mo.def.tracks, p)) {
                    pose[p] = (pose[p] || 0) + sampleTrack(mo.def.tracks[p], el) * mo.scale;
                }
            }
        }
        this._motions = alive;

        this._mouthLevelSmooth += (this._mouthLevel - this._mouthLevelSmooth) * (1 - Math.exp(-dt * 12));
        pose.angleY += this._mouthLevelSmooth * 2.2;

        this.renderer.applyPose(pose);
        this._raf = requestAnimationFrame(this._tick);
    };

    /* ---------- 感情・モーション ---------- */

    SageAvatar.prototype.setEmotion = function (name, opts) {
        var def = EMOTIONS[name] || EMOTIONS.neutral;
        clearTimeout(this._neutralTimer);
        var changed = this.emotion !== name;
        this.emotion = EMOTIONS[name] ? name : 'neutral';
        this.renderer.setExpression(def.expr);
        this._biasTarget = def.bias || {};
        if (changed && def.enter && !(opts && opts.motion === false)) {
            this.playMotion(def.enter);
        }
        if (typeof this.onEmotionChange === 'function') this.onEmotionChange(this.emotion);
    };

    SageAvatar.prototype.playMotion = function (name, opts) {
        var def = MOTIONS[name];
        if (!def) return;
        var scale = opts && opts.scale != null ? opts.scale : 1;
        this._motions = this._motions.filter(function (mo) { return mo.name !== name; });
        this._motions.push({
            name: name, def: def, scale: scale, start: performance.now(), duration: motionDuration(def),
        });
    };

    /** 旧 API 互換（idle / greeting / thinking / empathy / caution / nod） */
    SageAvatar.prototype.setState = function (state) {
        var map = { idle: 'neutral', greeting: 'smile', caution: 'surprise' };
        if (state === 'nod') {
            this.playMotion('nod');
            return;
        }
        this.setEmotion(map[state] || state);
    };

    /* ---------- まばたき ---------- */

    SageAvatar.prototype.startAutoBlink = function () {
        var self = this;
        this.stopAutoBlink();
        var schedule = function () {
            self._blinkTimer = setTimeout(function () {
                self.blink().then(function () {
                    if (Math.random() < 0.15) {
                        return new Promise(function (r) { setTimeout(r, 140); }).then(function () {
                            return self.blink();
                        });
                    }
                }).then(schedule);
            }, randomBetween(2500, 6000));
        };
        schedule();
    };

    SageAvatar.prototype.stopAutoBlink = function () {
        clearTimeout(this._blinkTimer);
        this._blinkTimer = null;
    };

    SageAvatar.prototype.blink = function () {
        var self = this;
        if (this._blinking) return Promise.resolve();
        this._blinking = true;
        var steps = [['half', 50], ['closed', 80], ['half', 50], ['open', 0]];
        return steps.reduce(function (p, step) {
            return p.then(function () {
                self.renderer.setEyes(step[0]);
                return new Promise(function (r) { setTimeout(r, step[1]); });
            });
        }, Promise.resolve()).then(function () {
            self._blinking = false;
        });
    };

    /* ---------- 口 ---------- */

    SageAvatar.prototype._setMouth = function (viseme, level) {
        this.renderer.setMouth(viseme || null);
        this._mouthLevel = level != null ? level : (viseme ? VISEME_LEVEL[viseme] || 0.5 : 0);
    };

    SageAvatar.prototype.setMouth = function (viseme) {
        this._setMouth(viseme);
    };

    /* ---------- 読み上げ ---------- */

    SageAvatar.prototype._setSpeaking = function (on) {
        if (this.speaking === on) return;
        this.speaking = on;
        if (typeof this.onSpeakingChange === 'function') this.onSpeakingChange(on);
    };

    SageAvatar.prototype.stopSpeaking = function () {
        this._token++;
        if (this._audio) {
            this._audio.pause();
            this._audio = null;
        }
        if (typeof speechSynthesis !== 'undefined' && speechSynthesis) {
            speechSynthesis.cancel();
        }
        cancelAnimationFrame(this._lipRaf);
        clearTimeout(this._speechTimer);
        this._lipRaf = null;
        this._speechTimer = null;
        this._setMouth(null);
        this._setSpeaking(false);
    };

    /**
     * テキストを読み上げて口を動かす。
     * options.autoEmotion: true なら文ごとにタグ・キーワードから感情とモーションを切り替える。
     * @returns {Promise<'server'|'webspeech'|'none'>}
     */
    SageAvatar.prototype.speak = function (text, options) {
        var self = this;
        var opts = options || {};
        this.stopSpeaking();
        clearTimeout(this._neutralTimer);
        this._ensureAudioContext();
        var token = this._token;
        var segs = parseScript(text, !!opts.autoEmotion);
        if (!segs.length) return Promise.resolve('none');

        var mode = 'none';
        var startedEmotion = this.emotion;
        this._setSpeaking(true);
        var run = segs.reduce(function (p, seg, idx) {
            return p.then(function () {
                if (token !== self._token) return;
                if (seg.emotion) self.setEmotion(seg.emotion);
                for (var i = 0; i < seg.motions.length; i++) self.playMotion(seg.motions[i]);
                if (!seg.motions.length && !seg.emotion && idx > 0) self.playMotion('nod', { scale: 0.35 });
                if (typeof self.onSegment === 'function') self.onSegment(seg, idx);
                if (!seg.text) return new Promise(function (r) { setTimeout(r, 600); });
                return self._speakSegment(seg.text, token).then(function (m) {
                    if (m !== 'none') mode = m;
                });
            });
        }, Promise.resolve());

        return run.then(function () {
            if (token === self._token) {
                self._setMouth(null);
                self._setSpeaking(false);
                if (opts.autoEmotion && self.emotion !== startedEmotion) {
                    self._neutralTimer = setTimeout(function () { self.setEmotion('neutral'); }, 1800);
                }
            }
            return mode;
        });
    };

    SageAvatar.prototype._speakSegment = function (text, token) {
        var self = this;
        if (!this.useServerTts) return this._speakWebSpeech(text, token);
        return fetch(this.ttsUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, lang: this.lang }),
        })
            .then(function (res) {
                if (!res.ok) throw new Error('TTS HTTP ' + res.status);
                return res.blob();
            })
            .then(function (blob) {
                if (token !== self._token) return 'none';
                return self._playAudio(URL.createObjectURL(blob), token).then(function () { return 'server'; });
            })
            .catch(function () {
                if (token !== self._token) return 'none';
                self.useServerTts = false;
                return self._speakWebSpeech(text, token);
            });
    };

    /** 任意の音声 URL（blob: 含む）を再生し、音量解析で口を動かす。 */
    SageAvatar.prototype.playAudioUrl = function (url) {
        var self = this;
        this.stopSpeaking();
        this._ensureAudioContext();
        var token = this._token;
        this._setSpeaking(true);
        return this._playAudio(url, token).then(function () {
            if (token === self._token) self._setSpeaking(false);
        }, function (err) {
            if (token === self._token) self._setSpeaking(false);
            throw err;
        });
    };

    SageAvatar.prototype._playAudio = function (url, token) {
        var self = this;
        var audio = new Audio(url);
        this._audio = audio;
        var stopLipSync = this._attachLipSync(audio, token);
        return new Promise(function (resolve, reject) {
            var cleanup = function () {
                stopLipSync();
                if (url.indexOf('blob:') === 0) URL.revokeObjectURL(url);
                if (token === self._token) {
                    self._setMouth(null);
                    self._audio = null;
                }
            };
            audio.onended = function () { cleanup(); resolve(); };
            audio.onerror = function () { cleanup(); reject(new Error('audio playback failed')); };
            audio.play().catch(function (err) { cleanup(); reject(err); });
        });
    };

    SageAvatar.prototype._ensureAudioContext = function () {
        var Ctx = global.AudioContext || global.webkitAudioContext;
        if (!Ctx) return null;
        if (!this._audioCtx) this._audioCtx = new Ctx();
        if (this._audioCtx.state === 'suspended') this._audioCtx.resume();
        return this._audioCtx;
    };

    SageAvatar.prototype._attachLipSync = function (audio, token) {
        var self = this;
        var ctx = this._audioCtx;
        if (!ctx) return this._pseudoLipSync(token);
        var source = ctx.createMediaElementSource(audio);
        var analyser = ctx.createAnalyser();
        analyser.fftSize = 1024;
        analyser.smoothingTimeConstant = 0.5;
        source.connect(analyser);
        analyser.connect(ctx.destination);

        var time = new Float32Array(analyser.fftSize);
        var freq = new Uint8Array(analyser.frequencyBinCount);
        var binHz = ctx.sampleRate / analyser.fftSize;
        var maxBin = Math.min(freq.length, Math.round(4000 / binHz));
        var peak = 0.05;
        var level = 0;
        var current = null;
        var lastSwitch = 0;
        var stopped = false;

        var tick = function (now) {
            if (stopped || token !== self._token) return;
            analyser.getFloatTimeDomainData(time);
            var sum = 0;
            for (var i = 0; i < time.length; i++) sum += time[i] * time[i];
            var rms = Math.sqrt(sum / time.length);
            peak = Math.max(rms, peak * 0.995, 0.02);
            level = level * 0.5 + (rms / peak) * 0.5;

            analyser.getByteFrequencyData(freq);
            var wsum = 0;
            var fsum = 0;
            for (var b = 1; b < maxBin; b++) {
                wsum += b * freq[b];
                fsum += freq[b];
            }
            var centroidHz = fsum > 0 ? (wsum / fsum) * binHz : 0;

            var next = rms < 0.008 ? null : pickViseme(level, centroidHz);
            if (next !== current && (next === null || now - lastSwitch >= MIN_VISEME_HOLD_MS)) {
                current = next;
                lastSwitch = now;
                self.renderer.setMouth(current);
            }
            self._mouthLevel = rms < 0.008 ? 0 : Math.min(level, 1);
            self._lipRaf = requestAnimationFrame(tick);
        };
        this._lipRaf = requestAnimationFrame(tick);

        return function () {
            stopped = true;
            try {
                source.disconnect();
                analyser.disconnect();
            } catch (e) { /* already disconnected */ }
        };
    };

    SageAvatar.prototype._pseudoLipSync = function (token, text) {
        var self = this;
        var seq = text ? textToVisemes(text) : [];
        var idx = 0;
        var stopped = false;
        var step = function () {
            if (stopped || token !== self._token) return;
            var v;
            if (idx < seq.length) {
                v = seq[idx++];
            } else {
                v = Math.random() < 0.2 ? null : RANDOM_VOWELS[Math.floor(Math.random() * 5)];
            }
            self._setMouth(v);
            self._speechTimer = setTimeout(step, randomBetween(MORA_MS * 0.8, MORA_MS * 1.2));
        };
        step();
        return function () {
            stopped = true;
            clearTimeout(self._speechTimer);
        };
    };

    SageAvatar.prototype._speakWebSpeech = function (text, token) {
        var self = this;
        if (typeof speechSynthesis === 'undefined' || !speechSynthesis
            || typeof SpeechSynthesisUtterance === 'undefined') {
            return Promise.resolve('none');
        }
        return new Promise(function (resolve) {
            var utter = new SpeechSynthesisUtterance(text);
            utter.lang = self.lang === 'ja' ? 'ja-JP' : self.lang;
            var stopLipSync = function () {};
            var settled = false;
            var done = function () {
                if (settled) return;
                settled = true;
                stopLipSync();
                if (token === self._token) self._setMouth(null);
                resolve('webspeech');
            };
            utter.onstart = function () {
                if (token !== self._token) return;
                stopLipSync = self._pseudoLipSync(token, text);
            };
            utter.onend = done;
            utter.onerror = done;
            speechSynthesis.speak(utter);
        });
    };

    SageAvatar.prototype.destroy = function () {
        this.stopSpeaking();
        this.stopAutoBlink();
        clearTimeout(this._neutralTimer);
        cancelAnimationFrame(this._raf);
        if (this._audioCtx && this._audioCtx.close) this._audioCtx.close();
        this._audioCtx = null;
        this.renderer.destroy();
    };

    global.SageAvatar = SageAvatar;
})(window);
