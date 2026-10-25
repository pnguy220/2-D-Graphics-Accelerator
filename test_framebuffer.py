"""Directed Cocotb tests for the synchronous framebuffer."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer


async def start_test(dut):
    """Start a fresh clock and drive inactive values on all inputs."""
    dut.wr_en.value = 0
    dut.wr_addr.value = 0
    dut.wr_data.value = 0
    dut.rd_addr.value = 0
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await FallingEdge(dut.clk)


async def clock_edge(dut):
    """Wait for a rising edge and allow registered outputs to update."""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


@cocotb.test()
async def write_address_100_then_read_back(dut):
    await start_test(dut)

    # First edge stores E0; the following read edge returns the stored value.
    dut.wr_en.value = 1
    dut.wr_addr.value = 100
    dut.wr_data.value = 0xE0
    dut.rd_addr.value = 100
    await clock_edge(dut)

    dut.wr_en.value = 0
    await clock_edge(dut)
    assert int(dut.rd_data.value) == 0xE0


@cocotb.test()
async def read_data_changes_only_after_a_clock_edge(dut):
    await start_test(dut)

    # Initialize two known locations before checking read timing.
    dut.wr_en.value = 1
    dut.wr_addr.value = 100
    dut.wr_data.value = 0xE0
    await clock_edge(dut)
    dut.wr_addr.value = 101
    dut.wr_data.value = 0x3C
    await clock_edge(dut)

    dut.wr_en.value = 0
    dut.rd_addr.value = 100
    await clock_edge(dut)
    assert int(dut.rd_data.value) == 0xE0

    # Changing the address between edges must not change the registered output.
    dut.rd_addr.value = 101
    await Timer(1, unit="ns")
    assert int(dut.rd_data.value) == 0xE0
    await clock_edge(dut)
    assert int(dut.rd_data.value) == 0x3C


@cocotb.test()
async def disabled_write_preserves_existing_data(dut):
    await start_test(dut)

    dut.wr_en.value = 1
    dut.wr_addr.value = 37
    dut.wr_data.value = 0x5A
    await clock_edge(dut)

    # Try to overwrite the location with writes disabled.
    dut.wr_en.value = 0
    dut.wr_data.value = 0xFF
    dut.rd_addr.value = 37
    await clock_edge(dut)
    assert int(dut.rd_data.value) == 0x5A


@cocotb.test()
async def first_and_last_memory_addresses_work(dut):
    await start_test(dut)

    # Write both ends of the address range.
    dut.wr_en.value = 1
    dut.wr_addr.value = 0
    dut.wr_data.value = 0x12
    await clock_edge(dut)
    dut.wr_addr.value = 4095
    dut.wr_data.value = 0xED
    await clock_edge(dut)

    dut.wr_en.value = 0
    dut.rd_addr.value = 0
    await clock_edge(dut)
    assert int(dut.rd_data.value) == 0x12

    dut.rd_addr.value = 4095
    await clock_edge(dut)
    assert int(dut.rd_data.value) == 0xED


@cocotb.test()
async def simultaneous_read_and_write_to_different_addresses(dut):
    await start_test(dut)

    # Preload a read location and a separate write location.
    dut.wr_en.value = 1
    dut.wr_addr.value = 12
    dut.wr_data.value = 0x67
    await clock_edge(dut)
    dut.wr_addr.value = 25
    dut.wr_data.value = 0x11
    await clock_edge(dut)

    # Read address 12 while writing a new value to address 25.
    dut.rd_addr.value = 12
    dut.wr_addr.value = 25
    dut.wr_data.value = 0xA9
    await clock_edge(dut)
    assert int(dut.rd_data.value) == 0x67

    # Confirm the simultaneous write updated its independent destination.
    dut.wr_en.value = 0
    dut.rd_addr.value = 25
    await clock_edge(dut)
    assert int(dut.rd_data.value) == 0xA9


@cocotb.test()
async def same_address_read_write_returns_old_data(dut):
    await start_test(dut)

    dut.wr_en.value = 1
    dut.wr_addr.value = 100
    dut.wr_data.value = 0x31
    await clock_edge(dut)

    # With nonblocking assignments, rd_data sees the old memory value here.
    dut.rd_addr.value = 100
    dut.wr_data.value = 0xC2
    await clock_edge(dut)
    assert int(dut.rd_data.value) == 0x31

    # A later read edge sees the value written during the collision.
    dut.wr_en.value = 0
    await clock_edge(dut)
    assert int(dut.rd_data.value) == 0xC2


@cocotb.test()
async def full_memory_write_and_read_sweep(dut):
    await start_test(dut)

    # Visit all 4096 locations with a repeatable address-dependent data pattern.
    dut.wr_en.value = 1
    for address in range(4096):
        dut.wr_addr.value = address
        dut.wr_data.value = (address * 37 ^ (address >> 3) ^ 0xA5) & 0xFF
        await clock_edge(dut)

    # Read every location back and compare it with the same reference pattern.
    dut.wr_en.value = 0
    for address in range(4096):
        dut.rd_addr.value = address
        await clock_edge(dut)
        expected = (address * 37 ^ (address >> 3) ^ 0xA5) & 0xFF
        assert int(dut.rd_data.value) == expected, (
            f"address {address}: expected 0x{expected:02X}, "
            f"got 0x{int(dut.rd_data.value):02X}"
        )
