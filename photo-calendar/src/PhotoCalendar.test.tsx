import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PhotoCalendar } from './PhotoCalendar';

describe('PhotoCalendar', () => {
  it('renders a placeholder grid and label', () => {
    render(<PhotoCalendar monthKey="2030-01" />);

    expect(() => screen.getByRole('grid', { name: /2030/i })).not.toThrow();
    const cells = screen.getAllByRole('gridcell');
    expect(cells.length).toBe(35);
    expect(cells[0]).toHaveAttribute('aria-disabled', 'true');
    expect(cells[2]).toHaveTextContent('1');
  });

  it('respects the firstDayOfWeek offset for alignment', () => {
    render(<PhotoCalendar monthKey="2030-01" firstDayOfWeek={1} />);

    const cells = screen.getAllByRole('gridcell');
    expect(cells[0]).toHaveAttribute('aria-disabled', 'true');
    expect(cells[1]).toHaveTextContent('1');
  });

  it('fires onDaySelect with ISO date and Date object', () => {
    const spy = vi.fn();
    render(<PhotoCalendar monthKey="2030-01" onDaySelect={spy} />);

    const cells = screen.getAllByRole('gridcell');
    fireEvent.click(cells[2]);

    expect(spy).toHaveBeenCalledTimes(1);
    expect(spy.mock.calls[0][0].isoDate).toBe('2030-01-01');
    expect(spy.mock.calls[0][0].date).toBeInstanceOf(Date);
  });

  it('advances months internally when uncontrolled', () => {
    render(<PhotoCalendar defaultMonthKey="2030-01" />);
    const nextButton = screen.getByLabelText(/next month/i);

    fireEvent.click(nextButton);

    const febLabel = new Date(Date.UTC(2030, 1, 1)).toLocaleString(undefined, { month: 'long', year: 'numeric' });
    expect(screen.getByText(febLabel)).toBeInTheDocument();
  });

  it('emits onMonthChange when controlled', () => {
    const spy = vi.fn();
    render(<PhotoCalendar monthKey="2030-01" onMonthChange={spy} />);

    fireEvent.click(screen.getByLabelText(/next month/i));
    expect(spy).toHaveBeenCalledWith('2030-02');
  });

  it('updates onDaySelect after month navigation', () => {
    const spy = vi.fn();
    render(<PhotoCalendar defaultMonthKey="2030-01" onDaySelect={spy} />);

    fireEvent.click(screen.getByLabelText(/next month/i));
    const cells = screen.getAllByRole('gridcell');
    const firstEnabled = cells.find((cell) => !cell.hasAttribute('aria-disabled'));
    fireEvent.click(firstEnabled!);

    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ isoDate: '2030-02-01' }));
  });
});
