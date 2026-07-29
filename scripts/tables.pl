#!/usr/bin/perl
# tables.pl main.tex -> in-place edit. ORE requires every table (with its
# legend) to appear in a dedicated "Tables" section AFTER the References, not
# inline in the body. This script:
#   1. finds every ACTIVE (non-commented) \begin{table}...\end{table} and
#      \begin{table*}...\end{table*} block,
#   2. removes each from its original in-text position,
#   3. relocates them, in original document order, into a new
#      "\section*{Tables}" section inserted immediately AFTER the
#      \bibliography{...} line (so the section falls after the reference list).
#      If there is no \bibliography line, it is inserted just before
#      \end{document}.
# \label{...}/\caption{...} are moved with their table, so \ref{tab:...}
# cross-references in the body keep resolving. Commented-out table blocks
# (lines starting with %) are left untouched.
#
# Runs on the AUTHOR-FACING copy (ore-submission/tex/main.tex), which still has
# a real \bibliography line, so the copy keeps compiling. At conversion time
# preprocess.pl replaces \bibliography with \hypertarget{refs}{} and figures.pl
# inserts the Figure Legends section immediately before this "Tables" section,
# giving the final ORE order: References -> Figure Legends -> Tables.
use strict;
use warnings;

my ($texfile) = @ARGV;
die "usage: tables.pl main.tex\n" unless $texfile;

local $/;
open( my $fh, '<', $texfile ) or die $!;
my $tex = <$fh>;
close $fh;

my @tables;

# Find all non-commented \begin{table}...\end{table} blocks (dotall so a block
# can span multiple lines). A leading %-comment line would start with % before
# \begin, so anchoring at optional leading whitespace keeps commented blocks
# (which have % first) from matching.
my @matches;
while ( $tex =~ /^([ \t]*)(\\begin\{table\*?\}.*?\\end\{table\*?\})/msg ) {
    push @matches, { full => $1 . $2, block => $2 };
}

for my $m (@matches) {
    push @tables, $m->{block};

    # Remove the original block from the body.
    my $orig = $m->{full};
    my $idx = index( $tex, $orig );
    if ( $idx >= 0 ) {
        substr( $tex, $idx, length($orig) ) = "";
    }
}

if ( !@tables ) {
    print "tables.pl: no tables to relocate\n";
    exit 0;
}

my $tables_block =
  "\n\\section*{Tables}\n" . join( "\n\n", @tables ) . "\n";

# Insert immediately after the \bibliography{...} line if present, else before
# \end{document}, else append.
if ( $tex =~ /^(\\bibliography\{[^}]*\}[ \t]*\n)/m ) {
    my $bibline = $1;
    $tex =~ s/\Q$bibline\E/$bibline$tables_block/;
}
elsif ( $tex =~ /\\end\{document\}/ ) {
    $tex =~ s/\\end\{document\}/$tables_block\n\\end{document}/;
}
else {
    $tex .= $tables_block;
}

open( my $ofh, '>', $texfile ) or die $!;
print $ofh $tex;
close $ofh;

print "tables.pl: relocated " . scalar(@tables) . " table block(s) to Tables section\n";
