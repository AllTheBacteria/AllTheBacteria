#!/usr/bin/env perl
use strict;
use warnings;
use File::Basename;
use File::Spec;


@ARGV == 3 or die "usage: $0 <in.tar.xz> <outdir> <new_name>";

my $tar_in = File::Spec->rel2abs($ARGV[0]);
my $outdir = $ARGV[1];
my $newname = $ARGV[2];


# miniphy does this with the naming of genus/species batch N:
# tarball: genus_species__N.asm.tar.xz
# extracts to: genus_species__N/
die "Output dir doesn't exist: $outdir" unless -e $outdir;
die "Input tarball doesn't end with .asm.tar.xz: $tar_in" unless $tar_in =~ /\.asm\.tar\.xz/;
my $oldname = basename($tar_in);
$oldname =~ s/.asm.tar.xz//;

chdir $outdir or die $!;
die "Extracted dir already exists $oldname" if -e "$oldname";

# get the filenames in the order they were added
my @filenames = `tar tsf $tar_in`;
chomp @filenames;
@filenames = grep(/\.fa$/, @filenames);


# extract to cwd, and then rename the extracted dir
system("tar xf $tar_in -C .") and die $!;
system("mv $oldname $newname") and die $!;


# write filenames to a file that can be input to tar, so the new
# archive has files added in the same order as the original
my $filenames_file = "$newname.file_list";
@filenames = map{s/$oldname/$newname/; $_} @filenames;
open (my $f, ">", "$filenames_file") or die $!;
foreach (@filenames) {
    print $f "$_\n";
}
close $f or die $!;

# Make the new tarball and clean up temp files
system("tar cf $newname.tar.xz -T $filenames_file -I 'xz -9'") and die $!;
unlink $filenames_file or die $!;
system("rm -r $newname") and die $!;

