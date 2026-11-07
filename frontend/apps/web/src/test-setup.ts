import "@testing-library/jest-dom/vitest";
import { configure } from "@testing-library/react";

// Écrans chargés à la demande + KaTeX : sous charge (toute la suite en parallèle), 1 s ne suffit pas toujours.
configure({ asyncUtilTimeout: 3000 });

// jsdom remplace Blob/File/FormData, mais fetch/Request restent ceux de Node (undici), qui ne savent pas
// lire un FormData jsdom (envoi multipart bloqué). On rend aux tests les classes natives de Node.
// (`getBuiltinModule` évite d'ajouter les types Node au code de l'application.)
type NodeProcess = { getBuiltinModule(id: "node:buffer"): { Blob: typeof Blob; File: typeof File } };
const { Blob: NodeBlob, File: NodeFile } = (
  globalThis as unknown as { process: NodeProcess }
).process.getBuiltinModule("node:buffer");
const urlencoded = { "Content-Type": "application/x-www-form-urlencoded" };
const NodeFormData = (await new Response("a=b", { headers: urlencoded }).formData())
  .constructor as typeof FormData;
Object.assign(globalThis, { Blob: NodeBlob, File: NodeFile, FormData: NodeFormData });
