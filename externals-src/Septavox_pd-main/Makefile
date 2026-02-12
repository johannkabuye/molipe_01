# Makefile to build class 'helloworld' for Pure Data.
# Needs Makefile.pdlibbuilder as helper makefile for platform-dependent build
# settings and rules.

# library name
lib.name = septavox~

# input source file (class name == source file basename)
class.sources = septavox~.c
#common.sources = pp6.c
common.sources = pp6.c audio.c oscillator.c wave_synth.c mode_adsr.c mode_octave_arp.c line.c sad.c sadsr.c mode_simple_poly.c mode_mega_wave.c mode_octave_cascade.c mode_slicer.c mode_slider.c

# all extra files to be included in binary distribution of the library
# datafiles = helloworld-help.pd helloworld-meta.pd README.md

# include Makefile.pdlibbuilder from submodule directory 'pd-lib-builder'
PDLIBBUILDER_DIR=pd-lib-builder/
include $(PDLIBBUILDER_DIR)/Makefile.pdlibbuilder

