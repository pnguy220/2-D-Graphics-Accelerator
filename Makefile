TOPLEVEL_LANG = verilog
SIM ?= icarus
VERILOG_SOURCES = $(abspath draw_engine.sv)
TOPLEVEL = draw_engine
MODULE = test_draw_engine
SIM_BUILD = sim_build/$(TOPLEVEL)_$(MODULE)

include $(shell cocotb-config --makefiles)/Makefile.sim
