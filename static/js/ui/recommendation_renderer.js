/**

 * Recommendation block renderer — Sage Terrace ui-bubble--reco + carousel.

 */

(function (global) {

  'use strict';



  var esc = function (s) {

    return global.MedicineMapper ? global.MedicineMapper.esc(s) : String(s == null ? '' : s);

  };



  var t = function (k, v) {

    return global.UiStrings ? global.UiStrings.t(k, v) : k;

  };



  function isSageUi() {

    return document.body && document.body.getAttribute('data-ui-variant') === 'sage';

  }



  function isDiagnosisPayload(diag) {

    return diag !== null && typeof diag === 'object' && !Array.isArray(diag);

  }



  function applyDiagnosisI18n(diag) {

    if (!isDiagnosisPayload(diag) || !global.UiStrings) return diag;

    var lang = global.UiStrings.lang();

    if (!lang || lang === 'ja') return diag;

    var bucket = diag.i18n && diag.i18n[lang];

    if (!bucket) return diag;

    var out = Object.assign({}, diag);

    Object.keys(bucket).forEach(function (key) {

      if (bucket[key] != null && bucket[key] !== '') {

        out[key] = bucket[key];

      }

    });

    if (bucket.error && out.error) {

      out.error = Object.assign({}, out.error, bucket.error);

    }

    if (bucket.hints && bucket.hints.length) {

      out.hints = bucket.hints;

    }

    return out;

  }



  function symptomNameList(diag) {

    if (!diag) return [];

    var symptoms = diag.symptoms || [];

    return symptoms.map(function (s) {

      if (typeof s === 'string' && s.trim()) return s.trim();

      if (s && typeof s === 'object') {

        return String(s.name || s.symptom || '').trim();

      }

      return s != null ? String(s).trim() : '';

    }).filter(Boolean).slice(0, 8);

  }



  function symptomsFromMedicines(medicines) {

    if (!medicines || !medicines.length) return [];

    var first = medicines[0] || {};

    var list = first.symptoms || first.matched_symptoms || [];

    if (Array.isArray(list) && list.length) {

      return list.map(function (s) { return String(s).trim(); }).filter(Boolean).slice(0, 8);

    }

    return [];

  }



  function stripHtmlText(html) {

    if (!html) return '';

    if (typeof document === 'undefined') {

      return String(html).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

    }

    var div = document.createElement('div');

    div.innerHTML = html;

    return (div.textContent || '').replace(/\s+/g, ' ').trim();

  }



  function userSessionSnippet() {

    var attrs = (typeof global !== 'undefined' && global.__lastUserAttributes) || {};

    var ageVal = attrs.age && attrs.age.value != null ? attrs.age.value : null;

    var age = ageVal != null && ageVal !== '' ? String(ageVal) + '歳' : '';

    var genderRaw = attrs.gender && attrs.gender.value ? String(attrs.gender.value) : '';

    var gender = '';

    if (genderRaw === 'male' || genderRaw === '男性') gender = '（男性）';

    else if (genderRaw === 'female' || genderRaw === '女性') gender = '（女性）';

    else if (genderRaw) gender = '（' + genderRaw + '）';

    return { age: age, gender: gender };

  }



  function isPersonalizedAdviceWarning(el) {

    return el.classList.contains('warning-info') &&

      el.getAttribute('aria-label') === 'あなたに合わせたアドバイス';

  }



  function getCollapsibleContentHtml(sec) {

    if (!sec) return '';

    var content = sec.querySelector('.collapse-content');

    if (content) return content.innerHTML;

    var toggle = sec.querySelector('.collapse-toggle');

    var child = toggle ? toggle.nextElementSibling : null;

    if (child && child.tagName !== 'BUTTON') return child.innerHTML;

    return '';

  }



  function parseLegacyUsageSections(legacyHost) {

    var perMedicine = {};

    var shared = [];

    if (!legacyHost) return { perMedicine: perMedicine, shared: shared };

    legacyHost.querySelectorAll('.collapsible-section').forEach(function (sec) {

      var label = sec.getAttribute('aria-label') || '';

      if (label === '症状分析結果' || label === '使用上の注意') return;

      var contentHtml = getCollapsibleContentHtml(sec);

      if (!contentHtml.trim()) return;

      var rankMatch = label.match(/^(\d+)つ目/);

      if (rankMatch) {

        perMedicine[parseInt(rankMatch[1], 10)] = contentHtml;

        return;

      }

      if (label.indexOf('使ってはいけない') >= 0 ||

          label.indexOf('服用時の注意') >= 0 ||

          label.indexOf('OTC') >= 0 ||

          label.indexOf('ドーピング') >= 0) {

        shared.push({ label: label, contentHtml: contentHtml });

      }

    });

    return { perMedicine: perMedicine, shared: shared };

  }



  function buildCardUsageDetailHtml(rank, usageSections, med) {

    usageSections = usageSections || { perMedicine: {}, shared: [] };

    med = med || {};

    var hasDb = !!(med.ingredients || med.usage || med.usageNotes);

    var parts = [];

    if (!hasDb) {

      var legacyMed = usageSections.perMedicine[rank];

      if (legacyMed) {

        parts.push('<div class="ui-card-usage-block ui-card-usage-block--legacy">' + legacyMed + '</div>');

      }

    }

    if (usageSections.shared && usageSections.shared.length) {

      usageSections.shared.forEach(function (section) {

        parts.push(

          '<div class="ui-card-usage-block ui-card-usage-block--shared">' +

            '<div class="ui-card-label">' + esc(section.label) + '</div>' +

            '<div class="ui-card-usage-content">' + section.contentHtml + '</div>' +

          '</div>'

        );

      });

    }

    return parts.join('');

  }



  function renderMedicinesCarousel(medicines, options) {

    options = options || {};

    if (!global.MedicineMapper || !global.MedicineCard || !global.MedicineCarousel) {

      return '';

    }

    var mapped = global.MedicineMapper.mapMedicines(medicines);

    if (!mapped.length) return '';

    var usageSections = options.usageSections || { perMedicine: {}, shared: [] };

    var cards = mapped.map(function (m) {

      return global.MedicineCard.cardHtmlPro(m, {

        usageDetailHtml: buildCardUsageDetailHtml(m.rank, usageSections, m)

      });

    }).join('');

    return global.MedicineCarousel.carouselBlockHtml(cards, mapped.length, 'pro');

  }



  function renderMedicinesEmptyHtml() {

    return (

      '<div class="ui-reco-medicines-empty ui-alert ui-alert--warn" role="status" aria-label="' + esc(t('recoIntro')) + '">' +

        '<strong>💊 ' + esc(t('recoIntro')) + '</strong><br>' + esc(t('noMedicinesFound')) +

      '</div>'

    );

  }



  function renderMedicinesBlock(medicines, options) {

    options = options || {};

    if (medicines && medicines.length) {

      return renderMedicinesCarousel(medicines, options);

    }

    return renderMedicinesEmptyHtml();

  }



  function symptomIntroHtml(symptoms) {

    if (!symptoms || !symptoms.length) return '';

    var tags = symptoms.map(function (s) {

      return '<span class="ui-symptom-tag">' + esc(s) + '</span>';

    }).join('');

    return (

      '<div class="ui-reco-intro recommendation-intro">' +

        '<svg class="ui-reco-intro-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true">' +

          '<circle cx="11" cy="11" r="7"/><line x1="16" y1="16" x2="21" y2="21" stroke="currentColor" stroke-width="2"/>' +

        '</svg>' +

        '<span>' + esc(t('estimatedSymptoms')) + '</span>' +

        '<span class="ui-symptom-tags ui-symptom-tags--inline">' + tags + '</span>' +

      '</div>'

    );

  }



  function personalizedAdviceHtml(diag, adviceText) {

    var text = (adviceText || '').trim();

    if (!text) {

      var sess = userSessionSnippet();

      var symptoms = symptomNameList(diag);

      if (!symptoms.length && diag && diag.recommended_medicines) {

        symptoms = symptomsFromMedicines(diag.recommended_medicines);

      }

      var symptomText = symptoms.slice(0, 3).join('・');

      if (sess.age || symptomText) {

        text =

          (sess.age || '') + sess.gender +

          'の方で、主な症状は「' + symptomText + '」です。' +

          '総合感冒薬のなかから症状のバランスと年齢適合を考慮して候補を選びました。' +

          '服用中のお薬やアレルギーがある場合は、購入前に薬剤師にご相談ください。';

      }

    }

    if (!text) return '';

    return (

      '<div class="ui-personal-advice" role="note" aria-label="' + esc(t('personalAdviceTitle')) + '">' +

        '<div class="ui-personal-advice__head">' +

          '<svg class="ui-personal-advice__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true">' +

            '<path d="M12 3l8 4v5c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V7l8-4z"/>' +

          '</svg>' +

          '<h4 class="ui-personal-advice__title">' + esc(t('personalAdviceTitle')) + '</h4>' +

        '</div>' +

        '<p class="ui-personal-advice__text">' + esc(text) + '</p>' +

      '</div>'

    );

  }



  function extractOnclickJson(btn) {

    if (!btn) return null;

    var onclick = btn.getAttribute('onclick') || '';

    var match = onclick.match(/handle(?:Positive|Negative)Feedback\(([\s\S]+)\)\s*$/);

    if (!match) return null;

    try {

      return JSON.parse(match[1].replace(/&quot;/g, '"').replace(/&#39;/g, "'"));

    } catch (e) {

      return null;

    }

  }

  function attrEscape(s) {

    return String(s)

      .replace(/&/g, '&amp;')

      .replace(/"/g, '&quot;')

      .replace(/</g, '&lt;');

  }

  function feedbackHtmlFromLegacy(feedbackEl) {

    var qText = t('feedbackQuestionRecommendation');

    var posBtn = null;

    var negBtn = null;

    if (feedbackEl) {

      var p = feedbackEl.querySelector('p');

      if (p && p.textContent.trim()) qText = p.textContent.trim();

      posBtn = feedbackEl.querySelector('.feedback-btn-positive');

      negBtn = feedbackEl.querySelector('.feedback-btn-negative');

    }

    var posJson = extractOnclickJson(posBtn);

    var negJson = extractOnclickJson(negBtn);

    var posAttr = posJson ? ' data-feedback-payload="' + attrEscape(JSON.stringify(posJson)) + '"' : '';

    var negAttr = negJson ? ' data-feedback-payload="' + attrEscape(JSON.stringify(negJson)) + '"' : '';

    return (

      '<div class="ui-feedback" data-sage-feedback="1">' +

        '<span>' + esc(qText) + '</span>' +

        '<button type="button" data-feedback="up"' + posAttr + ' onclick="handlePositiveFeedback(this.dataset.feedbackPayload ? JSON.parse(this.dataset.feedbackPayload) : null)">' + esc(t('feedbackPositive')) + '</button>' +

        '<button type="button" data-feedback="down"' + negAttr + ' onclick="handleNegativeFeedback(this.dataset.feedbackPayload ? JSON.parse(this.dataset.feedbackPayload) : null)">' + esc(t('feedbackNegative')) + '</button>' +

      '</div>'

    );

  }



  function voiceHtmlFromLegacy(voiceEl) {

    if (!voiceEl) return '';

    return '<div class="ui-reco-voice" id="voice-read-container-inline">' + voiceEl.innerHTML + '</div>';

  }



  function collectFollowupQuestions(diag, legacyHost) {

    var questions = [];

    if (diag && Array.isArray(diag.critical_questions)) {

      questions = questions.concat(diag.critical_questions);

    }

    if (diag && Array.isArray(diag.additional_questions)) {

      diag.additional_questions.forEach(function (q) {

        if (q && questions.indexOf(q) < 0) questions.push(q);

      });

    }

    if (!questions.length && legacyHost) {

      legacyHost.querySelectorAll('h4').forEach(function (h4) {

        if (h4.textContent.indexOf('追加でお伺い') < 0) return;

        var ul = h4.parentElement && h4.parentElement.querySelector('ul');

        if (!ul) return;

        ul.querySelectorAll('li').forEach(function (li) {

          var q = li.textContent.trim();

          if (q) questions.push(q);

        });

      });

    }

    return questions;

  }



  function followupQuestionsHtml(diag, legacyHost) {

    var questions = collectFollowupQuestions(diag, legacyHost);

    if (!questions.length) return '';

    var priority = (diag && diag.missing_priority) || 'important';

    var priorityLabel = { critical: '必須', important: '重要', optional: '任意' }[priority] || '重要';

    var alertClass = priority === 'critical' ? 'ui-alert--danger' : priority === 'important' ? 'ui-alert--warn' : 'ui-alert--caution';

    var intro = priority === 'critical'

      ? 'より適切な医薬品をご提案するため、以下の情報を教えてください：'

      : priority === 'important'

        ? '安全のため、以下の情報を教えてください：'

        : 'より安全な使用のため、可能であれば以下の情報を教えてください：';

    return (

      '<div class="ui-alert ' + alertClass + ' ui-reco-followup">' +

        '<strong>❓ ' + esc(t('followupTitle')) + '</strong>' +

        '<span class="ui-priority-badge">（優先度: ' + esc(priorityLabel) + '）</span>' +

        '<p class="ui-reco-followup__intro">' + esc(intro) + '</p>' +

        '<ul class="ui-followup-list">' +

          questions.map(function (q) { return '<li>' + esc(q) + '</li>'; }).join('') +

        '</ul>' +

        '<button type="button" class="ui-btn ui-btn--primary ui-btn--block" onclick="openAttributeModal()">📋 ' + esc(t('followupAnswer')) + '</button>' +

      '</div>'

    );

  }



  function doctorWarningHtml(legacyHost, diag) {

    if (legacyHost) {

      var legacy = legacyHost.querySelector('.warning-critical[aria-label="医師の受診が必要な場合"]');

      if (legacy) {

        var clone = legacy.cloneNode(true);

        clone.removeAttribute('style');

        clone.className = 'ui-alert ui-alert--danger ui-reco-doctor';

        clone.querySelectorAll('[style]').forEach(function (node) { node.removeAttribute('style'); });

        return clone.outerHTML;

      }

    }

    if (diag && diag.doctor_consultation) {

      var consult = String(diag.doctor_consultation || '').trim();

      if (consult) {

        return (

          '<div class="ui-alert ui-alert--danger ui-reco-doctor">' +

            '<strong>🏥 ' + esc(t('doctorConsultTitle')) + '</strong><br>' +

            esc(consult).replace(/\n/g, '<br>') +

          '</div>'

        );

      }

    }

    return '';

  }



  function parseOverlapLine(text) {

    var ingredient = '';

    var meds = '';

    var note = '';

    var colonIdx = text.indexOf('：');

    if (colonIdx < 0) colonIdx = text.indexOf(':');

    if (colonIdx >= 0) {

      ingredient = text.slice(0, colonIdx).trim();

      var rest = text.slice(colonIdx + 1).trim();

      var paren = rest.match(/^(.+?)（(.+)）$/);

      if (paren) {

        meds = paren[1].trim();

        note = paren[2].trim();

      } else {

        meds = rest;

      }

    } else {

      meds = text;

    }

    return { ingredient: ingredient, meds: meds, note: note };

  }



  function overlapWarningsFromDiagnosis(diag) {

    var overlap = diag && diag.ingredient_overlap;

    if (!overlap || !overlap.summaries || !overlap.summaries.length) return '';

    var severity = overlap.severity === 'red' ? 'danger'

      : overlap.severity === 'yellow' ? 'warn' : 'info';

    var badge = severity === 'danger' ? '重複禁止' : severity === 'warn' ? '注意' : '情報';

    var title = overlap.title || '成分の重複について';

    var rows = overlap.summaries.map(function (line) {

      var parsed = parseOverlapLine(line);

      return (

        '<div class="ui-overlap-row">' +

          (parsed.ingredient

            ? '<span class="ui-overlap-row__ingredient">' + esc(parsed.ingredient) + '</span>'

            : '') +

          '<span class="ui-overlap-row__meds">' + esc(parsed.meds) + '</span>' +

          (parsed.note

            ? '<span class="ui-overlap-row__note">' + esc(parsed.note) + '</span>'

            : '') +

        '</div>'

      );

    }).join('');

    return (

      '<div class="ui-overlap-card ui-overlap-card--' + severity + '">' +

        '<div class="ui-overlap-card__head">' +

          '<span class="ui-overlap-card__badge">' + esc(badge) + '</span>' +

          '<span class="ui-overlap-card__title">' + esc(title) + '</span>' +

        '</div>' +

        '<div class="ui-overlap-card__body">' + rows + '</div>' +

      '</div>'

    );

  }



  function usageSectionsFromDiagnosis(diag) {

    var perMedicine = {};

    var shared = [];

    if (!diag || !diag.usage_sections) return { perMedicine: perMedicine, shared: shared };

    diag.usage_sections.forEach(function (sec, idx) {

      var html = sec.html;

      if (!html && sec.items && sec.items.length) {

        html = sec.items.map(function (item) { return '<p>' + esc(item) + '</p>'; }).join('');

      }

      if (!html) return;

      if (sec.kind === 'per_medicine') {

        var rank = idx + 1;

        var match = String(sec.title || '').match(/^(\d+)つ目/);

        if (match) rank = parseInt(match[1], 10);

        perMedicine[rank] = html;

      } else {

        shared.push({ label: sec.title || sec.kind, contentHtml: html });

      }

    });

    return { perMedicine: perMedicine, shared: shared };

  }



  function errorAlertHtml(diag) {

    if (!diag || !diag.error) return '';

    var err = diag.error;

    var cls = err.severity === 'danger' ? 'ui-alert--danger'

      : err.severity === 'warn' ? 'ui-alert--warn' : 'ui-alert--info';

    var recs = (err.recommendations || []).map(function (r) {

      return '<li>' + esc(r) + '</li>';

    }).join('');

    return (

      '<div class="ui-alert ' + cls + ' ui-reco-error">' +

        '<strong>' + esc(err.title || t('recoIntro')) + '</strong><br>' +

        esc(err.message || '') +

        (recs ? '<ul class="ui-followup-list">' + recs + '</ul>' : '') +

      '</div>'

    );

  }



  function buildStandardVoiceHtml() {

    return (

      '<div class="ui-reco-voice" id="voice-read-container-inline">' +

        '<button type="button" class="voice-read-main-btn ui-btn ui-btn--block" id="voiceReadMainBtn" onclick="toggleVoiceRead()" aria-label="推奨結果を音声で読み上げる">' +

          '🔊 音声で聞く' +

        '</button>' +

      '</div>'

    );

  }



  function buildStandardFeedbackHtml() {

    return buildCompactFeedbackHtml('feedbackQuestionShort');

  }



  function buildCompactFeedbackHtml(questionKey) {

    var qKey = questionKey || 'feedbackQuestionShort';

    return (

      '<div class="ui-feedback-compact feedback-buttons">' +

        '<span class="ui-feedback-compact__label">' + esc(t(qKey)) + '</span>' +

        '<div class="ui-feedback-compact__actions">' +

          '<button type="button" class="feedback-btn-positive ui-feedback-compact__btn" data-feedback="positive" aria-label="' + esc(t('feedbackPositive')) + '">👍</button>' +

          '<button type="button" class="feedback-btn-negative ui-feedback-compact__btn" data-feedback="negative" aria-label="' + esc(t('feedbackNegative')) + '">👎</button>' +

        '</div>' +

      '</div>'

    );

  }



  function buildFeedbackThanksHtml() {

    return (

      '<div class="ui-feedback-compact feedback-buttons ui-feedback-compact--done">' +

        '<span class="ui-feedback-compact__thanks" aria-live="polite">✓ ' + esc(t('feedbackThanksShort')) + '</span>' +

      '</div>'

    );

  }



  function resolveFeedbackBlockHtml(diag, options) {

    if (diag && diag.feedback_completed) {

      return buildFeedbackThanksHtml();

    }

    if (diag && diag.show_feedback === false) {

      return '';

    }

    return (options && options.feedbackHtml) || buildStandardFeedbackHtml();

  }



  function buildUsageSectionsSkeletonHtml() {

    return (

      '<div class="ui-reco-detail-skeleton" aria-hidden="true">' +

        '<div class="ui-skeleton-line"></div>' +

        '<div class="ui-skeleton-line ui-skeleton-line--short"></div>' +

      '</div>'

    );

  }



  function overlapWarningsHtml(legacyHost) {

    if (!legacyHost) return '';

    var cards = [];

    legacyHost.querySelectorAll('.warning-critical, .warning-caution, .warning-info').forEach(function (el) {

      if (el.getAttribute('aria-label') === '医師の受診が必要な場合') return;

      if (isPersonalizedAdviceWarning(el)) return;

      var severity = el.classList.contains('warning-critical') ? 'danger'

        : el.classList.contains('warning-caution') ? 'warn' : 'info';

      var title = el.getAttribute('aria-label') || '';

      var h4 = el.querySelector('h4');

      if (h4) title = h4.textContent.replace(/^[\S]+\s*/, '').trim();

      var lines = [];

      el.querySelectorAll('li').forEach(function (li) {

        var line = li.textContent.trim();

        if (line) lines.push(line);

      });

      if (!lines.length) {

        var p = el.querySelector('p');

        if (p && p.textContent.trim()) lines.push(p.textContent.trim());

      }

      if (!lines.length) return;

      var badge = severity === 'danger' ? '重複禁止' : severity === 'warn' ? '注意' : '情報';

      var rows = lines.map(function (line) {

        var parsed = parseOverlapLine(line);

        return (

          '<div class="ui-overlap-row">' +

            (parsed.ingredient

              ? '<span class="ui-overlap-row__ingredient">' + esc(parsed.ingredient) + '</span>'

              : '') +

            '<span class="ui-overlap-row__meds">' + esc(parsed.meds) + '</span>' +

            (parsed.note

              ? '<span class="ui-overlap-row__note">' + esc(parsed.note) + '</span>'

              : '') +

          '</div>'

        );

      }).join('');

      cards.push(

        '<div class="ui-overlap-card ui-overlap-card--' + severity + '">' +

          '<div class="ui-overlap-card__head">' +

            '<span class="ui-overlap-card__badge">' + esc(badge) + '</span>' +

            '<span class="ui-overlap-card__title">' + esc(title) + '</span>' +

          '</div>' +

          '<div class="ui-overlap-card__body">' + rows + '</div>' +

        '</div>'

      );

    });

    if (!cards.length) return '';

    return (

      '<div class="ui-reco-cautions" role="region" aria-label="' + esc(t('overlapCautions')) + '">' +

        cards.join('') +

      '</div>'

    );

  }



  function isAncillaryUsageSection(label) {

    if (!label || label === '症状分析結果' || label === '使用上の注意') return false;

    if (/^\d+つ目/.test(label)) return false;

    if (label.indexOf('使ってはいけない') >= 0) return false;

    if (label.indexOf('服用時の注意') >= 0) return false;

    if (label.indexOf('OTC') >= 0) return false;

    if (label.indexOf('ドーピング') >= 0) return false;

    return true;

  }



  function ancillaryCollapsiblesHtml(legacyHost) {

    if (!legacyHost) return '';

    var sections = Array.prototype.slice.call(legacyHost.querySelectorAll('.collapsible-section'));

    if (!sections.length) return '';

    var html = '';

    sections.forEach(function (sec) {

      var label = sec.getAttribute('aria-label') || '';

      if (!isAncillaryUsageSection(label)) return;

      var toggle = sec.querySelector('.collapse-toggle');

      var title = label;

      if (toggle) {

        title = toggle.textContent.replace(/▼/g, '').replace(/\s+/g, ' ').trim();

      }

      var contentHtml = getCollapsibleContentHtml(sec);

      if (!contentHtml.trim()) return;

      var expanded = sec.getAttribute('data-default-expanded') === 'true';

      html +=

        '<div class="ui-sage-collapse collapsible-section" data-collapsible="true" data-default-expanded="' + (expanded ? 'true' : 'false') + '" role="region" aria-label="' + esc(label) + '">' +

          '<button type="button" class="ui-sage-collapse__toggle collapse-toggle" aria-expanded="' + (expanded ? 'true' : 'false') + '">' +

            '<span class="collapse-icon ui-sage-collapse__icon">▼</span>' +

            '<span class="ui-sage-collapse__title">' + esc(title) + '</span>' +

          '</button>' +

          '<div class="ui-sage-collapse__body collapse-content">' + contentHtml + '</div>' +

        '</div>';

    });

    return html ? '<div class="ui-reco-usage">' + html + '</div>' : '';

  }



  function buildAncillarySageHtml(legacyHost, diag) {

    return (

      doctorWarningHtml(legacyHost, diag) +

      followupQuestionsHtml(diag, legacyHost) +

      ancillaryCollapsiblesHtml(legacyHost)

    );

  }



  function alertsHtml(diag, options) {

    if (!diag || (options && options.skipDoctor)) return '';

    var parts = [];

    if (diag.severity_escalation) {

      parts.push(

        '<div class="ui-alert ui-alert--danger"><strong>⚠️</strong><br>' +

          esc(stripHtmlText(diag.severity_escalation)) + '</div>'

      );

    }

    if (diag.influenza_risk && diag.influenza_reason) {

      parts.push(

        '<div class="ui-alert ui-alert--warn"><strong>⚠️ ' + esc(t('influenzaTitle')) + '</strong><br>' +

          esc(diag.influenza_reason) + '</div>'

      );

    }

    return parts.join('');

  }



  function extractAdviceFromLegacy(legacyHost) {

    if (!legacyHost) return '';

    var el = legacyHost.querySelector('.warning-info p, .streaming-personalized-advice, .ui-personal-advice__text');

    return el ? el.textContent.trim() : '';

  }



  function buildRecoBlockHtml(diag, options) {

    options = options || {};

    var meds = diag.recommended_medicines || [];

    var symptoms = symptomNameList(diag);

    if (!symptoms.length) {

      symptoms = symptomsFromMedicines(meds);

    }

    var usageSections = options.usageSections || usageSectionsFromDiagnosis(diag);

    var overlapHtml = overlapWarningsFromDiagnosis(diag);

    var errorHtml = errorAlertHtml(diag);

    var block = (

      '<div class="ui-reco-block ui-reco-block--pro">' +

        symptomIntroHtml(symptoms) +

        personalizedAdviceHtml(diag, options.adviceText || (diag && diag.personalized_advice)) +

        overlapHtml +

        (errorHtml && !meds.length ? errorHtml : renderMedicinesBlock(meds, { usageSections: usageSections })) +

        (errorHtml && meds.length ? errorHtml : '') +

        alertsHtml(diag, { skipDoctor: !!(diag && diag.doctor_consultation) }) +

        doctorWarningHtml(null, diag) +

        followupQuestionsHtml(diag, null) +

        (options.detailPending ? buildUsageSectionsSkeletonHtml() : '') +

        resolveFeedbackBlockHtml(diag, options) +

        (options.voiceHtml || buildStandardVoiceHtml()) +

      '</div>'

    );

    return block;

  }



  function buildRecoBlockFromDiagnosis(diag, options) {

    return buildRecoBlockHtml(diag, options);

  }



  function mergeRecoDetail(root, detail) {

    if (!root || !detail || !detail.usage_sections) return false;

    var bubble = root.querySelector('.ui-bubble--reco') || root;

    var skeleton = bubble.querySelector('.ui-reco-detail-skeleton');

    if (skeleton) skeleton.remove();

    var block = bubble.querySelector('.ui-reco-block');

    if (!block) return false;

    var diag = { usage_sections: detail.usage_sections, recommended_medicines: detail.recommended_medicines || [] };

    var usageHost = block.querySelector('.ui-reco-usage');

    var usageHtml = buildAncillaryUsageFromDiagnosis(diag);

    if (usageHtml) {

      if (usageHost) {

        usageHost.outerHTML = usageHtml;

      } else {

        var feedback = block.querySelector('.ui-reco-feedback');

        if (feedback) {

          feedback.insertAdjacentHTML('beforebegin', usageHtml);

        } else {

          block.insertAdjacentHTML('beforeend', usageHtml);

        }

      }

    }

    bindRendered(root);

    return true;

  }



  function buildAncillaryUsageFromDiagnosis(diag) {

    var sections = usageSectionsFromDiagnosis(diag);

    if (!sections.shared.length && !Object.keys(sections.perMedicine).length) return '';

    var html = '';

    sections.shared.forEach(function (sec) {

      html += '<div class="ui-sage-collapse collapsible-section"><div class="ui-sage-collapse__body">' + sec.contentHtml + '</div></div>';

    });

    return html ? '<div class="ui-reco-usage">' + html + '</div>' : '';

  }



  function hasSageRecoRenderableContent(diag, options) {

    if (!isDiagnosisPayload(diag)) return false;

    return true;

  }



  function buildSageRecoBubbleHtml(diag, options) {

    options = options || {};

    if (!options.force && !isSageUi()) return null;

    if (!hasSageRecoRenderableContent(diag, options)) return null;

    diag = applyDiagnosisI18n(diag);

    return '<div class="ui-bubble ui-bubble--reco">' + buildRecoBlockHtml(diag, options) + '</div>';

  }



  function mountSageRecommendation(messageDiv, message, options) {

    if (!messageDiv || !isSageUi()) return false;

    options = options || {};

    var diag = applyDiagnosisI18n(message && message.diagnosis);

    if (!isDiagnosisPayload(diag)) return false;

    var mountFingerprint = options.mountFingerprint || '';
    if (
      mountFingerprint
      && messageDiv.__sageMountFingerprint === mountFingerprint
      && messageDiv.querySelector('.ui-bubble--reco')
    ) {
      return false;
    }

    var bubbleOpts = {

      adviceText: options.adviceText || diag.personalized_advice,

      feedbackHtml: options.feedbackHtml || buildStandardFeedbackHtml(),

      voiceHtml: options.voiceHtml || buildStandardVoiceHtml(),

      detailPending: options.detailPending

    };

    var html = buildSageRecoBubbleHtml(diag, bubbleOpts);

    if (!html) return false;



    messageDiv.innerHTML = html;

    messageDiv.classList.add('message--sage-reco');
    messageDiv.__messageDiagnosis = diag;
    if (mountFingerprint) {
      messageDiv.__sageMountFingerprint = mountFingerprint;
    }

    bindRendered(messageDiv);

    var symptomList = symptomNameList(diag);

    if (!symptomList.length) {

      symptomList = symptomsFromMedicines(diag.recommended_medicines || []);

    }

    if (global.SageShell && symptomList.length) {

      global.SageShell.updateHeaderSymptoms(symptomList);

    }

    return true;

  }



  function buildStreamingSageSkeletonHtml() {

    return (

      '<div class="ui-bubble ui-bubble--reco" data-streaming-sage-reco="true">' +

        '<div class="ui-reco-block ui-reco-block--pro" data-streaming-skeleton="true">' +

          '<div class="ui-personal-advice streaming-advice-section" role="note">' +

            '<div class="ui-personal-advice__head">' +

              '<svg class="ui-personal-advice__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true">' +

                '<path d="M12 3l8 4v5c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V7l8-4z"/>' +

              '</svg>' +

              '<h4 class="ui-personal-advice__title">' + esc(t('personalAdviceTitle')) + '</h4>' +

            '</div>' +

            '<p class="ui-personal-advice__text streaming-personalized-advice"></p>' +

          '</div>' +

          '<div class="streaming-medicines-container"></div>' +

        '</div>' +

      '</div>'

    );

  }



  function updateStreamingSageReco(wrapper, medicines, options) {

    if (!wrapper || !isSageUi() || !medicines || !medicines.length) return false;

    options = options || {};

    var block = wrapper.querySelector('.ui-reco-block');

    if (!block) return false;

    var adviceEl = block.querySelector('.streaming-personalized-advice');

    var adviceText = adviceEl ? adviceEl.textContent.trim() : '';

    var diag = {

      recommended_medicines: medicines,

      symptoms: options.symptoms || symptomsFromMedicines(medicines),

      doctor_consultation: options.doctor_consultation || '',

      influenza_risk: options.influenza_risk,

      influenza_reason: options.influenza_reason || ''

    };

    var inner = buildRecoBlockHtml(diag, { adviceText: adviceText });

    var newBlock = document.createElement('div');

    newBlock.innerHTML = inner;

    var replacement = newBlock.firstElementChild;

    if (!replacement) return false;

    block.replaceWith(replacement);

    bindRendered(wrapper);

    wrapper.classList.add('has-medicines');

    return true;

  }



  function bindRendered(root) {

    root = root || document;

    if (global.MedicineCarousel) global.MedicineCarousel.bindCarousels(root);

    if (global.MedicineCard) global.MedicineCard.bindCardInteractions(root);

  }



  function renderMedicinesSection(medicines) {

    if (!medicines || !medicines.length || !isSageUi()) return null;

    return renderMedicinesCarousel(medicines);

  }



  function buildRecommendationMedicinesHtml(medicines) {

    return renderMedicinesSection(medicines);

  }



  function patchStreamingContainer(container, medicines) {

    if (!container || !isSageUi()) return false;

    var wrapper = container.closest('[data-streaming-recommendation="true"]') || container;

    if (wrapper.querySelector('[data-streaming-sage-reco]')) {

      return updateStreamingSageReco(wrapper, medicines);

    }

    var html = renderMedicinesSection(medicines);

    if (!html) return false;

    var host = container.querySelector ? container.querySelector('.streaming-medicines-container') : null;

    if (!host) return false;

    host.innerHTML = html;

    bindRendered(host);

    return true;

  }



  global.RecommendationRenderer = {

    isSageUi: isSageUi,

    symptomNameList: symptomNameList,

    renderMedicinesCarousel: renderMedicinesCarousel,

    renderMedicinesSection: renderMedicinesSection,

    buildRecoBlockHtml: buildRecoBlockHtml,

    buildRecoBlockFromDiagnosis: buildRecoBlockFromDiagnosis,

    buildSageRecoBubbleHtml: buildSageRecoBubbleHtml,

    mountSageRecommendation: mountSageRecommendation,

    mergeRecoDetail: mergeRecoDetail,

    buildStreamingSageSkeletonHtml: buildStreamingSageSkeletonHtml,

    updateStreamingSageReco: updateStreamingSageReco,

    bindRendered: bindRendered,

    patchStreamingContainer: patchStreamingContainer,

    buildStandardFeedbackHtml: buildStandardFeedbackHtml,

    buildFeedbackThanksHtml: buildFeedbackThanksHtml,

    applyDiagnosisI18n: applyDiagnosisI18n

  };

})(typeof window !== 'undefined' ? window : globalThis);


