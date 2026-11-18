import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readExecutionProfile } from "./execution-profile.mjs";

const [command, ...args] = process.argv.slice(2);
if (!["dev", "build"].includes(command)) throw new Error("Expected dev or build.");
const managedLinux = readExecutionProfile() === "managed-linux";
const uiRoot = fileURLToPath(new URL("../", import.meta.url));

function ensureHostingConfig() {
  const hostingPath = path.join(uiRoot, ".openai", "hosting.json");
  if (!existsSync(hostingPath)) {
    mkdirSync(path.dirname(hostingPath), { recursive: true });
    writeFileSync(hostingPath, JSON.stringify({ d1: "DB", r2: "" }, null, 2) + "\n", "utf8");
  }
}

function parsePortArgs(rawArgs, defaultPort) {
  let port = defaultPort;
  const passthrough = [];
  for (let i = 0; i < rawArgs.length; i += 1) {
    const arg = rawArgs[i];
    if ((arg === "--port" || arg === "-p") && i + 1 < rawArgs.length) {
      port = rawArgs[i + 1];
      i += 1;
    } else if (arg.startsWith("--port=")) {
      port = arg.slice("--port=".length);
    } else {
      passthrough.push(arg);
    }
  }
  return { port, passthrough };
}

if (managedLinux && command === "build") {
  const result = spawnSync("bash", [
    fileURLToPath(new URL("./build-verified.sh", import.meta.url)), ...args,
  ], { stdio: "inherit" });
  if (result.error) throw result.error;
  process.exit(result.status ?? 1);
}

ensureHostingConfig();

// On Windows, vinext dev's workerd SSR runner throws an internal error on /.
// Build and serve locally via Wrangler instead unless LAYA_USE_VINEXT_DEV=1.
if (process.platform === "win32" && !managedLinux && command === "dev" && process.env.LAYA_USE_VINEXT_DEV !== "1") {
  const { port, passthrough } = parsePortArgs(args, "5173");
  const buildResult = spawnSync(
    process.execPath,
    [fileURLToPath(import.meta.url), "build"],
    { cwd: uiRoot, stdio: "inherit" },
  );
  if (buildResult.error) throw buildResult.error;
  if ((buildResult.status ?? 1) !== 0) process.exit(buildResult.status ?? 1);

  const wranglerArgs = [
    "--import", "./scripts/sites-env.mjs",
    "./node_modules/wrangler/bin/wrangler.js",
    "dev",
    "--config", "dist/server/wrangler.json",
    "--local",
    "--persist-to", ".wrangler/state",
    "--ip", "127.0.0.1",
    "--port", port,
    "--inspector-port", "0",
  ];
  if (process.env.LAYA_BACKEND_URL) {
    wranglerArgs.push("--var", `LAYA_BACKEND_URL:${process.env.LAYA_BACKEND_URL}`);
  }
  wranglerArgs.push(...passthrough);

  const child = spawn(
    process.execPath,
    wranglerArgs,
    { cwd: uiRoot, stdio: "inherit" },
  );
  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => {
      if (!child.killed) child.kill(signal);
    });
  }
  child.on("error", (error) => {
    throw error;
  });
  child.on("exit", (code, signal) => {
    if (signal) process.exit(1);
    process.exit(code ?? 0);
  });
} else {
  // Import in this process so the preview owner retains its PID and signals.
  const cli = new URL(managedLinux
    ? "../node_modules/vite/bin/vite.js"
    : "../node_modules/vinext/dist/cli.js", import.meta.url);
  process.argv = [process.execPath, fileURLToPath(cli), command,
    ...(!managedLinux && command === "dev" ? ["--port", "5173"] : []), ...args];
  await import(cli.href);
}
