/* Checking off learned questions. The state lives in the browser's
   localStorage — no account, no server, nothing is sent anywhere.

   The key is "subject/card/question", for example "lov-zvere/karta-1/A3".
   On a card page questions are checked off with the circle next to them; in
   the index they are only counted: a card is done once all its questions
   are done. */
(function () {
  'use strict';

  /* Right away, before rendering: without the script a check-off would have
     nowhere to be stored, so the marks are hidden in CSS and only this class
     reveals them. */
  document.documentElement.classList.add('js');

  var KEY = 'myslitest:learned';

  /* The state used to be stored under a Czech key; anyone who checked
     questions off back then must not lose them. It is migrated on the first
     load and the old key is removed. */
  var OLD_KEY = 'myslitest:naucene';

  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (raw === null) {
        raw = localStorage.getItem(OLD_KEY);
        if (raw !== null) {
          localStorage.setItem(KEY, raw);
          localStorage.removeItem(OLD_KEY);
        }
      }
      var d = JSON.parse(raw);
      return (d && typeof d === 'object') ? d : {};
    } catch (e) {
      return {};                 /* broken or unavailable storage */
    }
  }

  function save(state) {
    try {
      localStorage.setItem(KEY, JSON.stringify(state));
    } catch (e) {
      /* storage full or blocked: the check-off holds for this visit at least */
    }
  }

  /* The circle and the index mark belong to the state, not to the content —
     they are not in the HTML, they are built here. Without the script there
     would be no way to check them off anyway. */
  function checkbox(key) {
    var parts = /^([A-Z])?(\d+)$/.exec(key) || [];
    var block = parts[1] ? 'blok ' + parts[1] + ', ' : '';
    var button = document.createElement('button');
    button.className = 'learned';
    button.type = 'button';
    button.setAttribute('aria-pressed', 'false');
    button.setAttribute('aria-label', 'Naučeno – ' + block + 'otázka ' + parts[2]);
    return button;
  }

  function statusMark() {
    var mark = document.createElement('span');
    mark.className = 'status';
    mark.setAttribute('role', 'img');
    return mark;
  }

  /* Learned questions by group; the caller's key function says what a group
     is. */
  function countBy(state, group) {
    var totals = {};
    for (var id in state) {
      if (!Object.prototype.hasOwnProperty.call(state, id)) continue;
      var key = group(id);
      if (!key) continue;
      totals[key] = (totals[key] || 0) + 1;
    }
    return totals;
  }

  /* A numeral takes the genitive: "z 10 otázek", but "z 1 otázky". */
  function questionsWord(n) {
    return n === 1 ? 'otázky' : 'otázek';
  }

  function progressLabel(done, total) {
    if (total > 0 && done >= total) {
      return 'Hotovo, naučeno všech ' + total + ' ' + questionsWord(total);
    }
    return 'Naučeno ' + done + ' z ' + total + ' ' + questionsWord(total)
      + ', zbývá ' + (total - done);
  }

  /* --- card page: a circle next to every question --- */
  function cardPage(state) {
    var article = document.querySelector('.card[data-card]');
    if (!article) return;

    var prefix = article.getAttribute('data-card');
    var questions = article.querySelectorAll('.question[data-question]');
    if (!questions.length) return;

    var total = questions.length;

    /* The summary belongs to the state, not to the card content, which is
       why it is created here. */
    var summary = document.createElement('p');
    summary.className = 'progress';
    var header = article.querySelector('.card-header');
    if (header) {
      header.insertAdjacentElement('afterend', summary);
    } else {
      article.insertBefore(summary, article.firstChild);
    }

    function renderSummary() {
      var done = article.querySelectorAll('.learned[aria-pressed="true"]').length;
      summary.textContent = progressLabel(done, total);
      summary.classList.toggle('done', done >= total);
    }

    Array.prototype.forEach.call(questions, function (li) {
      var id = prefix + '/' + li.getAttribute('data-question');
      var button = checkbox(li.getAttribute('data-question'));
      li.appendChild(button);

      function setPressed(on) {
        button.setAttribute('aria-pressed', on ? 'true' : 'false');
        button.title = on ? 'Naučeno – klepnutím značku sundáš'
                          : 'Označit jako naučené';
      }

      setPressed(state[id] === true);

      button.addEventListener('click', function () {
        var on = button.getAttribute('aria-pressed') !== 'true';
        if (on) {
          state[id] = true;
        } else {
          delete state[id];      /* keep unchecked questions out of the state */
        }
        setPressed(on);
        save(state);
        renderSummary();
      });
    });

    renderSummary();
  }

  /* --- subject index: the mark only shows how far along the card is --- */
  function cardGrid(state) {
    var rows = document.querySelectorAll('.grid > li[data-card]');
    if (!rows.length) return;

    /* "subject/card/question" without the last part is the card */
    var learned = countBy(state, function (id) {
      var slash = id.lastIndexOf('/');
      return slash < 0 ? '' : id.slice(0, slash);
    });

    Array.prototype.forEach.call(rows, function (row) {
      var mark = statusMark();
      row.appendChild(mark);

      var prefix = row.getAttribute('data-card');
      var total = parseInt(row.getAttribute('data-questions'), 10) || 0;
      var done = Math.min(learned[prefix] || 0, total);
      var all = total > 0 && done >= total;

      /* The ratio is written the same way as for subjects on the home page;
         the full sentence is available on hover. */
      mark.textContent = done + '/' + total;
      mark.classList.toggle('done', all);

      var part = prefix.split('/')[1] || '';
      var word = part.indexOf('okruh') === 0 ? 'Okruh' : 'Karta';
      var number = part.replace(/^\D+/, '');
      var label = word + ' ' + number + ': ' + progressLabel(done, total);
      mark.title = label;
      mark.setAttribute('aria-label', label);
    });
  }

  /* --- home page: how many of a subject's questions are learned --- */
  function subjectList(state) {
    var rows = document.querySelectorAll('.subjects > li[data-subject]');
    if (!rows.length) return;

    /* the first part of the key is the subject */
    var learned = countBy(state, function (id) {
      var slash = id.indexOf('/');
      return slash < 0 ? '' : id.slice(0, slash);
    });

    Array.prototype.forEach.call(rows, function (row) {
      var count = row.querySelector('.count');
      if (!count) return;

      var total = parseInt(row.getAttribute('data-questions'), 10) || 0;
      var done = Math.min(learned[row.getAttribute('data-subject')] || 0, total);

      /* Without the script this shows the bare question count; only here does
         it become a ratio. The full sentence is available on hover; in the row
         it would only get in the way. */
      count.textContent = done + '/' + total;
      count.classList.toggle('done', total > 0 && done >= total);

      var label = progressLabel(done, total);
      count.title = label;
      count.setAttribute('aria-label', label);
    });
  }

  function start() {
    var state = load();
    cardPage(state);
    cardGrid(state);
    subjectList(state);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
