import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "@fontsource/barlow/latin-400.css";
import "@fontsource/barlow/latin-600.css";
import "@fontsource/barlow/latin-700.css";
import "./styles.css";

const container = document.getElementById("root");
if (!container) {
	throw new Error("Missing application mount point");
}

createRoot(container).render(
	<StrictMode>
		<App />
	</StrictMode>,
);
