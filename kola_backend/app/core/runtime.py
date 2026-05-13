from __future__ import annotations

import asyncio
import sys


def configure_windows_event_loop() -> None:
    if sys.platform != "win32":
        return
    policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy is not None:
        asyncio.set_event_loop_policy(policy())
