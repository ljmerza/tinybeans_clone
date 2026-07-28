import type { ReactNode } from 'react';
import { createContext, useContext } from 'react';
import type { PhotoCalendarState } from '../hooks/usePhotoCalendarState';

interface PhotoCalendarContextValue extends PhotoCalendarState {}

const PhotoCalendarContext = createContext<PhotoCalendarContextValue | null>(null);

export interface PhotoCalendarContextProviderProps {
  value: PhotoCalendarState;
  children: ReactNode;
}

export function PhotoCalendarContextProvider({ value, children }: PhotoCalendarContextProviderProps) {
  return <PhotoCalendarContext.Provider value={value}>{children}</PhotoCalendarContext.Provider>;
}

export function usePhotoCalendarContext(componentName = 'usePhotoCalendarContext'): PhotoCalendarState {
  const context = useContext(PhotoCalendarContext);

  if (!context) {
    throw new Error(`${componentName} must be used within a <PhotoCalendarRoot> or <PhotoCalendarContextProvider>.`);
  }

  return context;
}
