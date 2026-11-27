import { useCallback, useEffect, useState } from "react";
import { api, colorFor, human, type Comparison, type Meta } from "./model";
import { Experiment } from "./Experiment";
import { Inspector } from "./Inspector";
import { History } from "./History";
import { TownMap } from "./TownMap";
import { useRun } from "./useRun";

const sections = ["Town", "Experiment lab", "Replay"] as const;
type Section = (typeof sections)[number];
const titles: Record<Section, string> = {
	Town: "Town observatory",
	"Experiment lab": "Experiment lab",
	Replay: "History & replay",
};

export function Dashboard() {
	const [id, setId] = useState(() => localStorage.getItem("av-run") || ""),
		[section, setSection] = useState<Section>("Town");
	const [actor, setActor] = useState("A1"),
		[error, setError] = useState(""),
		[busy, setBusy] = useState(false);
	const [seed, setSeed] = useState(42),
		[speed, setSpeed] = useState(1),
		[online, setOnline] = useState<boolean | null>(null),
		[pair, setPair] = useState<Comparison | null>(null);
	const fail = useCallback((s: string) => setError(s), []),
		{ bundle, refresh } = useRun(id, fail);
	const meta = bundle?.meta,
		w = bundle?.projection.world;
	const select = useCallback((name: string) => {
		localStorage.setItem("av-run", name);
		setId(name);
	}, []);
	useEffect(() => {
		const c = new AbortController();
		api("/health", undefined, c.signal)
			.then(() => setOnline(true))
			.catch(() => {
				if (!c.signal.aborted) {
					setOnline(false);
					fail("The local API is unavailable.");
				}
			});
		const saved = localStorage.getItem("av-pair");
		if (saved)
			api<Comparison>(`/experiments/${saved}/comparison`, undefined, c.signal)
				.then(setPair)
				.catch(() => {});
		return () => c.abort();
	}, [fail]);
	async function create() {
		setBusy(true);
		setError("");
		try {
			const run = await api<Meta>("/runs", { key: crypto.randomUUID(), seed });
			select(run.id);
			setPair(null);
			localStorage.removeItem("av-pair");
			setSection("Town");
		} catch (e) {
			fail(String(e));
		} finally {
			setBusy(false);
		}
	}
	async function act(action: string) {
		if (!meta) return;
		setBusy(true);
		setError("");
		try {
			await api(`/runs/${id}/control`, {
				action,
				key: crypto.randomUUID(),
				expected_version: meta.version,
				expected_revision: meta.revision,
				delay: speed,
			});
			await refresh();
		} catch (e) {
			fail(String(e));
			await refresh().catch(() => {});
		} finally {
			setBusy(false);
		}
	}
	const controls =
		meta &&
		!meta.read_only &&
		!["stopped", "complete", "failed"].includes(meta.status);
	const settled = w ? w.round : 0;
	return (
		<div className="app">
			<header className="mast">
				<div className="brand">
					<span className="brand-icon" aria-hidden="true">
						▦
					</span>
					<span>
						AgentVerse <b>Lab</b>
					</span>
				</div>
				<nav aria-label="Workspace">
					{sections.map((s) => (
						<button
							type="button"
							key={s}
							onClick={() => setSection(s)}
							aria-current={section === s ? "page" : undefined}
						>
							{s}
						</button>
					))}
				</nav>
				<span className="online">
					<i className={online ? "connected" : ""} />
					{online === null
						? "Connecting"
						: online
							? "Local API online"
							: "API offline"}
				</span>
			</header>
			<main>
				<div className="page-head">
					<div>
						<h1>{titles[section]}</h1>
					</div>
					<div className="run-create">
						<label>
							Seed
							<input
								aria-label="Seed"
								type="number"
								step="1"
								value={seed}
								onChange={(e) => setSeed(Number(e.target.value))}
							/>
						</label>
						<button
							type="button"
							className="primary"
							onClick={create}
							disabled={busy || !online}
						>
							＋ New run
						</button>
					</div>
				</div>
				{error && (
					<div className="error" role="alert">
						<span>{error}</span>
						<button type="button" onClick={() => setError("")}>
							Dismiss
						</button>
					</div>
				)}
				{!bundle || !w || !meta ? (
					<section className="empty card">
						<div className="empty-map" aria-hidden="true">
							▦
						</div>
						<h2>{id && !error ? "Loading run…" : "No active run"}</h2>
						<p>
							Create a seeded six-agent town to inspect decisions, replay its
							history, and compare harvest evidence.
						</p>
					</section>
				) : (
					<>
						<div className="run-strip">
							<span className="badge mode">{human(meta.mode)}</span>
							<strong>{human(meta.status)}</strong>
							<span>Seed {meta.seed}</span>
							<span>
								Round {settled} / {w.scenario.harvest.length}
							</span>
							<code title={id}>{id.slice(0, 12)}</code>
							{meta.read_only && pair && (
								<button
									type="button"
									onClick={() => select(pair.manifest.parent)}
								>
									Return to parent
								</button>
							)}
						</div>
						{section === "Town" && (
							<>
								<div className="stats">
									{[
										["Food produced", w.produced],
										["Town food", w.agents.reduce((n, a) => n + a.food, 0)],
										[
											"Town coins",
											w.agents.reduce((n, a) => n + a.coins, w.treasury),
										],
										["Unmet food", w.agents.reduce((n, a) => n + a.unmet, 0)],
									].map(([label, v]) => (
										<div key={label}>
											<span>{label}</span>
											<strong>{v}</strong>
										</div>
									))}
								</div>
								<div className="columns town">
									<div className="stack">
										<section className="card map-card">
											<header className="card-head">
												<div>
													<p className="eyebrow">Operator view</p>
													<h2>Town map</h2>
												</div>
												<span className="map-meta">
													{w.scenario.grid[0].length} × {w.scenario.grid.length}{" "}
													tiles
												</span>
											</header>
											<fieldset
												className="map-controls controls"
												aria-label="Simulation controls"
											>
												<button
													type="button"
													className="primary"
													disabled={
														busy || !controls || meta.status === "running"
													}
													onClick={() => act("start")}
												>
													▶ Start
												</button>
												<button
													type="button"
													disabled={
														busy || !controls || meta.status !== "running"
													}
													onClick={() => act("pause")}
												>
													Pause
												</button>
												<button
													type="button"
													disabled={
														busy || !controls || meta.status === "running"
													}
													onClick={() => act("step")}
												>
													Step round
												</button>
												<button
													type="button"
													disabled={busy || !controls}
													onClick={() => act("stop")}
												>
													Stop
												</button>
												<label>
													Speed
													<select
														value={speed}
														onChange={(e) => setSpeed(+e.target.value)}
														disabled={meta.status === "running"}
													>
														<option value=".25">4×</option>
														<option value="1">1×</option>
														<option value="2">½×</option>
													</select>
												</label>
											</fieldset>
											<TownMap world={w} selected={actor} select={setActor} />
											<div className="map-footer">
												<span>
													<i className="legend-dot" />
													{w.agents.length} agents
												</span>
												<span>▧ Blocked terrain</span>
												<span>Event {meta.version}</span>
											</div>
										</section>

										<section className="card">
											<header className="card-head">
												<h2>Event feed</h2>
												<span className="badge">Operator</span>
											</header>
											<ol className="feed">
												{bundle.events
													.slice(-8)
													.reverse()
													.map((e) => (
														<li key={e.sequence}>
															<code>#{e.sequence}</code>
															<b>{human(e.kind)}</b>
															<span>
																{e.actor || "Environment"}
																{e.reason ? ` · ${human(e.reason)}` : ""}
															</span>
														</li>
													))}
											</ol>
										</section>
									</div>
									<aside className="stack">
										<section className="card">
											<header className="card-head">
												<h2>Agent roster</h2>
												<span className="badge">{w.agents.length} agents</span>
											</header>
											<div className="roster">
												{w.agents.map((a) => (
													<button
														type="button"
														key={a.id}
														className={actor === a.id ? "active" : ""}
														onClick={() => setActor(a.id)}
													>
														<span
															className="avatar"
															style={{ background: colorFor(a.id) }}
														>
															{a.id}
														</span>
														<span>
															<b>
																{
																	w.scenario.profiles.find((p) => p.id === a.id)
																		?.role
																}
															</b>
															<small>Tile {a.position.join(", ")}</small>
														</span>
														<span className="resource">{a.food} food</span>
													</button>
												))}
											</div>
										</section>
										<Inspector
											key={`${id}-${actor}-${meta.version}`}
											run={id}
											actor={actor}
											seq={meta.version}
										/>
									</aside>
								</div>
							</>
						)}
						{section === "Experiment lab" && (
							<Experiment
								bundle={bundle}
								data={pair}
								setData={setPair}
								inspect={(name) => {
									select(name);
									setSection("Replay");
								}}
								fail={fail}
							/>
						)}
						{section === "Replay" && <History key={id} bundle={bundle} />}
					</>
				)}
			</main>
		</div>
	);
}
