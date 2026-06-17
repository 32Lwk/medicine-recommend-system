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

  function scoreTier(pct) {
    if (pct >= 80) return 'high';
    if (pct >= 60) return 'medium';
    return 'low';
  }

  function scoreRingHtml(score) {
    var pct = Math.max(0, Math.min(100, Math.round(Number(score) || 0)));
    var tier = scoreTier(pct);
    return (
      '<button type="button" class="ui-score-ring ui-score-ring--' + tier + '" data-score-ring style="--ui-score:' + pct + '" aria-expanded="false" aria-label="' +
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

  function scorePenaltyChipHtml(m) {
    var penalty = Number(m.completenessPenalty) || 0;
    if (penalty <= 0) return '';
    var pct = Math.round(penalty * 1000) / 10;
    var pctLabel = pct % 1 === 0 ? String(Math.round(pct)) : String(pct);
    var title = t('scorePenaltyTitle', { n: pctLabel });
    return (
      '<p class="ui-score-penalty-chip" title="' + esc(title) + '" aria-label="' + esc(title) + '">' +
        esc(t('scorePenaltyChip', { n: pctLabel })) +
      '</p>'
    );
  }

  function scoreClusterHtml(m) {
    return (
      '<div class="ui-score-cluster">' +
        scoreRingHtml(m.score) +
        scorePenaltyChipHtml(m) +
      '</div>'
    );
  }

  function breakdownRowHtml(label, value, modifier) {
    if (value == null || value === '') return '';
    return (
      '<li class="ui-score-breakdown__item' + (modifier ? ' ui-score-breakdown__item--' + modifier : '') + '">' +
        '<span class="ui-score-breakdown__label">' + esc(label) + '</span>' +
        '<strong>' + Math.round(value) + '%</strong>' +
      '</li>'
    );
  }

  function scoreBreakdownPanelHtml(m) {
    var s = m.scores || {};
    if (!s.hasBreakdown) return '';
    var ageLabel = s.ageProvisional ? t('scoreAgeProvisional') : t('scoreAge');
    var hintHtml = (Number(m.completenessPenalty) || 0) > 0
      ? '<p class="ui-score-breakdown__hint">' + esc(t('scoreBreakdownHint')) + '</p>'
      : '';
    return (
      '<div class="ui-score-breakdown-panel score-breakdown" data-score-panel hidden>' +
        '<p class="ui-score-breakdown-panel__title">' + esc(t('scoreBreakdownTitle')) + '</p>' +
        '<ul class="ui-score-breakdown__list" aria-label="' + esc(t('scoreBreakdownTitle')) + '">' +
          breakdownRowHtml(t('scoreSymptom'), s.symptom) +
          breakdownRowHtml(t('scoreEfficacy'), s.efficacy) +
          breakdownRowHtml(ageLabel, s.age, s.ageProvisional ? 'provisional' : '') +
          breakdownRowHtml(t('scoreUsage'), s.usage) +
          breakdownRowHtml(t('scoreSideEffect'), s.sideEffect, 'risk') +
          breakdownRowHtml(t('scoreInteraction'), s.interaction, 'risk') +
        '</ul>' +
        hintHtml +
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

  function cleanReasonText(part) {
    return String(part || '')
      .replace(/^(?:\s|[\u2705\u26A0\u274C]|\uFE0F)+/u, '')
      .replace(/\uFE0F/g, '')
      .trim();
  }

  function reasonTone(part) {
    if (/^✅/.test(part)) return 'ok';
    if (/^⚠️/.test(part)) return 'warn';
    return 'info';
  }

  function reasonIcon(tone) {
    if (tone === 'ok') return '✓';
    if (tone === 'warn') return '!';
    return '·';
  }

  function shouldSkipReasonPart(part, m) {
    if (m.ingredients && /^主成分:/.test(part)) return true;
    if (m.ageLabel && m.ageLabel !== '—' && /^年齢制限:/.test(part)) return true;
    return false;
  }

  function reasonPartsHtml(m) {
    var reason = (m.reason || '').trim();
    if (!reason) return '';
    var parts = reason.split(/\s*\|\s*/).map(function (p) { return p.trim(); }).filter(Boolean);
    var items = [];
    parts.forEach(function (part) {
      if (shouldSkipReasonPart(part, m)) return;
      var tone = reasonTone(part);
      var text = cleanReasonText(part);
      items.push(
        '<li class="ui-reason-item ui-reason-item--' + tone + '">' +
          '<span class="ui-reason-item__icon" aria-hidden="true">' + reasonIcon(tone) + '</span>' +
          '<span class="ui-reason-item__text">' + esc(text) + '</span>' +
        '</li>'
      );
    });
    if (!items.length) return '';
    return '<ul class="ui-reason-list" aria-label="' + esc(t('reason')) + '">' + items.join('') + '</ul>';
  }

  function isHtmlContent(text) {
    return /<[a-z][\s\S]*>/i.test(text);
  }

  function dbFieldSectionHtml(label, content, modifier) {
    if (!content || !String(content).trim()) return '';
    var body = isHtmlContent(content) ? content : esc(content);
    return (
      '<div class="ui-card-section ui-card-section--db' + (modifier ? ' ui-card-section--' + modifier : '') + '">' +
        '<div class="ui-card-label">' + esc(label) + '</div>' +
        '<div class="ui-card-text ui-card-text--db">' + body + '</div>' +
      '</div>'
    );
  }

  function dbDetailSectionsHtml(m) {
    return (
      dbFieldSectionHtml(t('ingredients'), m.ingredients, 'ingredients') +
      dbFieldSectionHtml(t('dosage'), m.usage, 'dosage') +
      dbFieldSectionHtml(t('usageNotes'), m.usageNotes, 'notes')
    );
  }

  function cardHtmlPro(m, options) {
    options = options || {};
    var usageDetailHtml = options.usageDetailHtml || '';
    var hasDbDetail = !!(m.ingredients || m.usage || m.usageNotes);
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
        (m.riskWarning ? '<p class="ui-card-warn">' + esc(m.riskWarning) + '</p>' : '') +
        (m.lowScoreWarning ? '<p class="ui-card-warn ui-card-warn--low">' + esc(t('lowScoreWarning')) + '</p>' : '') +
        '<div class="ui-card-pro-detail is-collapsed app-scrollbar">' +
          '<div class="ui-card-section">' +
            '<div class="ui-card-label">' + esc(t('efficacy')) + '</div>' +
            '<div class="ui-card-text ui-clamp-2">' + esc(m.efficacy) + '</div>' +
          '</div>' +
          '<div class="ui-card-section ui-card-section--reason">' +
            '<div class="ui-card-label">' + esc(t('reason')) + '</div>' +
            reasonPartsHtml(m) +
          '</div>' +
          (hasDbDetail
            ? '<div class="ui-card-usage-db">' + dbDetailSectionsHtml(m) + '</div>'
            : '') +
          (usageDetailHtml
            ? '<div class="ui-card-usage-extra">' + usageDetailHtml + '</div>'
            : '') +
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
    bindCardInteractions: bindCardInteractions,
    reasonPartsHtml: reasonPartsHtml,
    dbDetailSectionsHtml: dbDetailSectionsHtml
  };
})(typeof window !== 'undefined' ? window : globalThis);
