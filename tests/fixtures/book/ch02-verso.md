## Chapter Two. The blank verso {.part}

The blank leaf inserted before a chapter opening is the smallest piece of
typesetting that is most often got wrong, because getting it wrong produces
something that looks deliberate.

A page that carries a folio and a running head and no text is not read as a
blank page. It is read as a page whose text has gone missing, and the reader
checks the pagination to see what they have lost. A page that carries nothing at
all is read as what it is: the back of the previous leaf, present because paper
has two sides. The difference is one line of instruction to the renderer and it
is the difference between a book and a printout.

The blank leaf still counts. Pagination runs through it, so the chapter that
follows a blank verso is numbered as though the blank had been printed on, and
a reference to a page in that chapter resolves the way a reader counting leaves
would expect. Suppressing the folio is not the same as suppressing the page, and
a renderer that removes it from the count produces a book whose page numbers
drift further from its leaves with every chapter.

Producing the blank at all is harder than it looks in any system that decides
where pages break by laying the text out. Asking whether the current page is
even, and inserting a break if it is, does not converge: inserting the break
makes the page odd, which removes the condition that inserted it, which makes
the page even again. A renderer has to be told to break to a recto and left to
work out for itself how many leaves that takes.

The instruction is worth stating precisely, because the two halves are
separable. Break to the next odd page is one thing. Leave what you skip
completely bare is another, and a renderer will happily do the first while
styling the skipped leaf exactly like every other page in the book.

There is a further case that only shows up in a long document. When the previous
chapter happens to end on a verso, no leaf needs to be skipped at all, and the
instruction to leave skipped leaves bare must not then strip the folio from the
chapter opening that follows. A rule scoped to the pages it creates does the
right thing in both cases; a rule scoped to the document does the right thing in
one of them and quietly breaks the other, which is the harder failure to notice
because it only appears in chapters of a particular length.

It is worth separating two things that look alike here. Leaving a leaf blank
because the next chapter must open on a recto is a decision about structure, and
the blank carries meaning: it says a division has ended. Leaving a leaf blank
because the text happened to run out is an accident, and a good setting does not
produce one. The first is planned and the second is a symptom, and a renderer
that cannot tell them apart will either produce accidental blanks or suppress
the deliberate ones.

The same distinction governs what may be pushed onto the blank. Nothing may. It
is tempting to fill a deliberate blank with an epigraph, a frontispiece, or the
first illustration of the chapter that follows, and each of those turns the leaf
into a page that a reader will look at, which is the one thing it exists not to
be. If a book has an illustration to place, it goes on a page that was going to
exist regardless.

Where the convention genuinely bends is in short-run and print-on-demand work,
where every leaf has a unit cost and a hundred-page book with fourteen chapters
carries seven blanks it is paying for. Publishers working to that constraint set
chapters to open on any new page rather than on a recto, and the result is a
legitimate object that is simply not a bound book in the traditional sense. It
is a decision about economics, and it belongs in the manifest where somebody
made it, rather than in a renderer that quietly assumes one answer.

What a renderer must not do is offer the convention and implement half of it.
A book whose chapters open recto but whose blanks carry folios is not a
compromise between the two positions; it is the first position, executed
incorrectly, and it will be read that way by anybody who notices.

### How the convention is checked

A convention this mechanical can be verified mechanically, and the check is
worth writing down because it is not the obvious one. The obvious check reads
the first words of each page and asks whether a chapter title is among them.
Applied to a bound edition it passes for the wrong reason: the running head puts
the chapter title at the top of every recto in the chapter, so a chapter that
never opened a page at all still answers to the probe on the second, third and
fourth leaf of its own text. The check reports success over text it should not
have been reading.

Dropping the top margin before reading fixes it, and the fix is safe in a way
that a general crop is not. The running head lives in the top margin by
construction and the body begins below it, so removing that band removes the
head and nothing else. A crop taken anywhere else — down the middle of a page to
separate two columns, for instance — cuts through content that is entitled to
cross it, and a part banner sliced in half is unfindable by any probe.

The general lesson is the one this pipeline keeps relearning. A check that reads
an artefact assumes a layout, and when the layout changes the check does not
fail; it goes on passing, against different text, and says nothing about the
thing it was written to guard.

### What the reader actually notices

Almost none of this is noticed consciously. A reader does not think about the
gutter, and would not be able to say which side a chapter opened on if asked an
hour later. What they notice is the absence of friction: they never lose the
return sweep, never turn back a leaf to check a page number, never wonder
whether they have missed something. Typography that is working is invisible, and
the only reliable way to find out whether it is working is to get one of these
things wrong and watch a reader stumble over it.
