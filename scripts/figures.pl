#!/usr/bin/perl
# figures_S.pl work.tex -> in-place edit implementing Figure Strategy S:
# Every ACTIVE (non-commented) \begin{figure}...\end{figure} block is:
#   1. stripped of all \includegraphics[...]{...} lines (no image data at all)
#   2. removed from its original in-text position
#   3. relocated, in original document order, into a new
#      "\section*{Figure Legends}" section. ORE section order is
#      References -> Figure Legends -> Tables, so if a "\section*{Tables}"
#      block already exists (Phase 2 moves tables there, after \bibliography),
#      the Figure Legends section is inserted immediately BEFORE it; otherwise
#      it is inserted just before \end{document}.
# \label{...}/\caption{...} (incl. inside \subfigure) are preserved so that
# \ref{...} cross-references elsewhere in the body keep resolving correctly.
# Commented-out figure blocks (lines starting with %) are left untouched.
use strict;
use warnings;

my ($texfile) = @ARGV;
die "usage: figures_S.pl work.tex\n" unless $texfile;

local $/;
open( my $fh, '<', $texfile ) or die $!;
my $tex = <$fh>;
close $fh;

my @legends;

# Find all non-commented \begin{figure}...\end{figure} blocks (dotall so the
# block can span multiple lines).
my @matches;
while ( $tex =~ /^([ \t]*)(\\begin\{figure\*?\}.*?\\end\{figure\*?\})/msg ) {
    push @matches, { full => $1 . $2, block => $2 };
}

for my $m (@matches) {
    my $stripped = $m->{block};
    $stripped =~ s/^[ \t]*\\includegraphics(\[[^\]]*\])?\{[^}]*\}[ \t]*\n?//mg;
    push @legends, $stripped;

    # Remove the original (unstripped) block from the body.
    my $orig = $m->{full};
    my $idx = index( $tex, $orig );
    if ( $idx >= 0 ) {
        substr( $tex, $idx, length($orig) ) = "";
    }
}

my $legends_block = "\n\\section*{Figure Legends}\n" . join( "\n\n", @legends ) . "\n";

# ORE order: References -> Figure Legends -> Tables. If Phase 2 has already
# placed a "\section*{Tables}" block (after \bibliography), insert the Figure
# Legends section immediately before it; otherwise fall back to just before
# \end{document}.
my $tables_re = qr/\\section\*?\{Tables\}/;
if ( $tex =~ $tables_re ) {
    $tex =~ s/($tables_re)/$legends_block\n$1/;
}
elsif ( $tex =~ /\\end\{document\}/ ) {
    $tex =~ s/\\end\{document\}/$legends_block\n\\end{document}/;
}
else {
    $tex .= $legends_block;
}

open( my $ofh, '>', $texfile ) or die $!;
print $ofh $tex;
close $ofh;

print "figures_S.pl: relocated " . scalar(@legends) . " figure block(s) to Figure Legends section\n";
