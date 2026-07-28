import { useEffect } from 'react';
import type { RefObject } from 'react';

interface UseCalendarWindowExpansionObserverParams {
  containerRef: RefObject<HTMLDivElement>;
  topSentinelRef: RefObject<HTMLDivElement>;
  bottomSentinelRef: RefObject<HTMLDivElement>;
  extendWindow: (direction: 'prev' | 'next') => void;
  /**
   * Delay enabling the intersection observers by N animation frames.
   * This gives initial programmatic alignment a chance to run so we don't
   * immediately expand backwards while the top sentinel is in view.
   * Defaults to 2 frames.
   */
  startDelayFrames?: number;
}

export function useCalendarWindowExpansionObserver({
  containerRef,
  topSentinelRef,
  bottomSentinelRef,
  extendWindow,
  startDelayFrames = 2,
}: UseCalendarWindowExpansionObserverParams) {
  useEffect(() => {
    const root = containerRef.current;
    const topSentinel = topSentinelRef.current;
    const bottomSentinel = bottomSentinelRef.current;

    if (
      typeof IntersectionObserver === 'undefined' ||
      !root ||
      !topSentinel ||
      !bottomSentinel
    ) {
      return;
    }

    let rafId: number | null = null;

    const setup = () => {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) {
              return;
            }
            if (entry.target === topSentinel) {
              // Avoid aggressive backwards expansion when scroller is at top
              if (root.scrollTop === 0) return;
              extendWindow('prev');
            } else if (entry.target === bottomSentinel) {
              extendWindow('next');
            }
          });
        },
        { root, threshold: 0.1 }
      );

      observer.observe(topSentinel);
      observer.observe(bottomSentinel);

      return observer;
    };

    // Delay enabling the observer to allow initial scroll alignment
    let frames = Math.max(0, Math.floor(startDelayFrames));
    let observer: IntersectionObserver | null = null;
    const tick = () => {
      if (frames > 0) {
        frames -= 1;
        rafId = window.requestAnimationFrame(tick);
      } else {
        observer = setup();
      }
    };
    rafId = window.requestAnimationFrame(tick);

    return () => {
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
      }
      observer?.disconnect();
    };
  }, [containerRef, topSentinelRef, bottomSentinelRef, extendWindow, startDelayFrames]);
}
