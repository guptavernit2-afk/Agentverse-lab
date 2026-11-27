import { useEffect, useState } from "react";
import { api, human, type Observation } from "./model";

export function Inspector({
	run,
	actor,
	seq,
}: {
	run: string;
	actor: string;
	seq: number;
}) {
	const [view, setView] = useState<Observation | null>(null),
		[error, setError] = useState("");
	useEffect(() => {
		const controller = new AbortController();
		setView(null);
		setError("");
		api<{ observation: Observation }>(
			`/runs/${run}/agents/${actor}/view?seq=${seq}`,
			undefined,
			controller.signal,
		)
			.then((data) => setView(data.observation))
			.catch((e) => {
				if (!controller.signal.aborted) setError(e.message);
			});
		return () => controller.abort();
	}, [run, actor, seq]);
	return (
		<section className="card inspector">
			<header className="card-head">
				<h2>Agent inspector</h2>
				<span className="badge">Agent view</span>
			</header>
			{error && <p role="alert">{error}</p>}
			{view && (
				<div className="card-body">
					<div className="inspector-title">
						<b>{actor}</b>
						<h3>{view.self.role}</h3>
					</div>
					<p>{view.self.goal}</p>
					<dl className="facts">
						<dt>Observation</dt>
						<dd>Event {seq}</dd>
						<dt>Position</dt>
						<dd>{view.self.position.join(", ")}</dd>
						<dt>Resources</dt>
						<dd>
							{view.self.food} food · {view.self.coins} coins
						</dd>
						<dt>Last action</dt>
						<dd>{human(view.self.last_action || "No action yet")}</dd>
					</dl>
					<h4>Claims and evidence</h4>
					{view.claims.map((c) => (
						<p key={c.id}>
							{c.text} <strong>{c.status}</strong>
						</p>
					))}
					{view.evidence.map((e) => (
						<p key={e.id}>
							<b>{e.id}</b> · {e.payload.join(", ")}
						</p>
					))}
					<details>
						<summary>Memory and obligations</summary>
						<pre>
							{JSON.stringify(
								{ memory: view.memory, obligations: view.obligations },
								null,
								2,
							)}
						</pre>
					</details>
					<details>
						<summary>Directed trust</summary>
						<pre>{JSON.stringify(view.trust, null, 2)}</pre>
					</details>
					<details>
						<summary>Authorized observation JSON</summary>
						<pre>{JSON.stringify(view, null, 2)}</pre>
					</details>
				</div>
			)}
		</section>
	);
}
