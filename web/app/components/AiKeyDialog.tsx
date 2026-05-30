"use client";

import { useState } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
  onSubmit: (provider: "anthropic" | "openai", key: string, model: string) => Promise<void>;
};

export function AiKeyDialog({ open, onClose, onSubmit }: Props) {
  const [provider, setProvider] = useState<"anthropic" | "openai">("anthropic");
  const [key, setKey] = useState("");
  const [model, setModel] = useState("");
  const [running, setRunning] = useState(false);

  if (!open) return null;

  const defaultModel = provider === "anthropic" ? "claude-sonnet-4-6" : "gpt-4o";

  async function handle(e: React.FormEvent) {
    e.preventDefault();
    setRunning(true);
    try {
      await onSubmit(provider, key, model || defaultModel);
      onClose();
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-ink/40 flex items-center justify-center z-50">
      <div className="bg-paper border-2 border-ink max-w-lg w-full p-8 relative">
        <p className="font-typewriter text-xs tracking-widest absolute top-2 right-4 text-faded-ink">
          BYOK · LOCAL ONLY
        </p>
        <h3 className="font-typewriter text-xl uppercase mb-4">Deep dive with AI</h3>
        <p className="font-prose text-sm text-faded-ink mb-6">
          Your key is forwarded once to the provider and never stored or logged on this
          server. No persistence.
        </p>
        <form onSubmit={handle} className="space-y-4">
          <div>
            <label className="font-typewriter text-xs uppercase tracking-wider block mb-1">
              Provider
            </label>
            <div className="flex gap-3">
              {(["anthropic", "openai"] as const).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setProvider(p)}
                  className={`font-typewriter uppercase text-sm px-3 py-1 border-2 ${
                    provider === p
                      ? "bg-ink text-paper border-ink"
                      : "bg-paper text-ink border-rule"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="font-typewriter text-xs uppercase tracking-wider block mb-1">
              API key
            </label>
            <input
              type="password"
              required
              value={key}
              onChange={(e) => setKey(e.target.value)}
              className="w-full border-b-2 border-ink bg-transparent font-data py-2 focus:outline-none focus:border-stamp-red"
            />
          </div>
          <div>
            <label className="font-typewriter text-xs uppercase tracking-wider block mb-1">
              Model (optional)
            </label>
            <input
              type="text"
              placeholder={defaultModel}
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full border-b-2 border-ink bg-transparent font-data py-2 focus:outline-none focus:border-stamp-red"
            />
          </div>
          <div className="flex gap-4 pt-2">
            <button
              type="submit"
              disabled={running || !key}
              className="font-typewriter uppercase tracking-widest text-sm px-6 py-2 bg-ink text-paper disabled:bg-faded-ink"
            >
              {running ? "Running …" : "Run AI"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="font-typewriter uppercase tracking-widest text-sm px-6 py-2 border-2 border-rule"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
