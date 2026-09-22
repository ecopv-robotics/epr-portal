export default function Logo({ light = false }: { light?: boolean }) {
  return <div className={`logo ${light ? 'logo-light' : ''}`}><span>EPR</span> FLOW</div>
}

