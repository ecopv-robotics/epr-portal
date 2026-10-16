export default function Logo({ light = false }: { light?: boolean }) {
  return <div className={`logo ${light ? 'logo-light' : ''}`}><img src="/ecopv-eu-logo.png" alt="ECOPV-EU GmbH" /></div>
}

