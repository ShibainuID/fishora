// Generate lib/api/schema.d.ts from the live server, or from create_main_app().
import { spawnSync } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(here, '..')
const repoRoot = resolve(frontendRoot, '../..')
const outFile = resolve(frontendRoot, 'lib/api/schema.d.ts')

mkdirSync(dirname(outFile), { recursive: true })

const live = spawnSync(
  'pnpm',
  ['exec', 'openapi-typescript', 'http://localhost:8000/openapi.json', '-o', 'lib/api/schema.d.ts'],
  { cwd: frontendRoot, encoding: 'utf8', shell: true }
)

if (live.status === 0) {
  process.stdout.write(live.stdout)
  process.exit(0)
}

process.stderr.write(
  'Live OpenAPI unavailable; dumping schema from create_main_app().openapi()\n'
)

const python =
  process.platform === 'win32'
    ? resolve(repoRoot, '.venv/Scripts/python.exe')
    : resolve(repoRoot, '.venv/bin/python')

const py = spawnSync(
  python,
  [
    '-c',
    'from apps.main_api.main import create_main_app; import json; print(json.dumps(create_main_app().openapi()))',
  ],
  { cwd: repoRoot, encoding: 'utf8' }
)

if (py.status !== 0) {
  process.stderr.write(py.stderr)
  process.exit(py.status ?? 1)
}

const tmp = resolve(frontendRoot, 'lib/api/openapi.json')
writeFileSync(tmp, py.stdout)
const dumped = spawnSync(
  'pnpm',
  ['exec', 'openapi-typescript', tmp, '-o', 'lib/api/schema.d.ts'],
  { cwd: frontendRoot, encoding: 'utf8', shell: true }
)
process.stdout.write(dumped.stdout)
process.stderr.write(dumped.stderr)
process.exit(dumped.status ?? 1)
