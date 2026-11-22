#!/usr/bin/env node
import { createBackup, restoreBackup } from '../src/lib/backup.ts'

const [action, input, output] = process.argv.slice(2)
if (action === 'create' && input) {
  console.log(JSON.stringify(await createBackup(input, output), null, 2))
} else if (action === 'restore' && input) {
  console.log(JSON.stringify(await restoreBackup(input), null, 2))
} else {
  console.error('usage: pnpm run backup -- create <state-file> [backup-file] | restore <manifest-file>')
  process.exitCode = 1
}
