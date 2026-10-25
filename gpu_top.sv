// Top-level integration of the rectangle drawing engine and framebuffer.
module gpu_top(
    // Command inputs are accepted when cmd_valid and cmd_ready are both high.
    input  logic        cmd_valid,
    output logic        cmd_ready,

    // Rectangle origin, dimensions, and RGB332 pixel color.
    input  logic [5:0]  cmd_x,
    input  logic [5:0]  cmd_y,
    input  logic [6:0]  cmd_width,
    input  logic [6:0]  cmd_height,
    input  logic [7:0]  cmd_color,

    // Synchronous framebuffer read port for inspection or display logic.
    input  logic [11:0] rd_addr,
    output logic [7:0]  rd_data,

    input  logic clk,
    input  logic rst_n,
    output logic done
);

    // Internal write channel connecting the draw engine to framebuffer memory.
    logic        fb_we;
    logic [11:0] fb_addr;
    logic [7:0]  fb_data;

    // Converts each accepted rectangle command into framebuffer pixel writes.
    draw_engine u_draw_engine (
    .clk       (clk),
    .rst_n     (rst_n),

    .cmd_valid (cmd_valid),
    .cmd_ready (cmd_ready),

    .cmd_x     (cmd_x),
    .cmd_y     (cmd_y),
    .cmd_width (cmd_width),
    .cmd_height(cmd_height),
    .cmd_color (cmd_color),

    .fb_we     (fb_we),
    .fb_addr   (fb_addr),
    .fb_data   (fb_data),

    .done      (done));

    // Stores written pixels and provides synchronous readback through rd_addr.
    framebuffer u_framebuffer(
    .clk(clk),
    .wr_en(fb_we),
    .wr_addr(fb_addr),
    .wr_data(fb_data),
    .rd_addr(rd_addr),
    .rd_data(rd_data));
endmodule
