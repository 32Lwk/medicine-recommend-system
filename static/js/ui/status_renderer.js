/**
 * Status block renderer — Sage Terrace ui-bubble--status
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

  var PLAIN_LAYOUT_KINDS = {
    concierge_greeting: true,
    concierge_thanks: true,
    concierge_chitchat: true
  };

  var COMPACT_LAYOUT_KINDS = {
    user_info_registration: true,
    attribute_update_confirmation: true
  };

  function isPlainLayout(diag) {
    if (!diag) return false;
    if (isCompactLayout(diag)) return false;
    if (diag.layout === 'plain') return true;
    if (diag.layout === 'card') return false;
    var kind = diag.kind || '';
    if (PLAIN_LAYOUT_KINDS[kind]) return true;
    if (/^concierge_/.test(kind)) {
      var hasSections = diag.sections && diag.sections.length;
      var hasHints = diag.hints && diag.hints.length;
      var hasSubtitle = !!(diag.subtitle && String(diag.subtitle).trim());
      return !hasSections && !hasHints && !hasSubtitle;
    }
    return false;
  }

  function isCompactLayout(diag) {
    if (!diag) return false;
    return !!COMPACT_LAYOUT_KINDS[diag.kind || ''];
  }

  function collectSectionItems(diag) {
    var items = [];
    (diag.sections || []).forEach(function (sec) {
      (sec.items || []).forEach(function (item) {
        if (item) items.push(String(item));
      });
    });
    return items;
  }

  function parseCompactStatusItem(text) {
    var raw = String(text || '').trim();
    if (!raw) return { key: '', value: '', meta: '' };
    var meta = '';
    var metaMatch = raw.match(/（([^）]+)）\s*$/);
    if (metaMatch) {
      meta = metaMatch[1];
      raw = raw.slice(0, metaMatch.index).trim();
    }
    var colon = raw.indexOf(':');
    if (colon === -1) colon = raw.indexOf('：');
    if (colon !== -1) {
      return {
        key: raw.slice(0, colon).trim(),
        value: raw.slice(colon + 1).trim(),
        meta: meta
      };
    }
    return { key: '', value: raw, meta: meta };
  }

  function compactItemRowHtml(item) {
    var parsed = parseCompactStatusItem(item);
    var keyHtml = parsed.key
      ? '<span class="ui-status-compact__key">' + esc(parsed.key) + '</span>'
      : '';
    var metaHtml = parsed.meta
      ? '<span class="ui-status-compact__meta">' + esc(parsed.meta) + '</span>'
      : '';
    return (
      '<li class="ui-status-compact__row">' +
        keyHtml +
        '<span class="ui-status-compact__val">' + esc(parsed.value || item) + '</span>' +
        metaHtml +
      '</li>'
    );
  }

  function compactItemsHtml(diag) {
    var items = collectSectionItems(diag);
    if (!items.length) return '';
    return (
      '<ul class="ui-status-compact__rows">' +
        items.map(compactItemRowHtml).join('') +
      '</ul>'
    );
  }

  function compactHintHtml(hints, variant) {
    if (!hints || !hints.length) return '';
    var text = String(hints[0] || '');
    if ((variant || 'notice') === 'notice' && !/エラー|注意|控え|受診|問題/.test(text)) {
      return '';
    }
    var alertClass = variantAlertClass(variant || 'notice');
    return (
      '<p class="ui-status-compact__hint ui-alert ' + alertClass + '" role="note">' +
        esc(text) +
      '</p>'
    );
  }

  function buildCompactStatusBlockHtml(diag) {
    var variant = diag.variant || 'notice';
    var render = diag.render || 'sage_status';
    var title = cleanStatusText(diag.title || '');
    var lead = cleanStatusText(diag.subtitle || diag.message || '');
    var icon = statusIconSvg(variant, render).replace(
      'ui-status-hero__icon',
      'ui-status-compact__icon'
    );
    return (
      '<div class="ui-status-block ui-status-block--pro ui-status-block--compact ui-status-block--' + esc(variant) + '">' +
        '<div class="ui-status-compact">' +
          '<div class="ui-status-compact__head">' +
            icon +
            '<div class="ui-status-compact__titles">' +
              (title ? '<span class="ui-status-compact__title">' + esc(title) + '</span>' : '') +
              (lead ? '<span class="ui-status-compact__lead">' + esc(lead) + '</span>' : '') +
            '</div>' +
          '</div>' +
          compactItemsHtml(diag) +
          compactHintHtml(diag.hints, variant) +
        '</div>' +
      '</div>'
    );
  }

  function statusIconSvg(variant, render) {
    if (render === 'sage_qa') {
      return (
        '<svg class="ui-status-hero__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true">' +
          '<path d="M8 10h8M8 14h5M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>' +
        '</svg>'
      );
    }
    if (variant === 'critical' || variant === 'error' || variant === 'security') {
      return (
        '<svg class="ui-status-hero__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true">' +
          '<path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>' +
        '</svg>'
      );
    }
    if (variant === 'caution') {
      return (
        '<svg class="ui-status-hero__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true">' +
          '<path d="M12 8v4m0 4h.01M12 3l9 16H3L12 3z"/>' +
        '</svg>'
      );
    }
    return (
      '<svg class="ui-status-hero__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" aria-hidden="true">' +
        '<path d="M12 3l8 4v5c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V7l8-4z"/>' +
      '</svg>'
    );
  }

  function cleanStatusText(text) {
    if (!text) return '';
    return String(text)
      .replace(/^[\s⚠️❗️‼️]+/u, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  function variantOverlapSeverity(variant) {
    if (variant === 'critical' || variant === 'error' || variant === 'security') return 'danger';
    if (variant === 'caution') return 'warn';
    return 'info';
  }

  function variantAlertClass(variant) {
    var sev = variantOverlapSeverity(variant);
    if (sev === 'danger') return 'ui-alert--danger';
    if (sev === 'warn') return 'ui-alert--warn';
    return 'ui-alert--info';
  }

  function getRuntimeClientConfig() {
    try {
      var cfgEl = typeof document !== 'undefined' ? document.getElementById('app-runtime-config') : null;
      if (cfgEl && cfgEl.textContent) {
        return JSON.parse(cfgEl.textContent.trim());
      }
    } catch (e) {
      // fall through
    }
    return null;
  }

  function buildGitCommitBrowseUrl(repoUrl, commit) {
    if (!repoUrl || !commit) return null;
    var base = String(repoUrl).trim().replace(/\/+$/, '');
    try {
      var host = new URL(base).hostname.toLowerCase();
      if (host === 'gitlab.com' || host.endsWith('.gitlab.com')) {
        return base + '/-/commit/' + commit;
      }
    } catch (e) {
      // fall through
    }
    return base + '/commit/' + commit;
  }

  function resolveCommitBrowseUrl(commit) {
    if (!commit) return null;
    var cfg = getRuntimeClientConfig() || {};
    var direct = typeof cfg.gitCommitUrl === 'string' ? cfg.gitCommitUrl.trim() : '';
    if (direct && /gitlab\.com/i.test(direct)) return direct;
    var repo = typeof cfg.gitRepoUrl === 'string' ? cfg.gitRepoUrl.trim() : '';
    if (repo) return buildGitCommitBrowseUrl(repo, commit);
    return buildGitCommitBrowseUrl('https://gitlab.com/blank2703726/medicine-recommend', commit);
  }

  function sectionCommitHtml(commit) {
    var hash = String(commit || '').trim().slice(0, 7);
    if (!/^[0-9a-f]{7}$/i.test(hash)) return '';
    var commitLabel = t('onboardingCommitLabel') || 'Commit';
    var commitUrl = resolveCommitBrowseUrl(hash);
    if (commitUrl) {
      return (
        '<a href="' + esc(commitUrl) + '" class="ui-overlap-card__commit onboarding-last-updated-commit" target="_blank" rel="noopener noreferrer" aria-label="' + esc(commitLabel) + ' ' + esc(hash) + '">' +
          '<code class="onboarding-commit-hash">' + esc(hash) + '</code>' +
        '</a>'
      );
    }
    return (
      '<span class="ui-overlap-card__commit onboarding-last-updated-commit" aria-label="' + esc(commitLabel) + ' ' + esc(hash) + '">' +
        '<code class="onboarding-commit-hash">' + esc(hash) + '</code>' +
      '</span>'
    );
  }

  function changelogDeployMetaHtml(subtitle) {
    var raw = cleanStatusText(subtitle || '');
    if (!raw) return '';
    var datePart = '';
    var dateMatch = raw.match(/最終更新日\s+(.+)/);
    if (dateMatch) {
      datePart = String(dateMatch[1] || '').trim();
    }
    if (!datePart) return '';
    var label = t('onboardingLastUpdatedLabel') || '最終更新日';
    return (
      '<p class="ui-status-last-updated onboarding-last-updated">' +
        '<span class="onboarding-last-updated-main">' +
          '<span class="onboarding-last-updated-label">' + esc(label) + '</span> ' +
          esc(datePart) +
        '</span>' +
      '</p>'
    );
  }

  function sectionBadgeLabel(variant, title, kind) {
    if (kind === 'concierge_doc_changelog') return t('statusBadgeUpdate') || '更新';
    if (/^\d{4}年\d{1,2}月\d{1,2}日/.test(title || '')) return t('statusBadgeUpdate') || '更新';
    if (/医師|受診|相談/.test(title || '')) return t('statusBadgeConsult') || '受診';
    if (/詳細|案内/.test(title || '')) return t('statusBadgeInfo') || '案内';
    if (variant === 'critical' || variant === 'error') return t('statusBadgeImportant') || '重要';
    if (variant === 'caution') return t('statusBadgeCaution') || '注意';
    return t('statusBadgeNote') || '補足';
  }

  function formatAgentRoleListItem(item) {
    var text = String(item || '').trim().replace(/^・+/, '');
    var match = text.match(/^([A-Za-z][A-Za-z0-9]*(?:Agent|Orchestrator|Manager|Router))\s*[：:]\s*(.+)$/);
    if (match) {
      return (
        '<li class="ui-agent-role-item">' +
          '<span class="ui-agent-role-item__name">' + esc(match[1]) + '</span>' +
          '<span class="ui-agent-role-item__desc">' + esc(match[2].trim()) + '</span>' +
        '</li>'
      );
    }
    return '<li>' + esc(text) + '</li>';
  }

  function sectionsHtml(sections, variant, kind) {
    if (!sections || !sections.length) return '';
    var sev = variantOverlapSeverity(variant || 'notice');
    return (
      '<div class="ui-status-sections">' +
        sections.map(function (sec) {
          var title = sec.title || '';
          var body = sec.html
            ? sec.html
            : (sec.items || []).map(function (item) {
              if (/Agent|Orchestrator|Manager|Router/.test(String(item || ''))) {
                return formatAgentRoleListItem(item);
              }
              return '<li>' + esc(item) + '</li>';
            }).join('');
          if (!sec.html && body) {
            body = '<ul class="ui-followup-list ui-status-section__list">' + body + '</ul>';
          }
          if (!body) return '';
          return (
            '<div class="ui-overlap-card ui-overlap-card--' + esc(sev) + ' ui-status-section-card">' +
              '<div class="ui-overlap-card__head">' +
                '<span class="ui-overlap-card__badge">' + esc(sectionBadgeLabel(variant, title, kind)) + '</span>' +
                '<span class="ui-overlap-card__title">' + esc(title) + '</span>' +
                (kind === 'concierge_doc_changelog' ? sectionCommitHtml(sec.commit) : '') +
              '</div>' +
              '<div class="ui-overlap-card__body">' + body + '</div>' +
            '</div>'
          );
        }).join('') +
      '</div>'
    );
  }

  function hintsHtml(hints, variant) {
    if (!hints || !hints.length) return '';
    var alertClass = variantAlertClass(variant || 'notice');
    return (
      '<div class="ui-alert ' + alertClass + ' ui-status-hints-card" role="note">' +
        '<strong>' + esc(t('statusHintsTitle') || '次に試すこと') + '</strong>' +
        '<ul class="ui-followup-list">' +
          hints.map(function (h) { return '<li>' + esc(h) + '</li>'; }).join('') +
        '</ul>' +
      '</div>'
    );
  }

  function actionsHtml(actions) {
    if (!actions || !actions.length) return '';
    return (
      '<div class="ui-status-actions">' +
        actions.map(function (act) {
          if (act.postback_text) {
            return (
              '<button type="button" class="ui-btn ui-btn--secondary ui-status-chip"' +
                ' data-postback-text="' + esc(act.postback_text) + '"' +
                ' data-status-action="' + esc(act.id) + '">' + esc(act.label) + '</button>'
            );
          }
          var onclick = act.action ? ' onclick="' + esc(act.action) + '"' : '';
          return (
            '<button type="button" class="ui-btn ui-btn--primary"' + onclick +
              ' data-status-action="' + esc(act.id) + '">' + esc(act.label) + '</button>'
          );
        }).join('') +
      '</div>'
    );
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

  function feedbackHtml(diag) {
    if (diag && diag.feedback_completed) {
      return buildFeedbackThanksHtml();
    }
    if (!diag || diag.show_feedback === false) return '';
    var qKey = diag.render === 'sage_reco' ? 'feedbackQuestionShort' : 'feedbackQuestionShort';
    return buildCompactFeedbackHtml(qKey);
  }

  function statusIntroHtml(diag, variant, render) {
    var title = cleanStatusText(diag.title || '');
    if (!title) return '';
    return (
      '<div class="ui-reco-intro ui-status-intro recommendation-intro">' +
        statusIconSvg(variant, render).replace('ui-status-hero__icon', 'ui-reco-intro-icon ui-status-intro__icon') +
        '<span class="ui-status-intro__title">' + esc(title) + '</span>' +
      '</div>'
    );
  }

  function isAbsoluteBlockStatus(diag) {
    return !!(diag && diag.kind === 'absolute_block');
  }

  function statusMessagePlainHtml(diag) {
    var message = cleanStatusText(diag.message || '');
    if (!message) return '';
    return (
      '<p class="ui-status-message ui-status-message--plain">' +
        esc(message).replace(/\n/g, '<br>') +
      '</p>'
    );
  }

  function statusAdviceHtml(diag) {
    if (isAbsoluteBlockStatus(diag)) {
      return statusMessagePlainHtml(diag);
    }
    var isChangelog = diag && diag.kind === 'concierge_doc_changelog';
    var subtitle = cleanStatusText(diag.subtitle || '');
    var message = cleanStatusText(diag.message || '');
    if (!subtitle && !message) return '';
    var bodyParts = [];
    if (message) {
      var paras = message.split(/\n\n+/).filter(function (p) { return p.trim(); });
      if (!paras.length) {
        paras = [message];
      }
      paras.forEach(function (para) {
        bodyParts.push(
          '<p class="ui-status-advice__text">' +
            esc(para.trim()).replace(/\n/g, '<br>') +
          '</p>'
        );
      });
    }
    if (isChangelog && subtitle) {
      bodyParts.push(changelogDeployMetaHtml(subtitle));
    } else if (subtitle) {
      bodyParts.unshift('<p class="ui-status-advice__lead">' + esc(subtitle) + '</p>');
    }
    return bodyParts.join('');
  }

  function buildStatusBlockHtml(diag) {
    if (!diag) return '';
    if (isCompactLayout(diag)) {
      return buildCompactStatusBlockHtml(diag);
    }
    var variant = diag.variant || 'notice';
    var render = diag.render || 'sage_status';
    return (
      '<div class="ui-status-block ui-status-block--pro ui-status-block--' + esc(variant) + '">' +
        statusIntroHtml(diag, variant, render) +
        statusAdviceHtml(diag) +
        sectionsHtml(diag.sections, variant, diag.kind) +
        hintsHtml(diag.hints, variant) +
        actionsHtml(diag.actions) +
        feedbackHtml(diag) +
      '</div>'
    );
  }

  function resolveDiagnosis(diag) {
    if (global.UiStrings && global.UiStrings.applyDiagnosisI18n) {
      return global.UiStrings.applyDiagnosisI18n(diag);
    }
    if (global.RecommendationRenderer && global.RecommendationRenderer.applyDiagnosisI18n) {
      return global.RecommendationRenderer.applyDiagnosisI18n(diag);
    }
    return diag;
  }

  function buildPlainChatBubbleHtml(diag) {
    var text = cleanStatusText(diag.message || '');
    if (!text) return '';
    return (
      '<div class="ui-bubble ui-bubble--chat ui-bubble--status-plain">' +
        '<p class="ui-chat-plain__text">' + esc(text).replace(/\n/g, '<br>') + '</p>' +
      '</div>'
    );
  }

  function buildSageStatusBubbleHtml(diag) {
    if (!isSageUi() || !diag) return null;
    diag = resolveDiagnosis(diag);
    if (isPlainLayout(diag)) {
      return buildPlainChatBubbleHtml(diag);
    }
    var render = diag.render || 'sage_status';
    var bubbleClass = render === 'sage_qa' ? 'ui-bubble--qa' : 'ui-bubble--status';
    return '<div class="ui-bubble ' + bubbleClass + '">' + buildStatusBlockHtml(diag) + '</div>';
  }

  function mountSageStatus(messageDiv, message, options) {
    options = options || {};
    if (!messageDiv || !isSageUi() || !message || !message.diagnosis) return false;
    var diag = resolveDiagnosis(message.diagnosis);
    if (diag.render !== 'sage_status' && diag.render !== 'sage_qa') return false;
    var mountFingerprint = options.mountFingerprint || '';
    var bubbleSelector = diag.render === 'sage_qa' ? '.ui-bubble--qa' : '.ui-bubble--status';
    if (
      mountFingerprint
      && messageDiv.__sageMountFingerprint === mountFingerprint
      && messageDiv.querySelector(bubbleSelector)
    ) {
      return false;
    }
    var html = buildSageStatusBubbleHtml(diag);
    if (!html) return false;
    messageDiv.innerHTML = html;
    messageDiv.classList.add(isPlainLayout(diag) ? 'message--sage-chat' : 'message--sage-status');
    messageDiv.__messageDiagnosis = diag;
    if (mountFingerprint) {
      messageDiv.__sageMountFingerprint = mountFingerprint;
    }
    return true;
  }

  global.StatusRenderer = {
    isSageUi: isSageUi,
    isPlainLayout: isPlainLayout,
    isCompactLayout: isCompactLayout,
    buildStatusBlockHtml: buildStatusBlockHtml,
    buildSageStatusBubbleHtml: buildSageStatusBubbleHtml,
    mountSageStatus: mountSageStatus
  };
})(typeof window !== 'undefined' ? window : globalThis);
