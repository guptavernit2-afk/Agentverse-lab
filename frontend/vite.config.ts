import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const proxy = {
	"^/(runs|experiments|settings|health)(/|$)": {
		target: "http://127.0.0.1:8000",
		ws: true,
	},
};
export default defineConfig({
	plugins: [react()],
	server: { host: "127.0.0.1", strictPort: true, proxy },
	preview: { host: "127.0.0.1", strictPort: true, proxy },
});
