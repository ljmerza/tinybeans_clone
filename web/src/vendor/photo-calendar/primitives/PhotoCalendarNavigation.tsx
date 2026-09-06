import type { ReactNode } from 'react';
import { CalendarBanner } from '../components/CalendarBanner';
import { usePhotoCalendarContext } from '../context/PhotoCalendarContext';
import type { PhotoCalendarNavigationState } from '../hooks/usePhotoCalendarState';

export interface NavigationRenderProps extends PhotoCalendarNavigationState {
  currentYear: number;
  currentMonth: number;
  monthLabel: string;
  monthNames: ReadonlyArray<string>;
}

export interface PhotoCalendarNavigationProps {
  /**
   * Provide custom navigation markup using render props.
   * The default renders the built-in CalendarBanner.
   */
  children?: (props: NavigationRenderProps) => ReactNode;
}

export function PhotoCalendarNavigation({ children }: PhotoCalendarNavigationProps) {
  const { currentYear, currentMonth, monthLabel, monthNames, navigation } = usePhotoCalendarContext('PhotoCalendarNavigation');
  const renderProps: NavigationRenderProps = {
    ...navigation,
    currentYear,
    currentMonth,
    monthLabel,
    monthNames
  };

  if (children) {
    return <>{children(renderProps)}</>;
  }

  return <CalendarBanner />;
}
