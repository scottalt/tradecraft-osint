import type { ReactNode } from "react";

type Props = {
  index: string;
  label: string;
  children?: ReactNode;
};

export function SectionHeader({ index, label, children }: Props) {
  return (
    <header className="mt-12 mb-6 border-t-2 border-b-2 border-rule py-3 flex items-baseline gap-6">
      <span className="font-typewriter text-sm tracking-widest text-faded-ink">§ {index}</span>
      <h2 className="font-typewriter text-2xl uppercase tracking-wide text-ink">{label}</h2>
      {children}
    </header>
  );
}
