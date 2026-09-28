import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'
import llmstxt from 'vitepress-plugin-llms'

const rawBase = process.env.VITEPRESS_BASE
const base = rawBase
  ? rawBase.startsWith('/')
    ? rawBase.endsWith('/') ? rawBase : `${rawBase}/`
    : `/${rawBase}/`
  : '/'

const sharedThemeConfig = {
  logo: {
    light: '/brand/logo-light.svg',
    dark: '/brand/logo-dark.svg',
    alt: 'MICOS-2024',
  },
  outline: [2, 3] as [number, number],
  search: { provider: 'local' as const },
  socialLinks: [
    { icon: 'github', link: 'https://github.com/open-genomics/micos-2024' },
  ],
}

const sharedSidebar = [
  {
    text: '学院',
    items: [
      { text: '流程基础', link: '/zh/academy/pipeline-foundations' },
      { text: '数据产物与解释', link: '/zh/academy/data-products' },
    ],
  },
  {
    text: '分析模块',
    items: [
      { text: '物种分类分析', link: '/zh/analysis/taxonomic-profiling' },
      { text: '功能注释分析', link: '/zh/analysis/functional-profiling' },
      { text: '多样性分析', link: '/zh/analysis/diversity-analysis' },
    ],
  },
]

export default withMermaid(defineConfig({
  base,
  title: 'MICOS-2024',
  description: '宏基因组分析平台文档',
  cleanUrls: true,
  lastUpdated: true,

  mermaid: {
    theme: 'base',
    themeVariables: {
      primaryColor: '#4f6ef7',
      primaryTextColor: '#1a1a2e',
      primaryBorderColor: '#4f6ef7',
      lineColor: '#5a6c7d',
      secondaryColor: '#f0f4ff',
      tertiaryColor: '#e8f0fe',
      noteBkgColor: '#fff9e6',
      noteTextColor: '#1a1a2e',
      noteBorderColor: '#ffc107',
      sequenceNumberColor: '#4f6ef7',
      actorBkg: '#f0f4ff',
      actorBorder: '#4f6ef7',
      actorTextColor: '#1a1a2e',
      actorLineColor: '#5a6c7d',
    },
  },

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: `${base}brand/favicon.svg` }],
    ['meta', { name: 'theme-color', content: '#0f766e' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:title', content: 'MICOS-2024' }],
    ['meta', { property: 'og:description', content: '宏基因组分析平台文档' }],
    ['meta', { property: 'og:site_name', content: 'MICOS-2024' }],
  ],

  locales: {
    zh: {
      label: '简体中文',
      lang: 'zh-CN',
      link: '/zh/',
      title: 'MICOS-2024',
      description: '宏基因组分析平台文档',
      themeConfig: {
        ...sharedThemeConfig,
        nav: [
          { text: '导读', link: '/zh/' },
          { text: '学院', link: '/zh/academy/pipeline-foundations', activeMatch: '/zh/academy/|/zh/analysis/' },
          { text: '架构', link: '/zh/architecture/system-overview', activeMatch: '/zh/architecture/' },
          { text: '算法', link: '/zh/algorithms/quality-control', activeMatch: '/zh/algorithms/' },
          { text: '指南', link: '/zh/guides/getting-started', activeMatch: '/zh/guides/|/zh/configuration|/zh/faq|/zh/troubleshooting' },
          { text: '参考', link: '/zh/reference/cli', activeMatch: '/zh/reference/' },
          { text: '研究', link: '/zh/research/citations', activeMatch: '/zh/research/' },
        ],
        sidebar: {
          '/zh/academy/': sharedSidebar,
          '/zh/analysis/': sharedSidebar,
          '/zh/architecture/': [
            {
              text: '架构',
              items: [
                { text: '系统总览', link: '/zh/architecture/system-overview' },
                { text: '模块设计原理', link: '/zh/architecture/module-design' },
                { text: '测试策略', link: '/zh/architecture/testing-strategy' },
              ],
            },
          ],
          '/zh/algorithms/': [
            {
              text: '算法',
              items: [
                { text: '质量控制算法', link: '/zh/algorithms/quality-control' },
                { text: '物种分类算法', link: '/zh/algorithms/taxonomic-classification' },
                { text: '多样性度量', link: '/zh/algorithms/diversity-metrics' },
              ],
            },
          ],
          '/zh/guides/': [
            {
              text: '指南',
              items: [
                { text: '快速开始', link: '/zh/guides/getting-started' },
                { text: '部署模式', link: '/zh/guides/deployment' },
                { text: '配置系统', link: '/zh/configuration' },
                { text: '常见问题', link: '/zh/faq' },
                { text: '故障排除', link: '/zh/troubleshooting' },
              ],
            },
          ],
          '/zh/reference/': [
            {
              text: '参考',
              items: [
                { text: 'CLI 参考', link: '/zh/reference/cli' },
                { text: '项目结构', link: '/zh/reference/project-structure' },
              ],
            },
          ],
          '/zh/research/': [
            {
              text: '研究',
              items: [
                { text: '参考文献', link: '/zh/research/citations' },
                { text: '相关开源项目', link: '/zh/research/related-projects' },
                { text: '演进思考', link: '/zh/research/evolution-notes' },
              ],
            },
          ],
        },
        outlineTitle: '本页内容',
        darkModeSwitchLabel: '主题',
        sidebarMenuLabel: '菜单',
        returnToTopLabel: '返回顶部',
        docFooter: { prev: '上一页', next: '下一页' },
        footer: {
          message: 'MICOS-2024 宏基因组分析平台',
          copyright: 'MIT License · LessUp / MICOS-2024',
        },
      },
    },
  },

  vite: {
    plugins: [llmstxt()],
  },
}))
