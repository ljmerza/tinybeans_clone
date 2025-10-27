import { useMemo, useState } from 'react';
import type { HTMLAttributes, ReactNode } from 'react';
import './PhotoCalendar.css';

export interface PhotoEntry {
  /**
   * ISO datetime string indicating when this photo was taken
   */
  datetime: string;
  /**
   * Array of photo URLs, the first one will be displayed in the calendar
   */
  photos: string[];
}

export interface PhotoCalendarProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * Visible month identifier (ISO yyyy-mm) used for quick visual validation while the real library takes shape.
   */
  monthKey?: string;
  /**
   * Default month identifier used when the component manages its own state.
   */
  defaultMonthKey?: string;
  /**
   * Fired when navigation arrows request a month change. Receives ISO yyyy-mm strings.
   */
  onMonthChange?: (nextMonthKey: string) => void;
  /**
   * Fired when the user activates a day cell. Receives the ISO date (yyyy-mm-dd) and native `Date` instance.
   */
  onDaySelect?: (info: { isoDate: string; date: Date }) => void;
  /**
   * Index of the first day of the week (0 = Sunday, 1 = Monday, ...).
   * Keeps the placeholder grid alignment consistent with locale expectations.
   */
  firstDayOfWeek?: 0 | 1 | 2 | 3 | 4 | 5 | 6;
  /**
   * Array of photo entries with datetime and photos array. First photo will be displayed.
   */
  entries?: PhotoEntry[];
  /**
   * Optional slot for dev-only scaffolding while the headless primitives are built.
   */
  children?: ReactNode;
}

type CalendarCell = { day: number } | null;

function parseMonthKey(value?: string): Date {
  if (!value) {
    const now = new Date();
    return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  }

  const [yearStr = '', monthStr = ''] = value.split('-');
  const year = Number(yearStr);
  const monthIndex = Number(monthStr) - 1;

  if (Number.isNaN(year) || Number.isNaN(monthIndex) || monthIndex < 0 || monthIndex > 11) {
    const now = new Date();
    return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  }

  return new Date(Date.UTC(year, monthIndex, 1));
}

function createCalendarCells(monthDate: Date, firstDayOfWeek: number): CalendarCell[] {
  const utcYear = monthDate.getUTCFullYear();
  const utcMonth = monthDate.getUTCMonth();
  const firstOfMonth = new Date(Date.UTC(utcYear, utcMonth, 1));
  const firstDay = firstOfMonth.getUTCDay();
  const leadingPlaceholders = (firstDay - firstDayOfWeek + 7) % 7;
  const daysInMonth = new Date(Date.UTC(utcYear, utcMonth + 1, 0)).getUTCDate();
  const totalCells = Math.ceil((leadingPlaceholders + daysInMonth) / 7) * 7;

  return Array.from<CalendarCell>({ length: totalCells }, (_, index) => {
    if (index < leadingPlaceholders) {
      return null;
    }

    const dayNumber = index - leadingPlaceholders + 1;
    if (dayNumber > daysInMonth) {
      return null;
    }

    return { day: dayNumber };
  });
}

function formatMonthKey(date: Date): string {
  const month = `${date.getUTCMonth() + 1}`.padStart(2, '0');
  return `${date.getUTCFullYear()}-${month}`;
}

function addMonths(date: Date, offset: number): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + offset, 1));
}

const MONTH_NAMES_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function PhotoCalendar({
  monthKey,
  defaultMonthKey,
  onMonthChange,
  onDaySelect,
  firstDayOfWeek = 0,
  entries,
  children,
  ...rest
}: PhotoCalendarProps) {
  const isControlled = monthKey !== undefined;
  const [internalMonthKey, setInternalMonthKey] = useState(() => formatMonthKey(parseMonthKey(defaultMonthKey)));

  const effectiveMonthKey = isControlled ? (monthKey as string) : internalMonthKey;
  const monthDate = useMemo(() => parseMonthKey(effectiveMonthKey), [effectiveMonthKey]);
  const currentYear = monthDate.getUTCFullYear();
  const currentMonth = monthDate.getUTCMonth();
  const monthLabel = monthDate.toLocaleString(undefined, { month: 'long', year: 'numeric' });
  const calendarCells = useMemo(() => createCalendarCells(monthDate, firstDayOfWeek), [monthDate, firstDayOfWeek]);

  // Convert entries array to a map for quick lookup by date
  const photosByDate = useMemo(() => {
    if (!entries) return {};
    const map: Record<string, string> = {};
    entries.forEach((entry) => {
      if (entry.photos.length > 0) {
        // Extract date portion from ISO datetime string (yyyy-mm-dd)
        const dateKey = entry.datetime.slice(0, 10);
        map[dateKey] = entry.photos[0];
      }
    });
    return map;
  }, [entries]);

  const navigateToMonth = (monthIndex: number) => {
    const nextDate = new Date(Date.UTC(currentYear, monthIndex, 1));
    const nextKey = formatMonthKey(nextDate);
    onMonthChange?.(nextKey);
    if (!isControlled) {
      setInternalMonthKey(nextKey);
    }
  };

  const navigateMonth = (delta: number) => {
    const nextDate = addMonths(monthDate, delta);
    const nextKey = formatMonthKey(nextDate);
    onMonthChange?.(nextKey);
    if (!isControlled) {
      setInternalMonthKey(nextKey);
    }
  };

  const navigateYear = (delta: number) => {
    const nextDate = new Date(Date.UTC(currentYear + delta, currentMonth, 1));
    const nextKey = formatMonthKey(nextDate);
    onMonthChange?.(nextKey);
    if (!isControlled) {
      setInternalMonthKey(nextKey);
    }
  };

  const goToToday = () => {
    const now = new Date();
    const nextDate = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
    const nextKey = formatMonthKey(nextDate);
    onMonthChange?.(nextKey);
    if (!isControlled) {
      setInternalMonthKey(nextKey);
    }
  };

  return (
    <div role="grid" aria-label={`Photo calendar prototype for ${monthLabel}`} data-view="calendar" {...rest}>
      <div className="calendar-banner">
        <div className="calendar-year-row">
          <strong className="calendar-year">{currentYear}</strong>
          <button
            type="button"
            className="today-button"
            aria-label="Go to current month"
            onClick={goToToday}
          >
            Today
          </button>
        </div>
        <div className="month-chips-row">
          <button
            type="button"
            className="nav-button nav-button--prev nav-button--year"
            aria-label="Previous year"
            onClick={() => navigateYear(-1)}
          >
            ‹
          </button>
          <button
            type="button"
            className="nav-button nav-button--prev nav-button--month"
            aria-label="Previous month"
            onClick={() => navigateMonth(-1)}
          >
            ‹
          </button>
          <div className="month-chips">
            {MONTH_NAMES_SHORT.map((monthName, monthIndex) => (
              <button
                key={monthName}
                type="button"
                className={`month-chip ${monthIndex === currentMonth ? 'month-chip--active' : ''}`}
                aria-label={`Go to ${monthName} ${currentYear}`}
                aria-current={monthIndex === currentMonth ? 'date' : undefined}
                onClick={() => navigateToMonth(monthIndex)}
              >
                {monthName}
              </button>
            ))}
          </div>
          <div className="month-label-mobile">
            <strong>{monthLabel}</strong>
          </div>
          <button
            type="button"
            className="nav-button nav-button--next nav-button--year"
            aria-label="Next year"
            onClick={() => navigateYear(1)}
          >
            ›
          </button>
          <button
            type="button"
            className="nav-button nav-button--next nav-button--month"
            aria-label="Next month"
            onClick={() => navigateMonth(1)}
          >
            ›
          </button>
          <button
            type="button"
            className="today-button-icon"
            aria-label="Go to current month"
            onClick={goToToday}
          >
            📅
          </button>
        </div>
      </div>
      <div className="calendar-grid">
        {calendarCells.map((cell, index) => {
          const isPlaceholder = cell === null;
          const dateForCell =
            !isPlaceholder && cell
              ? new Date(Date.UTC(monthDate.getUTCFullYear(), monthDate.getUTCMonth(), cell.day))
              : undefined;

          const isoDate = dateForCell?.toISOString().slice(0, 10);
          const photoUrl = isoDate ? photosByDate[isoDate] : undefined;

          return (
            <button
              key={`calendar-cell-${index}`}
              type="button"
              className={`calendar-cell ${photoUrl ? 'calendar-cell--has-photo' : ''}`}
              role="gridcell"
              aria-disabled={isPlaceholder}
              disabled={isPlaceholder}
              onClick={() => {
                if (!isPlaceholder && dateForCell && isoDate) {
                  onDaySelect?.({
                    isoDate,
                    date: dateForCell
                  });
                }
              }}
            >
              {photoUrl && (
                <img
                  src={photoUrl}
                  alt={`Photo for ${isoDate}`}
                  className="calendar-cell-image"
                />
              )}
              {!isPlaceholder && <span className="cell-label">{cell.day}</span>}
            </button>
          );
        })}
      </div>
      {children}
    </div>
  );
}
