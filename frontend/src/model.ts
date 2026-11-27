export type Position = [number, number];
export type Agent = {
	id: string;
	position: Position;
	food: number;
	coins: number;
	unmet: number;
	last_action: string | null;
};
export type Profile = {
	id: string;
	role: string;
	workplace: string;
	goal: string;
};
export type Zone = { id: string; tiles: Position[] };
export type World = {
	seed: number;
	round: number;
	stage: string;
	agents: Agent[];
	treasury: number;
	produced: number;
	consumed: number;
	scenario: {
		grid: string[];
		zones: Zone[];
		profiles: Profile[];
		scenario_id: string;
		harvest: number[];
	};
};
export type Projection = {
	version: number;
	state_hash: string;
	verified: boolean;
	world: World;
};
export type Meta = {
	id: string;
	version: number;
	revision: number;
	status: string;
	read_only: boolean;
	mode: string;
	seed: number;
	delay: number;
};
export type EventRow = {
	sequence: number;
	round: number;
	kind: string;
	actor: string | null;
	reason: string | null;
	note: { summary: string } | null;
};
export type Snapshot = { seq: number; digest: string };
export type Bundle = {
	meta: Meta;
	projection: Projection;
	events: EventRow[];
	snapshots: Snapshot[];
};
export type Observation = {
	self: Agent & Profile;
	messages: unknown[];
	evidence: { id: string; status: string; payload: number[] }[];
	claims: { id: string; text: string; status: string }[];
	memory: unknown[];
	obligations: unknown[];
	trust: Record<string, number>;
	allowed_actions: string[];
};
export type Branch = {
	run: string;
	status: string;
	runtime: { calls?: number; seconds?: number; estimated_cost?: number | null };
};
export type MetricRow = {
	round: number;
	unmet_units: number;
	agents_affected: number;
	food_units: number;
	mean_trust: number;
	fulfillment_rate: number | null;
	scheduled_turns: number;
	trust_edges: { observer: string; subject: string; score: number }[];
	[key: string]: unknown;
};
export type Comparison = {
	manifest: {
		experiment: string;
		checkpoint: number;
		parent: string;
		prefix_hash: string;
		assignment: Record<"A" | "B", { harvest_record_access: string }>;
		policy: { mode: string; model: string | null };
	};
	branches: Record<"A" | "B", Branch>;
	rounds: Record<"A" | "B", MetricRow[]>;
	completed_pairs: number;
	final_delta: Record<string, number | null> | null;
	mode: string;
};

export async function api<T>(
	path: string,
	body?: unknown,
	signal?: AbortSignal,
): Promise<T> {
	const options: RequestInit = { signal };
	if (body !== undefined)
		Object.assign(options, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body),
		});
	const res = await fetch(path, options);
	if (!res.ok) {
		const message = await res.json().catch(() => null);
		throw new Error(message?.detail || `Request failed (HTTP ${res.status})`);
	}
	return res.json();
}
export const human = (text: string) =>
	text.replaceAll("_", " ").replaceAll("-", " ");
export function display(value: unknown, percent = false): string {
	if (typeof value !== "number" || !Number.isFinite(value)) return "N/A";
	return percent
		? `${(value * 100).toFixed(1)}%`
		: Number(value.toFixed(3)).toString();
}
export function needsResync(
	cursor: number,
	message: { type: string; after: number; head: number },
): boolean {
	return (
		message.type === "gap" || message.after !== cursor || message.head < cursor
	);
}
export const colorFor = (id: string) =>
	["#d98151", "#517b94", "#9a78b0", "#577b58", "#ad8a3d", "#5d9390"][
		Number(id.slice(1)) - 1
	] || "#687078";
