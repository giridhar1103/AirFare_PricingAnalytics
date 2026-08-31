import {
  Activity,
  BarChart3,
  BookOpen,
  Calculator,
  Menu,
  Plane,
  Route as RouteIcon,
  X
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useRoute } from "wouter";

const navigation = [
  { to: "/", label: "Opportunities", icon: BarChart3 },
  { to: "/markets", label: "Market explorer", icon: RouteIcon },
  { to: "/models", label: "Model lab", icon: Activity },
  { to: "/scenario", label: "Scenario lab", icon: Calculator },
  { to: "/methodology", label: "Methodology", icon: BookOpen }
];

interface AppShellProps {
  children: ReactNode;
  isFixture: boolean;
  sourceVintage: string;
}

export function AppShell({ children, isFixture, sourceVintage }: AppShellProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true"><Plane size={19} /></div>
          <div>
            <span className="brand-name">FareLab</span>
            <span className="brand-subtitle">U.S. airline pricing analytics</span>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="source-label">Source vintage: {sourceVintage}</span>
          <span className={`mode-pill ${isFixture ? "mode-fixture" : "mode-observed"}`}>
            {isFixture ? "Development data" : "DOT observed data"}
          </span>
        </div>
        <button
          className="mobile-menu-button"
          aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((value) => !value)}
        >
          {mobileOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </header>

      <div className="app-frame">
        <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
          <nav aria-label="FareLab navigation">
            <p className="nav-eyebrow">Decision workspace</p>
            {navigation.map(({ to, label, icon: Icon }) => (
              <NavigationLink key={to} to={to} label={label} icon={Icon} onNavigate={() => setMobileOpen(false)} />
            ))}
          </nav>
          <div className="sidebar-note">
            <span className="sidebar-note-label">Model boundary</span>
            <p>Decision support for route reviews. Not a live fare filing or inventory system.</p>
          </div>
        </aside>
        <main id="main-content" className="main-content">{children}</main>
      </div>
    </div>
  );
}

function NavigationLink({ to, label, icon: Icon, onNavigate }: { to: string; label: string; icon: typeof Plane; onNavigate: () => void }) {
  const [matches] = useRoute(to);
  return (
    <Link href={to} className={`nav-link ${matches ? "nav-link-active" : ""}`} onClick={onNavigate}>
      <Icon size={18} aria-hidden="true" />
      <span>{label}</span>
    </Link>
  );
}
