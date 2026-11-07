// Régénère les types du client depuis l'OpenAPI du backend (README frontend §6).
// API_SCHEMA_URL prime ; sinon API_PROXY_TARGET (conteneur : http://web:8000) ; sinon localhost.
import { writeFileSync, mkdirSync } from "node:fs";
import { get } from "node:http";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";
import prettier from "prettier";

const here = dirname(fileURLToPath(import.meta.url));
const TARGET = resolve(here, "../src/generated/schema.gen.ts");
const base = process.env.API_PROXY_TARGET ?? "http://localhost:8000";
const url = process.env.API_SCHEMA_URL ?? `${base}/api/schema/`;

// `Host: localhost` : le serveur de dev n'accepte que les hôtes d'ALLOWED_HOSTS (pas `web`).
const download = (target) =>
  new Promise((ok, fail) => {
    get(target, { headers: { Host: "localhost" } }, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => (body += chunk));
      res.on("end", () => (res.statusCode === 200 ? ok(body) : fail(new Error(`${target} : HTTP ${res.statusCode}`))));
    }).on("error", fail);
  });

const ast = await openapiTS(await download(url));
const header = "// Fichier généré par scripts/generate.mjs depuis /api/schema/ — ne pas modifier (`pnpm api:generate`).\n";
const options = await prettier.resolveConfig(TARGET);
const output = await prettier.format(header + astToString(ast), { ...options, filepath: TARGET });
mkdirSync(dirname(TARGET), { recursive: true });
writeFileSync(TARGET, output);
console.log(`Écrit : ${TARGET} (depuis ${url})`);
