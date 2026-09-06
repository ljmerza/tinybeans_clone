import type { ReactNode } from 'react';
import { PhotoCalendarContextProvider } from '../context/PhotoCalendarContext';
import { usePhotoCalendarState, type PhotoCalendarState, type UsePhotoCalendarStateOptions } from '../hooks/usePhotoCalendarState';

export interface PhotoCalendarRootProps extends UsePhotoCalendarStateOptions {
  children?: ReactNode | ((state: PhotoCalendarState) => ReactNode);
}

export function PhotoCalendarRoot({ children, ...options }: PhotoCalendarRootProps) {
  const state = usePhotoCalendarState(options);
  const content = typeof children === 'function' ? (children as (state: PhotoCalendarState) => ReactNode)(state) : children;

  return <PhotoCalendarContextProvider value={state}>{content}</PhotoCalendarContextProvider>;
}
