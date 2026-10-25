# Architecture and interfaces

## System view

```text
Rectangle command                         Pixel readback
cmd_valid/ready, x/y, width/height/color  rd_addr/rd_data
             │                                  ▲
             ▼                                  │
       ┌─────────────┐   fb_we/fb_addr/data  ┌─────────────┐
       │ draw_engine │ ─────────────────────▶ │ framebuffer │
       └─────────────┘                        └─────────────┘
              └────────────── gpu_top ──────────────┘
```

`draw_engine` turns a command into a stream of pixel writes. `framebuffer` stores those writes and serves read requests. `gpu_top` connects the modules and exposes the command and read interfaces.

## Screen and pixel format

- Resolution: 64 columns × 64 rows.
- Address space: 4096 pixels, addressed from 0 through 4095.
- Pixel storage: 8-bit RGB332.
- Row-major address: `address = y * 64 + x`. The six-bit Y value forms the upper address bits, and six-bit X forms the lower bits.

RGB332 assigns bits `[7:5]` to red, `[4:2]` to green, and `[1:0]` to blue. The renderer scales the channel values to 8-bit RGB using `r * 255 // 7`, `g * 255 // 7`, and `b * 255 // 3`.

## `gpu_top` command interface

| Signal | Direction | Meaning |
| --- | --- | --- |
| `clk` | input | Shared rising-edge clock |
| `rst_n` | input | Active-low asynchronous reset for the draw engine |
| `cmd_valid` | input | Command is being offered |
| `cmd_ready` | output | Draw engine can accept a command |
| `cmd_x`, `cmd_y` | input | 6-bit starting coordinate, each 0–63 |
| `cmd_width`, `cmd_height` | input | 7-bit dimensions, each 0–64 for supported rectangle commands |
| `cmd_color` | input | RGB332 pixel value |
| `done` | output | One-cycle completion indication |
| `rd_addr` | input | Framebuffer address to read |
| `rd_data` | output | Registered pixel data from the framebuffer |

A command is accepted on a rising edge when `cmd_valid` and `cmd_ready` are both high. The engine asserts ready only in `IDLE`, captures the command parameters at that handshake, and ignores commands while drawing or reporting completion.

## Draw-engine behavior

The state machine uses `IDLE`, `DRAW`, and `DONE`:

- `IDLE` waits for a command. A zero width or height transitions directly to `DONE` without a pixel write.
- `DRAW` visits the rectangle in row-major order: X advances across a row, then resets while Y advances.
- Coordinates beyond 63 are clipped by suppressing `fb_we`; the offsets still advance so the command completes.
- The final logical pixel is presented to the framebuffer on the clock edge that transitions the engine to `DONE`.
- `DONE` asserts for one cycle, then the engine returns to `IDLE`.

The write channel consists of `fb_we`, `fb_addr`, and `fb_data`. The framebuffer accepts the pixel on a rising edge when `fb_we` is high.

## Framebuffer behavior and decisions

`framebuffer.sv` declares 4096 entries of 8 bits each. Writes are synchronous and occur only when `wr_en` is high. Reads are synchronous: `rd_data` is registered from `memory[rd_addr]` at the rising edge, so a read address must be held through that edge and the result is checked after the edge.

The memory has no reset. Locations are unspecified until written. Tests and image generation initialize any locations they inspect; the image tests fill the entire framebuffer first.

With the current nonblocking read and write assignments, RTL simulation returns the old stored value for a same-address read/write on one edge (read-first behavior). Confirm the selected FPGA memory primitive's collision mode before relying on this behavior in hardware, as implementation details can vary by target.

## Renderer

`test_gpu_top.py` reads addresses 0–4095 into a flat list in row-major order. `gpu_render.py` maps each RGB332 value to an RGB tuple, creates a 64×64 Pillow image, and scales it by 8× with nearest-neighbor interpolation, producing a 512×512 PNG. The text, checkerboard, and stripe patterns are sent through rectangle commands before readback; they are not drawn directly by Pillow.

