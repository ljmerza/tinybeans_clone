import { useMemo, useState } from 'react';
import type { HTMLAttributes, ReactNode } from 'react';

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

export function PhotoCalendar({
  monthKey,
  defaultMonthKey,
  onMonthChange,
  onDaySelect,
  firstDayOfWeek = 0,
  children,
  ...rest
}: PhotoCalendarProps) {
  const isControlled = monthKey !== undefined;
  const [internalMonthKey, setInternalMonthKey] = useState(() => formatMonthKey(parseMonthKey(defaultMonthKey)));

  const effectiveMonthKey = isControlled ? (monthKey as string) : internalMonthKey;
  const monthDate = useMemo(() => parseMonthKey(effectiveMonthKey), [effectiveMonthKey]);
  const monthLabel = monthDate.toLocaleString(undefined, { month: 'long', year: 'numeric' });
  const calendarCells = useMemo(() => createCalendarCells(monthDate, firstDayOfWeek), [monthDate, firstDayOfWeek]);

  const navigateMonth = (delta: number) => {
    const nextDate = addMonths(monthDate, delta);
    const nextKey = formatMonthKey(nextDate);
    onMonthChange?.(nextKey);
    if (!isControlled) {
      setInternalMonthKey(nextKey);
    }
  };

  return (
    <div role="grid" aria-label={`Photo calendar prototype for ${monthLabel}`} data-view="calendar" {...rest}>
      <div className="calendar-banner">
        <button
          type="button"
          className="nav-button nav-button--prev"
          aria-label="Previous month"
          onClick={() => navigateMonth(-1)}
        >
          ‹
        </button>
        <strong>{monthLabel}</strong>
        <button
          type="button"
          className="nav-button nav-button--next"
          aria-label="Next month"
          onClick={() => navigateMonth(1)}
        >
          ›
        </button>
      </div>
      <div className="calendar-grid">
        {calendarCells.map((cell, index) => {
          const isPlaceholder = cell === null;
          const dateForCell =
            !isPlaceholder && cell
              ? new Date(Date.UTC(monthDate.getUTCFullYear(), monthDate.getUTCMonth(), cell.day))
              : undefined;

          return (
            <button
              key={`calendar-cell-${index}`}
              type="button"
              className="calendar-cell"
              role="gridcell"
              aria-disabled={isPlaceholder}
              disabled={isPlaceholder}
              onClick={() => {
                if (!isPlaceholder && dateForCell) {
                  onDaySelect?.({
                    isoDate: dateForCell.toISOString().slice(0, 10),
                    date: dateForCell
                  });
                }
              }}
            >
              {!isPlaceholder && <span className="cell-label">{cell.day}</span>}
            </button>
          );
        })}
      </div>
      {children}
    </div>
  );
}
