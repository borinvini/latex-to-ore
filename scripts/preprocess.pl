#!/usr/bin/perl
# preprocess_B.pl work_B.tex -> in-place edit, for Reference Path B (citeproc)
# Same as preprocess.pl but does NOT inline main.bbl; instead removes both
# \bibliographystyle{...} and \bibliography{...} lines entirely (citeproc
# supplies the bibliography via --bibliography/--csl flags instead).
use strict; use warnings;

my ($texfile) = @ARGV;
die "usage: preprocess_B.pl work_B.tex\n" unless $texfile;

local $/;
open(my $fh, '<', $texfile) or die $!;
my $tex = <$fh>;
close $fh;

# 0. Strip \makeatletter ... \makeatother blocks. In this paper this block
#    only contains raw \@startsection redefinitions of \section/\subsection/
#    \subsubsection (for PDF vertical-spacing tweaks) and a \@listi tweak.
#    Pandoc's LaTeX reader does not understand \@startsection and expands the
#    \def literally, leaking text like "0.4ex plus 0.4ex minus 0ex" in front
#    of every heading. None of this affects DOCX output, so drop it wholesale.
$tex =~ s/\\makeatletter.*?\\makeatother\n?//gs;

# 1. Delete \bibliographystyle{...} line
$tex =~ s/^\\bibliographystyle\{[^}]*\}\s*\n//m;

# 2. Replace \bibliography{...} line with a "References" heading followed by
#    \hypertarget{refs}{} so citeproc places the generated reference list at THIS
#    point (where the author's bibliography was) instead of appending it at the
#    very end of the document. Pandoc's LaTeX reader turns \hypertarget{refs}{}
#    into a Div with id "refs", which is exactly the anchor citeproc uses for the
#    bibliography. The \section*{References} gives the reference list a proper
#    ORE heading (matching Ethics / Grant Information etc.) with heading spacing —
#    citeproc itself emits no heading. This yields the ORE order
#    References -> Figure Legends -> Tables: the Figure Legends and Tables
#    sections (added after \bibliography) then follow the reference list. hyperref
#    need not be loaded — pandoc recognises \hypertarget regardless.
$tex =~ s/^\\bibliography\{[^}]*\}\s*\n/\\section*{References}\n\\hypertarget{refs}{}\n/m;

# 2b. Give the keywords their own "Keywords" heading. IEEEtran's IEEEkeywords
#    environment otherwise renders (via Pandoc) as a bare paragraph with no
#    label. Emitting \section*{Keywords} makes Pandoc produce a Heading1
#    "Keywords"; postprocess.py then retypes that heading to the ORE
#    "Abstract Title" style so it matches the abstract's heading, per ORE house
#    style. Captures the keyword list and re-emits it as the section body.
$tex =~ s/\\begin\{IEEEkeywords\}(.*?)\\end\{IEEEkeywords\}/\\section*{Keywords}\n\n$1\n/s;

# 3. Strip \begin{IEEEbiographynophoto}...\end{IEEEbiographynophoto} blocks
$tex =~ s/\\begin\{IEEEbiographynophoto\}.*?\\end\{IEEEbiographynophoto\}\n?//gs;

# 4. \IEEEPARstart{X}{ext} -> Xext
$tex =~ s/\\IEEEPARstart\{([^}]*)\}\{([^}]*)\}/$1$2/g;

# 5. Remove \bstctlcite{...}, \balance, \IEEEpeerreviewmaketitle
$tex =~ s/\\bstctlcite\{[^}]*\}\s*\n?//g;
$tex =~ s/\\balance\b\s*//g;
$tex =~ s/\\IEEEpeerreviewmaketitle\b\s*//g;

# 6. Unwrap highlight/review macros
for my $macro (qw(hlyellow hlgreen hlpink hlred review)) {
    my $changed = 1;
    while ($changed) {
        $changed = 0;
        $tex =~ s/\\$macro\{((?:[^{}]|\{[^{}]*\})*)\}/$1/g and $changed = 1;
    }
}

# 7. Inside \author{...}, convert LaTeX line breaks (\\ or \\[2pt]) to \and.
#    IEEEtran honours \\ as real line breaks in the review PDF, so the author
#    block (names / affiliation / corresponding author) typesets cleanly there.
#    But Pandoc DROPS \\ inside \author{} (mashing the lines onto one line),
#    while it renders each \and-separated chunk as its OWN line in the ORE
#    "Author" style. Rewriting only this throwaway conversion copy gives a clean
#    review PDF AND a clean DOCX from the same author-facing .tex.
$tex =~ s{(\\author\{(?:[^{}]|\{[^{}]*\})*\})}{
    my $b = $1;
    $b =~ s{\\\\\s*(?:\[[^\]]*\])?}{ \\and }g;
    $b;
}ge;

# 7b. De-star full-width float environments: table* -> table, figure* -> figure.
#    The star only requests a two-column-spanning float in a LaTeX twocolumn
#    layout; it is meaningless for the single-column DOCX. Worse, Pandoc's LaTeX
#    reader fails to associate the \caption inside a table* with the table, so a
#    starred table converts WITHOUT its caption (and thus is not numbered, which
#    also breaks the in-text \ref to it). Dropping the star restores the caption.
$tex =~ s/\\(begin|end)\{table\*\}/\\$1\{table\}/g;
$tex =~ s/\\(begin|end)\{figure\*\}/\\$1\{figure\}/g;

# 8. Unwrap \resizebox{W}{H}{ CONTENT } -> CONTENT and
#    \rotatebox[opts]{angle}{ CONTENT } -> CONTENT.
#    IEEE papers routinely wrap wide tables in \resizebox{\columnwidth}{!}{ ...
#    \begin{tabular} ... } and rotate header cells with \rotatebox{90}{...}.
#    Pandoc's LaTeX reader does NOT look inside \resizebox, so the tabular becomes
#    an unparsed argument and the whole table (caption included) is dropped or
#    garbled in the DOCX. Removing these graphics wrappers exposes the plain
#    tabular so Pandoc converts it to a native Word table. A self-recursive regex
#    ($nested matches a balanced {...} group) strips the CONTENT argument's outer
#    braces while preserving its (arbitrarily nested) inner braces.
my $nested = qr/(\{(?:[^{}]++|(?1))*\})/;
# \resizebox has two brace args (width, height) before the content arg.
1 while $tex =~ s/\\resizebox\s*\{[^{}]*\}\s*\{[^{}]*\}\s*$nested/ substr($1, 1, -1) /ge;
# \rotatebox has an optional [..] then one brace arg (angle) before the content.
1 while $tex =~ s/\\rotatebox\s*(?:\[[^\]]*\])?\s*\{[^{}]*\}\s*$nested/ substr($1, 1, -1) /ge;

# 9. Demote inline math that is nothing but a thousands-separated number to plain
#    text: $5{,}915$ -> 5,915 and $245{,}000$ -> 245,000. IEEE authors write these
#    in math mode so LaTeX kerns the separator, but Pandoc converts them to OMML
#    and Word then typesets the comma as a math punctuation operator, inserting a
#    space after it ("5, 915"). These are not equations, so unwrapping the $...$
#    and dropping the {} braces yields a normally spaced number in the DOCX.
$tex =~ s/\$(\d{1,3}(?:\{,\}\d{3})+)\$/ my $n = $1; $n =~ s|\{,\}|,|g; $n /ge;

open(my $ofh, '>', $texfile) or die $!;
print $ofh $tex;
close $ofh;

print "preprocess_B.pl: done\n";
