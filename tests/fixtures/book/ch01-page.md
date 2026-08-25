## Chapter One. What a bound page owes the reader {.part}

A page in a bound book is not a rectangle of text. It is one side of a leaf,
and the leaf has another side, and the two are held together at an edge that
disappears into the binding. Every decision about the page follows from that
physical fact, and a renderer that treats the page as a rectangle produces
something that reads correctly and looks wrong.

The first consequence is the margin. A page bound at its left edge loses part
of that edge to the curve of the gutter, so the inside margin has to be wider
than the outside one. On a leaf printed on both sides the inside edge alternates
between left and right, which is why the margins of a book are described as
mirrored rather than as left and right. A document with symmetric margins looks
even when it is flat on a screen and lopsided the moment it is bound.

The second consequence is the opening. A reader turning to a new chapter should
find it under their right hand, on the recto, because that is where the eye
lands when a book is opened. Making that happen costs a page whenever the
previous chapter ends on a recto itself, and the cost is paid deliberately: the
leaf left over is blank, and it is blank in the strict sense, carrying neither a
folio nor a running head.

The third consequence is the running head. Its job is to answer the question a
reader asks halfway through a chapter with the book held open at one spread:
where am I. The conventional answer puts the book on the left-hand page and the
chapter on the right-hand one, so that a single spread names both. Repeating the
book title on every page of every chapter answers a question nobody asked.

None of these are matters of taste that a house style may settle either way.
They are what a reader's hands expect, and the expectation was set by four
centuries of books that met it.

The measure follows from the trim in the same way. A line the eye can follow
without losing its place on the return sweep runs to about sixty-six characters,
and that number, not the width of the paper, is what sets the text block. On a
royal octavo page a single column of ten-and-a-half point type lands close to it
without effort. On A4 the same setting gives ninety characters and the reader
begins skipping lines, which is why an A4 page that has to hold body text is
usually set in two columns and why a book almost never is.

The relationship runs the other way too. Having chosen a measure, the margins
are what is left, and they are not waste. The outer margin is where a thumb
goes, the lower margin is what stops the last line falling off the edge when the
book is trimmed, and the upper margin holds the running head clear of the text
without a rule between them. A page designed by shrinking the margins until the
text fits is a page whose reader has nowhere to put their hands.

None of this is expensive to get right. It is expensive to get right *later*,
which is the argument for the renderer knowing what kind of object it is
producing rather than being told, page by page, what to do about it.

A last consequence, and the one most often left out: the first page. A book does
not open with its first chapter. It opens with a half-title, and the half-title
is a recto, and the leaf behind it is blank. Everything after that inherits the
parity the half-title established, which is why a front matter that starts on
the wrong side puts every chapter opening in the book on the wrong side too.
