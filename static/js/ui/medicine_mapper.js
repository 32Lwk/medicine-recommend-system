/**
 * Normalize API / SSE / diagnosis medicine objects to carousel card model.
 */
(function (global) {
  'use strict';

  var PLACEHOLDER = '/static/line/medicine-noimage-hero.png';

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function parseScorePercent(med) {
    if (med.display_score != null && med.display_score !== '') {
      var ds = Number(med.display_score);
      if (!isNaN(ds)) {
        return ds <= 10 ? Math.round(ds * 10) : Math.round(ds);
      }
    }
    if (med.relative_score != null && med.relative_score !== '') {
      return Math.round(Number(med.relative_score) * 100);
    }
    if (med.score != null && med.score !== '') {
      var s = Number(med.score);
      return s <= 1 ? Math.round(s * 100) : Math.round(s);
    }
    return 0;
  }

  function ageLabelFromRestriction(med) {
    var ar = med.age_restriction || med.age_label || '';
    if (typeof ar === 'number' && !isNaN(ar)) {
      return ar + '歳以上';
    }
    if (typeof ar === 'string' && ar.trim()) {
      if (ar.indexOf('歳') >= 0) return ar.trim();
      return ar.trim() + '歳以上';
    }
    return '—';
  }

  function symptomsFromMed(med) {
    if (Array.isArray(med.symptoms) && med.symptoms.length) {
      return med.symptoms.slice(0, 6);
    }
    if (Array.isArray(med.matched_symptoms) && med.matched_symptoms.length) {
      return med.matched_symptoms.slice(0, 6);
    }
    return [];
  }

  function toBreakdownPercent(v) {
    if (v === undefined || v === null || v === '') return 0;
    var n = Number(v);
    if (isNaN(n)) return 0;
    if (n >= 0 && n <= 1) return Math.round(n * 100);
    return Math.max(0, Math.min(100, Math.round(n)));
  }

  function pickBreakdownPercent(sb, keys) {
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      if (sb[k] !== undefined && sb[k] !== null && sb[k] !== '') {
        return toBreakdownPercent(sb[k]);
      }
    }
    return 0;
  }

  function riskLevelPercent(v) {
    if (v === undefined || v === null || v === '') return null;
    var n = Number(v);
    if (isNaN(n)) return null;
    // バックエンドは 0=リスクなし、負値=ペナルティ量
    if (n <= 0) return Math.max(0, Math.min(100, Math.round(Math.abs(n) * 100)));
    if (n <= 1) return Math.round(n * 100);
    return Math.max(0, Math.min(100, Math.round(n)));
  }

  function pickBreakdownRaw(sb, keys) {
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      if (sb[k] !== undefined && sb[k] !== null && sb[k] !== '') {
        return sb[k];
      }
    }
    return null;
  }

  function completenessPenaltyFromMed(med) {
    var p = med.completeness_penalty;
    if (p != null && p !== '' && !isNaN(Number(p)) && Number(p) > 0) {
      return Number(p);
    }
    var sb = med.score_breakdown || med.scores || {};
    var fromSb = sb.completeness_penalty;
    if (fromSb != null && fromSb !== '' && !isNaN(Number(fromSb))) {
      return Math.abs(Number(fromSb));
    }
    return 0;
  }

  function hasScoreBreakdown(sb) {
    if (!sb || typeof sb !== 'object') return false;
    var keys = [
      'symptom', 'symptom_match', 'symptom_match_score',
      'efficacy', 'efficacy_specificity', 'efficacy_specificity_score',
      'age', 'age_fit', 'age_suitability',
      'usage', 'usage_convenience',
      'side_effect_risk', 'side_effect_risk_score',
      'interaction_risk', 'interaction_risk_score'
    ];
    for (var i = 0; i < keys.length; i++) {
      var v = sb[keys[i]];
      if (v !== undefined && v !== null && v !== '') return true;
    }
    return false;
  }

  function scoresFromMed(med) {
    var sb = med.score_breakdown || med.scores || {};
    var sideRaw = pickBreakdownRaw(sb, ['side_effect_risk', 'side_effect_risk_score']);
    var interRaw = pickBreakdownRaw(sb, ['interaction_risk', 'interaction_risk_score']);
    var sideEffect = sideRaw != null ? riskLevelPercent(sideRaw) : null;
    var interaction = interRaw != null ? riskLevelPercent(interRaw) : null;
    return {
      symptom: pickBreakdownPercent(sb, ['symptom', 'symptom_match', 'symptom_match_score']),
      efficacy: pickBreakdownPercent(sb, ['efficacy', 'efficacy_specificity', 'efficacy_specificity_score']),
      age: pickBreakdownPercent(sb, ['age', 'age_fit', 'age_suitability']),
      usage: pickBreakdownPercent(sb, ['usage', 'usage_convenience']),
      sideEffect: sideEffect,
      interaction: interaction,
      hasBreakdown: hasScoreBreakdown(sb)
    };
  }

  function imageUrlFromMed(med) {
    for (var i = 0; i < arguments.length; i++) {}
    var keys = ['image_url', 'imageUrl', 'hero_url', 'product_image_url'];
    for (var j = 0; j < keys.length; j++) {
      var v = med[keys[j]];
      if (v && String(v).trim()) return String(v).trim();
    }
    return null;
  }

  function splitUsageField(usageText) {
    var usage = String(usageText || '').trim();
    if (!usage) return { dosage: '', precautions: '' };
    var idx = usage.indexOf('＜');
    if (idx >= 0) {
      return {
        dosage: usage.slice(0, idx).trim(),
        precautions: usage.slice(idx).trim()
      };
    }
    return { dosage: usage, precautions: '' };
  }

  function resolveUsageNotes(usageText, apiNotes) {
    var split = splitUsageField(usageText);
    if (split.precautions) return split.precautions;
    var api = String(apiNotes || '').trim();
    return api;
  }

  function mapMedicine(med, index) {
    med = med || {};
    var rank = med.rank || med.number || index + 1;
    var score = parseScorePercent(med);
    var scores = scoresFromMed(med);
    var hasScores = scores.hasBreakdown;
    if (!hasScores && score) {
      scores = {
        symptom: score,
        efficacy: Math.max(0, score - 5),
        age: 100,
        usage: Math.max(0, score - 8),
        sideEffect: null,
        interaction: null,
        hasBreakdown: true
      };
    }
    var completenessPenalty = completenessPenaltyFromMed(med);
    if (completenessPenalty > 0) {
      scores.ageProvisional = true;
    }
    var usageFull = med.usage || '';
    var usageSplit = splitUsageField(usageFull);
    return {
      rank: rank,
      name: med.product_name || med.name || '',
      maker: med.manufacturer || med.maker || '',
      efficacy: med.efficacy || '',
      reason: med.explanation || med.reason || '',
      score: score,
      medType: med.medicine_type || med.medType || 'OTC',
      symptoms: symptomsFromMed(med),
      ageLabel: ageLabelFromRestriction(med),
      scores: scores,
      completenessPenalty: completenessPenalty,
      imageUrl: imageUrlFromMed(med),
      placeholderUrl: PLACEHOLDER,
      riskWarning: med.risk_warning || '',
      lowScoreWarning: !!med.low_score_warning,
      ageRestriction: med.age_restriction || '',
      ingredients: med.ingredients || '',
      usage: usageSplit.dosage || usageFull,
      usageNotes: resolveUsageNotes(usageFull, med.usage_notes || med.usageNotes),
      raw: med
    };
  }

  function mapMedicines(list) {
    return (list || []).slice(0, 5).map(function (m, i) {
      return mapMedicine(m, i);
    });
  }

  global.MedicineMapper = {
    esc: esc,
    mapMedicine: mapMedicine,
    mapMedicines: mapMedicines,
    placeholderUrl: PLACEHOLDER
  };
})(typeof window !== 'undefined' ? window : globalThis);
