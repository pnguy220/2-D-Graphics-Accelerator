TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(abspath draw_engine.sv)
TOPLEVEL = draw_engine
MODULE = test_draw_engine

include $(shell cocotb-config --makefiles)/Makefile.sim
