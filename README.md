# 2D Graphics Accelerator

This project is a learning-oriented 2D graphics accelerator written in SystemVerilog. Its first version accepts rectangle commands, writes RGB332 pixels to a 64×64 framebuffer, and can render simulated framebuffer contents to PNG files.

## Features

- `draw_engine` accepts rectangle commands through a valid/ready interface, clips writes at the screen edges, and reports completion.
- `framebuffer` stores 4096 8-bit pixels and provides synchronous readback.
- `gpu_top` connects the drawing engine to the framebuffer.
- Cocotb tests cover the modules individually and as an integrated design.
- `gpu_render.py` converts RGB332 framebuffer data to RGB888 and saves scaled PNGs.

The current drawing operation is `DRAW_RECT`. See [ARCHITECTURE.md](ARCHITECTURE.md) for interfaces, cycle behavior, and design decisions. See [VERIFICATION.md](VERIFICATION.md) for test coverage and commands.

## Requirements and setup

The project uses Python, Cocotb, Pillow, and Icarus Verilog. From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install cocotb Pillow
```

Install Icarus Verilog using your operating system's package manager if it is not already available. Confirm that `iverilog` is on `PATH` and that the virtual environment is active before running Make; the Makefile uses `cocotb-config` from the active environment.

## Run tests

From the project root, activate `.venv` and choose the test target:

```bash
# Draw-engine unit tests (the Makefile default)
make SIM=icarus

# Framebuffer unit tests
make SIM=icarus TOPLEVEL=framebuffer MODULE=test_framebuffer VERILOG_SOURCES=framebuffer.sv

# Top-level integration tests and PNG generation
make SIM=icarus TOPLEVEL=gpu_top MODULE=test_gpu_top VERILOG_SOURCES="gpu_top.sv draw_engine.sv framebuffer.sv"
```

The top-level tests generate `calhacks.png`, `checkerboard.png`, and `vertical_stripes.png` in the current working directory. `calhacks.png` contains the `CAL HACKS` scene. The Makefile currently uses Cocotb's legacy `MODULE` variable; Cocotb 2.x may print a deprecation warning, but the tests still run.

## Project files

| File | Purpose |
| --- | --- |
| `draw_engine.sv` | Rectangle command FSM, counters, clipping, and pixel-write generation |
| `framebuffer.sv` | 4096×8-bit pixel memory with a synchronous read port |
| `gpu_top.sv` | Connects the draw engine and framebuffer and exposes command/read ports |
| `test_draw_engine.py` | Directed and seeded randomized draw-engine tests |
| `test_framebuffer.py` | Framebuffer write/read and memory behavior tests |
| `test_gpu_top.py` | Integration tests, scene creation, readback, and PNG generation |
| `gpu_render.py` | RGB332-to-RGB888 conversion and PNG output |
| `agent.md` | Project-specific development and architecture notes |

