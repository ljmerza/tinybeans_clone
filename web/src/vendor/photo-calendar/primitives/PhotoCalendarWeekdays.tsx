import type { ReactNode } from 'react';
import { usePhotoCalendarContext } from '../context/PhotoCalendarContext';

export interface WeekdayRenderProps {
  shortLabels: ReadonlyArray<string>;
  longLabels: ReadonlyArray<string>;
}

export interface PhotoCalendarWeekdaysProps {
  className?: string;
  /**
   * Optional render prop to customise weekday header markup.
   * Defaults to rendering span elements matching the current CSS classes.
   */
  children?: (props: WeekdayRenderProps) => ReactNode;
}

export function PhotoCalendarWeekdays({ className = 'calendar-weekdays', children }: PhotoCalendarWeekdaysProps) {
  const { weekdayLabels } = usePhotoCalendarContext('PhotoCalendarWeekdays');
  const renderProps: WeekdayRenderProps = {
    shortLabels: weekdayLabels.short,
    longLabels: weekdayLabels.long
  };

  if (children) {
    return <>{children(renderProps)}</>;
  }

  return (
    <div className={className} role="row">
      {weekdayLabels.short.map((label, index) => (
        <span
          key={`${label}-${index}`}
          className="calendar-weekday"
          role="columnheader"
          aria-label={weekdayLabels.long[index]}
        >
          {label}
        </span>
      ))}
    </div>
  );
}
