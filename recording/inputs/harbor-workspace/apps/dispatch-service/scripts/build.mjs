import { mkdir, readFile, writeFile } from "node:fs/promises";

const routesUrl = new URL("../../../packages/route-core/dist/routes.json", import.meta.url);
const routes = JSON.parse(await readFile(routesUrl, "utf8"));
const outputUrl = new URL("../dist/manifest.json", import.meta.url);
await mkdir(new URL("../dist", import.meta.url), { recursive: true });
await writeFile(outputUrl, `${JSON.stringify({ service: "dispatch", routes }, null, 2)}\n`);
console.log(`built dispatch-service with ${routes.length} routes`);
