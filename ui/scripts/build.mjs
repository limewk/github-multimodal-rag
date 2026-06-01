import { mkdir, readFile, rm, writeFile, copyFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, '..')
const srcPath = resolve(root, 'src/App.vue')
const distDir = resolve(root, 'dist')
const assetsDir = resolve(distDir, 'assets')
const vueRuntime = resolve(root, 'node_modules/vue/dist/vue.esm-browser.prod.js')

const vueImport = './vue.esm-browser.prod.js'

await rm(distDir, { recursive: true, force: true })
await mkdir(assetsDir, { recursive: true })

const source = await readFile(srcPath, 'utf8')
const { descriptor, errors } = parse(source, { filename: 'App.vue' })
if (errors.length) {
  throw new Error(errors.map((error) => String(error)).join('\n'))
}

const script = compileScript(descriptor, { id: 'app' })
const template = compileTemplate({
  source: descriptor.template?.content ?? '<main />',
  filename: 'App.vue',
  id: 'app',
})
if (template.errors.length) {
  throw new Error(template.errors.map((error) => String(error)).join('\n'))
}

const scriptCode = script.content
  .replaceAll("from 'vue'", `from '${vueImport}'`)
  .replaceAll('from "vue"', `from '${vueImport}'`)
  .replace('export default', 'const App =')

const templateCode = template.code
  .replaceAll('from "vue"', `from '${vueImport}'`)
  .replaceAll("from 'vue'", `from '${vueImport}'`)
  .replace('export function render', 'function render')

const css = descriptor.styles.map((style) => style.content).join('\n\n')
const appCode = [
  `import { createApp } from '${vueImport}'`,
  scriptCode,
  templateCode,
  'App.render = render',
  "createApp(App).mount('#app')",
  '',
].join('\n\n')

await writeFile(resolve(assetsDir, 'app.js'), appCode, 'utf8')
await writeFile(resolve(assetsDir, 'style.css'), css, 'utf8')
await copyFile(vueRuntime, resolve(assetsDir, 'vue.esm-browser.prod.js'))
await writeFile(
  resolve(distDir, 'index.html'),
  [
    '<!doctype html>',
    '<html lang="zh-CN">',
    '  <head>',
    '    <meta charset="UTF-8" />',
    '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
    '    <title>GitHub Multimodal RAG</title>',
    '    <link rel="stylesheet" href="./assets/style.css" />',
    '  </head>',
    '  <body>',
    '    <div id="app"></div>',
    '    <script type="module" src="./assets/app.js"></script>',
    '  </body>',
    '</html>',
    '',
  ].join('\n'),
  'utf8',
)

console.log('Built frontend to dist/')
