# Keep the signed RTL intact while presenting unsigned top-level vectors to
# the pinned OpenROAD gate-level Verilog parser.
yosys rename systolic2x2 systolic2x2_signed
read_verilog /work/examples/systolic2x2/orfs_unsigned_top.v
hierarchy -check -top systolic2x2
