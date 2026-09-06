import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  addMonths,
  createCalendarCells,
  formatMonthKey,
  getVisibleRange,
  parseMonthKey,
  type CalendarCell
} from '../utils/calendar';
import { createPhotosByDateMap } from '../utils/photos';
import type { DayRenderContext, VisibleRange } from '../types/calendar';
import type { PhotoEntry } from '../types/photo';

export interface UsePhotoCalendarStateOptions {
  monthKey?: string;
  defaultMonthKey?: string;
  onMonthChange?: (nextMonthKey: string) => void;
  onDaySelect?: (info: { isoDate: string; date: Date }) => void;
  firstDayOfWeek?: 0 | 1 | 2 | 3 | 4 | 5 | 6;
  entries?: PhotoEntry[];
  maxThumbnailsPerDay?: number;
  minMonthKey?: string;
  maxMonthKey?: string;
  onRangeChange?: (range: VisibleRange) => void;
  onVisibleMonthChange?: (monthKey: string) => void;
  locale?: string;
  timeZone?: string;
}

export interface WeekdayLabels {
  short: string[];
  long: string[];
}

export interface PhotoCalendarDayState {
  cell: CalendarCell;
  context: DayRenderContext;
  ariaLabel: string;
  isSelectable: boolean;
}

export interface PhotoCalendarMonthSnapshot {
  monthKey: string;
  monthDate: Date;
  monthLabel: string;
  visibleRange: VisibleRange | null;
  dayStates: PhotoCalendarDayState[];
}

export interface PhotoCalendarScrollState {
  getMonthSnapshot: (monthKey: string) => PhotoCalendarMonthSnapshot;
  getAdjacentMonthKey: (currentMonthKey: string, delta: number) => string | null;
  clampMonthKey: (monthKey: string) => string;
  isMonthWithinBounds: (monthKey: string) => boolean;
  syncVisibleMonth: (monthKey: string) => void;
}

export interface PhotoCalendarNavigationState {
  canNavigatePrevMonth: boolean;
  canNavigateNextMonth: boolean;
  canNavigatePrevYear: boolean;
  canNavigateNextYear: boolean;
  isTodayDisabled: boolean;
  navigateMonth: (delta: number) => void;
  navigateYear: (delta: number) => void;
  navigateToMonth: (monthIndex: number) => void;
  goToToday: () => void;
  isMonthDisabled: (monthIndex: number) => boolean;
}

export interface PhotoCalendarState {
  currentYear: number;
  currentMonth: number;
  monthDate: Date;
  monthKey: string;
  monthLabel: string;
  monthNames: string[];
  weekdayLabels: WeekdayLabels;
  visibleRange: VisibleRange | null;
  dayStates: PhotoCalendarDayState[];
  navigation: PhotoCalendarNavigationState;
  scroll: PhotoCalendarScrollState;
  isControlled: boolean;
}

export function usePhotoCalendarState({
  monthKey,
  defaultMonthKey,
  onMonthChange,
  onDaySelect,
  firstDayOfWeek = 0,
  entries,
  maxThumbnailsPerDay = 1,
  minMonthKey,
  maxMonthKey,
  onRangeChange,
  onVisibleMonthChange,
  locale,
  timeZone
}: UsePhotoCalendarStateOptions = {}): PhotoCalendarState {
  const isControlled = monthKey !== undefined;
  const [internalMonthKey, setInternalMonthKey] = useState(() => formatMonthKey(parseMonthKey(defaultMonthKey)));

  const effectiveMonthKey = isControlled ? (monthKey as string) : internalMonthKey;
  const monthDate = useMemo(() => parseMonthKey(effectiveMonthKey), [effectiveMonthKey]);
  const minMonthDate = useMemo(() => (minMonthKey ? parseMonthKey(minMonthKey) : undefined), [minMonthKey]);
  const maxMonthDate = useMemo(() => (maxMonthKey ? parseMonthKey(maxMonthKey) : undefined), [maxMonthKey]);
  const currentYear = monthDate.getUTCFullYear();
  const currentMonth = monthDate.getUTCMonth();
  const resolvedLocale = locale ?? undefined;
  const resolvedTimeZone = timeZone ?? 'UTC';
  const timeZoneOption = useMemo(() => ({ timeZone: resolvedTimeZone }), [resolvedTimeZone]);
  const monthLabelFormatter = useMemo(
    () => new Intl.DateTimeFormat(resolvedLocale, { month: 'long', year: 'numeric', ...timeZoneOption }),
    [resolvedLocale, timeZoneOption]
  );
  const dayLabelFormatter = useMemo(
    () => new Intl.DateTimeFormat(resolvedLocale, { day: 'numeric', month: 'long', year: 'numeric', ...timeZoneOption }),
    [resolvedLocale, timeZoneOption]
  );
  const weekdayShortFormatter = useMemo(
    () => new Intl.DateTimeFormat(resolvedLocale, { weekday: 'short', ...timeZoneOption }),
    [resolvedLocale, timeZoneOption]
  );
  const weekdayLongFormatter = useMemo(
    () => new Intl.DateTimeFormat(resolvedLocale, { weekday: 'long', ...timeZoneOption }),
    [resolvedLocale, timeZoneOption]
  );
  const monthNameFormatter = useMemo(
    () => new Intl.DateTimeFormat(resolvedLocale, { month: 'short', ...timeZoneOption }),
    [resolvedLocale, timeZoneOption]
  );
  const monthNames = useMemo(
    () =>
      Array.from({ length: 12 }, (_, index) =>
        monthNameFormatter.format(new Date(Date.UTC(2021, index, 1)))
      ),
    [monthNameFormatter]
  );
  const photosByDate = useMemo(() => createPhotosByDateMap(entries), [entries]);
  const weekdayLabels = useMemo(() => {
    const baseDates = Array.from({ length: 7 }, (_, index) => new Date(Date.UTC(2021, 7, index + 1)));
    const shortNames = baseDates.map((date) => weekdayShortFormatter.format(date));
    const longNames = baseDates.map((date) => weekdayLongFormatter.format(date));
    const rotate = (arr: string[]) => arr.slice(firstDayOfWeek).concat(arr.slice(0, firstDayOfWeek));
    return {
      short: rotate(shortNames),
      long: rotate(longNames)
    };
  }, [firstDayOfWeek, weekdayShortFormatter, weekdayLongFormatter]);
  const maxThumbnails = Math.max(1, maxThumbnailsPerDay);
  const todayIso = useMemo(() => new Date().toISOString().slice(0, 10), []);

  const handleDaySelect = useCallback(
    (cell: CalendarCell) => {
      onDaySelect?.({
        isoDate: cell.isoDate,
        date: cell.date
      });
    },
    [onDaySelect]
  );

  const computeVisibleRange = useCallback((cells: CalendarCell[]): VisibleRange | null => {
    const range = getVisibleRange(cells);
    if (!range) {
      return null;
    }
    return {
      start: range.start,
      end: range.end,
      startIso: range.start.toISOString().slice(0, 10),
      endIso: range.end.toISOString().slice(0, 10)
    };
  }, []);

  const buildMonthSnapshot = useCallback(
    (targetMonthDate: Date): PhotoCalendarMonthSnapshot => {
      const cells = createCalendarCells(targetMonthDate, firstDayOfWeek);
      const range = computeVisibleRange(cells);
      const monthKeyValue = formatMonthKey(targetMonthDate);
      const monthLabelValue = monthLabelFormatter.format(targetMonthDate);

      const dayStatesForMonth = cells.map((cell) => {
        const photos = photosByDate[cell.isoDate] ?? [];
        const visibleThumbnails = photos.slice(0, maxThumbnails);
        const overflow = Math.max(0, photos.length - visibleThumbnails.length);
        const isToday = cell.isoDate === todayIso;
        const isSelectable = cell.inCurrentMonth;

        const context: DayRenderContext = {
          date: cell.date,
          isoDate: cell.isoDate,
          day: cell.day,
          isCurrentMonth: cell.inCurrentMonth,
          isToday,
          photos,
          visibleThumbnails,
          overflow,
          selectDay: () => {
            if (isSelectable) {
              handleDaySelect(cell);
            }
          }
        };

        const totalPhotos = photos.length;
        const photoPhrase = totalPhotos === 0 ? 'No photos' : `${totalPhotos} ${totalPhotos === 1 ? 'photo' : 'photos'}`;

        return {
          cell,
          context,
          ariaLabel: `${dayLabelFormatter.format(cell.date)}. ${photoPhrase}`,
          isSelectable
        };
      });

      return {
        monthKey: monthKeyValue,
        monthDate: new Date(targetMonthDate.getTime()),
        monthLabel: monthLabelValue,
        visibleRange: range,
        dayStates: dayStatesForMonth
      };
    },
    [computeVisibleRange, dayLabelFormatter, firstDayOfWeek, handleDaySelect, maxThumbnails, monthLabelFormatter, photosByDate, todayIso]
  );

  const currentSnapshot = useMemo(() => buildMonthSnapshot(monthDate), [buildMonthSnapshot, monthDate]);
  const { monthLabel, visibleRange, dayStates } = currentSnapshot;

  useEffect(() => {
    if (!onRangeChange || !visibleRange) {
      return;
    }

    onRangeChange(visibleRange);
  }, [onRangeChange, visibleRange]);

  useEffect(() => {
    if (!onVisibleMonthChange) {
      return;
    }
    onVisibleMonthChange(effectiveMonthKey);
  }, [effectiveMonthKey, onVisibleMonthChange]);

  const toComparableMonth = useCallback((date: Date) => date.getUTCFullYear() * 12 + date.getUTCMonth(), []);

  const minMonthIndex = useMemo(() => (minMonthDate ? toComparableMonth(minMonthDate) : null), [minMonthDate, toComparableMonth]);
  const maxMonthIndex = useMemo(() => (maxMonthDate ? toComparableMonth(maxMonthDate) : null), [maxMonthDate, toComparableMonth]);
  const currentMonthIndex = useMemo(() => toComparableMonth(monthDate), [monthDate, toComparableMonth]);

  const isWithinRange = useCallback(
    (date: Date) => {
      const index = toComparableMonth(date);
      if (minMonthIndex !== null && index < minMonthIndex) {
        return false;
      }
      if (maxMonthIndex !== null && index > maxMonthIndex) {
        return false;
      }
      return true;
    },
    [maxMonthIndex, minMonthIndex, toComparableMonth]
  );

  const clampToRange = useCallback(
    (date: Date) => {
      if (minMonthDate && toComparableMonth(date) < (minMonthIndex as number)) {
        return minMonthDate;
      }
      if (maxMonthDate && toComparableMonth(date) > (maxMonthIndex as number)) {
        return maxMonthDate;
      }
      return date;
    },
    [maxMonthDate, maxMonthIndex, minMonthDate, minMonthIndex, toComparableMonth]
  );

  const commitMonthChange = useCallback(
    (nextDate: Date) => {
      const nextKey = formatMonthKey(nextDate);
      if (nextKey === effectiveMonthKey) {
        return;
      }
      onMonthChange?.(nextKey);
      if (!isControlled) {
        setInternalMonthKey(nextKey);
      }
    },
    [effectiveMonthKey, isControlled, onMonthChange]
  );

  const navigateToMonth = useCallback(
    (monthIndex: number) => {
      const nextDate = new Date(Date.UTC(currentYear, monthIndex, 1));
      if (!isWithinRange(nextDate)) {
        const clamped = clampToRange(nextDate);
        if (toComparableMonth(clamped) === currentMonthIndex) {
          return;
        }
        commitMonthChange(clamped);
        return;
      }
      commitMonthChange(nextDate);
    },
    [clampToRange, commitMonthChange, currentMonthIndex, currentYear, isWithinRange, toComparableMonth]
  );

  const navigateMonth = useCallback(
    (delta: number) => {
      const nextDate = addMonths(monthDate, delta);
      const clamped = clampToRange(nextDate);
      if (toComparableMonth(clamped) === currentMonthIndex) {
        return;
      }
      commitMonthChange(clamped);
    },
    [clampToRange, commitMonthChange, currentMonthIndex, monthDate, toComparableMonth]
  );

  const navigateYear = useCallback(
    (delta: number) => {
      const nextDate = new Date(Date.UTC(currentYear + delta, currentMonth, 1));
      const clamped = clampToRange(nextDate);
      if (toComparableMonth(clamped) === currentMonthIndex) {
        return;
      }
      commitMonthChange(clamped);
    },
    [clampToRange, commitMonthChange, currentMonth, currentMonthIndex, currentYear, toComparableMonth]
  );

  const goToToday = useCallback(() => {
    const now = new Date();
    const nextDate = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
    const clamped = clampToRange(nextDate);
    if (toComparableMonth(clamped) === currentMonthIndex) {
      return;
    }
    commitMonthChange(clamped);
  }, [clampToRange, commitMonthChange, currentMonthIndex, toComparableMonth]);

  const clampMonthKey = useCallback(
    (candidateKey: string) => formatMonthKey(clampToRange(parseMonthKey(candidateKey))),
    [clampToRange]
  );

  const getMonthSnapshot = useCallback(
    (monthKeyValue: string) => {
      const targetDate = parseMonthKey(monthKeyValue);
      const clampedDate = clampToRange(targetDate);
      return buildMonthSnapshot(clampedDate);
    },
    [buildMonthSnapshot, clampToRange]
  );

  const getAdjacentMonthKey = useCallback(
    (currentMonthKeyValue: string, delta: number) => {
      if (delta === 0) {
        return clampMonthKey(currentMonthKeyValue);
      }
      const currentDate = parseMonthKey(currentMonthKeyValue);
      const candidateDate = addMonths(currentDate, delta);
      if (!isWithinRange(candidateDate)) {
        const clamped = clampToRange(candidateDate);
        if (toComparableMonth(clamped) === toComparableMonth(currentDate)) {
          return null;
        }
        return formatMonthKey(clamped);
      }
      return formatMonthKey(candidateDate);
    },
    [clampMonthKey, clampToRange, isWithinRange, toComparableMonth]
  );

  const isMonthWithinBounds = useCallback(
    (candidateKey: string) => isWithinRange(parseMonthKey(candidateKey)),
    [isWithinRange]
  );

  const syncVisibleMonth = useCallback(
    (monthKeyValue: string) => {
      const nextDate = parseMonthKey(monthKeyValue);
      const clamped = clampToRange(nextDate);
      commitMonthChange(clamped);
    },
    [clampToRange, commitMonthChange]
  );

  const isMonthDisabled = useCallback(
    (monthIndex: number) => {
      const candidate = new Date(Date.UTC(currentYear, monthIndex, 1));
      return !isWithinRange(candidate);
    },
    [currentYear, isWithinRange]
  );

  const isTodayDisabled = useMemo(() => {
    const now = new Date();
    const todayMonthDate = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
    const clampedToday = clampToRange(todayMonthDate);
    return toComparableMonth(clampedToday) === currentMonthIndex;
  }, [clampToRange, currentMonthIndex, toComparableMonth]);

  const canNavigatePrevMonth = useMemo(
    () => minMonthIndex === null || currentMonthIndex > minMonthIndex,
    [currentMonthIndex, minMonthIndex]
  );
  const canNavigateNextMonth = useMemo(
    () => maxMonthIndex === null || currentMonthIndex < maxMonthIndex,
    [currentMonthIndex, maxMonthIndex]
  );
  const canNavigatePrevYear = canNavigatePrevMonth;
  const canNavigateNextYear = canNavigateNextMonth;

  const navigation: PhotoCalendarNavigationState = useMemo(
    () => ({
      canNavigatePrevMonth,
      canNavigateNextMonth,
      canNavigatePrevYear,
      canNavigateNextYear,
      isTodayDisabled,
      navigateMonth,
      navigateYear,
      navigateToMonth,
      goToToday,
      isMonthDisabled
    }),
    [
      canNavigatePrevMonth,
      canNavigateNextMonth,
      canNavigatePrevYear,
      canNavigateNextYear,
      goToToday,
      isMonthDisabled,
      isTodayDisabled,
      navigateMonth,
      navigateToMonth,
      navigateYear
    ]
  );

  const scroll: PhotoCalendarScrollState = useMemo(
    () => ({
      getMonthSnapshot,
      getAdjacentMonthKey,
      clampMonthKey,
      isMonthWithinBounds,
      syncVisibleMonth
    }),
    [clampMonthKey, getAdjacentMonthKey, getMonthSnapshot, isMonthWithinBounds, syncVisibleMonth]
  );

  return {
    currentYear,
    currentMonth,
    monthDate,
    monthKey: effectiveMonthKey,
    monthLabel,
    monthNames,
    weekdayLabels,
    visibleRange,
    dayStates,
    navigation,
    scroll,
    isControlled
  };
}
