import { defineCollection, z } from 'astro:content';

const newsCollection = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    date: z.string(),
    reels_script: z.string().optional(),
  })
});

export const collections = {
  'news': newsCollection,
};
