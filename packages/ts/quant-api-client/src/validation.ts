import { Ajv2020 } from 'ajv/dist/2020.js';
import { schema } from './generated/schema.js';
import { schema as paperSchema } from './generated/paper-schema.js';
import type { components as PaperComponents } from './generated/paper-paths.js';
import type { components } from './generated/paths.js';

const ajv = new Ajv2020({ strict: false, allErrors: false, validateFormats: false });
ajv.addSchema(schema);
ajv.addSchema(paperSchema);
const validators = {
  HealthResponse: ajv.compile({ $ref: `${schema.$id}#/components/schemas/HealthResponse` }),
  SessionRequest: ajv.compile({ $ref: `${paperSchema.$id}#/components/schemas/SessionRequest` }),
  SubmitRequest: ajv.compile({ $ref: `${paperSchema.$id}#/components/schemas/SubmitRequest` }),
  PaperStatus: ajv.compile({ $ref: `${paperSchema.$id}#/components/schemas/PaperStatus` }),
  CommandResponse: ajv.compile({ $ref: `${paperSchema.$id}#/components/schemas/CommandResponse` }),
  FixtureSnapshot: ajv.compile({ $ref: `${paperSchema.$id}#/components/schemas/FixtureSnapshot` }),
  DecisionRequest: ajv.compile({ $ref: `${paperSchema.$id}#/components/schemas/DecisionRequest` }),
  CycleReceipt: ajv.compile({ $ref: `${paperSchema.$id}#/components/schemas/CycleReceipt` }),
  PaperError: ajv.compile({ $ref: `${paperSchema.$id}#/components/schemas/PaperError` }),
  MarketResponse: ajv.compile({ $ref: `${schema.$id}#/components/schemas/MarketResponse` }),
  StrategyEvidenceResponse: ajv.compile({ $ref: `${schema.$id}#/components/schemas/StrategyEvidenceResponse` }),
};

// Apply one resource policy to all untrusted wire data, without duplicating DTOs.
function bounded(value: unknown, depth = 0, key?: string): boolean {
  if (depth > 12) return false;
  if (typeof value === 'number') {
    // The paper fixture contract deliberately carries nanosecond timestamps.
    // They are larger than JS's exact-integer range, but remain bounded epoch
    // values and are never used as identifiers or monetary amounts. Keep the
    // strict safe-integer fence for every other numeric field.
    return Number.isFinite(value) && (Math.abs(value) <= Number.MAX_SAFE_INTEGER
      || (key?.endsWith('_ns') === true && Number.isInteger(value) && Math.abs(value) <= 10_000_000_000_000_000_000));
  }
  if (typeof value === 'string') return value.length <= 1024 && Array.from(value).every(character => { const code = character.charCodeAt(0); return code >= 32 || code === 9 || code === 10 || code === 13; });
  if (Array.isArray(value)) return value.length <= 256 && value.every((item: unknown) => bounded(item, depth + 1));
  if (typeof value === 'object' && value !== null) {
    const entries = Object.entries(value);
    return entries.length <= 256 && entries.every(([entryKey, child]) => entryKey.length <= 128 && !['__proto__', 'constructor', 'prototype'].includes(entryKey) && bounded(child, depth + 1, entryKey));
  }
  return value === null || typeof value === 'boolean';
}

export function validateResponse<T extends keyof typeof validators>(name: T, value: unknown): value is (components['schemas'] & PaperComponents['schemas'])[T] {
  return bounded(value) && validators[name](value);
}

const requestId = ajv.compile({ $ref: `${paperSchema.$id}#/components/schemas/SubmitRequest/properties/request_id` });
export function validateRequestId(value: unknown): value is string { return bounded(value) && requestId(value); }
