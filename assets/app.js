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
  var slides = hero.querySelectorAll('.slide'), thumbs = hero.querySelectorAll('.thumb');
  var bar = hero.querySelector('.hero__progress span'), i = 0, timer = null, D = 7000;
  function paint() {
    Array.prototype.forEach.call(slides, function (s, k) {
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

// Instant search over the inline index
(function () {
  var input = document.getElementById('q'), box = document.getElementById('qres'), raw = document.getElementById('siteIndex');
  if (!input || !box || !raw) return;
  var data = []; try { data = JSON.parse(raw.textContent); } catch (e) { return; }
  function render(list) {
    if (!list.length) { box.classList.remove('is-open'); box.innerHTML = ''; return; }
    box.innerHTML = list.slice(0, 6).map(function (m) {
      return '<a href="' + m.u + '"><img src="' + m.p + '" alt="" width="28" height="42" loading="lazy">' + m.t + ' <span style="opacity:.6">(' + m.y + ')</span></a>';
    }).join('');
    box.classList.add('is-open');
  }
  input.addEventListener('input', function () {
    var q = input.value.trim().toLowerCase();
    if (q.length < 2) { render([]); return; }
    render(data.filter(function (m) { return (m.t + ' ' + m.y).toLowerCase().indexOf(q) > -1; }));
  });
  input.addEventListener('keydown', function (e) { if (e.key === 'Escape') render([]); });
  document.addEventListener('click', function (e) { if (!box.contains(e.target) && e.target !== input) render([]); });
})();
