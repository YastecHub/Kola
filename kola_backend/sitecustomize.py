from __future__ import annotations

import asyncio
import sys


if sys.platform == "win32":
    policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if policy is not None:
        asyncio.set_event_loop_policy(policy())
