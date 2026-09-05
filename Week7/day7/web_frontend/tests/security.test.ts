import fs from "node:fs";
import path from "node:path";
import { expect, it } from "vitest";

function sources(directory: string): string[] {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? sources(target) : /\.(ts|tsx)$/.test(entry.name) ? [target] : [];
  });
}

it("contains no backend secrets, browser ML, or direct OpenAI/VAPI calls", () => {
  const content = ["app", "components", "lib", "types"].flatMap(sources).map(file => fs.readFileSync(file, "utf8")).join("\n");
  for (const forbidden of ["DATABASE_URL", "DAY4_API_KEY", "VAPI_API_KEY", "SMTP_PASSWORD", "joblib", "predict_proba", "api.openai.com", "api.vapi.ai"]) {
    expect(content).not.toContain(forbidden);
  }
});
