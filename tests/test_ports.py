"""Unit tests for TCP port allocation."""

from __future__ import annotations

import socket

import pytest

from batch_stlink_flasher.util.ports import (
    allocate_openocd_ports,
    allocate_openocd_ports_batch,
    allocate_tcp_ports,
)


def test_allocate_tcp_ports_count_and_unique() -> None:
    ports = allocate_tcp_ports(5)
    assert len(ports) == 5
    assert len(set(ports)) == 5
    assert all(1 <= p <= 65535 for p in ports)


def test_allocate_tcp_ports_rejects_zero() -> None:
    with pytest.raises(ValueError):
        allocate_tcp_ports(0)


def test_allocate_openocd_ports_distinct() -> None:
    ports = allocate_openocd_ports()
    assert len({ports.gdb, ports.telnet, ports.tcl}) == 3


def test_allocate_openocd_ports_batch_disjoint() -> None:
    batch = allocate_openocd_ports_batch(4)
    assert len(batch) == 4
    flat = [p for triple in batch for p in (triple.gdb, triple.telnet, triple.tcl)]
    assert len(flat) == len(set(flat))


def test_allocated_ports_are_bindable() -> None:
    """After allocation, another process should be able to bind the returned ports."""
    ports = allocate_tcp_ports(2)
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
