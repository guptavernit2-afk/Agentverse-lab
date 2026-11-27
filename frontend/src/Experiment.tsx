import { useEffect, useState } from "react";
import { api, display, human, type Bundle, type Comparison } from "./model";

const rounds = [1, 2, 3, 4, 5, 6, 7, 8];
const metrics = [
	["unmet_units", "Unmet food", "units"],
	["agents_affected", "Agents affected", "agents"],
	["food_units", "Food inventory", "units"],
	["produced_units", "Production", "units"],
	["trade_units", "Trade volume", "units"],
	["gift_units", "Gifts", "units"],
	["fulfillment_units", "Commitment deliveries", "units"],
	["fulfillment_rate", "Fulfillment rate", "%"],
	["mean_trust", "Mean directed trust", "points"],
	["food_gini", "Inventory Gini", "index"],
	["evidence_citations", "Evidence citations", "summaries"],
	["invalid_rate", "Invalid actions", "%"],
	["provider_failures", "Provider failures", "turns"],
];

function Trajectories({ data }: { data: Comparison }) {
	const rows = data.rounds,
		maximum = Math.max(1, ...[...rows.A, ...rows.B].map((r) => r.unmet_units));
	return (
		<div
			className="chart"
			role="img"
			aria-label="Cumulative unmet demand by round"
		>
			{rounds.map((roundNumber) => (
				<div className="chart-col" key={roundNumber}>
					<div className="bars">
						{(["A", "B"] as const).map((label) => (
							<div
								key={label}
								className={`bar ${label}`}
								title={`${label}, round ${roundNumber}: ${display(rows[label][roundNumber - 1]?.unmet_units)} units`}
								style={{
									height: `${((rows[label][roundNumber - 1]?.unmet_units ?? 0) / maximum) * 100}%`,
								}}
							/>
						))}
					</div>
					<small>{roundNumber}</small>
				</div>
			))}
		</div>
	);
}

export function Experiment({
	bundle,
	data,
	setData,
	inspect,
	fail,
}: {
	bundle: Bundle;
	data: Comparison | null;
	setData: (v: Comparison) => void;
	inspect: (id: string) => void;
	fail: (s: string) => void;
}) {
	const [checkpoint, setCheckpoint] = useState(2),
		[busy, setBusy] = useState(false),
		[model, setModel] = useState<string | null>(null);
	const [mode, setMode] = useState("rule_based"),
		[approval, setApproval] = useState(false),
		[calls, setCalls] = useState(96),
		[tokens, setTokens] = useState(1000000);
	const [round, setRound] = useState(8);
	useEffect(() => {
		let active = true;
		api<{ live_model: string | null }>("/settings")
			.then((s) => {
				if (active) setModel(s.live_model);
			})
			.catch((e) => {
				if (active) fail(e.message);
			});
		return () => {
			active = false;
		};
	}, [fail]);
	async function doWork(task: () => Promise<void>) {
		setBusy(true);
		try {
			await task();
		} catch (e) {
			fail(String(e));
		} finally {
			setBusy(false);
		}
	}
	async function fork() {
		const obj = await api<{ manifest: { experiment: string } }>(
			"/experiments",
			{
				key: crypto.randomUUID(),
				parent: bundle.meta.id,
				checkpoint,
				mode,
				...(mode === "live_llm"
					? { approve_live: approval, max_calls: calls, max_tokens: tokens }
					: {}),
			},
		);
		localStorage.setItem("av-pair", obj.manifest.experiment);
		setData(
			await api<Comparison>(
				`/experiments/${obj.manifest.experiment}/comparison`,
			),
		);
	}
	const eid = data?.manifest.experiment;
	async function finish(label: string) {
		await api(`/experiments/${eid}/branches/${label}/run`, {});
		setData(await api<Comparison>(`/experiments/${eid}/comparison`));
	}
	return (
		<div className="stack">
			<section className="card">
				<header className="card-head">
					<h2>Food scarcity and evidence</h2>
					<span className="badge">Paired experiment</span>
				</header>
				<div className="card-body">
					<p className="question">
						Does access to the harvest record change unmet food demand?
					</p>
					<div className="conditions">
						<div>
							<b className="tag A">A</b>
							<strong>Unverified bulletin</strong>
							<p>Agents see the bulletin. The harvest record stays private.</p>
						</div>
						<div>
							<b className="tag B">B</b>
							<strong>Verifiable evidence</strong>
							<p>
								All six agents can inspect the same authenticated harvest
								record.
							</p>
						</div>
					</div>
					<p className="muted">
						Shared seed, agent profiles, decision order and food supply. Eight
						rounds · three food units produced per round.
					</p>
					<div className="controls">
						<label>
							Checkpoint
							<select
								value={checkpoint}
								onChange={(e) => setCheckpoint(+e.target.value)}
							>
								{bundle.snapshots
									.filter((s) => s.seq === 2)
									.map((s) => (
										<option key={s.seq} value={s.seq}>
											Round 0 · event {s.seq}
										</option>
									))}
							</select>
						</label>
						<label>
							Decision policy
							<select value={mode} onChange={(e) => setMode(e.target.value)}>
								<option value="rule_based">Rule-based</option>
								<option value="live_llm" disabled={!model}>
									Live Gemini{model ? "" : " · unconfigured"}
								</option>
							</select>
						</label>
						<button
							type="button"
							className="primary"
							disabled={
								busy ||
								bundle.meta.read_only ||
								(mode === "live_llm" && !approval)
							}
							onClick={() => doWork(fork)}
						>
							Fork experiment
						</button>
					</div>
					{mode === "live_llm" && (
						<div className="controls">
							<label>
								Maximum calls
								<input
									type="number"
									value={calls}
									onChange={(e) => setCalls(+e.target.value)}
								/>
							</label>
							<label>
								Token limit
								<input
									type="number"
									value={tokens}
									onChange={(e) => setTokens(+e.target.value)}
								/>
							</label>
							<label>
								<input
									type="checkbox"
									checked={approval}
									onChange={(e) => setApproval(e.target.checked)}
								/>
								Approve calls to {model} within these limits
							</label>
						</div>
					)}
				</div>
			</section>
			{data && (
				<>
					<div className="conditions results">
						{(["A", "B"] as const).map((label) => (
							<section className="card card-body" key={label}>
								<div className="branch-title">
									<b className={`tag ${label}`}>{label}</b>
									<h2>Branch {label}</h2>
									<span className="badge">
										{human(data.branches[label].status)}
									</span>
								</div>
								<p>
									{data.manifest.assignment[label].harvest_record_access} record
									access · {human(data.mode)}
								</p>
								<p className="muted">
									Calls {display(data.branches[label].runtime.calls)} · runtime{" "}
									{display(data.branches[label].runtime.seconds)} s · estimated
									cost {display(data.branches[label].runtime.estimated_cost)}{" "}
									USD
								</p>
								<div className="controls">
									<button
										type="button"
										disabled={busy || data.branches[label].status !== "ready"}
										onClick={() => doWork(() => finish(label))}
									>
										Run branch {label}
									</button>
									<button
										type="button"
										onClick={() => inspect(data.branches[label].run)}
									>
										Inspect history {label}
									</button>
								</div>
							</section>
						))}
					</div>
					<section className="card">
						<header className="card-head">
							<h2>Paired comparison</h2>
							<span className="badge mode">{human(data.mode)}</span>
							<span className="badge">
								{data.completed_pairs} completed pair
								{data.completed_pairs === 1 ? "" : "s"}
							</span>
						</header>
						<div className="card-body">
							{!data.completed_pairs && (
								<p className="notice">
									Incomplete pair. Paired differences are unavailable until both
									branches finish.
								</p>
							)}
							<h3>Cumulative unmet demand</h3>
							<Trajectories data={data} />
							<p className="muted">
								Round · A in ochre, B in teal. Values appear below.
							</p>
							<label>
								Inspect round{" "}
								<select
									value={round}
									onChange={(e) => setRound(+e.target.value)}
								>
									{rounds.map((roundNumber) => (
										<option key={roundNumber}>{roundNumber}</option>
									))}
								</select>
							</label>
							<div className="scroll">
								<table>
									<thead>
										<tr>
											<th>Metric</th>
											<th>A</th>
											<th>B</th>
											<th>B − A</th>
										</tr>
									</thead>
									<tbody>
										{metrics.map(([key, label, unit]) => {
											const a = data.rounds.A[round - 1]?.[key],
												b = data.rounds.B[round - 1]?.[key];
											const delta =
												data.completed_pairs &&
												typeof a === "number" &&
												typeof b === "number"
													? b - a
													: null;
											return (
												<tr key={key}>
													<th>
														{label} <small>{unit}</small>
													</th>
													<td>{display(a, unit === "%")}</td>
													<td>{display(b, unit === "%")}</td>
													<td data-testid={`delta-${key}`}>
														{unit === "%" && delta !== null
															? `${display(delta * 100)} pp`
															: display(delta)}
													</td>
												</tr>
											);
										})}
									</tbody>
								</table>
							</div>
							<details>
								<summary>Directed trust matrix · round {round}</summary>
								{(["A", "B"] as const).map((label) => {
									const edges =
											data.rounds[label][round - 1]?.trust_edges ?? [],
										ids = [...new Set(edges.map((e) => e.observer))];
									return (
										<div className="scroll" key={label}>
											<h4>Branch {label}</h4>
											<table>
												<thead>
													<tr>
														<th>Observer</th>
														{ids.map((id) => (
															<th key={id}>{id}</th>
														))}
													</tr>
												</thead>
												<tbody>
													{ids.map((id) => (
														<tr key={id}>
															<th>{id}</th>
															{ids.map((s) => (
																<td key={s}>
																	{display(
																		edges.find(
																			(e) =>
																				e.subject === s && e.observer === id,
																		)?.score,
																	)}
																</td>
															))}
														</tr>
													))}
												</tbody>
											</table>
										</div>
									);
								})}
							</details>
							<div className="controls exports">
								<a download href={`/experiments/${eid}/export?format=json`}>
									Download JSON
								</a>
								<a download href={`/experiments/${eid}/export?format=csv`}>
									Download metrics CSV
								</a>
							</div>
						</div>
					</section>
				</>
			)}
		</div>
	);
}
