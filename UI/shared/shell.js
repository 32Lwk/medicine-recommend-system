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
      scores: { symptom: 94, efficacy: 88, age: 100, usage: 85, sideEffect: 92, interaction: 96 },
      completenessPenalty: 0.15,
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
      scores: { symptom: 88, efficacy: 82, age: 100, usage: 80, sideEffect: 88, interaction: 95 },
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
      scores: { symptom: 85, efficacy: 78, age: 100, usage: 90, sideEffect: 85, interaction: 90 },
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
      var iconHtml = variant === 'playful'
      ? ''
      : '<span class="ui-med-image__icon" aria-hidden="true">' + medFormIcon(m.form) + '</span>';

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

  function scoreTier(pct) {
    if (pct >= 80) return 'high';
    if (pct >= 60) return 'medium';
    return 'low';
  }

  function scoreRingHtml(score) {
    var pct = Math.max(0, Math.min(100, score));
    var tier = scoreTier(pct);
    return (
      '<button type="button" class="ui-score-ring ui-score-ring--' + tier + '" data-score-ring style="--ui-score:' + pct + '" aria-expanded="false" aria-label="おすすめ度 ' + pct + 'パーセント。タップで内訳を表示">' +
        '<span class="ui-score-ring__track" aria-hidden="true"></span>' +
        '<span class="ui-score-ring__fill" aria-hidden="true"></span>' +
        '<span class="ui-score-ring__inner">' +
          '<span class="ui-score-ring__value">' + pct + '</span>' +
          '<span class="ui-score-ring__unit">%</span>' +
        '</span>' +
      '</button>'
    );
  }

  function scorePenaltyChipHtml(m) {
    var penalty = Number(m.completenessPenalty) || 0;
    if (penalty <= 0) return '';
    var pct = Math.round(penalty * 1000) / 10;
    var pctLabel = pct % 1 === 0 ? String(Math.round(pct)) : String(pct);
    var title = '年齢などの情報が未入力のため、おすすめ度が最大' + pctLabel + '%低下しています。入力するとより正確な判定が可能です。';
    return '<p class="ui-score-penalty-chip" title="' + esc(title) + '" aria-label="' + esc(title) + '">未入力 −' + pctLabel + '%</p>';
  }

  function scoreClusterHtml(m) {
    return '<div class="ui-score-cluster">' + scoreRingHtml(m.score) + scorePenaltyChipHtml(m) + '</div>';
  }

  function scoreBreakdownPanelHtml(m) {
    var s = m.scores;
    var rows = [
      ['症状適合度', s.symptom],
      ['効能特異性', s.efficacy],
      ['年齢適合性', s.age],
      ['用法簡便性', s.usage],
      ['副作用リスク', s.sideEffect],
      ['相互作用リスク', s.interaction]
    ];
    var items = rows.filter(function (row) { return row[1] != null && row[1] !== ''; }).map(function (row) {
      var mod = row[0].indexOf('リスク') >= 0 ? ' ui-score-breakdown__item--risk' : '';
      return '<li class="ui-score-breakdown__item' + mod + '"><span class="ui-score-breakdown__label">' + row[0] + '</span><strong>' + row[1] + '%</strong></li>';
    }).join('');
    return (
      '<div class="ui-score-breakdown-panel" data-score-panel hidden>' +
        '<p class="ui-score-breakdown-panel__title">スコア内訳（参考）</p>' +
        '<ul class="ui-score-breakdown__list" aria-label="スコア内訳">' + items + '</ul>' +
        '<p class="ui-score-breakdown__note">ルールベースの評価です。最終判断は薬剤師・登録販売者にご相談ください。</p>' +
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

    return (
      '<div class="ui-med-image ui-med-image--placeholder ' + variantClass + extraClass + '" data-no-image="true" aria-label="画像なし">' +
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
            '<h3 class="ui-card-name">' + esc(m.name) + '</h3>' +
            '<p class="ui-card-maker">' + esc(m.maker) + '</p>' +
            symptomTagsHtml(m.symptoms) +
          '</div>' +
          scoreClusterHtml(m) +
        '</div>' +
        '<div class="ui-card-pro-meta">' +
          '<span class="ui-med-badge ui-med-badge--type">' + esc(m.medType) + '</span>' +
          '<span class="ui-age-suit" title="' + esc(m.ageLabel) + '">' +
            '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="7" r="3" fill="currentColor"/><path fill="currentColor" d="M6 20v-1.5c0-2.5 2.7-4 6-4s6 1.5 6 4V20H6z"/></svg>' +
            '<span>' + esc(m.ageLabel) + '</span>' +
          '</span>' +
        '</div>' +
        scoreBreakdownPanelHtml(m) +
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
    return scoreBreakdownPanelHtml(m);
  }

  function personalizedAdviceHtml(opts) {
    opts = opts || {};
    var session = opts.headerSession || { age: '30歳', gender: '男性' };
    var symptoms = opts.headerSymptoms || ['のど痛', '発熱', '鼻水'];
    var age = session.age || '30歳';
    var gender = session.gender ? '（' + session.gender + '）' : '';
    var symptomText = symptoms.slice(0, 3).join('・');
    return (
      '<div class="ui-personal-advice" role="note" aria-label="あなたへのひとこと">' +
        '<div class="ui-personal-advice__head">' +
          '<svg class="ui-personal-advice__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true">' +
            '<path d="M12 3l8 4v5c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V7l8-4z"/>' +
          '</svg>' +
          '<h4 class="ui-personal-advice__title">あなたへのひとこと</h4>' +
        '</div>' +
        '<p class="ui-personal-advice__text">' +
          esc(age) + esc(gender) + 'の方で、主な症状は「' + esc(symptomText) + '」です。' +
          '総合感冒薬のなかから症状のバランスと年齢適合を考慮して候補を選びました。' +
          '服用中のお薬やアレルギーがある場合は、購入前に薬剤師にご相談ください。' +
        '</p>' +
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
        personalizedAdviceHtml(opts) +
        inner +
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

  function greetingExamplesHtml(opts) {
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
    return '<p class="ui-greeting-examples">例：「頭痛がする」「喉が痛い」「熱がある」など</p>';
  }

  function symptomChipsHtml(opts) {
    return greetingExamplesHtml(opts);
  }

  function messagesHtml(recoLayout, recoOpts) {
    recoOpts = recoOpts || {};
    return (
      '<div class="ui-msg ui-msg--bot">' +
        '<div class="ui-bubble ui-bubble--chat ui-bubble--greeting">' +
          'こんにちは！どのような症状でお困りでしょうか？' +
          greetingExamplesHtml(recoOpts) +
        '</div>' +
      '</div>' +
      '<div class="ui-msg ui-msg--user">' +
        '<div class="ui-bubble ui-bubble--chat">のどが痛くて熱があります。鼻水も少しあります。</div>' +
      '</div>' +
      processingBubbleHtml(recoOpts) +
      '<div class="ui-msg ui-msg--bot"' + (recoOpts.demoStreamingProcessing ? ' data-demo-reveal-after-processing hidden' : '') + '>' +
        '<div class="ui-bubble ui-bubble--reco">' + recoBlock(recoLayout, recoOpts) + '</div>' +
      '</div>' +
      '<div class="ui-msg ui-msg--bot"' + (recoOpts.demoStreamingProcessing ? ' data-demo-reveal-after-processing hidden' : '') + '>' +
        '<div class="ui-bubble ui-bubble--chat ui-bubble--manual">' +
          '<strong>👤 薬剤師からの返信</strong><br><br>' +
          '現在服用中のお薬があれば教えてください。より安全なご提案のため確認させていただきます。' +
        '</div>' +
      '</div>' +
      '<div class="ui-msg ui-msg--bot"' + (recoOpts.demoStreamingProcessing ? ' data-demo-reveal-after-processing hidden' : '') + '>' +
        '<div class="ui-bubble ui-bubble--chat">' +
          '<strong>❓ 追加でお伺いしたいこと</strong>' +
          '<span class="ui-priority-badge">（優先度: 重要）</span><br>' +
          '安全のため、以下の情報を教えてください：<ul class="ui-followup-list">' +
          '<li>アレルギーはありますか？</li><li>現在の体温は何度ですか？</li></ul>' +
          '<p class="ui-followup-hint">💡 上記の質問への回答や、その他伝えたいことがあれば、下の入力欄からお送りください。</p>' +
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
            '<div class="ui-form-group"><label>その他</label><textarea rows="2" placeholder="眠気が心配 等"></textarea></div>' +
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

  function toolbarGlyphHtml(iconId, useLineIcons) {
    if (!useLineIcons) {
      var emoji = { user: '👤', trash: '🗑️', refresh: '🔄', pharmacist: '👨‍⚕️', info: 'ℹ️' };
      return '<span class="ui-toolbar-btn__glyph" aria-hidden="true">' + (emoji[iconId] || '') + '</span>';
    }
    var svgs = {
      user: '<svg class="ui-toolbar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="3.5"/><path d="M5 20v-1a7 7 0 0 1 14 0v1"/></svg>',
      trash: '<svg class="ui-toolbar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/><path d="M7 7l1 12a1 1 0 0 0 1 .9h6a1 1 0 0 0 1-.9L17 7"/></svg>',
      refresh: '<svg class="ui-toolbar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M20 11a8 8 0 1 0-2.2 5.5"/><path d="M20 4v7h-7"/></svg>',
      pharmacist: '<svg class="ui-toolbar-icon ui-toolbar-icon--filled" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="7" r="3.75" fill="currentColor"/><path fill="currentColor" d="M5 20v-1.75c0-3.6 3.1-5.75 7-5.75s7 2.15 7 5.75V20H5z"/></svg>',
      info: '<svg class="ui-toolbar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><circle cx="12" cy="8" r="0.5" fill="currentColor"/></svg>'
    };
    return '<span class="ui-toolbar-btn__glyph ui-toolbar-btn__glyph--svg" aria-hidden="true">' + (svgs[iconId] || '') + '</span>';
  }

  function hasSafetyRailStrip(opts) {
    opts = opts || {};
    if (opts.hideToolbarUserBtn) return true;
    if (opts.layout === 'safety') return true;
    return !!(opts.hybridStrips && opts.hybridStrips.indexOf('safety') >= 0);
  }

  function safetyPersonIconSvg() {
    return (
      '<svg class="ui-safety-rail__icon-svg ui-safety-rail__icon-svg--person" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<circle cx="12" cy="8" r="3.5"/>' +
        '<path d="M5 20v-1a7 7 0 0 1 14 0v1"/>' +
      '</svg>'
    );
  }

  var PROCESSING_DEMO_STEPS = [
    { label: '入力を確認しています', step: 1, total: 8, percent: 10 },
    { label: '症状の種類を分析しています', step: 2, total: 8, percent: 22 },
    { label: 'お客様情報を確認しています', step: 3, total: 8, percent: 35 },
    { label: '症状の内容を読み取り、該当する市販薬の種類を判定しています', step: 4, total: 8, percent: 52 },
    { label: 'お薬を選定しています', step: 5, total: 8, percent: 68 },
    { label: '安全性を確認しています', step: 6, total: 8, percent: 82 },
    { label: '使用上の注意を作成しています', step: 7, total: 8, percent: 92 },
    { label: '回答を仕上げています', step: 8, total: 8, percent: 98 }
  ];

  function renderProcessingStatusFallback(host, state) {
    var wrapper = host.querySelector('.processing-status-wrapper');
    if (!wrapper) return;
    var card = wrapper.querySelector('.processing-status-card');
    if (!card) {
      wrapper.innerHTML =
        '<div class="processing-status-card">' +
          '<div class="processing-status-header">' +
            '<span class="processing-status-badge">AI分析中</span>' +
            '<span class="processing-status-step-pill"></span>' +
          '</div>' +
          '<p class="processing-status-label"></p>' +
          '<div class="processing-status-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-label="処理の進捗">' +
            '<div class="processing-status-bar-fill"></div>' +
          '</div>' +
        '</div>';
      card = wrapper.querySelector('.processing-status-card');
    }
    var pill = card.querySelector('.processing-status-step-pill');
    var label = card.querySelector('.processing-status-label');
    var track = card.querySelector('.processing-status-track');
    var fill = card.querySelector('.processing-status-bar-fill');
    if (pill) pill.textContent = state.step + ' / ' + state.total;
    if (label) label.textContent = state.label;
    if (track) {
      track.setAttribute('aria-valuenow', String(state.percent));
    }
    if (fill) fill.style.width = state.percent + '%';
  }

  function updateProcessingHost(host, state) {
    if (!host || !state) return;
    if (window.ProcessingStatus && ProcessingStatus.renderProcessingStatus) {
      ProcessingStatus.renderProcessingStatus(host, {
        active: true,
        label: state.label,
        step: state.step,
        total: state.total,
        percent: state.percent,
        badge: 'AI分析中',
        progressAria: '処理の進捗'
      });
      return;
    }
    renderProcessingStatusFallback(host, state);
  }

  function processingBubbleHtml() {
    return (
      '<div class="ui-msg ui-msg--bot" data-processing-msg>' +
        '<div class="ui-bubble ui-bubble--chat ui-bubble--processing-host">' +
          '<div class="processing-status-bubble" data-processing-host>' +
            '<div class="processing-status-wrapper"></div>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  }

  function initProcessingStreamDemo(root, opts) {
    var host = root.querySelector('[data-processing-host]');
    if (!host) return;

    var steps = PROCESSING_DEMO_STEPS;
    var streamDemo = !!(opts && opts.demoStreamingProcessing);
    var afterNodes = root.querySelectorAll('[data-demo-reveal-after-processing]');

    if (streamDemo) {
      afterNodes.forEach(function (node) { node.hidden = true; });
    }

    var idx = streamDemo ? 0 : 3;
    updateProcessingHost(host, steps[idx]);

    if (!streamDemo) return;

    function tick() {
      idx += 1;
      if (idx >= steps.length) {
        setTimeout(function () {
          var procMsg = root.querySelector('[data-processing-msg]');
          if (procMsg) procMsg.remove();
          afterNodes.forEach(function (node) {
            node.hidden = false;
            node.classList.add('ui-msg--reveal');
          });
        }, 500);
        return;
      }
      updateProcessingHost(host, steps[idx]);
      setTimeout(tick, 850);
    }

    setTimeout(tick, 850);
  }

  function safetyChipHtml(chip) {
    var cls = 'ui-safety-chip';
    if (chip.type === 'ok') cls += ' ui-safety-chip--ok';
    else if (chip.type === 'warn') cls += ' ui-safety-chip--warn';
    else if (chip.type === 'pending') cls += ' ui-safety-chip--pending';
    else if (chip.type === 'info') cls += ' ui-safety-chip--info';
    return '<em class="' + cls + '">' + esc(chip.label) + '</em>';
  }

  function buildSafetyRailContext(opts) {
    opts = opts || {};
    var session = opts.headerSession || {};
    var profile = opts.safetyProfile || {};
    var age = profile.age || session.age;
    var gender = profile.gender || session.gender;
    var chips = [];
    var pendingCount = 0;

    if (age) {
      var identity = age + (gender ? '·' + gender : '');
      chips.push({ type: 'ok', label: identity });
    } else {
      chips.push({ type: 'pending', label: '年齢未登録' });
      pendingCount += 1;
    }

    var allergies = profile.allergies;
    if (allergies === 'none' || allergies === 'なし') {
      chips.push({ type: 'ok', label: 'アレルギーなし' });
    } else if (allergies) {
      chips.push({ type: 'warn', label: 'アレルギー: ' + allergies });
    } else {
      chips.push({ type: 'pending', label: 'アレルギー未登録' });
      pendingCount += 1;
    }

    var medications = profile.medications;
    if (medications === 'none' || medications === 'なし') {
      chips.push({ type: 'ok', label: '服用薬なし' });
    } else if (medications) {
      chips.push({ type: 'info', label: '服用中: ' + medications });
    } else {
      chips.push({ type: 'pending', label: '服用薬未登録' });
      pendingCount += 1;
    }

    var showPregnancy = profile.showPregnancy || gender === '女性';
    if (showPregnancy) {
      if (profile.pregnant === true) {
        chips.push({ type: 'warn', label: '妊娠中' });
      } else if (profile.pregnant === false && profile.breastfeeding !== true) {
        chips.push({ type: 'ok', label: '妊娠·授乳なし' });
      } else if (profile.breastfeeding === true) {
        chips.push({ type: 'warn', label: '授乳中' });
      } else {
        chips.push({ type: 'pending', label: '妊娠·授乳 未確認' });
        pendingCount += 1;
      }
    }

    var recoFlags = profile.recoFlags || [];
    recoFlags.forEach(function (flag) {
      chips.push({ type: 'warn', label: flag });
    });

    var ctaLabel = pendingCount > 0 ? '情報を追加' : '編集';
    var statusHtml = '';
    if (pendingCount > 0) {
      statusHtml =
        '<span class="ui-safety-rail__status ui-safety-rail__status--pending">' +
          pendingCount + '件未登録' +
        '</span>';
    } else if (recoFlags.length > 0) {
      statusHtml = '<span class="ui-safety-rail__status ui-safety-rail__status--warn">要確認</span>';
    } else {
      statusHtml = '<span class="ui-safety-rail__status ui-safety-rail__status--ok">登録済み</span>';
    }

    return {
      chips: chips,
      pendingCount: pendingCount,
      ctaLabel: ctaLabel,
      statusHtml: statusHtml,
      hint: pendingCount > 0
        ? '未登録の項目があると、より安全な提案がしづらくなります。'
        : '登録情報は推奨の安全性チェックに利用されます。'
    };
  }

  function safetyRailHtml(compact, opts) {
    opts = opts || {};
    var ctx = buildSafetyRailContext(opts);
    var compactClass = compact ? ' ui-safety-rail--compact' : '';
    var chipsHtml = ctx.chips.map(safetyChipHtml).join('');
    var title = compact ? 'あなたの情報' : 'あなたの情報（安全チェック）';
    var ctaLabel = ctx.ctaLabel;
    return (
      '<div class="ui-safety-rail' + compactClass + '" role="region" aria-label="ユーザー登録情報と安全チェック">' +
        '<div class="ui-safety-rail__icon" aria-hidden="true">' +
          (compact ? safetyPersonIconSvg() : '🛡️') +
        '</div>' +
        '<div class="ui-safety-rail__body">' +
          '<div class="ui-safety-rail__head">' +
            '<strong>' + esc(title) + '</strong>' +
            ctx.statusHtml +
          '</div>' +
          (compact
            ? ''
            : '<p class="ui-safety-rail__hint">' + esc(ctx.hint) + '</p>') +
          '<span class="ui-safety-rail__items app-scrollbar">' + chipsHtml + '</span>' +
        '</div>' +
        '<button type="button" class="ui-safety-rail__cta" data-modal="userinfo">' + esc(ctaLabel) + '</button>' +
      '</div>'
    );
  }

  function wizardStripHtml(activeStep) {
    var steps = [
      { n: 1, label: '症状' },
      { n: 2, label: '属性' },
      { n: 3, label: '推奨' },
      { n: 4, label: '確認' }
    ];
    var step = activeStep || 3;
    return (
      '<nav class="ui-wizard-strip" aria-label="相談の進捗">' +
        '<ol class="ui-wizard-steps">' +
          steps.map(function (s) {
            var cls = 'ui-wizard-step';
            if (s.n < step) cls += ' ui-wizard-step--done';
            if (s.n === step) cls += ' ui-wizard-step--active';
            return (
              '<li class="' + cls + '" data-wizard-step="' + s.n + '">' +
                '<span class="ui-wizard-step__num" aria-hidden="true">' + (s.n < step ? '✓' : s.n) + '</span>' +
                '<span class="ui-wizard-step__label">' + esc(s.label) + '</span>' +
              '</li>'
            );
          }).join('') +
        '</ol>' +
        '<p class="ui-wizard-hint">ステップ ' + step + '/4 — 推奨結果を確認してください</p>' +
      '</nav>'
    );
  }

  function familyStripHtml() {
    return (
      '<div class="ui-family-strip" role="tablist" aria-label="相談対象の切替">' +
        '<span class="ui-family-strip__label">相談対象</span>' +
        ['本人', '父', '母', '子ども'].map(function (name, i) {
          return (
            '<button type="button" class="ui-family-tab' + (i === 0 ? ' is-active' : '') + '" role="tab" data-family-tab="' + i + '" aria-selected="' + (i === 0 ? 'true' : 'false') + '">' +
              '<span class="ui-family-tab__avatar" aria-hidden="true">' + ['👤', '👴', '👵', '👧'][i] + '</span>' +
              '<span>' + esc(name) + '</span>' +
              (i === 0 ? '<span class="ui-family-tab__meta">30歳</span>' : '') +
            '</button>'
          );
        }).join('') +
        '<button type="button" class="ui-family-add" data-modal="userinfo" title="家族を追加">＋</button>' +
      '</div>'
    );
  }

  function triageStripHtml() {
    return (
      '<div class="ui-triage-strip" role="group" aria-label="つらさの程度">' +
        '<p class="ui-triage-strip__lead">今のつらさはどのくらいですか？</p>' +
        '<div class="ui-triage-options">' +
          '<button type="button" class="ui-triage-btn" data-triage="mild">軽い</button>' +
          '<button type="button" class="ui-triage-btn is-active" data-triage="moderate">普通</button>' +
          '<button type="button" class="ui-triage-btn" data-triage="severe">つらい</button>' +
          '<button type="button" class="ui-triage-btn ui-triage-btn--urgent" data-triage="urgent">今すぐ受診</button>' +
        '</div>' +
      '</div>'
    );
  }

  function checklistStripHtml() {
    return (
      '<div class="ui-checklist-strip" role="region" aria-label="推奨前の確認事項">' +
        '<h2 class="ui-checklist-strip__title">推奨の前に確認させてください</h2>' +
        '<ul class="ui-checklist">' +
          '<li class="ui-checklist-item ui-checklist-item--done"><span>年齢・性別</span><button type="button" class="ui-checklist-edit" data-modal="userinfo">編集</button></li>' +
          '<li class="ui-checklist-item ui-checklist-item--done"><span>アレルギー</span><span class="ui-checklist-val">なし</span></li>' +
          '<li class="ui-checklist-item ui-checklist-item--pending"><span>服用中のお薬</span><button type="button" class="ui-checklist-edit" data-modal="attribute">入力する</button></li>' +
          '<li class="ui-checklist-item ui-checklist-item--pending"><span>妊娠・授乳</span><button type="button" class="ui-checklist-edit" data-modal="attribute">入力する</button></li>' +
        '</ul>' +
        '<p class="ui-checklist-note">未入力の項目があると、より安全な提案のため追加質問が表示されます。</p>' +
      '</div>'
    );
  }

  function explainPanelHtml() {
    return (
      '<aside class="ui-split-pane ui-split-pane--left ui-explain-pane app-scrollbar" aria-label="推奨の根拠">' +
        '<div class="ui-explain-panel">' +
          '<h2 class="ui-explain-title">なぜこの薬？</h2>' +
          '<p class="ui-explain-sub">ルールベースの判断過程（デモ）</p>' +
          '<ol class="ui-explain-chain">' +
            '<li class="ui-explain-step ui-explain-step--done"><span class="ui-explain-step__n">1</span><div><strong>症状抽出</strong><p>のど痛・発熱・鼻水を検出</p></div></li>' +
            '<li class="ui-explain-step ui-explain-step--done"><span class="ui-explain-step__n">2</span><div><strong>候補絞込</strong><p>総合感冒薬 847件 → 312件</p></div></li>' +
            '<li class="ui-explain-step ui-explain-step--done"><span class="ui-explain-step__n">3</span><div><strong>スコアリング</strong><p>症状適合 94% · 年齢適合 100%</p></div></li>' +
            '<li class="ui-explain-step ui-explain-step--active"><span class="ui-explain-step__n">4</span><div><strong>第1候補</strong><p>ルルアタックTR — 成分バランスが最適</p></div></li>' +
          '</ol>' +
          '<div class="ui-explain-disclaimer">AIは順位を決めません。最終判断は登録販売者・薬剤師にご相談ください。</div>' +
        '</div>' +
      '</aside>'
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
    recoOpts = recoOpts || {};
    var orbHtml = layout === 'orb'
      ? '<div class="ui-orb" aria-hidden="true"><span class="ui-orb-core"></span><span class="ui-orb-ring"></span></div>'
      : '';
    var recoveryVoice = layout === 'recovery'
      ? '<div class="ui-recovery-voice" role="region" aria-label="音声入力">' +
          '<button type="button" class="ui-recovery-voice__btn" data-toast="音声で症状を話す（デモ）" aria-label="音声で症状を入力">' +
            '<span class="ui-recovery-voice__pulse" aria-hidden="true"></span>' +
            '<span class="ui-recovery-voice__icon" aria-hidden="true">🎤</span>' +
            '<span class="ui-recovery-voice__label">声で伝える</span>' +
          '</button>' +
          '<p class="ui-recovery-voice__hint">文字を打つのがつらいときは、タップして話してください</p>' +
        '</div>'
      : '';
    return (
      '<div class="ui-split-pane ui-split-pane--right">' +
        '<div class="ui-messages app-scrollbar" id="messages">' +
          '<div class="ui-particles" aria-hidden="true" id="particles"></div>' +
          messagesHtml(recoLayout, recoOpts) +
        '</div>' +
        recoveryVoice +
        '<div class="ui-input-bar ui-input-bar--compact">' +
          '<form class="ui-input-row" id="chat-form" onsubmit="return false">' +
            '<button type="button" class="ui-mic" title="音声入力" data-toast="音声入力（デモ）">🎤</button>' +
            '<div class="ui-textarea-wrap"><textarea class="ui-textarea app-scrollbar" rows="1" placeholder="症状を入力してください..." id="msg-input"></textarea></div>' +
            '<button type="submit" class="ui-send" title="送信">➤</button>' +
          '</form>' +
        '</div>' +
        (layout === 'compact' || layout === 'orb' || layout === 'wearable' || layout === 'wechat' || layout === 'whatsapp'
          ? '<nav class="ui-bottom-nav' + (layout === 'wechat' ? ' ui-bottom-nav--wechat' : '') + '" aria-label="クイック操作">' +
              '<button type="button" class="ui-nav-btn" data-modal="userinfo"><span>👤</span><span>情報</span></button>' +
              '<button type="button" class="ui-nav-btn" data-toast="会話をリセットしました（デモ）"><span>🔄</span><span>リセット</span></button>' +
              '<button type="button" class="ui-nav-btn" data-modal="info"><span>ℹ️</span><span>ヘルプ</span></button>' +
              '<button type="button" class="ui-nav-btn" data-toast="薬剤師要請"><span>👨‍⚕️</span><span>要請</span></button>' +
            '</nav>'
          : '') +
        orbHtml +
      '</div>'
    );
  }

  function langBlockHtml() {
    return (
      '<div class="ui-lang">' +
        '<button type="button" class="ui-lang-btn" id="lang-toggle" aria-expanded="false">🇯🇵 ▼</button>' +
        '<div class="ui-lang-dropdown" id="lang-menu">' +
          ['🇯🇵 日本語', '🇺🇸 English', '🇰🇷 한국어', '🇨🇳 中文'].map(function (l, i) {
            return '<button type="button" class="ui-lang-option' + (i === 0 ? ' active' : '') + '">' + l + '</button>';
          }).join('') +
        '</div>' +
      '</div>'
    );
  }

  function headerOverflowMenuHtml(menuIcon) {
    var icon = menuIcon || '☰';
    return (
      '<div class="ui-header-overflow">' +
        '<button type="button" class="ui-icon-btn ui-header-menu-btn" id="header-menu-toggle" aria-expanded="false" aria-label="その他の操作"><span aria-hidden="true">' + icon + '</span></button>' +
        '<div class="ui-header-menu" id="header-menu" aria-hidden="true">' +
          '<button type="button" class="ui-header-menu-item" data-modal="info">ℹ️ アプリ情報</button>' +
          '<button type="button" class="ui-header-menu-item" data-modal="userinfo">👤 ユーザー情報</button>' +
          '<button type="button" class="ui-header-menu-item" data-toast="会話をリセットしました（デモ）">🔄 会話をリセット</button>' +
          '<button type="button" class="ui-header-menu-item" data-toast="薬剤師要請（デモ）">👨‍⚕️ 薬剤師要請</button>' +
          '<button type="button" class="ui-header-menu-item" id="show-onboarding-menu">📖 ガイド</button>' +
        '</div>' +
      '</div>'
    );
  }

  function resolveHeaderStyle(opts) {
    var layout = opts.layout || 'default';
    if (opts.headerStyle) return opts.headerStyle;
    if (layout === 'whatsapp' || layout === 'wechat') return 'platform';
    if (layout === 'orb' || layout === 'wearable') return 'minimal';
    if (layout === 'compact') return 'compact';
    if (layout === 'recovery') return 'floating';
    return 'default';
  }

  function contextualTitle(opts) {
    var step = opts.wizardStep || opts.contextStep || 1;
    var titles = {
      1: { h: '症状を教えてください', p: 'のどの痛み・発熱・鼻水など' },
      2: { h: 'あなたの情報', p: '年齢やアレルギーを登録' },
      3: { h: 'おすすめの市販薬', p: '症状に合う候補を比較' },
      4: { h: '確認と次のステップ', p: '用法・受診の目安をチェック' }
    };
    return titles[step] || titles[1];
  }

  function toolbarPhaseText(opts) {
    var brand = opts.headerBrand || {};
    if (brand.phase) return brand.phase;
    var step = opts.wizardStep || opts.contextStep || 1;
    var symptoms = opts.headerSymptoms || ['のど痛', '発熱'];
    if (step === 1) return 'チャットまたは音声で入力';
    if (step === 2) return 'より安全な提案のために';
    if (step === 3) {
      return symptoms.slice(0, 2).join('・') + '向け · 候補3件';
    }
    if (step === 4) return '服用前にご確認ください';
    return contextualTitle(opts).p;
  }

  function headerHtml(opts) {
    var style = resolveHeaderStyle(opts);
    var brand = opts.headerBrand || {};
    var title = brand.title || 'チャット型医薬品相談';
    var subtitle = brand.subtitle || '症状を入力してOTC医薬品の候補を確認';

    if (style === 'toolbar') {
      var toolbarTitle = brand.title || 'チャット型医薬品相談ツール';
      var toolbarPhase = brand.phase || brand.subtitle || '症状に合う市販薬をご案内します。';
      var sessionTb = opts.headerSession || { complete: true };
      var userBadgeClass = sessionTb.complete ? ' ui-toolbar-btn__badge--ok' : ' ui-toolbar-btn__badge--warn';
      var lineIcons = opts.toolbarIcons === 'line';
      var toolbarClass = lineIcons ? ' ui-header-toolbar--line-icons' : '';
      var hideUserBtn = hasSafetyRailStrip(opts);
      var userBtnHtml = hideUserBtn
        ? ''
        : (
          '<button type="button" class="ui-toolbar-btn ui-toolbar-btn--badge" data-modal="userinfo" title="ユーザー情報" aria-label="ユーザー情報">' +
            toolbarGlyphHtml('user', lineIcons) +
            '<span class="ui-toolbar-btn__badge' + userBadgeClass + '" aria-hidden="true"></span>' +
          '</button>'
        );
      return (
        '<header class="ui-header ui-header--toolbar">' +
          langBlockHtml() +
          '<div class="ui-brand ui-brand--toolbar">' +
            '<h1>' + esc(toolbarTitle) + '</h1>' +
            '<p class="ui-header-phase">' + esc(toolbarPhase) + '</p>' +
          '</div>' +
          '<nav class="ui-header-toolbar' + toolbarClass + '" aria-label="クイック操作">' +
            userBtnHtml +
            '<button type="button" class="ui-toolbar-btn" data-toast="会話をリセットしました（デモ）" title="会話をリセット" aria-label="会話をリセット">' + toolbarGlyphHtml('refresh', lineIcons) + '</button>' +
            '<button type="button" class="ui-toolbar-btn ui-toolbar-btn--pharmacist" data-toast="薬剤師に相談（デモ）" title="薬剤師に相談" aria-label="薬剤師に相談">' + toolbarGlyphHtml('pharmacist', lineIcons) + '</button>' +
            '<button type="button" class="ui-toolbar-btn" data-modal="info" title="アプリ情報" aria-label="アプリ情報">' + toolbarGlyphHtml('info', lineIcons) + '</button>' +
          '</nav>' +
        '</header>'
      );
    }

    if (style === 'session') {
      return (
        '<header class="ui-header ui-header--session">' +
          langBlockHtml() +
          '<button type="button" class="ui-session-chip" data-modal="userinfo" aria-label="ユーザー情報を編集">' +
            '<span class="ui-session-chip__avatar" aria-hidden="true">👤</span>' +
            '<span class="ui-session-chip__body">' +
              '<strong>30歳 · 男性</strong>' +
              '<span>アレルギーなし · 服用中の薬なし</span>' +
            '</span>' +
            '<span class="ui-session-chip__edit" aria-hidden="true">✎</span>' +
          '</button>' +
          '<div class="ui-header-session-actions">' +
            '<button type="button" class="ui-icon-btn" data-toast="薬剤師要請（デモ）" aria-label="薬剤師要請">👨‍⚕️</button>' +
            '<button type="button" class="ui-icon-btn" data-modal="info" aria-label="情報">ℹ️</button>' +
          '</div>' +
        '</header>'
      );
    }

    if (style === 'overflow' || style === 'floating') {
      var floatingClass = style === 'floating' ? ' ui-header--floating' : '';
      return (
        '<header class="ui-header ui-header--overflow' + floatingClass + '">' +
          (style === 'floating'
            ? '<div class="ui-header-logo" aria-hidden="true">💊</div>'
            : langBlockHtml()) +
          '<div class="ui-brand ui-brand--compact">' +
            '<h1>' + esc(style === 'floating' ? 'OTC医薬品相談' : title) + '</h1>' +
            (style === 'floating' ? '' : '<p>' + esc(subtitle) + '</p>') +
          '</div>' +
          (style === 'floating' ? langBlockHtml() : '') +
          headerOverflowMenuHtml() +
        '</header>'
      );
    }

    if (style === 'pharmacy') {
      return (
        '<header class="ui-header ui-header--pharmacy">' +
          '<div class="ui-pharmacy-mark" aria-hidden="true"><span>薬</span></div>' +
          '<div class="ui-brand ui-brand--pharmacy">' +
            '<h1>薬局相談窓口</h1>' +
            '<p>登録販売者監修 · OTC自助療養支援</p>' +
          '</div>' +
          '<span class="ui-header-trust-pill">✓ 監修済</span>' +
          langBlockHtml() +
          '<div class="ui-info"><button type="button" class="ui-icon-btn" data-modal="info" aria-label="情報">ℹ️</button></div>' +
        '</header>'
      );
    }

    if (style === 'contextual') {
      var ctx = contextualTitle(opts);
      return (
        '<header class="ui-header ui-header--contextual">' +
          '<button type="button" class="ui-header-back" data-toast="前のステップ（デモ）" aria-label="戻る">←</button>' +
          '<div class="ui-brand ui-brand--contextual">' +
            '<h1>' + esc(ctx.h) + '</h1>' +
            '<p>' + esc(ctx.p) + '</p>' +
          '</div>' +
          langBlockHtml() +
          '<div class="ui-info"><button type="button" class="ui-icon-btn" data-modal="info" aria-label="情報">ℹ️</button></div>' +
        '</header>'
      );
    }

    if (style === 'smart') {
      var ctx = contextualTitle(opts);
      var session = opts.headerSession || { age: '30歳', gender: '男性', allergy: 'なし', complete: true };
      var sessionLabel = session.age + (session.gender ? ' · ' + session.gender : '');
      var sessionTitle = 'ユーザー情報: ' + sessionLabel + '、アレルギー' + (session.allergy || '未登録');
      return (
        '<header class="ui-header ui-header--smart">' +
          langBlockHtml() +
          '<div class="ui-brand ui-brand--smart">' +
            '<div class="ui-brand-smart-main">' +
              '<span class="ui-brand-smart-mark" aria-hidden="true">' +
                '<svg viewBox="0 0 24 24" width="20" height="20" focusable="false"><path fill="currentColor" d="M12 2a3 3 0 0 1 3 3v1h2a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2V5a3 3 0 0 1 3-3zm-1 4h2V5a1 1 0 1 0-2 0v1z"/></svg>' +
              '</span>' +
              '<div class="ui-brand-smart-text">' +
                '<h1>OTC相談</h1>' +
                '<p class="ui-header-phase" id="header-phase">' + esc(ctx.p) + '</p>' +
              '</div>' +
            '</div>' +
          '</div>' +
          '<div class="ui-header-smart-end">' +
            '<button type="button" class="ui-smart-session' + (session.complete ? ' ui-smart-session--ok' : ' ui-smart-session--warn') + '" data-modal="userinfo" title="' + esc(sessionTitle) + '" aria-label="' + esc(sessionTitle) + '">' +
              '<span class="ui-smart-session__dot" aria-hidden="true"></span>' +
              '<span class="ui-smart-session__text">' + esc(sessionLabel) + '</span>' +
            '</button>' +
            '<button type="button" class="ui-smart-pharmacist" data-toast="薬剤師に相談（デモ）" aria-label="薬剤師に相談">' +
              '<svg class="ui-smart-pharmacist__icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
                '<path fill="currentColor" d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm-6 8v-1.2c0-2.2 2.7-3.8 6-3.8s6 1.6 6 3.8V20H6z"/>' +
                '<path fill="currentColor" d="M18 8h2v2h-2v3h-2v-3h-2V8h2V6h2v2z"/>' +
              '</svg>' +
              '<span class="ui-smart-pharmacist__label">薬剤師</span>' +
            '</button>' +
            headerOverflowMenuHtml('⋯') +
          '</div>' +
        '</header>'
      );
    }

    if (style === 'minimal' || style === 'compact' || style === 'platform') {
      var platformClass = style === 'platform' ? ' ui-header--platform' : '';
      var minimalClass = style === 'minimal' ? ' ui-header--minimal' : '';
      var compactClass = style === 'compact' ? ' ui-header--compact-nav' : '';
      return (
        '<header class="ui-header' + platformClass + minimalClass + compactClass + '">' +
          langBlockHtml() +
          '<div class="ui-brand">' +
            '<h1>' + esc(title) + '</h1>' +
            (style === 'minimal' ? '' : '<p>' + esc(subtitle) + '</p>') +
          '</div>' +
          '<div class="ui-info"><button type="button" class="ui-icon-btn" data-modal="info" aria-label="情報">ℹ️</button></div>' +
        '</header>'
      );
    }

    return (
      '<header class="ui-header">' +
        langBlockHtml() +
        '<div class="ui-brand">' +
          '<h1>' + esc(title) + '</h1>' +
          '<p>' + esc(subtitle) + '</p>' +
        '</div>' +
        '<div class="ui-info"><button type="button" class="ui-icon-btn" data-modal="info" aria-label="情報">ℹ️</button></div>' +
        '<div class="ui-actions">' +
          '<button type="button" class="ui-action-btn ui-action-btn--primary" data-modal="userinfo">👤 ユーザー情報</button>' +
          '<button type="button" class="ui-action-btn ui-action-btn--ghost" data-toast="会話をリセットしました（デモ）">🔄 会話をリセット</button>' +
          '<button type="button" class="ui-action-btn ui-action-btn--warn" data-toast="薬剤師要請（デモ）">👨‍⚕️ 薬剤師要請</button>' +
          '<button type="button" class="ui-action-btn ui-action-btn--ghost" id="show-onboarding">📖 ガイド</button>' +
        '</div>' +
      '</header>'
    );
  }

  function shellHtml(opts) {
    var layout = opts.layout || 'default';
    var recoLayout = opts.recoLayout || 'carousel';
    var recoOpts = {
      carouselStyle: opts.carouselStyle || (recoLayout === 'carousel' ? 'pro' : 'playful'),
      a11yPictogram: !!opts.a11yPictogram,
      headerSession: opts.headerSession,
      headerSymptoms: opts.headerSymptoms,
      demoStreamingProcessing: !!opts.demoStreamingProcessing
    };
    var showDev = opts.showDev !== false;
    var headerStyle = resolveHeaderStyle(opts);

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
    } else if (layout === 'explain') {
      viewportHtml =
        '<div class="ui-viewport ui-viewport--split">' +
          explainPanelHtml() +
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
    if (layout === 'safety') stripHtml = safetyRailHtml(!!opts.compactSafetyRail, opts);
    if (layout === 'wizard') stripHtml = wizardStripHtml(opts.wizardStep || 3);
    if (layout === 'family') stripHtml = familyStripHtml();
    if (layout === 'triage') stripHtml = triageStripHtml();
    if (layout === 'checklist') stripHtml = checklistStripHtml();

    return (
      '<div class="ui-app" data-theme="' + esc(opts.theme || 'default') + '" data-layout="' + esc(layout) + '" data-reco="' + esc(recoLayout) + '" data-carousel-style="' + esc(recoOpts.carouselStyle) + '" data-header-style="' + esc(headerStyle) + '">' +
        (showDev ? '<span class="ui-dev-badge" role="status">UI MOCK</span>' : '') +
        headerHtml(opts) +
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

  function bindTriage(root) {
    root.querySelectorAll('[data-triage]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        root.querySelectorAll('[data-triage]').forEach(function (b) { b.classList.remove('is-active'); });
        btn.classList.add('is-active');
        if (btn.getAttribute('data-triage') === 'urgent') {
          toast('受診をおすすめします。緊急の場合は119番へ');
        } else {
          toast('重症度を記録しました（デモ）');
        }
      });
    });
  }

  function bindFamilyTabs(root) {
    root.querySelectorAll('[data-family-tab]').forEach(function (tab) {
      tab.addEventListener('click', function () {
        root.querySelectorAll('[data-family-tab]').forEach(function (t) {
          t.classList.remove('is-active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('is-active');
        tab.setAttribute('aria-selected', 'true');
        toast('相談対象を切り替えました（デモ）');
      });
    });
  }

  function bindWizardSteps(root) {
    root.querySelectorAll('[data-wizard-step]').forEach(function (step) {
      step.addEventListener('click', function () {
        toast('ステップ ' + step.getAttribute('data-wizard-step') + '（デモ）');
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

  function bindHeaderMenu(root) {
    var toggle = document.getElementById('header-menu-toggle');
    var menu = document.getElementById('header-menu');
    if (!toggle || !menu) return;
    toggle.addEventListener('click', function (ev) {
      ev.stopPropagation();
      var open = menu.classList.toggle('show');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      menu.setAttribute('aria-hidden', open ? 'false' : 'true');
    });
    document.addEventListener('click', function () {
      menu.classList.remove('show');
      toggle.setAttribute('aria-expanded', 'false');
      menu.setAttribute('aria-hidden', 'true');
    });
    var obMenu = document.getElementById('show-onboarding-menu');
    if (obMenu) {
      obMenu.addEventListener('click', function () {
        menu.classList.remove('show');
        obIndex = 0;
        renderOnboarding();
        document.getElementById('onboarding').classList.add('show');
      });
    }
  }

  function bindEvents(root) {
    root.addEventListener('click', function (e) {
      var scoreRing = e.target.closest('[data-score-ring]');
      if (scoreRing) {
        var card = scoreRing.closest('.ui-card--pro');
        var panel = card && card.querySelector('[data-score-panel]');
        if (panel) {
          var willOpen = panel.hasAttribute('hidden');
          root.querySelectorAll('[data-score-panel]').forEach(function (p) {
            p.hidden = true;
            var ring = p.closest('.ui-card--pro');
            if (ring) {
              var btn = ring.querySelector('[data-score-ring]');
              if (btn) {
                btn.setAttribute('aria-expanded', 'false');
                btn.classList.remove('is-active');
              }
            }
          });
          if (willOpen) {
            panel.hidden = false;
            scoreRing.setAttribute('aria-expanded', 'true');
            scoreRing.classList.add('is-active');
          }
        }
        return;
      }
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
    var showOb = document.getElementById('show-onboarding');
    if (showOb && ob) {
      showOb.addEventListener('click', function () {
        obIndex = 0; renderOnboarding(); ob.classList.add('show');
      });
    }
    document.getElementById('ob-skip').addEventListener('click', function () { ob.classList.remove('show'); });
    document.getElementById('ob-next').addEventListener('click', function () {
      if (obIndex >= ONBOARDING.length - 1) ob.classList.remove('show');
      else { obIndex++; renderOnboarding(); }
    });

    bindCarousels(root);
    bindBodymap(root);
    bindProductGrid(root);
    bindHeroRegion(root);
    bindTriage(root);
    bindFamilyTabs(root);
    bindWizardSteps(root);
    bindHeaderMenu(root);

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

  function injectHybridStrips(root, stripIds, mountOpts) {
    mountOpts = mountOpts || {};
    var app = root.querySelector('.ui-app');
    if (!app || !stripIds || !stripIds.length) return;
    var html = stripIds.filter(function (id) {
      return id !== 'wizard';
    }).map(function (id) {
      if (id === 'safety') return safetyRailHtml(!!mountOpts.compactSafetyRail, mountOpts);
      if (id === 'pharmacist') return pharmacistStripHtml();
      if (id === 'triage') return triageStripHtml();
      if (id === 'checklist') return checklistStripHtml();
      return '';
    }).join('');
    if (!html && stripIds.indexOf('wizard') < 0) return;
    var hybrid = document.createElement('div');
    hybrid.className = 'ui-hybrid-strips';
    hybrid.innerHTML = html;
    var wizard = app.querySelector('.ui-wizard-strip');
    var header = app.querySelector('.ui-header');
    if (!header) return;
    if (wizard) hybrid.appendChild(wizard);
    header.insertAdjacentElement('afterend', hybrid);
  }

  window.UIShell = {
    mount: function (targetId, options) {
      var root = document.getElementById(targetId);
      if (!root) return;
      var opts = options || {};
      root.innerHTML = shellHtml(opts);
      bindEvents(root);
      if (opts.hybridStrips && opts.hybridStrips.length) {
        injectHybridStrips(root, opts.hybridStrips, opts);
      }
      initProcessingStreamDemo(root, opts);
      if (opts.autoOnboarding) {
        obIndex = 0;
        renderOnboarding();
        document.getElementById('onboarding').classList.add('show');
      }
    }
  };
})();
