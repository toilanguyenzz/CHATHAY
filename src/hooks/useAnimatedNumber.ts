import { useState, useEffect } from "react";

/**
 * Animated number counter with cubic easing.
 * Shared hook — used by Hub, File Processing, AI Learning pages.
 */
export function useAnimatedNumber(target: number, duration = 800) {
  const [current, setCurrent] = useState(0);
  useEffect(() => {
    let start = 0;
    const step = (ts: number) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      setCurrent(Math.round((1 - Math.pow(1 - p, 3)) * target));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration]);
  return current;
}
