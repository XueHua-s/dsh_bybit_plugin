import { execFileSync } from 'node:child_process'

const mode = process.argv[2]
const maxBuffer = 64 * 1024 * 1024

function fail(message: string): never {
  console.error(`[git-hooks] ${message}`)
  process.exit(1)
}

// Never interpolate argv into a shell, or expose child errors containing input.
function captured(command: string, args: string[], input?: string): string {
  try {
    return execFileSync(command, args, {
      encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], maxBuffer,
      ...(input === undefined ? {} : { input }),
    })
  } catch {
    return fail(`${command} failed or is unavailable; checks remain blocked.`)
  }
}

function check(command: string, args: string[], label: string): void {
  console.log(`[git-hooks] ${label}`)
  try {
    execFileSync(command, args, { stdio: 'inherit' })
  } catch {
    fail(`${label} failed or is unavailable.`)
  }
}

function sensitivePath(path: string): boolean {
  return path.split('/').some(part =>
    /^\.env/i.test(part) ||
    /\.(?:pem|key|p12|pfx|secret|env)$/i.test(part) ||
    /^(?:\.?credentials?|\.?secrets?)(?:\.(?:json|ya?ml|toml|ini|env))?$/i.test(part),
  )
}

// Filename rejection precedes reading the diff, including for nested .env files.
// Scanner diagnostics stay private even if a broken scanner ignores --redact.
function scanStaged(files: string[]): void {
  if (files.some(sensitivePath)) fail('Sensitive staged path detected; remove it from the index. Contents were not read.')
  const diff = captured('git', ['diff', '--cached', '--no-ext-diff', '--no-textconv', '--unified=0', '--'])
  captured('gitleaks', ['stdin', '--redact', '--no-banner', '--ignore-gitleaks-allow'], diff)
}

function preCommit(): void {
  const files = captured('git', ['diff', '--cached', '--name-only', '-z', '--diff-filter=ACMR', '--'])
    .split('\0').filter(Boolean)
  scanStaged(files)
  const typescript = files.filter(path => /^(?:apps\/|packages\/ts\/|scripts\/)/.test(path) && /\.(?:ts|tsx|mts|cts)$/.test(path))
  const python = files.filter(path => path.startsWith('python/') && path.endsWith('.py'))
  const sources = [...typescript, ...python]
  // Linters inspect disk. Reject partial staging instead of silently checking
  // different bytes or stashing/restoring the user's worktree and index.
  if (sources.length && captured('git', ['diff', '--name-only', '-z', '--', ...sources])) {
    fail('Staged source paths also have unstaged edits; stage the intended complete files before linting.')
  }
  if (typescript.length) check('pnpm', ['exec', 'oxlint', '--', ...typescript], 'Lint staged TypeScript paths')
  if (python.length) {
    const uv = ['run', '--project', 'python', '--locked', 'ruff']
    check('uv', [...uv, 'check', '--', ...python], 'Lint staged Python paths')
    check('uv', [...uv, 'format', '--check', '--', ...python], 'Check staged Python formatting')
  }
  check('pnpm', ['run', 'typecheck'], 'Typecheck workspace')
  check('pnpm', ['run', 'typecheck:tooling'], 'Strict typecheck hook tooling')
}

function prePush(): void {
  console.log('[git-hooks] Scan committed history (redacted; scanner errors block push)')
  captured('gitleaks', ['git', '--redact', '--no-banner', '--ignore-gitleaks-allow'])
  for (const [script, label] of [
    ['verify', 'Verify workspace (tsdown build, lint, strict types, Mock unit tests, Bundle)'],
    ['typecheck:tests', 'Typecheck TypeScript tests'],
    ['python:lint', 'Lint Python workspace'],
    ['python:typecheck', 'Typecheck Python workspace'],
    ['python:test', 'Test Python workspace with local fixtures'],
  ] as const) {
    check('pnpm', ['run', script], label)
  }
}

if (mode === 'pre-commit') preCommit()
else if (mode === 'pre-push') prePush()
else fail('Expected pre-commit or pre-push mode.')
console.log(`[git-hooks] ${mode} checks passed.`)
