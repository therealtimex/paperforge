## Chapter Three. Where the folio restarts {.part}

Front matter is numbered in roman and the book proper in arabic, restarting at
one. The convention is old enough that its reasons are worth restating, because
they are practical rather than decorative.

Front matter is written last and its length is not known while the book is being
set. Numbering it separately means that adding two pages of preface does not
renumber the whole book, invalidate an index, or move every cross-reference by
two. The roman sequence absorbs the change and the arabic sequence does not
notice it.

The restart lands on a recto, because the first page of the book proper is a
chapter opening like any other. That makes the parity of the arabic sequence
agree with the parity of the leaves: odd numbers on the right, even on the left,
for the whole of the book. A restart on a verso inverts that for every page that
follows, and the inversion is invisible on screen and obvious in the hand.

There is a second reason, less often given, which is that the two sequences mean
different things. A roman numeral in a citation is understood to point at
apparatus: a preface, an editor's note, a table of contents. An arabic numeral
points at the work. A reader who sees a reference to page xii knows, before
turning to it, roughly what kind of thing they will find there. Collapsing the
two sequences into one throws that away for the sake of a simpler counter.

The restart also has to survive the machinery that produces it. A renderer that
suppresses the folio on blank leaves has, at that moment, an instruction to stop
printing page numbers, and the instruction has to expire before the chapter
opening that follows. Scoped to the leaves it creates, it does. Scoped to the
document, it silently removes the folio from every page after the first blank,
and the failure appears in the middle of a book rather than at its start, where
nobody thinks to look for it.

The last thing worth stating about the folio is where it goes. Centred at the
foot, it belongs to no side and needs no mirroring. Set at the outer corner it
has to swap sides with the margins, and a book that mirrors its margins without
mirroring its folios ends up with page numbers marching into the gutter on every
verso, which is both wrong and, once seen, impossible to stop seeing.
