(function () {
  var btn = document.querySelector('.nav-more');
  var sheet = document.getElementById('ms-nav-sheet');
  var scrim = document.getElementById('ms-nav-scrim');
  if (!btn || !sheet) return;

  function isOpen() {
    return document.body.classList.contains('nav-open');
  }

  function open() {
    document.body.classList.add('nav-open');
    btn.setAttribute('aria-expanded', 'true');
    btn.setAttribute('aria-label', 'Close menu');
    if (scrim) scrim.hidden = false;
    var first = sheet.querySelector('a');
    if (first && window.innerWidth <= 900) {
      setTimeout(function () { first.focus(); }, 60);
    }
  }

  function close() {
    document.body.classList.remove('nav-open');
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', 'Open menu');
    if (scrim && window.innerWidth > 900) scrim.hidden = true;
    else if (scrim) setTimeout(function () { if (!isOpen()) scrim.hidden = true; }, 260);
  }

  btn.addEventListener('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    if (isOpen()) close(); else open();
  });

  if (scrim) scrim.addEventListener('click', close);

  sheet.addEventListener('click', function (e) {
    if (e.target.closest('a')) close();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen()) {
      close();
      btn.focus();
    }
  });

  window.addEventListener('resize', function () {
    if (window.innerWidth > 900) close();
  });
})();
