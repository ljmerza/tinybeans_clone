import type { ReactNode } from 'react';
import { usePhotoCalendarContext } from '../context/PhotoCalendarContext';

export function PhotoCalendarNavigationLayout({ children }: { children: ReactNode }) {
  return <div className="calendar-banner">{children}</div>;
}

export function PhotoCalendarNavigationYearHeading() {
  const { currentYear } = usePhotoCalendarContext('PhotoCalendarNavigationYearHeading');
  return (
    <div className="calendar-year-row">
      <strong className="calendar-year">{currentYear}</strong>
    </div>
  );
}

export function PhotoCalendarNavigationControls({ children }: { children: ReactNode }) {
  return <div className="month-chips-row">{children}</div>;
}

const useNavigation = (componentName: string) => {
  const { navigation } = usePhotoCalendarContext(componentName);
  return navigation;
};

export function PhotoCalendarNavigationPrevYearButton() {
  const navigation = useNavigation('PhotoCalendarNavigationPrevYearButton');
  return (
    <button
      type="button"
      className="nav-button nav-button--prev nav-button--year"
      aria-label="Previous year"
      onClick={() => navigation.navigateYear(-1)}
      disabled={!navigation.canNavigatePrevYear}
    >
      <span aria-hidden="true" className="nav-button-icon">‹</span>
      <span className="nav-button-label">Previous year</span>
    </button>
  );
}

export function PhotoCalendarNavigationNextYearButton() {
  const navigation = useNavigation('PhotoCalendarNavigationNextYearButton');
  return (
    <button
      type="button"
      className="nav-button nav-button--next nav-button--year"
      aria-label="Next year"
      onClick={() => navigation.navigateYear(1)}
      disabled={!navigation.canNavigateNextYear}
    >
      <span aria-hidden="true" className="nav-button-icon">›</span>
      <span className="nav-button-label">Next year</span>
    </button>
  );
}

export function PhotoCalendarNavigationPrevMonthButton() {
  const navigation = useNavigation('PhotoCalendarNavigationPrevMonthButton');
  return (
    <button
      type="button"
      className="nav-button nav-button--prev nav-button--month"
      aria-label="Previous month"
      onClick={() => navigation.navigateMonth(-1)}
      disabled={!navigation.canNavigatePrevMonth}
    >
      <span aria-hidden="true" className="nav-button-icon">‹</span>
      <span className="nav-button-label">Previous month</span>
    </button>
  );
}

export function PhotoCalendarNavigationNextMonthButton() {
  const navigation = useNavigation('PhotoCalendarNavigationNextMonthButton');
  return (
    <button
      type="button"
      className="nav-button nav-button--next nav-button--month"
      aria-label="Next month"
      onClick={() => navigation.navigateMonth(1)}
      disabled={!navigation.canNavigateNextMonth}
    >
      <span aria-hidden="true" className="nav-button-icon">›</span>
      <span className="nav-button-label">Next month</span>
    </button>
  );
}

export function PhotoCalendarNavigationMonthChips() {
  const { currentYear, currentMonth, monthNames } = usePhotoCalendarContext('PhotoCalendarNavigationMonthChips');
  const navigation = useNavigation('PhotoCalendarNavigationMonthChips');

  return (
    <div className="month-chips">
      {monthNames.map((monthName, monthIndex) => (
        <button
          key={monthName}
          type="button"
          className={`month-chip ${monthIndex === currentMonth ? 'month-chip--active' : ''}`}
          aria-label={`Go to ${monthName} ${currentYear}`}
          aria-current={monthIndex === currentMonth ? 'date' : undefined}
          onClick={() => navigation.navigateToMonth(monthIndex)}
          disabled={navigation.isMonthDisabled(monthIndex)}
        >
          {monthName}
        </button>
      ))}
    </div>
  );
}

export function PhotoCalendarNavigationMonthLabelMobile() {
  const { monthLabel } = usePhotoCalendarContext('PhotoCalendarNavigationMonthLabelMobile');
  return (
    <div className="month-label-mobile">
      <strong>{monthLabel}</strong>
    </div>
  );
}

export function PhotoCalendarNavigationTodayButton() {
  const navigation = useNavigation('PhotoCalendarNavigationTodayButton');
  return (
    <button
      type="button"
      className="today-button-icon"
      aria-label="Go to current month"
      onClick={navigation.goToToday}
      disabled={navigation.isTodayDisabled}
    >
      <span aria-hidden="true">📅</span>
    </button>
  );
}

export function CalendarBanner() {
  return (
    <PhotoCalendarNavigationLayout>
      <PhotoCalendarNavigationYearHeading />
      <PhotoCalendarNavigationControls>
        <PhotoCalendarNavigationPrevYearButton />
        <PhotoCalendarNavigationPrevMonthButton />
        <PhotoCalendarNavigationMonthChips />
        <PhotoCalendarNavigationMonthLabelMobile />
        <PhotoCalendarNavigationNextYearButton />
        <PhotoCalendarNavigationNextMonthButton />
        <PhotoCalendarNavigationTodayButton />
      </PhotoCalendarNavigationControls>
    </PhotoCalendarNavigationLayout>
  );
}
