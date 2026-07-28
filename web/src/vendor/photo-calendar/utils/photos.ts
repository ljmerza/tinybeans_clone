import type { PhotoEntry } from '../types/photo';

/**
 * Converts a list of entries into a quick lookup map keyed by ISO date (yyyy-mm-dd).
 */
export function createPhotosByDateMap(entries?: PhotoEntry[]): Record<string, string[]> {
  if (!entries || entries.length === 0) {
    return {};
  }

  return entries.reduce<Record<string, string[]>>((map, entry) => {
    if (entry.photos.length > 0) {
      const isoDate = entry.datetime.slice(0, 10);
      const existing = map[isoDate] ?? [];
      map[isoDate] = existing.concat(entry.photos);
    }
    return map;
  }, {});
}
