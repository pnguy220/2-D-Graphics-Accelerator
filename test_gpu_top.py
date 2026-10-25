"""End-to-end Cocotb test for drawing into and reading from the framebuffer."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer
from gpu_render import save_framebuffer

FONT_5X7 = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def text_as_rectangle_runs(text, x, y, color):
    """Convert 5x7 glyphs to horizontal one-row rectangle commands."""
    rectangles = []
    for char_index, character in enumerate(text):
        glyph_x = x + char_index * 6  # five glyph columns and one spacing column
        for row_index, row_bits in enumerate(FONT_5X7[character]):
            column = 0
            while column < 5:
                if row_bits[column] == "0":
                    column += 1
                    continue

                run_start = column
                while column < 5 and row_bits[column] == "1":
                    column += 1
                rectangles.append(
                    (glyph_x + run_start, y + row_index, column - run_start, 1, color)
                )

    return rectangles


async def reset_dut(dut):
    """Initialize the top-level inputs and reset the drawing engine."""
    dut.rst_n.value = 0
    dut.cmd_valid.value = 0
    dut.cmd_x.value = 0
    dut.cmd_y.value = 0
    dut.cmd_width.value = 0
    dut.cmd_height.value = 0
    dut.cmd_color.value = 0
    dut.rd_addr.value = 0

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1


async def draw_rectangle(dut, x, y, width, height, color):
    """Handshake one rectangle command and wait for its done pulse."""
    for _ in range(10):
        await FallingEdge(dut.clk)
        if int(dut.cmd_ready.value):
            break
    else:
        assert False, "draw engine did not become ready"

    dut.cmd_x.value = x
    dut.cmd_y.value = y
    dut.cmd_width.value = width
    dut.cmd_height.value = height
    dut.cmd_color.value = color
    dut.cmd_valid.value = 1

    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.cmd_valid.value = 0

    for _ in range(5000):
        if int(dut.done.value):
            return
        await FallingEdge(dut.clk)
    assert False, "draw command did not complete within 5000 cycles"


async def read_framebuffer(dut):
    """Read addresses 0..4095 and return their values in row-major order."""
    pixels = []
    for address in range(4096):
        dut.rd_addr.value = address
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")  # allow the synchronous read register to update
        pixels.append(int(dut.rd_data.value))
    return pixels


@cocotb.test()
async def draws_rectangle_and_reads_pixels_back(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    await draw_rectangle(dut, x=5, y=10, width=3, height=2, color=0xE0)

    # Row-major addresses for x=5..7 on rows y=10 and y=11.
    expected_addresses = [645, 646, 647, 709, 710, 711]
    for address in expected_addresses:
        dut.rd_addr.value = address
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")  # synchronous read data updates after this edge
        assert int(dut.rd_data.value) == 0xE0, (
            f"framebuffer address {address}: expected 0xE0, "
            f"got 0x{int(dut.rd_data.value):02X}"
        )


@cocotb.test()
async def reads_initialized_full_framebuffer(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    # Initialize all locations before checking the complete image.
    background = 0x00
    await draw_rectangle(dut, x=0, y=0, width=64, height=64, color=background)

    # Center "CAL HACKS" in the 64x64 framebuffer using 5x7 glyphs.
    text = "CAL HACKS"
    text_width = len(text) * 6 - 1
    text_x = (64 - text_width) // 2
    text_y = (64 - 7) // 2
    text_color = 0xFF  # white in RGB332
    scene = text_as_rectangle_runs(text, text_x, text_y, text_color)

    # Send each horizontal lit-pixel run through the drawing engine.
    for x, y, width, height, color in scene:
        await draw_rectangle(dut, x, y, width, height, color)

    # Model the expected row-major image in software.
    expected = [background] * 4096
    for x, y, width, height, color in scene:
        for row_offset in range(height):
            for col_offset in range(width):
                address = (y + row_offset) * 64 + (x + col_offset)
                expected[address] = color

    pixels = await read_framebuffer(dut)
    assert len(pixels) == 4096
    for address, (actual, expected_value) in enumerate(zip(pixels, expected)):
        assert actual == expected_value, (
            f"Pixel ({address % 64}, {address // 64}) at address {address}: "
            f"expected 0x{expected_value:02X}, got 0x{actual:02X}"
        )

    # Save the simulated framebuffer as an 8x nearest-neighbor PNG.
    output_path = save_framebuffer(pixels, "gpu_output.png")
    dut._log.info("Saved rendered framebuffer to %s", output_path)


@cocotb.test()
async def renders_checkerboard_framebuffer(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    # Initialize the full image so no checkerboard squares contain unknown data.
    background = 0x00
    await draw_rectangle(dut, x=0, y=0, width=64, height=64, color=background)

    # Draw an 8x8 grid of 8-pixel tiles, alternating white and black.
    tile_size = 8
    light_color = 0xFF
    expected = [background] * 4096
    for tile_y in range(8):
        for tile_x in range(8):
            if (tile_x + tile_y) % 2 == 0:
                x = tile_x * tile_size
                y = tile_y * tile_size
                await draw_rectangle(
                    dut, x=x, y=y, width=tile_size, height=tile_size,
                    color=light_color
                )
                for row in range(y, y + tile_size):
                    for column in range(x, x + tile_size):
                        expected[row * 64 + column] = light_color

    pixels = await read_framebuffer(dut)
    for address, (actual, expected_value) in enumerate(zip(pixels, expected)):
        assert actual == expected_value, (
            f"Pixel ({address % 64}, {address // 64}) at address {address}: "
            f"expected 0x{expected_value:02X}, got 0x{actual:02X}"
        )

    output_path = save_framebuffer(pixels, "checkerboard.png")
    dut._log.info("Saved checkerboard image to %s", output_path)


@cocotb.test()
async def renders_alternating_vertical_stripes(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    # Initialize the full image to black before drawing the light columns.
    background = 0x00
    await draw_rectangle(dut, x=0, y=0, width=64, height=64, color=background)

    # Each stripe is exactly one framebuffer column wide and spans all 64 rows.
    stripe_color = 0xFF
    expected = [background] * 4096
    for column in range(0, 64, 2):
        await draw_rectangle(
            dut, x=column, y=0, width=1, height=64, color=stripe_color
        )
        for row in range(64):
            expected[row * 64 + column] = stripe_color

    pixels = await read_framebuffer(dut)
    for address, (actual, expected_value) in enumerate(zip(pixels, expected)):
        assert actual == expected_value, (
            f"Pixel ({address % 64}, {address // 64}) at address {address}: "
            f"expected 0x{expected_value:02X}, got 0x{actual:02X}"
        )

    output_path = save_framebuffer(pixels, "vertical_stripes.png")
    dut._log.info("Saved vertical-stripe image to %s", output_path)
