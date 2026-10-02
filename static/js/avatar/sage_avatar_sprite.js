/**
 * Sage アバター — 2.5D スプライトレンダラー（Cubism モデル完成までの代替）
 *
 * manifest.json（scripts/live2d_build_sprite_b.py が生成, version 2）を読み、
 * body / ear / face / features / hair のパーツを視差つきで動かして首振り・うなずき・横向きを表現する。
 *
 * SageAvatar（sage_avatar.js）から呼ばれるレンダラー共通インターフェース:
 *   load(): Promise<void>
 *   applyPose(params)  — Live2D 風パラメータ（下記 POSE_DEFAULTS）を毎フレーム反映
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
        this.current = { expression: 'neutral', eyes: 'open', mouth: null };
        this.scale = 1;
        this._ro = null;
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
                if (!manifest.parts) throw new Error('manifest version 2 (parts) is required');
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

        var head = group('sage-avatar__head');
        var pivot = (m.pivot && m.pivot.neck) || { x: cw / 2, y: ch * 0.75 };
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
                features.appendChild(el);
                this.layerEls[groups[g]][key] = el;
            }
        }
        head.appendChild(features);

        var hair = img(m.parts.hair, 'sage-avatar__part');
        head.appendChild(hair);

        this.els = {
            rig: rig, head: head, face: face, features: features, hair: hair, ear_l: earL, ear_r: earR,
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
        var tx = (p.angleX || 0) / 30;
        var ty = (p.angleY || 0) / 30;
        var bow = p.bow || 0;
        var lean = p.lean || 0;
        var breath = p.breath || 0;

        var rigY = (bow * 70 + lean * 18 - (p.hop || 0)) * s;
        var rigScale = 1 + lean * 0.07 + bow * 0.02;
        this.els.rig.style.transform =
            'translate3d(0,' + rigY.toFixed(2) + 'px,0) rotate(' + (p.bodyAngleZ || 0).toFixed(2) + 'deg)' +
            ' scale(' + rigScale.toFixed(4) + ',' + (rigScale * (1 + breath * 0.008)).toFixed(4) + ')';

        var hx = tx * PARALLAX.head.x * s;
        var hy = (-ty * PARALLAX.head.y - breath * 3 + bow * 10) * s;
        var sx = 1 - Math.abs(tx) * 0.025;
        var sy = 1 - Math.abs(ty) * 0.03;
        this.els.head.style.transform =
            'translate3d(' + hx.toFixed(2) + 'px,' + hy.toFixed(2) + 'px,0) rotate(' + (p.angleZ || 0).toFixed(2) + 'deg)' +
            ' scale(' + sx.toFixed(4) + ',' + sy.toFixed(4) + ')';

        var names = ['face', 'features', 'hair', 'ear_l', 'ear_r'];
        for (var i = 0; i < names.length; i++) {
            var k = names[i];
            var par = PARALLAX[k];
            var x = tx * par.x * s;
            var y = -ty * par.y * s;
            this.els[k].style.transform = 'translate3d(' + x.toFixed(2) + 'px,' + y.toFixed(2) + 'px,0)';
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

    SpriteAvatarRenderer.prototype.setExpression = function (key) {
        this.current.expression = key && this.layerEls.expression[key] ? key : 'neutral';
        this._show('expression', this.current.expression);
        if (this.current.eyes === 'half') this.setEyes('half');
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
        if (this._ro) this._ro.disconnect();
        if (this.root && this.root.parentNode) {
            this.root.parentNode.removeChild(this.root);
        }
        this.root = null;
        this.els = {};
        this.layerEls = { expression: {}, eyes: {}, mouth: {} };
    };

    global.SpriteAvatarRenderer = SpriteAvatarRenderer;
})(window);
