// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
const isGitHubPages = process.env.DEPLOY_TARGET === 'gh-pages';

export default defineConfig({
  site: isGitHubPages
    ? 'https://angelcobos380-art.github.io'
    : 'https://portafolio-blog.vercel.app',
  base: isGitHubPages ? '/Portafolio-Blog' : '/',
});
