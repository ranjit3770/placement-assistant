import React from 'react';
import { FileText, ChevronRight } from 'lucide-react';

interface Evidence {
  policy_reference?: string;
  version_reference?: string;
  excerpts: string[];
  source_metadata: any;
}

interface EvidenceCardProps {
  evidence: Evidence[];
}

export function EvidenceCard({ evidence }: EvidenceCardProps) {
  if (!evidence || evidence.length === 0) return null;

  return (
    <div className="mt-4 space-y-3">
      <div className="text-xs font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
        <FileText className="w-3.5 h-3.5" />
        Sourced Policies
      </div>
      
      <div className="flex flex-col gap-2">
        {evidence.map((ev, i) => (
          <div key={i} className="bg-white border border-zinc-200 rounded-lg p-3 text-sm shadow-sm">
            <div className="flex items-center justify-between mb-2 pb-2 border-b border-zinc-100">
              <span className="font-medium text-zinc-700">
                {ev.policy_reference || 'Campus Policy'}
              </span>
              <span className="text-xs text-zinc-500 font-mono">
                {ev.version_reference || 'latest'}
              </span>
            </div>
            
            <div className="space-y-2">
              {ev.excerpts.map((excerpt, j) => (
                <div key={j} className="text-zinc-600 pl-3 border-l-2 border-blue-200 bg-zinc-50/50 py-1 pr-2 rounded-r-md text-sm italic">
                  "{excerpt}"
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
