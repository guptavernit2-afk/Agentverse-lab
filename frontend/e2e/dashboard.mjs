import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { mkdtemp, mkdir, readFile, rmdir, unlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";
import { chromium } from "playwright";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const directory = await mkdtemp(join(tmpdir(), "agentverse-e2e-"));
const python =
	process.env.AGENTVERSE_VERIFICATION_PYTHON ||
	join(
		root,
		"backend",
		".venv",
		process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
	);
const db = join(directory, "test.sqlite");
const server = spawn(
	python,
	[
		"-m",
		"uvicorn",
		"agentverse.api.main:app",
		"--host",
		"127.0.0.1",
		"--port",
		"0",
	],
	{
		cwd: join(root, "backend"),
		windowsHide: true,
		env: {
			...process.env,
			AGENTVERSE_DB: db,
			AGENTVERSE_ENABLE_LIVE: "0",
			GEMINI_API_KEY: "",
		},
	},
);
let log = "",
	launchError;
server.on("error", (e) => {
	launchError = e;
});
server.stdout.on("data", (d) => {
	log += d;
});
server.stderr.on("data", (d) => {
	log += d;
});
let browser;
try {
	let url;
	for (let i = 0; i < 150; i++) {
		if (launchError) throw launchError;
		if (server.exitCode !== null) throw new Error(log);
		url = log.match(/Uvicorn running on (http:\/\/127\.0\.0\.1:\d+)/)?.[1];
		if (url) break;
		await delay(100);
	}
	assert.ok(url, "local API failed to start");
	browser = await chromium.launch();
	const ctx = await browser.newContext({
		viewport: { width: 1280, height: 720 },
	});
	const external = [],
		errors = [];
	await ctx.route("**/*", async (route) => {
		if (new URL(route.request().url()).origin !== url) {
			external.push(route.request().url());
			await route.abort();
		} else await route.continue();
	});
	const page = await ctx.newPage();
	page.setDefaultTimeout(10000);
	page.on("pageerror", (e) => errors.push(e.message));
	page.on("console", (m) => {
		if (m.type() === "error") errors.push(m.text());
	});
	const button = (name) => page.getByRole("button", { name, exact: true });
	const shotDir = process.env.AGENTVERSE_SCREENSHOTS;
	async function shot(name) {
		if (shotDir) {
			await mkdir(shotDir, { recursive: true });
			await page.screenshot({ path: join(shotDir, name + ".png") });
		}
	}
	await page.goto(url);
	await page.getByRole("heading", { name: "No active run" }).waitFor();
	const create = page.getByRole("button", { name: /New run/ });
	await create.focus();
	await page.keyboard.press("Enter");
	await page.getByText("Event 2", { exact: true }).first().waitFor();
	await button("Step round").click();
	await page.getByText("Event 10", { exact: true }).first().waitFor();
	const name = await page.evaluate(() => localStorage.getItem("av-run"));
	const get = async (path) => {
		const res = await ctx.request.get(url + path);
		assert.equal(res.status(), 200);
		return res.json();
	};
	const source = await get("/runs/" + name + "/world");
	assert.equal(source.world.round, 1);
	assert.equal(source.version, 10);
	await button("Inspect A2 on map").click();
	await page.locator(".inspector-title").filter({ hasText: "A2" }).waitFor();
	assert.equal(
		(await get("/runs/" + name + "/agents/A2/view")).observation.self.role,
		await page.locator(".inspector-title h3").innerText(),
	);
	for (const [width, height] of [
		[1280, 720],
		[1440, 900],
		[390, 844],
	]) {
		await page.setViewportSize({ width, height });
		assert.equal(
			await page.evaluate(
				() => document.documentElement.scrollWidth <= innerWidth,
			),
			true,
		);
		await page.evaluate(() => window.scrollTo(0, 0));
		await shot("town-" + width);
	}
	await page.setViewportSize({ width: 1440, height: 900 });
	await button("Experiment lab").click();
	await button("Fork experiment").click();
	await page.getByText(/Incomplete pair/).waitFor();
	await button("Run branch B").click();
	await button("Run branch A").click();
	await page.getByText("1 completed pair", { exact: true }).waitFor();
	const eid = await page.evaluate(() => localStorage.getItem("av-pair"));
	const comp = await get("/experiments/" + eid + "/comparison");
	assert.equal(
		await page.getByTestId("delta-unmet_units").innerText(),
		String(comp.final_delta.unmet_units),
	);
	assert.equal(
		await page
			.getByRole("row")
			.filter({ hasText: "Unmet food" })
			.locator("td")
			.first()
			.innerText(),
		String(comp.rounds.A.at(-1).unmet_units),
	);
	await page.getByText("rule based", { exact: true }).first().waitFor();
	await page
		.getByRole("heading", { name: "Paired comparison" })
		.evaluate((el) => el.scrollIntoView({ block: "start" }));
	await shot("experiment");
	for (const [name, format] of [
		["Download JSON", "json"],
		["Download metrics CSV", "csv"],
	]) {
		const download = page.waitForEvent("download");
		await page.getByRole("link", { name }).click();
		const file = await download;
		const content = await readFile(await file.path(), "utf8");
		if (format === "json") {
			const data = JSON.parse(content);
			assert.equal(data.manifest.experiment, eid);
			assert.equal(data.history.B.length, 67);
		} else assert.match(content, /unmet_units,28/);
	}
	await button("Inspect history B").click();
	await page.getByText("Verified state hash").waitFor();
	const slider = page.getByRole("slider", { name: "Event cursor" });
	await slider.focus();
	await page.keyboard.press("Home");
	await page.keyboard.press("ArrowRight");
	await page.keyboard.press("ArrowRight");
	const historical = await get(
		"/runs/" + comp.branches.B.run + "/replay?seq=2",
	);
	await page.getByText(historical.state_hash, { exact: true }).waitFor();
	await page
		.locator(".inspector")
		.getByText("unverified", { exact: true })
		.waitFor();
	await button("Next event").click();
	await page
		.locator(".inspector")
		.getByText("evidence-harvest", { exact: true })
		.waitFor();
	await shot("historical-evidence");
	assert.deepEqual(errors, []);
	assert.deepEqual(external, []);
	console.log(
		"Verified actual create, keyboard step/inspection, both branches, comparison, exact replay and JSON/CSV downloads.",
	);
	console.log(
		"1280x720, 1440x900 and 390x844 fit; normal-path console errors 0, external requests 0.",
	);
	const bad = await ctx.newPage();
	await bad.route("**/health", (r) =>
		r.fulfill({ status: 503, body: "unavailable" }),
	);
	await bad.goto(url);
	await bad.getByRole("alert").filter({ hasText: "unavailable" }).waitFor();
	assert.equal(
		await bad.getByRole("button", { name: /New run/ }).isDisabled(),
		true,
	);
	console.log("Unavailable API surfaced an error and disabled run creation.");
} finally {
	await browser?.close();
	if (server.exitCode === null && !launchError) {
		const stopped = once(server, "exit");
		server.kill();
		await stopped;
	}
	for (const filename of [db, db + "-wal", db + "-shm", db + "-journal"])
		await unlink(filename).catch((e) => {
			if (e.code !== "ENOENT") throw e;
		});
	await rmdir(directory);
}
