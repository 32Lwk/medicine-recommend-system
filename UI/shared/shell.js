/**
 * UI mockup shell — demo interactions only (no backend).
 * Used by UI/patterns/*.html prototypes.
 */
(function () {
  'use strict';

  var MEDICINES = [
    {
      rank: 1,
      name: 'ルルアタックTR',
      maker: '第一三共ヘルスケア',
      efficacy: 'のどの痛み・発熱・鼻水・鼻づまり・くしゃみ・せき・たん・悪寒',
      reason: 'のどの痛みと発熱を伴う風邪症状に対し、総合感冒薬として成分バランスが適合',
      score: 92,
      emoji: '💊',
      medType: '総合感冒薬',
      form: 'tablets',
      symptoms: ['のど痛', '発熱', '鼻水', 'くしゃみ'],
      ageLabel: '15歳以上',
      scores: { symptom: 94, efficacy: 88, age: 100, usage: 85 },
      imageUrl: null
    },
    {
      rank: 2,
      name: 'パブロンゴールドA微粒',
      maker: '大正製薬',
      efficacy: 'のどの痛み・発熱・鼻みず・鼻づまり・くしゃみ・せき・たん・頭痛',
      reason: '複数症状への広い効能カバー。眠くなりにくい成分設計',
      score: 86,
      emoji: '🌟',
      medType: '総合感冒薬',
      form: 'granules',
      symptoms: ['発熱', '鼻水', '頭痛', 'せき'],
      ageLabel: '15歳以上',
      scores: { symptom: 88, efficacy: 82, age: 100, usage: 80 },
      imageUrl: null
    },
    {
      rank: 3,
      name: 'コルゲンコーワIB',
      maker: '興和',
      efficacy: 'のどの痛み・発熱・鼻水・鼻づまり・くしゃみ',
      reason: 'のど症状に特化した配合。服用回数が少なく利便性が高い',
      score: 81,
      emoji: '🍀',
      medType: '総合感冒薬',
      form: 'tablet',
      symptoms: ['のど痛', '発熱', '鼻づまり'],
      ageLabel: '15歳以上',
      scores: { symptom: 85, efficacy: 78, age: 100, usage: 90 },
      imageUrl: null
    }
  ];

  var carouselUid = 0;

  var ONBOARDING = [
    { title: 'ようこそ', text: '症状をチャットで入力すると、OTC医薬品の候補をご提案します。' },
    { title: 'ユーザー情報', text: '年齢・アレルギー等を登録すると、より安全な提案が可能です。' },
    { title: '多言語UI', text: '表示言語は4か国語に切り替え可能（AI返信はβ版では日本語）。' },
    { title: 'はじめましょう', text: '下の入力欄から症状を入力してみてください。' }
  ];

  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function medFormIcon(form) {
    if (form === 'granules') {
      return (
        '<svg class="ui-med-type-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
          '<path fill="currentColor" d="M6 4h12v2H6V4zm0 4h12l-1 12H7L6 8zm4 2v8h2v-8h-2z"/>' +
        '</svg>'
      );
    }
    return (
      '<svg class="ui-med-type-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
        '<ellipse cx="12" cy="12" rx="9" ry="5" fill="none" stroke="currentColor" stroke-width="1.5"/>' +
        '<line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="1.5"/>' +
      '</svg>'
    );
  }

  function scoreRingHtml(score) {
    var pct = Math.max(0, Math.min(100, score));
    return (
      '<div class="ui-score-ring" style="--ui-score:' + pct + '" role="img" aria-label="おすすめ度 ' + pct + 'パーセント">' +
        '<div class="ui-score-ring__track" aria-hidden="true"></div>' +
        '<div class="ui-score-ring__fill" aria-hidden="true"></div>' +
        '<div class="ui-score-ring__inner">' +
          '<span class="ui-score-ring__value">' + pct + '</span>' +
          '<span class="ui-score-ring__unit">%</span>' +
        '</div>' +
      '</div>'
    );
  }

  function symptomTagsHtml(symptoms) {
    return (
      '<div class="ui-symptom-tags" aria-label="症状マッチ">' +
        symptoms.map(function (s) {
          return '<span class="ui-symptom-tag">' + esc(s) + '</span>';
        }).join('') +
      '</div>'
    );
  }

  function medicineImageVariantClass(variant) {
    if (variant === 'pro' || variant === 'card') return 'ui-med-image--card';
    return 'ui-med-image--' + variant;
  }

  function medicineImageHtml(m, opts) {
    opts = opts || {};
    var variant = opts.variant || 'card';
    var variantClass = medicineImageVariantClass(variant);
    var extraClass = variant === 'playful' ? ' ui-card-hero' : '';
    var url = m.imageUrl;

    if (url) {
      return (
        '<div class="ui-med-image ' + variantClass + extraClass + '">' +
          '<img src="' + esc(url) + '" alt="' + esc(m.name) + '" loading="lazy" decoding="async">' +
        '</div>'
      );
    }

    var iconHtml = variant === 'playful'
      ? ''
      : '<span class="ui-med-image__icon" aria-hidden="true">' + medFormIcon(m.form) + '</span>';

    return (
      '<div class="ui-med-image ui-med-image--placeholder ' + variantClass + extraClass + '" data-no-image="true" aria-label="画像なし">' +
        iconHtml +
        '<span class="ui-med-image__label">Noimage</span>' +
      '</div>'
    );
  }

  function cardHtmlPlayful(m) {
    return (
      '<article class="ui-card ui-card--playful" role="listitem" aria-label="' + esc(m.name) + '">' +
        medicineImageHtml(m, { variant: 'playful' }) +
        '<div class="ui-card-body">' +
          '<div class="ui-card-rank">第' + m.rank + '候補</div>' +
          '<div class="ui-card-name">' + esc(m.name) + '</div>' +
          '<div class="ui-card-maker">' + esc(m.maker) + '</div>' +
          '<div class="ui-card-section">' +
            '<div class="ui-card-label">効能・効果</div>' +
            '<div class="ui-card-text">' + esc(m.efficacy) + '</div>' +
          '</div>' +
          '<div class="ui-card-section">' +
            '<div class="ui-card-label">推奨理由</div>' +
            '<div class="ui-card-text">' + esc(m.reason) + '</div>' +
          '</div>' +
          '<div class="ui-card-score">おすすめ度 ' + m.score + '%</div>' +
        '</div>' +
      '</article>'
    );
  }

  function cardHtmlPro(m) {
    return (
      '<article class="ui-card ui-card--pro" role="listitem" aria-label="' + esc(m.name) + '">' +
        medicineImageHtml(m, { variant: 'pro' }) +
        '<header class="ui-card-pro-head">' +
          '<span class="ui-med-badge ui-med-badge--rank">第' + m.rank + '候補</span>' +
          '<span class="ui-med-badge ui-med-badge--otc">OTC</span>' +
        '</header>' +
        '<div class="ui-card-pro-main">' +
          '<div class="ui-card-pro-info">' +
            medFormIcon(m.form) +
            '<h3 class="ui-card-name">' + esc(m.name) + '</h3>' +
            '<p class="ui-card-maker">' + esc(m.maker) + '</p>' +
            symptomTagsHtml(m.symptoms) +
          '</div>' +
          scoreRingHtml(m.score) +
        '</div>' +
        '<div class="ui-card-pro-meta">' +
          '<span class="ui-med-badge ui-med-badge--type">' + esc(m.medType) + '</span>' +
          '<span class="ui-age-suit" title="' + esc(m.ageLabel) + '">' +
            '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="7" r="3" fill="currentColor"/><path fill="currentColor" d="M6 20v-1.5c0-2.5 2.7-4 6-4s6 1.5 6 4V20H6z"/></svg>' +
            '<span>' + esc(m.ageLabel) + '</span>' +
          '</span>' +
        '</div>' +
        '<div class="ui-card-pro-detail is-collapsed">' +
          '<div class="ui-card-section">' +
            '<div class="ui-card-label">効能・効果</div>' +
            '<div class="ui-card-text ui-clamp-2">' + esc(m.efficacy) + '</div>' +
          '</div>' +
          '<div class="ui-card-section">' +
            '<div class="ui-card-label">推奨理由</div>' +
            '<div class="ui-card-text ui-clamp-2">' + esc(m.reason) + '</div>' +
          '</div>' +
          '<button type="button" class="ui-card-expand" data-expand aria-expanded="false">詳細を見る</button>' +
        '</div>' +
        '<p class="ui-trust-strip">※OTC医薬品の情報は参考です。症状が続く場合は医師・薬剤師にご相談ください。</p>' +
      '</article>'
    );
  }

  function cardHtml(m, style) {
    return style === 'playful' ? cardHtmlPlayful(m) : cardHtmlPro(m);
  }

  function matrixBlockHtml() {
    var rows = [
      { label: '商品画像', html: function (m) { return medicineImageHtml(m, { variant: 'thumb' }); } },
      { label: 'おすすめ度', key: 'score', fmt: function (m) { return m.score + '%'; } },
      { label: '医薬品種別', key: 'medType' },
      { label: '対象年齢', key: 'ageLabel' },
      { label: '効能・効果', key: 'efficacy' },
      { label: '推奨理由', key: 'reason' }
    ];
    var thead =
      '<tr><th scope="col" class="ui-matrix-corner">比較項目</th>' +
      MEDICINES.map(function (m) {
        return '<th scope="col"><span class="ui-matrix-rank">第' + m.rank + '候補</span>' + esc(m.name) + '</th>';
      }).join('') +
      '</tr>';
    var tbody = rows.map(function (row) {
      return (
        '<tr><th scope="row">' + row.label + '</th>' +
        MEDICINES.map(function (m) {
          if (row.html) return '<td class="ui-matrix-image-cell">' + row.html(m) + '</td>';
          var val = row.fmt ? row.fmt(m) : m[row.key];
          return '<td>' + esc(String(val)) + '</td>';
        }).join('') +
        '</tr>'
      );
    }).join('');
    return (
      '<div class="ui-matrix-wrap app-scrollbar">' +
        '<table class="ui-matrix">' +
          '<thead>' + thead + '</thead>' +
          '<tbody>' + tbody + '</tbody>' +
        '</table>' +
      '</div>'
    );
  }

  function gridBlockHtml() {
    var cards = MEDICINES.map(function (m, i) {
      return (
        '<article class="ui-product-card" role="listitem" data-product-index="' + i + '" tabindex="0">' +
          medicineImageHtml(m, { variant: 'thumb' }) +
          '<span class="ui-product-rank">第' + m.rank + '候補</span>' +
          '<h3 class="ui-product-name">' + esc(m.name) + '</h3>' +
          '<p class="ui-product-maker">' + esc(m.maker) + '</p>' +
          '<div class="ui-product-score">' + m.score + '%</div>' +
          '<button type="button" class="ui-product-detail-btn" data-product-index="' + i + '">詳細を見る</button>' +
        '</article>'
      );
    }).join('');
    return (
      '<div class="ui-product-grid" role="list">' + cards + '</div>' +
      '<div class="ui-product-drawer" id="ui-product-drawer" aria-hidden="true" role="dialog" aria-label="製品詳細">' +
        '<div class="ui-product-drawer-backdrop" data-drawer-close></div>' +
        '<div class="ui-product-drawer-panel app-scrollbar">' +
          '<button type="button" class="ui-product-drawer-close" data-drawer-close aria-label="閉じる">&times;</button>' +
          '<div id="ui-product-drawer-content"></div>' +
        '</div>' +
      '</div>'
    );
  }

  function heroBlockHtml() {
    var thumbs = MEDICINES.map(function (m, i) {
      return (
        '<button type="button" class="ui-hero-thumb' + (i === 0 ? ' is-active' : '') + '" data-hero-index="' + i + '" role="tab" aria-selected="' + (i === 0 ? 'true' : 'false') + '">' +
          medicineImageHtml(m, { variant: 'thumb' }) +
          '<span class="ui-hero-thumb-rank">' + m.rank + '</span>' +
          '<span class="ui-hero-thumb-name">' + esc(m.name) + '</span>' +
          '<span class="ui-hero-thumb-score">' + m.score + '%</span>' +
        '</button>'
      );
    }).join('');
    return (
      '<div class="ui-hero-region" data-hero-region>' +
        '<div class="ui-hero-main" id="ui-hero-main">' + cardHtmlPro(MEDICINES[0]) + '</div>' +
        '<div class="ui-hero-thumbs" role="tablist" aria-label="他の候補">' + thumbs + '</div>' +
      '</div>'
    );
  }

  function labelBlockHtml() {
    return MEDICINES.map(function (m) {
      return (
        '<article class="ui-drug-label" role="listitem">' +
          medicineImageHtml(m, { variant: 'hero' }) +
          '<header class="ui-drug-label__head">' +
            '<div class="ui-drug-label__title-row">' +
              '<span class="ui-drug-label__otc">OTC医薬品</span>' +
              '<span class="ui-drug-label__rank">第' + m.rank + '候補</span>' +
            '</div>' +
            '<h3 class="ui-drug-label__name">' + esc(m.name) + '</h3>' +
            '<p class="ui-drug-label__maker">製造販売: ' + esc(m.maker) + '</p>' +
          '</header>' +
          '<section class="ui-drug-label__section">' +
            '<h4 class="ui-drug-label__heading">効能・効果</h4>' +
            '<p>' + esc(m.efficacy) + '</p>' +
          '</section>' +
          '<section class="ui-drug-label__section">' +
            '<h4 class="ui-drug-label__heading">用法・用量</h4>' +
            '<p>用法用量を守り、なるべく空腹時を避けて服用してください。<br>15歳以上: 1回2錠、1日3回</p>' +
          '</section>' +
          '<section class="ui-drug-label__section ui-drug-label__section--warn">' +
            '<h4 class="ui-drug-label__heading">使用上の注意</h4>' +
            '<p>運転・機械操作をしないでください。服用後の眠気に注意。</p>' +
          '</section>' +
          '<section class="ui-drug-label__section">' +
            '<h4 class="ui-drug-label__heading">AI推奨理由</h4>' +
            '<p>' + esc(m.reason) + '</p>' +
          '</section>' +
          '<footer class="ui-drug-label__footer">' +
            '<span class="ui-drug-label__score">適合度 ' + m.score + '%</span>' +
            '<span class="ui-drug-label__pmda">※本表示は参考情報です（薬情表示様式参考）</span>' +
          '</footer>' +
        '</article>'
      );
    }).join('');
  }

  function carouselNavHtml(id, count) {
    var dots = '';
    for (var i = 0; i < count; i++) {
      dots += '<button type="button" class="ui-carousel-dot' + (i === 0 ? ' is-active' : '') + '" data-carousel-dot="' + i + '" aria-label="第' + (i + 1) + '候補へ" aria-current="' + (i === 0 ? 'true' : 'false') + '"></button>';
    }
    return (
      '<nav class="ui-carousel-nav" aria-label="カルーセル操作" data-carousel-nav="' + id + '">' +
        '<button type="button" class="ui-carousel-arrow ui-carousel-arrow--prev" data-carousel-prev aria-label="前の候補">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M15 6l-6 6 6 6"/></svg>' +
        '</button>' +
        '<div class="ui-carousel-dots" role="tablist" aria-label="候補インジケータ">' + dots + '</div>' +
        '<span class="ui-carousel-counter" data-carousel-counter>1 / ' + count + '</span>' +
        '<button type="button" class="ui-carousel-arrow ui-carousel-arrow--next" data-carousel-next aria-label="次の候補">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9 6l6 6-6 6"/></svg>' +
        '</button>' +
      '</nav>'
    );
  }

  function carouselBlockHtml(cards, style) {
    var id = 'carousel-' + (++carouselUid);
    var proClass = style === 'pro' ? ' ui-carousel-pro' : '';
    return (
      '<div class="ui-carousel-region" data-carousel-region="' + id + '">' +
        '<div class="ui-carousel-wrap app-scrollbar' + proClass + '" id="' + id + '" tabindex="0" role="region" aria-label="推奨医薬品カルーセル" data-carousel-wrap>' +
          '<div class="ui-carousel" role="list">' + cards + '</div>' +
        '</div>' +
        carouselNavHtml(id, MEDICINES.length) +
      '</div>'
    );
  }

  function scoreGrid(m) {
    var s = m.scores;
    return (
      '<div class="ui-score-grid">' +
        '<span class="ui-score-chip">症状適合 ' + s.symptom + '%</span>' +
        '<span class="ui-score-chip">効能特異 ' + s.efficacy + '%</span>' +
        '<span class="ui-score-chip">年齢適合 ' + s.age + '%</span>' +
        '<span class="ui-score-chip">用法簡便 ' + s.usage + '%</span>' +
      '</div>'
    );
  }

  function recoBlock(layout, opts) {
    opts = opts || {};
    var cardStyle = opts.carouselStyle === 'playful' ? 'playful' : 'pro';
    var stackStyle = opts.carouselStyle === 'playful' ? 'playful' : 'pro';
    var cards = MEDICINES.map(function (m) { return cardHtml(m, cardStyle); }).join('');
    var inner;
    if (layout === 'stack') {
      inner = '<div class="ui-stack">' + MEDICINES.map(function (m) { return cardHtml(m, stackStyle); }).join('') + '</div>';
    } else if (layout === 'shelf') {
      inner =
        '<div class="ui-shelf" role="list">' +
          '<div class="ui-shelf-row"><div class="ui-shelf-label">第1棚 — 総合感冒薬</div><div class="ui-shelf-items">' + cardHtml(MEDICINES[0], 'playful') + '</div></div>' +
          '<div class="ui-shelf-row"><div class="ui-shelf-label">第2棚 — 広効能タイプ</div><div class="ui-shelf-items">' + cardHtml(MEDICINES[1], 'playful') + '</div></div>' +
          '<div class="ui-shelf-row"><div class="ui-shelf-label">第3棚 — のど特化</div><div class="ui-shelf-items">' + cardHtml(MEDICINES[2], 'playful') + '</div></div>' +
        '</div>';
    } else if (layout === 'story') {
      inner =
        '<div class="ui-story-wrap app-scrollbar" role="list">' +
          '<div class="ui-story">' + MEDICINES.map(function (m) { return cardHtml(m, stackStyle); }).join('') + '</div>' +
          '<div class="ui-story-hint" aria-hidden="true">↑↓ スワイプで候補を比較</div>' +
        '</div>';
    } else if (layout === 'matrix') {
      inner = matrixBlockHtml();
    } else if (layout === 'grid') {
      inner = gridBlockHtml();
    } else if (layout === 'hero') {
      inner = heroBlockHtml();
    } else if (layout === 'label') {
      inner = '<div class="ui-label-stack">' + labelBlockHtml() + '</div>';
    } else {
      inner = carouselBlockHtml(cards, cardStyle);
    }

    var introIcon = cardStyle === 'pro'
      ? '<svg class="ui-reco-intro-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2"/><line x1="16" y1="16" x2="21" y2="21" stroke="currentColor" stroke-width="2"/></svg>'
      : '🔍 ';

    return (
      '<div class="ui-reco-block' + (cardStyle === 'pro' ? ' ui-reco-block--pro' : '') + '">' +
        '<div class="ui-reco-intro">' + introIcon + '推定症状: <span class="ui-symptom-tags ui-symptom-tags--inline"><span class="ui-symptom-tag">のど痛</span><span class="ui-symptom-tag">発熱</span><span class="ui-symptom-tag">鼻水</span></span></div>' +
        inner +
        scoreGrid(MEDICINES[0]) +
        '<div class="ui-alert ui-alert--danger"><strong>⚠️ アレルギー注意</strong><br>アスピリン系成分に注意が必要な場合があります。</div>' +
        '<div class="ui-alert ui-alert--warn"><strong>⚠️ 相互作用</strong><br>ワーファリン服用中の方は医師・薬剤師にご相談ください。</div>' +
        '<div class="ui-alert ui-alert--caution"><strong>⚠️ 使用上の注意</strong><br>運転・機械操作前の服用は避けてください。用法用量を守ってご使用ください。</div>' +
        '<div class="ui-alert ui-alert--info"><strong>🏥 受診の目安</strong><br>38.5℃以上が3日続く、呼吸困難がある場合は医療機関を受診してください。</div>' +
        feedbackHtml('この推奨結果はいかがでしたか？') +
      '</div>'
    );
  }

  function feedbackHtml(question) {
    return (
      '<div class="ui-feedback">' +
        '<span>' + esc(question) + '</span>' +
        '<button type="button" data-feedback="up">👍 適切</button>' +
        '<button type="button" data-feedback="down">👎 不適切</button>' +
      '</div>'
    );
  }

  function symptomChipsHtml(opts) {
    opts = opts || {};
    if (opts.a11yPictogram) {
      return (
        '<div class="ui-chips ui-chips--pictogram">' +
          '<button type="button" class="ui-chip ui-chip--pictogram" data-prompt="のどが痛くて熱があります">' +
            '<span class="ui-pictogram" aria-hidden="true"><svg viewBox="0 0 32 32"><circle cx="16" cy="10" r="6" fill="none" stroke="currentColor" stroke-width="2"/><path d="M10 22c0-4 2.7-7 6-7s6 3 6 7" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 14h8" stroke="currentColor" stroke-width="2"/></svg></span>' +
            '<span class="ui-chip-label">のど痛・発熱</span></button>' +
          '<button type="button" class="ui-chip ui-chip--pictogram" data-prompt="鼻水とくしゃみが止まりません">' +
            '<span class="ui-pictogram" aria-hidden="true"><svg viewBox="0 0 32 32"><ellipse cx="16" cy="14" rx="8" ry="10" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 20c2 3 6 3 8 0" fill="none" stroke="currentColor" stroke-width="2"/></svg></span>' +
            '<span class="ui-chip-label">鼻水・くしゃみ</span></button>' +
          '<button type="button" class="ui-chip ui-chip--pictogram" data-prompt="頭痛と吐き気があります">' +
            '<span class="ui-pictogram" aria-hidden="true"><svg viewBox="0 0 32 32"><circle cx="16" cy="14" r="9" fill="none" stroke="currentColor" stroke-width="2"/><path d="M10 12h4M18 12h4M13 18c1 2 5 2 6 0" fill="none" stroke="currentColor" stroke-width="2"/></svg></span>' +
            '<span class="ui-chip-label">頭痛・吐き気</span></button>' +
        '</div>'
      );
    }
    return (
      '<div class="ui-chips">' +
        '<button type="button" class="ui-chip" data-prompt="のどが痛くて熱があります">のど痛・発熱</button>' +
        '<button type="button" class="ui-chip" data-prompt="鼻水とくしゃみが止まりません">鼻水・くしゃみ</button>' +
        '<button type="button" class="ui-chip" data-prompt="頭痛と吐き気があります">頭痛・吐き気</button>' +
      '</div>'
    );
  }

  function messagesHtml(recoLayout, recoOpts) {
    return (
      '<div class="ui-msg ui-msg--bot">' +
        '<div class="ui-bubble">' +
          'こんにちは。症状を教えてください。<br><br>' +
          symptomChipsHtml(recoOpts) +
        '</div>' +
      '</div>' +
      '<div class="ui-msg ui-msg--user">' +
        '<div class="ui-bubble">のどが痛くて熱があります。鼻水も少しあります。</div>' +
      '</div>' +
      '<div class="ui-msg ui-msg--bot">' +
        '<div class="ui-bubble ui-bubble--processing">' +
          '<span class="ui-dots" aria-hidden="true"><span></span><span></span><span></span></span>' +
          '<span>症状を分析しています…</span>' +
        '</div>' +
      '</div>' +
      '<div class="ui-msg ui-msg--bot">' +
        '<div class="ui-bubble">' + recoBlock(recoLayout, recoOpts) + '</div>' +
      '</div>' +
      '<div class="ui-msg ui-msg--bot">' +
        '<div class="ui-bubble ui-bubble--manual">' +
          '<strong>👤 薬剤師 返信</strong><br><br>' +
          '追加で、現在服用中のお薬があれば教えてください。より安全な提案のため確認させていただきます。' +
        '</div>' +
      '</div>' +
      '<div class="ui-msg ui-msg--bot">' +
        '<div class="ui-bubble">' +
          '<strong>❓ 追加でお伺いしたいこと</strong>（優先度: 重要）<br>' +
          'より安全な使用のため、以下を教えてください：<ul style="margin:8px 0;padding-left:1.2em">' +
          '<li>アレルギーはありますか？</li><li>現在の体温は何度ですか？</li></ul>' +
          '<button type="button" class="ui-btn ui-btn--primary ui-btn--block" data-modal="attribute">📋 追加情報を入力</button>' +
        '</div>' +
      '</div>'
    );
  }

  function modalsHtml() {
    return (
      '<div class="ui-modal-backdrop" id="modal-info" aria-hidden="true">' +
        '<div class="ui-modal" role="dialog" aria-labelledby="modal-info-title">' +
          '<div class="ui-modal-header">' +
            '<h2 id="modal-info-title">アプリ情報</h2>' +
            '<button type="button" class="ui-modal-close" data-close>&times;</button>' +
          '</div>' +
          '<div class="ui-modal-body app-scrollbar">' +
            '<a class="ui-list-item" href="../index.html"><div class="ui-list-icon">📄</div><div><div class="ui-list-title">UIパターン一覧</div><div class="ui-list-desc">他のデザイン案を見る</div></div><div class="ui-list-arrow">→</div></a>' +
            '<div class="ui-list-item" data-detail="overview"><div class="ui-list-icon">📱</div><div><div class="ui-list-title">アプリ概要</div><div class="ui-list-desc">β版・研究目的の説明</div></div><div class="ui-list-arrow">→</div></div>' +
            '<div class="ui-list-item" data-detail="usage"><div class="ui-list-icon">📖</div><div><div class="ui-list-title">使い方</div><div class="ui-list-desc">チャット・音声入力・薬剤師要請</div></div><div class="ui-list-arrow">→</div></div>' +
            '<div class="ui-list-item" data-detail="privacy"><div class="ui-list-icon">🔒</div><div><div class="ui-list-title">プライバシー</div><div class="ui-list-desc">個人情報の取り扱い</div></div><div class="ui-list-arrow">→</div></div>' +
            '<div class="ui-list-item" data-detail="settings"><div class="ui-list-icon">⚙️</div><div><div class="ui-list-title">表示設定</div><div class="ui-list-desc">文字サイズ</div></div><div class="ui-list-arrow">→</div></div>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="ui-modal-backdrop" id="modal-userinfo" aria-hidden="true">' +
        '<div class="ui-modal" role="dialog">' +
          '<div class="ui-modal-header"><h3>👤 ユーザー情報登録</h3><button type="button" class="ui-modal-close" data-close>&times;</button></div>' +
          '<div class="ui-modal-body app-scrollbar">' +
            '<div class="ui-form-group"><label>年齢 *</label><input type="number" min="0" max="120" placeholder="例: 30"></div>' +
            '<div class="ui-form-group"><label>性別 *</label><select><option>選択してください</option><option>男性</option><option>女性</option></select></div>' +
            '<div class="ui-form-group"><label>アレルギー</label><input type="text" placeholder="例: 花粉、卵"></div>' +
            '<div class="ui-form-group"><label>服用中の薬</label><input type="text" placeholder="例: 血圧の薬"></div>' +
            '<div class="ui-form-group"><label>既往症</label><input type="text" placeholder="例: 糖尿病"></div>' +
            '<div class="ui-form-group"><label>その他</label><textarea rows="3" placeholder="眠気が心配 等"></textarea></div>' +
            '<button type="button" class="ui-btn ui-btn--primary ui-btn--block" data-toast="保存しました（デモ）">💾 保存</button>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="ui-modal-backdrop" id="modal-attribute" aria-hidden="true">' +
        '<div class="ui-modal" role="dialog">' +
          '<div class="ui-modal-header"><h3>📋 追加情報の入力</h3><button type="button" class="ui-modal-close" data-close>&times;</button></div>' +
          '<div class="ui-modal-body app-scrollbar">' +
            '<div class="ui-form-group"><label>年齢</label><input type="number" placeholder="例: 30"></div>' +
            '<div class="ui-form-group"><label>性別</label><select><option>男性</option><option>女性</option></select></div>' +
            '<div class="ui-form-group"><label>アレルギー</label><input type="text"></div>' +
            '<div class="ui-form-group"><label>症状開始日</label><input type="date"><small>カレンダーから選択</small></div>' +
            '<div class="ui-form-group"><label>その他</label><textarea rows="3"></textarea></div>' +
            '<button type="button" class="ui-btn ui-btn--primary ui-btn--block" data-toast="再分析を送信（デモ）">📤 送信して再分析</button>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="ui-modal-backdrop" id="modal-feedback" aria-hidden="true">' +
        '<div class="ui-modal" role="dialog">' +
          '<div class="ui-modal-header"><h3>フィードバック</h3><button type="button" class="ui-modal-close" data-close>&times;</button></div>' +
          '<div class="ui-modal-body app-scrollbar">' +
            '<p>具体的にどこが適切でなかったか教えてください：</p>' +
            '<label style="display:block;margin:8px 0"><input type="checkbox"> 医薬品の推奨が表示されなかった</label>' +
            '<textarea rows="4" style="width:100%;padding:10px;border:1px solid var(--ui-border);border-radius:8px;font:inherit" placeholder="改善点…"></textarea>' +
          '</div>' +
          '<div class="ui-modal-footer">' +
            '<button type="button" class="ui-btn ui-btn--secondary" data-close>キャンセル</button>' +
            '<button type="button" class="ui-btn ui-btn--primary" data-toast="フィードバックありがとうございます！">送信</button>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="ui-onboarding" id="onboarding" aria-hidden="true">' +
        '<div class="ui-onboarding-card">' +
          '<h2 id="ob-title"></h2><p id="ob-text"></p>' +
          '<div class="ui-dots-nav" id="ob-dots"></div>' +
          '<button type="button" class="ui-btn ui-btn--secondary" id="ob-skip">スキップ</button> ' +
          '<button type="button" class="ui-btn ui-btn--primary" id="ob-next">次へ</button>' +
        '</div>' +
      '</div>' +
      '<div id="ui-toast" style="position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#333;color:#fff;padding:10px 18px;border-radius:999px;font-size:0.85rem;opacity:0;transition:opacity .3s;z-index:3000;pointer-events:none"></div>'
    );
  }

  function bodymapHtml() {
    return (
      '<aside class="ui-split-pane ui-split-pane--left ui-bodymap-pane app-scrollbar" aria-label="症状部位マップ">' +
        '<div class="ui-bodymap">' +
          '<h2 class="ui-bodymap-title">どこがつらいですか？</h2>' +
          '<p class="ui-bodymap-sub">部位をタップして症状を入力</p>' +
          '<div class="ui-bodymap-figure">' +
            '<svg viewBox="0 0 120 280" class="ui-bodymap-svg" role="img" aria-label="人体図">' +
              '<ellipse class="ui-bodymap-zone" data-zone="頭" data-prompt="頭が痛いです" cx="60" cy="28" rx="22" ry="26" />' +
              '<rect class="ui-bodymap-zone" data-zone="のど" data-prompt="のどが痛いです" x="48" y="54" width="24" height="16" rx="4" />' +
              '<path class="ui-bodymap-zone" data-zone="胸" data-prompt="胸が苦しいです" d="M38 72 L82 72 L78 130 L42 130 Z" />' +
              '<path class="ui-bodymap-zone" data-zone="お腹" data-prompt="お腹が痛いです" d="M42 132 L78 132 L74 170 L46 170 Z" />' +
              '<path class="ui-bodymap-zone" data-zone="腕" data-prompt="腕がだるいです" d="M18 75 L35 72 L32 140 L15 138 Z" />' +
              '<path class="ui-bodymap-zone" data-zone="腕" data-prompt="腕がだるいです" d="M85 72 L102 75 L105 138 L88 140 Z" />' +
              '<path class="ui-bodymap-zone" data-zone="脚" data-prompt="脚が痛いです" d="M42 172 L55 172 L52 260 L38 260 Z" />' +
              '<path class="ui-bodymap-zone" data-zone="脚" data-prompt="脚が痛いです" d="M65 172 L78 172 L82 260 L68 260 Z" />' +
            '</svg>' +
          '</div>' +
          '<div class="ui-bodymap-selected" id="bodymap-selected" aria-live="polite"></div>' +
        '</div>' +
      '</aside>'
    );
  }

  function telehealthStripHtml() {
    return (
      '<div class="ui-telehealth-strip">' +
        '<div class="ui-telehealth-video" aria-label="ビデオ通話エリア（デモ）">' +
          '<div class="ui-telehealth-preview">' +
            '<span class="ui-telehealth-avatar" aria-hidden="true">👨‍⚕️</span>' +
            '<span class="ui-telehealth-label">オンライン診療待機中</span>' +
            '<span class="ui-telehealth-status"><span class="ui-telehealth-dot"></span>接続準備完了</span>' +
          '</div>' +
          '<button type="button" class="ui-telehealth-cta" data-toast="ビデオ通話を開始（デモ）">📹 通話開始</button>' +
        '</div>' +
        '<div class="ui-trust-badges" aria-label="信頼バッジ">' +
          '<span class="ui-trust-badge">🏥 医師監修</span>' +
          '<span class="ui-trust-badge">🔒 暗号化通信</span>' +
          '<span class="ui-trust-badge">✓ PMDA準拠情報</span>' +
        '</div>' +
      '</div>'
    );
  }

  function pharmacistStripHtml() {
    return (
      '<div class="ui-pharmacist-strip">' +
        '<div class="ui-pharmacist-avatar" aria-hidden="true">' +
          '<svg viewBox="0 0 48 48"><circle cx="24" cy="17" r="9" fill="#e2e8f0"/><path fill="#e2e8f0" d="M8 44c0-8 7-14 16-14s16 6 16 14"/></svg>' +
          '<span class="ui-pharmacist-badge">薬</span>' +
        '</div>' +
        '<div class="ui-pharmacist-info">' +
          '<strong>監修: 田中 健一 薬剤師</strong>' +
          '<span>第一類医薬品登録販売者 · 日本薬剤師会会員 · 相談歴12年</span>' +
        '</div>' +
        '<button type="button" class="ui-pharmacist-call" data-toast="薬剤師に電話（デモ）">📞 相談</button>' +
      '</div>'
    );
  }

  function timelineHtml() {
    return (
      '<aside class="ui-split-pane ui-split-pane--left app-scrollbar" aria-label="症状タイムライン">' +
        '<div class="ui-timeline">' +
          '<h2 class="ui-timeline-title">症状タイムライン</h2>' +
          '<p class="ui-timeline-sub">入力内容を時系列で整理</p>' +
          '<ol class="ui-timeline-list">' +
            '<li class="ui-timeline-item ui-timeline-item--done"><time>09:15</time><span>くしゃみ・鼻水</span></li>' +
            '<li class="ui-timeline-item ui-timeline-item--done"><time>10:30</time><span>のどの痛み</span></li>' +
            '<li class="ui-timeline-item ui-timeline-item--active"><time>11:00</time><span>発熱（37.8℃）</span></li>' +
            '<li class="ui-timeline-item"><time>—</time><span>追加症状待ち</span></li>' +
          '</ol>' +
          '<div class="ui-timeline-tags">' +
            '<span class="ui-timeline-tag">風邪疑い</span>' +
            '<span class="ui-timeline-tag">要フォロー</span>' +
          '</div>' +
        '</div>' +
      '</aside>'
    );
  }

  function chatPaneHtml(recoLayout, layout, recoOpts) {
    var orbHtml = layout === 'orb'
      ? '<div class="ui-orb" aria-hidden="true"><span class="ui-orb-core"></span><span class="ui-orb-ring"></span></div>'
      : '';
    return (
      '<div class="ui-split-pane ui-split-pane--right">' +
        '<div class="ui-messages app-scrollbar" id="messages">' +
          '<div class="ui-particles" aria-hidden="true" id="particles"></div>' +
          messagesHtml(recoLayout, recoOpts) +
        '</div>' +
        '<div class="ui-input-bar">' +
          '<form class="ui-input-row" id="chat-form" onsubmit="return false">' +
            '<button type="button" class="ui-mic" title="音声入力" data-toast="音声入力（デモ）">🎤</button>' +
            '<div class="ui-textarea-wrap"><textarea class="ui-textarea app-scrollbar" rows="1" placeholder="症状を入力してください…" id="msg-input"></textarea></div>' +
            '<button type="submit" class="ui-send" title="送信">➤</button>' +
          '</form>' +
        '</div>' +
        (layout === 'compact' || layout === 'orb' || layout === 'wearable' || layout === 'wechat' || layout === 'whatsapp'
          ? '<nav class="ui-bottom-nav' + (layout === 'wechat' ? ' ui-bottom-nav--wechat' : '') + '" aria-label="クイック操作">' +
              '<button type="button" class="ui-nav-btn" data-modal="userinfo"><span>👤</span><span>情報</span></button>' +
              '<button type="button" class="ui-nav-btn" data-toast="履歴クリア"><span>🗑️</span><span>クリア</span></button>' +
              '<button type="button" class="ui-nav-btn" data-toast="新セッション"><span>🔄</span><span>新規</span></button>' +
              '<button type="button" class="ui-nav-btn" data-modal="info"><span>ℹ️</span><span>ヘルプ</span></button>' +
              '<button type="button" class="ui-nav-btn" data-toast="薬剤師要請"><span>👨‍⚕️</span><span>要請</span></button>' +
            '</nav>'
          : '') +
        orbHtml +
      '</div>'
    );
  }

  function shellHtml(opts) {
    var layout = opts.layout || 'default';
    var recoLayout = opts.recoLayout || 'carousel';
    var recoOpts = {
      carouselStyle: opts.carouselStyle || (recoLayout === 'carousel' ? 'pro' : 'playful'),
      a11yPictogram: !!opts.a11yPictogram
    };
    var showDev = opts.showDev !== false;
    var headerClass = 'ui-header';
    if (layout === 'compact' || layout === 'orb' || layout === 'wearable' || layout === 'whatsapp' || layout === 'wechat') headerClass += ' ui-header--compact-nav';
    if (layout === 'orb' || layout === 'wearable') headerClass += ' ui-header--minimal';
    if (layout === 'whatsapp' || layout === 'wechat') headerClass += ' ui-header--platform';

    var viewportHtml;
    if (layout === 'split') {
      viewportHtml =
        '<div class="ui-viewport ui-viewport--split">' +
          timelineHtml() +
          chatPaneHtml(recoLayout, layout, recoOpts) +
        '</div>';
    } else if (layout === 'bodymap') {
      viewportHtml =
        '<div class="ui-viewport ui-viewport--split">' +
          bodymapHtml() +
          chatPaneHtml(recoLayout, layout, recoOpts) +
        '</div>';
    } else if (layout === 'wearable') {
      viewportHtml =
        '<div class="ui-wearable-frame">' +
          '<div class="ui-wearable-bezel">' +
            '<div class="ui-wearable-screen">' + chatPaneHtml(recoLayout, layout, recoOpts) + '</div>' +
          '</div>' +
        '</div>';
    } else {
      viewportHtml =
        '<div class="ui-viewport">' + chatPaneHtml(recoLayout, layout, recoOpts) + '</div>';
    }

    var stripHtml = '';
    if (layout === 'telehealth') stripHtml = telehealthStripHtml();
    if (layout === 'pharmacist') stripHtml = pharmacistStripHtml();

    return (
      '<div class="ui-app" data-theme="' + esc(opts.theme || 'default') + '" data-layout="' + esc(layout) + '" data-reco="' + esc(recoLayout) + '" data-carousel-style="' + esc(recoOpts.carouselStyle) + '">' +
        (showDev ? '<span class="ui-dev-badge" role="status">UI MOCK</span>' : '') +
        '<header class="' + headerClass + '">' +
          '<div class="ui-lang">' +
            '<button type="button" class="ui-lang-btn" id="lang-toggle" aria-expanded="false">🇯🇵 ▼</button>' +
            '<div class="ui-lang-dropdown" id="lang-menu">' +
              ['🇯🇵 日本語', '🇺🇸 English', '🇰🇷 한국어', '🇨🇳 中文'].map(function (l, i) {
                return '<button type="button" class="ui-lang-option' + (i === 0 ? ' active' : '') + '">' + l + '</button>';
              }).join('') +
            '</div>' +
          '</div>' +
          '<div class="ui-brand">' +
            '<h1>チャット型医薬品相談</h1>' +
            '<p>症状を入力してOTC医薬品の候補を確認</p>' +
          '</div>' +
          '<div class="ui-info"><button type="button" class="ui-icon-btn" data-modal="info" aria-label="情報">ℹ️</button></div>' +
          '<div class="ui-actions">' +
            '<button type="button" class="ui-action-btn ui-action-btn--primary" data-modal="userinfo">👤 ユーザー情報</button>' +
            '<button type="button" class="ui-action-btn ui-action-btn--dark" data-toast="履歴をクリア（デモ）">🗑️ 履歴クリア</button>' +
            '<button type="button" class="ui-action-btn ui-action-btn--ghost" data-toast="新セッション（デモ）">🔄 新セッション</button>' +
            '<button type="button" class="ui-action-btn ui-action-btn--warn" data-toast="薬剤師要請（デモ）">👨‍⚕️ 薬剤師要請</button>' +
            '<button type="button" class="ui-action-btn ui-action-btn--ghost" id="show-onboarding">📖 ガイド</button>' +
          '</div>' +
        '</header>' +
        stripHtml +
        viewportHtml +
      '</div>' +
      modalsHtml()
    );
  }

  function toast(msg) {
    var el = document.getElementById('ui-toast');
    if (!el) return;
    el.textContent = msg;
    el.style.opacity = '1';
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.style.opacity = '0'; }, 2200);
  }

  function openModal(id) {
    var m = document.getElementById('modal-' + id);
    if (m) { m.classList.add('show'); m.setAttribute('aria-hidden', 'false'); }
  }

  function closeModals() {
    document.querySelectorAll('.ui-modal-backdrop.show').forEach(function (m) {
      m.classList.remove('show');
      m.setAttribute('aria-hidden', 'true');
    });
  }

  var obIndex = 0;
  function renderOnboarding() {
    var slide = ONBOARDING[obIndex];
    document.getElementById('ob-title').textContent = slide.title;
    document.getElementById('ob-text').textContent = slide.text;
    document.getElementById('ob-dots').innerHTML = ONBOARDING.map(function (_, i) {
      return '<i class="' + (i === obIndex ? 'active' : '') + '"></i>';
    }).join('');
    document.getElementById('ob-next').textContent = obIndex >= ONBOARDING.length - 1 ? 'はじめる' : '次へ';
  }

  function scrollCarouselTo(wrap, index) {
    var cards = wrap.querySelectorAll('.ui-carousel .ui-card');
    if (!cards.length) return;
    var i = Math.max(0, Math.min(index, cards.length - 1));
    var card = cards[i];
    var offset = card.offsetLeft - (wrap.clientWidth - card.offsetWidth) / 2;
    if (window.matchMedia('(min-width: 769px)').matches) {
      offset = card.offsetLeft - 4;
    }
    wrap.scrollTo({ left: Math.max(0, offset), behavior: 'smooth' });
  }

  function updateCarouselState(region) {
    var wrap = region.querySelector('[data-carousel-wrap]');
    var cards = wrap ? wrap.querySelectorAll('.ui-card') : [];
    if (!wrap || !cards.length) return;
    var center = wrap.scrollLeft + wrap.clientWidth / 2;
    var active = 0;
    var minDist = Infinity;
    cards.forEach(function (card, idx) {
      var cardCenter = card.offsetLeft + card.offsetWidth / 2;
      var dist = Math.abs(cardCenter - center);
      if (dist < minDist) { minDist = dist; active = idx; }
    });
    region.querySelectorAll('[data-carousel-dot]').forEach(function (dot, idx) {
      var on = idx === active;
      dot.classList.toggle('is-active', on);
      dot.setAttribute('aria-current', on ? 'true' : 'false');
    });
    var counter = region.querySelector('[data-carousel-counter]');
    if (counter) counter.textContent = (active + 1) + ' / ' + cards.length;
  }

  function bindBodymap(root) {
    var selected = document.getElementById('bodymap-selected');
    root.querySelectorAll('.ui-bodymap-zone').forEach(function (zone) {
      zone.addEventListener('click', function () {
        root.querySelectorAll('.ui-bodymap-zone').forEach(function (z) { z.classList.remove('is-active'); });
        zone.classList.add('is-active');
        var label = zone.getAttribute('data-zone');
        var prompt = zone.getAttribute('data-prompt') || label + 'の症状があります';
        if (selected) {
          selected.innerHTML = '<span class="ui-bodymap-chip">' + esc(label) + ' を選択中</span>';
        }
        var input = document.getElementById('msg-input');
        if (input) { input.value = prompt; input.focus(); }
      });
    });
  }

  function bindProductGrid(root) {
    function openDrawer(index) {
      var drawer = document.getElementById('ui-product-drawer');
      var content = document.getElementById('ui-product-drawer-content');
      if (!drawer || !content || !MEDICINES[index]) return;
      content.innerHTML = cardHtmlPro(MEDICINES[index]);
      drawer.classList.add('is-open');
      drawer.setAttribute('aria-hidden', 'false');
    }
    function closeDrawer() {
      var drawer = document.getElementById('ui-product-drawer');
      if (!drawer) return;
      drawer.classList.remove('is-open');
      drawer.setAttribute('aria-hidden', 'true');
    }
    root.querySelectorAll('[data-product-index]').forEach(function (el) {
      el.addEventListener('click', function (e) {
        if (e.target.closest('[data-drawer-close]')) return;
        var idx = parseInt(el.getAttribute('data-product-index'), 10);
        if (!isNaN(idx)) openDrawer(idx);
      });
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          var idx = parseInt(el.getAttribute('data-product-index'), 10);
          if (!isNaN(idx)) openDrawer(idx);
        }
      });
    });
    root.querySelectorAll('[data-drawer-close]').forEach(function (btn) {
      btn.addEventListener('click', closeDrawer);
    });
  }

  function bindHeroRegion(root) {
    var region = root.querySelector('[data-hero-region]');
    if (!region) return;
    var main = document.getElementById('ui-hero-main');
    region.querySelectorAll('[data-hero-index]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var idx = parseInt(btn.getAttribute('data-hero-index'), 10);
        if (isNaN(idx) || !MEDICINES[idx] || !main) return;
        main.innerHTML = cardHtmlPro(MEDICINES[idx]);
        region.querySelectorAll('[data-hero-index]').forEach(function (b) {
          var on = b === btn;
          b.classList.toggle('is-active', on);
          b.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        main.querySelectorAll('[data-expand]').forEach(function (expandBtn) {
          expandBtn.addEventListener('click', function () {
            var detail = expandBtn.closest('.ui-card-pro-detail');
            if (detail) {
              var collapsed = detail.classList.toggle('is-collapsed');
              expandBtn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
              expandBtn.textContent = collapsed ? '詳細を見る' : '閉じる';
            }
          });
        });
      });
    });
  }

  function bindCarousels(root) {
    root.querySelectorAll('[data-carousel-region]').forEach(function (region) {
      var wrap = region.querySelector('[data-carousel-wrap]');
      if (!wrap) return;

      wrap.addEventListener('scroll', function () {
        if (wrap._scrollTimer) clearTimeout(wrap._scrollTimer);
        wrap._scrollTimer = setTimeout(function () { updateCarouselState(region); }, 60);
      }, { passive: true });

      wrap.addEventListener('wheel', function (e) {
        if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
        wrap.scrollLeft += e.deltaY;
        e.preventDefault();
      }, { passive: false });

      wrap.addEventListener('keydown', function (e) {
        var cards = wrap.querySelectorAll('.ui-card');
        if (!cards.length) return;
        var center = wrap.scrollLeft + wrap.clientWidth / 2;
        var active = 0;
        cards.forEach(function (card, idx) {
          if (Math.abs(card.offsetLeft + card.offsetWidth / 2 - center) < wrap.clientWidth / 2) active = idx;
        });
        if (e.key === 'ArrowRight') { scrollCarouselTo(wrap, active + 1); e.preventDefault(); }
        if (e.key === 'ArrowLeft') { scrollCarouselTo(wrap, active - 1); e.preventDefault(); }
      });

      var prevBtn = region.querySelector('[data-carousel-prev]');
      if (prevBtn) {
        prevBtn.addEventListener('click', function () {
          var cards = wrap.querySelectorAll('.ui-card');
          var center = wrap.scrollLeft + wrap.clientWidth / 2;
          var active = 0;
          cards.forEach(function (card, idx) {
            if (Math.abs(card.offsetLeft + card.offsetWidth / 2 - center) < wrap.clientWidth / 2) active = idx;
          });
          scrollCarouselTo(wrap, active - 1);
        });
      }

      var nextBtn = region.querySelector('[data-carousel-next]');
      if (nextBtn) {
        nextBtn.addEventListener('click', function () {
          var cards = wrap.querySelectorAll('.ui-card');
          var center = wrap.scrollLeft + wrap.clientWidth / 2;
          var active = 0;
          cards.forEach(function (card, idx) {
            if (Math.abs(card.offsetLeft + card.offsetWidth / 2 - center) < wrap.clientWidth / 2) active = idx;
          });
          scrollCarouselTo(wrap, active + 1);
        });
      }

      region.querySelectorAll('[data-carousel-dot]').forEach(function (dot) {
        dot.addEventListener('click', function () {
          scrollCarouselTo(wrap, parseInt(dot.getAttribute('data-carousel-dot'), 10));
        });
      });

      if ('IntersectionObserver' in window) {
        var observer = new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting && entry.intersectionRatio >= 0.55) {
              updateCarouselState(region);
            }
          });
        }, { root: wrap, threshold: [0.55, 0.75] });
        wrap.querySelectorAll('.ui-card').forEach(function (card) { observer.observe(card); });
      }

      updateCarouselState(region);
    });
  }

  function bindEvents(root) {
    root.addEventListener('click', function (e) {
      var expandBtn = e.target.closest('[data-expand]');
      if (expandBtn) {
        var detail = expandBtn.closest('.ui-card-pro-detail');
        if (detail) {
        var collapsed = detail.classList.toggle('is-collapsed');
          expandBtn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
          expandBtn.textContent = collapsed ? '詳細を見る' : '閉じる';
        }
        return;
      }
      var t = e.target.closest('[data-modal]');
      if (t) { openModal(t.getAttribute('data-modal')); return; }
      if (e.target.closest('[data-close]') || e.target.classList.contains('ui-modal-backdrop')) {
        closeModals();
        return;
      }
      var toastBtn = e.target.closest('[data-toast]');
      if (toastBtn) { toast(toastBtn.getAttribute('data-toast')); return; }
      if (e.target.closest('[data-feedback="down"]')) { openModal('feedback'); return; }
      if (e.target.closest('[data-feedback="up"]')) { toast('フィードバックありがとうございます！'); return; }
      var chip = e.target.closest('[data-prompt]');
      if (chip) {
        var input = document.getElementById('msg-input');
        if (input) { input.value = chip.getAttribute('data-prompt'); input.focus(); }
      }
    });

    var langToggle = document.getElementById('lang-toggle');
    var langMenu = document.getElementById('lang-menu');
    if (langToggle && langMenu) {
      langToggle.addEventListener('click', function (ev) {
        ev.stopPropagation();
        langMenu.classList.toggle('show');
        langToggle.setAttribute('aria-expanded', langMenu.classList.contains('show'));
      });
      langMenu.querySelectorAll('.ui-lang-option').forEach(function (btn) {
        btn.addEventListener('click', function () {
          langMenu.classList.remove('show');
          langToggle.textContent = btn.textContent.split(' ')[0] + ' ▼';
          toast('言語を切り替え（デモ）');
        });
      });
      document.addEventListener('click', function () { langMenu.classList.remove('show'); });
    }

    var form = document.getElementById('chat-form');
    if (form) {
      form.addEventListener('submit', function () {
        var input = document.getElementById('msg-input');
        if (input && input.value.trim()) toast('送信しました（デモ）');
      });
    }

    var ob = document.getElementById('onboarding');
    document.getElementById('show-onboarding').addEventListener('click', function () {
      obIndex = 0; renderOnboarding(); ob.classList.add('show');
    });
    document.getElementById('ob-skip').addEventListener('click', function () { ob.classList.remove('show'); });
    document.getElementById('ob-next').addEventListener('click', function () {
      if (obIndex >= ONBOARDING.length - 1) ob.classList.remove('show');
      else { obIndex++; renderOnboarding(); }
    });

    bindCarousels(root);
    bindBodymap(root);
    bindProductGrid(root);
    bindHeroRegion(root);

    /* demo particles */
    var pc = document.getElementById('particles');
    if (pc) {
      var chars = (document.documentElement.dataset.particles || '✨ · ☀').split(/\s+/);
      for (var i = 0; i < 12; i++) {
        var p = document.createElement('span');
        p.className = 'ui-particle';
        p.textContent = chars[i % chars.length];
        p.style.left = Math.random() * 100 + '%';
        p.style.animationDuration = 6 + Math.random() * 8 + 's';
        p.style.animationDelay = Math.random() * 5 + 's';
        pc.appendChild(p);
      }
    }
  }

  window.UIShell = {
    mount: function (targetId, options) {
      var root = document.getElementById(targetId);
      if (!root) return;
      var opts = options || {};
      root.innerHTML = shellHtml(opts);
      bindEvents(root);
      if (opts.autoOnboarding) {
        obIndex = 0;
        renderOnboarding();
        document.getElementById('onboarding').classList.add('show');
      }
    }
  };
})();
