# Verification guide

The design uses Cocotb with Icarus Verilog. Tests are separated by DUT: `draw_engine`, `framebuffer`, and integrated `gpu_top`.

## Running the suites

Activate the project virtual environment before running Make:

```bash
source .venv/bin/activate
```

From the project root:

```bash
# Draw-engine directed and randomized tests
make SIM=icarus

# Framebuffer tests
make SIM=icarus TOPLEVEL=framebuffer MODULE=test_framebuffer VERILOG_SOURCES=framebuffer.sv

# GPU integration tests; also creates the PNG outputs
make SIM=icarus TOPLEVEL=gpu_top MODULE=test_gpu_top VERILOG_SOURCES="gpu_top.sv draw_engine.sv framebuffer.sv"
```

Build outputs and generated images are written relative to the current working directory. Run from the project root to keep them there.

## Draw-engine tests

`test_draw_engine.py` checks:

- A 1×1 rectangle and a 3×2 rectangle's ordered writes and colors.
- Zero-width and zero-height commands produce no writes.
- Maximum dimensions (64×1, 1×64, and 64×64), including all 4096 framebuffer addresses.
- Clipping at the lower-right edge and at X and Y independently.
- A pending command is not accepted while the engine is drawing; changing unaccepted command inputs does not change the active draw.
- Asynchronous reset stops a draw and returns the engine to its ready state.
- 32 reproducible randomized rectangles, compared against a Python clipping/address reference model. The seed is reported on failure.

## Framebuffer tests

`test_framebuffer.py` checks the address-100 write/read example, synchronous read timing, disabled writes, addresses 0 and 4095, simultaneous operations at different addresses, same-address read/write behavior, and a write/read sweep across all 4096 locations.

The same-address test expects the old value at the collision edge and the newly written value on the next read edge.

## Integration tests and image outputs

`test_gpu_top.py` covers:

- A 3×2 rectangle command followed by readback of its six written pixels.
- Full-frame initialization followed by the centered `CAL HACKS` scene and a full readback/reference comparison.
- An 8×8 checkerboard made from 8×8-pixel tiles.
- 64 alternating vertical stripes, each one framebuffer column wide.

Each image test initializes the full framebuffer before reading it. The resulting 512×512 RGB images are `calhacks.png`, `checkerboard.png`, and `vertical_stripes.png`.

## Interpreting results

The top-level framebuffer read has one registered read step: set `rd_addr`, wait for the rising edge, then inspect `rd_data` after the edge. A failure in a full-image comparison reports the first mismatched pixel's `(x, y)`, address, expected value, and actual value.

The Cocotb Makefile integration currently uses the legacy `MODULE` variable. Cocotb 2.x emits a deprecation warning for it, but it is still accepted. Icarus may also print a constant-select notice for the draw engine's `always_comb` process; treat these as tool notices unless compilation or a test reports an actual failure.

