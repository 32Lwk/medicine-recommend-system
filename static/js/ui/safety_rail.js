/**
 * Compact safety rail (header strip) synced with user_attributes.
 */
(function (global) {
  'use strict';

  var FULL_LABEL_MIN_WIDTH = 640;
  var mountedCtx = null;
  var activeRailEl = null;
  var resizeObserver = null;
  var fontSizeObserver = null;
  var windowResizeBound = false;
  var chipMeasureEl = null;

  var esc = function (s) {
    return global.MedicineMapper ? global.MedicineMapper.esc(s) : String(s);
  };
  var t = function (k, v) {
    return global.UiStrings ? global.UiStrings.t(k, v) : k;
  };

  function safetyPersonIconSvg() {
    return (
      '<svg class="ui-safety-rail__icon-svg ui-safety-rail__icon-svg--person" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true">' +
        '<circle cx="12" cy="8" r="3.5"/><path d="M5 20v-1a7 7 0 0 1 14 0v1"/>' +
      '</svg>'
    );
  }

  function chipEntry(type, labelFull, labelShort) {
    return {
      type: type,
      labelFull: labelFull,
      labelShort: labelShort != null ? labelShort : labelFull
    };
  }

  function chipLabel(chip, compact) {
    return compact ? chip.labelShort : chip.labelFull;
  }

  function safetyChipHtml(chip) {
    var cls = 'ui-safety-chip';
    if (chip.type === 'ok') cls += ' ui-safety-chip--ok';
    else if (chip.type === 'warn') cls += ' ui-safety-chip--warn';
    else if (chip.type === 'pending') cls += ' ui-safety-chip--pending';
    else if (chip.type === 'info') cls += ' ui-safety-chip--info';
    else if (chip.type === 'overflow') cls += ' ui-safety-chip--info ui-safety-chip--overflow';
    return '<em class="' + cls + '"' + (chip.ariaLabel ? ' aria-label="' + esc(chip.ariaLabel) + '"' : '') + '>' + esc(chip.label) + '</em>';
  }

  function getChipMeasureEl() {
    if (chipMeasureEl && chipMeasureEl.isConnected) return chipMeasureEl;
    chipMeasureEl = document.createElement('em');
    chipMeasureEl.className = 'ui-safety-chip ui-safety-rail__chip-measure';
    chipMeasureEl.setAttribute('aria-hidden', 'true');
    document.body.appendChild(chipMeasureEl);
    return chipMeasureEl;
  }

  function measureChipWidth(label, type) {
    var el = getChipMeasureEl();
    el.className = 'ui-safety-chip ui-safety-rail__chip-measure ui-safety-chip--' + type;
    el.textContent = label;
    return el.offsetWidth;
  }

  function measureOverflowChipWidth(count) {
    return measureChipWidth('+' + count, 'info') + 4;
  }

  function reservedRailWidth(rail) {
    var style = getComputedStyle(rail);
    var gap = parseFloat(style.columnGap || style.gap) || 8;
    var iconEl = rail.querySelector('.ui-safety-rail__icon');
    var headEl = rail.querySelector('.ui-safety-rail__head');
    var ctaEl = rail.querySelector('.ui-safety-rail__cta');
    var bodyEl = rail.querySelector('.ui-safety-rail__body');
    var bodyGap = bodyEl ? (parseFloat(getComputedStyle(bodyEl).columnGap || getComputedStyle(bodyEl).gap) || 6) : 6;
    var paddingX = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
    var reserved = paddingX + gap;
    if (iconEl) reserved += iconEl.offsetWidth + gap;
    if (ctaEl) reserved += ctaEl.offsetWidth + gap;
    if (headEl) reserved += headEl.offsetWidth + bodyGap;
    return reserved + 4;
  }

  function updateResponsiveRail(rail) {
    if (!rail || !mountedCtx) return;

    var width = rail.clientWidth;
    var compactLabels = width < FULL_LABEL_MIN_WIDTH;
    rail.setAttribute('data-safety-label-mode', compactLabels ? 'compact' : 'full');

    var statusEl = rail.querySelector('.ui-safety-rail__status');
    if (statusEl) {
      if (mountedCtx.pendingCount > 0) {
        statusEl.textContent = compactLabels
          ? t('safetyPendingShort', { n: mountedCtx.pendingCount })
          : t('safetyPending', { n: mountedCtx.pendingCount });
      } else {
        statusEl.textContent = t('safetyOk');
      }
    }

    var itemsEl = rail.querySelector('.ui-safety-rail__items');
    if (!itemsEl) return;

    var chips = mountedCtx.chips;
    var budget = Math.max(0, width - reservedRailWidth(rail));
    var chipGap = 4;
    var maxVisible = 0;
    var used = 0;

    for (var i = 0; i < chips.length; i += 1) {
      var label = chipLabel(chips[i], compactLabels);
      var chipWidth = measureChipWidth(label, chips[i].type);
      var hiddenAfter = chips.length - (i + 1);
      var overflowWidth = hiddenAfter > 0 ? measureOverflowChipWidth(hiddenAfter) : 0;
      var nextUsed = used + (maxVisible > 0 ? chipGap : 0) + chipWidth + overflowWidth;

      if (nextUsed <= budget || maxVisible === 0) {
        if (maxVisible > 0) used += chipGap;
        used += chipWidth;
        maxVisible = i + 1;
      } else {
        break;
      }
    }

    maxVisible = Math.max(1, Math.min(maxVisible, chips.length));
    var hiddenCount = chips.length - maxVisible;
    var html = chips.slice(0, maxVisible).map(function (chip) {
      return safetyChipHtml({ type: chip.type, label: chipLabel(chip, compactLabels) });
    }).join('');

    if (hiddenCount > 0) {
      html += safetyChipHtml({
        type: 'overflow',
        label: '+' + hiddenCount,
        ariaLabel: t('safetyMoreChips', { n: hiddenCount })
      });
    }

    itemsEl.innerHTML = html;
  }

  function bindResponsiveRail(rail) {
    activeRailEl = rail;
    updateResponsiveRail(rail);

    if (typeof ResizeObserver !== 'undefined') {
      if (resizeObserver) resizeObserver.disconnect();
      resizeObserver = new ResizeObserver(function () {
        if (activeRailEl) updateResponsiveRail(activeRailEl);
      });
      resizeObserver.observe(rail);
    }

    if (!windowResizeBound) {
      global.addEventListener('resize', onWindowResize, { passive: true });
      windowResizeBound = true;
    }

    if (!fontSizeObserver && typeof MutationObserver !== 'undefined') {
      fontSizeObserver = new MutationObserver(function () {
        if (activeRailEl) updateResponsiveRail(activeRailEl);
      });
      fontSizeObserver.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-font-size']
      });
    }
  }

  function onWindowResize() {
    if (activeRailEl) updateResponsiveRail(activeRailEl);
  }

  function unwrapAttr(attrs, key) {
    if (!attrs || typeof attrs !== 'object') return undefined;
    var v = attrs[key];
    if (v && typeof v === 'object' && Object.prototype.hasOwnProperty.call(v, 'value')) {
      return v.value;
    }
    return v;
  }

  function displayAllergies(attrs) {
    attrs = attrs || {};
    var list = [];
    var allergies = attrs.allergies;
    if (Array.isArray(allergies)) {
      allergies.forEach(function (a) {
        var t = String(a || '').trim();
        if (t && t !== 'なし' && list.indexOf(t) < 0) list.push(t);
      });
    }
    var envHistory = ['花粉症', 'アレルギー性鼻炎', '季節性アレルギー性鼻炎', '常年性アレルギー性鼻炎', 'アトピー', 'アトピー性皮膚炎'];
    var envMap = {
      '花粉症': '花粉',
      'アレルギー性鼻炎': 'アレルギー性鼻炎',
      '季節性アレルギー性鼻炎': 'アレルギー性鼻炎',
      '常年性アレルギー性鼻炎': 'アレルギー性鼻炎',
      'アトピー性皮膚炎': 'アトピー',
      'アトピー': 'アトピー'
    };
    (attrs.medical_history || []).forEach(function (h) {
      var text = String(h || '').trim();
      if (!text) return;
      var label = envMap[text] || (envHistory.indexOf(text) >= 0 ? text : null);
      if (label && list.indexOf(label) < 0) list.push(label);
    });
    return list;
  }

  function normalizeAttrs(attrs) {
    attrs = attrs || {};
    if (typeof attrs !== 'object') return {};
    var out = {};
    var scalarKeys = ['age', 'gender', 'pregnant', 'breastfeeding', 'other_info', 'symptom_duration_days'];
    scalarKeys.forEach(function (key) {
      var v = unwrapAttr(attrs, key);
      if (v !== undefined && v !== null && v !== '') out[key] = v;
    });
    ['allergies', 'current_medications', 'medical_history'].forEach(function (key) {
      var v = unwrapAttr(attrs, key);
      if (v === undefined || v === null) return;
      if (Array.isArray(v)) out[key] = v;
      else if (typeof v === 'string' && v.trim()) out[key] = v.split(/[、,]/).map(function (s) { return s.trim(); }).filter(Boolean);
      else out[key] = [];
    });
    return out;
  }

  function buildContext(attrs) {
    attrs = normalizeAttrs(attrs);
    var chips = [];
    var pendingCount = 0;
    var age = attrs.age;
    var gender = attrs.gender;

    if (age != null && age !== '') {
      chips.push(chipEntry('ok', age + '歳' + (gender ? '·' + gender : '')));
    } else {
      chips.push(chipEntry('pending', t('safetyAgePending'), t('safetyAgePendingShort')));
      pendingCount += 1;
    }

    var allergies = displayAllergies(attrs);
    if (allergies.length) {
      chips.push(chipEntry('warn', t('safetyAllergyPrefix') + allergies.join('、')));
    } else if (Array.isArray(attrs.allergies) && (!attrs.allergies.length || attrs.allergies.indexOf('なし') >= 0)) {
      chips.push(chipEntry('ok', t('safetyAllergyNone')));
    } else if (!attrs.allergies) {
      chips.push(chipEntry('pending', t('safetyAllergyPending'), t('safetyAllergyPendingShort')));
      pendingCount += 1;
    }

    var meds = attrs.current_medications;
    if (Array.isArray(meds)) {
      if (!meds.length) chips.push(chipEntry('ok', t('safetyMedsNone')));
      else chips.push(chipEntry('info', t('safetyMedsPrefix') + meds.join('、')));
    } else {
      chips.push(chipEntry('pending', t('safetyMedsPending'), t('safetyMedsPendingShort')));
      pendingCount += 1;
    }

    if (gender === '女性') {
      if (attrs.pregnant === true) chips.push(chipEntry('warn', t('safetyPregnant')));
      else if (attrs.breastfeeding === true) chips.push(chipEntry('warn', t('safetyBreastfeeding')));
      else if (attrs.pregnant === false && attrs.breastfeeding === false) {
        chips.push(chipEntry('ok', t('safetyPregnancyNone')));
      } else if (attrs.pregnant == null && attrs.breastfeeding == null) {
        chips.push(chipEntry('pending', t('safetyPregnancyPending'), t('safetyPregnancyPendingShort')));
        pendingCount += 1;
      }
    }

    var statusClass = pendingCount > 0 ? 'ui-safety-rail__status--pending' : 'ui-safety-rail__status--ok';
    var statusHtml = '<span class="ui-safety-rail__status ' + statusClass + '"></span>';

    return {
      chips: chips,
      pendingCount: pendingCount,
      statusHtml: statusHtml,
      ctaLabel: pendingCount > 0 ? t('safetyCtaAdd') : t('safetyCtaEdit')
    };
  }

  function htmlFromContext(ctx) {
    ctx = ctx || { chips: [], statusHtml: '', ctaLabel: t('safetyCtaEdit') };
    return (
      '<div class="ui-safety-rail ui-safety-rail--compact" role="region" aria-label="safety">' +
        '<div class="ui-safety-rail__icon" aria-hidden="true">' + safetyPersonIconSvg() + '</div>' +
        '<div class="ui-safety-rail__body">' +
          '<div class="ui-safety-rail__head">' +
            '<strong>' + esc(t('safetyTitle')) + '</strong>' +
            ctx.statusHtml +
          '</div>' +
          '<span class="ui-safety-rail__items"></span>' +
        '</div>' +
        '<button type="button" class="ui-safety-rail__cta" id="safetyRailCta" aria-label="' + esc(ctx.ctaLabel) + '">' + esc(ctx.ctaLabel) + '</button>' +
      '</div>'
    );
  }

  function mount(attrs) {
    var mountEl = document.getElementById('safetyRailMount');
    if (!mountEl) return;
    mountedCtx = buildContext(attrs);
    mountEl.innerHTML = htmlFromContext(mountedCtx);
    var rail = mountEl.querySelector('.ui-safety-rail--compact');
    if (rail) bindResponsiveRail(rail);
    var cta = document.getElementById('safetyRailCta');
    if (cta) {
      cta.addEventListener('click', function () {
        if (typeof global.openUserInfoModal === 'function') global.openUserInfoModal();
        else if (typeof global.openAttributeModal === 'function') global.openAttributeModal();
      });
    }
  }

  function updateHeaderPhase() {
    /* header phase rotates fixed messages via SageShell.refreshHeaderPhase */
  }

  global.SafetyRail = {
    mount: mount,
    buildContext: buildContext,
    normalizeAttrs: normalizeAttrs,
    displayAllergies: displayAllergies,
    updateHeaderPhase: updateHeaderPhase,
    reflow: function () {
      if (activeRailEl) updateResponsiveRail(activeRailEl);
    }
  };
})(typeof window !== 'undefined' ? window : globalThis);
