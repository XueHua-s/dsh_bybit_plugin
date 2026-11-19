#!/usr/bin/env node
import { execFileSync } from 'node:child_process'
import { writeFile } from 'node:fs/promises'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { pnpmEnvironment } from './pnpm-environment.ts'

interface PnpmPackage {
  path?: string
  name?: string
  from?: string
  version?: string
  dependencies?: Record<string, PnpmPackage>
  devDependencies?: Record<string, PnpmPackage>
  optionalDependencies?: Record<string, PnpmPackage>
  unsavedDependencies?: Record<string, PnpmPackage>
}

const packageRoot = fileURLToPath(new URL('..', import.meta.url))
const workspaceRoot = resolve(packageRoot, '../..')
const pnpm = (args: string[]) => execFileSync('pnpm', args, {
  encoding: 'utf8',
  cwd: workspaceRoot,
  env: pnpmEnvironment(),
})
const roots = JSON.parse(pnpm(['list', '--recursive', '--depth', 'Infinity', '--json', '--lockfile=false'])) as PnpmPackage[]
const workspacePackages = new Map(roots.filter(pkg => pkg.path).map(pkg => [pkg.path, pkg]))
const components = new Map<string, { type: string, name: string, version: string, purl: string }>()
const edges = new Map<string, Set<string>>()
const refOf = (name: string, version: string) => `pkg:npm/${encodeURIComponent(name).replaceAll('%2F', '/') }@${version}`

function visit(pkg: PnpmPackage, parent?: string, dependencyName?: string): void {
  const workspace = pkg.path ? workspacePackages.get(pkg.path) : undefined
  if (workspace && workspace !== pkg) pkg = workspace
  if (pkg.version?.startsWith('link:')) {
    if (!pkg.path) throw new Error('linked package metadata path is missing')
    const metadata: unknown = JSON.parse(readFileSync(resolve(pkg.path, 'package.json'), 'utf8'))
    if (typeof metadata !== 'object' || metadata === null || !('name' in metadata) || !('version' in metadata)
      || typeof metadata.name !== 'string' || typeof metadata.version !== 'string' || metadata.version.startsWith('link:')) {
      throw new Error('linked package metadata is invalid')
    }
    pkg = { ...pkg, name: metadata.name, version: metadata.version }
  }
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
    for (const [childName, dependency] of Object.entries(collection ?? {})) visit(dependency, ref, childName)
  }
}

for (const root of roots) visit(root)
const rootPackage = roots.find(pkg => pkg.path === workspaceRoot)
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
  components: [...components.entries()].sort(([a], [b]) => a.localeCompare(b)).filter(([ref]) => ref !== rootRef).map(([ref, component]) => ({ ...component, 'bom-ref': ref })),
  dependencies: [...edges.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([ref, dependencies]) => ({ ref, dependsOn: [...dependencies].sort() })),
}
await writeFile(resolve(workspaceRoot, 'sbom.cdx.json'), `${JSON.stringify(bom, null, 2)}\n`)
console.log(`Wrote CycloneDX SBOM with ${components.size - 1} npm components to sbom.cdx.json`)
