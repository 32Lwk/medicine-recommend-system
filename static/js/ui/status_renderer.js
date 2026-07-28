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

  /** DOM 再描画スキップ時も chrome 更新を検知する（フィードバック 🔊・余白・リストドット） */
  var SAGE_STATUS_CHROME_VERSION = '10';

  var CHANGELOG_DEV_INTRO_RE = /PMDA|正本|品質フィルタ|quality_filter|ingestion job|data\/pmda|CHANGELOG|doc_changelog|build-meta|CodeBuild|Bedrock ingestion|§\d|reparse_from_raw|live fetch|開発者向け|developer.?facing|画面の[「『]?最近の更新|反映精度|見やすい表示に整え|案内の流れも、より安心/i;

  function isChangelogKind(kind) {
    return kind === 'concierge_doc_changelog' || kind === 'doc_changelog';
  }

  function sanitizeChangelogIntroText(message) {
    var text = cleanStatusText(message || '');
    if (!text) return '';
    if (!CHANGELOG_DEV_INTRO_RE.test(text)) return text;
    var sentences = text.split(/(?<=[。．!！?？])\s*/).filter(function (chunk) {
      chunk = String(chunk || '').trim();
      if (!chunk) return false;
      if (!/[。．!！?？]$/.test(chunk)) chunk += '。';
      return chunk.length >= 6 && !CHANGELOG_DEV_INTRO_RE.test(chunk);
    });
    if (sentences.length >= 2) {
      return sentences.slice(0, 3).join('');
    }
    if (sentences.length === 1 && sentences[0].length >= 18) {
      return sentences[0];
    }
    return '最近のアップデートをまとめました。画面の案内やお薬情報の表示が、より分かりやすくなっています。';
  }

  function sanitizeChangelogDiagnosis(diag) {
    if (!diag || !isChangelogKind(diag.kind)) return diag;
    var next = Object.assign({}, diag);
    next.message = sanitizeChangelogIntroText(next.message || '');
    if (next.sections && next.sections.length) {
      next.sections = next.sections.map(function (sec) {
        return Object.assign({}, sec, {
          items: (sec.items || []).filter(function (item) {
            var line = String(item || '').trim();
            return line.length >= 4 && !CHANGELOG_DEV_INTRO_RE.test(line);
          })
        });
      }).filter(function (sec) {
        return sec.items && sec.items.length;
      });
    }
    return next;
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
    if (direct) return direct;
    var repo = typeof cfg.gitRepoUrl === 'string' ? cfg.gitRepoUrl.trim() : '';
    if (repo) return buildGitCommitBrowseUrl(repo, commit);
    return buildGitCommitBrowseUrl('https://github.com/32Lwk/medicine-recommend-system', commit);
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
    if (isChangelogKind(kind)) return t('statusBadgeUpdate') || '更新';
    if (/^\d{4}年\d{1,2}月\d{1,2}日/.test(title || '')) return t('statusBadgeUpdate') || '更新';
    if (/^GCP/.test(title || '')) return 'GCP';
    if (/^AWS/.test(title || '')) return 'AWS';
    if (/デプロイ|CI\/CD|Pipeline/i.test(title || '')) return t('statusBadgeDeploy') || 'デプロイ';
    if (/医師|受診|相談/.test(title || '')) return t('statusBadgeConsult') || '受診';
    if (/副作用/.test(title || '')) return '副作用';
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

  function isReferenceHint(text) {
    var raw = String(text || '').trim();
    return /^参照[:：]/.test(raw) || /^公開情報/.test(raw);
  }

  function isMetaFootnoteBlock(hints, diag) {
    if (!hints || !hints.length) return false;
    var kind = (diag && diag.kind) || '';
    if (/^concierge_(doc_|architecture|capabilities|app_about|doc_)/.test(kind)) {
      return true;
    }
    return hints.every(isReferenceHint);
  }

  function referenceFootnoteHtml(hints, variant) {
    if (!hints || !hints.length) return '';
    var alertClass = variantAlertClass(variant || 'notice');
    var items = hints.map(function (h) {
      var text = String(h || '').trim();
      if (/^参照[:：]/.test(text)) {
        text = text.replace(/^参照[:：]\s*/, '');
      }
      return text;
    }).filter(Boolean);
    if (!items.length) return '';
    return (
      '<div class="ui-status-footnote ' + alertClass + '" role="note">' +
        '<span class="ui-status-footnote__label">' +
          esc(t('statusFootnoteLabel') || '補足') +
        '</span>' +
        '<ul class="ui-status-footnote__list">' +
          items.map(function (item) {
            return '<li class="ui-status-footnote__item">' + esc(item) + '</li>';
          }).join('') +
        '</ul>' +
      '</div>'
    );
  }

  function formatChangelogListItem(item) {
    var text = String(item || '').trim().replace(/^＋\s*/, '');
    if (!text) return '';
    return '<li class="ui-status-update-item">' + esc(text) + '</li>';
  }

  function buildVoiceIconHtml(playing) {
    if (playing) {
      return (
        '<span class="ui-feedback-voice-icon ui-feedback-voice-icon--stop" aria-hidden="true">' +
          '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true">' +
            '<rect x="6" y="6" width="12" height="12" rx="1.5"/>' +
          '</svg>' +
        '</span>'
      );
    }
    return (
      '<span class="ui-feedback-voice-icon" aria-hidden="true">' +
        '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
          '<path d="M11 5 6 9H3v6h3l5 4V5z"/>' +
          '<path d="M15.5 8.5a4.5 4.5 0 0 1 0 7"/>' +
          '<path d="M18.5 5.5a8 8 0 0 1 0 13"/>' +
        '</svg>' +
      '</span>'
    );
  }

  function buildVoiceReadBtnHtml() {
    var label = t('voiceReadCompactAria') || '音声で読み上げる';
    return (
      '<button type="button" class="ui-feedback-compact__btn ui-feedback-compact__btn--voice voice-read-main-btn voice-read-compact-btn"' +
        ' onclick="toggleVoiceRead(this)" aria-label="' + esc(label) + '" title="' + esc(label) + '">' +
        buildVoiceIconHtml(false) +
      '</button>'
    );
  }

  function statusBubbleHasVoiceButton(messageDiv) {
    return !!(messageDiv && messageDiv.querySelector && messageDiv.querySelector('.voice-read-compact-btn'));
  }

  function ensureStatusFeedbackVoice(messageDiv, diag) {
    if (!messageDiv || !messageDiv.querySelector) return;
    if (diag && diag.show_feedback === false) {
      messageDiv.setAttribute('data-sage-chrome-v', SAGE_STATUS_CHROME_VERSION);
      return;
    }
    var block = messageDiv.querySelector('.ui-bubble--status .ui-status-block, .ui-bubble--qa .ui-status-block');
    if (!block) return;

    var feedbackRow = block.querySelector('.ui-feedback-compact.feedback-buttons');
    if (!feedbackRow) {
      var tmp = document.createElement('div');
      tmp.innerHTML = buildCompactFeedbackHtml('feedbackQuestionShort');
      feedbackRow = tmp.firstElementChild;
      if (feedbackRow) block.appendChild(feedbackRow);
    }
    if (!feedbackRow) return;

    var actions = feedbackRow.querySelector('.ui-feedback-compact__actions');
    if (!actions) {
      actions = document.createElement('div');
      actions.className = 'ui-feedback-compact__actions';
      var looseBtns = feedbackRow.querySelectorAll(
        ':scope > .feedback-btn-positive, :scope > .feedback-btn-negative, :scope > [data-feedback]'
      );
      feedbackRow.appendChild(actions);
      looseBtns.forEach(function (btn) { actions.appendChild(btn); });
    }

    if (!actions.querySelector('.voice-read-compact-btn')) {
      var label = t('voiceReadCompactAria') || '音声で読み上げる';
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'ui-feedback-compact__btn ui-feedback-compact__btn--voice voice-read-main-btn voice-read-compact-btn';
      btn.setAttribute('aria-label', label);
      btn.setAttribute('title', label);
      btn.innerHTML = buildVoiceIconHtml(false);
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        if (typeof global.toggleVoiceRead === 'function') {
          global.toggleVoiceRead(btn);
        }
      });
      actions.insertBefore(btn, actions.firstChild);
    }

    if (statusBubbleHasVoiceButton(messageDiv)) {
      messageDiv.setAttribute('data-sage-chrome-v', SAGE_STATUS_CHROME_VERSION);
    } else {
      messageDiv.removeAttribute('data-sage-chrome-v');
    }
  }

  function sectionsHtml(sections, variant, kind) {
    if (!sections || !sections.length) return '';
    var sev = variantOverlapSeverity(variant || 'notice');
    var isChangelog = isChangelogKind(kind);
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
              if (isChangelog) {
                return formatChangelogListItem(item);
              }
              return '<li>' + esc(item) + '</li>';
            }).join('');
          if (!sec.html && body) {
            var listClass = isChangelog
              ? 'ui-followup-list ui-status-section__list ui-status-section__list--updates'
              : 'ui-followup-list ui-status-section__list';
            body = '<ul class="' + listClass + '">' + body + '</ul>';
          }
          if (!body) return '';
          return (
            '<div class="ui-overlap-card ui-overlap-card--' + esc(sev) + ' ui-status-section-card">' +
              '<div class="ui-overlap-card__head">' +
                '<span class="ui-overlap-card__badge">' + esc(sectionBadgeLabel(variant, title, kind)) + '</span>' +
                '<span class="ui-overlap-card__title">' + esc(title) + '</span>' +
                (isChangelogKind(kind) ? sectionCommitHtml(sec.commit) : '') +
              '</div>' +
              '<div class="ui-overlap-card__body">' + body + '</div>' +
            '</div>'
          );
        }).join('') +
      '</div>'
    );
  }

  function hintsHtml(hints, variant, diag) {
    if (!hints || !hints.length) return '';
    if (isMetaFootnoteBlock(hints, diag)) {
      return referenceFootnoteHtml(hints, variant);
    }
    var alertClass = variantAlertClass(variant || 'notice');
    if (diag && diag.kind === 'cold_symptom_chip_prompt') {
      var coldHints = hints.filter(function (h) {
        var text = String(h || '');
        return text.indexOf('例') !== 0 && text.indexOf('例：') !== 0;
      });
      var tipsHtml = coldHints.length
        ? (
          '<ul class="ui-status-hints-card__tips">' +
            coldHints.map(function (h) {
              return '<li class="ui-status-hints-card__tip">' + esc(h) + '</li>';
            }).join('') +
          '</ul>'
        )
        : '';
      return (
        '<div class="ui-alert ' + alertClass + ' ui-status-hints-card ui-status-hints-card--chips" role="note">' +
          '<div class="ui-status-hints-card__icon" aria-hidden="true">' +
            '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">' +
              '<circle cx="12" cy="12" r="9"/>' +
              '<path d="M12 8v4M12 16h.01"/>' +
            '</svg>' +
          '</div>' +
          '<div class="ui-status-hints-card__body">' +
            '<p class="ui-status-hints-card__lead">' +
              esc(t('coldSymptomHintsLead') || '当てはまる症状をタップして選べます') +
            '</p>' +
            tipsHtml +
          '</div>' +
        '</div>'
      );
    }
    return (
      '<div class="ui-alert ' + alertClass + ' ui-status-hints-card" role="note">' +
        '<strong>' + esc(t('statusHintsTitle') || '次に試すこと') + '</strong>' +
        '<ul class="ui-followup-list">' +
          hints.map(function (h) { return '<li>' + esc(h) + '</li>'; }).join('') +
        '</ul>' +
      '</div>'
    );
  }

  function actionsHtml(actions, diag) {
    if (!actions || !actions.length) return '';
    var multiSelect = !!(diag && diag.kind === 'cold_symptom_chip_prompt');
    var chipsHtml = actions.map(function (act) {
      if (act.postback_text) {
        return (
          '<button type="button" class="ui-btn ui-btn--secondary ui-status-chip"' +
            ' data-postback-text="' + esc(act.postback_text) + '"' +
            ' data-chip-label="' + esc(act.label) + '"' +
            ' data-status-action="' + esc(act.id) + '"' +
            (multiSelect ? ' aria-pressed="false"' : '') +
            '>' + esc(act.label) + '</button>'
        );
      }
      var onclick = act.action ? ' onclick="' + esc(act.action) + '"' : '';
      return (
        '<button type="button" class="ui-btn ui-btn--primary"' + onclick +
          ' data-status-action="' + esc(act.id) + '">' + esc(act.label) + '</button>'
      );
    }).join('');
    if (!multiSelect) {
      return '<div class="ui-status-actions">' + chipsHtml + '</div>';
    }
    return (
      '<div class="ui-status-actions ui-status-actions--multi" data-symptom-multi-select="true">' +
        '<div class="ui-status-actions__chips">' +
          chipsHtml +
          '<button type="button" class="ui-btn ui-btn--primary ui-status-chip ui-status-multi-submit" disabled' +
            ' aria-label="' + esc(t('coldSymptomMultiSubmitAria') || '選択した症状を送る') + '">' +
            esc(t('coldSymptomMultiSubmit') || '送る') +
          '</button>' +
        '</div>' +
      '</div>'
    );
  }

  function buildCompactFeedbackHtml(questionKey) {
    var qKey = questionKey || 'feedbackQuestionShort';
    return (
      '<div class="ui-feedback-compact feedback-buttons">' +
        '<span class="ui-feedback-compact__label">' + esc(t(qKey)) + '</span>' +
        '<div class="ui-feedback-compact__actions">' +
          buildVoiceReadBtnHtml() +
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
        '<div class="ui-feedback-compact__actions">' +
          buildVoiceReadBtnHtml() +
        '</div>' +
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

  function formatInlineMarkdown(escaped) {
    if (!escaped) return '';
    return String(escaped).replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
  }

  function infoBtnLinkHtml() {
    return (
      '<button type="button" class="ui-status-info-btn-link" aria-label="情報（ℹ️）を開く">' +
        'ℹ️' +
      '</button>'
    );
  }

  function formatInfoHintParagraph(trimmed) {
    var m = String(trimmed || '').match(/^詳細は画面右上の\s*ℹ️\s*から(.+)$/);
    if (!m) return '';
    return (
      '<p class="ui-status-advice__text ui-status-advice__text--info-hint">' +
        esc('詳細は画面右上の') +
        infoBtnLinkHtml() +
        esc('から' + m[1]) +
      '</p>'
    );
  }

  function formatStatusAdviceParagraph(para) {
    var trimmed = (para || '').trim();
    if (!trimmed) return '';
    var infoHint = formatInfoHintParagraph(trimmed);
    if (infoHint) return infoHint;
    return (
      '<p class="ui-status-advice__text">' +
        formatInlineMarkdown(esc(trimmed).replace(/\n/g, '<br>')) +
      '</p>'
    );
  }

  function bindStatusInfoBtnLinks(root) {
    var scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll('.ui-status-info-btn-link:not([data-info-bound])').forEach(function (btn) {
      btn.setAttribute('data-info-bound', '1');
      btn.addEventListener('click', function (ev) {
        ev.preventDefault();
        if (typeof global.openInfoModal === 'function') {
          global.openInfoModal();
        }
      });
    });
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
        formatInlineMarkdown(esc(message).replace(/\n/g, '<br>')) +
      '</p>'
    );
  }

  function statusAdviceHtml(diag) {
    if (isAbsoluteBlockStatus(diag)) {
      return statusMessagePlainHtml(diag);
    }
    var isChangelog = diag && isChangelogKind(diag.kind);
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
        bodyParts.push(formatStatusAdviceParagraph(para.trim()));
      });
    }
    if (isChangelog && subtitle) {
      bodyParts.push(changelogDeployMetaHtml(subtitle));
    } else if (subtitle) {
      bodyParts.unshift('<p class="ui-status-advice__lead">' + esc(subtitle) + '</p>');
    }
    return bodyParts.join('');
  }

  function crisisString(key, fallback) {
    var val = t(key);
    return (val && val !== key) ? val : fallback;
  }

  function crisisPhoneHref(phone) {
    var digits = String(phone || '').replace(/\D/g, '');
    return digits ? 'tel:' + digits : '';
  }

  function crisisResourcesHtml(diag) {
    if (!diag || diag.kind !== 'crisis_support') return '';
    var resources = diag.crisis_resources || [];
    if (!resources.length) return '';
    var lineLabel = crisisString('crisisLineConsult', 'LINEで相談する');
    var webLabel = crisisString('crisisWebsite', 'ウェブサイトを開く');
    var qrLabel = crisisString('crisisLineQr', 'LINE QRコードを表示');
    var phoneAria = crisisString('crisisPhoneAria', '電話相談');
    var html = (
      '<div class="ui-crisis-panel">' +
        '<p class="ui-crisis-panel__lead">' + esc(crisisString('crisisResourcesIntro', '相談先')) + '</p>' +
        '<ul class="ui-crisis-panel__list">'
    );
    resources.forEach(function (resource) {
      resource = resource || {};
      html += '<li class="ui-crisis-resource">';
      if (resource.name) {
        html += '<div class="ui-crisis-resource__name">' + esc(resource.name) + '</div>';
      }
      if (resource.organization) {
        html += '<div class="ui-crisis-resource__org">' + esc(resource.organization) + '</div>';
      }
      var actions = [];
      if (resource.phone) {
        var tel = crisisPhoneHref(resource.phone);
        if (tel) {
          actions.push(
            '<a class="ui-crisis-resource__chip ui-crisis-resource__chip--phone" href="' + esc(tel) +
            '" aria-label="' + esc(phoneAria) + '">' +
            '<span class="ui-crisis-resource__chip-icon" aria-hidden="true">📞</span>' +
            '<span class="ui-crisis-resource__chip-text">' + esc(resource.phone) + '</span></a>'
          );
        } else {
          actions.push(
            '<span class="ui-crisis-resource__chip ui-crisis-resource__chip--phone">' +
            '<span class="ui-crisis-resource__chip-icon" aria-hidden="true">📞</span>' +
            '<span class="ui-crisis-resource__chip-text">' + esc(resource.phone) + '</span></span>'
          );
        }
      }
      if (resource.line) {
        actions.push(
          '<a class="ui-crisis-resource__chip ui-crisis-resource__chip--line" href="' + esc(resource.line) +
          '" target="_blank" rel="noopener noreferrer">' +
          '<span class="ui-crisis-resource__chip-icon" aria-hidden="true">💬</span>' +
          '<span class="ui-crisis-resource__chip-text">' + esc(lineLabel) + '</span></a>'
        );
      }
      if (resource.website) {
        actions.push(
          '<a class="ui-crisis-resource__chip ui-crisis-resource__chip--web" href="' + esc(resource.website) +
          '" target="_blank" rel="noopener noreferrer">' +
          '<span class="ui-crisis-resource__chip-icon" aria-hidden="true">🌐</span>' +
          '<span class="ui-crisis-resource__chip-text">' + esc(webLabel) + '</span></a>'
        );
      }
      if (actions.length) {
        html += '<div class="ui-crisis-resource__actions">' + actions.join('') + '</div>';
      }
      if (resource.hours) {
        html += '<div class="ui-crisis-resource__hours">⏰ ' + esc(resource.hours) + '</div>';
      }
      if (resource.description) {
        html += '<p class="ui-crisis-resource__desc">' + esc(resource.description) + '</p>';
      }
      if (resource.line_qr) {
        html += (
          '<details class="ui-crisis-resource__qr">' +
            '<summary>' + esc(qrLabel) + '</summary>' +
            '<img src="' + esc(resource.line_qr) + '" alt="LINE QRコード" class="ui-crisis-resource__qr-img" loading="lazy" decoding="async">' +
          '</details>'
        );
      }
      html += '</li>';
    });
    html += '</ul>';
    var emergency = diag.emergency_message || '';
    if (emergency) {
      html += '<p class="ui-crisis-panel__emergency" role="note">' + esc(emergency) + '</p>';
    }
    html += '</div>';
    return html;
  }

  function buildCrisisStatusBlockHtml(diag) {
    var variant = diag.variant || 'security';
    var render = diag.render || 'sage_status';
    return (
      '<div class="ui-status-block ui-status-block--pro ui-status-block--crisis ui-status-block--' + esc(variant) + '">' +
        statusIntroHtml(diag, variant, render) +
        statusAdviceHtml(diag) +
        crisisResourcesHtml(diag) +
      '</div>'
    );
  }

  function buildStatusBlockHtml(diag) {
    if (!diag) return '';
    if (isCompactLayout(diag)) {
      return buildCompactStatusBlockHtml(diag);
    }
    if (diag.kind === 'crisis_support' && diag.crisis_resources && diag.crisis_resources.length) {
      return buildCrisisStatusBlockHtml(diag);
    }
    var variant = diag.variant || 'notice';
    var render = diag.render || 'sage_status';
    var crisisHtml = crisisResourcesHtml(diag);
    var sectionsBlock = crisisHtml || sectionsHtml(diag.sections, variant, diag.kind);
    return (
      '<div class="ui-status-block ui-status-block--pro ui-status-block--' + esc(variant) + '">' +
        statusIntroHtml(diag, variant, render) +
        statusAdviceHtml(diag) +
        sectionsBlock +
        hintsHtml(diag.hints, variant, diag) +
        actionsHtml(diag.actions, diag) +
        feedbackHtml(diag) +
      '</div>'
    );
  }

  function resolveDiagnosis(diag) {
    if (global.UiStrings && global.UiStrings.applyDiagnosisI18n) {
      diag = global.UiStrings.applyDiagnosisI18n(diag);
    } else if (global.RecommendationRenderer && global.RecommendationRenderer.applyDiagnosisI18n) {
      diag = global.RecommendationRenderer.applyDiagnosisI18n(diag);
    }
    return sanitizeChangelogDiagnosis(diag);
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

  function patchStatusBubbleChrome(messageDiv, diag) {
    if (!messageDiv || !messageDiv.querySelector) return;
    messageDiv.querySelectorAll('.ui-status-section__list--updates > li').forEach(function (li) {
      if (!li.classList.contains('ui-status-update-item')) {
        li.classList.add('ui-status-update-item');
      }
    });
    ensureStatusFeedbackVoice(messageDiv, diag || messageDiv.__messageDiagnosis);
    bindStatusInfoBtnLinks(messageDiv);
  }

  function needsStatusChromeRefresh(messageDiv, diag) {
    if (!messageDiv) return true;
    if (messageDiv.getAttribute('data-sage-chrome-v') !== SAGE_STATUS_CHROME_VERSION) {
      return true;
    }
    if (diag && diag.show_feedback === false) return false;
    return !statusBubbleHasVoiceButton(messageDiv);
  }

  function mountSageStatus(messageDiv, message, options) {
    options = options || {};
    if (!messageDiv || !isSageUi() || !message || !message.diagnosis) return false;
    var diag = resolveDiagnosis(message.diagnosis);
    if (diag.render !== 'sage_status' && diag.render !== 'sage_qa') return false;
    var mountFingerprint = options.mountFingerprint || '';
    var bubbleSelector = diag.render === 'sage_qa' ? '.ui-bubble--qa' : '.ui-bubble--status';
    var alreadyMounted = !!(
      mountFingerprint
      && messageDiv.__sageMountFingerprint === mountFingerprint
      && messageDiv.querySelector(bubbleSelector)
      && !needsStatusChromeRefresh(messageDiv, diag)
    );
    if (!alreadyMounted) {
      var html = buildSageStatusBubbleHtml(diag);
      if (!html) return false;
      messageDiv.innerHTML = html;
      messageDiv.classList.add(isPlainLayout(diag) ? 'message--sage-chat' : 'message--sage-status');
      messageDiv.__messageDiagnosis = diag;
      if (mountFingerprint) {
        messageDiv.__sageMountFingerprint = mountFingerprint;
      }
    } else {
      messageDiv.__messageDiagnosis = diag;
    }
    patchStatusBubbleChrome(messageDiv, diag);
    if (!statusBubbleHasVoiceButton(messageDiv) && diag.show_feedback !== false) {
      messageDiv.removeAttribute('data-sage-chrome-v');
      messageDiv.__sageMountFingerprint = '';
      messageDiv.innerHTML = buildSageStatusBubbleHtml(diag);
      messageDiv.__messageDiagnosis = diag;
      if (mountFingerprint) {
        messageDiv.__sageMountFingerprint = mountFingerprint;
      }
      patchStatusBubbleChrome(messageDiv, diag);
    }
    return true;
  }

  global.StatusRenderer = {
    isSageUi: isSageUi,
    isPlainLayout: isPlainLayout,
    isCompactLayout: isCompactLayout,
    buildStatusBlockHtml: buildStatusBlockHtml,
    buildSageStatusBubbleHtml: buildSageStatusBubbleHtml,
    mountSageStatus: mountSageStatus,
    patchStatusBubbleChrome: patchStatusBubbleChrome,
    ensureStatusFeedbackVoice: ensureStatusFeedbackVoice,
    buildVoiceIconHtml: buildVoiceIconHtml,
    SAGE_STATUS_CHROME_VERSION: SAGE_STATUS_CHROME_VERSION
  };
})(typeof window !== 'undefined' ? window : globalThis);
