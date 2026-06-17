/**
 * Compact safety rail (header strip) synced with user_attributes.
 */
(function (global) {
  'use strict';

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

  function safetyChipHtml(chip) {
    var cls = 'ui-safety-chip';
    if (chip.type === 'ok') cls += ' ui-safety-chip--ok';
    else if (chip.type === 'warn') cls += ' ui-safety-chip--warn';
    else if (chip.type === 'pending') cls += ' ui-safety-chip--pending';
    else if (chip.type === 'info') cls += ' ui-safety-chip--info';
    return '<em class="' + cls + '">' + esc(chip.label) + '</em>';
  }

  function unwrapAttr(attrs, key) {
    if (!attrs || typeof attrs !== 'object') return undefined;
    var v = attrs[key];
    if (v && typeof v === 'object' && Object.prototype.hasOwnProperty.call(v, 'value')) {
      return v.value;
    }
    return v;
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
      chips.push({ type: 'ok', label: age + '歳' + (gender ? '·' + gender : '') });
    } else {
      chips.push({ type: 'pending', label: t('safetyAgePending') });
      pendingCount += 1;
    }

    var allergies = attrs.allergies;
    if (Array.isArray(allergies)) {
      if (!allergies.length || allergies.indexOf('なし') >= 0) {
        chips.push({ type: 'ok', label: t('safetyAllergyNone') });
      } else {
        chips.push({ type: 'warn', label: t('safetyAllergyPrefix') + allergies.join('、') });
      }
    } else if (!allergies) {
      chips.push({ type: 'pending', label: t('safetyAllergyPending') });
      pendingCount += 1;
    }

    var meds = attrs.current_medications;
    if (Array.isArray(meds)) {
      if (!meds.length) chips.push({ type: 'ok', label: t('safetyMedsNone') });
      else chips.push({ type: 'info', label: t('safetyMedsPrefix') + meds.join('、') });
    } else {
      chips.push({ type: 'pending', label: t('safetyMedsPending') });
      pendingCount += 1;
    }

    if (gender === '女性') {
      if (attrs.pregnant === true) chips.push({ type: 'warn', label: t('safetyPregnant') });
      else if (attrs.breastfeeding === true) chips.push({ type: 'warn', label: t('safetyBreastfeeding') });
      else if (attrs.pregnant === false && attrs.breastfeeding === false) {
        chips.push({ type: 'ok', label: t('safetyPregnancyNone') });
      } else if (attrs.pregnant == null && attrs.breastfeeding == null) {
        chips.push({ type: 'pending', label: t('safetyPregnancyPending') });
        pendingCount += 1;
      }
    }

    var statusHtml = '';
    if (pendingCount > 0) {
      statusHtml = '<span class="ui-safety-rail__status ui-safety-rail__status--pending">' + esc(t('safetyPending', { n: pendingCount })) + '</span>';
    } else {
      statusHtml = '<span class="ui-safety-rail__status ui-safety-rail__status--ok">' + esc(t('safetyOk')) + '</span>';
    }

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
          '<span class="ui-safety-rail__items app-scrollbar">' +
            ctx.chips.map(safetyChipHtml).join('') +
          '</span>' +
        '</div>' +
        '<button type="button" class="ui-safety-rail__cta" id="safetyRailCta" aria-label="' + esc(ctx.ctaLabel) + '">' + esc(ctx.ctaLabel) + '</button>' +
      '</div>'
    );
  }

  function mount(attrs) {
    var mountEl = document.getElementById('safetyRailMount');
    if (!mountEl) return;
    var ctx = buildContext(attrs);
    mountEl.innerHTML = htmlFromContext(ctx);
    var cta = document.getElementById('safetyRailCta');
    if (cta) {
      cta.addEventListener('click', function () {
        if (typeof global.openUserInfoModal === 'function') global.openUserInfoModal();
        else if (typeof global.openAttributeModal === 'function') global.openAttributeModal();
      });
    }
  }

  function updateHeaderPhase(symptoms) {
    var el = document.getElementById('headerPhase');
    if (!el || !symptoms || !symptoms.length) return;
    el.textContent = symptoms.slice(0, 2).join('・') + '向け · 候補' + Math.min(3, symptoms.length) + '件';
  }

  global.SafetyRail = {
    mount: mount,
    buildContext: buildContext,
    normalizeAttrs: normalizeAttrs,
    updateHeaderPhase: updateHeaderPhase
  };
})(typeof window !== 'undefined' ? window : globalThis);
