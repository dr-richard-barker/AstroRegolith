import { Sprout, FlaskConical, Timer, type LucideIcon } from 'lucide-react';

// Sibling CoSE image-analysis tools, chosen for what a regolith study measures.
// `launch: 'image'` tools read `imgParam` to auto-load an image passed from this
// database; `launch: 'standalone'` tools take no per-entry handoff — they open
// embedded for the user to feed their own input (e.g. a whole time-lapse series
// a single database entry cannot represent). MarkerInspector's per-photo
// "analyse this image in X" buttons only render `launch: 'image'` tools, so
// 'standalone' tools appear in the sidebar list only.
export interface ToolRef { id: string; name: string; sub: string; url: string; icon: LucideIcon; launch: 'image' | 'standalone'; imgParam?: string; }

export const TOOLS: ToolRef[] = [
  // Regolith-grown plants show reddish-black pigmentation and severe stunting,
  // so pigment + leaf area is the first thing worth measuring on a photo.
  { id: 'leaf-pigment-size', name: 'Leaf Pigment & Size', sub: 'Anthocyanin · leaf area', url: 'https://dr-richard-barker.github.io/Anthocyanin-Image-analysis/', icon: FlaskConical, launch: 'image', imgParam: 'image' },
  // Root penetration into a dense, angular substrate is the other half of the question.
  { id: 'astroroot', name: 'AstroRoot', sub: 'Root tracing', url: 'https://dr-richard-barker.github.io/astroroot/', icon: Sprout, launch: 'image', imgParam: 'image' },
  // Germination failure is the commonest regolith outcome; scoring it is a study in itself.
  { id: 'germinator-ai', name: 'Germinator AI', sub: 'Seed germination · time-lapse', url: 'https://dr-richard-barker.github.io/germinator-ai/', icon: Timer, launch: 'standalone' },
];
export const toolById = (id: string) => TOOLS.find(t => t.id === id);

// The iframe src for embedding a tool inside the database shell (embed=1 tells
// the tool to hide its own cross-site CoSE chrome).
export function toolFrameSrc(t: ToolRef, imageUrl?: string, ref?: string): string {
  if (t.launch === 'standalone') return `${t.url}?embed=1`;
  const q = new URLSearchParams({ embed: '1' });
  if (imageUrl) q.set(t.imgParam!, imageUrl);
  if (ref) q.set('ref', ref);
  return `${t.url}?${q.toString()}`;
}

// Build a tool URL that hands off the image plus a stable `ref` (so the tool can
// write its results back to the shared store keyed to this image).
export const toolUrl = (base: string, param: string, imageUrl?: string, ref?: string) => {
  if (!imageUrl) return base;
  const q = new URLSearchParams({ [param]: imageUrl });
  if (ref) q.set('ref', ref);
  return `${base}?${q.toString()}`;
};
