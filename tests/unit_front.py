#!/usr/bin/env python3
"""Structured front matter: parsed, validated, and refusing to guess.

The last of the three gaps between this pipeline and a manuscript. A document
head was prose - `**Publisher:** X` - which is right for a ministry cover and
wrong for a paper, where an author carries affiliation markers, an ORCID and a
corresponding flag, and those markers have to point somewhere real.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paperforge import front, lint, profile

failures = []

GOOD = '''+++
abstract = "Physical AI reshapes production."
keywords = ["Physical AI", "Việt Nam"]

[[author]]
name = "Trần Văn A"
affiliation = [1, 2]
orcid = "0000-0002-1825-0097"
corresponding = true
email = "a@example.gov.vn"

[[author]]
name = "Nguyễn Thị B"
affiliation = [2]

[affiliation]
1 = "Ministry of Foreign Affairs"
2 = "National Innovation Centre"

[declarations]
funding = "State budget."
conflicts = "None declared."
+++

# ARTICLE
## A title
'''


def check(label, condition):
    print('  %-58s %s' % (label, 'ok' if condition else 'FAIL'))
    if not condition:
        failures.append(label)


def main():
    print('parsing')
    data, body = front.split(GOOD)
    check('the block is taken off the top', body.strip().startswith('# ARTICLE'))
    check('and the fence does not survive into the body', '+++' not in body)
    check('a document without front matter is untouched',
          front.split('# TITLE\n')[0] == {} and front.split('# TITLE\n')[1] == '# TITLE\n')
    try:
        front.split('+++\nname = "x"\n')
        check('an unclosed block is an error, not a silent skip', False)
    except ValueError:
        check('an unclosed block is an error, not a silent skip', True)
    try:
        front.split('+++\nthis is not toml\n+++\n')
        check('malformed TOML is an error, not a silent skip', False)
    except ValueError:
        check('malformed TOML is an error, not a silent skip', True)

    print('laying it out')
    check('the byline carries markers and the corresponding star',
          front.byline(data) == [('Trần Văn A', '1,2,*'), ('Nguyễn Thị B', '2')])
    check('only marker-shaped keys count as affiliations',
          set(front.affiliations(data)) == {'1', '2'})
    check('the corresponding line names the author and the address',
          'Trần Văn A' in front.corresponding(data) and 'a@example.gov.vn' in front.corresponding(data))
    check('declarations come out in a stable order',
          [k for k, _ in front.declarations(data, profile.load('en'))]
          == ['Funding', 'Conflicts of interest'])
    check('labels are localised',
          front.label(profile.load('vi'), 'abstract') == 'Tóm tắt')

    print('refusing to guess')
    check('a correct block has no problems', front.problems(data) == [])
    bad, _ = front.split(GOOD.replace('affiliation = [1, 2]', 'affiliation = [1, 9]'))
    check('a marker pointing at nothing is reported',
          any('affiliation 9' in p for p in front.problems(bad)))
    # both authors have to stop citing it: A cites [1, 2] as well
    unused, _ = front.split(GOOD.replace('affiliation = [1, 2]', 'affiliation = [1]')
                            .replace('affiliation = [2]\n', 'affiliation = [1]\n'))
    check('an affiliation nobody cites is reported',
          any('no author cites' in p for p in front.problems(unused)))
    orcid, _ = front.split(GOOD.replace('0000-0002-1825-0097', '1825-0097'))
    check('a malformed ORCID is reported',
          any('ORCID' in p for p in front.problems(orcid)))
    nobody, _ = front.split(GOOD.replace('corresponding = true\n', ''))
    check('no corresponding author is reported',
          any('corresponding' in p for p in front.problems(nobody)))

    # TOML's own rule, and the quietest way to get this wrong
    trap, _ = front.split(GOOD.replace('abstract = "Physical AI reshapes production."\n', '')
                          .replace('2 = "National Innovation Centre"',
                                   '2 = "National Innovation Centre"\nabstract = "swallowed"'))
    check('an abstract written below [affiliation] is reported, not lost',
          any('written after [affiliation]' in p for p in front.problems(trap)))
    check('and it does not masquerade as an affiliation',
          'abstract' not in front.affiliations(trap))

    # The same trap one table header earlier, and the likelier one: [[author]]
    # is the first header in every example anyone writes. It went unnoticed
    # until a manuscript was built and its abstract simply was not on the page.
    sunk, _ = front.split(GOOD.replace('abstract = "Physical AI reshapes production."\n', '')
                          .replace('name = "Nguyễn Thị B"',
                                   'name = "Nguyễn Thị B"\nabstract = "swallowed"'))
    check('an abstract written below [[author]] is reported too',
          any("'abstract' is not a key an author carries" in p
              for p in front.problems(sunk)))
    check('the author it was swallowed by is named',
          any('Nguyễn Thị B' in p for p in front.problems(sunk)))
    check('and so is the way out of it',
          any('above the first table header' in p for p in front.problems(sunk)))
    check('a correctly placed abstract raises nothing',
          not any('not a key an author carries' in p for p in front.problems(data)))

    print('the blind review copy')
    blind = front.anonymise(data, profile.load('en'))
    check('the author list is gone', 'author' not in blind)
    check('the affiliations are gone', 'affiliation' not in blind)
    check('funding is gone, because a funder identifies a group',
          'funding' not in (blind.get('declarations') or {}))
    check('conflicts stay, because a reviewer needs them',
          'conflicts' in (blind.get('declarations') or {}))
    check('the abstract and keywords stay',
          blind.get('abstract') and blind.get('keywords'))
    check('and the copy says why the names are missing',
          'blind review' in blind.get('anonymised', ''))
    check('the notice is localised',
          'phản biện kín' in front.anonymise(data, profile.load('vi'))['anonymised'])
    check('anonymising nothing is not an error', front.anonymise({}, None) == {})
    check('the original is not mutated', 'author' in data)

    print('the gate')
    with tempfile.TemporaryDirectory() as tmp:
        doc = Path(tmp) / 'r.md'
        doc.write_text(GOOD.replace('affiliation = [1, 2]', 'affiliation = [1, 9]'),
                       encoding='utf-8')
        found = lint.check_front_matter(doc)
        check('lint blocks a marker pointing at nothing',
              found and found[0]['severity'] == 'block')
        doc.write_text(GOOD, encoding='utf-8')
        check('and passes a correct block', lint.check_front_matter(doc) == [])

    if failures:
        print('\n%d check(s) failed: %s' % (len(failures), '; '.join(failures)))
        return 1
    print('\nfront matter: all checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
