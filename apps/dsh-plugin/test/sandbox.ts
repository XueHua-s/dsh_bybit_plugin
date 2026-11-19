import assert from 'node:assert/strict'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { runAlgorithmSandbox, SANDBOX_IMAGE } from '../src/lib/sandbox.ts'

assert.equal(
  SANDBOX_IMAGE,
  'node:22.20.0-alpine@sha256:dbcedd8aeab47fbc0f4dd4bffa55b7c3c729a707875968d467aaaea42d6225af',
)

const directory = await mkdtemp(join(tmpdir(), 'bybit-quant-host-secret-'))
const hostOnlyFile = join(directory, 'sentinel.txt')
try {
  const fs = await import('node:fs/promises')
  await fs.writeFile(hostOnlyFile, 'must stay outside the sandbox')
  const result = await runAlgorithmSandbox({
    code: `import fs from 'node:fs'; export default async () => {
      const net = await import('node:net');
      const network = await new Promise(resolve => {
        const socket = net.connect(80, '1.1.1.1');
        socket.setTimeout(500, () => { socket.destroy(); resolve(true); });
        socket.once('connect', () => { socket.destroy(); resolve(true); });
        socket.once('error', () => resolve(false));
      });
      let rootWritable = true;
      try { fs.writeFileSync('/etc/bybit-quant-escape', 'x'); } catch { rootWritable = false; }
      return { hostFileVisible: fs.existsSync(${JSON.stringify(hostOnlyFile)}), network, rootWritable };
    }`,
  })
  assert.equal(result.ok, true, result.error)
  assert.deepEqual(JSON.parse(result.output), { hostFileVisible: false, network: false, rootWritable: false })
  console.log('ok generated code runs with no host filesystem, network, or writable root')
} finally {
  await rm(directory, { recursive: true, force: true })
}
