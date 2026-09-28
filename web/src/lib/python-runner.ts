import { spawn, ChildProcessWithoutNullStreams } from "child_process";
import path from "path";
import fs from "fs";
import { APP_DIR, PATHS } from "./paths";

export function spawnPython(
  scriptNameWithOrWithoutPy: string,
  args: string[] = [],
  customOptions: any = {}
): ChildProcessWithoutNullStreams {
  const cleanName = scriptNameWithOrWithoutPy.replace(".py", "").trim();
  const engineExe = path.join(APP_DIR, "bin", "python_engine", "python_engine.exe");
  const hasEngine = fs.existsSync(engineExe);

  const defaultEnv = {
    ...process.env,
    PYTHONUNBUFFERED: "1",
    PYTHONIOENCODING: "utf-8",
  };

  const spawnOptions = {
    cwd: APP_DIR,
    ...customOptions,
    env: { ...defaultEnv, ...(customOptions.env || {}) },
  };

  if (hasEngine) {
    return spawn(engineExe, [cleanName, ...args], spawnOptions) as unknown as ChildProcessWithoutNullStreams;
  } else {
    const scriptPath = path.join(PATHS.scripts, `${cleanName}.py`);
    return spawn("python", ["-u", scriptPath, ...args], spawnOptions) as unknown as ChildProcessWithoutNullStreams;
  }
}
