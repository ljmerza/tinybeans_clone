import type { ReactNode } from 'react';

export interface VisibleRange {
  start: Date;
  end: Date;
  startIso: string;
  endIso: string;
}

export interface DayRenderContext {
  date: Date;
  isoDate: string;
  day: number;
  isCurrentMonth: boolean;
  isToday: boolean;
  photos: string[];
  visibleThumbnails: string[];
  overflow: number;
  selectDay: () => void;
  defaultContent?: ReactNode;
}

export interface DayRenderProps extends DayRenderContext {
  defaultContent: ReactNode;
  ariaLabel: string;
  isSelectable: boolean;
}
