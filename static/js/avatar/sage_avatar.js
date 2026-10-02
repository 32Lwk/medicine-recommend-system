/**
 * Sage アバター — コントローラー（感情・モーション・まばたき・リップシンク）
 *
 * レンダラー（SpriteAvatarRenderer / 将来の Cubism レンダラー）に依存しない層。
 * レンダラーは applyPose / setExpression / setEyes / setMouth を実装していればよい。
 *
 *   var avatar = new SageAvatar(renderer);
 *   avatar.setEmotion('worry');
 *   avatar.playMotion('nod');
 *   avatar.playGesture('wave');
 *   avatar.speak('[心配]それはおつらいですね。お大事にしてください。', { autoEmotion: true });
 *
 * 読み上げ方式（ttsMode）:
 *   'voicevox'  — ローカルの VOICEVOX Engine（既定 http://127.0.0.1:50021）。モーラ単位の口パク
 *   'server'    — /api/tts の音声を再生し、音量解析で口パク
 *   'webspeech' — ブラウザの読み上げ（擬似口パク）
 *   voicevox / server が失敗した文はブラウザの読み上げで代用する。
 *
 *   new SageAvatar(renderer, { ttsMode: 'voicevox', voicevox: { speaker: 11 } });
 */
(function (global) {
    'use strict';

    /* ---------- 感情: 表情 + 姿勢のかたより + 入りのモーション ---------- */

    // gesture: 感情が切り替わったときに自動で出す手の動き（autoGesture 時）
    var EMOTIONS = {
        neutral: { label: '通常', expr: 'neutral', bias: {} },
        smile: { label: '微笑み', expr: 'smile', bias: { angleZ: 2, angleY: 1 }, enter: 'nod' },
        thinking: { label: '思案', expr: 'thinking', bias: { angleZ: 7, angleX: 8, angleY: 6 }, gesture: 'chin' },
        empathy: {
            label: '共感', expr: 'empathy', bias: { angleZ: 4, angleY: -3, lean: 0.15 }, enter: 'nodSlow', gesture: 'explain',
        },
        surprise: { label: '軽い驚き', expr: 'surprise', bias: { angleY: 5, lean: -0.1 }, enter: 'flinch' },
        relief: { label: '安心', expr: 'relief', bias: { angleY: 1, angleZ: -2 }, enter: 'nod', gesture: 'ok' },
        worry: { label: '心配', expr: 'worry', bias: { angleZ: 5, angleY: -3, lean: 0.25 }, gesture: 'chest' },
        sorry: { label: '申し訳なさ', expr: 'sorry', bias: { angleY: -5, angleZ: -3 }, enter: 'bow', gesture: 'bow_hands' },
        serious: { label: '真剣', expr: 'serious', bias: { angleY: -2, lean: 0.3 }, gesture: 'point' },
        cheer: { label: '励まし', expr: 'cheer', bias: { angleY: 3 }, enter: 'hop', gesture: 'fist' },
        shy: { label: '照れ', expr: 'shy', bias: { angleX: -12, angleY: -5, angleZ: 6 } },
        confused: { label: '困惑', expr: 'confused', bias: { angleZ: -9, angleY: 3 } },
    };

    /* ---------- 手・腕: 腕の形が変わった体へディゾルブし、hold 秒とどまって戻る ---------- */

    // 手先の動き。sway: 袖口・肘を支点にした揺れ [振幅(度), 周波数(Hz)]、
    // lift: 入り切った後の上下 [秒, px] キーフレーム（手先は袖から離れないよう小さく）
    var GESTURES = {
        wave: { label: '手を振る', hold: 1.8, sway: [8, 1.6] },
        explain: { label: '手のひら差し出し', hold: 2.4, sway: [2, 0.5], lift: [[0, 0], [0.35, 4], [0.8, 0]] },
        point: { label: '人差し指', hold: 2.2, sway: [1.5, 0.6], lift: [[0, 0], [0.18, 6], [0.4, 0], [0.6, 4], [0.8, 0]] },
        chest: { label: '胸に手', hold: 2.6, sway: [0.8, 0.4] },
        chin: { label: 'あごに手', hold: 3.0, sway: [0.4, 0.35] },
        fist: { label: 'こぶし', hold: 1.8, sway: [1.5, 0.8], lift: [[0, 0], [0.14, 8], [0.3, 0], [0.46, 6], [0.62, 0]] },
        bow_hands: { label: '両手を合わせる', hold: 2.2, sway: [0.6, 0.4], lift: [[0, 0], [0.3, 3], [0.7, 0]] },
        ok: { label: 'OK サイン', hold: 2.0, sway: [3, 0.9], lift: [[0, 0], [0.2, 4], [0.45, 0]] },
    };
    var GESTURE_IN = 0.42; // 秒
    var GESTURE_OUT = 0.38;

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
    var GESTURE_TAGS = {
        手を振る: 'wave', 手振り: 'wave', 説明: 'explain', 手のひら: 'explain', 差し出し: 'explain',
        人差し指: 'point', ポイント: 'point', 胸に手: 'chest', あごに手: 'chin', 顎に手: 'chin',
        こぶし: 'fist', ガッツポーズ: 'fist', 両手を合わせる: 'bow_hands', 合掌: 'bow_hands',
        OK: 'ok', ＯＫ: 'ok', オーケー: 'ok', OKサイン: 'ok',
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
    // 感情からの自動割り当てより優先される
    var GESTURE_KEYWORDS = [
        [/こんにちは|こんばんは|おはよう|はじめまして|いらっしゃいませ|またお越し|さようなら/, 'wave'],
        [/申し訳|ごめんなさい|お願いいたします|お願いします/, 'bow_hands'],
        [/ポイント|大切なのは|注意(点|して)|ひとつ(目|め)|まず(は)?/, 'point'],
        [/お任せ|私が|ご案内します|サポートします/, 'chest'],
        [/問題ありません|大丈夫です|OK|オーケー|ばっちり/, 'ok'],
        [/がんば|頑張|応援して|ファイト/, 'fist'],
        [/例えば|こちらの|おすすめ|ご紹介|いかがでしょう/, 'explain'],
        [/うーん|考えて|確認します|お調べ/, 'chin'],
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

    var VOICEVOX_DEFAULTS = { url: 'http://127.0.0.1:50021', speaker: 3, params: {} };
    var VOICEVOX_CACHE_MAX = 40;
    // 唇を閉じてから開く子音
    var LIP_CLOSE_CONSONANTS = { m: 1, my: 1, b: 1, by: 1, p: 1, py: 1 };
    var DEVOICED_LEVEL = 0.15;
    var UPSPEAK_SEC = 0.15;

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

    /**
     * VOICEVOX の audio_query から口形の時刻表 [{ t, v, level }] を作る（t は再生開始からの秒）。
     * 大文字の母音は無声化（ほぼ口を開けない）、N・cl・pau は口を閉じる。
     */
    function voicevoxTimeline(query) {
        var speed = query.speedScale || 1;
        var pauseScale = query.pauseLengthScale == null ? 1 : query.pauseLengthScale;
        var t = 0;
        var out = [];
        var push = function (sec, v, level) {
            if (!(sec > 0)) return;
            var last = out[out.length - 1];
            if (!last || last.v !== v || last.level !== level) out.push({ t: t, v: v, level: level });
            t += sec;
        };
        push((query.prePhonemeLength || 0) / speed, null, 0);
        var phrases = query.accent_phrases || [];
        for (var i = 0; i < phrases.length; i++) {
            var moras = phrases[i].moras || [];
            for (var j = 0; j < moras.length; j++) {
                var m = moras[j];
                var raw = m.vowel || '';
                var lower = raw.toLowerCase();
                var v = lower.length === 1 && 'aiueo'.indexOf(lower) >= 0 ? lower : null;
                var level = v ? (raw === lower ? VISEME_LEVEL[v] : DEVOICED_LEVEL) : 0;
                if (m.consonant && m.consonant_length) {
                    var closed = LIP_CLOSE_CONSONANTS[m.consonant];
                    push(m.consonant_length / speed, closed ? null : v, closed ? 0 : level * 0.6);
                }
                push((m.vowel_length || 0) / speed, v, level);
            }
            // 疑問文はエンジンが語尾上げの母音を 1 つ足す（モーラ一覧には出てこない）
            if (phrases[i].is_interrogative && moras.length) {
                var tail = (moras[moras.length - 1].vowel || '').toLowerCase();
                if (tail.length === 1 && 'aiueo'.indexOf(tail) >= 0) push(UPSPEAK_SEC / speed, tail, VISEME_LEVEL[tail]);
            }
            var pause = phrases[i].pause_mora;
            if (pause) {
                var pauseSec = query.pauseLength != null ? query.pauseLength : pause.vowel_length * pauseScale;
                push(pauseSec / speed, null, 0);
            }
        }
        out.push({ t: t, v: null, level: 0 });
        return out;
    }

    function decodeAudio(ctx, arrayBuffer) {
        return new Promise(function (resolve, reject) {
            var p = ctx.decodeAudioData(arrayBuffer, resolve, reject);
            if (p && typeof p.then === 'function') p.then(resolve, reject);
        });
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
     * タグ（[心配] [お辞儀] [手を振る] など）が優先、なければキーワードから推定（autoEmotion 時）。
     */
    function parseScript(text, autoEmotion) {
        var sentences = String(text || '').match(/[^。！？!?\n]+[。！？!?\n]*/g) || [];
        var segs = [];
        for (var i = 0; i < sentences.length; i++) {
            var raw = sentences[i];
            var emotion = null;
            var motions = [];
            var gesture = null;
            var body = raw.replace(/[\[［]([^\]］]+)[\]］]/g, function (_, name) {
                name = name.trim();
                if (EMOTION_TAGS[name] || EMOTIONS[name]) emotion = EMOTION_TAGS[name] || name;
                else if (MOTION_TAGS[name] || MOTIONS[name]) motions.push(MOTION_TAGS[name] || name);
                else if (GESTURE_TAGS[name] || GESTURES[name]) gesture = GESTURE_TAGS[name] || name;
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
                if (!gesture) {
                    for (var q = 0; q < GESTURE_KEYWORDS.length; q++) {
                        if (GESTURE_KEYWORDS[q][0].test(body)) { gesture = GESTURE_KEYWORDS[q][1]; break; }
                    }
                }
            }
            if (!body && !emotion && !motions.length && !gesture) continue;
            segs.push({ text: body, emotion: emotion, motions: motions, gesture: gesture });
        }
        return segs;
    }

    /* ---------- SageAvatar ---------- */

    function SageAvatar(renderer, options) {
        var opts = options || {};
        this.renderer = renderer;
        this.lang = opts.lang || 'ja';
        this.ttsUrl = opts.ttsUrl || ((global.APP_BASE_PATH || '') + '/api/tts');
        this.ttsMode = opts.ttsMode || (opts.useServerTts === false ? 'webspeech' : 'server');
        this.voicevox = {};
        this.setVoicevox(VOICEVOX_DEFAULTS);
        if (opts.voicevox) this.setVoicevox(opts.voicevox);
        this.onSpeakingChange = opts.onSpeakingChange || null;
        this.onEmotionChange = opts.onEmotionChange || null;
        this.onSegment = opts.onSegment || null;
        this.idleAmount = opts.idleAmount == null ? 1 : opts.idleAmount;
        this.autoGesture = opts.autoGesture !== false; // 感情の切り替えで手を動かす

        this.emotion = 'neutral';
        this.speaking = false;
        this._token = 0;
        this._blinkTimer = null;
        this._blinking = false;
        this._audio = null;
        this._source = null;
        this._audioCtx = null;
        this._voicevoxCache = new Map();
        this._voicevoxFailed = false;
        this._serverTtsFailed = false;
        this._lipRaf = null;
        this._speechTimer = null;
        this._neutralTimer = null;

        this._bias = {};
        this._biasTarget = {};
        this._motions = [];
        this._gestures = [];
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
    SageAvatar.GESTURES = GESTURES;
    SageAvatar.parseScript = parseScript;
    SageAvatar.textToVisemes = textToVisemes;
    SageAvatar.voicevoxTimeline = voicevoxTimeline;

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

        pose.gestures = this._gesturePose(now);
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
        if (changed && def.gesture && this.autoGesture && !(opts && opts.gesture === false)) {
            this.playGesture(def.gesture);
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

    function gestureAmount(g, now) {
        if (g.outStart != null) {
            var u = Math.min((now - g.outStart) / 1000 / GESTURE_OUT, 1);
            return g.outFrom * (1 - u * u * (3 - 2 * u));
        }
        var el = (now - g.start) / 1000;
        if (el < GESTURE_IN) {
            var v = el / GESTURE_IN;
            return 1 - Math.pow(1 - v, 3);
        }
        return 1;
    }

    SageAvatar.prototype._gesturePose = function (now) {
        var out = [];
        var alive = [];
        for (var i = 0; i < this._gestures.length; i++) {
            var g = this._gestures[i];
            var el = (now - g.start) / 1000;
            if (g.outStart == null && el >= GESTURE_IN + g.hold) {
                g.outStart = g.start + (GESTURE_IN + g.hold) * 1000;
                g.outFrom = 1;
            }
            if (g.outStart != null && now - g.outStart >= GESTURE_OUT * 1000) continue;
            alive.push(g);
            var amount = gestureAmount(g, now);
            var sway = g.def.sway ? g.def.sway[0] * Math.sin(2 * Math.PI * g.def.sway[1] * el) * amount : 0;
            var lift = g.def.lift && el > GESTURE_IN ? sampleTrack(g.def.lift, el - GESTURE_IN) : 0;
            out.push({ key: g.name, amount: amount, sway: sway, lift: lift });
        }
        this._gestures = alive;
        return out;
    };

    /**
     * 手・腕のジェスチャーを出す。出ている別のジェスチャーは下げる。
     * opts.hold: とどまる秒数（Infinity なら stopGesture まで）
     */
    SageAvatar.prototype.playGesture = function (name, opts) {
        var def = GESTURES[name];
        if (!def) return;
        var now = performance.now();
        var hold = opts && opts.hold != null ? opts.hold : def.hold;
        var same = null;
        for (var i = 0; i < this._gestures.length; i++) {
            var g = this._gestures[i];
            if (g.outStart != null) continue;
            if (g.name === name) {
                same = g;
            } else {
                g.outFrom = gestureAmount(g, now);
                g.outStart = now;
            }
        }
        if (same) {
            // 出ている同じ手はそのまま、とどまる時間だけ延ばす
            same.hold = (now - same.start) / 1000 - GESTURE_IN + hold;
            return;
        }
        this._gestures.push({ name: name, def: def, start: now, hold: hold, outStart: null, outFrom: 1 });
    };

    SageAvatar.prototype.stopGesture = function () {
        var now = performance.now();
        for (var i = 0; i < this._gestures.length; i++) {
            var g = this._gestures[i];
            if (g.outStart == null) {
                g.outFrom = gestureAmount(g, now);
                g.outStart = now;
            }
        }
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
        if (this._source) {
            try { this._source.stop(); } catch (e) { /* not started */ }
            this._source = null;
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
     * @returns {Promise<'voicevox'|'server'|'webspeech'|'none'>} 最後に使えた読み上げ方式
     */
    SageAvatar.prototype.speak = function (text, options) {
        var self = this;
        var opts = options || {};
        this.stopSpeaking();
        clearTimeout(this._neutralTimer);
        this._ensureAudioContext();
        this._voicevoxFailed = false;
        var token = this._token;
        var segs = parseScript(text, !!opts.autoEmotion);
        if (!segs.length) return Promise.resolve('none');

        var prefetch = function (idx) {
            if (self.ttsMode !== 'voicevox' || self._voicevoxFailed) return;
            var seg = segs[idx];
            if (seg && seg.text) self._voicevoxPrepare(seg.text).catch(function () {});
        };
        prefetch(0);
        prefetch(1);

        var mode = 'none';
        var startedEmotion = this.emotion;
        this._setSpeaking(true);
        var run = segs.reduce(function (p, seg, idx) {
            return p.then(function () {
                if (token !== self._token) return;
                if (seg.emotion) self.setEmotion(seg.emotion, { gesture: !seg.gesture });
                for (var i = 0; i < seg.motions.length; i++) self.playMotion(seg.motions[i]);
                if (seg.gesture) self.playGesture(seg.gesture);
                if (!seg.motions.length && !seg.emotion && !seg.gesture && idx > 0) self.playMotion('nod', { scale: 0.35 });
                if (typeof self.onSegment === 'function') self.onSegment(seg, idx);
                prefetch(idx + 1);
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
        if (this.ttsMode === 'voicevox' && !this._voicevoxFailed) return this._speakVoicevox(text, token);
        if (this.ttsMode === 'server' && !this._serverTtsFailed) return this._speakServer(text, token);
        return this._speakWebSpeech(text, token);
    };

    /* ---------- VOICEVOX ---------- */

    /** VOICEVOX の接続先・話者・合成パラメータ（speedScale など audio_query の項目）を変える。 */
    SageAvatar.prototype.setVoicevox = function (conf) {
        var vv = this.voicevox;
        var changed = false;
        if (conf.url != null && conf.url !== vv.url) { vv.url = String(conf.url).replace(/\/+$/, ''); changed = true; }
        if (conf.speaker != null && conf.speaker !== vv.speaker) { vv.speaker = conf.speaker; changed = true; }
        if (conf.params) { vv.params = conf.params; changed = true; }
        if (changed && this._voicevoxCache) this._voicevoxCache.clear();
    };

    /** エンジンに届くか確かめる。@returns {Promise<string|null>} バージョン（届かなければ null） */
    SageAvatar.prototype.checkVoicevox = function (timeoutMs) {
        var url = this.voicevox.url;
        var ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
        var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, timeoutMs || 2500) : null;
        return fetch(url + '/version', ctrl ? { signal: ctrl.signal } : {})
            .then(function (res) { return res.ok ? res.json() : null; })
            .catch(function () { return null; })
            .then(function (v) { clearTimeout(timer); return v; });
    };

    /** 文を合成して { buffer, timeline } を返す（話者・文ごとにキャッシュ）。 */
    SageAvatar.prototype._voicevoxPrepare = function (text) {
        var vv = this.voicevox;
        var key = vv.speaker + '\u0000' + text;
        var cache = this._voicevoxCache;
        if (cache.has(key)) {
            var hit = cache.get(key);
            cache.delete(key);
            cache.set(key, hit);
            return hit;
        }
        var ctx = this._ensureAudioContext();
        if (!ctx) return Promise.reject(new Error('Web Audio unavailable'));
        var speaker = encodeURIComponent(vv.speaker);
        var job = fetch(vv.url + '/audio_query?speaker=' + speaker + '&text=' + encodeURIComponent(text), { method: 'POST' })
            .then(function (res) {
                if (!res.ok) throw new Error('VOICEVOX audio_query HTTP ' + res.status);
                return res.json();
            })
            .then(function (query) {
                for (var k in vv.params) {
                    if (Object.prototype.hasOwnProperty.call(vv.params, k)) query[k] = vv.params[k];
                }
                return fetch(vv.url + '/synthesis?speaker=' + speaker, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(query),
                }).then(function (res) {
                    if (!res.ok) throw new Error('VOICEVOX synthesis HTTP ' + res.status);
                    return res.arrayBuffer();
                }).then(function (wav) {
                    return decodeAudio(ctx, wav);
                }).then(function (buffer) {
                    return { buffer: buffer, timeline: voicevoxTimeline(query) };
                });
            });
        job.catch(function () {
            if (cache.get(key) === job) cache.delete(key);
        });
        cache.set(key, job);
        while (cache.size > VOICEVOX_CACHE_MAX) cache.delete(cache.keys().next().value);
        return job;
    };

    SageAvatar.prototype._speakVoicevox = function (text, token) {
        var self = this;
        return this._voicevoxPrepare(text)
            .then(function (res) {
                if (token !== self._token) return 'none';
                return self._playVoicevox(res, token).then(function () { return 'voicevox'; });
            })
            .catch(function (err) {
                if (token !== self._token) return 'none';
                console.warn('VOICEVOX unavailable, falling back to Web Speech:', err);
                self._voicevoxFailed = true;
                return self._speakWebSpeech(text, token);
            });
    };

    SageAvatar.prototype._playVoicevox = function (res, token) {
        var self = this;
        var ctx = this._audioCtx;
        var timeline = res.timeline;
        var src = ctx.createBufferSource();
        src.buffer = res.buffer;
        src.connect(ctx.destination);
        this._source = src;
        var start = ctx.currentTime + 0.03;
        var idx = -1;
        var stopped = false;
        return new Promise(function (resolve) {
            var tick = function () {
                if (stopped || token !== self._token) return;
                var t = ctx.currentTime - start;
                var next = idx;
                while (next + 1 < timeline.length && timeline[next + 1].t <= t) next++;
                if (next !== idx && next >= 0) {
                    idx = next;
                    self._setMouth(timeline[idx].v, timeline[idx].level);
                }
                self._lipRaf = requestAnimationFrame(tick);
            };
            src.onended = function () {
                stopped = true;
                src.disconnect();
                if (token === self._token) {
                    cancelAnimationFrame(self._lipRaf);
                    self._lipRaf = null;
                    self._source = null;
                    self._setMouth(null);
                }
                resolve();
            };
            src.start(start);
            self._lipRaf = requestAnimationFrame(tick);
        });
    };

    /* ---------- サーバー TTS ---------- */

    SageAvatar.prototype._speakServer = function (text, token) {
        var self = this;
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
                self._serverTtsFailed = true;
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
