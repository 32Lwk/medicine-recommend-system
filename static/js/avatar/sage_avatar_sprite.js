/**
 * Sage アバター — 2.5D スプライトレンダラー（Cubism モデル完成までの代替）
 *
 * manifest.json（scripts/live2d_build_sprite.py が生成, version 3）を読み、
 * body / ear / face / features / hair のパーツを視差つきで動かして首振り・うなずき・横向きを表現する。
 *
 * 首（parts.neck）は体と頭の間で曲がる: 下端は体に固定、上端は頭のあご下に追従する。
 * 頭は首の上端（pivot.head）を支点に傾ける。
 *
 * 手・腕（layers.gesture）は 2 枚組:
 *   body — 腕の形が変わった体全体（上腕まで）。素の体と短く入れ替える（元の腕が消え、新しい腕が出る）
 *   hand — 手と前腕。肘（pivot）を支点に一体で回り、入るときは下から振り上がる。
 *          attach: 'head'（あごに手）は頭の動きに合わせて肘を支点に向きを変える。rigid は回さない
 *
 * SageAvatar（sage_avatar.js）から呼ばれるレンダラー共通インターフェース:
 *   load(): Promise<void>
 *   applyPose(params)  — Live2D 風パラメータ（下記 POSE_DEFAULTS）を毎フレーム反映
 *                        params.gestures: [{ key, amount 0..1, swing 0..1（行き過ぎ可）, sway 度, lift px }]
 *                        amount は体の入れ替えと不透明度、swing は前腕の振り上げ位置、
 *                        lift は手先の持ち上げ量（肘を支点に回して出す）
 *   setExpression(key) — 'neutral' | manifest.layers.expression のキー
 *   setEyes(state)     — 'open' | 'half' | 'closed'
 *   setMouth(viseme)   — null | 'a' | 'i' | 'u' | 'e' | 'o'
 *   destroy()
 */
(function (global) {
    'use strict';

    var POSE_DEFAULTS = {
        angleX: 0, // 首の左右 -30..30（+ で画面右を向く）
        angleY: 0, // 首の上下 -30..30（+ で上を向く）
        angleZ: 0, // 首の傾き 度（+ で画面右へ傾ける）
        bodyAngleZ: 0, // 上半身の傾き 度
        lean: 0, // 前のめり 0..1
        bow: 0, // お辞儀 0..1
        hop: 0, // 弾み（キャンバス px, + で上）
        breath: 0, // 呼吸 0..1
    };

    // 頭の各パーツの視差（キャンバス px / 正規化角度）。手前ほど大きい。
    // 耳と顔のずれは、耳を顔の下へ伸ばした幅（約 10px）を超えないこと。
    var PARALLAX = {
        head: { x: 8, y: 6 },
        face: { x: 4, y: 3 },
        features: { x: 14, y: 11 },
        hair: { x: 2, y: 2 },
        ear_l: { x: 0, y: -1 },
        ear_r: { x: 0, y: -1 },
    };

    function SpriteAvatarRenderer(container, options) {
        if (!container) {
            throw new Error('SpriteAvatarRenderer: container is required');
        }
        this.container = container;
        this.manifestUrl = (options && options.manifestUrl) || '';
        this.baseUrl = this.manifestUrl.replace(/[^/]*$/, '');
        this.manifest = null;
        this.root = null;
        this.els = {};
        this.layerEls = { expression: {}, eyes: {}, mouth: {} };
        this.gestureEls = {};
        this.current = { expression: 'neutral', eyes: 'open', mouth: null };
        this.scale = 1;
        this._ro = null;
        this._exprZ = 1;
        this._exprOut = null;
        this._exprTimer = null;
    }

    // 体の入れ替えは短く: 新しい腕の体を先に出し切ってから素の体（元の腕）を消す。
    // 長いディゾルブは元の腕と新しい腕が半透明で重なって見えるため。
    var BODY_IN_END = 0.25;
    var BASE_OUT_START = 0.15;
    var BASE_OUT_END = 0.4;
    var EXPRESSION_FADE_MS = 110;
    var Z_EYES = 100000;

    // 首を切り絵で曲げられる範囲。重なった感情・モーション・待機の揺れの合計をここで抑える
    var LIMIT = { angleX: 28, angleY: 28, angleZ: 14 };
    // 頭の傾き・向きの一部を上半身が受け持つ（頭だけが動いて見えないように）
    var BODY_FOLLOW_Z = 0.18; // 傾きの割合
    var BODY_FOLLOW_X = 5; // 横を向いたときの上半身のずれ（キャンバス px）
    var NECK_TURN = 0.5; // 首が受け持つ頭の傾きの割合（残りはせん断と頭の回転）

    function clamp01(v) {
        return v < 0 ? 0 : v > 1 ? 1 : v;
    }

    function clamp(v, lim) {
        return v < -lim ? -lim : v > lim ? lim : v;
    }

    var DEG = Math.PI / 180;

    /** 2D アフィン [a, b, c, d, e, f]（CSS の matrix と同じ並び） */
    function mul(m, n) {
        return [
            m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1],
            m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
            m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5],
        ];
    }

    function apply(m, x, y) {
        return [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
    }

    /** origin を中心にした transform（CSS の transform-origin と同じ） */
    function about(ox, oy, m) {
        return mul(mul([1, 0, 0, 1, ox, oy], m), [1, 0, 0, 1, -ox, -oy]);
    }

    function rotation(deg) {
        var r = deg * DEG;
        return [Math.cos(r), Math.sin(r), -Math.sin(r), Math.cos(r), 0, 0];
    }

    /** 回転角（度）: 点 p を支点 o のまわりで q の方向へ向ける */
    function turnTo(o, p, q) {
        var a0 = Math.atan2(p[1] - o[1], p[0] - o[0]);
        var a1 = Math.atan2(q[1] - o[1], q[0] - o[0]);
        var d = a1 - a0;
        while (d > Math.PI) d -= 2 * Math.PI;
        while (d < -Math.PI) d += 2 * Math.PI;
        return d / DEG;
    }

    function pt(p) {
        return [p.x, p.y];
    }

    SpriteAvatarRenderer.POSE_DEFAULTS = POSE_DEFAULTS;

    SpriteAvatarRenderer.prototype.load = function () {
        var self = this;
        return fetch(this.manifestUrl, { cache: 'no-cache' })
            .then(function (res) {
                if (!res.ok) throw new Error('manifest HTTP ' + res.status);
                return res.json();
            })
            .then(function (manifest) {
                if (!manifest.parts || (manifest.version || 0) < 3) throw new Error('manifest version 3 is required');
                self.manifest = manifest;
                return self._build();
            });
    };

    SpriteAvatarRenderer.prototype.expressions = function () {
        var out = [];
        var ex = (this.manifest && this.manifest.layers.expression) || {};
        for (var k in ex) {
            if (Object.prototype.hasOwnProperty.call(ex, k)) out.push({ key: k, label: ex[k].label || k });
        }
        return out;
    };

    SpriteAvatarRenderer.prototype.gestures = function () {
        var out = [];
        var gs = (this.manifest && this.manifest.layers.gesture) || {};
        for (var k in gs) {
            if (Object.prototype.hasOwnProperty.call(gs, k)) out.push({ key: k, label: gs[k].label || k });
        }
        return out;
    };

    SpriteAvatarRenderer.prototype._build = function () {
        var m = this.manifest;
        var cw = m.canvas.width;
        var ch = m.canvas.height;
        var self = this;
        var pending = [];

        var place = function (el, spec) {
            el.style.left = (spec.x / cw * 100) + '%';
            el.style.top = (spec.y / ch * 100) + '%';
            el.style.width = (spec.w / cw * 100) + '%';
            el.style.height = (spec.h / ch * 100) + '%';
        };
        var img = function (spec, cls) {
            var el = document.createElement('img');
            el.className = cls;
            el.alt = '';
            el.decoding = 'async';
            el.draggable = false;
            el.src = self.baseUrl + spec.src;
            place(el, spec);
            pending.push(el);
            return el;
        };
        var group = function (cls) {
            var el = document.createElement('div');
            el.className = 'sage-avatar__group ' + cls;
            return el;
        };

        var root = document.createElement('div');
        root.className = 'sage-avatar';
        root.style.aspectRatio = cw + ' / ' + ch;

        var rig = group('sage-avatar__rig');
        root.appendChild(rig);
        var body = img(m.parts.body, 'sage-avatar__part sage-avatar__part--body');
        rig.appendChild(body);
        var gestures = m.layers.gesture || {};
        var gk;
        for (gk in gestures) {
            if (!Object.prototype.hasOwnProperty.call(gestures, gk)) continue;
            var gBody = img(gestures[gk].body, 'sage-avatar__gesture');
            rig.appendChild(gBody);
            this.gestureEls[gk] = { body: gBody, hand: null, spec: gestures[gk], shown: false };
        }

        var pv = m.pivot || {};
        this.pivots = {
            head: pv.head || pv.neck || { x: cw / 2, y: ch * 0.75 },
            neckBase: pv.neckBase || null,
            neckTop: pv.neckTop || null,
        };
        var neck = null;
        if (m.parts.neck && pv.neckBase && pv.neckTop) {
            neck = img(m.parts.neck, 'sage-avatar__part');
            neck.style.transformOrigin =
                ((pv.neckBase.x - m.parts.neck.x) / m.parts.neck.w * 100) + '% ' +
                ((pv.neckBase.y - m.parts.neck.y) / m.parts.neck.h * 100) + '%';
            rig.appendChild(neck);
        }

        var head = group('sage-avatar__head');
        var pivot = this.pivots.head;
        head.style.transformOrigin = (pivot.x / cw * 100) + '% ' + (pivot.y / ch * 100) + '%';
        rig.appendChild(head);

        var earL = img(m.parts.ear_l, 'sage-avatar__part');
        var earR = img(m.parts.ear_r, 'sage-avatar__part');
        var face = img(m.parts.face, 'sage-avatar__part');
        head.appendChild(earL);
        head.appendChild(earR);
        head.appendChild(face);

        var features = group('sage-avatar__features');
        features.appendChild(img(m.parts.features, 'sage-avatar__part'));
        var groups = ['expression', 'eyes', 'mouth'];
        for (var g = 0; g < groups.length; g++) {
            var entries = m.layers[groups[g]] || {};
            for (var key in entries) {
                if (!Object.prototype.hasOwnProperty.call(entries, key)) continue;
                var el = img(entries[key], 'sage-avatar__layer sage-avatar__layer--' + groups[g]);
                el.dataset.group = groups[g];
                el.dataset.key = key;
                if (groups[g] !== 'expression') el.style.zIndex = String(Z_EYES + g);
                features.appendChild(el);
                this.layerEls[groups[g]][key] = el;
            }
        }
        head.appendChild(features);

        var hair = img(m.parts.hair, 'sage-avatar__part');
        head.appendChild(hair);

        // 手と前腕は頭より手前。肘（pivot）を支点に回す
        for (gk in this.gestureEls) {
            if (!Object.prototype.hasOwnProperty.call(this.gestureEls, gk)) continue;
            var entry = this.gestureEls[gk];
            var hs = entry.spec.hand;
            if (!hs) continue;
            var hel = img(hs, 'sage-avatar__gesture');
            var hp = hs.pivot || { x: hs.x + hs.w / 2, y: hs.y + hs.h };
            hel.style.transformOrigin = ((hp.x - hs.x) / hs.w * 100) + '% ' + ((hp.y - hs.y) / hs.h * 100) + '%';
            rig.appendChild(hel);
            entry.hand = hel;
        }

        this.els = {
            rig: rig, body: body, neck: neck, head: head, face: face, features: features, hair: hair,
            ear_l: earL, ear_r: earR,
        };

        this.container.innerHTML = '';
        this.container.appendChild(root);
        this.root = root;
        this.canvasWidth = cw;
        this._updateScale();
        if (global.ResizeObserver) {
            this._ro = new ResizeObserver(function () { self._updateScale(); });
            this._ro.observe(root);
        }
        this.applyPose(POSE_DEFAULTS);

        return Promise.all(pending.map(function (el) {
            return el.decode ? el.decode().catch(function () {}) : Promise.resolve();
        }));
    };

    SpriteAvatarRenderer.prototype._updateScale = function () {
        if (!this.root) return;
        var w = (this.els.rig && this.els.rig.clientWidth) || this.root.clientWidth || this.canvasWidth;
        this.scale = w / this.canvasWidth;
    };

    SpriteAvatarRenderer.prototype.applyPose = function (p) {
        if (!this.root) return;
        var s = this.scale;
        var tx = clamp(p.angleX || 0, LIMIT.angleX) / 30;
        var ty = clamp(p.angleY || 0, LIMIT.angleY) / 30;
        var az = clamp(p.angleZ || 0, LIMIT.angleZ);
        var bow = p.bow || 0;
        var lean = p.lean || 0;
        var breath = p.breath || 0;

        var rigX = tx * BODY_FOLLOW_X * s;
        var rigY = (bow * 70 + lean * 18 - (p.hop || 0)) * s;
        var rigScale = 1 + lean * 0.07 + bow * 0.02;
        var bodyRot = (p.bodyAngleZ || 0) + az * BODY_FOLLOW_Z;
        this.els.rig.style.transform =
            'translate3d(' + rigX.toFixed(2) + 'px,' + rigY.toFixed(2) + 'px,0) rotate(' + bodyRot.toFixed(2) + 'deg)' +
            ' scale(' + rigScale.toFixed(4) + ',' + (rigScale * (1 + breath * 0.008)).toFixed(4) + ')';

        // 頭（rig 内のキャンバス座標）: 首の上端を支点に傾け、視差ぶんずらす
        var hx = tx * PARALLAX.head.x;
        var hy = -ty * PARALLAX.head.y - breath * 3 + bow * 10;
        var headRot = az * (1 - BODY_FOLLOW_Z);
        var sx = 1 - Math.abs(tx) * 0.025;
        var sy = 1 - Math.abs(ty) * 0.03;
        this.els.head.style.transform =
            'translate3d(' + (hx * s).toFixed(2) + 'px,' + (hy * s).toFixed(2) + 'px,0) rotate(' + headRot.toFixed(2) + 'deg)' +
            ' scale(' + sx.toFixed(4) + ',' + sy.toFixed(4) + ')';
        var hp = this.pivots.head;
        this._headM = mul([1, 0, 0, 1, hx, hy], about(hp.x, hp.y, mul(rotation(headRot), [sx, 0, 0, sy, 0, 0])));
        this._faceShift = [tx * PARALLAX.face.x, -ty * PARALLAX.face.y];

        var names = ['face', 'features', 'hair', 'ear_l', 'ear_r'];
        for (var i = 0; i < names.length; i++) {
            var k = names[i];
            var par = PARALLAX[k];
            var x = tx * par.x * s;
            var y = -ty * par.y * s;
            this.els[k].style.transform = 'translate3d(' + x.toFixed(2) + 'px,' + y.toFixed(2) + 'px,0)';
        }

        this._applyNeck(headRot);
        this._applyGestures(p.gestures || []);
    };

    /**
     * 首の上端を、頭が動いた先のあご下（pivot.neckTop）へ合わせる。下端は体に固定。
     * 横ずれはせん断で受け（上端が水平のまま）、傾きは頭の一部だけ回す。首は短いので回しすぎると
     * 上端の角があごの横へはみ出す
     */
    SpriteAvatarRenderer.prototype._applyNeck = function (headRot) {
        var neck = this.els.neck;
        if (!neck) return;
        var b = pt(this.pivots.neckBase);
        var top = pt(this.pivots.neckTop);
        var moved = apply(this._headM, top[0] + this._faceShift[0], top[1] + this._faceShift[1]);
        var vx = top[0] - b[0];
        var vy = top[1] - b[1];
        if (vy > -1) vy = -1;
        var r = rotation(-headRot * NECK_TURN);
        var m = apply(r, moved[0] - b[0], moved[1] - b[1]);
        var shear = [1, 0, (m[0] - vx) / vy, m[1] / vy, 0, 0];
        var t = mul(rotation(headRot * NECK_TURN), shear);
        neck.style.transform = 'matrix(' + t[0].toFixed(5) + ',' + t[1].toFixed(5) + ',' + t[2].toFixed(5) + ',' +
            t[3].toFixed(5) + ',0,0)';
    };

    SpriteAvatarRenderer.prototype._applyGestures = function (list) {
        var active = {};
        var cover = 0;
        for (var i = 0; i < list.length; i++) {
            var g = list[i];
            var entry = this.gestureEls[g.key];
            if (!entry || !(g.amount > 0)) continue;
            active[g.key] = true;
            var a = Math.min(g.amount, 1);
            var swing = g.swing == null ? a : g.swing;
            entry.body.style.opacity = clamp01(a / BODY_IN_END).toFixed(3);
            cover = Math.max(cover, clamp01((a - BASE_OUT_START) / (BASE_OUT_END - BASE_OUT_START)));
            if (entry.hand) {
                var hs = entry.spec.hand;
                var rot = 0;
                if (!hs.rigid) {
                    var elbow = pt(hs.pivot);
                    var tip = hs.tip ? pt(hs.tip) : null;
                    rot = (hs.enterRot || 0) * (1 - swing) + (g.sway || 0);
                    if (tip && g.lift) {
                        // 持ち上げは肘まわりの回転で出す（平行移動すると肘で腕が切れる）
                        var reach = Math.hypot(tip[0] - elbow[0], tip[1] - elbow[1]) || 1;
                        rot -= (hs.enterRot < 0 ? -1 : 1) * Math.atan(g.lift / reach) / DEG;
                    }
                    if (tip && entry.spec.attach === 'head' && this._headM) {
                        var on = apply(this._headM, tip[0] + this._faceShift[0], tip[1] + this._faceShift[1]);
                        rot += turnTo(elbow, tip, on);
                    }
                }
                entry.hand.style.transform = 'rotate(' + rot.toFixed(2) + 'deg)';
                // 前腕の下は素の体なので、体の新しい上腕と同時に出さないと袖だけの瞬間ができる
                entry.hand.style.opacity = clamp01(a / BODY_IN_END).toFixed(3);
            }
            if (!entry.shown) {
                entry.body.classList.add('is-visible');
                if (entry.hand) entry.hand.classList.add('is-visible');
                entry.shown = true;
            }
        }
        this.els.body.style.opacity = cover > 0 ? (1 - cover).toFixed(3) : '';
        for (var k in this.gestureEls) {
            if (!Object.prototype.hasOwnProperty.call(this.gestureEls, k)) continue;
            var e = this.gestureEls[k];
            if (e.shown && !active[k]) {
                e.body.classList.remove('is-visible');
                if (e.hand) e.hand.classList.remove('is-visible');
                e.shown = false;
            }
        }
    };

    SpriteAvatarRenderer.prototype._show = function (group, key) {
        var els = this.layerEls[group];
        for (var k in els) {
            if (Object.prototype.hasOwnProperty.call(els, k)) {
                els[k].classList.toggle('is-visible', k === key);
            }
        }
    };

    /**
     * 表情の入れ替え。新しい表情を一番上に重ねて短くフェードインし、出し切ってから古い表情を消す。
     * 2 枚を同時に半透明にすると眉や口が二重に見えるため、半透明になるのは上の 1 枚だけにする。
     */
    SpriteAvatarRenderer.prototype.setExpression = function (key) {
        var els = this.layerEls.expression;
        var next = key && els[key] ? key : 'neutral';
        var prev = this.current.expression;
        if (next === prev) return;
        this.current.expression = next;
        this._finishExpressionFade();

        var inEl = els[next] || null;
        var outEl = els[prev] || null;
        if (inEl) {
            if (++this._exprZ >= Z_EYES) this._renumberExpressions();
            inEl.style.zIndex = String(this._exprZ);
            inEl.classList.add('is-visible');
        }
        if (outEl) {
            if (inEl) {
                this._exprOut = outEl;
                var self = this;
                this._exprTimer = setTimeout(function () { self._finishExpressionFade(); }, EXPRESSION_FADE_MS);
            } else {
                outEl.classList.remove('is-visible');
            }
        }
        if (this.current.eyes === 'half') this.setEyes('half');
    };

    SpriteAvatarRenderer.prototype._finishExpressionFade = function () {
        clearTimeout(this._exprTimer);
        this._exprTimer = null;
        var outEl = this._exprOut;
        this._exprOut = null;
        if (!outEl || outEl === this.layerEls.expression[this.current.expression]) return;
        outEl.classList.add('is-instant');
        outEl.classList.remove('is-visible');
        void outEl.offsetWidth;
        outEl.classList.remove('is-instant');
    };

    SpriteAvatarRenderer.prototype._renumberExpressions = function () {
        var els = this.layerEls.expression;
        var list = [];
        for (var k in els) {
            if (Object.prototype.hasOwnProperty.call(els, k)) list.push(els[k]);
        }
        list.sort(function (a, b) { return (+a.style.zIndex || 0) - (+b.style.zIndex || 0); });
        for (var i = 0; i < list.length; i++) list[i].style.zIndex = String(i + 1);
        this._exprZ = list.length + 1;
    };

    SpriteAvatarRenderer.prototype.setEyes = function (state) {
        this.current.eyes = state || 'open';
        var key = null;
        if (state === 'closed') {
            key = 'closed';
        } else if (state === 'half') {
            var own = 'half@' + this.current.expression;
            key = this.layerEls.eyes[own] ? own : 'half';
        }
        this._show('eyes', key);
    };

    SpriteAvatarRenderer.prototype.setMouth = function (viseme) {
        if (viseme === this.current.mouth) return;
        this.current.mouth = viseme || null;
        this._show('mouth', this.current.mouth);
    };

    SpriteAvatarRenderer.prototype.destroy = function () {
        clearTimeout(this._exprTimer);
        this._exprOut = null;
        if (this._ro) this._ro.disconnect();
        if (this.root && this.root.parentNode) {
            this.root.parentNode.removeChild(this.root);
        }
        this.root = null;
        this.els = {};
        this.layerEls = { expression: {}, eyes: {}, mouth: {} };
        this.gestureEls = {};
    };

    global.SpriteAvatarRenderer = SpriteAvatarRenderer;
})(window);
