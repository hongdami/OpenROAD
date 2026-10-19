// examples/systolic2x2/rtl/processing_element.sv
module processing_element (
  input  logic                     clk,
  input  logic                     reset,
  input  logic                     valid_in,
  input  logic                     start_in,
  input  logic                     last_in,
  input  logic signed [7:0]        a_in,
  input  logic signed [7:0]        b_in,
  output logic                     valid_out,
  output logic                     start_out,
  output logic                     last_out,
  output logic signed [7:0]        a_out,
  output logic signed [7:0]        b_out,
  output logic signed [23:0]       acc_out
);
  logic signed [15:0] product;
  logic signed [23:0] extended_product;

  always_comb begin
    product = a_in * b_in;
    extended_product = {{8{product[15]}}, product};
  end

  always_ff @(posedge clk) begin
    if (reset) begin
      valid_out <= 1'b0;
      start_out <= 1'b0;
      last_out <= 1'b0;
      a_out <= '0;
      b_out <= '0;
      acc_out <= '0;
    end else begin
      valid_out <= valid_in;
      start_out <= valid_in && start_in;
      last_out <= valid_in && last_in;
      if (valid_in) begin
        a_out <= a_in;
        b_out <= b_in;
        if (start_in)
          acc_out <= extended_product;
        else
          acc_out <= acc_out + extended_product;
      end
    end
  end
endmodule
