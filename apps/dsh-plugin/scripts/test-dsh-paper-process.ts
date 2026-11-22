import { spawn, spawnSync } from 'node:child_process'
import type { ChildProcess } from 'node:child_process'
import { chmodSync, existsSync, mkdtempSync, realpathSync, rmSync } from 'node:fs'
import { createConnection, createServer } from 'node:net'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { setTimeout as delay } from 'node:timers/promises'
import { createQuantApiClient } from '@bybit-quant/quant-api-client'
import type { PaperAiCycleReceipt, PaperCommand, PaperResult, PaperStatus, PaperSubmitRequest } from '@bybit-quant/quant-api-client'
import { apply } from '../dist/index.js'
import { createPaperCapabilityProvider } from '../dist/lib/paper-capability.js'
import type { PluginContext, ToolDefinition } from '../src/host-runtime.ts'

// Only trusted fixed fixtures run in Python. No user environment, profile, database or exchange is used.
process.env = {}
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const python = join(root, 'python/.venv/bin/python')
const directory = mkdtempSync(join(realpathSync(process.platform === 'darwin' ? '/private/tmp' : '/tmp'), 'bqe-'))
chmodSync(directory, 0o700)
const database = join(directory, 'paper.sqlite')
const socketPath = join(directory, 's')
const sessionId = 'dsh-process-fixture'
const environment = { PATH: `${dirname(python)}:/usr/bin:/bin`, LANG: 'C.UTF-8' }
const privateOutput: Buffer[] = []
const capabilities = new Set<string>()
const hosts: Host[] = []
const services: Service[] = []
const providers: ReturnType<typeof createPaperCapabilityProvider>[] = []
const clients: ReturnType<typeof createQuantApiClient>[] = []
const originalFetch = globalThis.fetch
let origin = ''
let stage = 'temporary_database'
let passed = false
type Identity = { pid: number, created: number, role: 'native' | 'tracker' }
type Exit = { code: number | null, signal: NodeJS.Signals | null }
type Service = { child: ChildProcess, exit: Promise<Exit>, children: Identity[] }
type AiHarness = {
  releaseCreation(): void
  completion: Promise<Record<string, unknown>>
  run?: (cycleId: string) => Promise<Record<string, unknown>>
  queryCycle?: (requestId: string) => Promise<PaperAiCycleReceipt>
}
type Host = { call(name: string, args?: Record<string, unknown>): Promise<Record<string, unknown>>, close(): Promise<void> }

class VerificationFailure extends Error {}
function check(value: unknown, message: string): asserts value { if (!value) throw new VerificationFailure(message) }
function undisclosed(value: string | Buffer): boolean {
  return [...capabilities].every(capability => !value.includes(capability))
}
function pythonFixture(arguments_: string[]): string {
  const result = spawnSync(python, arguments_, { cwd: directory, env: environment, encoding: 'utf8', timeout: 5000, maxBuffer: 1048576 })
  privateOutput.push(Buffer.from(result.stdout ?? ''), Buffer.from(result.stderr ?? ''))
  check(result.status === 0 && result.error === undefined, 'trusted_fixture_failed')
  return result.stdout
}
async function bounded<T>(promise: Promise<T>, milliseconds: number, message: string): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined
  try { return await Promise.race([promise, new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error(message)), milliseconds) })]) }
  finally { clearTimeout(timer) }
}
function object(value: unknown): Record<string, unknown> {
  check(value !== null && typeof value === 'object' && !Array.isArray(value), 'expected_object')
  return value as Record<string, unknown>
}
function decode(value: string): unknown { return JSON.parse(value) as unknown }
function hostData<T extends PaperStatus | PaperCommand>(result: Record<string, unknown>): T {
  check(result.ok === true && result.environment === 'internal_paper' && result.synthetic === true
    && result.source === 'quant-engine-paper' && result.configured === true, 'scoped_host_success_required')
  const data = object(result.data)
  check(data.session_id === sessionId && data.environment === 'internal_paper', 'host_session_binding')
  return data as T
}
function sdkData<T>(result: PaperResult<T>): T { check(result.ok, 'sdk_success_required'); return result.data }
function capture(value: string): void { privateOutput.push(Buffer.from(value)) }

function host(config: Record<string, unknown> = {}, aiHarness?: AiHarness): Host {
  const tools = new Map<string, ToolDefinition>()
  const disposers: Array<() => void | Promise<void>> = []
  let releaseCreation!: () => void
  const creation = new Promise<void>(resolve => { releaseCreation = resolve })
  let completeCycle!: (value: Record<string, unknown>) => void
  const completion = new Promise<Record<string, unknown>>(resolve => { completeCycle = resolve })
  if (aiHarness !== undefined) {
    aiHarness.releaseCreation = releaseCreation
    aiHarness.completion = completion
    aiHarness.run = async cycleId => {
      const execute = async (name: string, args: Record<string, unknown> = {}) => {
        const definition = tools.get(name)
        check(definition !== undefined, `ai_tool_missing:${name}`)
        return object(await definition.execute(args, {}))
      }
      const deadline = performance.now() + 12_000
      while (true) {
        const status = await execute('quant_get_paper_status')
        const data = status.ok === true ? object(status.data) : undefined
        if (data?.state === 'running') break
        check(performance.now() < deadline, 'ai_paper_running_deadline')
        await delay(30)
      }
      const discovered = await execute('quant_brief')
      check(discovered.brief === null, 'ai_discovery_must_be_brief_free')
      const universe = object(discovered.candidateUniverse)
      check(universe.status === 'fresh' && universe.category === 'linear' && universe.eligibleCount === 1, 'ai_fixture_universe_required')
      const candidates = universe.candidates
      check(Array.isArray(candidates) && candidates.length === 1, 'ai_fixture_candidate_count')
      const candidate = object(candidates[0])
      check(candidate.symbol === 'BTCUSDT', 'ai_fixture_candidate_symbol')
      const detailed = await execute('quant_brief', { symbols: ['BTCUSDT'] })
      const selected = detailed.selectedCandidates
      check(Array.isArray(selected) && selected.length === 1, 'ai_selected_candidate_required')
      const selectedCandidate = object(selected[0])
      check(selectedCandidate.symbol === 'BTCUSDT', 'ai_selected_symbol_required')
      const evidenceValues = selectedCandidate.selector_evidence
      check(Array.isArray(evidenceValues) && evidenceValues.length > 0, 'ai_selector_evidence_required')
      const evidence = object(evidenceValues[0])
      const decision = await execute('quant_decide_background', {
        cycleId,
        symbol: 'BTCUSDT',
        action: 'long',
        strategyId: evidence.strategy_id,
        strategyVersion: evidence.version,
        evidenceDigest: evidence.evidence_digest,
        targetExposure: 0.1,
      })
      completeCycle(decision)
      return decision
    }
  }
  const effect: PluginContext['effect'] = factory => { const dispose = factory(); if (dispose) disposers.push(dispose) }
  const ctx: PluginContext = {
    tools: { register: definition => { tools.set(definition.name, definition) } }, effect,
    systemPrompt: { section: () => {} },
    credentials: { resolve: async () => { throw new Error('exchange_credentials_forbidden') } },
    logger: () => ({ info: capture, warn: capture, error: capture }),
    inject: (_dependencies, callback) => callback({
      effect,
      connection: { fetch: { register: () => async () => {} } },
      ...(aiHarness === undefined ? {} : {
        agents: {
          create: async (options: { sessionId: string, setup(context: { tools: { restrict(filter: { allow: readonly string[] }): unknown }, systemPrompt: { section(section: { name: string, order: number, text: string }): unknown } }): void }) => {
            options.setup({ tools: { restrict: () => {} }, systemPrompt: { section: () => {} } })
            await creation
            let idleResolve!: () => void
            const idle = new Promise<void>(resolve => { idleResolve = resolve })
            let started = false
            const agent = {
              followup: () => {
                if (started) return
                started = true
                void aiHarness.run?.(options.sessionId).then(idleResolve, error => {
                  completeCycle({ ok: false, code: error instanceof Error ? error.message : 'ai_cycle_failed' })
                  idleResolve()
                })
              },
              cancel: () => { idleResolve() },
              whenIdle: () => idle,
            }
            return { agent, dispose: async () => { idleResolve() } }
          },
        },
        agentDefaultModel: { currentSelection: () => ({ provider: 'paper-test', model: 'paper-test-model' }) },
      }),
    }),
  }
  apply(ctx, {
    ...config,
    paperBaseUrl: origin, paperSessionId: sessionId, paperCapabilitySocket: socketPath, paperControlEnabled: true,
    aiEnabled: true, aiBackgroundEnvironment: 'internal_paper', aiBackgroundLoopEnabled: aiHarness !== undefined,
    paperFixtureId: 'builtin-synthetic',
    credentialsFile: join(directory, 'nonexistent-credentials.json'), stateFile: join(directory, `host-${hosts.length}.json`),
  })
  let closed = false
  const value: Host = {
    async call(name, arguments_ = {}) {
      check(!closed, 'test_host_closed')
      const tool = tools.get(name)
      check(tool, 'paper_tool_missing')
      const result = object(await tool.execute(arguments_, {}))
      const serialized = JSON.stringify(result)
      capture(serialized)
      check(undisclosed(serialized), 'tool_capability_disclosure')
      return result
    },
    async close() { if (closed) return; closed = true; for (const dispose of disposers.toReversed()) await dispose() },
  }
  hosts.push(value)
  return value
}

async function freePort(): Promise<number> {
  const listener = createServer()
  await new Promise<void>((accept, reject) => { listener.once('error', reject); listener.listen(0, '127.0.0.1', accept) })
  const address = listener.address()
  check(address !== null && typeof address !== 'string', 'temporary_port_required')
  await new Promise<void>((accept, reject) => listener.close(error => error ? reject(error) : accept()))
  return address.port
}
async function listenerClosed(): Promise<void> {
  const connected = await new Promise<boolean>(accept => {
    const peer = createConnection({ host: '127.0.0.1', port: Number(new URL(origin).port) })
    const finish = (open: boolean) => { peer.destroy(); accept(open) }
    peer.once('connect', () => finish(true)); peer.once('error', () => finish(false)); peer.setTimeout(500, () => finish(true))
  })
  check(!connected, 'http_listener_not_closed')
}
async function startService(config: Record<string, unknown> = {}, aiHarness?: AiHarness): Promise<{ service: Service, host: Host }> {
  const port = await freePort()
  origin = `http://127.0.0.1:${port}`
  const child = spawn(python, ['-m', 'quant_engine.paper_bootstrap', '--database', database, '--session', sessionId,
    '--host', '127.0.0.1', '--port', String(port), '--capability-socket', socketPath],
  { cwd: directory, env: environment, stdio: ['ignore', 'pipe', 'pipe'] })
  child.stdout?.on('data', (chunk: Buffer) => privateOutput.push(chunk))
  child.stderr?.on('data', (chunk: Buffer) => privateOutput.push(chunk))
  let spawnError = false
  child.once('error', () => { spawnError = true })
  const service: Service = { child, children: [], exit: new Promise<Exit>(accept => child.once('close', (code, signal) => accept({ code, signal }))) }
  services.push(service)
  const value = host(config, aiHarness)
  const deadline = performance.now() + 12000
  while (true) {
    check(!spawnError && child.exitCode === null && child.signalCode === null, 'paper_cli_exited_before_ready')
    const status = await value.call('quant_get_paper_status')
    if (status.ok === true) {
      const observer = createPaperCapabilityProvider({ origin, sessionId, socketPath })
      providers.push(observer)
      capabilities.add(await observer.resolve())
      if (aiHarness !== undefined) {
        const queryClient = createQuantApiClient({ baseUrl: origin, timeoutMs: 5000, serviceCapability: () => observer.resolve() })
        clients.push(queryClient)
        aiHarness.queryCycle = async requestId => {
          const result = await queryClient.paper.cycleRequest(requestId)
          check(result.ok, 'ai_cycle_query_failed')
          return result.data
        }
      }
      break
    }
    check(performance.now() < deadline, 'paper_cli_startup_deadline')
    await delay(30)
  }
  return { service, host: value }
}

// psutil's creation time disambiguates PID reuse. Only an exact unflagged stdlib tracker gets relaxed exit semantics.
function captureChildren(service: Service): Identity[] {
  check(service.child.pid !== undefined, 'service_pid_missing')
  const value = decode(pythonFixture(['-c', `import json,psutil,re,sys
result=[]
for child in psutil.Process(int(sys.argv[1])).children(recursive=True):
    args=child.cmdline()
    tracker=len(args)==3 and args[:2]==[sys.executable,'-c'] and re.fullmatch(r'from multiprocessing\\.resource_tracker import main;main\\([0-9]+\\)',args[2]) is not None
    result.append({'pid':child.pid,'created':child.create_time(),'role':'tracker' if tracker else 'native'})
print(json.dumps(result))`, String(service.child.pid)]))
  check(Array.isArray(value), 'child_observation_invalid')
  const identities = value.map(item => {
    const row = object(item)
    check(typeof row.pid === 'number' && Number.isInteger(row.pid) && row.pid > 0 && typeof row.created === 'number'
      && (row.role === 'native' || row.role === 'tracker'), 'child_identity_invalid')
    return { pid: row.pid, created: row.created, role: row.role } as Identity
  })
  check(identities.some(item => item.role === 'native') && identities.some(item => item.role === 'tracker'), 'native_and_tracker_must_be_observed')
  service.children = identities
  return identities
}
function childStates(identities: Identity[], kill = false): Array<{ role: string, state: string }> {
  const value = decode(pythonFixture(['-c', `import json,psutil,sys
result=[]
for row in json.loads(sys.argv[1]):
    state='gone'
    try:
        child=psutil.Process(row['pid'])
        if child.create_time()==row['created']:
            if sys.argv[2]=='kill': child.kill()
            state=child.status()
    except psutil.NoSuchProcess: pass
    result.append({'role':row['role'],'state':state})
print(json.dumps(result))`, JSON.stringify(identities), kill ? 'kill' : 'observe']))
  check(Array.isArray(value), 'child_state_invalid')
  return value.map(item => { const row = object(item); check(typeof row.role === 'string' && typeof row.state === 'string', 'child_state_invalid'); return { role: row.role, state: row.state } })
}
function nativeReaped(service: Service): void {
  check(childStates(service.children.filter(item => item.role === 'native')).every(item => item.state === 'gone'), 'native_not_reaped')
}
async function terminate(service: Service): Promise<void> {
  if (service.child.exitCode === null && service.child.signalCode === null) service.child.kill('SIGTERM')
  const exit = await bounded(service.exit, 12000, 'paper_cli_shutdown_deadline')
  check(exit.code === 0 || exit.signal === 'SIGTERM', 'paper_cli_shutdown_failed')
  nativeReaped(service)
  const deadline = performance.now() + 3000
  while (childStates(service.children.filter(item => item.role === 'tracker')).some(item => !['gone', 'zombie'].includes(item.state))) {
    check(performance.now() < deadline, 'resource_tracker_shutdown_deadline')
    await delay(10)
  }
  check(!existsSync(socketPath), 'unix_listener_not_removed')
  await listenerClosed()
}
async function filled(value: Host, requestId: string, expected: PaperCommand): Promise<PaperCommand> {
  const deadline = performance.now() + 8000
  while (true) {
    const command = hostData<PaperCommand>(await value.call('quant_get_paper_command', { request_id: requestId }))
    check(command.command_id === expected.command_id && command.native_client_order_id === expected.native_client_order_id, 'command_identity_changed')
    if (command.state === 'filled') { check(command.cumulative_filled === '0.001', 'native_fill_quantity'); return command }
    check(!['rejected', 'risk_rejected', 'reconciliation_required'].includes(command.state) && performance.now() < deadline, 'native_fill_deadline')
    await delay(30)
  }
}
async function statusUntil(value: Host, expected: PaperStatus['state'], milliseconds = 12000): Promise<PaperStatus> {
  const deadline = performance.now() + milliseconds
  while (true) {
    const result = await value.call('quant_get_paper_status')
    if (result.ok === true) {
      const observed = hostData<PaperStatus>(result)
      if (observed.state === expected) return observed
    }
    check(performance.now() < deadline, `status_${expected}_deadline`)
    await delay(30)
  }
}
const proposal = (request_id: string) => ({ request_id, symbol: 'BTCUSDT', side: 'buy', quantity: '0.001', limit_price: '50000' })

try {
  check(process.platform === 'darwin' || process.platform === 'linux', 'posix_platform_required')
  check(existsSync(python), 'locked_python_environment_required')
  const migrationHead = pythonFixture(['-c', "from alembic.script import ScriptDirectory; from quant_data.migrations import migration_config; print(ScriptDirectory.from_config(migration_config()).get_current_head())"]).trim()
  pythonFixture(['-c', "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('PRAGMA user_version=0'); c.close()", database])
  pythonFixture(['-m', 'quant_data.migrations', database])
  check(pythonFixture(['-c', "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute('select version_num from alembic_version').fetchone()[0]); c.close()", database]).trim() === migrationHead, 'temporary_schema_required')
  globalThis.fetch = async (input, init) => {
    const request = new Request(input, init)
    check(new URL(request.url).origin === origin && new URL(request.url).pathname.startsWith('/api/v1/trading/'), 'nonpaper_network_forbidden')
    check(!request.headers.has('origin') && !request.headers.has('cookie') && !request.headers.has('x-bapi-api-key'), 'ambient_authority_forbidden')
    return originalFetch(request)
  }
  stage = 'built_host_unix_sdk_cli_start'
  const aiHarness: AiHarness = {} as AiHarness
  const first = await startService({}, aiHarness)
  let status = hostData<PaperStatus>(await first.host.call('quant_get_paper_status'))
  check(status.state === 'idle' && !status.ready && !status.native_process_alive, 'initial_idle_required')
  const startResult = await first.host.call('quant_start_paper')
  if (startResult.ok === true) status = hostData<PaperStatus>(startResult)
  else check(startResult.code === 'outcome_uncertain', 'native_start_failure')
  // An uncertain mutation is recovered by observation only; it is never resent.
  status = await statusUntil(first.host, 'running')
  check(status.ready && status.native_process_alive, 'native_start_required')
  const children = captureChildren(first.service)
  const provider = createPaperCapabilityProvider({ origin, sessionId, socketPath })
  providers.push(provider)
  const privateCapability = async () => { const capability = await provider.resolve(); capabilities.add(capability); return capability }
  await privateCapability()
  const unauthenticated = await originalFetch(`${origin}/api/v1/trading/status`, { signal: AbortSignal.timeout(1000) })
  check(unauthenticated.status === 401, 'unauthenticated_http_must_fail'); await unauthenticated.body?.cancel()
  stage = 'stable_ids_idempotency_conflict_native_fills'
  const input = proposal('first-request')
  const receipt = hostData<PaperCommand>(await first.host.call('quant_submit_paper_order', input))
  await filled(first.host, input.request_id, receipt)
  const same = hostData<PaperCommand>(await first.host.call('quant_submit_paper_order', input))
  check(same.command_id === receipt.command_id && same.native_client_order_id === receipt.native_client_order_id, 'duplicate_identity_changed')
  const conflict = await first.host.call('quant_submit_paper_order', { ...input, quantity: '0.002' })
  check(conflict.ok === false && conflict.code === 'conflict' && conflict.status === 409, 'changed_request_must_conflict')
  const later = proposal('later-request')
  const laterReceipt = hostData<PaperCommand>(await first.host.call('quant_submit_paper_order', later))
  check(laterReceipt.command_id !== receipt.command_id && laterReceipt.native_client_order_id !== receipt.native_client_order_id, 'later_command_identity_required')
  await filled(first.host, later.request_id, laterReceipt)
  stage = 'injected_postdispatch_503_original_request_recovery'
  let submitPosts = 0
  let dispatched: PaperCommand | undefined
  const sdk = createQuantApiClient({ baseUrl: origin, timeoutMs: 5000, serviceCapability: privateCapability,
    fetch: async (input_, init) => {
      const request = new Request(input_, init)
      const response = await globalThis.fetch(request)
      if (request.method === 'POST') {
        check(new URL(request.url).pathname === '/api/v1/trading/commands', 'fault_probe_submit_only')
        submitPosts++
        check(response.status === 202, 'real_dispatch_202_required_before_injection')
        dispatched = object(await response.json()) as PaperCommand
        check(dispatched.session_id === sessionId && typeof dispatched.command_id === 'string' && typeof dispatched.native_client_order_id === 'string', 'real_dispatch_receipt_required')
        return Response.json({ detail: 'service_unavailable' }, { status: 503 })
      }
      return response
    },
  })
  clients.push(sdk)
  const faultInput: PaperSubmitRequest = { ...proposal('postdispatch-request'), environment: 'internal_paper', session_id: sessionId, order_type: 'limit', symbol: 'BTCUSDT', side: 'buy' }
  const uncertain = await sdk.paper.submit(faultInput)
  check(!uncertain.ok && uncertain.code === 'outcome_uncertain' && uncertain.cause === 'unavailable'
    && uncertain.recovery.action === 'query_request' && uncertain.recovery.request_id === faultInput.request_id, 'postdispatch_503_must_preserve_original_recovery')
  check(dispatched !== undefined && submitPosts === 1, 'exactly_one_actual_submit_required')
  const recovered = sdkData(await sdk.paper.request(faultInput.request_id))
  check(recovered.command_id === dispatched.command_id && recovered.native_client_order_id === dispatched.native_client_order_id, 'postdispatch_recovery_identity_changed')
  await filled(first.host, faultInput.request_id, dispatched)
  check(submitPosts === 1, 'recovery_must_never_resubmit')
  stage = 'real_risk_veto_and_durable_native_evidence'
  const rejected = hostData<PaperCommand>(await first.host.call('quant_submit_paper_order', { ...proposal('risk-veto-request'), quantity: '0.1' }))
  check(rejected.state === 'risk_rejected' && rejected.cumulative_filled === '0', 'real_risk_veto_required')
  const proof = object(decode(pythonFixture(['-c', `import json,sqlite3,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
queries={'commands':'select count(*) from execution_commands','filled':"select count(*) from execution_commands where state='filled'",'risk_rejected':"select count(*) from execution_commands where state='risk_rejected'",'allowed':'select count(*) from admission_decisions where allowed=1','denied':'select count(*) from admission_decisions where allowed=0','native_filled':"select count(distinct command_id) from paper_native_events where state='filled' and applied=1",'dispatches':"select count(*) from command_events where event_id='internal:dispatch'"}
print(json.dumps({key:c.execute(query).fetchone()[0] for key,query in queries.items()})); c.close()`, database])))
  check(proof.commands === 4 && proof.filled === 3 && proof.risk_rejected === 1 && proof.allowed === 3 && proof.denied === 1
    && proof.native_filled === 3 && proof.dispatches === 3, 'durable_native_risk_evidence_required')
  stage = 'host_ai_internal_paper_cycle_receipt'
  // The scheduler is opt-in and receives a fake Agent only for this process
  // test. The model-facing tools still execute through the real Host and the
  // real Python fixture/cycle service.
  aiHarness.releaseCreation()
  const aiDecision = await bounded(aiHarness.completion, 15_000, 'ai_cycle_completion_deadline')
  check(aiDecision.accepted === true && aiDecision.status === 'open', `ai_decision_receipt_status:${JSON.stringify(aiDecision)}`)
  const paperReceipt = object(aiDecision.paperReceipt)
  check(paperReceipt.status === 'filled' && typeof paperReceipt.request_id === 'string'
    && typeof paperReceipt.payload_digest === 'string' && typeof paperReceipt.decision_id === 'string', 'ai_paper_receipt_required')
  const decisionReceipt = object(aiDecision.decisionReceipt)
  check(decisionReceipt.status === 'open' && decisionReceipt.decisionId === paperReceipt.decision_id, 'ai_scheduler_receipt_binding')
  check(typeof aiHarness.queryCycle === 'function', 'ai_cycle_query_client_required')
  const recoveredCycle = await aiHarness.queryCycle(String(paperReceipt.request_id))
  check(recoveredCycle.request_id === paperReceipt.request_id
    && recoveredCycle.payload_digest === paperReceipt.payload_digest
    && recoveredCycle.decision_id === paperReceipt.decision_id
    && recoveredCycle.status === paperReceipt.status, 'ai_cycle_original_request_recovery')
  stage = 'host_close_independent_service_and_stop_reaping'
  await first.host.close()
  status = sdkData(await sdk.paper.status())
  check(status.state === 'running' && status.native_process_alive, 'host_close_must_preserve_service_and_native')
  const reopenedHost = host()
  const stopResult = await reopenedHost.call('quant_stop_paper')
  if (stopResult.ok === true) status = hostData<PaperStatus>(stopResult)
  else check(stopResult.code === 'outcome_uncertain', 'native_stop_failure')
  status = await statusUntil(reopenedHost, 'stopped')
  check(status.state === 'stopped' && !status.ready && !status.native_process_alive, 'explicit_native_stop_required')
  nativeReaped(first.service)
  await reopenedHost.close(); sdk.close(); provider.close()
  stage = 'sigterm_listeners_and_tracker_cleanup'
  await terminate(first.service)
  stage = 'protected_restart_no_replay_or_autostart'
  const restarted = await startService()
  status = hostData<PaperStatus>(await restarted.host.call('quant_get_paper_status'))
  check(status.state === 'protected' && !status.ready && !status.native_process_alive, 'restart_must_be_protected')
  const refused = await restarted.host.call('quant_start_paper')
  check(refused.ok === false && refused.code === 'outcome_uncertain' && refused.cause === 'unavailable', 'protected_restart_start_must_refuse')
  status = await statusUntil(restarted.host, 'protected')
  check(!status.native_process_alive, 'protected_restart_native_absent')
  const persisted = hostData<PaperCommand>(await restarted.host.call('quant_get_paper_command', { request_id: input.request_id }))
  check(persisted.command_id === receipt.command_id && persisted.native_client_order_id === receipt.native_client_order_id && persisted.state === 'filled', 'restart_durable_identity_required')
  await restarted.host.close()
  await terminate(restarted.service)
  check(privateOutput.every(undisclosed), 'captured_capability_disclosure')
  console.log(JSON.stringify({ result: 'ok', environment: 'internal_paper', synthetic: true, commands: 4, native_filled: 3, risk_rejected: 1,
    injected_postdispatch_503: true, actual_fault_submit_posts: submitPosts, service_pids: services.map(service => service.child.pid),
    native_pids: children.filter(item => item.role === 'native').map(item => item.pid), tracker_pids: children.filter(item => item.role === 'tracker').map(item => item.pid),
    host_close_survived: true, native_reaped: true, listeners_closed: true, restart: 'protected', capability_disclosed: false }))
  passed = true
} catch (error: unknown) {
  console.error(`not ok dsh paper process: ${stage}/${error instanceof VerificationFailure ? error.message : 'unexpected_failure'}`)
  process.exitCode = 1
} finally {
  for (const client of clients) client.close()
  for (const provider of providers) provider.close()
  for (const value of hosts) await value.close()
  for (const service of services) {
    if (service.child.exitCode === null && service.child.signalCode === null) {
      service.child.kill('SIGTERM')
      try { await bounded(service.exit, 12000, 'failure_cleanup_deadline') }
      catch { service.child.kill('SIGKILL'); await bounded(service.exit, 3000, 'failure_cleanup_kill_deadline'); process.exitCode = 1 }
    }
    if (!passed && service.children.length) childStates(service.children, true)
  }
  globalThis.fetch = originalFetch
  rmSync(directory, { recursive: true, force: true })
}
