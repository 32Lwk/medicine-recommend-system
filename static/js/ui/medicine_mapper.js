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

  function scoresFromMed(med) {
    var sb = med.score_breakdown || med.scores || {};
    return {
      symptom: sb.symptom != null ? sb.symptom : (sb.symptom_match != null ? sb.symptom_match : 0),
      efficacy: sb.efficacy != null ? sb.efficacy : (sb.efficacy_specificity != null ? sb.efficacy_specificity : 0),
      age: sb.age != null ? sb.age : (sb.age_suitability != null ? sb.age_suitability : 0),
      usage: sb.usage != null ? sb.usage : (sb.usage_convenience != null ? sb.usage_convenience : 0)
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

  function mapMedicine(med, index) {
    med = med || {};
    var rank = med.rank || med.number || index + 1;
    var score = parseScorePercent(med);
    var scores = scoresFromMed(med);
    var hasScores = scores.symptom || scores.efficacy || scores.age || scores.usage;
    if (!hasScores && score) {
      scores = { symptom: score, efficacy: Math.max(0, score - 5), age: 100, usage: Math.max(0, score - 8) };
    }
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
      imageUrl: imageUrlFromMed(med),
      placeholderUrl: PLACEHOLDER,
      riskWarning: med.risk_warning || '',
      lowScoreWarning: !!med.low_score_warning,
      ageRestriction: med.age_restriction || '',
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
