import { useState } from "react";

/**
 * Small plain-SVG charts for the person page: one series each, in the theme's
 * primary color, with a recessive grid and a hover readout per mark.
 * They scale to their container's width through the viewBox.
 */

const WIDTH = 320;
const HEIGHT = 160;
const PAD = { top: 12, right: 12, bottom: 22, left: 48 };
const PLOT_WIDTH = WIDTH - PAD.left - PAD.right;
const PLOT_HEIGHT = HEIGHT - PAD.top - PAD.bottom;

export interface ChartPoint {
	x: number;
	y: number;
	/** Read out on hover, e.g. "Jun 1, 2025: 13 lb 13 oz". */
	label: string;
}

export interface LineChartProps {
	points: ChartPoint[];
	formatX: (x: number) => string;
	formatY: (y: number) => string;
	/** Names the chart for screen readers, e.g. "Weight over time". */
	ariaLabel: string;
	/** Shown instead of the chart when there are no points. */
	emptyMessage: string;
}

/** A domain that never collapses to zero width, padded a little at both ends. */
function domain(values: number[], padRatio: number): [number, number] {
	const min = Math.min(...values);
	const max = Math.max(...values);
	if (min === max) {
		const pad = Math.abs(min) * 0.1 || 1;
		return [min - pad, max + pad];
	}
	const pad = (max - min) * padRatio;
	return [min - pad, max + pad];
}

function scale([d0, d1]: [number, number], r0: number, r1: number) {
	return (value: number) => r0 + ((value - d0) / (d1 - d0)) * (r1 - r0);
}

/** Readout box above a mark, kept inside the chart. */
function Readout({ x, y, label }: { x: number; y: number; label: string }) {
	const width = Math.min(label.length * 5.6 + 12, WIDTH - 4);
	const left = Math.min(Math.max(x - width / 2, 2), WIDTH - width - 2);
	const top = Math.max(y - 26, 0);
	return (
		<g pointerEvents="none" data-testid="chart-readout">
			<rect
				x={left}
				y={top}
				width={width}
				height={18}
				rx={4}
				className="fill-popover stroke-border"
			/>
			<text
				x={left + width / 2}
				y={top + 12.5}
				textAnchor="middle"
				fontSize={10}
				className="fill-popover-foreground"
			>
				{label}
			</text>
		</g>
	);
}

/**
 * One measure over time (or age). No points shows `emptyMessage`; one point
 * is a lone marker; more are joined by a line.
 */
export function LineChart({
	points,
	formatX,
	formatY,
	ariaLabel,
	emptyMessage,
}: LineChartProps) {
	const [active, setActive] = useState<number | null>(null);

	if (points.length === 0) {
		return (
			<p className="py-8 text-center text-sm text-muted-foreground">
				{emptyMessage}
			</p>
		);
	}

	const xDomain = domain(
		points.map((point) => point.x),
		0.04,
	);
	const yDomain = domain(
		points.map((point) => point.y),
		0.1,
	);
	const sx = scale(xDomain, PAD.left, PAD.left + PLOT_WIDTH);
	const sy = scale(yDomain, PAD.top + PLOT_HEIGHT, PAD.top);
	const yTicks = [0, 0.5, 1].map(
		(t) => yDomain[0] + t * (yDomain[1] - yDomain[0]),
	);
	const first = points[0];
	const last = points[points.length - 1];
	const xTicks = first === last ? [first.x] : [first.x, last.x];
	const linePath = points
		.map(
			(point, i) =>
				`${i === 0 ? "M" : "L"}${sx(point.x).toFixed(1)},${sy(point.y).toFixed(1)}`,
		)
		.join(" ");
	const activePoint = active === null ? null : points[active];

	return (
		<svg
			viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
			role="img"
			aria-label={ariaLabel}
			className="h-auto w-full text-primary"
		>
			{yTicks.map((tick) => (
				<g key={tick}>
					<line
						x1={PAD.left}
						x2={PAD.left + PLOT_WIDTH}
						y1={sy(tick)}
						y2={sy(tick)}
						className="stroke-border"
						strokeWidth={1}
					/>
					<text
						x={PAD.left - 6}
						y={sy(tick) + 3}
						textAnchor="end"
						fontSize={10}
						className="fill-muted-foreground"
					>
						{formatY(tick)}
					</text>
				</g>
			))}
			{xTicks.map((tick, i) => (
				<text
					key={tick}
					x={sx(tick)}
					y={HEIGHT - 6}
					textAnchor={
						xTicks.length === 1 ? "middle" : i === 0 ? "start" : "end"
					}
					fontSize={10}
					className="fill-muted-foreground"
				>
					{formatX(tick)}
				</text>
			))}
			{points.length > 1 && (
				<path
					d={linePath}
					fill="none"
					stroke="currentColor"
					strokeWidth={2}
					strokeLinejoin="round"
					strokeLinecap="round"
					data-testid="chart-line"
				/>
			)}
			{points.map((point, i) => (
				<circle
					key={`${point.x}-${i}`}
					cx={sx(point.x)}
					cy={sy(point.y)}
					r={4}
					fill="currentColor"
					strokeWidth={2}
					className="stroke-card"
					data-testid="chart-point"
				/>
			))}
			{/* Hover targets bigger than the marks. The list below the chart
			    carries the same values for keyboard and screen readers. */}
			{points.map((point, i) => (
				<circle
					key={`hit-${point.x}-${i}`}
					cx={sx(point.x)}
					cy={sy(point.y)}
					r={10}
					fill="transparent"
					onPointerEnter={() => setActive(i)}
					onPointerLeave={() => setActive(null)}
				>
					<title>{point.label}</title>
				</circle>
			))}
			{activePoint && (
				<Readout
					x={sx(activePoint.x)}
					y={sy(activePoint.y)}
					label={activePoint.label}
				/>
			)}
		</svg>
	);
}

export interface BarDatum {
	key: string;
	value: number;
	/** Under the bar, e.g. "J". */
	tick: string;
	/** Read out on hover, e.g. "June 2026: 4 posts". */
	label: string;
}

export interface BarChartProps {
	bars: BarDatum[];
	ariaLabel: string;
}

const BAR_HEIGHT = 96;
const BAR_PAD = { top: 26, bottom: 16 };

/** Counts per bucket, e.g. posts per month; bars grow from a shared baseline. */
export function BarChart({ bars, ariaLabel }: BarChartProps) {
	const [active, setActive] = useState<number | null>(null);
	const max = Math.max(1, ...bars.map((bar) => bar.value));
	const plotHeight = BAR_HEIGHT - BAR_PAD.top - BAR_PAD.bottom;
	const baseline = BAR_PAD.top + plotHeight;
	const slot = WIDTH / Math.max(bars.length, 1);
	// A 2px gap between neighbours.
	const barWidth = Math.max(slot - 2, 1);
	const activeBar = active === null ? null : bars[active];

	return (
		<svg
			viewBox={`0 0 ${WIDTH} ${BAR_HEIGHT}`}
			role="img"
			aria-label={ariaLabel}
			className="h-auto w-full text-primary"
		>
			<line
				x1={0}
				x2={WIDTH}
				y1={baseline}
				y2={baseline}
				className="stroke-border"
				strokeWidth={1}
			/>
			{bars.map((bar, i) => {
				const x = i * slot + 1;
				const height = (bar.value / max) * plotHeight;
				const radius = Math.min(4, height, barWidth / 2);
				const top = baseline - height;
				// Rounded at the data end only; square on the baseline.
				const d =
					height > 0
						? `M${x},${baseline} V${top + radius} Q${x},${top} ${x + radius},${top} H${x + barWidth - radius} Q${x + barWidth},${top} ${x + barWidth},${top + radius} V${baseline} Z`
						: "";
				return (
					<g key={bar.key}>
						{d && (
							<path
								d={d}
								fill="currentColor"
								opacity={active === null || active === i ? 1 : 0.6}
								data-testid="chart-bar"
							/>
						)}
						<text
							x={x + barWidth / 2}
							y={BAR_HEIGHT - 3}
							textAnchor="middle"
							fontSize={10}
							className="fill-muted-foreground"
						>
							{bar.tick}
						</text>
						<rect
							x={i * slot}
							y={0}
							width={slot}
							height={baseline}
							fill="transparent"
							onPointerEnter={() => setActive(i)}
							onPointerLeave={() => setActive(null)}
						>
							<title>{bar.label}</title>
						</rect>
					</g>
				);
			})}
			{activeBar && active !== null && (
				<Readout
					x={active * slot + slot / 2}
					y={baseline - (activeBar.value / max) * plotHeight}
					label={activeBar.label}
				/>
			)}
		</svg>
	);
}
