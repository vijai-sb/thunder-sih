import type { CellIntelligence } from '../lib/types';
import { LANGS, riskKey, t, type Lang } from '../lib/i18n';

interface Props {
  intel: CellIntelligence[];
  lang: Lang;
  onLang: (l: Lang) => void;
  onBack: () => void;
}

const ORDER = ['low', 'moderate', 'high', 'severe'] as const;

function riskIcon(risk: string): string {
  if (risk === 'severe') return '▲▲';
  if (risk === 'high') return '▲';
  if (risk === 'moderate') return '●';
  return '○';
}

export default function CitizenView({ intel, lang, onLang, onBack }: Props) {
  const top = [...intel].sort(
    (a, b) => ORDER.indexOf(b.risk.storm_risk) - ORDER.indexOf(a.risk.storm_risk),
  )[0];
  const risk = top?.risk.storm_risk ?? 'low';
  const calm = !top || risk === 'low';

  return (
    <div className="citizen">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <div className="row" role="group" aria-label="Warning language">
          {LANGS.map((l) => (
            <button
              key={l.id}
              onClick={() => onLang(l.id)}
              aria-pressed={lang === l.id}
              style={lang === l.id ? { borderColor: '#4da3ff', fontWeight: 700 } : undefined}
            >
              {l.label}
            </button>
          ))}
        </div>
        <button onClick={onBack}>← Technical dashboard</button>
      </div>

      <h1 className="citizen-title">{t(lang, 'app_title')}</h1>

      {calm ? (
        <div className="card citizen-calm">
          <span className="pill low">○ {t(lang, 'risk_low')}</span>
          <p>{t(lang, 'no_threat')}</p>
        </div>
      ) : (
        <div className={`card citizen-risk ${risk}`}>
          <div className="citizen-big" aria-live="polite">
            <span aria-hidden="true">{riskIcon(risk)}</span> {t(lang, 'current_risk')}:{' '}
            {t(lang, riskKey(risk))}
          </div>
          <p className="citizen-place">
            {top.tti.minutes != null
              ? t(lang, 'expected_in', { min: Math.round(top.tti.minutes), place: top.tti.target_name || 'Delhi-NCR' })
              : t(lang, 'unknown_time')}
          </p>
          <p>
            {t(lang, 'lightning_risk')}: <b>{t(lang, riskKey(top.risk.lightning_risk))}</b>
          </p>
          <h2>{t(lang, 'action_title')}</h2>
          <p className="citizen-action">{t(lang, 'action_body')}</p>
          <ul>
            <li>{t(lang, 'guide_1')}</li>
            <li>{t(lang, 'guide_2')}</li>
            <li>{t(lang, 'guide_3')}</li>
          </ul>
          <h2>{t(lang, 'why_title')}</h2>
          <p>{t(lang, risk === 'moderate' ? 'why_moderate' : 'why_high')}</p>
        </div>
      )}
      <p className="small">{t(lang, 'demo_note')}</p>
    </div>
  );
}
