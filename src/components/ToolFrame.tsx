import React from 'react';
import { ExternalLink } from 'lucide-react';
import { type ToolRef, toolFrameSrc } from '../tools';

interface Props {
  tool: ToolRef;
  launch: { imageUrl?: string; ref?: string } | null;
}

// Embeds a sibling CoSE tool inside the database shell via a same-origin iframe.
export const ToolFrame: React.FC<Props> = ({ tool, launch }) => {
  const src = toolFrameSrc(tool, launch?.imageUrl, launch?.ref);
  const imageName = launch?.imageUrl ? (decodeURIComponent(launch.imageUrl).split('/').pop() || '').split('?')[0] : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 58px)' }}>
      <div className="row sb" style={{ justifyContent: 'space-between', padding: '9px 18px', borderBottom: '1px solid var(--line)', gap: 12, flexShrink: 0 }}>
        <span className="row" style={{ gap: 8, fontWeight: 650, fontSize: '.92rem' }}>
          <tool.icon size={17} color="var(--accent2)" /> {tool.name}
          {imageName && <span className="muted" style={{ fontWeight: 400, fontSize: '.8rem' }}>· analysing <span className="mono">{imageName}</span></span>}
        </span>
        <a className="btn btn-sm btn-ghost" href={src} target="_blank" rel="noreferrer" title="Open the tool full-screen in a new tab">
          <ExternalLink size={14} /> Open standalone
        </a>
      </div>
      <iframe
        key={src}
        src={src}
        title={tool.name}
        style={{ flex: 1, border: 0, width: '100%', background: 'var(--bg)' }}
        allow="clipboard-write"
      />
    </div>
  );
};
