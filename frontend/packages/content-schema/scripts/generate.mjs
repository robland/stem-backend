// Génère src/generated/content.gen.ts (schémas Zod) depuis le JSON Schema exporté par le backend
// (`python manage.py export_content_schema`, README backend §6). `--check` échoue si le fichier n'est pas à jour.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import prettier from "prettier";

const here = dirname(fileURLToPath(import.meta.url));
const SOURCE = resolve(here, "../../../../stem_learning_app/schemas/exercise-content.schema.json");
const TARGET = resolve(here, "../src/generated/content.gen.ts");

// Champs retirés par `GET /api/exercises/{id}` (backend `learning.services.public_content`, §6.4).
const PUBLIC_STEP_OMIT = ["common_mistakes", "explanation"];
const PUBLIC_ACTIVITY_OMIT = ["answer"];

const schema = JSON.parse(readFileSync(SOURCE, "utf8"));
const defs = schema.$defs ?? {};
const ROOT = schema.title;

const refName = (ref) => ref.replace(/^#\/\$defs\//, "");

function deps(node, acc = new Set()) {
  if (Array.isArray(node)) node.forEach((n) => deps(n, acc));
  else if (node && typeof node === "object") {
    if (typeof node.$ref === "string") acc.add(refName(node.$ref));
    Object.values(node).forEach((v) => deps(v, acc));
  }
  return acc;
}

// Ordre topologique : chaque schéma est déclaré après ceux qu'il référence (aucun cycle dans le contrat).
const ordered = [];
const seen = new Set();
function visit(name) {
  if (seen.has(name)) return;
  seen.add(name);
  deps(defs[name]).forEach(visit);
  ordered.push(name);
}
Object.keys(defs).sort().forEach(visit);

const isNull = (s) => s.type === "null";
const discriminator = (members) =>
  members.every((m) => m.$ref && defs[refName(m.$ref)]?.properties?.type?.const !== undefined)
    ? "type"
    : null;

function zod(s) {
  if (s.$ref) return refName(s.$ref);
  if (s.const !== undefined) return `z.literal(${JSON.stringify(s.const)})`;
  if (s.enum) return `z.enum(${JSON.stringify(s.enum)})`;
  if (s.anyOf) {
    const members = s.anyOf.filter((m) => !isNull(m));
    const nullable = members.length < s.anyOf.length ? ".nullable()" : "";
    if (members.length === 1) return zod(members[0]) + nullable;
    const key = discriminator(members);
    const list = members.map(zod).join(", ");
    return (key ? `z.discriminatedUnion("${key}", [${list}])` : `z.union([${list}])`) + nullable;
  }
  switch (s.type) {
    case "string": {
      let out = "z.string()";
      if (s.minLength !== undefined) out += `.min(${s.minLength})`;
      if (s.maxLength !== undefined) out += `.max(${s.maxLength})`;
      if (s.pattern) out += `.regex(new RegExp(${JSON.stringify(s.pattern)}))`;
      return out;
    }
    case "integer":
      return "z.number().int()";
    case "number":
      return "z.number()";
    case "boolean":
      return "z.boolean()";
    case "null":
      return "z.null()";
    case "array": {
      let out = `z.array(${zod(s.items ?? {})})`;
      if (s.minItems !== undefined) out += `.min(${s.minItems})`;
      if (s.maxItems !== undefined) out += `.max(${s.maxItems})`;
      return out;
    }
    case "object": {
      const required = new Set(s.required ?? []);
      const fields = Object.entries(s.properties ?? {}).map(
        ([key, value]) => `${JSON.stringify(key)}: ${zod(value)}${required.has(key) ? "" : ".optional()"}`,
      );
      return `z.object({ ${fields.join(", ")} })${s.additionalProperties === false ? ".strict()" : ""}`;
    }
    default:
      throw new Error(`Type JSON Schema non géré : ${JSON.stringify(s)}`);
  }
}

const omit = (keys) => `{ ${keys.map((k) => `${k}: true`).join(", ")} }`;
const activityRefs = defs.Step.properties.activity.anyOf.map((m) => refName(m.$ref));
const publicActivities = activityRefs.map((name) => `${name}Public`);

const lines = [
  "// Fichier généré par scripts/generate.mjs — ne pas modifier à la main (`pnpm schema:generate`).",
  `// Source : stem_learning_app/schemas/exercise-content.schema.json (schema_version ${schema.properties.schema_version.const}).`,
  'import { z } from "zod";',
  "",
  `export const SCHEMA_VERSION = ${JSON.stringify(schema.properties.schema_version.const)};`,
  "",
];
for (const name of [...ordered, ROOT]) {
  lines.push(`export const ${name} = ${zod(name === ROOT ? schema : defs[name])};`);
  lines.push(`export type ${name} = z.infer<typeof ${name}>;`, "");
}

lines.push(
  "export const Activity = Step.shape.activity;",
  "export type Activity = z.infer<typeof Activity>;",
  "",
  "// Contenu public (`GET /api/exercises/{id}`) : sans réponse attendue, erreurs typiques ni correction,",
  "// et sans le dernier niveau d'indice (obtenu par `POST attempts/{id}/hints`).",
);
for (const name of activityRefs) {
  lines.push(`export const ${name}Public = ${name}.omit(${omit(PUBLIC_ACTIVITY_OMIT)});`);
  lines.push(`export type ${name}Public = z.infer<typeof ${name}Public>;`);
}
lines.push(
  "",
  `export const ActivityPublic = z.discriminatedUnion("type", [${publicActivities.join(", ")}]);`,
  "export type ActivityPublic = z.infer<typeof ActivityPublic>;",
  "",
  `export const StepPublic = Step.omit(${omit([...PUBLIC_STEP_OMIT, "activity"])}).extend({ activity: ActivityPublic });`,
  "export type StepPublic = z.infer<typeof StepPublic>;",
  "",
  `export const ${ROOT}Public = ${ROOT}.extend({ steps: z.array(StepPublic) });`,
  `export type ${ROOT}Public = z.infer<typeof ${ROOT}Public>;`,
  "",
  `export const ACTIVITY_TYPES = ${JSON.stringify(activityRefs.map((n) => defs[n].properties.type.const))} as const;`,
  "export type ActivityType = (typeof ACTIVITY_TYPES)[number];",
  "",
);

const options = await prettier.resolveConfig(TARGET);
const output = await prettier.format(lines.join("\n"), { ...options, filepath: TARGET });
if (process.argv.includes("--check")) {
  let current = "";
  try {
    current = readFileSync(TARGET, "utf8");
  } catch {
    /* absent */
  }
  if (current !== output) {
    console.error("content.gen.ts n'est pas à jour : lancer `pnpm schema:generate`.");
    process.exit(1);
  }
} else {
  mkdirSync(dirname(TARGET), { recursive: true });
  writeFileSync(TARGET, output);
  console.log(`Écrit : ${TARGET}`);
}
