import { createContext, useContext, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

// The shell owns the top bar. Each tool can put its own buttons on the right
// side of it by wrapping them in <HeaderActions>, without knowing about the shell.
export const HeaderSlot = createContext<HTMLElement | null>(null);

export default function HeaderActions({ children }: { children: ReactNode }) {
  const slot = useContext(HeaderSlot);
  return slot ? createPortal(children, slot) : null;
}
