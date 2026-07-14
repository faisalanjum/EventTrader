#!/usr/bin/env python3
"""Extract filer words from one exact inline-XBRL lock fact."""
import argparse, json, re, warnings
from pathlib import Path
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings('ignore', category=XMLParsedAsHTMLWarning)


def text(node):
    return ' '.join(node.get_text(' ', strip=True).replace('\u200b', '').split()) if node else ''


def local(qname):
    return (qname or '').split(':')[-1]


def plain(qname):
    name = re.sub(r'(Axis|Member)$', '', local(qname))
    return ' '.join(re.findall(r'[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+', name))


def words(value):
    return re.findall(r"[A-Za-z][A-Za-z’'-]*", value)


def member_pairs(context):
    return tuple(sorted(
        (item.get('dimension'), text(item))
        for item in context.find_all(
            lambda tag: tag.name and tag.name.lower() == 'xbrldi:explicitmember'
        )
    ))


def period(context):
    find = lambda name: context.find(lambda tag: tag.name and tag.name.lower() == name)
    instant = text(find('xbrli:instant'))
    return (text(find('xbrli:startdate')), text(find('xbrli:enddate'))) if not instant else ('', instant)


def span(value):
    try:
        return max(1, int(value or 1))
    except (TypeError, ValueError):
        return 1


def table_grid(rows):
    """Return each direct cell's physical [start, end) columns."""
    occupied_until = {}
    grid = []
    for row_number, row in enumerate(rows):
        placed = []
        column = 0
        for cell in row.find_all(['td', 'th'], recursive=False):
            width = span(cell.get('colspan'))
            while any(occupied_until.get(item, 0) > row_number
                      for item in range(column, column + width)):
                column += 1
            placed.append((cell, column, column + width))
            height = span(cell.get('rowspan'))
            if height > 1:
                for item in range(column, column + width):
                    occupied_until[item] = row_number + height
            column += width
        grid.append(placed)
    return grid


def has_number_fact(cell):
    return bool(cell.find(
        lambda tag: tag.name and tag.name.lower() == 'ix:nonfraction'
    ))


def hidden(cell):
    style = str(cell.get('style') or '')
    return cell.has_attr('hidden') or str(cell.get('aria-hidden') or '').lower() == 'true' \
        or bool(re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)', style, re.I))


def aligned_column(rows, row_number, fact_cell, wanted_pairs):
    """Find the visible header over the exact numeric cell."""
    grid = table_grid(rows)
    target = next((item for item in grid[row_number] if item[0] is fact_cell), None)
    if not target:
        return ''
    _, target_start, target_end = target
    facet_words = {
        word.lower()
        for axis, member in wanted_pairs
        for value in (plain(axis), plain(member))
        for word in words(value)
    }
    candidates = []
    for distance in range(1, row_number + 1):
        prior_number = row_number - distance
        if has_number_fact(rows[prior_number]):
            continue
        for cell, start, end in grid[prior_number]:
            value = text(cell).strip(' —-')
            if end <= target_start or start >= target_end or not words(value) \
                    or (start == 0 and target_start > 0) or hidden(cell):
                continue
            value_words = {word.lower() for word in words(value)}
            candidates.append((len(value_words & facet_words), distance, value))
    if not candidates:
        return ''
    # Facet words choose the semantic header in a multi-level heading. Distance
    # is the fallback when a filer label and its XBRL member use different words.
    return sorted(candidates, key=lambda item: (-item[0], item[1]))[0][2]


def extract(path, concept, start, end, wanted_pairs):
    soup = BeautifulSoup(Path(path).read_text(errors='replace'), 'lxml')
    contexts = {
        context.get('id'): (member_pairs(context), period(context))
        for context in soup.find_all(lambda tag: tag.name and tag.name.lower() == 'xbrli:context')
    }
    wanted_pairs = tuple(sorted(wanted_pairs))
    hits = []
    for fact in soup.find_all(lambda tag: tag.name and tag.name.lower() == 'ix:nonfraction'):
        pairs, fact_period = contexts.get(fact.get('contextref'), ((), ('', '')))
        if str(fact.get('name') or '') == str(concept) and pairs == wanted_pairs \
                and fact_period == (start, end):
            hits.append(fact)
    if len(hits) != 1:
        raise SystemExit(f'exact fact count was {len(hits)}, expected 1')

    fact = hits[0]
    cell = fact.find_parent(['td', 'th'])
    row = cell.find_parent('tr')
    cells = row.find_all(['td', 'th'], recursive=False)
    fact_cell = cells.index(cell)
    left_labels = [text(item) for item in cells[:fact_cell]
                   if words(text(item)) and not re.search(r'\d', text(item))]

    section = ''
    table = row.find_parent('table')
    # Rows commonly sit inside <tbody>; exclude only rows from nested tables.
    table_rows = [candidate for candidate in table.find_all('tr')
                  if candidate.find_parent('table') is table]
    row_number = table_rows.index(row)
    column = aligned_column(table_rows, row_number, cell, wanted_pairs)
    for prior in reversed(table_rows[:row_number]):
        prior_cells = prior.find_all(['td', 'th'], recursive=False)
        labels = [text(item) for item in prior_cells if words(text(item)) and not re.search(r'\d', text(item))]
        if prior_cells and not has_number_fact(prior) and text(prior_cells[0]) \
                and len(labels) == 1 and not labels[0].startswith('('):
            section = labels[0].strip(' —-')
            break

    anchor = ''
    if not section:
        seen = set()
        for prior in table.find_all_previous(['td', 'th', 'p', 'div'], limit=150):
            value = text(prior)
            if value in seen:
                continue
            seen.add(value)
            if 4 <= len(words(value)) <= 14 and not re.search(r'\d', value) and len(value) <= 140:
                anchor = value
                break

    return {
        'concept': local(concept),
        'period': {'start': start, 'end': end},
        'facets': [
            {'axis': local(axis), 'member': local(member),
             'axis_words': plain(axis), 'member_words': plain(member)}
            for axis, member in wanted_pairs
        ],
        'source_words': {
            'section': section,
            'row': left_labels[0] if left_labels else '',
            'column': column,
            'nearby_anchor': anchor,
        },
        'evidence': {
            'fact_id': fact.get('id'),
            'context_id': fact.get('contextref'),
            'displayed_value': text(fact),
            'row_cells': [text(item) for item in cells],
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', required=True)
    parser.add_argument('--concept', required=True)
    parser.add_argument('--start', default='')
    parser.add_argument('--end', required=True)
    parser.add_argument('--member', action='append', default=[], metavar='AXIS=MEMBER')
    args = parser.parse_args()
    pairs = []
    for item in args.member:
        if '=' not in item:
            parser.error(f'bad --member {item!r}; expected AXIS=MEMBER')
        pairs.append(tuple(item.split('=', 1)))
    print(json.dumps(extract(args.html, args.concept, args.start, args.end, pairs), indent=2))


if __name__ == '__main__':
    main()
