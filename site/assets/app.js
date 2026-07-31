import { ITEMS, STATUS, STATUS_ORDER, DOCS, BLOB_BASE } from './roadmap-data.js';

/* ------------------------------------------------------------------ util */

const $ = (sel, root = document) => root.querySelector(sel);

const el = (tag, attrs = {}, ...children) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? '' : String(v));
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
};

const ICONS = {
  check:
    '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 10.5 7.5 15 17 5"/></svg>',
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

const jaHref = (item) => `${BLOB_BASE}roadmaps/${item.dir}/${item.dir}-ja.md`;
const enHref = (item) => `${BLOB_BASE}roadmaps/${item.dir}/${item.dir}.md`;
const byId = (id) => ITEMS.find((i) => i.id === id);

/* ------------------------------------------------------------------ list */

function buildItem(item) {
  const st = STATUS[item.status];

  // メタ行。存在するものだけを中黒で連ねる
  const meta = [el('span', { text: item.topic })];
  if (item.phase) meta.push(el('span', { text: item.phase }));
  if (item.related.length) {
    meta.push(
      el(
        'span',
        {},
        '関連 ',
        item.related.flatMap((rid, i) => {
          const r = byId(rid);
          const link = r
            ? el('a', { href: jaHref(r), text: rid })
            : el('span', { text: rid });
          return i === 0 ? [link] : [document.createTextNode('、'), link];
        })
      )
    );
  }

  return el(
    'li',
    { class: 'item' },
    el(
      'div',
      { class: 'item__main' },
      el(
        'h3',
        { class: 'item__title' },
        el('a', { href: jaHref(item) }, el('span', { class: 'item__id', text: item.id }), item.title)
      ),
      item.note ? el('p', { class: 'item__note', text: item.note }) : null,
      el('p', { class: 'item__meta' }, meta)
    ),
    el(
      'div',
      { class: 'item__aside' },
      el('span', { class: `status status--${item.status}` }, icon(st.icon), st.label),
      el(
        'span',
        { class: 'item__langs' },
        el('a', { href: jaHref(item), text: '日本語' }),
        el('span', { 'aria-hidden': 'true', text: '·' }),
        el('a', { href: enHref(item), hreflang: 'en', text: 'English' })
      )
    )
  );
}

function buildList(mount) {
  // 状態ごとに束ね、束の中は採番順。並びの根拠を見出しで明示する
  STATUS_ORDER.forEach((key) => {
    const group = ITEMS.filter((i) => i.status === key);
    if (!group.length) return;
    const st = STATUS[key];

    mount.append(
      el(
        'section',
        { class: 'group', id: `status-${key}` },
        el(
          'h2',
          { class: 'group__head' },
          st.label,
          el('span', { class: 'group__count', text: `${group.length} 件` })
        ),
        el('ul', { class: 'list' }, group.map(buildItem))
      )
    );
  });
}

/* ------------------------------------------------------------------ docs */

function buildDocs(mount) {
  DOCS.forEach((d) => {
    mount.append(
      el(
        'li',
        {},
        el('a', { href: BLOB_BASE + d.file }, d.title),
        el('span', { class: 'doc__desc', text: d.desc })
      )
    );
  });
}

/* ----------------------------------------------------------------- theme */

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

/* ------------------------------------------------------------------ init */

buildList($('#list'));
buildDocs($('#docs'));
initTheme();
