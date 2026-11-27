import { useCallback, useEffect, useRef, useState } from "react";
import {
	api,
	needsResync,
	type Bundle,
	type EventRow,
	type Meta,
	type Projection,
	type Snapshot,
} from "./model";

export function useRun(id: string, fail: (message: string) => void) {
	const [bundle, setBundle] = useState<Bundle | null>(null);
	const generation = useRef(0);
	const refresh = useCallback(
		async (signal?: AbortSignal) => {
			if (!id) return;
			const generationId = ++generation.current;
			const meta = await api<Meta>(`/runs/${id}`, undefined, signal);
			const [projection, page, snapshots] = await Promise.all([
				api<Projection>(
					`/runs/${id}/replay?seq=${meta.version}`,
					undefined,
					signal,
				),
				api<{ events: EventRow[] }>(
					`/runs/${id}/events?limit=128`,
					undefined,
					signal,
				),
				api<Snapshot[]>(`/runs/${id}/snapshots`, undefined, signal),
			]);
			if (generation.current === generationId && !signal?.aborted)
				setBundle({
					meta,
					projection,
					events: page.events.filter((e) => e.sequence <= meta.version),
					snapshots: snapshots.filter((s) => s.seq <= meta.version),
				});
		},
		[id],
	);
	useEffect(() => {
		setBundle(null);
		if (!id) return;
		const ac = new AbortController();
		let ws: WebSocket | undefined,
			timer: ReturnType<typeof setTimeout>,
			cursor = 0;
		const sync = () =>
			refresh(ac.signal).catch((e) => {
				if (!ac.signal.aborted) fail(e.message);
			});
		function connect() {
			if (ac.signal.aborted) return;
			const scheme = location.protocol === "https:" ? "wss" : "ws";
			ws = new WebSocket(
				`${scheme}://${location.host}/runs/${id}/stream?after=${cursor}`,
			);
			ws.onmessage = (e) => {
				try {
					const message = JSON.parse(e.data);
					const gap = needsResync(cursor, message);
					cursor = message.head;
					void sync();
					if (gap) ws?.close();
				} catch {
					fail("Invalid event notification");
				}
			};
			ws.onclose = () => {
				if (!ac.signal.aborted)
					timer = setTimeout(() => {
						void sync();
						connect();
					}, 900);
			};
		}
		void sync().then(() => {
			if (!ac.signal.aborted) connect();
		});
		return () => {
			ac.abort();
			generation.current++;
			clearTimeout(timer);
			ws?.close();
		};
	}, [id, refresh, fail]);
	return { bundle, refresh };
}
