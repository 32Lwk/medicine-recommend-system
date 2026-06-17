/**

 * Sage Terrace shell — toolbar wiring and safety rail bootstrap.

 */

(function () {

  'use strict';



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



  function syncHeaderPhaseDefault() {

    var el = document.getElementById('headerPhase');

    if (!el || el.textContent) return;

    if (window.UiStrings) {

      el.textContent = window.UiStrings.t('headerPhaseDefault');

    }

  }



  function onDomReady() {

    if (!isSage()) return;

    wireToolbar();

    initSafetyRailFromSession();

    syncHeaderPhaseDefault();

    document.documentElement.style.setProperty('--focus-color', '#5b7c99');

  }



  if (document.readyState === 'loading') {

    document.addEventListener('DOMContentLoaded', onDomReady);

  } else {

    onDomReady();

  }



  window.SageShell = {

    isSage: isSage,

    refreshSafetyRail: function (attrs) {

      if (attrs && window.SafetyRail && window.SafetyRail.normalizeAttrs) {
        attrs = window.SafetyRail.normalizeAttrs(attrs);
      }

      if (attrs) window.__lastUserAttributes = attrs;

      if (window.SafetyRail) window.SafetyRail.mount(attrs || window.__lastUserAttributes || {});

    },

    updateHeaderSymptoms: function (symptoms) {

      if (window.SafetyRail) window.SafetyRail.updateHeaderPhase(symptoms);

    }

  };

})();


