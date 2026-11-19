import assert from 'node:assert/strict'
import { BoundedOutputCapture, SANDBOX_IMAGE } from '../src/lib/sandbox.ts'

assert.equal(
  SANDBOX_IMAGE,
  'node:22.20.0-alpine@sha256:dbcedd8aeab47fbc0f4dd4bffa55b7c3c729a707875968d467aaaea42d6225af',
)

const output = new BoundedOutputCapture(400_000)
const oversizedChunk = Buffer.alloc(2_000_000, 97)
for (let index = 0; index < 100; index += 1) output.append(oversizedChunk)

assert.equal(output.size, 400_000)
assert.equal(output.toString().length, 400_000)
assert.equal(output.toString(), 'a'.repeat(400_000))
assert.equal(output.toString().slice(0, 100_000).length, 100_000)

const errors = new BoundedOutputCapture(40_000)
errors.append('é'.repeat(30_000))
assert.equal(errors.size, 40_000)
assert.equal(errors.toString().length, 20_000)

console.log('ok sandbox output capture retains a fixed byte budget under stream flooding')
