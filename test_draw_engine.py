"""Directed and randomized cocotb tests for draw_engine rectangles."""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer


async def reset_dut(dut):
    # Hold reset active while the clock runs, then release it before testing.
    dut.rst_n.value = 0
    dut.cmd_valid.value = 0
    dut.cmd_x.value = 0
    dut.cmd_y.value = 0
    dut.cmd_width.value = 0
    dut.cmd_height.value = 0
    dut.cmd_color.value = 0

    await FallingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def issue_and_collect(dut, x, y, width, height, color):
    """Send one command and collect each framebuffer write until done."""
    await FallingEdge(dut.clk)
    assert int(dut.cmd_ready.value) == 1, "engine should be ready in IDLE"

    # Present a stable command; valid and ready together form the handshake.
    dut.cmd_x.value = x
    dut.cmd_y.value = y
    dut.cmd_width.value = width
    dut.cmd_height.value = height
    dut.cmd_color.value = color
    dut.cmd_valid.value = 1

    await RisingEdge(dut.clk)  # command is accepted on this edge
    await FallingEdge(dut.clk)
    dut.cmd_valid.value = 0

    # Record each enabled write once per cycle, stopping at the done pulse.
    writes = []
    for _ in range(5000):
        # Sample during the cycle, before the framebuffer's active clock edge.
        if int(dut.fb_we.value):
            writes.append((int(dut.fb_addr.value), int(dut.fb_data.value)))

        if int(dut.done.value):
            return writes

        await FallingEdge(dut.clk)

    assert False, "engine did not assert done within 5000 cycles"


async def start_test(dut):
    # Each test gets a fresh clock and a reset DUT.
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)


@cocotb.test()
async def draws_one_pixel(dut):
    await start_test(dut)

    # A 1x1 rectangle should generate exactly one write at y*64+x.
    writes = await issue_and_collect(dut, x=5, y=7, width=1, height=1, color=0xA6)

    assert writes == [(7 * 64 + 5, 0xA6)]


@cocotb.test()
async def draws_multi_row_rectangle_in_row_major_order(dut):
    await start_test(dut)

    # Check that X traverses each row before Y advances to the next row.
    writes = await issue_and_collect(dut, x=10, y=20, width=3, height=2, color=0x5C)

    # Expected addresses cover 3 pixels in row 20, then 3 in row 21.
    expected = [
        (20 * 64 + 10, 0x5C),
        (20 * 64 + 11, 0x5C),
        (20 * 64 + 12, 0x5C),
        (21 * 64 + 10, 0x5C),
        (21 * 64 + 11, 0x5C),
        (21 * 64 + 12, 0x5C),
    ]
    assert writes == expected


@cocotb.test()
async def empty_rectangles_complete_without_writes(dut):
    await start_test(dut)

    # Exercise zero width, zero height, and both dimensions zero.
    for width, height in ((0, 4), (4, 0), (0, 0)):
        writes = await issue_and_collect(
            dut, x=12, y=9, width=width, height=height, color=0xFF
        )
        assert writes == [], f"empty {width}x{height} rectangle wrote pixels"


@cocotb.test()
async def clips_at_lower_right_screen_edge(dut):
    await start_test(dut)

    # The 3x3 rectangle extends beyond both edges; only its 2x2 corner fits.
    writes = await issue_and_collect(dut, x=62, y=62, width=3, height=3, color=0x3B)

    # These are the four in-bounds pixels at coordinates 62..63 on each axis.
    expected = [
        (62 * 64 + 62, 0x3B),
        (62 * 64 + 63, 0x3B),
        (63 * 64 + 62, 0x3B),
        (63 * 64 + 63, 0x3B),
    ]
    assert writes == expected


@cocotb.test()
async def draws_maximum_width_and_height(dut):
    await start_test(dut)

    # Exercise each maximum dimension and the full 64x64 framebuffer.
    cases = (
        (64, 1, list(range(64))),
        (1, 64, [row * 64 for row in range(64)]),
        (64, 64, list(range(4096))),
    )
    for width, height, expected_addresses in cases:
        writes = await issue_and_collect(
            dut, x=0, y=0, width=width, height=height, color=0xC7
        )
        assert [addr for addr, _ in writes] == expected_addresses
        assert all(data == 0xC7 for _, data in writes)
        assert len(writes) == width * height


@cocotb.test()
async def clips_x_and_y_edges_independently(dut):
    await start_test(dut)

    # Only X extends past the screen; the two in-bounds pixels should write.
    x_edge_writes = await issue_and_collect(
        dut, x=62, y=10, width=4, height=1, color=0x71
    )
    assert x_edge_writes == [
        (10 * 64 + 62, 0x71),
        (10 * 64 + 63, 0x71),
    ]

    # Only Y extends past the screen; the two in-bounds pixels should write.
    y_edge_writes = await issue_and_collect(
        dut, x=10, y=62, width=1, height=4, color=0x72
    )
    assert y_edge_writes == [
        (62 * 64 + 10, 0x72),
        (63 * 64 + 10, 0x72),
    ]


@cocotb.test()
async def command_waits_until_engine_is_ready(dut):
    await start_test(dut)

    # Launch a multi-cycle draw command.
    await FallingEdge(dut.clk)
    dut.cmd_x.value = 0
    dut.cmd_y.value = 0
    dut.cmd_width.value = 3
    dut.cmd_height.value = 1
    dut.cmd_color.value = 0x11
    dut.cmd_valid.value = 1
    await RisingEdge(dut.clk)

    # Present another command during DRAW. It must remain pending until IDLE.
    await FallingEdge(dut.clk)
    dut.cmd_x.value = 5
    dut.cmd_y.value = 5
    dut.cmd_width.value = 1
    dut.cmd_height.value = 1
    dut.cmd_color.value = 0x22
    assert int(dut.cmd_ready.value) == 0

    first_writes = []
    for cycle in range(10):
        if cycle == 1:
            # Change the still-unaccepted command again while ready remains low.
            dut.cmd_x.value = 7
            dut.cmd_y.value = 8
            dut.cmd_color.value = 0x33
            assert int(dut.cmd_ready.value) == 0

        if int(dut.fb_we.value):
            first_writes.append((int(dut.fb_addr.value), int(dut.fb_data.value)))
        if int(dut.done.value):
            break
        await FallingEdge(dut.clk)
    else:
        assert False, "first command did not complete"

    assert first_writes == [
        (0, 0x11),
        (1, 0x11),
        (2, 0x11),
    ]
    assert int(dut.cmd_ready.value) == 0  # still in DONE

    # Restore the intended command once ready returns; it is accepted at the edge.
    await FallingEdge(dut.clk)
    dut.cmd_x.value = 5
    dut.cmd_y.value = 5
    dut.cmd_width.value = 1
    dut.cmd_height.value = 1
    dut.cmd_color.value = 0x22
    assert int(dut.cmd_ready.value) == 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.cmd_valid.value = 0

    second_writes = []
    for _ in range(10):
        if int(dut.fb_we.value):
            second_writes.append((int(dut.fb_addr.value), int(dut.fb_data.value)))
        if int(dut.done.value):
            break
        await FallingEdge(dut.clk)

    assert second_writes == [(5 * 64 + 5, 0x22)]
    assert int(dut.done.value) == 1


@cocotb.test()
async def reset_aborts_draw_and_returns_engine_to_idle(dut):
    await start_test(dut)

    # Start a long draw so reset can interrupt it before normal completion.
    await FallingEdge(dut.clk)
    dut.cmd_x.value = 0
    dut.cmd_y.value = 0
    dut.cmd_width.value = 64
    dut.cmd_height.value = 64
    dut.cmd_color.value = 0xE3
    dut.cmd_valid.value = 1
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.cmd_valid.value = 0
    assert int(dut.fb_we.value) == 1

    # Active-low asynchronous reset should stop writes and restore IDLE promptly.
    dut.rst_n.value = 0
    await Timer(1, unit="ns")
    assert int(dut.fb_we.value) == 0
    assert int(dut.done.value) == 0
    assert int(dut.cmd_ready.value) == 1

    await RisingEdge(dut.clk)
    dut.rst_n.value = 1

    # Confirm the reset engine can accept and complete a fresh command.
    writes = await issue_and_collect(
        dut, x=3, y=4, width=1, height=1, color=0x4D
    )
    assert writes == [(4 * 64 + 3, 0x4D)]


@cocotb.test()
async def randomized_rectangles_match_reference_model(dut):
    await start_test(dut)

    # Fixed seed makes any failure repeatable from run to run.
    seed = 0x2D5350
    rng = random.Random(seed)

    for case_index in range(32):
        x = rng.randrange(64)
        y = rng.randrange(64)
        width = rng.randrange(65)
        height = rng.randrange(65)
        color = rng.randrange(256)

        # Build expected writes in row-major order, omitting clipped pixels.
        expected = [
            ((y + dy) * 64 + (x + dx), color)
            for dy in range(height)
            for dx in range(width)
            if (x + dx) < 64 and (y + dy) < 64
        ]

        actual = await issue_and_collect(
            dut, x=x, y=y, width=width, height=height, color=color
        )
        assert actual == expected, (
            f"seed={seed:#x}, case={case_index}: "
            f"command=({x=}, {y=}, {width=}, {height=}, {color=:#04x})"
        )
