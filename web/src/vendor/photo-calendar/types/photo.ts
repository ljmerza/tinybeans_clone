/**
 * Represents a single photo entry used by the calendar.
 * The first photo URL in the array will be displayed as the day's preview.
 */
export interface PhotoEntry {
  /**
   * ISO datetime string indicating when this photo was taken
   */
  datetime: string;
  /**
   * Array of photo URLs, the first one will be displayed in the calendar
   */
  photos: string[];
}
