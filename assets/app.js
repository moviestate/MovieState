// MovieState — light progressive enhancement
(function () {
  var header = document.querySelector('.header');
  var onScroll = function () {
    if (!header) return;
    header.classList.toggle('is-scrolled', window.scrollY > 8);
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  if (!('IntersectionObserver' in window)) return;
  var targets = document.querySelectorAll('.section__head, .card, .spotlight, .step, .panel, .faq__item');
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-in');
        io.unobserve(entry.target);
      }
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
  targets.forEach(function (el) {
    el.classList.add('reveal');
    io.observe(el);
  });
})();

// Load more for the movies grid (all cards stay in the DOM for crawlers)
(function () {
  var grid = document.getElementById('movieGrid');
  var btn = document.getElementById('loadMore');
  var count = document.getElementById('moreCount');
  if (!grid || !btn) return;
  var BATCH = 12, shown = BATCH;
  var total = grid.children.length;
  grid.classList.add('is-limited');
  function sync() {
    var hidden = Math.max(0, total - shown);
    if (count) count.textContent = 'Showing ' + Math.min(shown, total) + ' of ' + total + ' movies';
    if (hidden <= 0) { btn.style.display = 'none'; grid.classList.remove('is-limited'); }
  }
  btn.addEventListener('click', function () {
    shown += BATCH;
    Array.prototype.forEach.call(grid.children, function (el, i) { if (i < shown) el.style.display = ''; });
    grid.classList.remove('is-limited');
    sync();
  });
  sync();
})();

// Cinematic hero carousel
(function () {
  var hero = document.getElementById('hero'); if (!hero) return;
  var slides = hero.querySelectorAll('.slide'), thumbs = hero.querySelectorAll('.hdot');
  var bar = hero.querySelector('.hero__progress span'), i = 0, timer = null, D = 7000;
  function load(s) {
    Array.prototype.forEach.call(s.querySelectorAll('img[data-src]'), function (im) {
      if (!im.getAttribute('src')) { im.setAttribute('src', im.dataset.src); }
    });
  }
  function paint() {
    Array.prototype.forEach.call(slides, function (s, k) {
      if (k === i) load(s);
      s.classList.toggle('is-on', k === i);
      try { s.inert = k !== i; } catch (e) {}
      var bg = s.querySelector('.slide__bg');
      if (bg) { if (k === i) { bg.style.animation = 'none'; void bg.offsetWidth; bg.style.animation = ''; } }
      var c = s.querySelector('.slide__copy'); if (c) Array.prototype.forEach.call(c.children, function (n) { n.style.animation = 'none'; void n.offsetWidth; n.style.animation = ''; });
    });
    Array.prototype.forEach.call(thumbs, function (t, k) { t.classList.toggle('is-on', k === i); t.setAttribute('aria-current', k === i ? 'true' : 'false'); });
    if (bar) { bar.classList.remove('is-run'); void bar.offsetWidth; if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) bar.classList.add('is-run'); }
  }
  function go(n) { i = (n + slides.length) % slides.length; paint(); }
  function play() { stop(); timer = setInterval(function () { go(i + 1); }, D); }
  function stop() { if (timer) clearInterval(timer); }
  Array.prototype.forEach.call(thumbs, function (t) { t.addEventListener('click', function () { go(+t.dataset.goto); play(); }); });
  var nx = hero.querySelector('[data-next]'), pv = hero.querySelector('[data-prev]');
  if (nx) nx.addEventListener('click', function () { go(i + 1); play(); });
  if (pv) pv.addEventListener('click', function () { go(i - 1); play(); });
  hero.addEventListener('mouseenter', stop); hero.addEventListener('mouseleave', play);
  hero.addEventListener('focusin', stop); hero.addEventListener('focusout', play);
  document.addEventListener('visibilitychange', function () { document.hidden ? stop() : play(); });
  paint();
  setTimeout(function () { if (slides[1]) load(slides[1]); }, 2500);
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches && slides.length > 1) play();
})();

// Count-up stats
(function () {
  var els = document.querySelectorAll('[data-count]'); if (!els.length) return;
  var io = new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      if (!e.isIntersecting) return;
      var el = e.target, end = +el.dataset.count, t0 = null;
      function tick(t) { if (!t0) t0 = t; var p = Math.min(1, (t - t0) / 900); el.textContent = Math.round(end * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(tick); }
      requestAnimationFrame(tick); io.unobserve(el);
    });
  }, { threshold: .4 });
  Array.prototype.forEach.call(els, function (el) { io.observe(el); });
})();

// Search: suggestions + real results
(function () {
  var input = document.getElementById('q'), box = document.getElementById('qres'),
      raw = document.getElementById('siteIndex'), grid = document.getElementById('qgrid'),
      form = document.getElementById('sf');
  if (!input || !raw) return;
  var data = []; try { data = JSON.parse(raw.textContent); } catch (e) { return; }

  function match(q) {
    q = q.toLowerCase().trim();
    if (!q) return [];
    var starts = [], has = [];
    data.forEach(function (m) {
      var hay = (m.t + ' ' + m.y + ' ' + (m.g || '')).toLowerCase();
      if (m.t.toLowerCase().indexOf(q) === 0) starts.push(m);
      else if (hay.indexOf(q) > -1) has.push(m);
    });
    return starts.concat(has);
  }
  function close() { if (box) { box.classList.remove('is-open'); box.innerHTML = ''; } }
  function suggest(list) {
    if (!box) return;
    if (!list.length) { close(); return; }
    box.innerHTML = list.slice(0, 6).map(function (m) {
      return '<a href="' + m.u + '"><img src="' + m.p + '" alt="" width="28" height="42" loading="lazy"><span>' + m.t + ' <em>(' + m.y + ')</em></span></a>';
    }).join('');
    box.classList.add('is-open');
  }
  if (input) input.addEventListener('input', function () {
    var q = input.value.trim();
    if (q.length < 2) { close(); return; }
    suggest(match(q));
  });
  input.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') close();
    if (ev.key === 'Enter') { ev.preventDefault(); if (form) run(); }
  });
  function run() {
    var q = input.value.trim();
    var list = match(q);
    close();
    if (!grid) return;
    if (!list.length) {
      grid.innerHTML = '<p class="qres__empty">No guide matches “' + q.replace(/[<>&]/g, '') + '”. <a href="https://moviestate.github.io/MovieState/movies/">Browse all films &#8594;</a></p>';
    } else {
      grid.innerHTML = list.slice(0, 12).map(function (m) {
        return '<a class="qhit" href="' + m.u + '"><img src="' + m.p + '" alt="' + m.t + ' poster" width="92" height="138" loading="lazy"><span>' + m.t + '</span></a>';
      }).join('');
    }
    grid.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  if (form) form.addEventListener('submit', function (ev) { ev.preventDefault(); run(); });
  document.addEventListener('click', function (ev) { if (box && !box.contains(ev.target) && ev.target !== input) close(); });
})();
