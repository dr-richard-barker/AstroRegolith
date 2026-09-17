import React from 'react';
import { Gem, Mountain, Sprout, HelpCircle, ExternalLink } from 'lucide-react';
import { links, type SubstrateRow } from '../lib/substrates';

const ICON: Record<string, React.ComponentType<any>> = {
  apollo_soil: Gem,
  lunar_simulant: Mountain,
  mars_simulant: Mountain,
  terrestrial_medium: Sprout,
};

const num = (v: number | string) =>
  v === '' || v === null || v === undefined ? null : Number(v).toLocaleString();

/**
 * One substrate, with whatever provenance is actually known about it.
 *
 * An unresolved substrate renders as unresolved, with the reason — the point of
 * the registry is that a material nobody recorded properly looks different from
 * one that was.
 */
export const SubstrateChip: React.FC<{
  substrate: SubstrateRow | null;
  name: string;
  photo?: string | null;
  compact?: boolean;
}> = ({ substrate, name, photo, compact }) => {
  if (!substrate) {
    return (
      <span className="chip" title={`"${name}" is not in the substrate registry`}>
        <HelpCircle size={12} /> {name}
      </span>
    );
  }

  const Icon = ICON[substrate.kind] ?? Mountain;
  const unresolved = substrate.resolution === 'unresolved';

  if (compact) {
    return (
      <span className="chip" title={unresolved ? substrate.evidence : substrate.label}>
        <Icon size={12} /> {substrate.short}
        {unresolved && <span className="muted"> · unidentified</span>}
      </span>
    );
  }

  const mass = num(substrate.original_weight_g);
  const pristinity = num(substrate.pristinity_pct);

  return (
    <div className="card pad" style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
      {photo && (
        <img src={photo} alt={substrate.label} loading="lazy"
             style={{ width: 84, height: 84, objectFit: 'cover', borderRadius: 6,
                      flexShrink: 0, background: 'var(--card-2)' }} />
      )}
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: '.88rem', fontWeight: 600 }}>
          <Icon size={13} /> {substrate.label}
          {substrate.surface && <span className="muted" style={{ fontWeight: 400 }}> · {substrate.surface}</span>}
        </div>

        {unresolved ? (
          <p className="muted" style={{ fontSize: '.76rem', lineHeight: 1.6, margin: '5px 0 0' }}>
            <strong>Not identified.</strong> {substrate.evidence}
          </p>
        ) : (
          <>
            <div className="muted" style={{ fontSize: '.76rem', lineHeight: 1.6, marginTop: 4 }}>
              {substrate.apollo_generic && (
                <>
                  {substrate.mission}
                  {substrate.landmark ? ` · ${substrate.landmark}` : ''}
                  {mass ? ` · ${mass} g returned` : ''}
                  {pristinity ? ` · ${pristinity}% pristine` : ''}
                  {substrate.particle_size ? ` · ${substrate.particle_size}` : ''}
                </>
              )}
              {!substrate.apollo_generic && substrate.ares_simulant && (
                <>In NASA's Simulant Development Lab catalogue
                  {substrate.n_photos > 0 ? `, photographed` : ''}.</>
              )}
              {substrate.kind === 'terrestrial_medium' && <>Terrestrial growth medium, not a simulant.</>}
            </div>
            <div className="row wrap" style={{ gap: 5, marginTop: 6 }}>
              {links(substrate).map(l => (
                <a key={l.href + l.label} className="btn btn-xs btn-ghost"
                   href={l.href} target="_blank" rel="noopener">
                  {l.label} <ExternalLink size={9} />
                </a>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
