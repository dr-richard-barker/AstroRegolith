import React, { useEffect, useState } from 'react';
import { Loader2, FileDown } from 'lucide-react';
import { isTiffUrl, tiffObjectUrl } from '../lib/tiff';

// Drop-in <img> that transparently decodes TIFF sources (which browsers can't
// render natively) to a JPEG in-browser. Non-TIFF URLs pass straight through.
interface Props {
  src: string;
  alt?: string;
  className?: string;
  style?: React.CSSProperties;
  loading?: 'lazy' | 'eager';
  crossOrigin?: 'anonymous' | 'use-credentials' | '';
}

export const SmartImg: React.FC<Props> = ({ src, alt, className, style, loading, crossOrigin }) => {
  const tiff = isTiffUrl(src);
  const [resolved, setResolved] = useState<string | null>(tiff ? null : src);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!isTiffUrl(src)) { setResolved(src); setFailed(false); return; }
    let alive = true;
    setResolved(null); setFailed(false);
    tiffObjectUrl(src).then(u => alive && setResolved(u)).catch(() => alive && setFailed(true));
    return () => { alive = false; };
  }, [src]);

  if (failed) {
    return (
      <div className={className} style={{ display: 'grid', placeItems: 'center', height: '100%', gap: 6, color: 'var(--muted)', fontSize: '.7rem', ...style }}>
        <FileDown size={20} style={{ opacity: .6 }} />
        <span>TIFF — <a href={src} target="_blank" rel="noreferrer" download>download</a></span>
      </div>
    );
  }
  if (resolved === null) {
    return (
      <div className={className} style={{ display: 'grid', placeItems: 'center', height: '100%', color: 'var(--muted)', ...style }}>
        <Loader2 className="spin" size={18} />
      </div>
    );
  }
  // Decoded TIFFs are same-origin blob: URLs — no crossOrigin needed (and it can
  // otherwise mark the element cross-origin). Pass it through only for real URLs.
  const co = resolved.startsWith('blob:') ? undefined : crossOrigin;
  return <img src={resolved} alt={alt} className={className} style={style} loading={loading} crossOrigin={co} />;
};
