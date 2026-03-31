#!/usr/bin/env python3
"""W610 diagnostic tool — test connectivity and dump raw RS485 data.

Usage:
    python3 diag_w610.py <IP> [PORT]

Example:
    python3 diag_w610.py 192.168.1.11
    python3 diag_w610.py 192.168.1.11 8899
"""

import socket
import sys
import time


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 diag_w610.py <IP> [PORT]")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8899
    duration = 5

    print(f"=== W610 Diagnostic Tool ===")
    print(f"Target: {host}:{port}")
    print()

    # Step 1: TCP connection
    print(f"[1/3] Connecting to {host}:{port} ...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        t0 = time.time()
        sock.connect((host, port))
        elapsed = (time.time() - t0) * 1000
        print(f"  OK — connected in {elapsed:.0f}ms")
    except socket.timeout:
        print(f"  FAIL — timeout after 5s. The host {host} is not reachable.")
        print(f"  Check: IP address, W610 powered on, same network/VLAN.")
        sys.exit(1)
    except ConnectionRefusedError:
        print(f"  FAIL — connection refused. Host {host} is reachable but port {port} is closed.")
        print(f"  Check: port number in W610 config (default 8899), no other client connected.")
        sys.exit(1)
    except OSError as e:
        print(f"  FAIL — {e}")
        sys.exit(1)

    # Step 2: Read raw data
    print(f"[2/3] Listening for RS485 data ({duration}s) ...")
    sock.settimeout(0.5)
    data = b""
    start = time.time()
    while time.time() - start < duration:
        try:
            chunk = sock.recv(2048)
            if chunk:
                data += chunk
        except socket.timeout:
            continue
    sock.close()

    print(f"  Received {len(data)} bytes in {duration}s")
    if not data:
        print(f"  FAIL — 0 bytes. No RS485 traffic.")
        print(f"  Check: RS485 A/B wiring, W610 mode = Transparent, baud = 9600, spa powered on.")
        sys.exit(1)

    # Step 3: Show raw data + check for Joyonway frames
    print(f"[3/3] Analyzing data ...")
    print()
    print("--- Raw hex dump (first 256 bytes) ---")
    for i in range(0, min(len(data), 256), 16):
        hexpart = " ".join(f"{b:02x}" for b in data[i : i + 16])
        ascpart = "".join(chr(b) if 32 <= b < 127 else "." for b in data[i : i + 16])
        print(f"  {i:04x}  {hexpart:<48s}  {ascpart}")
    print()

    # Look for 7E frames
    frame_count = 0
    b4_found = False
    b5_found = False
    idx = 0
    while idx < len(data):
        pos = data.find(b"\x7e", idx)
        if pos == -1:
            break
        if pos + 2 < len(data) and data[pos + 1] == 0x1A:
            frame_count += 1
            if pos + 5 <= len(data):
                if data[pos + 2:pos + 5] == b"\xf9\xbf\xb4":
                    b4_found = True
                elif data[pos + 2:pos + 5] == b"\xf9\xbf\xb5":
                    b5_found = True
        idx = pos + 1

    if frame_count > 0:
        print(f"  Found {frame_count} Joyonway frame(s) (0x7E delimited)")
        print(f"  Status frame (B4): {'YES' if b4_found else 'not found'}")
        print(f"  Filtration frame (B5): {'YES' if b5_found else 'not found'}")
        if b4_found:
            print()
            print("  ==> Data looks valid! The integration should work.")
    else:
        print(f"  No Joyonway frames found (expected 0x7E delimiters with 0xF9 0xBF header).")
        print(f"  Data is received but not recognized as Joyonway protocol.")
        print(f"  Check: baud rate = 9600 8N1, this is a Joyonway/Mesda spa.")


if __name__ == "__main__":
    main()
