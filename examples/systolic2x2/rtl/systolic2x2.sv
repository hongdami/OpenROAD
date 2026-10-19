// examples/systolic2x2/rtl/systolic2x2.sv
module systolic2x2 (
  input  logic                      clk,
  input  logic                      reset,
  input  logic                      valid_in,
  input  logic                      start,
  input  logic                      last,
  input  logic signed [15:0]        a_left,
  input  logic signed [15:0]        b_top,
  output logic signed [23:0]        c00,
  output logic signed [23:0]        c01,
  output logic signed [23:0]        c10,
  output logic signed [23:0]        c11,
  output logic                      done
);
  logic signed [7:0] a1_skew, b1_skew;
  logic skew_valid, skew_start, skew_last;

  logic signed [7:0] a00_right, b00_down;
  logic signed [7:0] a01_right, b01_down;
  logic signed [7:0] a10_right, b10_down;
  logic signed [7:0] a11_right, b11_down;
  logic v00, s00, l00, v01, s01, l01;
  logic v10, s10, l10, v11, s11, l11;

  always_ff @(posedge clk) begin
    if (reset) begin
      a1_skew <= '0;
      b1_skew <= '0;
      skew_valid <= 1'b0;
      skew_start <= 1'b0;
      skew_last <= 1'b0;
    end else begin
      skew_valid <= valid_in;
      skew_start <= valid_in && start;
      skew_last <= valid_in && last;
      if (valid_in) begin
        a1_skew <= a_left[15:8];
        b1_skew <= b_top[15:8];
      end
    end
  end

  processing_element pe00 (
    .clk, .reset,
    .valid_in, .start_in(start), .last_in(last),
    .a_in(a_left[7:0]), .b_in(b_top[7:0]),
    .valid_out(v00), .start_out(s00), .last_out(l00),
    .a_out(a00_right), .b_out(b00_down), .acc_out(c00)
  );

  processing_element pe01 (
    .clk, .reset,
    .valid_in(v00), .start_in(s00), .last_in(l00),
    .a_in(a00_right), .b_in(b1_skew),
    .valid_out(v01), .start_out(s01), .last_out(l01),
    .a_out(a01_right), .b_out(b01_down), .acc_out(c01)
  );

  processing_element pe10 (
    .clk, .reset,
    .valid_in(v00), .start_in(s00), .last_in(l00),
    .a_in(a1_skew), .b_in(b00_down),
    .valid_out(v10), .start_out(s10), .last_out(l10),
    .a_out(a10_right), .b_out(b10_down), .acc_out(c10)
  );

  processing_element pe11 (
    .clk, .reset,
    .valid_in(v10), .start_in(s10), .last_in(l10),
    .a_in(a10_right), .b_in(b01_down),
    .valid_out(v11), .start_out(s11), .last_out(l11),
    .a_out(a11_right), .b_out(b11_down), .acc_out(c11)
  );

  assign done = v11 && l11;
endmodule
