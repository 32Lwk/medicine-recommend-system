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



  function renderMedicinesCarousel(medicines) {

    if (!global.MedicineMapper || !global.MedicineCard || !global.MedicineCarousel) {

      return '';

    }

    var mapped = global.MedicineMapper.mapMedicines(medicines);

    if (!mapped.length) return '';

    var cards = mapped.map(function (m) {

      return global.MedicineCard.cardHtmlPro(m);

    }).join('');

    return global.MedicineCarousel.carouselBlockHtml(cards, mapped.length, 'pro');

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

      var consult = stripHtmlText(diag.doctor_consultation);

      if (consult) {

        return (

          '<div class="ui-alert ui-alert--danger ui-reco-doctor">' +

            '<strong>🏥 ' + esc(t('doctorConsultTitle')) + '</strong><br>' + esc(consult) +

          '</div>'

        );

      }

    }

    return '';

  }



  function overlapWarningsHtml(legacyHost) {

    if (!legacyHost) return '';

    var html = '';

    legacyHost.querySelectorAll('.warning-critical, .warning-caution, .warning-info').forEach(function (el) {

      if (el.getAttribute('aria-label') === '医師の受診が必要な場合') return;

      var cls = 'ui-alert--info';

      if (el.classList.contains('warning-critical')) cls = 'ui-alert--danger';

      else if (el.classList.contains('warning-caution')) cls = 'ui-alert--warn';

      var clone = el.cloneNode(true);

      clone.removeAttribute('style');

      clone.className = 'ui-alert ' + cls + ' ui-reco-overlap';

      clone.querySelectorAll('[style]').forEach(function (node) { node.removeAttribute('style'); });

      html += clone.outerHTML;

    });

    return html;

  }



  function usageSectionSortKey(label) {
    if (!label) return 900;
    var rankMatch = label.match(/(\d+)つ目/);
    if (rankMatch) return parseInt(rankMatch[1], 10);
    if (label.indexOf('OTC') >= 0) return 20;
    if (label.indexOf('使ってはいけない') >= 0) return 30;
    if (label.indexOf('服用時の注意') >= 0) return 40;
    if (label.indexOf('ドーピング') >= 0) return 50;
    return 60;
  }

  function usageCollapsiblesHtml(legacyHost) {

    if (!legacyHost) return '';

    var sections = Array.prototype.slice.call(legacyHost.querySelectorAll('.collapsible-section'));

    if (!sections.length) return '';

    sections.sort(function (a, b) {
      var la = a.getAttribute('aria-label') || '';
      var lb = b.getAttribute('aria-label') || '';
      return usageSectionSortKey(la) - usageSectionSortKey(lb);
    });

    var html = '';

    sections.forEach(function (sec) {

      var label = sec.getAttribute('aria-label') || '';

      if (label === '症状分析結果') return;

      var toggle = sec.querySelector('.collapse-toggle');

      var title = label;

      if (toggle) {

        title = toggle.textContent.replace(/▼/g, '').replace(/\s+/g, ' ').trim();

      }

      var content = sec.querySelector('.collapse-content');

      var expanded = sec.getAttribute('data-default-expanded') === 'true';

      var contentHtml = content ? content.innerHTML : '';

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

      overlapWarningsHtml(legacyHost) +

      usageCollapsiblesHtml(legacyHost)

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

    var legacyHost = options.legacyHost || null;

    var hasLegacyDoctor = !!(legacyHost && legacyHost.querySelector('.warning-critical[aria-label="医師の受診が必要な場合"]'));

    return (

      '<div class="ui-reco-block ui-reco-block--pro">' +

        symptomIntroHtml(symptoms) +

        personalizedAdviceHtml(diag, options.adviceText) +

        renderMedicinesCarousel(meds) +

        alertsHtml(diag, { skipDoctor: hasLegacyDoctor }) +

        buildAncillarySageHtml(legacyHost, diag) +

        (options.feedbackHtml || '') +

        (options.voiceHtml || '') +

      '</div>'

    );

  }



  function buildSageRecoBubbleHtml(diag, options) {

    if (!isSageUi() || !isDiagnosisPayload(diag)) return null;

    var meds = diag.recommended_medicines;

    if (!meds || !meds.length) return null;

    return '<div class="ui-bubble ui-bubble--reco">' + buildRecoBlockHtml(diag, options) + '</div>';

  }



  function mountSageRecommendation(messageDiv, message, options) {

    if (!messageDiv || !isSageUi()) return false;

    options = options || {};

    var diag = message && message.diagnosis;

    if (!isDiagnosisPayload(diag)) return false;

    var meds = diag.recommended_medicines;

    if (!meds || !meds.length) return false;



    var legacyHost = options.legacyHost || messageDiv.querySelector('.recommendation-result');

    var adviceText = options.adviceText || extractAdviceFromLegacy(legacyHost);

    var feedbackEl = legacyHost && legacyHost.querySelector('.feedback-buttons');

    var voiceEl = legacyHost && legacyHost.querySelector('#voice-read-container-inline');



    var bubbleOpts = {

      legacyHost: legacyHost,

      adviceText: adviceText,

      feedbackHtml: feedbackHtmlFromLegacy(feedbackEl),

      voiceHtml: voiceHtmlFromLegacy(voiceEl)

    };

    var html = buildSageRecoBubbleHtml(diag, bubbleOpts);

    if (!html) return false;



    messageDiv.innerHTML = html;

    messageDiv.classList.add('message--sage-reco');

    bindRendered(messageDiv);

    var symptomList = symptomNameList(diag);

    if (!symptomList.length) {

      symptomList = symptomsFromMedicines(meds);

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

    buildSageRecoBubbleHtml: buildSageRecoBubbleHtml,

    mountSageRecommendation: mountSageRecommendation,

    buildStreamingSageSkeletonHtml: buildStreamingSageSkeletonHtml,

    updateStreamingSageReco: updateStreamingSageReco,

    bindRendered: bindRendered,

    patchStreamingContainer: patchStreamingContainer,

    buildRecommendationMedicinesHtml: buildRecommendationMedicinesHtml

  };

})(typeof window !== 'undefined' ? window : globalThis);


