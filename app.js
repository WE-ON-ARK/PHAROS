/* ============================================================
   PHAROS — 프로젝트 소개 사이트 인터랙션
   1) 내비게이션 / 스크롤 진행도 / 섹션 하이라이트
   2) 스크롤 진입 리빌
   3) 적응 엔진 시뮬레이터 (코어 수식 재현)
   ============================================================ */
(function () {
  'use strict';

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── 1. NAV ────────────────────────────────────────────── */
  var nav = document.getElementById('nav');
  var bar = document.getElementById('navProgress');
  var toggle = document.getElementById('navToggle');
  var links = document.getElementById('navLinks');

  function onScroll() {
    var y = window.scrollY || document.documentElement.scrollTop;
    var h = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = (h > 0 ? Math.min(100, (y / h) * 100) : 0) + '%';
    nav.classList.toggle('is-stuck', y > 12);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  toggle.addEventListener('click', function () {
    var open = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!open));
    toggle.setAttribute('aria-label', open ? '메뉴 열기' : '메뉴 닫기');
    links.classList.toggle('is-open', !open);
  });
  links.addEventListener('click', function (e) {
    if (e.target.tagName === 'A') {
      links.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    }
  });

  /* 현재 보고 있는 섹션 표시 */
  var navAnchors = Array.prototype.slice.call(links.querySelectorAll('a'));
  var targets = navAnchors
    .map(function (a) { return document.querySelector(a.getAttribute('href')); })
    .filter(Boolean);

  if ('IntersectionObserver' in window && targets.length) {
    var spy = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        navAnchors.forEach(function (a) {
          a.classList.toggle('is-active', a.getAttribute('href') === '#' + en.target.id);
        });
      });
    }, { rootMargin: '-45% 0px -50% 0px', threshold: 0 });
    targets.forEach(function (t) { spy.observe(t); });
  }

  /* ── 2. REVEAL ─────────────────────────────────────────────
     스크롤 위치를 직접 계산해 노출한다. IntersectionObserver에만
     의존하면 콜백이 실행되지 않는 환경에서 본문이 영구히 숨겨질
     수 있으므로, 스크롤·리사이즈·로드 시점마다 직접 훑는다.        */
  var pending = Array.prototype.slice.call(document.querySelectorAll('.reveal'));

  /* 같은 부모 안의 형제끼리 계단식 지연 */
  var groups = {};
  pending.forEach(function (el) {
    var key = el.parentNode.className || 'x';
    groups[key] = groups[key] || 0;
    if (!el.hasAttribute('data-delay')) el.__stagger = Math.min(groups[key]++, 6);
  });

  function revealAll() {
    pending.forEach(function (el) { el.classList.add('is-in'); });
    pending.length = 0;
  }

  function sweep() {
    var vh = window.innerHeight || document.documentElement.clientHeight || 800;
    for (var i = pending.length - 1; i >= 0; i--) {
      var el = pending[i];
      var r = el.getBoundingClientRect();
      if (r.top < vh * 0.94 && r.bottom > -80) {
        var d = parseInt(el.getAttribute('data-delay') || '0', 10);
        el.style.transitionDelay = (d * 90 + (el.__stagger || 0) * 55) + 'ms';
        el.classList.add('is-in');
        pending.splice(i, 1);
      }
    }
  }

  if (reduced) {
    revealAll();
  } else {
    var ticking = false;
    var onFrame = function () {
      ticking = false;
      sweep();
    };
    var schedule = function () {
      if (ticking) return;
      ticking = true;
      (window.requestAnimationFrame || function (f) { setTimeout(f, 16); })(onFrame);
    };
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    window.addEventListener('load', sweep);
    sweep();
    setTimeout(sweep, 400);
    setTimeout(sweep, 1500);
  }

  /* ── 3. SIMULATOR ──────────────────────────────────────── */
  var sim = document.getElementById('sim');
  if (!sim) return;

  /* 코어 상수 — PHAROS 엔진과 동일 */
  var V_MAX = 30;      // 청정 대기 기준 최대 가시거리 (m)
  var K_ATT = 3.0;     // Koschmieder 감쇄 계수 (ρ=1 → 1.49 m)
  var LAMBDA = 0.6;    // 농연에 의한 시각 전달 가치 감쇄 계수
  var MU = 0.25;       // CLI의 대체 채널 가중
  var NU = 0.10;       // 하드웨어 신뢰도 가중

  var THREATS = [
    { id: 'A', tag: 'R', name: '요구조자',        dir: 'R', B: 0.575 },
    { id: 'B', tag: 'E', name: '안전 대피로',      dir: 'F', B: 0.495 },
    { id: 'C', tag: 'F', name: '화점·플래시오버',  dir: 'F', B: 0.435 },
    { id: 'D', tag: 'S', name: '구조물 붕괴 위험', dir: 'L', B: 0.355 },
    { id: 'E', tag: 'T', name: '동료 대원 위치',   dir: 'L', B: 0.295 }
  ];
  var DIRNAME = { F: '전방', L: '좌측', R: '우측' };

  var el = {
    cli: document.getElementById('cli'),
    rf: document.getElementById('rf'),
    rl: document.getElementById('rl'),
    rr: document.getElementById('rr'),
    cliOut: document.getElementById('cliOut'),
    rfOut: document.getElementById('rfOut'),
    rlOut: document.getElementById('rlOut'),
    rrOut: document.getElementById('rrOut'),
    vfOut: document.getElementById('vfOut'),
    vlOut: document.getElementById('vlOut'),
    vrOut: document.getElementById('vrOut'),
    vfBar: document.getElementById('vfBar'),
    vlBar: document.getElementById('vlBar'),
    vrBar: document.getElementById('vrBar'),
    visor: document.getElementById('visor'),
    smoke: document.getElementById('visorSmoke'),
    mode: document.getElementById('modeBadge'),
    kOut: document.getElementById('kOut'),
    items: document.getElementById('hudItems'),
    queue: document.getElementById('queue'),
    note: document.getElementById('queueNote'),
    chans: sim.querySelectorAll('.ch')
  };

  var PRESETS = {
    normal:   { cli: 0.20, rf: 0.10, rl: 0.10, rr: 0.10 },
    stage4:   { cli: 0.20, rf: 0.00, rl: 0.00, rr: 0.99 },
    blackout: { cli: 0.72, rf: 0.86, rl: 0.80, rr: 0.90 }
  };

  function visibility(rho) { return V_MAX * Math.exp(-K_ATT * rho); }
  function fmt(n, d) { return n.toFixed(d === undefined ? 4 : d); }

  function paintRange(input) {
    input.style.setProperty('--p', (input.value * 100) + '%');
  }

  function render() {
    var cli = parseFloat(el.cli.value);
    var rho = { F: parseFloat(el.rf.value), L: parseFloat(el.rl.value), R: parseFloat(el.rr.value) };
    var V = { F: visibility(rho.F), L: visibility(rho.L), R: visibility(rho.R) };

    [el.cli, el.rf, el.rl, el.rr].forEach(paintRange);
    el.cliOut.textContent = fmt(cli, 2);
    el.rfOut.textContent = fmt(rho.F, 2);
    el.rlOut.textContent = fmt(rho.L, 2);
    el.rrOut.textContent = fmt(rho.R, 2);

    [['F', el.vfOut, el.vfBar], ['L', el.vlOut, el.vlBar], ['R', el.vrOut, el.vrBar]].forEach(function (p) {
      var v = V[p[0]];
      p[1].textContent = fmt(v, 2) + ' m';
      p[2].style.setProperty('--w', Math.max(2, (v / V_MAX) * 100) + '%');
      p[2].style.setProperty('--bp', (100 - (v / V_MAX) * 100) + '%');
    });

    /* 적응 모드 판정 — 전방 가시거리와 인지부하 기준 */
    var mode = 'NORMAL', reason = '';
    if (cli >= 0.65 || V.F < 3) {
      mode = 'EMERGENCY';
      reason = (V.F < 3 ? '전방 가시거리 ' + fmt(V.F, 2) + ' m — 시계 제로 선언' : '인지부하 ' + fmt(cli, 2) + ' — 과부하 임계 초과');
    } else if (cli > 0.45 || V.F < 10) {
      mode = 'FOCUSED';
      reason = (cli > 0.45 ? '인지부하 ' + fmt(cli, 2) + ' > 0.45 — 표시 항목 압축' : '전방 가시거리 ' + fmt(V.F, 2) + ' m — 화면 간소화');
    } else {
      reason = '인지 여유 확보 — 상위 2개 위협 표출';
    }
    var K = mode === 'NORMAL' ? 2 : 1;

    /* 전술 점수 산출 */
    var scored = THREATS.map(function (t) {
      var r = rho[t.dir], vd = V[t.dir];
      var Vi = Math.max(0, t.B * (1 - LAMBDA * r));
      var Ai = t.B * LAMBDA * r + MU * cli + NU * 1;
      var channel = vd < 3 ? 'alt' : (vd < 10 ? 'dim' : 'hud');
      return { t: t, Vi: Vi, Ai: Ai, vd: vd, rho: r, channel: channel };
    }).sort(function (a, b) { return b.Vi - a.Vi || b.t.B - a.t.B; });

    /* EMERGENCY: HUD에는 대피 경로만 남긴다 (큐 자체는 점수 순 유지) */
    var hudOrder = scored.slice();
    if (mode === 'EMERGENCY') {
      hudOrder.sort(function (a, b) {
        if (a.t.id === 'B') return -1;
        if (b.t.id === 'B') return 1;
        return b.Vi - a.Vi;
      });
    }

    el.mode.textContent = mode;
    el.visor.setAttribute('data-mode', mode);
    el.kOut.textContent = String(K);
    el.smoke.style.setProperty('--smoke', (0.05 + rho.F * 0.8).toFixed(3));

    /* HUD 렌더 */
    var shown = hudOrder.filter(function (s) { return s.channel !== 'alt'; }).slice(0, K);
    var html = '';
    if (mode === 'EMERGENCY') {
      var exit = hudOrder[0];
      html += '<li class="hitem hitem--alarm">' +
        '<span class="hitem__ico">' + exit.t.tag + '</span>' +
        '<span><span class="hitem__name">' + exit.t.name + '</span>' +
        '<span class="hitem__meta">' + DIRNAME[exit.t.dir] + ' · 대피 방위 고정</span></span>' +
        '<span class="hitem__val">' + fmt(exit.Vi) + '</span></li>';
      html += '<li class="visor__empty"><b>MAYDAY</b>그 외 모든 지시 소거 · 골전도 유도음 최대 송출</li>';
    } else if (shown.length === 0) {
      html = '<li class="visor__empty"><b>NO VISUAL</b>전 방위 시각 차단 · 전술 정보 전량 음향/햅틱 이관</li>';
    } else {
      shown.forEach(function (s, i) {
        var cls = 'hitem' + (i === 0 ? ' hitem--top' : '');
        var meta = DIRNAME[s.t.dir] + ' · V ' + fmt(s.vd, 1) + ' m' + (s.channel === 'dim' ? ' · 저휘도+골전도' : '');
        html += '<li class="' + cls + '">' +
          '<span class="hitem__ico">' + s.t.tag + '</span>' +
          '<span><span class="hitem__name">' + s.t.name + '</span>' +
          '<span class="hitem__meta">' + meta + '</span></span>' +
          '<span class="hitem__val">' + fmt(s.Vi) + '</span></li>';
      });
    }
    el.items.innerHTML = html;

    /* 우선순위 큐 — 표시 순서는 항상 전술 점수 순 */
    var onHud = {};
    shown.forEach(function (s) { onHud[s.t.id] = true; });
    var q = '';
    scored.forEach(function (s, i) {
      var cls = 'qitem';
      var state;
      if (s.channel === 'alt') { cls += ' qitem--alt'; state = '햅틱 · 골전도 이관'; }
      else if (onHud[s.t.id]) { state = mode === 'EMERGENCY' ? 'HUD 고정 · 대피 방위' : 'HUD 표출'; }
      else { cls += ' qitem--muted'; state = mode === 'EMERGENCY' ? '소거' : '대기'; }
      var drop = s.t.B - s.Vi > 0.05
        ? '<s>B ' + fmt(s.t.B, 3) + ' →</s>'
        : '';
      q += '<li class="' + cls + '">' +
        '<span class="qitem__r">' + (i + 1) + '</span>' +
        '<span class="qitem__n">' + s.t.name +
        '<small>' + DIRNAME[s.t.dir] + ' · ρ ' + fmt(s.rho, 2) + ' · ' + state + '</small></span>' +
        '<span class="qitem__v">' + drop + fmt(s.Vi) + '</span></li>';
    });
    el.queue.innerHTML = q;

    /* 채널 표시등 */
    var anyAlt = scored.some(function (s) { return s.channel === 'alt'; });
    var anyDim = scored.some(function (s) { return s.channel === 'dim'; });
    Array.prototype.forEach.call(el.chans, function (c) {
      var ch = c.getAttribute('data-ch');
      var on = true;
      if (ch === 'audio') on = anyAlt || anyDim || mode !== 'NORMAL';
      else if (ch === 'haptic') on = anyAlt || mode === 'EMERGENCY';
      c.classList.toggle('is-on', on);
    });

    /* 해설 */
    var moved = scored.filter(function (s) { return s.channel === 'alt'; });
    var note = '<b>' + mode + '</b> · ' + reason + '.';
    if (moved.length) {
      note += ' ' + moved.slice(0, 2).map(function (s) {
        return DIRNAME[s.t.dir] + ' 가시거리 ' + fmt(s.vd, 2) + ' m로 <b>' + s.t.name + '</b> 점수가 ' +
          fmt(s.t.B, 4) + ' → ' + fmt(s.Vi) + '로 강등, 햅틱·골전도로 이관';
      }).join('. ') + '.';
      if (moved.length > 2) note += ' 외 ' + (moved.length - 2) + '건도 동일하게 이관.';
      if (moved.length < THREATS.length) note += ' 나머지 방향의 점수는 그대로 보존됩니다.';
    }
    el.note.innerHTML = note;
  }

  ['cli', 'rf', 'rl', 'rr'].forEach(function (k) {
    el[k].addEventListener('input', function () {
      Array.prototype.forEach.call(sim.querySelectorAll('.chip'), function (c) { c.classList.remove('is-on'); });
      render();
    });
  });

  Array.prototype.forEach.call(sim.querySelectorAll('.chip'), function (chip) {
    chip.addEventListener('click', function () {
      var p = PRESETS[chip.getAttribute('data-preset')];
      if (!p) return;
      el.cli.value = p.cli; el.rf.value = p.rf; el.rl.value = p.rl; el.rr.value = p.rr;
      Array.prototype.forEach.call(sim.querySelectorAll('.chip'), function (c) { c.classList.remove('is-on'); });
      chip.classList.add('is-on');
      render();
    });
  });

  var first = sim.querySelector('.chip[data-preset="normal"]');
  if (first) first.classList.add('is-on');
  render();
})();
