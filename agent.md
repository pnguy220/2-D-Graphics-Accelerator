#2D GPU — Codex Project Instructions

## Project Overview

Learning-oriented digital hardware project developed for Cal Hacks 13.0.

The project has two primary components:

1. A 2D graphics accelerator implemented in synthesizable SystemVerilog, intended for eventual FPGA deployment.
2. A reusable RTL verification framework using Python, cocotb, and an RTL simulator.

No physical FPGA is currently available. The GPU will initially be simulated, with its framebuffer output visualized using Python.

## Developer Background and Goals

The developer is an electrical engineering student with experience in:

- SystemVerilog RTL design, including synchronous FIFOs.
- cocotb verification and Python reference scoreboards using `deque`.
- Randomized verification and debugging.
- Basic digital design, FSMs, and sequential logic.
- Python and Linux/WSL development.

The primary goals are to strengthen RTL design and verification skills, learn agent-assisted development using Codex, and create a reusable verification framework.

## How Codex Should Assist

Act as an experienced RTL engineer, technical reviewer, and educational mentor.

- Prioritize understanding over implementation speed.
- Do not implement entire RTL modules unless explicitly requested.
- Help the developer reason about architecture, FSMs, datapaths, timing, and clock-cycle behavior.
- When reviewing RTL, explain why a change is necessary.
- Identify possible synthesis issues, off-by-one errors, width mismatches, latches, and race conditions.
- Prefer small, incremental changes.
- Ask before making substantial architectural changes.
- Help create testbenches and development tooling, but explain how they work.
- Clearly distinguish between verified results, assumptions, and suggestions.
- Never claim that a simulation passed unless it was actually executed.

## GPU Architecture

Initial specifications:

- Resolution: 64 × 64 pixels.
- Color depth: 8-bit RGB332.
- Framebuffer: 4096 entries, 8 bits each.
- Single clock domain.
- Active-low asynchronous reset for the drawing engine.
- One logical pixel processed per DRAW clock cycle.
- Initial drawing operation: DRAW_RECT.
- Future operations: DRAW_PIXEL and CLEAR_SCREEN.
- Out-of-bounds pixels are clipped.
- Zero-width and zero-height rectangles produce no framebuffer writes.
- Command interface uses valid/ready handshaking.

### DRAW_RECT Behavior

The drawing engine receives:

- Starting X/Y coordinates.
- Rectangle width and height.
- Pixel color.
- Command valid signal.

It outputs:

- Command ready.
- Framebuffer write enable.
- Framebuffer address.
- Framebuffer pixel data.
- Completion signal.

The drawing engine uses three FSM states:

- IDLE: Wait for a command, capture parameters on a valid/ready handshake, and initialize counters.
- DRAW: Generate pixel writes and advance the X/Y offset counters.
- DONE: Assert completion for one cycle and return to IDLE.

For a nonempty rectangle, the counters follow nested-loop behavior:

- Increment X after each logical pixel.
- When X reaches width - 1, reset X to zero and increment Y.
- When both X and Y reach their final offsets, transition to DONE at the next rising edge.
- The final pixel must be written at the same clock edge that transitions the FSM into DONE.
- Invalid coordinates suppress framebuffer writes but do not prevent counter advancement.

Coordinate calculations:

current_x = start_x + x_offset

current_y = start_y + y_offset

For valid coordinates:

fb_addr = current_y * 64 + current_x

Coordinate calculations must have sufficient width to prevent overflow before clipping.

The framebuffer uses synchronous writes.

## Current Implementation Status

The first functional version of the accelerator is implemented:

- `draw_engine.sv` accepts rectangle commands, advances X/Y offsets, clips out-of-bounds writes, and reports completion.
- `framebuffer.sv` stores 4096 8-bit pixels with synchronous write and read ports. Its memory is not reset.
- `gpu_top.sv` connects the drawing engine and framebuffer and exposes command and readback ports.
- Cocotb tests cover directed and seeded randomized drawing, framebuffer behavior, and top-level integration.
- `gpu_render.py` converts RGB332 pixels to RGB888 and saves scaled PNGs. Top-level tests render `CAL HACKS`, a checkerboard, and vertical stripes.

See `README.md`, `ARCHITECTURE.md`, and `VERIFICATION.md` for setup, interfaces, design decisions, and test commands.

Features such as `DRAW_PIXEL`, `CLEAR_SCREEN` as a command, a display controller, reusable test-runner infrastructure, and FPGA synthesis are future work.

## Reusable Verification Framework

The verification framework should eventually:

1. Load a project configuration.
2. Compile SystemVerilog using a supported simulator.
3. Execute cocotb tests.
4. Support project-specific Python reference models.
5. Collect pass/fail results and reproducible random seeds.
6. Track explicitly defined functional coverage scenarios.
7. Generate useful verification reports.
8. Optionally use an AI agent to analyze simulation failures.

The framework must be reusable for other RTL designs, such as FIFOs, UARTs, and arithmetic accelerators.

Keep deterministic simulation and correctness checking independent of the AI agent.

## Development Philosophy

Work incrementally:

1. Define behavior and interfaces.
2. Design the architecture.
3. Implement one RTL component.
4. Write directed tests.
5. Debug and validate.
6. Expand functionality.
7. Refactor reusable infrastructure.

The developer should remain the primary author of the core RTL.

For educational RTL work, provide explanations, hints, and code review before complete solutions unless explicitly asked otherwise.
