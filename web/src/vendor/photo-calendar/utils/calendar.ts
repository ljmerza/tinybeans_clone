export interface CalendarCell {
  date: Date;
  isoDate: string;
  day: number;
  inCurrentMonth: boolean;
}

export function parseMonthKey(value?: string): Date {
  if (!value) {
    const now = new Date();
    return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  }

  const [yearStr = '', monthStr = ''] = value.split('-');
  const year = Number(yearStr);
  const monthIndex = Number(monthStr) - 1;

  if (Number.isNaN(year) || Number.isNaN(monthIndex) || monthIndex < 0 || monthIndex > 11) {
    const now = new Date();
    return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  }

  return new Date(Date.UTC(year, monthIndex, 1));
}

function toISODate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function createCalendarCells(monthDate: Date, firstDayOfWeek: number): CalendarCell[] {
  const utcYear = monthDate.getUTCFullYear();
  const utcMonth = monthDate.getUTCMonth();
  const firstOfMonth = new Date(Date.UTC(utcYear, utcMonth, 1));
  const firstDay = firstOfMonth.getUTCDay();
  const leadingPlaceholders = (firstDay - firstDayOfWeek + 7) % 7;
  const daysInMonth = new Date(Date.UTC(utcYear, utcMonth + 1, 0)).getUTCDate();
  const totalCells = Math.ceil((leadingPlaceholders + daysInMonth) / 7) * 7;

  const firstVisible = new Date(Date.UTC(utcYear, utcMonth, 1 - leadingPlaceholders));
  const cells: CalendarCell[] = [];

  for (let index = 0; index < totalCells; index += 1) {
    const date = new Date(
      Date.UTC(firstVisible.getUTCFullYear(), firstVisible.getUTCMonth(), firstVisible.getUTCDate() + index)
    );
    cells.push({
      date,
      isoDate: toISODate(date),
      day: date.getUTCDate(),
      inCurrentMonth: date.getUTCMonth() === utcMonth
    });
  }

  return cells;
}

export function formatMonthKey(date: Date): string {
  const month = `${date.getUTCMonth() + 1}`.padStart(2, '0');
  return `${date.getUTCFullYear()}-${month}`;
}

export function addMonths(date: Date, offset: number): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + offset, 1));
}

export function getVisibleRange(cells: CalendarCell[]): { start: Date; end: Date } | null {
  if (cells.length === 0) {
    return null;
  }

  const start = cells[0].date;
  const end = cells[cells.length - 1].date;

  return {
    start: new Date(start.getTime()),
    end: new Date(end.getTime())
  };
}
