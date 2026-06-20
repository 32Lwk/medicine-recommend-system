/**
 * Sage UI color theme presets — CSS variable bundles + settings UI
 */
(function (global) {
  'use strict';

  var STORAGE_KEY = 'sageColorTheme';
  var DEFAULT_ID = 'sage-terrace';

  function baseLightBundle(primary, primaryDark, primarySoft, accent, outer, chat, header) {
    return {
      '--ui-primary': primary,
      '--ui-primary-dark': primaryDark,
      '--ui-primary-soft': primarySoft,
      '--ui-accent': accent,
      '--ui-warn': accent,
      '--ui-bg-outer': outer,
      '--ui-bg-chat': chat,
      '--ui-bg-surface': '#ffffff',
      '--ui-bg-header': header,
      '--ui-text-on-primary': '#ffffff',
      '--ui-text': '#2c3440',
      '--ui-text-muted': '#6b7280',
      '--ui-border': primarySoft,
      '--ui-bubble-user-bg': primary,
      '--focus-color': primary
    };
  }

  var PRESETS = {
    'sage-terrace': {
      labelKey: 'settingsColorSage',
      swatches: ['#5b7c99', '#faf9f7', '#c9846a'],
      vars: baseLightBundle(
        '#5b7c99', '#3d5a73', '#e8eef4', '#c9846a',
        'linear-gradient(165deg, #f5f3f0 0%, #ebe8e4 45%, #e2e6ec 100%)',
        '#faf9f7',
        'linear-gradient(180deg, #5b7c99 0%, #4d6d88 100%)'
      )
    },
    'classic-green': {
      labelKey: 'settingsColorClassicGreen',
      swatches: ['#4caf50', '#c0c0c0', '#2196f3'],
      vars: Object.assign(baseLightBundle(
        '#4caf50', '#388e3c', '#e8f5e9', '#2196f3',
        'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        '#c0c0c0',
        '#4caf50'
      ), { '--ui-bg-chat': '#c0c0c0' })
    },
    'warm-care': {
      labelKey: 'settingsColorWarmCare',
      swatches: ['#e07a5f', '#fff9f5', '#81b29a'],
      vars: baseLightBundle(
        '#e07a5f', '#c45c42', '#fde8e0', '#81b29a',
        'linear-gradient(160deg, #fef9f3 0%, #fde8e0 50%, #f4e4d4 100%)',
        '#fff9f5',
        '#e07a5f'
      )
    },
    'minimal-zen': {
      labelKey: 'settingsColorMinimal',
      swatches: ['#37474f', '#ffffff', '#546e7a'],
      vars: {
        '--ui-primary': '#37474f',
        '--ui-primary-dark': '#263238',
        '--ui-primary-soft': '#eceff1',
        '--ui-accent': '#546e7a',
        '--ui-warn': '#78909c',
        '--ui-bg-outer': '#fafafa',
        '--ui-bg-chat': '#ffffff',
        '--ui-bg-surface': '#ffffff',
        '--ui-bg-header': '#ffffff',
        '--ui-text-on-primary': '#263238',
        '--ui-text': '#263238',
        '--ui-text-muted': '#607d8b',
        '--ui-border': '#e0e0e0',
        '--ui-bubble-user-bg': '#37474f',
        '--focus-color': '#37474f'
      }
    },
    'dark-clinical': {
      labelKey: 'settingsColorDark',
      swatches: ['#5ba4b8', '#1a1f26', '#7ec8b8'],
      vars: {
        '--ui-primary': '#5ba4b8',
        '--ui-primary-dark': '#4a8a9c',
        '--ui-primary-soft': '#243038',
        '--ui-accent': '#7ec8b8',
        '--ui-warn': '#c9a87c',
        '--ui-bg-outer': '#1a1f26',
        '--ui-bg-chat': '#222830',
        '--ui-bg-surface': '#2a3038',
        '--ui-bg-header': 'linear-gradient(180deg, #2a3038 0%, #222830 100%)',
        '--ui-text-on-primary': '#eef4f7',
        '--ui-text': '#e2e8ed',
        '--ui-text-muted': '#9aa8b5',
        '--ui-border': '#3a424c',
        '--ui-bubble-user-bg': '#4a8f7c',
        '--focus-color': '#5ba4b8'
      }
    },
    'pharmacy-green': {
      labelKey: 'settingsColorPharmacyGreen',
      swatches: ['#4caf50', '#c0c0c0', '#2196f3'],
      vars: Object.assign(baseLightBundle(
        '#4caf50', '#388e3c', '#e8f5e9', '#2196f3',
        'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        '#c0c0c0',
        'linear-gradient(135deg, #4CAF50, #45a049)'
      ), {
        '--ui-bg-chat': '#c0c0c0',
        '--ui-border': '#dee2e6',
        '--ui-warn': '#ffc107'
      })
    },
    'lavender-calm': {
      labelKey: 'settingsColorLavender',
      swatches: ['#6d6d9a', '#f9f8fc', '#9a8fbc'],
      vars: baseLightBundle(
        '#6d6d9a', '#52527a', '#ededf5', '#9a8fbc',
        'linear-gradient(165deg, #f6f5fa 0%, #eeedf5 50%, #e5e4ef 100%)',
        '#f9f8fc',
        'linear-gradient(180deg, #6d6d9a 0%, #5c5c85 100%)'
      )
    },
    'ocean-trust': {
      labelKey: 'settingsColorOcean',
      swatches: ['#4a7a8c', '#f7fafb', '#6a9aaa'],
      vars: baseLightBundle(
        '#4a7a8c', '#355f6e', '#e8f1f5', '#6a9aaa',
        'linear-gradient(165deg, #f2f7f9 0%, #e8f0f4 50%, #dde8ee 100%)',
        '#f7fafb',
        'linear-gradient(180deg, #4a7a8c 0%, #3d6a7a 100%)'
      )
    },
    'sand-neutral': {
      labelKey: 'settingsColorSand',
      swatches: ['#8b7355', '#faf8f5', '#a89278'],
      vars: baseLightBundle(
        '#8b7355', '#6b5740', '#f5f0e8', '#a89278',
        'linear-gradient(165deg, #faf8f5 0%, #f3efe8 50%, #ebe5dc 100%)',
        '#faf8f5',
        'linear-gradient(180deg, #8b7355 0%, #756045 100%)'
      )
    },
    'mint-fresh': {
      labelKey: 'settingsColorMint',
      swatches: ['#4a8f7c', '#f7fbf9', '#6aad9a'],
      vars: baseLightBundle(
        '#4a8f7c', '#357262', '#e8f5f1', '#6aad9a',
        'linear-gradient(165deg, #f2f9f6 0%, #e8f3ef 50%, #ddeee8 100%)',
        '#f7fbf9',
        'linear-gradient(180deg, #4a8f7c 0%, #3d7a68 100%)'
      )
    }
  };

  var ORDER = [
    'sage-terrace',
    'pharmacy-green',
    'ocean-trust',
    'mint-fresh',
    'warm-care',
    'lavender-calm',
    'sand-neutral',
    'classic-green',
    'minimal-zen',
    'dark-clinical'
  ];

  function settingsString(key, lang) {
    var table = (global.UiStrings && global.UiStrings.all && global.UiStrings.all[lang]) ||
      (global.UiStrings && global.UiStrings.all && global.UiStrings.all.ja) ||
      {};
    return table[key] != null ? table[key] : key;
  }

  function getCurrentThemeId() {
    try {
      return localStorage.getItem(STORAGE_KEY) || DEFAULT_ID;
    } catch (e) {
      return DEFAULT_ID;
    }
  }

  function applySageColorTheme(themeId) {
    var preset = PRESETS[themeId] || PRESETS[DEFAULT_ID];
    var body = document.body;
    if (!body || body.getAttribute('data-ui-variant') !== 'sage') {
      return;
    }

    Object.keys(PRESETS[DEFAULT_ID].vars).forEach(function (key) {
      body.style.removeProperty(key);
      document.documentElement.style.removeProperty(key);
    });
    Object.keys(preset.vars).forEach(function (key) {
      body.style.setProperty(key, preset.vars[key]);
      document.documentElement.style.setProperty(key, preset.vars[key]);
    });

    body.setAttribute('data-sage-color-theme', themeId);
    try {
      localStorage.setItem(STORAGE_KEY, themeId);
    } catch (e) { /* ignore */ }

    document.querySelectorAll('.settings-color-option').forEach(function (btn) {
      var active = btn.getAttribute('data-theme') === themeId;
      btn.classList.toggle('is-active', active);
      btn.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  }

  function loadSageColorTheme() {
    applySageColorTheme(getCurrentThemeId());
  }

  function buildColorSettingsHtml(lang, currentId) {
    var s = function (key) { return settingsString(key, lang); };
    var options = ORDER.map(function (id) {
      var preset = PRESETS[id];
      if (!preset) return '';
      var swatchHtml = preset.swatches.map(function (color) {
        return '<span class="settings-color-swatch" style="background:' + color + '" aria-hidden="true"></span>';
      }).join('');
      var active = id === currentId;
      return (
        '<button type="button" class="settings-color-option' + (active ? ' is-active' : '') + '" ' +
        'data-theme="' + id + '" aria-pressed="' + (active ? 'true' : 'false') + '" ' +
        'aria-label="' + s(preset.labelKey) + '">' +
        '<span class="settings-color-swatches">' + swatchHtml + '</span>' +
        '<span class="settings-color-label">' + s(preset.labelKey) + '</span>' +
        '</button>'
      );
    }).join('');

    return (
      '<section class="settings-card settings-card--color">' +
      '<div class="settings-card__header">' +
      '<span class="settings-card__icon" aria-hidden="true">🎨</span>' +
      '<div><h3 class="settings-card__title">' + s('settingsColorTitle') + '</h3>' +
      '<p class="settings-card__desc">' + s('settingsColorDesc') + '</p></div></div>' +
      '<div class="settings-color-grid" role="group" aria-label="' + s('settingsColorTitle') + '">' +
      options +
      '</div></section>'
    );
  }

  function bindColorSettingsEvents(root) {
    if (!root) return;
    root.querySelectorAll('.settings-color-option').forEach(function (btn) {
      if (btn.dataset.bound) return;
      btn.dataset.bound = 'true';
      btn.addEventListener('click', function () {
        applySageColorTheme(btn.getAttribute('data-theme'));
      });
    });
  }

  global.SageColorThemes = {
    presets: PRESETS,
    order: ORDER,
    defaultId: DEFAULT_ID,
    getCurrentThemeId: getCurrentThemeId,
    apply: applySageColorTheme,
    load: loadSageColorTheme,
    buildSettingsHtml: buildColorSettingsHtml,
    bindSettingsEvents: bindColorSettingsEvents
  };

  global.applySageColorTheme = applySageColorTheme;
})(typeof window !== 'undefined' ? window : globalThis);
