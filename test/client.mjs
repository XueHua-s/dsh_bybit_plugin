/**
 * Browser-half smoke test: load `client.js` with a stand-in module loader and a
 * minimal React shim, then run the plugin body against a fake client context.
 * It proves the bundle parses, exports the expected shape, and registers a main
 * panel plus its sidebar row; it cannot prove how the page renders.
 *
 * Run from the bundle directory: `node test/client.mjs`
 */
import assert from 'node:assert/strict'

let loaded
globalThis.window = {
  __ModuleLoader__: {
    load: (bundle) => { loaded = bundle },
  },
}

const React = {
  createElement: (type, props, ...children) => ({ type, props, children }),
  useState: (initial) => [typeof initial === 'function' ? initial() : initial, () => {}],
  useEffect: () => {},
  useMemo: (factory) => factory(),
  useCallback: (fn) => fn,
}

await import('../dist/client.js')

assert.ok(loaded !== undefined, 'client bundle did not call __ModuleLoader__.load')
assert.equal(loaded.id, '@local/bybit-quant')

const plugin = loaded.factory((specifier) => {
  assert.equal(specifier, 'react', 'the bundle must only require react')
  return React
})

assert.deepEqual(plugin.inject, ['slots', 'locale'])
assert.equal(typeof plugin.apply, 'function')

const registrations = []
const injections = []
const locales = []
const effects = []

plugin.apply({
  effect: (factory) => { effects.push(factory()) },
  locale: {
    register: (namespace, dictionaries) => {
      locales.push({ namespace, dictionaries })
      return () => {}
    },
    bind: (namespace) => (key) => `${namespace}.${key}`,
  },
  slots: {
    inject: (key, factory) => { injections.push(key); return factory() },
    register: (options, component) => {
      registrations.push({ options, component })
      return () => {}
    },
  },
})

assert.deepEqual([...new Set(injections)].sort(), ['main', 'sidebar.panellist'])

const main = registrations.find(entry => entry.options.name === 'main')
const sidebar = registrations.find(entry => entry.options.name === 'sidebar.panellist')
assert.ok(main !== undefined, 'no main panel registration')
assert.equal(main.options.key, 'bybit-quant')
assert.equal(main.options.locale, 'bybitQuant')
assert.equal(typeof main.component, 'function')
assert.ok(sidebar !== undefined, 'no sidebar registration')
assert.equal(sidebar.options.id, 'bybit-quant')
assert.equal(sidebar.options.order, 40)
assert.equal(typeof sidebar.options.label, 'function')
assert.equal(sidebar.options.label(), 'bybitQuant.panel')
assert.equal(typeof sidebar.component, 'function')

const dictionary = locales.find(entry => entry.namespace === 'bybitQuant')
assert.ok(dictionary !== undefined, 'no dictionaries registered')
assert.ok(dictionary.dictionaries.zh !== undefined && dictionary.dictionaries.en !== undefined)
for (const key of Object.keys(dictionary.dictionaries.zh)) {
  assert.ok(dictionary.dictionaries.en[key] !== undefined, `missing English text for "${key}"`)
  assert.ok(dictionary.dictionaries.zh[key].length > 0, `empty Chinese text for "${key}"`)
}

// The panel component renders through the React shim without touching hooks'
// side effects, so an unmountable tree comes back instead of a throw.
const tree = main.component({ t: (key) => key })
assert.equal(tree.type, 'div')
assert.ok(tree.children.length > 0)

const icon = sidebar.component({ size: 20 })
assert.equal(icon.type, 'svg')

console.log(`ok client bundle: ${registrations.length} registrations, ${Object.keys(dictionary.dictionaries.zh).length} dictionary keys\n`)
