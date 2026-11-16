/** Provenance boundary for free text that may be shown to an LLM or user. */
export type EvidenceSource = 'news' | 'github' | 'agent' | 'user' | 'tool' | 'unknown'

export interface UntrustedText {
  kind: 'untrusted-evidence'
  source: EvidenceSource
  trusted: false
  text: string
}

const MAX_ENVELOPE_CHARS = 20_000

function cleanText(value: string): string {
  return [...value.normalize('NFKC')].filter(character => {
    if (character === '\n' || character === '\t') return true
    const codePoint = character.codePointAt(0) ?? 0
    return codePoint > 0x1f && (codePoint < 0x7f || codePoint > 0x9f)
  }).join('')
}

/** Validate and normalize text at an untrusted boundary with a caller-owned limit. */
export function normalizeUntrustedText(value: unknown, maxChars: number): string {
  if (typeof value !== 'string') throw new Error('untrusted evidence must be a string')
  if (!Number.isSafeInteger(maxChars) || maxChars < 1) throw new Error('evidence character limit must be positive')
  if (value.length > maxChars) throw new Error(`untrusted evidence must be at most ${maxChars} characters`)
  const text = cleanText(value).trim()
  if (text.length === 0) throw new Error('untrusted evidence must not be empty')
  if (text.length > maxChars) throw new Error(`untrusted evidence must be at most ${maxChars} characters`)
  return text
}

/** Return a bounded provenance envelope; the content remains data, never policy. */
export function evidenceEnvelope(value: unknown, source: EvidenceSource = 'unknown'): UntrustedText {
  if (typeof value !== 'string') throw new Error('untrusted evidence must be a string')
  return {
    kind: 'untrusted-evidence',
    source,
    trusted: false,
    text: cleanText(value.slice(0, MAX_ENVELOPE_CHARS)),
  }
}
