/* georgejpappas.org — small enhancements; every page is fully readable without this script. */
(function () {
  'use strict';
  var $$ = function (sel, el) { return Array.prototype.slice.call((el || document).querySelectorAll(sel)); };
  $$('.js-only').forEach(function (el) { el.hidden = false; });

  /* Close the mobile menu after choosing a link or pressing Escape */
  $$('details.nav-mobile').forEach(function (d) {
    d.addEventListener('keydown', function (e) { if (e.key === 'Escape') { d.open = false; d.querySelector('summary').focus(); } });
  });

  /* Research: one area at a time; #area-id in the address selects it */
  var tabs = $$('.area-tab');
  if (tabs.length) {
    var panels = $$('.area-panel');
    var select = function (id, focus) {
      if (!document.getElementById(id)) id = panels[0].id;
      tabs.forEach(function (t) {
        var on = t.getAttribute('data-area') === id;
        t.setAttribute('aria-selected', on ? 'true' : 'false');
        t.tabIndex = on ? 0 : -1;
        if (on && focus) t.focus();
      });
      panels.forEach(function (p) { p.hidden = p.id !== id; });
    };
    tabs.forEach(function (t, i) {
      t.addEventListener('click', function () {
        var id = t.getAttribute('data-area');
        select(id);
        if (history.replaceState) history.replaceState(null, '', '#' + id);
      });
      t.addEventListener('keydown', function (e) {
        var j = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : null;
        if (j === null) return;
        e.preventDefault();
        j = (j + tabs.length) % tabs.length;
        select(tabs[j].getAttribute('data-area'), true);
      });
    });
    $$('.area-chip').forEach(function (c) {
      c.addEventListener('click', function (e) {
        e.preventDefault();
        var id = c.getAttribute('data-area');
        select(id);
        if (history.replaceState) history.replaceState(null, '', '#' + id);
        document.querySelector('[role="tablist"]').scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
    var aliases = { 'formal-methods': 'formal-methods-and-control', 'layered-control': 'formal-methods-and-control' };
    var fromHash = function () { var h = decodeURIComponent(location.hash.slice(1)); select(aliases[h] || h); };
    window.addEventListener('hashchange', fromHash);
    fromHash();
  }

  /* News: filter by kind */
  var newsButtons = $$('.news-filter');
  if (newsButtons.length) {
    var items = $$('.news-item');
    newsButtons.forEach(function (b) {
      b.addEventListener('click', function () {
        var k = b.getAttribute('data-filter');
        newsButtons.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
        items.forEach(function (n) { n.hidden = !(k === 'all' || n.getAttribute('data-kind') === k); });
      });
    });
  }

  /* Publications: search and type filter */
  var search = document.getElementById('pub-search');
  if (search) {
    var pubButtons = $$('.pub-filter');
    var years = $$('.pub-year');
    var empty = document.getElementById('pub-empty');
    var kind = 'all';
    var defaults = years.map(function (y) { return y.open; });
    var apply = function () {
      var q = search.value.trim().toLowerCase();
      var filtering = q !== '' || kind !== 'all';
      var shown = 0;
      years.forEach(function (y, i) {
        var n = 0;
        $$('li.pub', y).forEach(function (li) {
          var ok = (kind === 'all' || (kind === 'award' ? li.getAttribute('data-award') === '1' : kind === 'code' ? li.getAttribute('data-code') === '1' : li.getAttribute('data-kind') === kind)) &&
                   (!q || (li.querySelector('.pub-id').textContent + ' ' + li.querySelector('.pub-text').textContent).toLowerCase().indexOf(q) >= 0);
          li.hidden = !ok;
          if (ok) n++;
        });
        y.hidden = n === 0;
        y.open = filtering ? n > 0 : defaults[i];
        shown += n;
      });
      empty.hidden = shown > 0;
    };
    var timer;
    search.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(apply, 120); });
    pubButtons.forEach(function (b) {
      b.addEventListener('click', function () {
        kind = b.getAttribute('data-filter');
        pubButtons.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
        apply();
      });
    });
  }

  /* Publications: [BibTeX] opens the entry under the paper, with a copy button */
  var bibBtns = $$('.bib-btn');
  if (bibBtns.length) {
    var bibData = null;
    var loadBib = function (url) {
      if (!bibData) bibData = fetch(url).then(function (r) { return r.json(); });
      return bibData;
    };
    bibBtns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var li = btn.closest('li.pub');
        var open = li.querySelector('.bib-box');
        if (open) { open.remove(); btn.setAttribute('aria-expanded', 'false'); return; }
        loadBib(btn.closest('[data-bib]').getAttribute('data-bib')).then(function (all) {
          var box = document.createElement('div'); box.className = 'bib-box';
          var pre = document.createElement('pre'); pre.textContent = all[li.getAttribute('data-id')] || 'BibTeX not available.';
          var copy = document.createElement('button'); copy.type = 'button'; copy.className = 'bib-copy'; copy.textContent = 'Copy';
          copy.addEventListener('click', function () {
            if (navigator.clipboard) navigator.clipboard.writeText(pre.textContent).then(function () { copy.textContent = 'Copied'; });
          });
          box.appendChild(pre); box.appendChild(copy);
          li.querySelector('.pub-body').appendChild(box);
          btn.setAttribute('aria-expanded', 'true');
        });
      });
    });
  }

  /* Book: copy BibTeX */
  var copy = document.getElementById('copy-bibtex');
  if (copy) {
    copy.addEventListener('click', function () {
      var text = document.getElementById('bibtex').textContent;
      var done = function () { copy.textContent = 'Copied'; setTimeout(function () { copy.textContent = 'Copy BibTeX'; }, 2000); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () {});
      } else {
        var r = document.createRange(); r.selectNodeContents(document.getElementById('bibtex'));
        var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
        try { document.execCommand('copy'); done(); } catch (e) {}
      }
    });
  }
})();
