import type { HTMLAttributes, ReactNode } from 'react';
import './PhotoCalendar.css';
import { PhotoCalendarRoot } from './primitives/PhotoCalendarRoot';
import { PhotoCalendarNavigation, type NavigationRenderProps } from './primitives/PhotoCalendarNavigation';
import { PhotoCalendarWeekdays, type WeekdayRenderProps } from './primitives/PhotoCalendarWeekdays';
import { PhotoCalendarMonthGrid, type DayRenderProps } from './primitives/PhotoCalendarMonthGrid';
import { PhotoCalendarDay } from './primitives/PhotoCalendarDay';
import { PhotoCalendarScrollView } from './components/PhotoCalendarScrollView';
import type { DayRenderContext, VisibleRange } from './types/calendar';
import type { PhotoEntry } from './types/photo';

export type { DayRenderContext, PhotoEntry, VisibleRange };

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
   * Array of photo entries with datetime and photos array. First entries become day thumbnails.
   */
  entries?: PhotoEntry[];
  /**
   * Maximum thumbnails to show per day before showing a +X overflow badge.
   * Defaults to 1 to mimic the Tinybeans hero-photo layout.
   */
  maxThumbnailsPerDay?: number;
  /**
   * Optional minimum bound for navigation (ISO yyyy-mm).
   */
  minMonthKey?: string;
  /**
   * Optional maximum bound for navigation (ISO yyyy-mm).
   */
  maxMonthKey?: string;
  /**
   * Fired whenever the visible calendar range (including leading/trailing placeholders) changes.
   */
  onRangeChange?: (range: VisibleRange) => void;
  /**
   * Fired when the scroll timeline promotes a new month into the active position.
   */
  onVisibleMonthChange?: (monthKey: string) => void;
  /**
   * Locale override used for weekday/month labels. Defaults to browser locale.
   */
  locale?: string;
  /**
   * Optional timeZone passed to Intl formatters.
   */
  timeZone?: string;
  /**
   * Slot to customise the content rendered inside each day cell.
   */
  renderDayContent?: (context: DayRenderContext) => ReactNode;
  /**
   * New slot to customise the entire day cell button. Receives extended render props.
   */
  renderDay?: (props: DayRenderProps) => ReactNode;
  /**
   * Optional slot to customise navigation controls.
   */
  renderNavigation?: (props: NavigationRenderProps) => ReactNode;
  /**
   * Optional slot to customise weekday headers.
   */
  renderWeekdays?: (props: WeekdayRenderProps) => ReactNode;
  /**
   * Optional slot for dev-only scaffolding while the headless primitives are built.
   */
  children?: ReactNode;
  /**
   * Switch between legacy control navigation and the mobile scroll timeline.
   * Defaults to "controls" for backward compatibility.
   */
  navigationMode?: 'controls' | 'scroll';
  /**
   * Maximum number of months to keep mounted when `navigationMode` is "scroll".
   */
  scrollMaxRenderedMonths?: number;
}

export function PhotoCalendar({
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
  timeZone,
  renderDayContent,
  renderDay,
  renderNavigation,
  renderWeekdays,
  children,
  navigationMode = 'controls',
  scrollMaxRenderedMonths,
  ...rest
}: PhotoCalendarProps) {
  const calendarOptions = {
    monthKey,
    defaultMonthKey,
    onMonthChange,
    onDaySelect,
    firstDayOfWeek,
    entries,
    maxThumbnailsPerDay,
    minMonthKey,
    maxMonthKey,
    onRangeChange,
    onVisibleMonthChange,
    locale,
    timeZone
  };
  const resolvedRenderDay = renderDay
    ? renderDay
    : renderDayContent
      ? (props: DayRenderProps) => (
          <PhotoCalendarDay day={{ ...props, defaultContent: renderDayContent(props) ?? props.defaultContent }} />
        )
      : undefined;
  const resolvedNavigation = renderNavigation
      ? (props: NavigationRenderProps) => renderNavigation(props)
    : undefined;
  const resolvedWeekdays = renderWeekdays
    ? (props: WeekdayRenderProps) => renderWeekdays(props)
    : undefined;

  if (navigationMode === 'scroll') {
    return (
      <PhotoCalendarRoot {...calendarOptions}>
        {() => (
          <PhotoCalendarScrollView
            {...rest}
            renderDay={resolvedRenderDay}
            renderWeekdays={resolvedWeekdays}
            maxRenderedMonths={scrollMaxRenderedMonths}
          >
            {children}
          </PhotoCalendarScrollView>
        )}
      </PhotoCalendarRoot>
    );
  }

  return (
    <PhotoCalendarRoot {...calendarOptions}>
      {(state) => (
        <div role="grid" aria-label={`Photo calendar for ${state.monthLabel}`} data-view="calendar" {...rest}>
          <PhotoCalendarNavigation>{resolvedNavigation}</PhotoCalendarNavigation>
          <PhotoCalendarWeekdays>{resolvedWeekdays}</PhotoCalendarWeekdays>
          <PhotoCalendarMonthGrid renderDay={resolvedRenderDay} />
          {children}
        </div>
      )}
    </PhotoCalendarRoot>
  );
}
