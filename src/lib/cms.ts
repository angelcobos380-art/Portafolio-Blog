import { marked } from 'marked';

export interface SeoMeta {
  title?: string | null;
  description?: string | null;
  og_image?: string | null;
}

export interface TemplateTokens {
  version: number;
  colors: {
    accent: string;
    background: string;
    surface: string;
    text: string;
    textMuted: string;
    border: string;
    link: string;
    codeBg: string;
  };
  typography: {
    headingFont: string;
    bodyFont: string;
    codeFont: string;
    baseSize: number;
    lineHeight: number;
  };
  layout: {
    maxWidth: number;
    density: 'compact' | 'comfortable' | 'spacious';
    headerStyle: 'banner' | 'editorial-centered' | 'split-cover' | 'minimal';
    imageRadius: number;
    shadow: 'none' | 'soft' | 'elevated';
  };
  blocks: {
    callout: {
      info: { bg: string; border: string };
      tip: { bg: string; border: string };
      warning: { bg: string; border: string };
      danger: { bg: string; border: string };
    };
    quote: { borderColor: string; style: 'normal' | 'italic' };
    code: { radius: number; showLanguageBadge: boolean };
  };
}

export interface PostTemplate {
  template_id: string;
  name: string;
  tokens: TemplateTokens;
}

export interface PublicPostListItem {
  post_id: string;
  slug: string;
  title: string;
  excerpt: string | null;
  cover_image_url: string | null;
  tags: string[];
  published_at: string | null;
}

export interface PublicPostDetail extends PublicPostListItem {
  seo: SeoMeta | null;
  content_html: string | null;
  content: string | null;
  template: PostTemplate | null;
}

export interface Project {
  project_id: string;
  slug: string;
  title: string;
  description: string;
  demo_url: string | null;
  cover_image_url: string | null;
  stack: string[];
  is_featured: boolean;
  sort_order: number;
}

interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

const BASE_URL = import.meta.env.PUBLIC_CMS_BASE_URL;

async function fetchJson<T>(path: string): Promise<T | null> {
  if (!BASE_URL) return null;
  try {
    const res = await fetch(`${BASE_URL}${path}`, { signal: AbortSignal.timeout(20000) });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch (err) {
    console.warn(`[cms] No se pudo cargar ${path}`, err);
    return null;
  }
}

export async function getPublicPosts(): Promise<PublicPostListItem[]> {
  const all: PublicPostListItem[] = [];
  const pageSize = 100;
  let page = 1;

  while (true) {
    const data = await fetchJson<Paginated<PublicPostListItem>>(
      `/public/posts?page=${page}&page_size=${pageSize}`
    );
    if (!data || data.items.length === 0) break;
    all.push(...data.items);
    if (all.length >= data.total || data.items.length < pageSize) break;
    page += 1;
  }

  return all;
}

export async function getPublicProjects(): Promise<Project[]> {
  return (await fetchJson<Project[]>('/public/projects')) ?? [];
}

export async function getPostBySlug(slug: string): Promise<PublicPostDetail | null> {
  return fetchJson<PublicPostDetail>(`/public/posts/${slug}`);
}

export function renderMarkdown(markdown: string): string {
  return marked.parse(markdown) as string;
}

export function excerpt(markdown: string, max = 160): string {
  const plain = markdown
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/[#>*_`~\[\]()!|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return plain.length > max ? `${plain.slice(0, max).trimEnd()}…` : plain;
}

export function tokensToCssVars(tokens?: TemplateTokens | null): string {
  if (!tokens) return '';
  const { colors, typography, layout, blocks } = tokens;
  const vars: Record<string, string> = {
    '--cms-accent': colors.accent,
    '--cms-bg': colors.background,
    '--cms-surface': colors.surface,
    '--cms-text': colors.text,
    '--cms-text-muted': colors.textMuted,
    '--cms-border': colors.border,
    '--cms-link': colors.link,
    '--cms-code-bg': colors.codeBg,
    '--cms-heading-font': typography.headingFont,
    '--cms-body-font': typography.bodyFont,
    '--cms-code-font': typography.codeFont,
    '--cms-base-size': `${typography.baseSize}px`,
    '--cms-line-height': String(typography.lineHeight),
    '--cms-max-width': `${layout.maxWidth}px`,
    '--cms-image-radius': `${layout.imageRadius}px`,
    '--cms-quote-border': blocks.quote.borderColor,
    '--cms-quote-style': blocks.quote.style,
    '--cms-code-radius': `${blocks.code.radius}px`,
    '--cms-callout-info-bg': blocks.callout.info.bg,
    '--cms-callout-info-border': blocks.callout.info.border,
    '--cms-callout-tip-bg': blocks.callout.tip.bg,
    '--cms-callout-tip-border': blocks.callout.tip.border,
    '--cms-callout-warning-bg': blocks.callout.warning.bg,
    '--cms-callout-warning-border': blocks.callout.warning.border,
    '--cms-callout-danger-bg': blocks.callout.danger.bg,
    '--cms-callout-danger-border': blocks.callout.danger.border,
  };
  return Object.entries(vars)
    .map(([key, value]) => `${key}: ${value}`)
    .join('; ');
}
