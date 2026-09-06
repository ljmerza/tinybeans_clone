import type { DayRenderProps } from '../types/calendar';

export interface PhotoCalendarDayProps {
  day: DayRenderProps;
  className?: string;
}

export function PhotoCalendarDay({ day, className }: PhotoCalendarDayProps) {
  const {
    defaultContent,
    ariaLabel,
    isSelectable,
    isCurrentMonth,
    isToday,
    visibleThumbnails,
    selectDay
  } = day;
  const combinedClassName = [
    'calendar-cell',
    isCurrentMonth ? '' : 'calendar-cell--placeholder',
    isToday ? 'calendar-cell--today' : '',
    visibleThumbnails.length > 0 ? 'calendar-cell--has-photo' : '',
    className ?? ''
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      type="button"
      className={combinedClassName}
      role="gridcell"
      aria-label={ariaLabel}
      aria-disabled={!isSelectable}
      disabled={!isSelectable}
      onClick={selectDay}
    >
      {defaultContent}
    </button>
  );
}
