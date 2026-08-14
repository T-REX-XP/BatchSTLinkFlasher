"""Allocate free localhost TCP ports for OpenOCD instances."""

from __future__ import annotations

import socket

from batch_stlink_flasher.flashing.models import OpenOcdPorts


def allocate_tcp_ports(count: int, *, host: str = "127.0.0.1") -> list[int]:
    """
    Bind ``count`` ephemeral sockets and return their port numbers.

    Sockets are closed before return so callers can bind the same ports shortly after.
    There is a small race until the consumer binds; acceptable for local OpenOCD jobs.
    """
    if count < 1:
        raise ValueError("count must be >= 1")

    sockets: list[socket.socket] = []
    try:
        for _ in range(count):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind((host, 0))
            sockets.append(sock)
        return [s.getsockname()[1] for s in sockets]
    finally:
        for sock in sockets:
            sock.close()


def allocate_openocd_ports(*, host: str = "127.0.0.1") -> OpenOcdPorts:
    """Allocate three distinct free ports for gdb / telnet / tcl."""
    gdb, telnet, tcl = allocate_tcp_ports(3, host=host)
    return OpenOcdPorts(gdb=gdb, telnet=telnet, tcl=tcl)


def allocate_openocd_ports_batch(job_count: int, *, host: str = "127.0.0.1") -> list[OpenOcdPorts]:
    """Allocate a disjoint port triple for each of ``job_count`` concurrent OpenOCD jobs."""
    if job_count < 1:
        raise ValueError("job_count must be >= 1")
    ports = allocate_tcp_ports(job_count * 3, host=host)
    return [
        OpenOcdPorts(gdb=ports[i], telnet=ports[i + 1], tcl=ports[i + 2])
        for i in range(0, len(ports), 3)
    ]
