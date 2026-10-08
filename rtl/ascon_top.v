// Top: Avalon-MM slave -> ascon_ctrl -> ascon_perm. UNROLL = ronde per siklus (1, 2, atau 4).
module ascon_top #(parameter UNROLL = 1) (
    input         clk,
    input         rst,               // reset sinkron, aktif tinggi
    input  [5:0]  address,
    input         write,
    input  [31:0] writedata,
    input         read,
    output [31:0] readdata,
    output        irq
);
    wire         start, blk_valid, blk_ad, blk_last, blk_ready, out_valid, busy, done, tag_ok;
    wire         ps, pp, run;
    wire [1:0]   mode;
    wire [4:0]   blk_len;
    wire [127:0] key, nonce, tag_in, blk_data, out_data, tag_out;
    wire [255:0] digest;
    wire [319:0] pd, st;

    ascon_csr_avalon u_csr (.clk(clk), .rst(rst), .address(address), .write(write), .writedata(writedata),
        .read(read), .readdata(readdata), .irq(irq), .start(start), .mode(mode), .key(key), .nonce(nonce),
        .tag_in(tag_in), .blk_valid(blk_valid), .blk_ad(blk_ad), .blk_data(blk_data), .blk_len(blk_len),
        .blk_last(blk_last), .blk_ready(blk_ready), .out_data(out_data), .out_valid(out_valid),
        .tag_out(tag_out), .digest(digest), .busy(busy), .done(done), .tag_ok(tag_ok));

    ascon_ctrl u_ctrl (.clk(clk), .rst(rst), .start(start), .mode(mode), .key(key), .nonce(nonce),
        .tag_in(tag_in), .blk_valid(blk_valid), .blk_ad(blk_ad), .blk_data(blk_data), .blk_len(blk_len),
        .blk_last(blk_last), .blk_ready(blk_ready), .out_data(out_data), .out_valid(out_valid),
        .tag_out(tag_out), .digest(digest), .busy(busy), .done(done), .tag_ok(tag_ok),
        .perm_start(ps), .perm_p12(pp), .perm_d(pd), .st(st), .perm_run(run));

    ascon_perm #(.UNROLL(UNROLL)) u_perm (.clk(clk), .rst(rst), .start(ps), .p12(pp), .d_in(pd),
        .st(st), .run(run));
endmodule
