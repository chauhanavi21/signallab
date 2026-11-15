/* All Python and SQLite execution is confined to this tab's worker. */
importScripts("./vendor/pyodide.js");
const boot = (async () => {
  const python = await loadPyodide({ indexURL: "./vendor/" });
  await python.loadPackage(["sqlite3", "hashlib"]);
  for (const name of ["core.py", "server.py", "httpkit.py", "bridge.py"]) {
    const response = await fetch(`./${name}`);
    if (!response.ok) throw new Error(`Missing Python source: ${name}`);
    python.FS.writeFile(`/home/pyodide/${name}`, await response.text());
  }
  await python.runPythonAsync(
    "import sys; sys.path.insert(0, '/home/pyodide'); from bridge import dispatch",
  );
  const dispatch = python.globals.get("dispatch");
  self.postMessage({ ready: true, version: python.version });
  return { python, dispatch };
})();
boot.catch((error) => self.postMessage({ fatal: String(error) }));
let queue = Promise.resolve();
self.onmessage = ({ data }) => {
  queue = queue.then(async () => {
    try {
      const { dispatch } = await boot;
      const response = JSON.parse(dispatch(JSON.stringify(data)));
      self.postMessage({ id: data.id, ...response });
    } catch (error) {
      self.postMessage({ id: data.id, error: String(error) });
    }
  });
};
