// FSM Ascon-AEAD128 (enc/dec) dan Ascon-Hash256. Blok masuk lewat handshake blk_valid/blk_ready.
// Aturan host: blok AD (blk_ad=1) opsional, blok terakhir tiap jenis diberi blk_last=1;
// blok data/pesan terakhir wajib ada (boleh len=0). blk_last dengan len penuh -> ctrl
// menyisipkan blok pad kosong sendiri. mode: 0 enc, 1 dec, 2 hash. Blok hash <= 8 byte.
// Byte ke-i blok = bit [8i+7:8i]; word state little-endian (SP 800-232).
module ascon_ctrl (
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
    output reg [127:0] out_data,     // keluaran blok data terakhir yang diterima (len byte valid)
    output reg         out_valid,
    output reg [127:0] tag_out,
    output reg [255:0] digest,
    output             busy,
    output reg         done,
    output reg         tag_ok,       // hanya bermakna untuk dekripsi
    output             perm_start,
    output             perm_p12,
    output     [319:0] perm_d,
    input      [319:0] st,
    input              perm_run
);
    localparam S_IDLE = 3'd0, S_INIT = 3'd1, S_WAIT = 3'd2, S_RUN = 3'd3, S_SQ = 3'd4;
    localparam [63:0] AEAD_IV = 64'h00001000808c0001, HASH_IV = 64'h0000080100cc0002;

    reg [2:0] state;
    reg [1:0] md, sq;
    reg       kx_pend, ds_pend, synth, syn_ad, fin_op;

    wire hash = (md == 2'd2);
    wire dec  = (md == 2'd1);

    // blok yang sedang diproses: blok host, atau blok pad kosong sisipan
    wire         cur_ad   = synth ? syn_ad : blk_ad;
    wire [4:0]   cur_len  = synth ? 5'd0 : blk_len;
    wire [127:0] cur_data = synth ? 128'd0 : blk_data;
    wire         full     = (cur_len == (hash ? 5'd8 : 5'd16));
    wire         cur_last = synth | blk_last | ~full;
    wire         defer    = cur_last & full;
    wire         term     = cur_last & ~full;
    wire         fin_now  = term & ~cur_ad & ~hash;
    wire         issue    = (state == S_WAIT) & (synth | blk_valid);

    wire [319:0] kx = {192'd0, key[63:0], key[127:64]};            // s3^=K0, s4^=K1
    wire [319:0] fx = {128'd0, key[63:0], key[127:64], 64'd0};     // s2^=K0, s3^=K1
    wire [319:0] ds = {256'd0, 1'b1, 63'd0};                       // s4 ^= 0x80<<56
    wire [319:0] base = st ^ (kx_pend ? kx : 320'd0) ^ ((ds_pend & ~cur_ad & ~hash) ? ds : 320'd0);

    wire [127:0] x   = {base[255:192], base[319:256]};             // {s1,s0}
    wire [127:0] sh  = 128'd1 << {cur_len, 3'b000};
    wire [127:0] msk = sh - 128'd1;
    wire [127:0] pad = full ? 128'd0 : sh;
    wire [127:0] m   = cur_data & msk;
    wire [127:0] xn  = ((dec & ~cur_ad) ? ((x & ~msk) | m) : (x ^ m)) ^ pad;
    wire [319:0] dn  = {xn[63:0], xn[127:64], base[191:0]};
    wire [319:0] d_blk = fin_now ? (dn ^ fx) : dn;

    wire [319:0] d_init = (mode == 2'd2) ? {HASH_IV, 256'd0}
                                         : {AEAD_IV, key[63:0], key[127:64], nonce[63:0], nonce[127:64]};

    wire [127:0] tag_calc = {st[63:0] ^ key[127:64], st[127:64] ^ key[63:0]};
    wire         cmp_ok;
    tag_compare u_tc (.a(tag_calc), .b(tag_in), .tag_ok(cmp_ok));

    assign perm_start = ((state == S_IDLE) & start) | issue
                      | ((state == S_RUN) & ~perm_run & fin_op & hash)
                      | ((state == S_SQ) & ~perm_run & (sq != 2'd3));
    assign perm_d   = (state == S_IDLE) ? d_init : (state == S_WAIT) ? d_blk : st;
    assign perm_p12 = (state != S_WAIT) | hash | fin_now;
    assign blk_ready = (state == S_WAIT) & ~synth;
    assign busy      = (state != S_IDLE);

    always @(posedge clk) begin
        if (rst) begin
            state <= S_IDLE; md <= 2'd0; sq <= 2'd0;
            kx_pend <= 1'b0; ds_pend <= 1'b0; synth <= 1'b0; syn_ad <= 1'b0; fin_op <= 1'b0;
            out_data <= 128'd0; out_valid <= 1'b0; tag_out <= 128'd0; digest <= 256'd0;
            done <= 1'b0; tag_ok <= 1'b0;
        end else case (state)
            S_IDLE: if (start) begin
                md <= mode; done <= 1'b0; tag_ok <= 1'b0; out_valid <= 1'b0;
                synth <= 1'b0; kx_pend <= 1'b0; ds_pend <= (mode != 2'd2); fin_op <= 1'b0;
                state <= S_INIT;
            end
            S_INIT: if (~perm_run) begin
                kx_pend <= ~hash;
                state <= S_WAIT;
            end
            S_WAIT: if (issue) begin
                kx_pend <= 1'b0;
                if (~cur_ad) ds_pend <= 1'b0;
                fin_op <= term & ~cur_ad;
                if (synth) synth <= 1'b0;
                else begin
                    if (defer) begin synth <= 1'b1; syn_ad <= blk_ad; end
                    if (~blk_ad & ~hash) begin out_data <= (x & msk) ^ m; out_valid <= 1'b1; end
                end
                state <= S_RUN;
            end
            S_RUN: if (~perm_run) begin
                if (~fin_op) state <= S_WAIT;
                else if (hash) begin
                    digest[63:0] <= st[319:256];
                    sq <= 2'd1;
                    state <= S_SQ;
                end else begin
                    tag_out <= tag_calc; tag_ok <= dec & cmp_ok; done <= 1'b1;
                    state <= S_IDLE;
                end
            end
            S_SQ: if (~perm_run) begin
                digest[{sq, 6'b000000} +: 64] <= st[319:256];
                if (sq == 2'd3) begin done <= 1'b1; state <= S_IDLE; end
                else sq <= sq + 2'd1;
            end
            default: state <= S_IDLE;
        endcase
    end
endmodule
