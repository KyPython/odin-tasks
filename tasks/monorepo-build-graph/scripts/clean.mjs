import { rm } from "node:fs/promises";

await Promise.all([
  rm(new URL("../apps/dispatch-service/dist", import.meta.url), { recursive: true, force: true }),
  rm(new URL("../packages/route-core/dist", import.meta.url), { recursive: true, force: true }),
  rm(new URL("../.turbo", import.meta.url), { recursive: true, force: true })
]);
