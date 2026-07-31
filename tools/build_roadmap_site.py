#!/usr/bin/env python3
"""roadmaps/ から GitHub Pages のロードマップサイトを生成する。

状態・トピック・進捗・関連は、すべて roadmaps/ 配下の項目そのものから読む。
ページはビルドのたびに生成し直すので、記録と表示がずれることはない。手で書き写した
値はひとつも持たない。

出力:
  site/index.html          英語版
  site/ja/index.html       日本語版
  site/assets/style.css
  site/assets/app.js
  site/assets/favicon.svg
  site/.nojekyll

使い方:
  python3 tools/build_roadmap_site.py [--out site] [--check]

--check は生成せずに、いま出力されているものが最新かどうかだけを判定する
（差分があれば終了コード 1）。CI でページの陳腐化を検出するために使う。
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROADMAPS = REPO / 'roadmaps'
GITHUB = 'https://github.com/0x0c/bakuchi'
BLOB = f'{GITHUB}/blob/main'

# 状態の正規化。英語版の Status セルを鍵にする（日本語表記の揺れに依存しない）。
STATUS_KEYS = {
    'implemented': 'implemented',
    'in progress': 'in-progress',
    'accepted': 'accepted',
    'proposal (deferred)': 'deferred',
    'deferred': 'deferred',
    'proposal': 'proposal',
}

# 積み上げ棒とチップの並び順。決着した状態から未決の状態へ向かう。
# 配色はこの順序で検証済み（隣接ペアの CVD 分離と面とのコントラスト）。
STATUS_ORDER = ['implemented', 'in-progress', 'accepted', 'proposal', 'deferred']

INTRO_HEADS = {'en': 'Introduction', 'ja': 'はじめに'}
PROGRESS_HEADS = {'en': 'Progress', 'ja': '進捗'}
INTRO_LIMIT = 200


@dataclass
class Doc:
    """1 つの言語版の中身。"""

    title: str
    status_label: str
    topic_label: str
    intro: str
    checks: list[tuple[bool, str]] = field(default_factory=list)


@dataclass
class Item:
    id: str
    dir: str
    status: str
    topic_key: str
    related: list[str]
    author: str
    docs: dict[str, Doc]

    def href(self, lang: str) -> str:
        name = f'{self.dir}-ja.md' if lang == 'ja' else f'{self.dir}.md'
        return f'{BLOB}/roadmaps/{self.dir}/{name}'

    @property
    def total(self) -> int:
        return len(self.docs['en'].checks)

    @property
    def done(self) -> int:
        return sum(1 for ticked, _ in self.docs['en'].checks if ticked)


# --------------------------------------------------------------------- parse


def strip_markdown(text: str) -> str:
    """本文を 1 行の素の文へ均す。リンクはラベルだけ残す。"""
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = text.replace('`', '')
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    return re.sub(r'\s+', ' ', text).strip()


def section(body: str, heading: str) -> str:
    """`## <heading>` から次の `## ` までを返す。"""
    pattern = rf'^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)'
    found = re.search(pattern, body, re.M | re.S)
    return found.group(1) if found else ''


def first_paragraph(text: str) -> str:
    for block in re.split(r'\n\s*\n', text.strip()):
        block = block.strip()
        if block and not block.startswith(('#', '|', '<!--')):
            return strip_markdown(block)
    return ''


def clip(text: str, limit: int = INTRO_LIMIT) -> str:
    return text if len(text) <= limit else text[:limit].rstrip() + '…'


def checkboxes(text: str) -> list[tuple[bool, str]]:
    """`- [ ]` / `- [x]` を拾う。字下げした継続行は同じ項目に畳む。"""
    items: list[tuple[bool, list[str]]] = []
    for line in text.splitlines():
        box = re.match(r'^\s*-\s+\[([ xX])\]\s*(.*)$', line)
        if box:
            items.append((box.group(1).lower() == 'x', [box.group(2)]))
        elif items and line.startswith((' ', '\t')) and line.strip():
            items[-1][1].append(line.strip())
    return [(ticked, strip_markdown(' '.join(parts))) for ticked, parts in items]


def metadata(body: str) -> dict[str, str]:
    block = re.search(r'<!--\s*BK-METADATA\s*-->(.*?)<!--\s*/BK-METADATA\s*-->', body, re.S)
    if not block:
        return {}
    rows: dict[str, str] = {}
    for line in block.group(1).strip().splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) == 2 and not set(cells[1]) <= {'-', ':'}:
            rows[cells[0]] = cells[1]
    return rows


def read_doc(path: Path, lang: str) -> tuple[Doc, dict[str, str], str]:
    body = path.read_text(encoding='utf-8')
    heading = re.search(r'^#\s+(.+)$', body, re.M)
    if not heading:
        raise SystemExit(f'{path}: 見出し（# BK-xxxx — …）が見つからない')
    # 「BK-0006 — 表題」から表題だけを取る。em ダッシュは書式で固定されている。
    title = heading.group(1).split('—', 1)[-1].strip()

    rows = metadata(body)
    status = rows.get('Status') or rows.get('状態') or ''
    topic = rows.get('Topic') or rows.get('トピック') or ''

    doc = Doc(
        title=title,
        status_label=strip_markdown(status),
        topic_label=strip_markdown(topic),
        intro=clip(first_paragraph(section(body, INTRO_HEADS[lang]))),
        checks=checkboxes(section(body, PROGRESS_HEADS[lang])),
    )
    return doc, rows, heading.group(1).split('—', 1)[0].strip()


def load_items() -> list[Item]:
    items: list[Item] = []
    for directory in sorted(ROADMAPS.glob('BK-*')):
        if not directory.is_dir():
            continue
        en_path = directory / f'{directory.name}.md'
        ja_path = directory / f'{directory.name}-ja.md'
        if not en_path.exists() or not ja_path.exists():
            raise SystemExit(f'{directory.name}: 日英どちらかの版がない')

        en, rows, item_id = read_doc(en_path, 'en')
        ja, _, _ = read_doc(ja_path, 'ja')

        key = STATUS_KEYS.get(en.status_label.lower())
        if key is None:
            raise SystemExit(f'{item_id}: 未知の Status「{en.status_label}」')
        if len(en.checks) != len(ja.checks):
            raise SystemExit(
                f'{item_id}: 進捗の項目数が日英で食い違う（en {len(en.checks)} / ja {len(ja.checks)}）'
            )

        items.append(
            Item(
                id=item_id,
                dir=directory.name,
                status=key,
                topic_key=slug(en.topic_label),
                related=sorted(set(re.findall(r'BK-\d{4}', rows.get('Related', '')))),
                author=(re.search(r'@[\w-]+', rows.get('Author', '')) or [''])[0]
                if re.search(r'@[\w-]+', rows.get('Author', ''))
                else '',
                docs={'en': en, 'ja': ja},
            )
        )
    if not items:
        raise SystemExit('roadmaps/ に BK 項目が見つからない')
    return items


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-') or 'other'


def last_updated() -> str:
    """roadmaps/ に最後に触れたコミットの時刻。git がなければ最終更新時刻。"""
    try:
        stamp = subprocess.run(
            ['git', '-C', str(REPO), 'log', '-1', '--format=%cI', '--', 'roadmaps'],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        ).stdout.strip()
        if stamp:
            return stamp
    except (OSError, subprocess.SubprocessError):
        pass
    newest = max(p.stat().st_mtime for p in ROADMAPS.rglob('*.md'))
    import datetime

    return datetime.datetime.utcfromtimestamp(newest).strftime('%Y-%m-%dT%H:%M:%SZ')


# ------------------------------------------------------------------ strings

TEXT = {
    'en': {
        'lang': 'en',
        'title': 'bakuchi roadmap',
        'desc': (
            "Every design decision behind bakuchi's iOS / Android experimentation platform, "
            'on one board: status, topic, progress, and how the items relate.'
        ),
        'skip': 'Skip to the roadmap',
        'other_lang': '日本語',
        'other_href': 'ja/',
        'other_code': 'ja',
        'theme': 'Theme',
        'theme_auto': 'Auto',
        'theme_light': 'Light',
        'theme_dark': 'Dark',
        'eyebrow': 'Mobile experimentation platform',
        'h1': 'Roadmap',
        'lede': (
            "Every design decision behind bakuchi's iOS / Android experimentation platform, on "
            'one board. Each item records what we are building, why, and what we rejected. '
            'Status, topic, and progress are read straight from the files under roadmaps/, and '
            'the page is regenerated on every build, so it cannot drift from the roadmap it '
            'describes.'
        ),
        'updated': 'Roadmap last updated',
        'overview': 'Overview',
        'items_label': 'roadmap items',
        'topics_sub': 'across {n} topics',
        'status_chart': 'Status composition',
        'status_alt': 'Every roadmap item by status: {parts}.',
        'work_chart': 'Work items completed',
        'boxes_note': '{done} of {total} boxes ticked across every item’s Progress section',
        'search_label': 'Search roadmap items',
        'search_hint': 'Search by ID, title, topic, or status…',
        'views_label': 'Choose a layout',
        'view_cards': 'Cards',
        'view_table': 'Table',
        'view_map': 'Map',
        'status': 'Status',
        'topic': 'Topic',
        'implemented_of': '{done}/{total} implemented',
        'work_items': '{done}/{total} work items',
        'related': 'Related',
        'checklist': 'Progress checklist',
        'th_id': 'ID',
        'th_item': 'Item',
        'th_topic': 'Topic',
        'th_status': 'Status',
        'th_progress': 'Progress',
        'th_updated': 'Updated',
        'map_caption': (
            'Items sit left to right by identifier and group into rows by topic. A line joins '
            'two items that name each other under Related.'
        ),
        'map_alt': 'A map of the roadmap items, grouped by topic and joined by their relations.',
        'map_readout': 'Point at an item to read its title. Selecting one opens its full record.',
        'empty_query': 'No roadmap item matches “{query}”.',
        'empty_filters': 'No roadmap item matches the current filters.',
        'foot': 'Generated from the roadmaps/ directory of',
        'foot_how': 'How the roadmap works',
        'foot_plan': 'Phased build plan',
        'how_href': f'{BLOB}/roadmaps/README.md',
        'plan_href': f'{BLOB}/docs/09-roadmap.md',
        'statuses': {
            'implemented': 'Implemented',
            'in-progress': 'In progress',
            'accepted': 'Accepted',
            'proposal': 'Proposal',
            'deferred': 'Deferred',
        },
    },
    'ja': {
        'lang': 'ja',
        'title': 'bakuchi ロードマップ',
        'desc': (
            'bakuchi の iOS / Android 実験プラットフォームについて、設計上の決定を 1 つの画面に'
            'まとめました。状態、トピック、進捗、項目どうしの関連を見渡せます。'
        ),
        'skip': 'ロードマップ本体へ移動',
        'other_lang': 'English',
        'other_href': '../',
        'other_code': 'en',
        'theme': '配色',
        'theme_auto': '自動',
        'theme_light': '明るい',
        'theme_dark': '暗い',
        'eyebrow': 'モバイル実験プラットフォーム',
        'h1': 'ロードマップ',
        'lede': (
            'bakuchi の iOS / Android 実験プラットフォームについて、設計上の決定を 1 つの画面に'
            'まとめました。各項目は、何を作るのか、なぜそうするのか、何を採らなかったのかを記録'
            'します。状態、トピック、進捗は roadmaps/ 配下のファイルから直接読み取ります。'
            'ビルドのたびに生成し直すため、記録と表示がずれることはありません。'
        ),
        'updated': 'ロードマップの最終更新',
        'overview': '概要',
        'items_label': 'ロードマップ項目',
        'topics_sub': '{n} つのトピック',
        'status_chart': '状態の内訳',
        'status_alt': 'ロードマップ項目を状態ごとに数えた内訳です。{parts}。',
        'work_chart': '完了した作業項目',
        'boxes_note': '全項目の進捗のうち {total} 件中 {done} 件が完了',
        'search_label': 'ロードマップ項目を検索',
        'search_hint': 'ID、題名、トピック、状態で絞り込む',
        'views_label': '表示方法を選ぶ',
        'view_cards': 'カード',
        'view_table': '表',
        'view_map': '関連図',
        'status': '状態',
        'topic': 'トピック',
        'implemented_of': '{total} 件中 {done} 件が完了',
        'work_items': '作業 {total} 件中 {done} 件',
        'related': '関連',
        'checklist': '進捗',
        'th_id': 'ID',
        'th_item': '項目',
        'th_topic': 'トピック',
        'th_status': '状態',
        'th_progress': '進捗',
        'th_updated': '更新',
        'map_caption': (
            '項目は採番順に左から右へ並び、トピックごとに行をなします。'
            '関連として互いを挙げている項目どうしを線でつなぎます。'
        ),
        'map_alt': 'ロードマップ項目をトピックごとに並べ、関連を線で結んだ図です。',
        'map_readout': '点にカーソルを合わせると題名を表示します。選ぶと項目の本文を開きます。',
        'empty_query': '「{query}」に一致する項目はありません。',
        'empty_filters': '現在の絞り込み条件に一致する項目はありません。',
        'foot': 'このページは次のリポジトリの roadmaps/ ディレクトリから生成しています。',
        'foot_how': 'ロードマップの読み方',
        'foot_plan': '段階的構築計画',
        'how_href': f'{BLOB}/roadmaps/README-ja.md',
        'plan_href': f'{BLOB}/docs/09-roadmap.md',
        'statuses': {
            'implemented': '実装済み',
            'in-progress': '進行中',
            'accepted': '可決',
            'proposal': '提案',
            'deferred': '提案（保留）',
        },
    },
}


# ------------------------------------------------------------------- render

E = html.escape


def pct(done: int, total: int) -> float:
    return 0.0 if not total else 100.0 * done / total


def topic_order(items: list[Item]) -> list[str]:
    """件数の多いトピックから。同数なら最も若い採番の順。並びは入力だけで決まる。"""
    keys = {}
    for item in items:
        keys.setdefault(item.topic_key, []).append(item.id)
    return sorted(keys, key=lambda k: (-len(keys[k]), keys[k][0]))


def status_counts(items: list[Item]) -> list[tuple[str, int]]:
    return [(k, sum(1 for i in items if i.status == k)) for k in STATUS_ORDER
            if any(i.status == k for i in items)]


def search_blob(item: Item, doc: Doc, t: dict) -> str:
    return E(' '.join([item.id, doc.title, doc.topic_label,
                       t['statuses'][item.status]]).lower())


def data_attrs(item: Item, doc: Doc, t: dict) -> str:
    return (f' data-id="{E(item.id)}" data-status="{item.status}"'
            f' data-topic="{E(item.topic_key)}" data-search="{search_blob(item, doc, t)}"')


def meter(done: int, total: int, label: str) -> str:
    return (f'<div class="meter meter-sm" role="img" aria-label="{E(label)}" title="{E(label)}">'
            f'<span class="meter-fill" style="width:{pct(done, total):.4g}%"></span></div>')


def legend(counts: list[tuple[str, int]], total: int, t: dict) -> str:
    parts = []
    for key, n in counts:
        share = 0 if not total else round(100 * n / total)
        parts.append(
            f'<li class="legend-item"><span class="swatch" data-status="{key}"></span>'
            f'<span class="legend-name">{E(t["statuses"][key])}</span>'
            f'<span class="legend-value">{n}</span>'
            f'<span class="legend-share">{share}%</span></li>'
        )
    return f'<ul class="legend">{"".join(parts)}</ul>'


def stack(counts: list[tuple[str, int]], t: dict, small: bool = False) -> str:
    alt = '、'.join(f'{t["statuses"][k]} {n}' for k, n in counts) if t['lang'] == 'ja' \
        else ', '.join(f'{t["statuses"][k]} {n}' for k, n in counts)
    segs = []
    for key, n in counts:
        value = '' if small else f'<span class="seg-value">{n}</span>'
        segs.append(
            f'<span class="seg" data-status="{key}" style="flex-grow:{n}"'
            f' title="{E(t["statuses"][key])}: {n}">{value}</span>'
        )
    cls = 'stack stack-sm' if small else 'stack'
    label = alt if small else E(t['status_alt'].format(parts=alt))
    return f'<div class="{cls}" role="img" aria-label="{E(label) if small else label}">' \
           f'{"".join(segs)}</div>'


def card(item: Item, lang: str, t: dict) -> str:
    doc = item.docs[lang]
    work = t['work_items'].format(done=item.done, total=item.total)
    rel = ''
    if item.related:
        links = ''.join(
            f'<a class="rel" href="{E(by_id[r].href(lang))}">{E(r)}</a>'
            for r in item.related if r in by_id
        )
        if links:
            rel = (f'<p class="card-rel"><span class="card-rel-label">{E(t["related"])}</span>'
                   f'{links}</p>')

    checks = ''
    if item.total:
        boxes = ''.join(
            f'<li class="check" data-checked="{str(ticked).lower()}">{E(text)}</li>'
            for ticked, text in doc.checks
        )
        checks = (f'<details class="card-details"><summary>{E(t["checklist"])}'
                  f'<span class="card-boxes">{E(work)}</span></summary>'
                  f'<ol class="checklist">{boxes}</ol></details>')

    author = f'<span>{E(item.author)}</span>' if item.author else ''
    return (
        f'<article class="card"{data_attrs(item, doc, t)}>'
        f'<div class="card-top"><span class="card-id">{E(item.id)}</span>'
        f'<span class="badge" data-status="{item.status}">{E(t["statuses"][item.status])}</span>'
        f'</div>'
        f'<h4 class="card-title"><a href="{E(item.href(lang))}">{E(doc.title)}</a></h4>'
        f'<p class="card-intro">{E(doc.intro)}</p>'
        f'<div class="card-progress">{meter(item.done, item.total, work)}'
        f'<span class="card-progress-text">{E(work)}</span></div>'
        f'<p class="card-meta"><span>{E(doc.topic_label)}</span>{author}</p>'
        f'{rel}{checks}</article>'
    )


def cards_view(items: list[Item], lang: str, t: dict) -> str:
    out = []
    for key in topic_order(items):
        group = [i for i in items if i.topic_key == key]
        done = sum(1 for i in group if i.status == 'implemented')
        counts = status_counts(group)
        label = group[0].docs[lang].topic_label
        out.append(
            f'<section class="topic" data-topic="{E(key)}">'
            f'<header class="topic-head"><h3 class="topic-name">{E(label)}</h3>'
            f'<p class="topic-prog"><span class="topic-pct">{pct(done, len(group)):.0f}%</span>'
            f'<span class="topic-detail">'
            f'{E(t["implemented_of"].format(done=done, total=len(group)))}</span></p>'
            f'{stack(counts, t, small=True)}</header>'
            f'<div class="cards">{"".join(card(i, lang, t) for i in group)}</div></section>'
        )
    return f'<div class="view view-cards">{"".join(out)}</div>'


def table_view(items: list[Item], lang: str, t: dict, updated: str) -> str:
    heads = ''.join(
        f'<th scope="col" data-sort-key="{k}" aria-sort="none" tabindex="0">{E(t[label])}</th>'
        for k, label in [('id', 'th_id'), ('title', 'th_item'), ('topic', 'th_topic'),
                         ('status', 'th_status'), ('progress', 'th_progress'),
                         ('updated', 'th_updated')]
    )
    rows = []
    for item in items:
        doc = item.docs[lang]
        work = t['work_items'].format(done=item.done, total=item.total)
        rows.append(
            f'<tr class="row"{data_attrs(item, doc, t)}>'
            f'<td class="cell-id" data-sort="{E(item.id)}">{E(item.id)}</td>'
            f'<th scope="row" class="cell-title">'
            f'<a href="{E(item.href(lang))}">{E(doc.title)}</a></th>'
            f'<td>{E(doc.topic_label)}</td>'
            f'<td><span class="badge" data-status="{item.status}">'
            f'{E(t["statuses"][item.status])}</span></td>'
            f'<td data-sort="{pct(item.done, item.total) / 100:.4f}">'
            f'<span class="cell-progress">{meter(item.done, item.total, work)}'
            f'<span class="cell-progress-text">{item.done}/{item.total}</span></span></td>'
            f'<td class="cell-date" data-sort="{E(updated)}">{E(updated[:10])}</td></tr>'
        )
    return (f'<div class="view view-table is-hidden"><div class="table-scroll">'
            f'<table class="table"><thead><tr>{heads}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></div>')


def text_width(label: str, size: float = 12.0) -> float:
    """SVG のラベル幅の見積り。全角は 1em、半角は 0.55em として数える。

    SVG は本文を測ってから折り返してくれないので、行ラベルの列幅はここで決める。
    見積りを外すと長いトピック名が図の左に食み出す。
    """
    return size * sum(1.0 if ord(ch) > 0x2E80 else 0.55 for ch in label)


def map_view(items: list[Item], lang: str, t: dict) -> str:
    """採番順に左から右、トピックごとに行。関連を線で結ぶ。"""
    order = topic_order(items)
    row_h, top, bottom, inner = 92, 86, 80, 710.0
    labels = [next(i.docs[lang].topic_label for i in items if i.topic_key == k) for k in order]
    label_x = max(150.0, max(text_width(x) for x in labels) + 8.0)
    rule_x1 = label_x + 12.0
    rule_x2 = rule_x1 + inner
    width = rule_x2 + 28.0
    height = top + row_h * (len(order) - 1) + bottom

    step = (rule_x2 - rule_x1) / len(items)
    x = {item.id: rule_x1 + step / 2 + i * step for i, item in enumerate(items)}
    y = {item.id: float(top + row_h * order.index(item.topic_key)) for item in items}

    rows = ''.join(
        f'<g class="map-row"><line class="map-rule" x1="{rule_x1:.1f}"'
        f' y1="{top + row_h * i:.1f}" x2="{rule_x2:.1f}" y2="{top + row_h * i:.1f}"/>'
        f'<text class="map-row-label" x="{label_x:.0f}" y="{top + row_h * i:.1f}"'
        f' text-anchor="end" dominant-baseline="middle">{E(label)}</text></g>'
        for i, label in enumerate(labels)
    )

    seen: set[tuple[str, str]] = set()
    edges = []
    for item in items:
        for other in item.related:
            if other not in by_id:
                continue
            pair = tuple(sorted((item.id, other)))
            if pair in seen:
                continue
            seen.add(pair)
            a, b = pair
            x1, y1, x2, y2 = x[a], y[a], x[b], y[b]
            if y1 == y2:
                path = f'M{x1:.1f},{y1:.1f} Q{(x1 + x2) / 2:.1f},{y1 - 38:.1f} {x2:.1f},{y2:.1f}'
            else:
                dx = x2 - x1
                path = (f'M{x1:.1f},{y1:.1f} C{x1 + dx * 0.4:.1f},{y1:.1f}'
                        f' {x1 + dx * 0.6:.1f},{y2:.1f} {x2:.1f},{y2:.1f}')
            edges.append(f'<path class="map-edge" d="{path}" data-a="{E(a)}" data-b="{E(b)}"/>')

    nodes = []
    for item in items:
        doc = item.docs[lang]
        caption = f'{item.id} — {doc.title}'
        cx, cy = x[item.id], y[item.id]
        nodes.append(
            f'<a class="map-node" href="{E(item.href(lang))}"{data_attrs(item, doc, t)}'
            f' data-caption="{E(caption)}"'
            f' data-status-label="{E(t["statuses"][item.status])}">'
            f'<title>{E(caption)}</title>'
            f'<circle class="map-hit" cx="{cx:.1f}" cy="{cy:.1f}" r="21"/>'
            f'<circle class="map-dot" cx="{cx:.1f}" cy="{cy:.1f}" r="9"/>'
            f'<text class="map-label" x="{cx:.1f}" y="{cy + 24:.1f}"'
            f' text-anchor="middle">{E(item.id)}</text></a>'
        )

    counts = status_counts(items)
    return (
        f'<div class="view view-map is-hidden">'
        f'<p class="map-caption">{E(t["map_caption"])}</p>'
        f'<div class="map-scroll"><svg class="map" viewBox="0 0 {width:.0f} {height:.0f}"'
        f' role="img"'
        f' aria-label="{E(t["map_alt"])}" preserveAspectRatio="xMidYMid meet">'
        f'<g class="map-rows">{rows}</g><g class="map-edges">{"".join(edges)}</g>'
        f'<g class="map-nodes">{"".join(nodes)}</g></svg></div>'
        f'<p class="map-readout" role="status" data-default="{E(t["map_readout"])}">'
        f'{E(t["map_readout"])}</p>{legend(counts, len(items), t)}</div>'
    )


def controls(items: list[Item], lang: str, t: dict) -> str:
    counts = status_counts(items)
    status_chips = ''.join(
        f'<label class="chip is-on" data-status="{k}">'
        f'<input type="checkbox" class="chip-box" data-filter="status" data-key="{k}" checked>'
        f'<span class="chip-name">{E(t["statuses"][k])}</span>'
        f'<span class="chip-count">{n}</span></label>'
        for k, n in counts
    )
    topic_chips = ''
    for key in topic_order(items):
        group = [i for i in items if i.topic_key == key]
        topic_chips += (
            f'<label class="chip is-on">'
            f'<input type="checkbox" class="chip-box" data-filter="topic"'
            f' data-key="{E(key)}" checked>'
            f'<span class="chip-name">{E(group[0].docs[lang].topic_label)}</span>'
            f'<span class="chip-count">{len(group)}</span></label>'
        )
    views = ''.join(
        f'<button type="button" class="view-btn{" is-on" if k == "cards" else ""}"'
        f' data-view="{k}" aria-pressed="{"true" if k == "cards" else "false"}">'
        f'{E(t[label])}</button>'
        for k, label in [('cards', 'view_cards'), ('table', 'view_table'), ('map', 'view_map')]
    )
    return (
        f'<section class="controls" aria-label="{E(t["search_label"])}"><div class="wrap">'
        f'<div class="control-row"><label class="search-field">'
        f'<span class="sr-only">{E(t["search_label"])}</span>'
        f'<input type="search" class="search" placeholder="{E(t["search_hint"])}"></label>'
        f'<div class="views" role="group" aria-label="{E(t["views_label"])}">{views}</div></div>'
        f'<fieldset class="chips" data-kind="status">'
        f'<legend class="chips-legend">{E(t["status"])}</legend>{status_chips}</fieldset>'
        f'<fieldset class="chips" data-kind="topic">'
        f'<legend class="chips-legend">{E(t["topic"])}</legend>{topic_chips}</fieldset>'
        f'</div></section>'
    )


def overview(items: list[Item], t: dict) -> str:
    counts = status_counts(items)
    topics = len(topic_order(items))
    total_boxes = sum(i.total for i in items)
    done_boxes = sum(i.done for i in items)
    note = t['boxes_note'].format(done=done_boxes, total=total_boxes)
    return (
        f'<section class="overview" aria-labelledby="overview-h"><div class="wrap">'
        f'<h2 class="section-h" id="overview-h">{E(t["overview"])}</h2>'
        f'<div class="overview-grid">'
        f'<div class="panel hero-figure"><span class="hero-value">{len(items)}</span>'
        f'<span class="hero-label">{E(t["items_label"])}</span>'
        f'<span class="hero-sub">{E(t["topics_sub"].format(n=topics))}</span></div>'
        f'<figure class="panel chart">'
        f'<figcaption class="chart-title">{E(t["status_chart"])}</figcaption>'
        f'{stack(counts, t)}{legend(counts, len(items), t)}</figure>'
        f'<figure class="panel chart">'
        f'<figcaption class="chart-title">{E(t["work_chart"])}</figcaption>'
        f'<p class="chart-value">{pct(done_boxes, total_boxes):.0f}'
        f'<span class="chart-unit">%</span></p>'
        f'<div class="meter" role="img" aria-label="{E(note)}" title="{E(note)}">'
        f'<span class="meter-fill" style="width:{pct(done_boxes, total_boxes):.4g}%"></span></div>'
        f'<p class="chart-note">{E(note)}</p></figure>'
        f'</div></div></section>'
    )


def page(items: list[Item], lang: str, updated: str) -> str:
    t = TEXT[lang]
    up = '../' if lang == 'ja' else ''
    home = '../index.html' if lang == 'ja' else './index.html'
    return f'''<!doctype html>
<html lang="{t['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(t['title'])}</title>
<meta name="description" content="{E(t['desc'])}">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml">
<link rel="alternate" hreflang="{t['other_code']}" href="{t['other_href']}">
<link rel="stylesheet" href="{up}assets/style.css">
<script>try{{var t=localStorage.getItem('bakuchi-roadmap-theme');if(t==='light'||t==='dark')\
document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
</head>
<body>
<a class="skip" href="#board">{E(t['skip'])}</a>
<header class="site-head"><div class="wrap head-inner">\
<a class="brand" href="{home}"><span class="brand-mark" aria-hidden="true"></span>\
<span class="brand-name">bakuchi</span></a>\
<nav class="head-nav"><a class="head-link" href="{GITHUB}">GitHub</a>\
<a class="head-link" href="{t['other_href']}" lang="{t['other_code']}" \
hreflang="{t['other_code']}">{E(t['other_lang'])}</a>\
<button type="button" class="theme-btn" data-theme-toggle aria-label="{E(t['theme'])}">\
<span class="theme-name" data-auto="{E(t['theme_auto'])}" data-light="{E(t['theme_light'])}" \
data-dark="{E(t['theme_dark'])}">{E(t['theme_auto'])}</span></button></nav></div></header>
<main>
<section class="hero"><div class="wrap"><p class="eyebrow">{E(t['eyebrow'])}</p>\
<h1>{E(t['h1'])}</h1><p class="lede">{E(t['lede'])}</p>\
<p class="hero-updated">{E(t['updated'])} \
<time datetime="{E(updated)}">{E(updated[:10])}</time></p></div></section>
{overview(items, t)}
{controls(items, lang, t)}
<section class="board" id="board"><div class="wrap">{cards_view(items, lang, t)}\
{table_view(items, lang, t, updated)}{map_view(items, lang, t)}\
<p class="empty" role="status" data-msg-query="{E(t['empty_query'])}" \
data-msg-filters="{E(t['empty_filters'])}"></p></div></section>
</main>
<footer class="site-foot"><div class="wrap"><p>{E(t['foot'])} \
<a href="{GITHUB}">0x0c/bakuchi</a></p><p class="foot-links">\
<a href="{t['how_href']}">{E(t['foot_how'])}</a>\
<a href="{t['plan_href']}">{E(t['foot_plan'])}</a></p></div></footer>
<script src="{up}assets/app.js" defer></script>
</body>
</html>
'''


# -------------------------------------------------------------------- assets

CSS = '''/* bakuchi roadmap — generated by tools/build_roadmap_site.py, do not edit by hand.
   状態色は隣接ペアの CVD 分離と面とのコントラストを検証済み（明暗それぞれ個別に選定）。
   薄い状態色は色だけで意味を担わない: バッジは文字、積み上げ棒は件数と凡例、表は
   同じ値を文字で持つ。 */

:root {
  color-scheme: light;
  --surface: #fcfcfb;
  --plane: #f9f9f7;
  --ink: #0b0b0b;
  --ink-2: #52514e;
  --muted: #898781;
  --grid: #e1e0d9;
  --rule: #c3c2b7;
  --border: rgba(11, 11, 11, 0.10);
  --track: rgba(11, 11, 11, 0.08);
  --wash: rgba(11, 11, 11, 0.04);
  --accent: #2a78d6;
  --st-implemented: #008300;
  --st-in-progress: #eda100;
  --st-accepted: #1baf7a;
  --st-proposal: #2a78d6;
  --st-deferred: #e87ba4;
  --sans: system-ui, -apple-system, "Segoe UI", "Hiragino Sans", "Noto Sans JP",
    "Yu Gothic UI", sans-serif;
}

@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --surface: #1a1a19;
    --plane: #0d0d0d;
    --ink: #ffffff;
    --ink-2: #c3c2b7;
    --muted: #898781;
    --grid: #2c2c2a;
    --rule: #383835;
    --border: rgba(255, 255, 255, 0.10);
    --track: rgba(255, 255, 255, 0.10);
    --wash: rgba(255, 255, 255, 0.06);
    --accent: #3987e5;
    --st-implemented: #008300;
    --st-in-progress: #c98500;
    --st-accepted: #199e70;
    --st-proposal: #3987e5;
    --st-deferred: #d55181;
  }
}

:root[data-theme="dark"] {
  color-scheme: dark;
  --surface: #1a1a19;
  --plane: #0d0d0d;
  --ink: #ffffff;
  --ink-2: #c3c2b7;
  --muted: #898781;
  --grid: #2c2c2a;
  --rule: #383835;
  --border: rgba(255, 255, 255, 0.10);
  --track: rgba(255, 255, 255, 0.10);
  --wash: rgba(255, 255, 255, 0.06);
  --accent: #3987e5;
  --st-implemented: #008300;
  --st-in-progress: #c98500;
  --st-accepted: #199e70;
  --st-proposal: #3987e5;
  --st-deferred: #d55181;
}

*, *::before, *::after { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--plane);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.6;
  -webkit-text-size-adjust: 100%;
}

a { color: inherit; }
h1, h2, h3, h4 { line-height: 1.3; }

.wrap { width: min(1120px, 100% - 3rem); margin-inline: auto; }
@media (max-width: 640px) { .wrap { width: min(1120px, 100% - 2rem); } }

.sr-only {
  position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
  overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
}

.skip {
  position: absolute; left: -9999px; top: 0; z-index: 10;
  background: var(--surface); color: var(--ink); padding: .6rem 1rem;
  border: 1px solid var(--border);
}
.skip:focus { left: .75rem; top: .75rem; }

/* --- masthead --- */

.site-head {
  position: sticky; top: 0; z-index: 5;
  background: color-mix(in srgb, var(--plane) 88%, transparent);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
}
.head-inner { display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  min-height: 56px; }
.brand { display: inline-flex; align-items: center; gap: .55rem; text-decoration: none;
  font-weight: 600; letter-spacing: -0.01em; }
.brand-mark {
  width: 18px; height: 18px; border-radius: 5px; background: var(--accent);
  box-shadow: inset 0 0 0 3px var(--plane), 0 0 0 1px var(--accent);
}
.head-nav { display: flex; align-items: center; gap: .35rem; }
.head-link, .theme-btn {
  font: inherit; font-size: 13px; color: var(--ink-2); text-decoration: none;
  padding: .3rem .6rem; border-radius: 7px; border: 1px solid transparent; background: none;
  cursor: pointer;
}
.head-link:hover, .theme-btn:hover { background: var(--wash); color: var(--ink); }
.theme-btn { border-color: var(--border); }

/* --- hero --- */

.hero { padding: 3rem 0 1.5rem; }
.eyebrow { margin: 0; font-size: 12px; letter-spacing: .08em; text-transform: uppercase;
  color: var(--muted); }
.hero h1 { margin: .2rem 0 .6rem; font-size: clamp(2rem, 5vw, 2.75rem); letter-spacing: -0.02em; }
.lede { margin: 0; max-width: 62ch; color: var(--ink-2); }
.hero-updated { margin: 1rem 0 0; font-size: 12.5px; color: var(--muted); }

/* --- panels --- */

.section-h {
  margin: 0 0 .9rem; font-size: 12px; font-weight: 600; letter-spacing: .08em;
  text-transform: uppercase; color: var(--muted);
}
.overview { padding: 1.5rem 0; }
.overview-grid {
  display: grid; gap: .9rem;
  grid-template-columns: repeat(auto-fit, minmax(248px, 1fr));
}
.panel {
  margin: 0; padding: 1.1rem 1.2rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: 12px;
}
.hero-figure { display: flex; flex-direction: column; justify-content: center; }
.hero-value { font-size: 3.4rem; font-weight: 600; line-height: 1; letter-spacing: -0.03em; }
.hero-label { margin-top: .45rem; font-size: 14px; color: var(--ink-2); }
.hero-sub { font-size: 12.5px; color: var(--muted); }
.chart-title { font-size: 12.5px; font-weight: 600; color: var(--ink-2); margin-bottom: .7rem; }
.chart-value { margin: 0 0 .55rem; font-size: 2.1rem; font-weight: 600; line-height: 1;
  letter-spacing: -0.02em; }
.chart-unit { font-size: 1rem; font-weight: 500; color: var(--muted); margin-left: .1rem; }
.chart-note { margin: .6rem 0 0; font-size: 12px; color: var(--muted); }

/* --- marks --- */

.stack { display: flex; gap: 2px; height: 14px; }
.stack-sm { height: 7px; max-width: 320px; }
.seg { position: relative; display: flex; align-items: center; justify-content: center;
  min-width: 3px; border-radius: 2px; background: var(--muted); }
.stack .seg:first-child { border-start-start-radius: 4px; border-end-start-radius: 4px; }
.stack .seg:last-child { border-start-end-radius: 4px; border-end-end-radius: 4px; }
.seg-value { font-size: 10px; font-weight: 600; color: var(--surface); }
.seg[data-status="implemented"] { background: var(--st-implemented); }
.seg[data-status="in-progress"] { background: var(--st-in-progress); }
.seg[data-status="accepted"] { background: var(--st-accepted); }
.seg[data-status="proposal"] { background: var(--st-proposal); }
.seg[data-status="deferred"] { background: var(--st-deferred); }

.meter { height: 8px; border-radius: 4px; background: var(--track); overflow: hidden; }
.meter-sm { height: 5px; }
.meter-fill { display: block; height: 100%; border-radius: 4px;
  background: var(--st-implemented); min-width: 0; }

.legend { list-style: none; display: flex; flex-wrap: wrap; gap: .35rem 1rem;
  margin: .8rem 0 0; padding: 0; font-size: 12px; color: var(--ink-2); }
.legend-item { display: inline-flex; align-items: center; gap: .35rem; }
.swatch { width: 9px; height: 9px; border-radius: 3px; background: var(--muted); flex: none; }
.swatch[data-status="implemented"] { background: var(--st-implemented); }
.swatch[data-status="in-progress"] { background: var(--st-in-progress); }
.swatch[data-status="accepted"] { background: var(--st-accepted); }
.swatch[data-status="proposal"] { background: var(--st-proposal); }
.swatch[data-status="deferred"] { background: var(--st-deferred); }
.legend-value { font-weight: 600; font-variant-numeric: tabular-nums; }
.legend-share { color: var(--muted); font-variant-numeric: tabular-nums; }

.badge {
  display: inline-block; font-size: 11px; line-height: 1.5; padding: 0 .4rem;
  border-radius: 5px; border: 1px solid currentColor; white-space: nowrap;
}
.badge[data-status="implemented"] { color: var(--st-implemented); }
.badge[data-status="in-progress"] { color: var(--st-in-progress); }
.badge[data-status="accepted"] { color: var(--st-accepted); }
.badge[data-status="proposal"] { color: var(--st-proposal); }
.badge[data-status="deferred"] { color: var(--st-deferred); }

/* --- controls --- */

.controls { padding: 1rem 0 .5rem; }
.control-row { display: flex; flex-wrap: wrap; align-items: center; gap: .75rem;
  margin-bottom: .8rem; }
.search-field { flex: 1 1 260px; }
.search {
  width: 100%; font: inherit; font-size: 14px; padding: .45rem .75rem;
  border: 1px solid var(--border); border-radius: 9px; background: var(--surface); color: inherit;
}
.search:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.views { display: inline-flex; border: 1px solid var(--border); border-radius: 9px;
  overflow: hidden; background: var(--surface); }
.view-btn { font: inherit; font-size: 13px; padding: .4rem .95rem; border: 0; background: none;
  color: var(--ink-2); cursor: pointer; }
.view-btn + .view-btn { border-left: 1px solid var(--border); }
.view-btn.is-on { background: var(--wash); color: var(--ink); font-weight: 600; }

.chips { display: flex; flex-wrap: wrap; align-items: center; gap: .4rem;
  border: 0; margin: 0 0 .5rem; padding: 0; }
.chips-legend { padding: 0; margin-right: .3rem; font-size: 12px; color: var(--muted);
  min-width: 4.5rem; }
.chip {
  display: inline-flex; align-items: center; gap: .4rem; cursor: pointer; user-select: none;
  font-size: 12.5px; padding: .18rem .55rem; border-radius: 7px;
  border: 1px solid var(--border); background: var(--surface); opacity: .45;
}
.chip.is-on { opacity: 1; }
.chip-box { width: 13px; height: 13px; margin: 0; accent-color: var(--accent); flex: none; }
.chip[data-status="implemented"] .chip-box { accent-color: var(--st-implemented); }
.chip[data-status="in-progress"] .chip-box { accent-color: var(--st-in-progress); }
.chip[data-status="accepted"] .chip-box { accent-color: var(--st-accepted); }
.chip[data-status="proposal"] .chip-box { accent-color: var(--st-proposal); }
.chip[data-status="deferred"] .chip-box { accent-color: var(--st-deferred); }
.chip-count { font-variant-numeric: tabular-nums; color: var(--muted); }

/* --- board --- */

.board { padding: .5rem 0 3rem; }
.is-hidden { display: none !important; }

.topic { margin: 1.6rem 0 2rem; }
.topic-head { margin-bottom: .75rem; }
.topic-name { margin: 0; font-size: 17px; letter-spacing: -0.01em; }
.topic-prog { display: flex; align-items: baseline; gap: .5rem; margin: .15rem 0 .4rem; }
.topic-pct { font-size: 14px; font-weight: 600; font-variant-numeric: tabular-nums; }
.topic-detail { font-size: 12px; color: var(--muted); }

.cards { display: grid; gap: .7rem;
  grid-template-columns: repeat(auto-fill, minmax(268px, 1fr)); }
.card {
  display: flex; flex-direction: column; gap: .45rem; padding: .85rem .95rem;
  background: var(--surface); border: 1px solid var(--border); border-radius: 11px;
}
.card:hover { border-color: var(--rule); }
.card-top { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
.card-id { font-size: 12px; font-weight: 600; color: var(--muted);
  font-variant-numeric: tabular-nums; }
.card-title { margin: 0; font-size: 14.5px; }
.card-title a { text-decoration: none; }
.card-title a:hover { text-decoration: underline; }
.card-intro { margin: 0; font-size: 12.5px; line-height: 1.55; color: var(--ink-2); }
.card-progress { display: flex; align-items: center; gap: .5rem; }
.card-progress .meter { flex: 1; }
.card-progress-text { font-size: 11.5px; color: var(--muted); white-space: nowrap; }
.card-meta, .card-rel { display: flex; flex-wrap: wrap; align-items: center; gap: .5rem;
  margin: 0; font-size: 11.5px; color: var(--muted); }
.card-meta > span + span::before,
.card-rel-label + .rel::before { content: "·"; margin-right: .5rem; color: var(--rule); }
.card-rel-label + .rel::before { content: none; }
.rel { font-variant-numeric: tabular-nums; text-decoration: none;
  border-bottom: 1px solid var(--border); }
.rel:hover { border-color: currentColor; color: var(--ink); }
.card-details { font-size: 12px; }
.card-details > summary { cursor: pointer; color: var(--ink-2); display: flex;
  align-items: baseline; gap: .4rem; }
.card-boxes { color: var(--muted); font-variant-numeric: tabular-nums; }
.checklist { margin: .5rem 0 0; padding-left: 1.1rem; color: var(--ink-2); }
.checklist .check { margin-bottom: .3rem; line-height: 1.5; }
.checklist .check[data-checked="true"] { color: var(--muted); text-decoration: line-through; }

/* --- table --- */

.table-scroll { overflow-x: auto; border: 1px solid var(--border); border-radius: 11px;
  background: var(--surface); }
.table { width: 100%; min-width: 720px; border-collapse: collapse; font-size: 13.5px; }
.table th, .table td { text-align: left; padding: .55rem .8rem;
  border-bottom: 1px solid var(--grid); vertical-align: middle; }
.table thead th { font-size: 12px; color: var(--ink-2); white-space: nowrap;
  cursor: pointer; user-select: none; background: var(--surface); position: sticky; top: 0; }
.table thead th:hover { background: var(--wash); }
.table thead th[aria-sort="ascending"]::after { content: " \\25B2"; font-size: 8px; }
.table thead th[aria-sort="descending"]::after { content: " \\25BC"; font-size: 8px; }
.table tbody tr:hover { background: var(--wash); }
.table tbody tr:last-child td, .table tbody tr:last-child th { border-bottom: 0; }
.cell-id { font-variant-numeric: tabular-nums; color: var(--muted); white-space: nowrap; }
.cell-title { font-weight: 500; }
.cell-title a { text-decoration: none; }
.cell-title a:hover { text-decoration: underline; }
.cell-progress { display: flex; align-items: center; gap: .5rem; min-width: 118px; }
.cell-progress .meter { flex: 1; min-width: 56px; }
.cell-progress-text { font-size: 11.5px; color: var(--muted);
  font-variant-numeric: tabular-nums; }
.cell-date { color: var(--muted); white-space: nowrap; font-variant-numeric: tabular-nums; }

/* --- map --- */

.map-caption { margin: 0 0 .9rem; max-width: 64ch; font-size: 12.5px; color: var(--ink-2); }
.map-scroll { overflow-x: auto; background: var(--surface); border: 1px solid var(--border);
  border-radius: 11px; padding: .5rem; }
.map { display: block; width: 100%; min-width: 720px; height: auto; }
.map-rule { stroke: var(--grid); stroke-width: 1; }
.map-row-label { fill: var(--ink-2); font-size: 12px; font-family: var(--sans); }
.map-edge { fill: none; stroke: var(--rule); stroke-width: 1.5; opacity: .55; }
.map-node { cursor: pointer; }
.map-hit { fill: transparent; }
.map-dot { fill: var(--muted); stroke: var(--surface); stroke-width: 2; }
.map-node[data-status="implemented"] .map-dot { fill: var(--st-implemented); }
.map-node[data-status="in-progress"] .map-dot { fill: var(--st-in-progress); }
.map-node[data-status="accepted"] .map-dot { fill: var(--st-accepted); }
.map-node[data-status="proposal"] .map-dot { fill: var(--st-proposal); }
.map-node[data-status="deferred"] .map-dot { fill: var(--st-deferred); }
.map-label { fill: var(--muted); font-size: 9.5px; font-family: var(--sans);
  font-variant-numeric: tabular-nums; }
.map-node:hover .map-dot, .map-node:focus-visible .map-dot { stroke: var(--ink); }
.map-node:hover .map-label, .map-node:focus-visible .map-label { fill: var(--ink); }
.map.is-picking .map-node:not(.is-lit) { opacity: .28; }
.map.is-picking .map-edge:not(.is-lit) { opacity: .12; }
.map-edge.is-lit { stroke: var(--accent); opacity: 1; stroke-width: 2; }
.map-node.is-out, .map-edge.is-out { display: none; }
.map-readout { margin: .8rem 0 0; font-size: 12.5px; color: var(--ink-2); min-height: 1.5em; }
.view-map .legend { margin-top: .6rem; }

.empty { margin: 1.5rem 0; font-size: 13.5px; color: var(--ink-2); }
.empty:empty { margin: 0; }

/* --- footer --- */

.site-foot { border-top: 1px solid var(--border); padding: 1.6rem 0 2.5rem;
  font-size: 12.5px; color: var(--muted); }
.site-foot p { margin: 0 0 .35rem; }
.foot-links { display: flex; flex-wrap: wrap; gap: 1rem; }
.foot-links a { color: var(--ink-2); }

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
'''

JS = '''/* bakuchi roadmap — generated by tools/build_roadmap_site.py, do not edit by hand.
   全体を段階的強化として書く。スクリプトを切ってもすべての絞り込みは有効な状態で、
   カード表示が出たままページは読める。ここでは何も取得も再計算もしない。ビルドが
   すでに描いたマークアップを、見せる・隠す・並べ替えるだけ。 */
(function () {
  'use strict';

  var root = document.documentElement;
  var THEME_KEY = 'bakuchi-roadmap-theme';
  var VIEW_KEY = 'bakuchi-roadmap-view';

  function store(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* プライベートモード: 無視 */ }
  }
  function recall(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }

  /* --- 配色: 自動 -> 明るい -> 暗い。次回以降も覚えておく --- */

  var themeBtn = document.querySelector('[data-theme-toggle]');
  if (themeBtn) {
    var name = themeBtn.querySelector('.theme-name');
    var order = ['auto', 'light', 'dark'];
    var paint = function (mode) {
      if (mode === 'auto') { root.removeAttribute('data-theme'); }
      else { root.setAttribute('data-theme', mode); }
      if (name) { name.textContent = name.getAttribute('data-' + mode) || mode; }
    };
    var current = recall(THEME_KEY);
    if (order.indexOf(current) < 0) { current = 'auto'; }
    paint(current);
    themeBtn.addEventListener('click', function () {
      current = order[(order.indexOf(current) + 1) % order.length];
      paint(current);
      store(THEME_KEY, current);
    });
  }

  /* --- 絞り込み: 状態チップ かつ トピックチップ かつ 自由入力 --- */

  var search = document.querySelector('.search');
  var boxes = Array.prototype.slice.call(document.querySelectorAll('.chip-box'));
  var cards = Array.prototype.slice.call(document.querySelectorAll('.card'));
  var rows = Array.prototype.slice.call(document.querySelectorAll('.row'));
  var nodes = Array.prototype.slice.call(document.querySelectorAll('.map-node'));
  var edges = Array.prototype.slice.call(document.querySelectorAll('.map-edge'));
  var topics = Array.prototype.slice.call(document.querySelectorAll('.topic'));
  var empty = document.querySelector('.empty');

  var on = { status: {}, topic: {} };
  boxes.forEach(function (box) {
    on[box.getAttribute('data-filter')][box.getAttribute('data-key')] = box.checked;
  });

  function terms() {
    return (search ? search.value : '').toLowerCase().split(/\\s+/).filter(Boolean);
  }

  function passes(element, query) {
    var hay = element.getAttribute('data-search') || '';
    if (!on.status[element.getAttribute('data-status')]) { return false; }
    if (!on.topic[element.getAttribute('data-topic')]) { return false; }
    return query.every(function (term) { return hay.indexOf(term) >= 0; });
  }

  function apply() {
    var query = terms();
    var shown = 0;
    var live = {};

    cards.forEach(function (card) {
      var visible = passes(card, query);
      if (visible) { shown += 1; }
      card.classList.toggle('is-hidden', !visible);
    });
    rows.forEach(function (row) { row.classList.toggle('is-hidden', !passes(row, query)); });
    nodes.forEach(function (node) {
      var visible = passes(node, query);
      live[node.getAttribute('data-id')] = visible;
      node.classList.toggle('is-out', !visible);
    });
    edges.forEach(function (edge) {
      var both = live[edge.getAttribute('data-a')] && live[edge.getAttribute('data-b')];
      edge.classList.toggle('is-out', !both);
    });
    topics.forEach(function (topic) {
      topic.classList.toggle('is-hidden', !topic.querySelector('.card:not(.is-hidden)'));
    });
    boxes.forEach(function (box) {
      box.closest('.chip').classList.toggle('is-on', box.checked);
    });

    if (empty) {
      if (shown > 0) {
        empty.textContent = '';
      } else if (query.length) {
        empty.textContent = (empty.getAttribute('data-msg-query') || '')
          .replace('{query}', search.value.trim());
      } else {
        empty.textContent = empty.getAttribute('data-msg-filters') || '';
      }
    }
  }

  boxes.forEach(function (box) {
    box.addEventListener('change', function () {
      on[box.getAttribute('data-filter')][box.getAttribute('data-key')] = box.checked;
      apply();
    });
  });
  if (search) { search.addEventListener('input', apply); }

  /* --- 表示切り替え: 描画済みの 1 つを見せ、残りを隠す --- */

  var viewBtns = Array.prototype.slice.call(document.querySelectorAll('.view-btn'));
  var views = {
    cards: document.querySelector('.view-cards'),
    table: document.querySelector('.view-table'),
    map: document.querySelector('.view-map')
  };
  function setView(wanted) {
    Object.keys(views).forEach(function (key) {
      if (views[key]) { views[key].classList.toggle('is-hidden', key !== wanted); }
    });
    viewBtns.forEach(function (btn) {
      var active = btn.getAttribute('data-view') === wanted;
      btn.classList.toggle('is-on', active);
      btn.setAttribute('aria-pressed', String(active));
    });
    store(VIEW_KEY, wanted);
  }
  viewBtns.forEach(function (btn) {
    btn.addEventListener('click', function () { setView(btn.getAttribute('data-view')); });
  });
  var saved = recall(VIEW_KEY);
  setView(views[saved] ? saved : 'cards');

  /* --- 表の並べ替え: 描画済みの行を並べ替えるだけ。見える行の集合は変えない --- */

  var table = document.querySelector('.table');
  var tbody = table ? table.querySelector('tbody') : null;
  var heads = table ? Array.prototype.slice.call(table.querySelectorAll('th[data-sort-key]')) : [];
  var sorted = null;
  var direction = 1;

  function value(row, index) {
    var cell = row.children[index];
    if (!cell) { return ''; }
    var explicit = cell.getAttribute('data-sort');
    return (explicit !== null ? explicit : cell.textContent || '').trim().toLowerCase();
  }

  heads.forEach(function (head, index) {
    function sortBy() {
      direction = sorted === index ? -direction : 1;
      sorted = index;
      Array.prototype.slice.call(tbody.children).sort(function (a, b) {
        var left = value(a, index);
        var right = value(b, index);
        if (left === right) { return 0; }
        return left < right ? -direction : direction;
      }).forEach(function (row) { tbody.appendChild(row); });
      heads.forEach(function (other) { other.setAttribute('aria-sort', 'none'); });
      head.setAttribute('aria-sort', direction > 0 ? 'ascending' : 'descending');
    }
    head.addEventListener('click', sortBy);
    head.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); sortBy(); }
    });
  });

  /* --- 関連図: 指した項目の題名を出し、つながる先を明るくする --- */

  var map = document.querySelector('.map');
  var readout = document.querySelector('.map-readout');
  var fallback = readout ? readout.getAttribute('data-default') || '' : '';

  function pick(node) {
    if (!map) { return; }
    var id = node.getAttribute('data-id');
    var lit = {};
    lit[id] = true;
    edges.forEach(function (edge) {
      var a = edge.getAttribute('data-a');
      var b = edge.getAttribute('data-b');
      var touches = (a === id || b === id) && !edge.classList.contains('is-out');
      edge.classList.toggle('is-lit', touches);
      if (touches) { lit[a] = true; lit[b] = true; }
    });
    nodes.forEach(function (other) {
      other.classList.toggle('is-lit', !!lit[other.getAttribute('data-id')]);
    });
    map.classList.add('is-picking');
    if (readout) {
      readout.textContent = node.getAttribute('data-caption') + ' · '
        + node.getAttribute('data-status-label');
    }
  }

  function release() {
    if (!map) { return; }
    map.classList.remove('is-picking');
    edges.forEach(function (edge) { edge.classList.remove('is-lit'); });
    nodes.forEach(function (node) { node.classList.remove('is-lit'); });
    if (readout) { readout.textContent = fallback; }
  }

  nodes.forEach(function (node) {
    node.addEventListener('mouseenter', function () { pick(node); });
    node.addEventListener('focus', function () { pick(node); });
    node.addEventListener('mouseleave', release);
    node.addEventListener('blur', release);
  });

  apply();
})();
'''

FAVICON = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
<rect width="32" height="32" rx="7" fill="#2a78d6"/>
<rect x="6" y="8" width="13" height="4" rx="2" fill="#cde2fb"/>
<rect x="6" y="14" width="20" height="4" rx="2" fill="#ffffff"/>
<rect x="6" y="20" width="9" height="4" rx="2" fill="#9ec5f4"/>
</svg>
'''


# --------------------------------------------------------------------- main


by_id: dict[str, Item] = {}


def outputs(items: list[Item], updated: str) -> dict[str, str]:
    return {
        'index.html': page(items, 'en', updated),
        'ja/index.html': page(items, 'ja', updated),
        'assets/style.css': CSS,
        'assets/app.js': JS,
        'assets/favicon.svg': FAVICON,
        '.nojekyll': '',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='site', help='出力先ディレクトリ（既定: site）')
    parser.add_argument('--check', action='store_true',
                        help='生成せず、出力が最新かどうかだけを判定する')
    args = parser.parse_args()

    items = load_items()
    by_id.update({i.id: i for i in items})
    updated = last_updated()
    out_dir = (REPO / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    files = outputs(items, updated)

    if args.check:
        stale = [
            name for name, body in files.items()
            if not (out_dir / name).exists()
            or (out_dir / name).read_text(encoding='utf-8') != body
        ]
        if stale:
            print('生成物が roadmaps/ と一致しない:', ', '.join(sorted(stale)), file=sys.stderr)
            print(f'  python3 {Path(__file__).relative_to(REPO)} で作り直す', file=sys.stderr)
            return 1
        print(f'OK   site は最新（{len(items)} 項目）')
        return 0

    for name, body in files.items():
        path = out_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8')

    boxes = sum(i.total for i in items)
    print(f'OK   {len(items)} 項目 / {len(topic_order(items))} トピック / '
          f'作業 {boxes} 件中 {sum(i.done for i in items)} 件完了 → {out_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
