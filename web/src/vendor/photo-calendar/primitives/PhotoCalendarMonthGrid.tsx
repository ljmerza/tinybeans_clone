import type { ReactNode } from 'react';
import { Fragment } from 'react';
import { usePhotoCalendarContext } from '../context/PhotoCalendarContext';
import { PhotoCalendarDay } from './PhotoCalendarDay';
import type { DayRenderProps } from '../types/calendar';
import type { PhotoCalendarDayState } from '../hooks/usePhotoCalendarState';

export type { DayRenderProps } from '../types/calendar';

export interface PhotoCalendarMonthGridProps {
  className?: string;
  /**
   * Custom render function for the contents inside each day button.
   */
  renderDay?: (props: DayRenderProps) => ReactNode;
  /**
   * Optional override for day states, enabling multi-month rendering scenarios.
   */
  dayStates?: PhotoCalendarDayState[];
}

export function PhotoCalendarMonthGrid({ className = 'calendar-grid', renderDay, dayStates }: PhotoCalendarMonthGridProps) {
  const { dayStates: contextDayStates } = usePhotoCalendarContext('PhotoCalendarMonthGrid');
  const resolvedDayStates = dayStates ?? contextDayStates;

  return (
    <div className={className}>
      {resolvedDayStates.map((dayState, index) => {
        const { cell, context, ariaLabel, isSelectable } = dayState;
        const { visibleThumbnails, overflow } = context;
        const defaultContent = (
          <>
            {visibleThumbnails.length > 0 && (
              <div className="calendar-cell-thumbnails" data-count={visibleThumbnails.length}>
                {visibleThumbnails.map((url, thumbIndex) => (
                  <img
                    key={`${cell.isoDate}-${thumbIndex}`}
                    src={url}
                    alt=""
                    loading="lazy"
                    decoding="async"
                    className="calendar-cell-image"
                  />
                ))}
                {overflow > 0 && <span className="calendar-cell-overflow">+{overflow}</span>}
              </div>
            )}
            <span className="cell-label">{cell.day}</span>
          </>
        );
        const renderProps: DayRenderProps = {
          ...context,
          defaultContent,
          ariaLabel,
          isSelectable
        };

        if (renderDay) {
          return (
            <Fragment key={`calendar-cell-${index}`}>
              {renderDay(renderProps)}
            </Fragment>
          );
        }

        return <PhotoCalendarDay key={`calendar-cell-${index}`} day={renderProps} />;
      })}
    </div>
  );
}
