/**

 * Horizontal medicine carousel (snap, dots, keyboard).

 */

(function (global) {

  'use strict';



  var carouselUid = 0;

  var esc = function (s) {

    return global.MedicineMapper ? global.MedicineMapper.esc(s) : String(s == null ? '' : s);

  };

  var t = function (k, v) {

    return global.UiStrings ? global.UiStrings.t(k, v) : k;

  };



  function carouselNavHtml(id, count) {

    var dots = '';

    for (var i = 0; i < count; i++) {

      dots += '<button type="button" class="ui-carousel-dot' + (i === 0 ? ' is-active' : '') + '" data-carousel-dot="' + i + '" aria-label="' + esc(t('rankBadge', { n: i + 1 })) + '" aria-current="' + (i === 0 ? 'true' : 'false') + '"></button>';

    }

    return (

      '<nav class="ui-carousel-nav" aria-label="' + esc(t('carouselNavLabel')) + '" data-carousel-nav="' + id + '">' +

        '<button type="button" class="ui-carousel-arrow ui-carousel-arrow--prev" data-carousel-prev aria-label="' + esc(t('carouselPrev')) + '">' +

          '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M15 6l-6 6 6 6"/></svg>' +

        '</button>' +

        '<div class="ui-carousel-dots" role="tablist" aria-label="' + esc(t('carouselDotsLabel')) + '">' + dots + '</div>' +

        '<span class="ui-carousel-counter" data-carousel-counter>1 / ' + count + '</span>' +

        '<button type="button" class="ui-carousel-arrow ui-carousel-arrow--next" data-carousel-next aria-label="' + esc(t('carouselNext')) + '">' +

          '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9 6l6 6-6 6"/></svg>' +

        '</button>' +

      '</nav>'

    );

  }



  function carouselBlockHtml(cardsHtml, count, style) {

    var id = 'carousel-' + (++carouselUid);

    var proClass = style === 'pro' ? ' ui-carousel-pro' : '';

    count = count || 0;

    return (

      '<div class="ui-carousel-region" data-carousel-region="' + id + '">' +

        '<div class="ui-carousel-wrap app-scrollbar' + proClass + '" id="' + id + '" tabindex="0" role="region" aria-label="' + esc(t('carouselLabel')) + '" data-carousel-wrap>' +

          '<div class="ui-carousel" role="list">' + cardsHtml + '</div>' +

        '</div>' +

        (count > 0 ? carouselNavHtml(id, count) : '') +

      '</div>'

    );

  }



  function scrollCarouselTo(wrap, index) {

    var cards = wrap.querySelectorAll('.ui-carousel .ui-card');

    if (!cards.length) return;

    var i = Math.max(0, Math.min(index, cards.length - 1));

    var card = cards[i];

    var offset = card.offsetLeft - (wrap.clientWidth - card.offsetWidth) / 2;

    if (window.matchMedia('(min-width: 769px)').matches) {

      offset = card.offsetLeft - 4;

    }

    wrap.scrollTo({ left: Math.max(0, offset), behavior: 'smooth' });

  }



  function updateCarouselState(region) {

    var wrap = region.querySelector('[data-carousel-wrap]');

    var cards = wrap ? wrap.querySelectorAll('.ui-card') : [];

    if (!wrap || !cards.length) return;

    var center = wrap.scrollLeft + wrap.clientWidth / 2;

    var active = 0;

    var minDist = Infinity;

    cards.forEach(function (card, idx) {

      var cardCenter = card.offsetLeft + card.offsetWidth / 2;

      var dist = Math.abs(cardCenter - center);

      if (dist < minDist) { minDist = dist; active = idx; }

    });

    region.querySelectorAll('[data-carousel-dot]').forEach(function (dot, idx) {

      var on = idx === active;

      dot.classList.toggle('is-active', on);

      dot.setAttribute('aria-current', on ? 'true' : 'false');

    });

    var counter = region.querySelector('[data-carousel-counter]');

    if (counter) counter.textContent = (active + 1) + ' / ' + cards.length;

  }



  function bindCarousels(root) {

    root = root || document;

    root.querySelectorAll('[data-carousel-region]').forEach(function (region) {

      if (region._carouselBound) return;

      region._carouselBound = true;

      var wrap = region.querySelector('[data-carousel-wrap]');

      if (!wrap) return;



      wrap.addEventListener('scroll', function () {

        if (wrap._scrollTimer) clearTimeout(wrap._scrollTimer);

        wrap._scrollTimer = setTimeout(function () { updateCarouselState(region); }, 60);

      }, { passive: true });



      wrap.addEventListener('keydown', function (e) {

        var cards = wrap.querySelectorAll('.ui-card');

        if (!cards.length) return;

        var center = wrap.scrollLeft + wrap.clientWidth / 2;

        var active = 0;

        cards.forEach(function (card, idx) {

          if (Math.abs(card.offsetLeft + card.offsetWidth / 2 - center) < wrap.clientWidth / 2) active = idx;

        });

        if (e.key === 'ArrowRight') { scrollCarouselTo(wrap, active + 1); e.preventDefault(); }

        if (e.key === 'ArrowLeft') { scrollCarouselTo(wrap, active - 1); e.preventDefault(); }

      });



      var prevBtn = region.querySelector('[data-carousel-prev]');

      if (prevBtn) {

        prevBtn.addEventListener('click', function () {

          var cards = wrap.querySelectorAll('.ui-card');

          var center = wrap.scrollLeft + wrap.clientWidth / 2;

          var active = 0;

          cards.forEach(function (card, idx) {

            if (Math.abs(card.offsetLeft + card.offsetWidth / 2 - center) < wrap.clientWidth / 2) active = idx;

          });

          scrollCarouselTo(wrap, active - 1);

        });

      }



      var nextBtn = region.querySelector('[data-carousel-next]');

      if (nextBtn) {

        nextBtn.addEventListener('click', function () {

          var cards = wrap.querySelectorAll('.ui-card');

          var center = wrap.scrollLeft + wrap.clientWidth / 2;

          var active = 0;

          cards.forEach(function (card, idx) {

            if (Math.abs(card.offsetLeft + card.offsetWidth / 2 - center) < wrap.clientWidth / 2) active = idx;

          });

          scrollCarouselTo(wrap, active + 1);

        });

      }



      region.querySelectorAll('[data-carousel-dot]').forEach(function (dot) {

        dot.addEventListener('click', function () {

          scrollCarouselTo(wrap, parseInt(dot.getAttribute('data-carousel-dot'), 10));

        });

      });



      if ('IntersectionObserver' in window) {

        var observer = new IntersectionObserver(function () {

          updateCarouselState(region);

        }, { root: wrap, threshold: [0.55, 0.75] });

        wrap.querySelectorAll('.ui-card').forEach(function (card) { observer.observe(card); });

      }



      updateCarouselState(region);

    });

  }



  global.MedicineCarousel = {

    carouselBlockHtml: carouselBlockHtml,

    bindCarousels: bindCarousels,

    updateCarouselState: updateCarouselState

  };

})(typeof window !== 'undefined' ? window : globalThis);


