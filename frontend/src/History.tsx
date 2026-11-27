import { useEffect, useState } from "react";
import { api, human, type Bundle, type Projection } from "./model";
import { Inspector } from "./Inspector";

export function History({ bundle }: { bundle: Bundle }) {
	const [seq, setSeq] = useState(bundle.meta.version),
		[p, setP] = useState<Projection | null>(null),
		[error, setError] = useState("");
	const [actor, setActor] = useState("A1");
	useEffect(() => {
		const ac = new AbortController();
		setP(null);
		setError("");
		api<Projection>(
			`/runs/${bundle.meta.id}/replay?seq=${seq}`,
			undefined,
			ac.signal,
		)
			.then(setP)
			.catch((e) => {
				if (!ac.signal.aborted) setError(e.message);
			});
		return () => ac.abort();
	}, [bundle.meta.id, seq]);
	const event = bundle.events.find((e) => e.sequence === seq);
	return (
		<div className="columns">
			<section className="card">
				<header className="card-head">
					<h2>Historical replay</h2>
					<span className="badge">Read-only · operator</span>
				</header>
				<div className="card-body">
					<label>
						Event cursor{" "}
						<input
							aria-label="Event cursor"
							type="range"
							min="0"
							max={bundle.meta.version}
							value={seq}
							onChange={(e) => setSeq(+e.target.value)}
						/>
					</label>
					<div className="controls">
						<button
							type="button"
							disabled={!seq}
							onClick={() => setSeq(seq - 1)}
						>
							Previous event
						</button>
						<b>
							{seq} / {bundle.meta.version}
						</b>
						<button
							type="button"
							disabled={seq === bundle.meta.version}
							onClick={() => setSeq(seq + 1)}
						>
							Next event
						</button>
					</div>
					{error && <p role="alert">{error}</p>}
					{p && (
						<>
							<h3>{event ? human(event.kind) : "Initial world"}</h3>
							<p>
								Round {p.world.round} · {event?.actor ?? "Environment"}
							</p>
							<div className="hash">
								<b>Verified state hash</b>
								<code>{p.state_hash}</code>
							</div>
							<details>
								<summary>Committed event JSON</summary>
								<pre>{JSON.stringify(event ?? {}, null, 2)}</pre>
							</details>
							<details>
								<summary>Operator world at event {seq}</summary>
								<pre>{JSON.stringify(p.world, null, 2)}</pre>
							</details>
						</>
					)}
					<label>
						Inspect agent
						<select value={actor} onChange={(e) => setActor(e.target.value)}>
							{bundle.projection.world.agents.map((a) => (
								<option key={a.id}>{a.id}</option>
							))}
						</select>
					</label>
					{event?.actor && (
						<div className="notice">
							<button
								type="button"
								onClick={() => {
									setActor(event.actor ?? actor);
									setSeq(seq - 1);
								}}
							>
								Inspect pre-decision context for {event.actor}
							</button>
							{event.note && <p>Self-report · {event.note.summary}</p>}
						</div>
					)}
				</div>
			</section>
			<Inspector run={bundle.meta.id} actor={actor} seq={seq} />
		</div>
	);
}
