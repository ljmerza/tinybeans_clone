import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BarChart, type ChartPoint, LineChart } from "./charts";

const points = (count: number): ChartPoint[] =>
	Array.from({ length: count }, (_, i) => ({
		x: i * 2,
		y: 50 + i * 3,
		label: `Point ${i + 1}`,
	}));

function renderLine(data: ChartPoint[]) {
	return render(
		<LineChart
			points={data}
			formatX={(x) => `${x} mo`}
			formatY={(y) => `${y.toFixed(1)} cm`}
			ariaLabel="Height over time"
			emptyMessage="No heights logged yet."
		/>,
	);
}

describe("LineChart", () => {
	it("shows the empty message and no chart without points", () => {
		renderLine([]);

		expect(screen.getByText("No heights logged yet.")).toBeInTheDocument();
		expect(
			screen.queryByRole("img", { name: "Height over time" }),
		).not.toBeInTheDocument();
	});

	it("draws a lone marker, without a line, for one point", () => {
		renderLine(points(1));

		expect(
			screen.getByRole("img", { name: "Height over time" }),
		).toBeInTheDocument();
		expect(screen.getAllByTestId("chart-point")).toHaveLength(1);
		expect(screen.queryByTestId("chart-line")).not.toBeInTheDocument();
		// One x tick, and the y axis is padded around the single value.
		expect(screen.getByText("0 mo")).toBeInTheDocument();
		expect(screen.getByText("50.0 cm")).toBeInTheDocument();
	});

	it("joins many points with a line through each of them", () => {
		renderLine(points(5));

		const markers = screen.getAllByTestId("chart-point");
		expect(markers).toHaveLength(5);
		const line = screen.getByTestId("chart-line");
		const path = line.getAttribute("d") ?? "";
		expect(path.match(/[ML]/g)).toHaveLength(5);
		// Later, larger values sit further right and higher up.
		const [first, last] = [markers[0], markers[4]];
		expect(Number(last.getAttribute("cx"))).toBeGreaterThan(
			Number(first.getAttribute("cx")),
		);
		expect(Number(last.getAttribute("cy"))).toBeLessThan(
			Number(first.getAttribute("cy")),
		);
		// First and last x ticks.
		expect(screen.getByText("0 mo")).toBeInTheDocument();
		expect(screen.getByText("8 mo")).toBeInTheDocument();
	});

	it("reads out a point on hover", () => {
		const { container } = renderLine(points(3));

		const targets = container.querySelectorAll("circle[fill='transparent']");
		fireEvent.pointerEnter(targets[1]);
		expect(screen.getByTestId("chart-readout")).toHaveTextContent("Point 2");

		fireEvent.pointerLeave(targets[1]);
		expect(screen.queryByTestId("chart-readout")).not.toBeInTheDocument();
	});
});

describe("BarChart", () => {
	it("draws a bar for each non-zero value", () => {
		render(
			<BarChart
				ariaLabel="Posts per month"
				bars={[
					{ key: "2026-08", value: 2, tick: "A", label: "August: 2 posts" },
					{ key: "2026-09", value: 0, tick: "S", label: "September: 0 posts" },
					{ key: "2026-10", value: 4, tick: "O", label: "October: 4 posts" },
				]}
			/>,
		);

		expect(
			screen.getByRole("img", { name: "Posts per month" }),
		).toBeInTheDocument();
		expect(screen.getAllByTestId("chart-bar")).toHaveLength(2);
		expect(screen.getByText("S")).toBeInTheDocument();
	});
});
