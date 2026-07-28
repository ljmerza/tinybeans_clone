import { useEffect, useMemo, useRef, useState } from 'react';
import type { MutableRefObject, RefObject } from 'react';
import type { MonthRefsMap } from './useCalendarMonthWindow';

interface UseCalendarMonthVisibilityParams {
  containerRef: RefObject<HTMLDivElement | null>;
  monthRefs: MutableRefObject<MonthRefsMap>;
  monthKeys: string[];
  /**
   * IntersectionObserver threshold. Defaults to 0.01 (1% in view).
   */
  threshold?: number;
  /**
   * Root margin for the observer.
   */
  rootMargin?: string;
}

export function useCalendarMonthVisibility({
  containerRef,
  monthRefs,
  monthKeys,
  threshold = 0.01,
  rootMargin,
}: UseCalendarMonthVisibilityParams) {
  const [visibleSet, setVisibleSet] = useState<Set<string>>(new Set());
  const observerRef = useRef<IntersectionObserver | null>(null);

  // Stable helpers to mutate the visible set
  const addVisible = (key: string) =>
    setVisibleSet((prev) => (prev.has(key) ? prev : new Set([...prev, key])));
  const removeVisible = (key: string) =>
    setVisibleSet((prev) => {
      if (!prev.has(key)) return prev;
      const next = new Set(prev);
      next.delete(key);
      return next;
    });

  useEffect(() => {
    const root = containerRef.current;
    if (!root || typeof IntersectionObserver === 'undefined') {
      // Without IO, treat nothing as visible; caller may decide to render everything.
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const element = entry.target as HTMLElement;
          const key = element.getAttribute('data-month-key');
          if (!key) return;
          if (entry.isIntersecting) {
            addVisible(key);
          } else {
            removeVisible(key);
          }
        });
      },
      { root, threshold, rootMargin }
    );
    observerRef.current = observer;

    // Observe currently available nodes for the month keys
    monthKeys.forEach((key) => {
      const node = monthRefs.current.get(key);
      if (node) {
        observer.observe(node);
      }
    });

    return () => {
      observer.disconnect();
      observerRef.current = null;
    };
  }, [containerRef, monthRefs, monthKeys, threshold, rootMargin]);

  // Keep observer in sync when refs are added later for existing keys
  useEffect(() => {
    const observer = observerRef.current;
    if (!observer) return;

    monthKeys.forEach((key) => {
      const node = monthRefs.current.get(key);
      if (node) observer.observe(node);
    });
  }, [monthRefs, monthKeys]);

  return useMemo(() => visibleSet, [visibleSet]);
}
