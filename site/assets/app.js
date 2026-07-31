import {
  AXIS_END,
  AXIS_TICKS,
  PHASES,
  CAPABILITIES,
  RISKS,
  DECISIONS,
  DECISION_STATUS,
  DOCS,
  BLOB_BASE,
} from './roadmap-data.js';

/* ------------------------------------------------------------------ util */

const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k === 'style') node.setAttribute('style', v);
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? '' : String(v));
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
};

const pct = (weeks) => (weeks / AXIS_END) * 100;
const phaseVar = (id) => `var(--phase-${id})`;
const phaseSoftVar = (id) => `var(--phase-${id}-soft)`;

/* --------------------------------------------------------------- icons */

const ICONS = {
  check:
    '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 7.5 15 17 5"/></svg>',
  ban:
    '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="10" cy="10" r="7.2"/><path d="M5 15 15 5"/></svg>',
  info:
    '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="10" cy="10" r="7.2"/><path d="M10 9v5M10 6.2v.1"/></svg>',
  alert:
    '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 2.8 18.4 17H1.6z"/><path d="M10 8v3.6M10 14.2v.1"/></svg>',
  open:
    '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="10" cy="10" r="6.4"/></svg>',
  pause:
    '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="10" cy="10" r="6.4" stroke-dasharray="2.6 2.8"/><path d="M8.4 7.8v4.4M11.6 7.8v4.4"/></svg>',
};

const icon = (name) => {
  const span = el('span');
  span.innerHTML = ICONS[name];
  return span.firstElementChild;
};

/* -------------------------------------------------------------- tooltip */

const tip = el('div', { class: 'tooltip', role: 'status', 'aria-live': 'polite' });
document.body.append(tip);

let tipAnchor = null;

function placeTip() {
  if (!tipAnchor) return;
  const r = tipAnchor.getBoundingClientRect();
  const t = tip.getBoundingClientRect();
  let left = r.left + r.width / 2 - t.width / 2;
  left = Math.max(10, Math.min(left, window.innerWidth - t.width - 10));
  let top = r.top - t.height - 10;
  if (top < 10) top = r.bottom + 10;
  tip.style.left = `${left}px`;
  tip.style.top = `${top}px`;
}

function showTip(html, target) {
  tip.innerHTML = html;
  tipAnchor = target;
  tip.dataset.open = 'true';
  placeTip();
}

function hideTip() {
  tipAnchor = null;
  tip.dataset.open = 'false';
}

/** hover / focus の両方で同じ内容を出す。ツールチップは補助であり唯一の経路にはしない。 */
function bindTip(node, htmlFn) {
  node.addEventListener('mouseenter', () => showTip(htmlFn(), node));
  node.addEventListener('focus', () => showTip(htmlFn(), node));
  node.addEventListener('mouseleave', hideTip);
  node.addEventListener('blur', hideTip);
}

/* キーボード操作の focus はスクロールを伴う。隠すのではなく追従させる。 */
window.addEventListener('scroll', placeTip, { passive: true });
window.addEventListener('resize', placeTip);
window.addEventListener('keydown', (e) => e.key === 'Escape' && hideTip());

/* ---------------------------------------------------------------- gantt */

const weekRange = (a, b) => `${a}–${b} 週`;

function phaseTiming(p) {
  const w = p.weeks;
  if (w.tentative) return { short: '未定', long: '未定' };
  if (w.open) {
    return {
      short: `${w.minStart} 週から（最長で ${w.maxStart} 週から）`,
      long: '終了を定めない（継続）',
    };
  }
  return { short: weekRange(w.minStart, w.minEnd), long: weekRange(w.maxStart, w.maxEnd) };
}

function buildGantt(mount) {
  const gantt = el('div', { class: 'gantt' });
  const rows = el('div', { class: 'gantt__rows' });

  PHASES.forEach((p) => {
    const w = p.weeks;
    const barLeft = w.minStart;
    const barRight = w.tentative || w.open ? AXIS_END : w.maxEnd;

    const track = el('div', { class: 'gantt__track' });

    // 目盛り線（実線ヘアライン、背面）
    const grid = el('div', { class: 'gantt__grid', 'aria-hidden': 'true' });
    AXIS_TICKS.forEach((t) => {
      grid.append(el('div', { class: 'gantt__gridline', style: `left:${pct(t)}%` }));
    });
    track.append(grid);

    // ヒット領域（バーより広く取る）
    const hit = el('button', {
      class: 'gantt__hit',
      type: 'button',
      style: `left:${pct(barLeft)}%;width:${pct(barRight - barLeft)}%`,
      'aria-label': `${p.label} ${p.title}、${p.duration}`,
    });
    track.append(hit);

    // バー本体
    const bar = el('div', {
      class: [
        'gantt__bar',
        w.open ? 'gantt__bar--open' : '',
        w.tentative ? 'gantt__bar--tentative' : '',
      ]
        .filter(Boolean)
        .join(' '),
      style: `left:${pct(barLeft)}%;width:${pct(barRight - barLeft)}%`,
      'aria-hidden': 'true',
    });

    const segs = [];
    if (w.maxStart > w.minStart) {
      segs.push({ span: w.maxStart - w.minStart, soft: true });
    }
    const coreStart = Math.max(w.minStart, w.maxStart);
    const coreEnd = w.open || w.tentative ? AXIS_END : w.minEnd;
    if (coreEnd > coreStart) segs.push({ span: coreEnd - coreStart, soft: false });
    if (!w.open && !w.tentative && w.maxEnd > w.minEnd) {
      segs.push({ span: w.maxEnd - w.minEnd, soft: true });
    }

    segs.forEach((s, i) => {
      bar.append(
        el('div', {
          class: [
            'gantt__seg',
            i === 0 ? 'gantt__seg--core' : '',
            i === segs.length - 1 ? 'gantt__seg--last' : '',
          ]
            .filter(Boolean)
            .join(' '),
          style: `flex:${s.span} 1 0;background:${s.soft ? phaseSoftVar(p.id) : phaseVar(p.id)}`,
        })
      );
    });
    track.append(bar);

    const timing = phaseTiming(p);
    bindTip(
      hit,
      () => `<b>${p.label} · ${p.title}</b>${p.goal}
        <dl>
          <dt>期間</dt><dd>${p.duration}</dd>
          <dt>最短</dt><dd>${timing.short}</dd>
          <dt>最長</dt><dd>${timing.long}</dd>
        </dl>`
    );
    hit.addEventListener('click', () => {
      document.getElementById(`phase-${p.id}`)?.scrollIntoView({ block: 'start' });
    });

    rows.append(
      el(
        'div',
        { class: 'gantt__row' },
        el('div', { class: 'gantt__label' }, el('b', { text: p.label }), el('span', { text: `${p.title} · ${p.duration}` })),
        track
      )
    );
  });

  // 現在地マーカー。行と同じグリッドを重ねてトラック列にだけ縦線を引く
  rows.append(
    el(
      'div',
      { class: 'gantt__row gantt__overlay', 'aria-hidden': 'true' },
      el('div'),
      el(
        'div',
        { class: 'gantt__overlay-track' },
        el('div', { class: 'gantt__now', 'data-label': '現在地 · 未着手', style: 'left:0%' })
      )
    )
  );
  gantt.append(rows);

  // x 軸
  const axis = el('div', { class: 'gantt__axis' });
  AXIS_TICKS.forEach((t, i) => {
    const isLast = i === AXIS_TICKS.length - 1;
    // 狭い画面では中間の目盛りラベルを間引いて重なりを防ぐ（グリッド線は残す）
    const isMinor = !isLast && i % 2 === 1;
    axis.append(
      el('div', {
        class: [
          'gantt__tick',
          isLast ? 'gantt__tick--last' : '',
          isMinor ? 'gantt__tick--minor' : '',
        ]
          .filter(Boolean)
          .join(' '),
        style: `left:${pct(t)}%`,
        text: isLast ? `${t} 週 →` : String(t),
      })
    );
  });
  gantt.append(el('div', { class: 'gantt__row' }, el('div'), axis));
  gantt.append(
    el('div', { class: 'gantt__row' }, el('div'), el('div', { class: 'gantt__axistitle', text: 'Phase 0 開始からの経過週' }))
  );

  mount.append(gantt);
}

function buildGanttTable(mount) {
  const body = el('tbody');
  PHASES.forEach((p) => {
    const t = phaseTiming(p);
    body.append(
      el(
        'tr',
        {},
        el('th', { scope: 'row', text: p.label }),
        el('td', { text: p.title }),
        el('td', { class: 'num', text: p.duration }),
        el('td', { class: 'num', text: t.short }),
        el('td', { class: 'num', text: t.long })
      )
    );
  });
  mount.append(
    el(
      'div',
      { class: 'table-scroll' },
      el(
        'table',
        { class: 'data' },
        el('caption', { text: 'ガントチャートと同じ値の表。週は Phase 0 開始を 0 週とした経過週。' }),
        el(
          'thead',
          {},
          el(
            'tr',
            {},
            el('th', { scope: 'col', text: 'フェーズ' }),
            el('th', { scope: 'col', text: '内容' }),
            el('th', { scope: 'col', text: '期間' }),
            el('th', { scope: 'col', text: '最短' }),
            el('th', { scope: 'col', text: '最長' })
          )
        ),
        body
      )
    )
  );
}

/* ---------------------------------------------------------- phase cards */

function buildPhases(mount) {
  PHASES.forEach((p) => {
    const card = el('article', {
      class: 'card phase',
      id: `phase-${p.id}`,
      style: `--phase-color:${phaseVar(p.id)}`,
    });

    card.append(
      el(
        'div',
        { class: 'phase__head' },
        el('span', { class: 'phase__badge', text: p.label }),
        el('h3', { class: 'phase__title', text: p.title }),
        el('span', { class: 'phase__dur', text: p.duration })
      ),
      el('p', { class: 'phase__goal', text: p.goal })
    );

    if (p.lead && p.lead !== p.goal) card.append(el('p', { class: 'phase__lead', text: p.lead }));

    if (p.layout === 'checklist') {
      const list = el('ul', { class: 'checklist' });
      p.items[0].rows.forEach((r) => list.append(el('li', { text: r })));
      card.append(list);
    } else if (p.layout === 'list') {
      const list = el('ul', { class: 'bullets' });
      p.items.forEach((it) =>
        list.append(el('li', {}, it.text, it.note ? el('small', { text: it.note }) : null))
      );
      card.append(list);
    } else {
      const body = el('tbody');
      p.items.forEach((it) =>
        body.append(
          el('tr', {}, el('th', { scope: 'row', text: it.area }), el('td', { text: it.detail }))
        )
      );
      card.append(
        el(
          'div',
          { class: 'table-scroll phase__items' },
          el(
            'table',
            { class: 'data' },
            el(
              'thead',
              {},
              el('tr', {}, el('th', { scope: 'col', text: '領域' }), el('th', { scope: 'col', text: '成果物' }))
            ),
            body
          )
        )
      );
    }

    if (p.canDo) {
      card.append(
        el(
          'div',
          { class: 'notebox notebox--done' },
          icon('check'),
          el('div', {}, el('b', { text: 'この段階でできること: ' }), p.canDo)
        )
      );
    }
    if (p.wontDo) {
      card.append(
        el(
          'div',
          { class: 'notebox notebox--wont' },
          icon('ban'),
          el('div', {}, el('b', { text: '意図的にやらないこと: ' }), p.wontDo)
        )
      );
    }
    if (p.done) {
      card.append(
        el(
          'div',
          { class: 'notebox notebox--done' },
          icon('check'),
          el('div', {}, el('b', { text: '完了条件: ' }), p.done)
        )
      );
    }
    if (p.callout) {
      card.append(
        el('div', { class: 'notebox notebox--note' }, icon('info'), el('div', { text: p.callout.text }))
      );
    }

    mount.append(card);
  });
}

/* -------------------------------------------------------------- matrix */

function buildMatrix(mount) {
  const cols = PHASES.filter((p) => !p.weeks.tentative);

  const head = el(
    'tr',
    {},
    el('th', { scope: 'col', text: '領域' }),
    cols.map((p) =>
      el('th', { scope: 'col' }, p.label, el('span', { text: p.title }))
    )
  );

  const body = el('tbody');
  CAPABILITIES.forEach((row) => {
    const tr = el('tr', {}, el('th', { scope: 'row', text: row.area }));
    cols.forEach((p) => {
      const detail = row.cells[p.id];
      if (!detail) {
        tr.append(el('td', {}, el('span', { class: 'cell cell--empty', 'aria-label': '該当なし', text: '—' })));
        return;
      }
      const cell = el(
        'span',
        {
          class: 'cell cell--filled',
          tabindex: '0',
          style: `--cell-bg:${phaseSoftVar(p.id)};--dot:${phaseVar(p.id)}`,
        },
        el('i', { class: 'cell__dot', 'aria-hidden': 'true' }),
        detail
      );
      bindTip(
        cell,
        () => `<b>${row.area}</b><dl><dt>時期</dt><dd>${p.label} · ${p.title}</dd></dl>${detail}`
      );
      tr.append(el('td', {}, cell));
    });
    body.append(tr);
  });

  mount.append(
    el(
      'table',
      { class: 'matrix' },
      el('caption', { class: 'sr-only', text: '領域ごとの導入フェーズ' }),
      el('thead', {}, head),
      body
    )
  );
}

/* --------------------------------------------------------------- risks */

function buildRisks(mount) {
  RISKS.forEach((r) => {
    const phase = PHASES.find((p) => p.id === r.phase);
    mount.append(
      el(
        'article',
        { class: 'card risk' },
        el('div', { class: 'risk__head' }, icon('alert'), el('span', { text: r.risk })),
        el('p', { class: 'risk__body', text: r.mitigation }),
        el(
          'span',
          { class: 'risk__phase' },
          el('i', { style: `background:${phaseVar(r.phase)}`, 'aria-hidden': 'true' }),
          `対処は ${phase.label}`
        )
      )
    );
  });
}

/* ----------------------------------------------------------- decisions */

function buildDecisions(mount) {
  const body = el('tbody');

  DECISIONS.forEach((d) => {
    const st = DECISION_STATUS[d.status];
    const phase = d.phase === null ? null : PHASES.find((p) => p.id === d.phase);

    body.append(
      el(
        'tr',
        {},
        el(
          'th',
          { scope: 'row' },
          el('a', { href: `${BLOB_BASE}roadmaps/${d.dir}/${d.dir}-ja.md`, text: d.id })
        ),
        el('td', {}, d.title, d.note ? el('small', { class: 'sub', text: d.note }) : null),
        // 状態は色だけで伝えない。必ずアイコン + ラベルの組で出す
        el(
          'td',
          {},
          el('span', { class: `dstatus dstatus--${d.status}` }, icon(st.icon), st.label)
        ),
        el(
          'td',
          {},
          phase
            ? el(
                'span',
                { class: 'dphase' },
                el('i', { style: `background:${phaseVar(phase.id)}`, 'aria-hidden': 'true' }),
                phase.label
              )
            : el('span', { class: 'dphase dphase--none', text: '未割当' })
        )
      )
    );
  });

  mount.append(
    el(
      'div',
      { class: 'table-scroll' },
      el(
        'table',
        { class: 'data data--decisions' },
        el(
          'thead',
          {},
          el(
            'tr',
            {},
            el('th', { scope: 'col', text: 'ID' }),
            el('th', { scope: 'col', text: '論点' }),
            el('th', { scope: 'col', text: '状態' }),
            el('th', { scope: 'col', text: '関係するフェーズ' })
          )
        ),
        body
      )
    )
  );
}

/* ---------------------------------------------------------------- docs */

function buildDocs(mount) {
  DOCS.forEach((d) => {
    mount.append(
      el(
        'a',
        { class: 'card doc', href: BLOB_BASE + d.file },
        el('b', { text: d.title }),
        el('span', { text: d.desc })
      )
    );
  });
}

/* --------------------------------------------------------------- stats */

function buildStats(mount) {
  const p2 = PHASES.find((p) => p.id === 2);
  const tiles = [
    { value: String(PHASES.length), unit: 'フェーズ', label: 'Phase 0 〜 4' },
    {
      value: `${p2.weeks.minEnd}–${p2.weeks.maxEnd}`,
      unit: '週',
      label: 'Phase 2 完了までの見積り',
    },
    { value: String(CAPABILITIES.length), unit: '領域', label: 'ロードマップが触るケイパビリティ' },
    { value: String(RISKS.length), unit: '件', label: '明示されたリスクと対処' },
  ];
  tiles.forEach((t) => {
    mount.append(
      el(
        'div',
        { class: 'stat' },
        el('span', { class: 'stat__value' }, t.value, el('small', { text: t.unit })),
        el('span', { class: 'stat__label', text: t.label })
      )
    );
  });
}

/* --------------------------------------------------------------- theme */

function initTheme() {
  const KEY = 'bakuchi-theme';
  const stored = localStorage.getItem(KEY);
  if (stored === 'light' || stored === 'dark') document.documentElement.dataset.theme = stored;

  $('#theme-toggle').addEventListener('click', () => {
    const current =
      document.documentElement.dataset.theme ||
      (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem(KEY, next);
  });
}

/* ----------------------------------------------------------------- init */

buildStats($('#stats'));
buildGantt($('#gantt-mount'));
buildGanttTable($('#gantt-table'));
buildPhases($('#phases'));
buildMatrix($('#matrix-mount'));
buildRisks($('#risks'));
buildDecisions($('#decisions'));
buildDocs($('#docs'));
initTheme();

const tableBtn = $('#gantt-table-toggle');
tableBtn.addEventListener('click', () => {
  const view = $('#gantt-table');
  const open = view.hasAttribute('hidden');
  view.toggleAttribute('hidden', !open);
  tableBtn.setAttribute('aria-expanded', String(open));
  tableBtn.textContent = open ? 'チャートだけ表示' : '表で見る';
});
