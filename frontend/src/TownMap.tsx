import { useEffect, useRef } from "react";
import { colorFor, human, type World, type Position } from "./model";

function scene(canvas: HTMLCanvasElement, world: World) {
	const ctx = canvas.getContext("2d");
	if (!ctx) return;
	const grid = world.scenario.grid,
		cols = grid[0].length,
		rows = grid.length,
		tw = 48,
		th = 34;
	canvas.width = cols * tw;
	canvas.height = rows * th;
	const rect = (x: number, y: number, w: number, h: number, c: string) => {
		ctx.fillStyle = c;
		ctx.fillRect(x, y, w, h);
	};
	const poly = (points: Position[], c: string) => {
		ctx.fillStyle = c;
		ctx.beginPath();
		points.forEach(([x, y], i) => {
			if (i) ctx.lineTo(x, y);
			else ctx.moveTo(x, y);
		});
		ctx.closePath();
		ctx.fill();
	};
	const zones = world.scenario.zones;
	const centers = zones.map((z) => z.tiles[0]);
	for (let y = 0; y < rows; y++)
		for (let x = 0; x < cols; x++) {
			const px = x * tw,
				py = y * th,
				noise = (x * 97 + y * 59 + x * y * 13) % 19;
			rect(
				px,
				py,
				tw,
				th,
				["#d0d6aa", "#d4d9b0", "#cdd4a7", "#d6dab1"][noise % 4],
			);
			rect(px, py, tw, 1, "#bfc99d");
			rect(px, py, 1, th, "#c2cca0");
			for (let n = 0; n < 5; n++) {
				const xx = px + ((noise * 3 + n * 13) % 44),
					yy = py + ((noise * 7 + n * 11) % 30);
				rect(xx, yy, 2, 2, "#b7bf8f");
			}
		}
	// Footpaths are cartographic decoration; the scenario grid defines traversability.
	const origin = centers[0];
	if (origin)
		for (const [x, y] of centers) {
			const left = Math.min(x, origin[0]),
				top = Math.min(y, origin[1]);
			rect(
				left * tw + tw / 2,
				origin[1] * th + th / 2 - 4,
				Math.abs(x - origin[0]) * tw + 6,
				9,
				"#dfcba1",
			);
			rect(
				x * tw + tw / 2 - 4,
				top * th + th / 2,
				9,
				Math.abs(y - origin[1]) * th + 6,
				"#dfcba1",
			);
		}
	function pine(x: number, y: number, scale: number) {
		const tri = (w: number, h: number, off: number, col: string) =>
			poly(
				[
					[x, y + off - h * scale],
					[x - w * scale, y + off],
					[x + w * scale, y + off],
				],
				col,
			);
		rect(x - 2, y - 2, 4, 10, "#816545");
		tri(12, 17, 1, "#62825d");
		tri(10, 15, -5, "#789569");
		tri(6, 12, -11, "#8fa677");
	}
	grid.forEach((row, y) => {
		[...row].forEach((cell, x) => {
			if (cell === "#") {
				const cx = x * tw + tw / 2,
					cy = y * th + th / 2 + 6;
				pine(cx - 9, cy + 3, 0.82);
				pine(cx + 7, cy, 1);
			}
		});
	});
	function building(id: string, x: number, y: number) {
		const X = x * tw + tw / 2,
			Y = y * th + th / 2;
		if (id === "square") {
			rect(X - 18, Y - 9, 36, 20, "#c4bb9e");
			rect(X - 12, Y - 6, 24, 12, "#aaa58d");
			rect(X - 9, Y - 5, 18, 9, "#8caeb1");
			rect(X - 2, Y - 13, 4, 12, "#e9e1c9");
			return;
		}
		const colors: Record<string, string> = {
			farm: "#a96d4b",
			market: "#bd8b55",
			"town-hall": "#6c8990",
			clinic: "#9b796e",
			workshop: "#737e74",
		};
		rect(X - 15, Y - 3, 31, 18, "#9da382");
		rect(X - 16, Y - 7, 30, 19, "#ebd9b7");
		rect(X - 16, Y + 8, 30, 4, "#beae90");
		poly(
			[
				[X - 20, Y - 5],
				[X - 12, Y - 17],
				[X + 10, Y - 17],
				[X + 18, Y - 5],
			],
			colors[id] || "#879073",
		);
		rect(X - 20, Y - 5, 38, 3, "#746e58");
		rect(X - 3, Y, 7, 12, "#776e58");
		for (const xx of [-12, 6]) {
			rect(X + xx, Y, 5, 6, "#748d8b");
			rect(X + xx, Y + 3, 5, 1, "#cec7af");
		}
		if (id === "market")
			for (let i = 0; i < 5; i++)
				rect(X - 15 + i * 6, Y - 5, 5, 6, i % 2 ? "#e5d5b2" : "#ae7156");
		if (id === "clinic") {
			rect(X - 1, Y - 14, 3, 8, "#f1e4cb");
			rect(X - 4, Y - 11, 9, 3, "#f1e4cb");
		}
		if (id === "workshop") {
			rect(X + 7, Y - 23, 5, 10, "#786957");
			rect(X + 6, Y - 24, 7, 3, "#656252");
		}
		if (id === "farm")
			for (let n = 0; n < 3; n++) {
				rect(X - 22, Y + 12 + n * 3, 14, 2, "#a49261");
			}
	}
	for (const zone of zones)
		for (const [x, y] of zone.tiles) building(zone.id, x, y);
}

export function TownMap({
	world,
	selected,
	select,
}: {
	world: World;
	selected: string;
	select: (s: string) => void;
}) {
	const ref = useRef<HTMLCanvasElement>(null);
	useEffect(() => {
		if (ref.current) scene(ref.current, world);
	}, [world]);
	const cols = world.scenario.grid[0].length,
		rows = world.scenario.grid.length;
	return (
		<div
			className="atlas"
			style={{ aspectRatio: `${cols * 48} / ${rows * 34}` }}
		>
			<canvas
				ref={ref}
				aria-label="Town terrain, buildings and blocked tiles"
				role="img"
			/>
			{world.scenario.zones.map((z) => (
				<span
					className="map-label"
					key={z.id}
					style={{
						left: `${((z.tiles[0][0] + 0.5) / cols) * 100}%`,
						top: `${((z.tiles[0][1] + 0.96) / rows) * 100}%`,
					}}
				>
					{human(z.id)}
				</span>
			))}
			{world.agents.map((a) => {
				const here = world.agents.filter(
					(b) =>
						b.position[0] === a.position[0] && b.position[1] === a.position[1],
				);
				const idx = here.indexOf(a);
				const offset =
					((idx % 3) -
						(Math.min(here.length - 3 * Math.floor(idx / 3), 3) - 1) / 2) *
					26;
				return (
					<button
						type="button"
						key={a.id}
						className={`map-pin ${selected === a.id ? "selected" : ""}`}
						aria-label={`Inspect ${a.id} on map`}
						onClick={() => select(a.id)}
						style={{
							left: `calc(${((a.position[0] + 0.5) / cols) * 100}% + ${offset}px)`,
							top: `calc(${((a.position[1] + 0.38) / rows) * 100}% + ${Math.floor(idx / 3) * 24}px)`,
							background: colorFor(a.id),
						}}
					>
						{a.id}
					</button>
				);
			})}
		</div>
	);
}
