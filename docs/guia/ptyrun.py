#!/usr/bin/env python3
"""Run a command at a pseudo-terminal and answer its first "> " prompt.

    python3 ptyrun.py <answer> <command> [args...]

The engine asks the mode question only at a terminal. This gives it one, waits
for the prompt, types the answer, and prints everything the terminal showed.
Used by capture.sh; macOS and Linux only.
"""
import os
import pty
import select
import sys
import time

answer = sys.argv[1].encode() + b"\n"
command = sys.argv[2:]
pid, fd = pty.fork()
if pid == 0:
    os.execvp(command[0], command)
shown = b""
sent = False
while True:
    ready, _, _ = select.select([fd], [], [], 120)
    if not ready:
        break
    try:
        data = os.read(fd, 4096)
    except OSError:
        break
    if not data:
        break
    shown += data
    if not sent and b"> " in shown:
        time.sleep(0.3)
        os.write(fd, answer)
        sent = True
os.waitpid(pid, 0)
sys.stdout.buffer.write(shown.replace(b"\r\n", b"\n"))
