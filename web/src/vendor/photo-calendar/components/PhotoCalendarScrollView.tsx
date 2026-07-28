import type { HTMLAttributes, ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePhotoCalendarContext } from '../context/PhotoCalendarContext';
import { PhotoCalendarMonthGrid } from '../primitives/PhotoCalendarMonthGrid';
import { PhotoCalendarWeekdays, type WeekdayRenderProps } from '../primitives/PhotoCalendarWeekdays';
import type { DayRenderProps } from '../types/calendar';
import { useCalendarMonthVisibility } from '../hooks/useCalendarMonthVisibility';

export interface PhotoCalendarScrollViewProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Custom renderer for day cells.
   */
  renderDay?: (props: DayRenderProps) => ReactNode;
  /**
   * Custom renderer for weekday headers.
   */
  renderWeekdays?: (props: WeekdayRenderProps) => ReactNode;
  /**
   * Optional developer scaffolding slot rendered inside the scroll view container.
   */
  children?: ReactNode;
  /**
   * Maximum number of month sections to keep mounted at once.
   * Defaults to 7 which keeps memory in check while preserving scroll continuity.
   */
  maxRenderedMonths?: number;
}

const DEFAULT_MAX_RENDERED_MONTHS = 7;

function combineClassName(base: string, additional?: string) {
  return additional ? `${base} ${additional}` : base;
}

export function PhotoCalendarScrollView({
  renderDay,
  renderWeekdays,
  children,
  maxRenderedMonths = DEFAULT_MAX_RENDERED_MONTHS,
  className,
  ...rest
}: PhotoCalendarScrollViewProps) {
  const { monthKey, scroll } = usePhotoCalendarContext('PhotoCalendarScrollView');
  const containerRef = useRef<HTMLDivElement | null>(null);
  const topSentinelRef = useRef<HTMLDivElement | null>(null);
  const bottomSentinelRef = useRef<HTMLDivElement | null>(null);
  const monthRefs = useRef<Map<string, HTMLElement>>(new Map());

  const maxMountedMonths = Math.max(1, maxRenderedMonths);

  const buildWindow = useCallback(
    (centerKey: string, targetSize: number) => {
      const keys: string[] = [centerKey];
      let prevKey = centerKey;
      let nextKey = centerKey;
      while (keys.length < targetSize) {
        const prevCandidate = scroll.getAdjacentMonthKey(prevKey, -1);
        const nextCandidate = scroll.getAdjacentMonthKey(nextKey, 1);
        if (prevCandidate && !keys.includes(prevCandidate)) {
          keys.unshift(prevCandidate);
          prevKey = prevCandidate;
        }
        if (keys.length >= targetSize) break;
        if (nextCandidate && !keys.includes(nextCandidate)) {
          keys.push(nextCandidate);
          nextKey = nextCandidate;
        }
        if (!prevCandidate && !nextCandidate) break;
      }
      return keys;
    },
    [scroll]
  );

  const [monthKeys, setMonthKeys] = useState<string[]>(() =>
    buildWindow(monthKey, Math.min(3, maxMountedMonths))
  );

  useEffect(() => {
    monthRefs.current.forEach((_node, key) => {
      if (!monthKeys.includes(key)) monthRefs.current.delete(key);
    });
  }, [monthKeys]);

  const registerMonthRef = useCallback(
    (key: string) => (node: HTMLElement | null) => {
      if (!node) {
        monthRefs.current.delete(key);
        return;
      }
      monthRefs.current.set(key, node);
    },
    []
  );

  const extendWindow = useCallback(
    (direction: 'prev' | 'next') => {
      setMonthKeys((prev) => {
        if (prev.length === 0) return prev;
        const pivot = direction === 'prev' ? prev[0] : prev[prev.length - 1];
        const delta = direction === 'prev' ? -1 : 1;
        const adjacent = scroll.getAdjacentMonthKey(pivot, delta);
        if (!adjacent || prev.includes(adjacent)) return prev;
        const next = direction === 'prev' ? [adjacent, ...prev] : [...prev, adjacent];
        if (next.length <= maxMountedMonths) return next;
        return direction === 'prev' ? next.slice(0, maxMountedMonths) : next.slice(next.length - maxMountedMonths);
      });
    },
    [maxMountedMonths, scroll]
  );

  const ensureMonthInWindow = useCallback(
    (targetKey: string) => {
      setMonthKeys((prev) => (prev.includes(targetKey) ? prev : buildWindow(targetKey, maxMountedMonths)));
    },
    [buildWindow, maxMountedMonths]
  );

  const [activeMonthKey, setActiveMonthKey] = useState<string>(monthKey);
  const activeMonthKeyRef = useRef(activeMonthKey);
  const isProgrammaticScrollRef = useRef(false);
  const hasAlignedInitialRef = useRef(false);
  const lastScrollSyncRef = useRef<string | null>(null);
  const scrollFrameRef = useRef<number | null>(null);
  const sectionHeightsRef = useRef<Map<string, number>>(new Map());

  const scrollToMonthKey = useCallback((targetKey: string, behavior: ScrollBehavior = 'smooth') => {
    const node = monthRefs.current.get(targetKey);
    const container = containerRef.current;
    if (!node || !container) return;
    if (typeof node.scrollIntoView === 'function') {
      node.scrollIntoView({ block: 'start', behavior });
    } else {
      const offsetTop = node.offsetTop - container.offsetTop;
      container.scrollTop = offsetTop;
    }
  }, []);

  // Initial alignment
  useEffect(() => {
    ensureMonthInWindow(monthKey);
    if (hasAlignedInitialRef.current) return;
    const id = requestAnimationFrame(() => {
      hasAlignedInitialRef.current = true;
      if (activeMonthKeyRef.current !== monthKey) {
        activeMonthKeyRef.current = monthKey;
        setActiveMonthKey(monthKey);
      }
      isProgrammaticScrollRef.current = true;
      scrollToMonthKey(monthKey, 'auto');
      requestAnimationFrame(() => {
        isProgrammaticScrollRef.current = false;
      });
    });
    return () => cancelAnimationFrame(id);
  }, [ensureMonthInWindow, monthKey, scrollToMonthKey]);

  // External monthKey changes
  useEffect(() => {
    if (!hasAlignedInitialRef.current) return;
    if (lastScrollSyncRef.current === monthKey) {
      lastScrollSyncRef.current = null;
      return;
    }
    ensureMonthInWindow(monthKey);
    if (activeMonthKeyRef.current !== monthKey) {
      activeMonthKeyRef.current = monthKey;
      setActiveMonthKey(monthKey);
    }
    isProgrammaticScrollRef.current = true;
    scrollToMonthKey(monthKey);
    requestAnimationFrame(() => {
      isProgrammaticScrollRef.current = false;
    });
  }, [ensureMonthInWindow, monthKey, scrollToMonthKey]);

  // Only render the heavy month grid when the section is actually visible
  const visibleSet = useCalendarMonthVisibility({
    containerRef,
    monthRefs,
    monthKeys,
    threshold: 0.01,
  });

  // Cache measured section heights for offscreen placeholders
  useEffect(() => {
    visibleSet.forEach((key) => {
      const node = monthRefs.current.get(key);
      if (!node) return;
      const rect = node.getBoundingClientRect();
      if (rect.height > 0) {
        sectionHeightsRef.current.set(key, rect.height);
      }
    });
  }, [visibleSet, monthRefs]);

  // Window expansion via IntersectionObserver
  useEffect(() => {
    const root = containerRef.current;
    const top = topSentinelRef.current;
    const bottom = bottomSentinelRef.current;
    if (!root || !top || !bottom || typeof IntersectionObserver === 'undefined') return;
    let rafId: number | null = null;
    let observer: IntersectionObserver | null = null;
    const start = () => {
      observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            if (entry.target === top) {
              if (root.scrollTop === 0) return;
              extendWindow('prev');
            } else if (entry.target === bottom) {
              extendWindow('next');
            }
          });
        },
        { root, threshold: 0.1 }
      );
      observer.observe(top);
      observer.observe(bottom);
    };
    rafId = requestAnimationFrame(start);
    return () => {
      if (rafId) cancelAnimationFrame(rafId);
      observer?.disconnect();
    };
  }, [extendWindow]);

  // Active month tracking on scroll
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const onScroll = () => {
      if (isProgrammaticScrollRef.current) return;
      if (scrollFrameRef.current !== null) cancelAnimationFrame(scrollFrameRef.current);
      scrollFrameRef.current = requestAnimationFrame(() => {
        scrollFrameRef.current = null;
        const containerTop = container.getBoundingClientRect().top;
        let nextActive = monthKeys[0] ?? activeMonthKeyRef.current;
        for (const key of monthKeys) {
          const node = monthRefs.current.get(key);
          if (!node) continue;
          const rect = node.getBoundingClientRect();
          if (rect.top - containerTop <= 2) nextActive = key; else break;
        }
        if (nextActive !== activeMonthKeyRef.current) {
          activeMonthKeyRef.current = nextActive;
          setActiveMonthKey(nextActive);
          if (nextActive !== monthKey) {
            lastScrollSyncRef.current = nextActive;
            scroll.syncVisibleMonth(nextActive);
          }
        }
      });
    };
    container.addEventListener('scroll', onScroll, { passive: true });
    // fire once in case initial viewport already shows multiple months
    onScroll();
    return () => {
      container.removeEventListener('scroll', onScroll);
      if (scrollFrameRef.current !== null) cancelAnimationFrame(scrollFrameRef.current);
    };
  }, [monthKeys, monthKey, scroll]);

  const snapshots = useMemo(() => monthKeys.map((key) => scroll.getMonthSnapshot(key)), [monthKeys, scroll]);
  const activeSnapshot = snapshots.find((s) => s.monthKey === activeMonthKey) ?? scroll.getMonthSnapshot(activeMonthKey);

  const { role: roleProp, ['aria-label']: ariaLabelProp, ...containerProps } = rest;
  const role = roleProp ?? 'grid';
  const ariaLabel =
    ariaLabelProp ?? `Photo calendar timeline – currently viewing ${activeSnapshot.monthLabel}`;
  const containerClassName = combineClassName('calendar-scroll-container', className);

  return (
    <div className="calendar-scroll-view">
      <div
        {...containerProps}
        role={role}
        aria-label={ariaLabel}
        className={containerClassName}
        ref={containerRef}
      >
        <div ref={topSentinelRef} aria-hidden="true" className="calendar-scroll-sentinel" />
        {snapshots.map((snapshot) => {
          const isActive = snapshot.monthKey === activeMonthKey;
          const headerId = `calendar-month-${snapshot.monthKey}`;
          const isVisible = visibleSet.has(snapshot.monthKey);

          return (
            <section
              key={snapshot.monthKey}
              className="calendar-month-section"
              data-month-key={snapshot.monthKey}
              aria-labelledby={`${headerId}-header`}
              ref={registerMonthRef(snapshot.monthKey)}
            >
              <div
                id={`${headerId}-header`}
                className={combineClassName(
                  'calendar-month-header',
                  isActive ? 'calendar-month-header--active' : undefined
                )}
                aria-current={isActive ? 'date' : undefined}
              >
                <strong>{snapshot.monthLabel}</strong>
              </div>
              {isVisible ? (
                <>
                  <PhotoCalendarWeekdays>{renderWeekdays}</PhotoCalendarWeekdays>
                  <PhotoCalendarMonthGrid renderDay={renderDay} dayStates={snapshot.dayStates} />
                </>
              ) : (
                <div aria-hidden="true" style={{ height: sectionHeightsRef.current.get(snapshot.monthKey) ?? 480 }} />
              )}
            </section>
          );
        })}
        <div ref={bottomSentinelRef} aria-hidden="true" className="calendar-scroll-sentinel" />
        {children}
      </div>
    </div>
  );
}
