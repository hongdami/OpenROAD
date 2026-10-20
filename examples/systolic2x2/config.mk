# examples/systolic2x2/config.mk
export DESIGN_NAME = systolic2x2
export PLATFORM = sky130hd

export VERILOG_FILES = \
  /work/examples/systolic2x2/rtl/processing_element.sv \
  /work/examples/systolic2x2/rtl/systolic2x2.sv
export SDC_FILE = /work/examples/systolic2x2/constraint.sdc
export SYNTH_CANONICALIZE_TCL = /work/examples/systolic2x2/orfs_canonicalize.tcl

export CORE_UTILIZATION ?= 35
export PLACE_DENSITY_LB_ADDON = 0.10
export TNS_END_PERCENT = 100
export SYNTH_REPEATABLE_BUILD ?= 1
export ABC_AREA = 1
export ADDER_MAP_FILE :=
