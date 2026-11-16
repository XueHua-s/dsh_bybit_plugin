export type TestNode = { type: unknown, props: unknown, children: unknown[] }

export type ReactRuntime = {
  createElement(type: unknown, props: unknown, ...children: unknown[]): TestNode
  useState<T>(initial: T | (() => T)): [T, (next: T | ((previous: T) => T)) => void]
  useEffect(effect: () => void | (() => void), deps?: readonly unknown[]): void
  useMemo<T>(factory: () => T, deps: readonly unknown[]): T
  useCallback<T extends (...args: never[]) => unknown>(fn: T, deps: readonly unknown[]): T
}

export type LoadedBundle = {
  id: string
  factory(require: (specifier: string) => ReactRuntime): Plugin
}

export type Plugin = {
  inject: string[]
  apply(context: PluginContext): void
}

export type Registration = {
  options: Record<string, unknown>
  component: (props: Record<string, unknown>) => TestNode
}

export type PluginContext = {
  effect(factory: () => void | (() => void)): void
  locale: {
    register(namespace: string, dictionaries: { zh: Record<string, string>, en: Record<string, string> }): () => void
    bind(namespace: string): (key: string) => string
  }
  slots: {
    inject(key: string, factory: () => void): void
    register(options: Record<string, unknown>, component: (props: Record<string, unknown>) => TestNode): () => void
  }
}

export type ClientSnapshot = {
  data: Record<string, unknown> | null
  error: string | null
  at: number
}

export function installBundleLoader(onLoad: (bundle: LoadedBundle) => void): void {
  Object.defineProperty(globalThis, 'window', {
    configurable: true,
    value: { __ModuleLoader__: { load: onLoad } },
  })
}

export function assertDefined<T>(value: T | undefined, message: string): asserts value is T {
  if (value === undefined) throw new Error(message)
}
