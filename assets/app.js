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
