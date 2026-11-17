import { Ajv2020 } from 'ajv/dist/2020.js';
import { schema } from './generated/schema.js';
import type { components } from './generated/paths.js';

const ajv = new Ajv2020({ strict: false, allErrors: false, validateFormats: false });
ajv.addSchema(schema);
const validators = {
  HealthResponse: ajv.compile({ $ref: `${schema.$id}#/components/schemas/HealthResponse` }),
  MarketResponse: ajv.compile({ $ref: `${schema.$id}#/components/schemas/MarketResponse` }),
};

// Apply one resource policy to all untrusted wire data, without duplicating DTOs.
function bounded(value: unknown, depth = 0): boolean {
  if (depth > 12) return false;
  if (typeof value === 'number') return Number.isFinite(value) && Math.abs(value) <= Number.MAX_SAFE_INTEGER;
  if (typeof value === 'string') return value.length <= 1024 && Array.from(value).every(character => { const code = character.charCodeAt(0); return code >= 32 || code === 9 || code === 10 || code === 13; });
  if (Array.isArray(value)) return value.length <= 256 && value.every((item: unknown) => bounded(item, depth + 1));
  if (typeof value === 'object' && value !== null) {
    const entries = Object.entries(value);
    return entries.length <= 256 && entries.every(([key, child]) => key.length <= 128 && !['__proto__', 'constructor', 'prototype'].includes(key) && bounded(child, depth + 1));
  }
  return value === null || typeof value === 'boolean';
}

export function validateResponse<T extends keyof typeof validators>(name: T, value: unknown): value is components['schemas'][T] {
  return bounded(value) && validators[name](value);
}
