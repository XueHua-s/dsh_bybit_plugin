#!/usr/bin/env node
import { execFileSync } from 'node:child_process'
import { writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

interface PnpmPackage {
  name?: string
  from?: string
  version?: string
  dependencies?: Record<string, PnpmPackage>
  devDependencies?: Record<string, PnpmPackage>
  optionalDependencies?: Record<string, PnpmPackage>
  unsavedDependencies?: Record<string, PnpmPackage>
}

const pnpmEnvironment = {
  PATH: process.env.PATH,
  HOME: process.env.HOME,
  USER: process.env.USER,
  TMPDIR: process.env.TMPDIR,
  SystemRoot: process.env.SystemRoot,
  COREPACK_ENABLE_PROJECT_SPEC: '0',
  COREPACK_ENABLE_AUTO_PIN: '0',
  npm_config_manage_package_manager_versions: 'false',
}
const packageRoot = fileURLToPath(new URL('..', import.meta.url))
const workspaceRoot = resolve(packageRoot, '../..')
const pnpm = (args: string[]) => execFileSync('pnpm', args, {
  encoding: 'utf8',
  cwd: workspaceRoot,
  env: pnpmEnvironment,
})
const roots = JSON.parse(pnpm(['list', '--depth', 'Infinity', '--json', '--lockfile=false'])) as PnpmPackage[]
const components = new Map<string, { type: string, name: string, version: string, purl: string }>()
const edges = new Map<string, Set<string>>()
const refOf = (name: string, version: string) => `pkg:npm/${encodeURIComponent(name).replaceAll('%2F', '/') }@${version}`

function visit(pkg: PnpmPackage, parent?: string, dependencyName?: string): void {
  const name = pkg.name ?? pkg.from ?? dependencyName
  if (!name || !pkg.version) return
  const ref = refOf(name, pkg.version)
  components.set(ref, { type: 'library', name, version: pkg.version, purl: ref })
  if (parent) {
    const children = edges.get(parent) ?? new Set<string>()
    children.add(ref)
    edges.set(parent, children)
  }
  for (const collection of [pkg.dependencies, pkg.devDependencies, pkg.optionalDependencies, pkg.unsavedDependencies]) {
    for (const [dependencyName, dependency] of Object.entries(collection ?? {})) visit(dependency, ref, dependencyName)
  }
}

for (const root of roots) visit(root)
const rootPackage = roots[0]
if (!rootPackage?.name || !rootPackage.version) throw new Error('pnpm list did not return a workspace root package')
const rootRef = refOf(rootPackage.name, rootPackage.version)
const bom = {
  bomFormat: 'CycloneDX',
  specVersion: '1.6',
  version: 1,
  metadata: {
    timestamp: new Date().toISOString(),
    tools: { components: [{ type: 'application', name: 'pnpm', version: pnpm(['--version']).trim() }] },
    component: { type: 'application', name: rootPackage.name, version: rootPackage.version, purl: rootRef, 'bom-ref': rootRef },
  },
  components: [...components.entries()].filter(([ref]) => ref !== rootRef).map(([ref, component]) => ({ ...component, 'bom-ref': ref })),
  dependencies: [...edges.entries()].map(([ref, dependencies]) => ({ ref, dependsOn: [...dependencies].sort() })),
}
await writeFile(resolve(workspaceRoot, 'sbom.cdx.json'), `${JSON.stringify(bom, null, 2)}\n`)
console.log(`Wrote CycloneDX SBOM with ${components.size - 1} npm components to sbom.cdx.json`)
