import { useCallback, useEffect, useRef, useState } from 'react';
import type { MutableRefObject, RefObject } from 'react';
import type { PhotoCalendarScrollState } from './usePhotoCalendarState';
import type { MonthRefsMap } from './useCalendarMonthWindow';

interface UseCalendarActiveMonthTrackingParams {
  containerRef: RefObject<HTMLDivElement>;
  monthRefs: MutableRefObject<MonthRefsMap>;
  monthKeys: string[];
  visibleMonthKey: string;
  scroll: PhotoCalendarScrollState;
  ensureMonthInWindow: (targetKey: string) => void;
}

export function useCalendarActiveMonthTracking({
  containerRef,
  monthRefs,
  monthKeys,
  visibleMonthKey,
  scroll,
  ensureMonthInWindow,
}: UseCalendarActiveMonthTrackingParams) {
  const [activeMonthKey, setActiveMonthKey] = useState(() => visibleMonthKey);
  const activeMonthKeyRef = useRef(activeMonthKey);
  const scrollFrameRef = useRef<number | null>(null);
  const lastScrollSyncRef = useRef<string | null>(null);
  const isProgrammaticScrollRef = useRef<boolean>(false);
  const hasAlignedInitialRef = useRef<boolean>(false);
  const initialAlignRafRef = useRef<number | null>(null);
  const initialAlignAttemptsRef = useRef<number>(0);

  const scrollToMonthKey = useCallback(
    (targetKey: string, behavior: ScrollBehavior = 'smooth') => {
      const node = monthRefs.current.get(targetKey);
      if (!node) {
        return;
      }
      if (typeof node.scrollIntoView === 'function') {
        node.scrollIntoView({ block: 'start', behavior });
        return;
      }
      const container = containerRef.current;
      if (!container) {
        return;
      }
      const offsetTop = node.offsetTop - container.offsetTop;
      container.scrollTop = offsetTop;
    },
    [containerRef, monthRefs]
  );

  const evaluateActiveMonth = useCallback(() => {
    // Ignore scroll events triggered by our own scrollToMonthKey
    if (isProgrammaticScrollRef.current) {
      return;
    }

    // Defer evaluation until we've aligned the viewport once
    if (!hasAlignedInitialRef.current) {
      return;
    }

    const container = containerRef.current;
    if (!container || monthKeys.length === 0) {
      return;
    }

    const containerTop = container.getBoundingClientRect().top;
    let nextActiveKey = monthKeys[0];

    for (const key of monthKeys) {
      const section = monthRefs.current.get(key);
      if (!section) {
        continue;
      }
      const rect = section.getBoundingClientRect();
      if (rect.top - containerTop <= 2) {
        nextActiveKey = key;
      } else {
        break;
      }
    }

    const currentActiveKey = activeMonthKeyRef.current;
    if (nextActiveKey !== currentActiveKey) {
      activeMonthKeyRef.current = nextActiveKey;
      setActiveMonthKey(nextActiveKey);
      if (nextActiveKey !== visibleMonthKey && lastScrollSyncRef.current !== nextActiveKey) {
        lastScrollSyncRef.current = nextActiveKey;
        scroll.syncVisibleMonth(nextActiveKey);
      }
    }
  }, [containerRef, monthKeys, monthRefs, scroll, visibleMonthKey]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const handleScroll = () => {
      if (scrollFrameRef.current !== null) {
        cancelAnimationFrame(scrollFrameRef.current);
      }

      scrollFrameRef.current = window.requestAnimationFrame(() => {
        scrollFrameRef.current = null;
        evaluateActiveMonth();
      });
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    return () => {
      container.removeEventListener('scroll', handleScroll);
      if (scrollFrameRef.current !== null) {
        cancelAnimationFrame(scrollFrameRef.current);
        scrollFrameRef.current = null;
      }
    };
  }, [containerRef, evaluateActiveMonth]);

  useEffect(() => {
    ensureMonthInWindow(visibleMonthKey);

    // On first mount, always align the viewport to the visible month (today)
    if (!hasAlignedInitialRef.current) {
      const tryAlign = () => {
        const node = monthRefs.current.get(visibleMonthKey);
        const container = containerRef.current;
        if (node && container) {
          hasAlignedInitialRef.current = true;
          if (activeMonthKeyRef.current !== visibleMonthKey) {
            activeMonthKeyRef.current = visibleMonthKey;
            setActiveMonthKey(visibleMonthKey);
          }
          isProgrammaticScrollRef.current = true;
          scrollToMonthKey(visibleMonthKey);
          requestAnimationFrame(() => {
            isProgrammaticScrollRef.current = false;
          });
          return;
        }

        if (initialAlignAttemptsRef.current < 30) {
          initialAlignAttemptsRef.current += 1;
          initialAlignRafRef.current = requestAnimationFrame(tryAlign);
        } else {
          // Give up to avoid hanging; mark aligned and proceed
          hasAlignedInitialRef.current = true;
        }
      };

      // Kick alignment on the next frame to allow refs to populate
      initialAlignRafRef.current = requestAnimationFrame(tryAlign);
      return () => {
        if (initialAlignRafRef.current !== null) {
          cancelAnimationFrame(initialAlignRafRef.current);
          initialAlignRafRef.current = null;
        }
      };
    }

    const isInternalSync = lastScrollSyncRef.current === visibleMonthKey;

    if (isInternalSync) {
      // Clear the sentinel set during evaluateActiveMonth → syncVisibleMonth
      lastScrollSyncRef.current = null;
      return; // Do not scroll programmatically when user scroll drove the change
    }

    // External/monthKey-controlled change: align the viewport, but suppress
    // evaluateActiveMonth during the programmatic scroll to avoid reentry.
    if (activeMonthKeyRef.current !== visibleMonthKey) {
      activeMonthKeyRef.current = visibleMonthKey;
      setActiveMonthKey(visibleMonthKey);
    }

    isProgrammaticScrollRef.current = true;
    scrollToMonthKey(visibleMonthKey);
    // Clear suppression on next frame
    requestAnimationFrame(() => {
      isProgrammaticScrollRef.current = false;
    });
  }, [ensureMonthInWindow, scrollToMonthKey, visibleMonthKey]);

  useEffect(() => {
    evaluateActiveMonth();
  }, [evaluateActiveMonth, monthKeys]);

  return activeMonthKey;
}
