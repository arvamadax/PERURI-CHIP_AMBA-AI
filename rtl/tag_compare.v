// Bandingkan dua tag 128-bit sekaligus.
module tag_compare (
    input  [127:0] a,
    input  [127:0] b,
    output         tag_ok
);
    assign tag_ok = (a == b);
endmodule
