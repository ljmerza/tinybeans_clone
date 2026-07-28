import { useCallback, useEffect, useRef, useState } from 'react';
import type { MutableRefObject } from 'react';
import type { PhotoCalendarScrollState } from './usePhotoCalendarState';

export type MonthRefsMap = Map<string, HTMLElement>;

interface UseCalendarMonthWindowParams {
  scroll: PhotoCalendarScrollState;
  visibleMonthKey: string;
  maxMountedMonths: number;
}

export interface CalendarMonthWindowResult {
  monthKeys: string[];
  registerMonthRef: (key: string) => (node: HTMLElement | null) => void;
  monthRefs: MutableRefObject<MonthRefsMap>;
  extendWindow: (direction: 'prev' | 'next') => void;
  ensureMonthInWindow: (targetKey: string) => void;
}

const INITIAL_WINDOW_COUNT = 3;

function buildWindow(scroll: PhotoCalendarScrollState, centerKey: string, targetSize: number) {
  const keys: string[] = [centerKey];
  let prevKey = centerKey;
  let nextKey = centerKey;

  while (keys.length < targetSize) {
    const prevCandidate = scroll.getAdjacentMonthKey(prevKey, -1);
    const nextCandidate = scroll.getAdjacentMonthKey(nextKey, 1);
    const canAddPrev = Boolean(prevCandidate) && !keys.includes(prevCandidate as string);
    const canAddNext = Boolean(nextCandidate) && !keys.includes(nextCandidate as string);

    if (!canAddPrev && !canAddNext) {
      break;
    }

    if (canAddPrev && prevCandidate) {
      keys.unshift(prevCandidate);
      prevKey = prevCandidate;
    }

    if (keys.length >= targetSize) {
      break;
    }

    if (canAddNext && nextCandidate) {
      keys.push(nextCandidate);
      nextKey = nextCandidate;
    }
  }

  return keys;
}

function arraysEqual(left: string[], right: string[]) {
  if (left.length !== right.length) {
    return false;
  }
  return left.every((value, index) => value === right[index]);
}

export function useCalendarMonthWindow({
  scroll,
  visibleMonthKey,
  maxMountedMonths,
}: UseCalendarMonthWindowParams): CalendarMonthWindowResult {
  const initialWindowSize = Math.min(INITIAL_WINDOW_COUNT, maxMountedMonths);
  const monthRefs = useRef<MonthRefsMap>(new Map());

  const [monthKeys, setMonthKeys] = useState<string[]>(() =>
    buildWindow(scroll, visibleMonthKey, initialWindowSize)
  );

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

  useEffect(() => {
    monthRefs.current.forEach((_node, key) => {
      if (!monthKeys.includes(key)) {
        monthRefs.current.delete(key);
      }
    });
  }, [monthKeys]);

  useEffect(() => {
    setMonthKeys((prev) => {
      const desiredSize = Math.max(Math.min(prev.length, maxMountedMonths), 1);
      const nextKeys = buildWindow(scroll, visibleMonthKey, desiredSize);
      return arraysEqual(prev, nextKeys) ? prev : nextKeys;
    });
  }, [scroll, visibleMonthKey, maxMountedMonths]);

  const extendWindow = useCallback(
    (direction: 'prev' | 'next') => {
      setMonthKeys((prev) => {
        if (prev.length === 0) {
          return prev;
        }

        const pivot = direction === 'prev' ? prev[0] : prev[prev.length - 1];
        const offset = direction === 'prev' ? -1 : 1;
        const adjacent = scroll.getAdjacentMonthKey(pivot, offset);

        if (!adjacent || prev.includes(adjacent)) {
          return prev;
        }

        const nextKeys = direction === 'prev' ? [adjacent, ...prev] : [...prev, adjacent];

        if (nextKeys.length <= maxMountedMonths) {
          return nextKeys;
        }

        if (direction === 'prev') {
          return nextKeys.slice(0, maxMountedMonths);
        }

        return nextKeys.slice(nextKeys.length - maxMountedMonths);
      });
    },
    [maxMountedMonths, scroll]
  );

  const ensureMonthInWindow = useCallback(
    (targetKey: string) => {
      setMonthKeys((prev) => {
        if (prev.includes(targetKey)) {
          return prev;
        }
        return buildWindow(scroll, targetKey, maxMountedMonths);
      });
    },
    [scroll, maxMountedMonths]
  );

  return {
    monthKeys,
    registerMonthRef,
    monthRefs,
    extendWindow,
    ensureMonthInWindow,
  };
}
