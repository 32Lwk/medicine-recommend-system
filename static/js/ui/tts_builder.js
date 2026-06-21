/**
 * TTS text builder — diagnosis / Sage DOM から plain text を組み立て
 */
(function (global) {
  'use strict';

  function stripHtml(html) {
    if (!html) return '';
    if (typeof document === 'undefined') {
      return String(html).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    }
    var div = document.createElement('div');
    div.innerHTML = html;
    return (div.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function buildFromDiagnosis(diag) {
    if (!diag || typeof diag !== 'object') return '';
    var parts = [];
    if (diag.render === 'sage_status' || diag.render === 'sage_qa') {
      if (diag.title) parts.push(diag.title);
      if (diag.subtitle) parts.push(diag.subtitle);
      if (diag.message) parts.push(diag.message);
      (diag.hints || []).forEach(function (h) { parts.push(h); });
      (diag.sections || []).forEach(function (sec) {
        if (sec.title) parts.push(sec.title);
        (sec.items || []).forEach(function (item) { parts.push(item); });
      });
      return parts.filter(Boolean).join('。');
    }
    if (diag.symptoms && diag.symptoms.length) {
      parts.push('推測される症状: ' + diag.symptoms.join('、'));
    }
    if (diag.personalized_advice) parts.push(diag.personalized_advice);
    (diag.recommended_medicines || []).forEach(function (med, idx) {
      var name = med.product_name || med.name || '';
      if (name) parts.push((idx + 1) + 'つ目: ' + name);
      if (med.explanation) parts.push(med.explanation);
    });
    if (diag.error && diag.error.message) parts.push(diag.error.message);
    if (diag.doctor_consultation) parts.push(diag.doctor_consultation);
    (diag.usage_sections || []).forEach(function (sec) {
      if (sec.title) parts.push(sec.title);
      (sec.items || []).forEach(function (item) { parts.push(item); });
    });
    return parts.filter(Boolean).join('。');
  }

  function buildFromElement(root) {
    if (!root) return '';
    return (root.innerText || root.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function buildFromLastBotMessage(messages) {
    if (!Array.isArray(messages)) return '';
    for (var i = messages.length - 1; i >= 0; i--) {
      var msg = messages[i];
      if (msg && msg.type === 'bot' && msg.diagnosis) {
        var text = buildFromDiagnosis(msg.diagnosis);
        if (text) return text;
      }
    }
    return '';
  }

  global.TtsBuilder = {
    buildFromDiagnosis: buildFromDiagnosis,
    buildFromElement: buildFromElement,
    buildFromLastBotMessage: buildFromLastBotMessage,
    stripHtml: stripHtml
  };
})(typeof window !== 'undefined' ? window : globalThis);
