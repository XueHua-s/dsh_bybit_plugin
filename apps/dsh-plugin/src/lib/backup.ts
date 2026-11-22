import { mkdir, readFile, rename, writeFile } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { createHash } from 'node:crypto'

export interface BackupManifest {
  version: 1
  createdAt: string
  source: string
  backup: string
  sha256: string
}

/** Create a checksum-backed backup beside a state file. */
export async function createBackup(source: string, destination = `${source}.bak`): Promise<BackupManifest> {
  const content = await readFile(source)
  await mkdir(dirname(destination), { recursive: true })
  const temporary = `${destination}.tmp-${process.pid}`
  await writeFile(temporary, content, { mode: 0o600 })
  await rename(temporary, destination)
  const manifest: BackupManifest = {
    version: 1,
    createdAt: new Date().toISOString(),
    source,
    backup: destination,
    sha256: createHash('sha256').update(content).digest('hex'),
  }
  const manifestPath = join(dirname(destination), `${destination.split('/').at(-1) ?? 'state'}.manifest.json`)
  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, { mode: 0o600 })
  return manifest
}

/** Restore a checksum-backed backup after validating its manifest. */
export async function restoreBackup(manifestFile: string): Promise<BackupManifest> {
  const manifest = JSON.parse(await readFile(manifestFile, 'utf8')) as BackupManifest
  if (manifest.version !== 1 || typeof manifest.source !== 'string' || typeof manifest.backup !== 'string') throw new Error('unsupported backup manifest')
  const content = await readFile(manifest.backup)
  const sha256 = createHash('sha256').update(content).digest('hex')
  if (sha256 !== manifest.sha256) throw new Error('backup checksum mismatch; refusing restore')
  const temporary = `${manifest.source}.restore-${process.pid}`
  await writeFile(temporary, content, { mode: 0o600 })
  await rename(temporary, manifest.source)
  return manifest
}
