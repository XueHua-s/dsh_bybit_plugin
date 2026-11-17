/** Isolate nested pnpm from Nx/npm lifecycle variables and package-manager auto-switching. */
export function pnpmEnvironment(): NodeJS.ProcessEnv {
  return {
    PATH: process.env.PATH,
    HOME: process.env.HOME,
    USER: process.env.USER,
    TMPDIR: process.env.TMPDIR,
    SystemRoot: process.env.SystemRoot,
    COREPACK_ENABLE_PROJECT_SPEC: '0',
    COREPACK_ENABLE_AUTO_PIN: '0',
    npm_config_manage_package_manager_versions: 'false',
  }
}
