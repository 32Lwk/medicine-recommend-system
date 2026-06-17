/**
 * Professional medicine carousel cards (Sage Terrace pro style).
 */
(function (global) {
  'use strict';

  var esc = global.MedicineMapper ? global.MedicineMapper.esc : function (s) { return String(s); };
  var t = function (k, v) {
    return global.UiStrings ? global.UiStrings.t(k, v) : k;
  };

  function medicineImageHtml(m, variant) {
    variant = variant || 'pro';
    var variantClass = variant === 'pro' || variant === 'card' ? 'ui-med-image--card' : 'ui-med-image--' + variant;
    var url = m.imageUrl;
    if (url) {
      return (
        '<div class="ui-med-image ' + variantClass + '">' +
          '<img src="' + esc(url) + '" alt="' + esc(m.name) + '" loading="lazy" decoding="async">' +
        '</div>'
      );
    }
    return (
      '<div class="ui-med-image ui-med-image--placeholder ' + variantClass + '" data-no-image="true" aria-label="' + esc(t('noImage')) + '">' +
        '<span class="ui-med-image__label">' + esc(t('noImage')) + '</span>' +
      '</div>'
    );
  }

  function scoreRingHtml(score) {
    var pct = Math.max(0, Math.min(100, Math.round(Number(score) || 0)));
    return (
      '<button type="button" class="ui-score-ring" data-score-ring style="--ui-score:' + pct + '" aria-expanded="false" aria-label="' +
        esc(t('scoreLabel')) + ' ' + pct + '%">' +
        '<span class="ui-score-ring__track" aria-hidden="true"></span>' +
        '<span class="ui-score-ring__fill" aria-hidden="true"></span>' +
        '<span class="ui-score-ring__inner">' +
          '<span class="ui-score-ring__value">' + pct + '</span>' +
          '<span class="ui-score-ring__unit">%</span>' +
        '</span>' +
      '</button>'
    );
  }

  function scoreBreakdownPanelHtml(m) {
    var s = m.scores || {};
    if (!s.symptom && !s.efficacy && !s.age && !s.usage) return '';
    return (
      '<div class="ui-score-breakdown-panel score-breakdown" data-score-panel hidden>' +
        '<p class="ui-score-breakdown-panel__title">' + esc(t('scoreBreakdownTitle')) + '</p>' +
        '<ul class="ui-score-breakdown__list" aria-label="' + esc(t('scoreBreakdownTitle')) + '">' +
          '<li><span class="ui-score-breakdown__label">' + esc(t('scoreSymptom')) + '</span><strong>' + Math.round(s.symptom || 0) + '%</strong></li>' +
          '<li><span class="ui-score-breakdown__label">' + esc(t('scoreEfficacy')) + '</span><strong>' + Math.round(s.efficacy || 0) + '%</strong></li>' +
          '<li><span class="ui-score-breakdown__label">' + esc(t('scoreAge')) + '</span><strong>' + Math.round(s.age || 0) + '%</strong></li>' +
          '<li><span class="ui-score-breakdown__label">' + esc(t('scoreUsage')) + '</span><strong>' + Math.round(s.usage || 0) + '%</strong></li>' +
        '</ul>' +
        '<p class="ui-score-breakdown__note">' + esc(t('scoreNote')) + '</p>' +
      '</div>'
    );
  }

  function symptomTagsHtml(symptoms) {
    if (!symptoms || !symptoms.length) return '';
    return (
      '<div class="ui-symptom-tags" aria-label="symptoms">' +
        symptoms.map(function (s) {
          return '<span class="ui-symptom-tag">' + esc(s) + '</span>';
        }).join('') +
      '</div>'
    );
  }

  function cardHtmlPro(m) {
    return (
      '<article class="ui-card ui-card--pro medicine-item" role="listitem" aria-label="' + esc(m.name) + '" data-rank="' + esc(m.rank) + '">' +
        medicineImageHtml(m, 'pro') +
        '<header class="ui-card-pro-head">' +
          '<span class="ui-med-badge ui-med-badge--rank">' + esc(t('rankBadge', { n: m.rank })) + '</span>' +
          '<span class="ui-med-badge ui-med-badge--otc">' + esc(t('otc')) + '</span>' +
        '</header>' +
        '<div class="ui-card-pro-main">' +
          '<div class="ui-card-pro-info">' +
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
        scoreBreakdownPanelHtml(m) +
        (m.riskWarning ? '<p class="ui-card-warn">' + esc(m.riskWarning) + '</p>' : '') +
        (m.lowScoreWarning ? '<p class="ui-card-warn ui-card-warn--low">' + esc(t('lowScoreWarning')) + '</p>' : '') +
        '<div class="ui-card-pro-detail is-collapsed">' +
          '<div class="ui-card-section">' +
            '<div class="ui-card-label">' + esc(t('efficacy')) + '</div>' +
            '<div class="ui-card-text ui-clamp-2">' + esc(m.efficacy) + '</div>' +
          '</div>' +
          '<div class="ui-card-section">' +
            '<div class="ui-card-label">' + esc(t('reason')) + '</div>' +
            '<div class="ui-card-text ui-clamp-2">' + esc(m.reason) + '</div>' +
          '</div>' +
          '<button type="button" class="ui-card-expand collapse-toggle" data-expand aria-expanded="false">' + esc(t('expand')) + '</button>' +
        '</div>' +
        '<p class="ui-trust-strip">' + esc(t('trustStrip')) + '</p>' +
      '</article>'
    );
  }

  function bindCardInteractions(root) {
    root = root || document;
    root.querySelectorAll('[data-score-ring]').forEach(function (btn) {
      if (btn._scoreBound) return;
      btn._scoreBound = true;
      btn.addEventListener('click', function () {
        var panel = btn.closest('.ui-card') && btn.closest('.ui-card').querySelector('[data-score-panel]');
        if (!panel) return;
        var hidden = panel.hasAttribute('hidden');
        if (hidden) panel.removeAttribute('hidden');
        else panel.setAttribute('hidden', '');
        btn.setAttribute('aria-expanded', hidden ? 'true' : 'false');
      });
    });
    root.querySelectorAll('[data-expand]').forEach(function (btn) {
      if (btn._expandBound) return;
      btn._expandBound = true;
      btn.addEventListener('click', function () {
        var detail = btn.closest('.ui-card-pro-detail');
        if (!detail) return;
        var collapsed = detail.classList.toggle('is-collapsed');
        btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        btn.textContent = collapsed ? t('expand') : t('collapse');
      });
    });
  }

  global.MedicineCard = {
    cardHtmlPro: cardHtmlPro,
    bindCardInteractions: bindCardInteractions
  };
})(typeof window !== 'undefined' ? window : globalThis);
