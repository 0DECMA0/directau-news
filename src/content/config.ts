import { defineCollection, z } from 'astro:content';

const newsCollection = defineCollection({
  type: 'content',
  schema: z.object({
    // Tus campos originales
    title: z.string(),
    date: z.string(),
    reels_script: z.string().optional(),
    category: z.string().default('Actualidad'),
    description: z.string().optional(),
    image: z.string().default('/placeholder-news.jpg'),
  })
});

export const collections = {
  'news': newsCollection,
};