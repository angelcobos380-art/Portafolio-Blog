import { marked } from 'marked';

export interface CmsCategory {
  id: string;
  name: string;
  slug: string;
}

export interface Post {
  post_id: string;
  slug: string;
  title: string;
  content: string;
  category_id: string;
  frozen_category: CmsCategory | null;
  tags: string[];
  published_at: string | null;
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

const BASE_URL = import.meta.env.PUBLIC_CMS_BASE_URL;

async function fetchJson<T>(path: string): Promise<T | null> {
  if (!BASE_URL) return null;
  try {
    const res = await fetch(`${BASE_URL}${path}`);
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch (err) {
    console.warn(`[cms] No se pudo cargar ${path}`, err);
    return null;
  }
}

export async function getPublicPosts(): Promise<Post[]> {
  const data = await fetchJson<{ items: Post[] }>('/public/posts');
  return data?.items ?? [];
}

export async function getPublicProjects(): Promise<Project[]> {
  return (await fetchJson<Project[]>('/public/projects')) ?? [];
}

export async function getPostBySlug(slug: string): Promise<Post | null> {
  return fetchJson<Post>(`/public/posts/${slug}`);
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
