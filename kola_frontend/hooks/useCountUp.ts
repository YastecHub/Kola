"use client";

import { useEffect, useState } from "react";

export function useCountUp(target: number, duration = 1200, trigger = true, start = 0) {
  const [value, setValue] = useState(start);

  useEffect(() => {
    if (!trigger) return;
    let frame = 0;
    let startTime: number | null = null;
    const step = (time: number) => {
      if (startTime === null) startTime = time;
      const progress = Math.min((time - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 4);
      setValue(Math.round(start + (target - start) * eased));
      if (progress < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [duration, start, target, trigger]);

  return value;
}
