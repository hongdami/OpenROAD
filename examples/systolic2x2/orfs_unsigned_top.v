// OpenROAD's pinned gate-level parser rejects signed top-level ports.
// Preserve the bit-level interface through an unsigned synthesis-only shell.
module systolic2x2 (
  input         clk,
  input         reset,
  input         valid_in,
  input         start,
  input         last,
  input  [15:0] a_left,
  input  [15:0] b_top,
  output [23:0] c00,
  output [23:0] c01,
  output [23:0] c10,
  output [23:0] c11,
  output        done
);
  systolic2x2_signed wrapped_design (
    .clk(clk),
    .reset(reset),
    .valid_in(valid_in),
    .start(start),
    .last(last),
    .a_left(a_left),
    .b_top(b_top),
    .c00(c00),
    .c01(c01),
    .c10(c10),
    .c11(c11),
    .done(done)
  );
endmodule
