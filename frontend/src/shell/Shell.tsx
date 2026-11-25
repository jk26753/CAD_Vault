import { useEffect, useState } from 'react';
import { Box, SlidersHorizontal, Table2 } from 'lucide-react';
import ModelVault from '../App';
import Configurator from '../configurator/Configurator';
import { HeaderSlot } from './HeaderActions';
import './shell.css';

// Table Configurations: the Model Vault page showing only tables saved from the Configurator.
const TableConfigurations = () => <ModelVault collection="table_config" />;

// Each tool is a self-contained page. Add a new tool by adding an entry here.
const TOOLS = [
  { path: 'vault', label: 'Model Vault', icon: Box, Page: ModelVault },
  { path: 'configurator', label: 'Table Configurator', icon: SlidersHorizontal, Page: Configurator },
  { path: 'configurations', label: 'Table Configurations', icon: Table2, Page: TableConfigurations },
];

const current = () => {
  const path = window.location.hash.replace(/^#\/?/, '');
  return TOOLS.find(t => t.path === path) ?? TOOLS[0];
};

export default function Shell() {
  const [tool, setTool] = useState(current);
  const [slot, setSlot] = useState<HTMLElement | null>(null);

  useEffect(() => {
    const onHash = () => setTool(current());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    document.title = tool.label;
  }, [tool]);

  return (
    <HeaderSlot.Provider value={slot}>
      <header>
        <div className="headerLeft">
          {/* Company logo (white version for the dark header); clicking it opens the Model Vault. */}
          <a href="#/vault" className="hdrLogoLink" title="Model Vault">
            <img src="/logo-white.png" alt="In-Position Technologies" className="hdrLogo" />
          </a>
          <span className="hdrDivider" aria-hidden="true" />
          <nav className="toolTabs">
            {TOOLS.map(({ path, label, icon: Icon }) => (
              <a key={path} href={`#/${path}`} className={path === tool.path ? 'on' : ''}>
                <Icon />
                {label}
              </a>
            ))}
          </nav>
        </div>
        <div ref={setSlot} className="headerActions" />
      </header>
      <tool.Page key={tool.path} />
    </HeaderSlot.Provider>
  );
}
