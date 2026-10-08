// Testbench wrapper: ascon_ctrl + ascon_perm tanpa CSR (antarmuka tingkat blok).
module tb_ctrl #(parameter UNROLL = 1) (
    input              clk,
    input              rst,
    input              start,
    input      [1:0]   mode,
    input      [127:0] key,
    input      [127:0] nonce,
    input      [127:0] tag_in,
    input              blk_valid,
    input              blk_ad,
    input      [127:0] blk_data,
    input      [4:0]   blk_len,
    input              blk_last,
    output             blk_ready,
    output     [127:0] out_data,
    output             out_valid,
    output     [127:0] tag_out,
    output     [255:0] digest,
    output             busy,
    output             done,
    output             tag_ok
);
    wire         ps, pp, run;
    wire [319:0] pd, st;
    ascon_ctrl u_ctrl (.clk(clk), .rst(rst), .start(start), .mode(mode), .key(key), .nonce(nonce),
        .tag_in(tag_in), .blk_valid(blk_valid), .blk_ad(blk_ad), .blk_data(blk_data),
        .blk_len(blk_len), .blk_last(blk_last), .blk_ready(blk_ready), .out_data(out_data),
        .out_valid(out_valid), .tag_out(tag_out), .digest(digest), .busy(busy), .done(done),
        .tag_ok(tag_ok), .perm_start(ps), .perm_p12(pp), .perm_d(pd), .st(st), .perm_run(run));
    ascon_perm #(.UNROLL(UNROLL)) u_perm (.clk(clk), .rst(rst), .start(ps), .p12(pp), .d_in(pd),
        .st(st), .run(run));
endmodule
