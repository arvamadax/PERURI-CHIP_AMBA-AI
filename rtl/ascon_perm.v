// State register 320-bit + penghitung ronde. Tiap siklus menjalankan UNROLL ronde.
// start: jalankan permutasi pada d_in (p12=1: 12 ronde, 0: 8 ronde). run=1 selama masih ada ronde.
// Hasil valid di st saat run=0. UNROLL harus 1, 2, atau 4.
module ascon_perm #(parameter UNROLL = 1) (
    input              clk,
    input              rst,
    input              start,
    input              p12,
    input      [319:0] d_in,
    output reg [319:0] st,
    output reg         run
);
    reg  [3:0] idx;                              // indeks round constant berikutnya
    wire [3:0] i0  = start ? (p12 ? 4'd0 : 4'd4) : idx;
    wire [4:0] nxt = {1'b0, i0} + UNROLL;

    wire [320*(UNROLL+1)-1:0] r;
    assign r[319:0] = start ? d_in : st;

    genvar j;
    generate
        for (j = 0; j < UNROLL; j = j + 1) begin : g
            wire [3:0] ci = i0 + j;
            ascon_round u (.s_in(r[320*j +: 320]), .rc({4'd15 - ci, ci}),
                           .s_out(r[320*(j+1) +: 320]));
        end
    endgenerate

    always @(posedge clk) begin
        if (rst) begin
            st  <= 320'd0;
            idx <= 4'd0;
            run <= 1'b0;
        end else if (start | run) begin
            st  <= r[320*UNROLL +: 320];
            idx <= nxt[3:0];
            run <= nxt < 5'd12;
        end
    end
endmodule
