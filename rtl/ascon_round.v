module ascon_round (
    input  [319:0] s_in,
    input  [7:0]   rc,
    output [319:0] s_out
);
    function [63:0] ror(input [63:0] x, input integer n);
        ror = (x >> n) | (x << (64 - n));
    endfunction

    wire [63:0] a0 = s_in[319:256], a1 = s_in[255:192], a3 = s_in[127:64], a4 = s_in[63:0];
    wire [63:0] a2 = s_in[191:128] ^ {56'd0, rc};

    wire [63:0] b0 = a0 ^ a4, b1 = a1, b2 = a2 ^ a1, b3 = a3, b4 = a4 ^ a3;
    wire [63:0] t0 = ~b0 & b1, t1 = ~b1 & b2, t2 = ~b2 & b3, t3 = ~b3 & b4, t4 = ~b4 & b0;
    wire [63:0] c0 = b0 ^ t1, c1 = b1 ^ t2, c2 = b2 ^ t3, c3 = b3 ^ t4, c4 = b4 ^ t0;
    wire [63:0] d0 = c0 ^ c4, d1 = c1 ^ c0, d2 = ~c2, d3 = c3 ^ c2, d4 = c4;

    assign s_out = {
        d0 ^ ror(d0, 19) ^ ror(d0, 28),
        d1 ^ ror(d1, 61) ^ ror(d1, 39),
        d2 ^ ror(d2, 1)  ^ ror(d2, 6),
        d3 ^ ror(d3, 10) ^ ror(d3, 17),
        d4 ^ ror(d4, 7)  ^ ror(d4, 41)
    };
endmodule
