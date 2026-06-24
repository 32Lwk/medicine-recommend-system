/**
 * Sage Terrace shell — toolbar wiring and safety rail bootstrap.
 */
(function () {
  'use strict';

  var HEADER_PHASE_ROTATE_MS = 10000;
  var headerPhaseRotateTimer = null;
  var headerPhaseIndex = 0;

  function isSage() {
    return document.body && document.body.getAttribute('data-ui-variant') === 'sage';
  }

  function wireToolbar() {
    var clearBtn = document.getElementById('sage-clear-btn');
    var adminBtn = document.getElementById('sage-admin-request-btn');
    var legacyClear = document.getElementById('clearBtn');
    var legacyAdmin = document.getElementById('admin-request-btn');

    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        if (typeof window.startNewSession === 'function') {
          window.startNewSession();
        } else {
          var legacyNew = document.getElementById('new-session-btn');
          if (legacyNew) {
            legacyNew.click();
          } else if (typeof window.clearChat === 'function') {
            window.clearChat();
          } else if (legacyClear) {
            legacyClear.click();
          }
        }
      });
    }

    if (adminBtn && legacyAdmin) {
      adminBtn.addEventListener('click', function () { legacyAdmin.click(); });
    }
  }

  function initSafetyRailFromSession() {
    if (!window.SafetyRail) return;
    var attrs = window.__lastUserAttributes || {};
    window.SafetyRail.mount(attrs);
  }

  function headerPhaseMessageList() {
    if (window.UiStrings && typeof window.UiStrings.headerPhaseMessages === 'function') {
      return window.UiStrings.headerPhaseMessages();
    }
    if (window.UiStrings) return [window.UiStrings.t('headerPhaseDefault')];
    return [];
  }

  function applyHeaderPhaseMessage(index) {
    var el = document.getElementById('headerPhase');
    var messages = headerPhaseMessageList();
    if (!el || !messages.length) return;
    el.textContent = messages[index % messages.length];
  }

  function stopHeaderPhaseRotation() {
    if (headerPhaseRotateTimer) {
      clearInterval(headerPhaseRotateTimer);
      headerPhaseRotateTimer = null;
    }
  }

  function startHeaderPhaseRotation(resetIndex) {
    stopHeaderPhaseRotation();
    if (!isSage()) return;

    var messages = headerPhaseMessageList();
    if (!messages.length) return;

    if (resetIndex) headerPhaseIndex = 0;
    applyHeaderPhaseMessage(headerPhaseIndex);

    if (messages.length < 2) return;

    headerPhaseRotateTimer = setInterval(function () {
      headerPhaseIndex = (headerPhaseIndex + 1) % messages.length;
      applyHeaderPhaseMessage(headerPhaseIndex);
    }, HEADER_PHASE_ROTATE_MS);
  }

  function refreshHeaderPhase() {
    startHeaderPhaseRotation(true);
  }

  function onDomReady() {
    if (!isSage()) return;
    wireToolbar();
    initSafetyRailFromSession();
    refreshHeaderPhase();
    document.documentElement.style.setProperty('--focus-color', '#5b7c99');
  }

  document.addEventListener('DOMContentLoaded', onDomReady);

  window.SageShell = {
    isSage: isSage,
    refreshSafetyRail: function (attrs) {
      var normalized = attrs;
      if (normalized && window.SafetyRail && window.SafetyRail.normalizeAttrs) {
        normalized = window.SafetyRail.normalizeAttrs(normalized);
      }
      if (normalized && Object.keys(normalized).length > 0) {
        window.__lastUserAttributes = normalized;
      }
      if (window.SafetyRail) {
        window.SafetyRail.mount(window.__lastUserAttributes || {});
      }
    },
    refreshHeaderPhase: refreshHeaderPhase,
    updateHeaderSymptoms: function () {
      /* header phase no longer reflects symptom context */
    }
  };
})();
