// Avalon-MM slave 32-bit (alamat word, tanpa waitrequest, read latency tetap 1 siklus).
// Peta register (alamat word); data 128-bit/256-bit = beberapa word, word 0 = bit [31:0], little-endian:
//   0x00 CTRL    W: [0] START (pulsa), [2:1] MODE (0 enc, 1 dec, 2 hash), [3] IRQ_EN.  R: {IRQ_EN, MODE, 0}
//   0x01 BLK     W: [4:0] LEN, [8] LAST, [9] AD; menulis = push blok dari DIN
//   0x02 STATUS  R: [0] BUSY, [1] READY (boleh push), [2] DONE, [3] TAG_OK (dekripsi), [4] OUT_VALID
//   0x04-0x07 KEY (W)   0x08-0x0B NONCE (W)   0x0C-0x0F DIN (W)   0x10-0x13 TAG_IN (W)
//   0x14-0x17 DOUT (R)  0x18-0x1B TAG_OUT (R) 0x1C-0x23 DIGEST (R)
// irq = IRQ_EN & DONE. Register W-only terbaca 0 (key tidak bocor lewat bus).
module ascon_csr_avalon (
    input              clk,
    input              rst,
    input      [5:0]   address,
    input              write,
    input      [31:0]  writedata,
    input              read,
    output reg [31:0]  readdata,
    output             irq,
    // ke ascon_ctrl
    output reg         start,
    output reg [1:0]   mode,
    output reg [127:0] key,
    output reg [127:0] nonce,
    output reg [127:0] tag_in,
    output reg         blk_valid,
    output reg         blk_ad,
    output reg [127:0] blk_data,
    output reg [4:0]   blk_len,
    output reg         blk_last,
    input              blk_ready,
    input      [127:0] out_data,
    input              out_valid,
    input      [127:0] tag_out,
    input      [255:0] digest,
    input              busy,
    input              done,
    input              tag_ok
);
    reg irq_en;

    // start tertunda 1 siklus: sembunyikan done lama dan tampilkan busy supaya poll tidak balapan
    wire st_busy  = busy | start;
    wire st_done  = done & ~start;
    wire st_ready = blk_ready & ~blk_valid;
    assign irq = irq_en & st_done;

    always @(posedge clk) begin
        if (rst) begin
            start <= 1'b0; mode <= 2'd0; irq_en <= 1'b0;
            key <= 128'd0; nonce <= 128'd0; tag_in <= 128'd0; blk_data <= 128'd0;
            blk_valid <= 1'b0; blk_ad <= 1'b0; blk_len <= 5'd0; blk_last <= 1'b0;
        end else begin
            start <= 1'b0;
            if (blk_valid & blk_ready) blk_valid <= 1'b0;
            if (write) begin
                case (address)
                    6'h00: begin start <= writedata[0]; mode <= writedata[2:1]; irq_en <= writedata[3]; end
                    6'h01: begin blk_len <= writedata[4:0]; blk_last <= writedata[8]; blk_ad <= writedata[9];
                                 blk_valid <= 1'b1; end
                    6'h04, 6'h05, 6'h06, 6'h07: key[{address[1:0], 5'b0} +: 32]      <= writedata;
                    6'h08, 6'h09, 6'h0a, 6'h0b: nonce[{address[1:0], 5'b0} +: 32]    <= writedata;
                    6'h0c, 6'h0d, 6'h0e, 6'h0f: blk_data[{address[1:0], 5'b0} +: 32] <= writedata;
                    6'h10, 6'h11, 6'h12, 6'h13: tag_in[{address[1:0], 5'b0} +: 32]   <= writedata;
                    default: ;
                endcase
            end
        end
    end

    always @(posedge clk) begin
        if (read) begin
            case (address)
                6'h00: readdata <= {28'd0, irq_en, mode, 1'b0};
                6'h02: readdata <= {27'd0, out_valid, tag_ok, st_done, st_ready, st_busy};
                6'h14, 6'h15, 6'h16, 6'h17: readdata <= out_data[{address[1:0], 5'b0} +: 32];
                6'h18, 6'h19, 6'h1a, 6'h1b: readdata <= tag_out[{address[1:0], 5'b0} +: 32];
                6'h1c, 6'h1d, 6'h1e, 6'h1f, 6'h20, 6'h21, 6'h22, 6'h23:
                    readdata <= digest[{address[2:0] + 3'd4, 5'b0} +: 32];   // 0x1c -> word 0
                default: readdata <= 32'd0;
            endcase
        end
    end
endmodule
