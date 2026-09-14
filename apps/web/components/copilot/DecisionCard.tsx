import React from 'react';
import { CheckCircle2, XCircle, HelpCircle, ShieldAlert } from 'lucide-react';

interface Decision {
  status: 'ELIGIBLE' | 'NOT_ELIGIBLE' | 'UNKNOWN';
  reason?: string;
  evaluation_reference?: string;
}

interface DecisionCardProps {
  decision: Decision;
}

export function DecisionCard({ decision }: DecisionCardProps) {
  if (!decision) return null;

  const getStatusConfig = () => {
    switch (decision.status) {
      case 'ELIGIBLE':
        return {
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
          bgColor: 'bg-emerald-50',
          borderColor: 'border-emerald-200',
          textColor: 'text-emerald-800',
          label: 'Eligible',
        };
      case 'NOT_ELIGIBLE':
        return {
          icon: <XCircle className="w-5 h-5 text-red-600" />,
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          textColor: 'text-red-800',
          label: 'Not Eligible',
        };
      case 'UNKNOWN':
      default:
        return {
          icon: <HelpCircle className="w-5 h-5 text-amber-600" />,
          bgColor: 'bg-amber-50',
          borderColor: 'border-amber-200',
          textColor: 'text-amber-800',
          label: 'Unknown Eligibility',
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className={`mt-3 p-4 rounded-xl border ${config.bgColor} ${config.borderColor}`}>
      <div className="flex items-center gap-2 mb-2">
        {config.icon}
        <span className={`font-semibold ${config.textColor}`}>
          {config.label}
        </span>
        <div className="ml-auto flex items-center gap-1.5 px-2 py-0.5 bg-white/50 rounded-full border border-black/5">
          <ShieldAlert className="w-3 h-3 text-zinc-500" />
          <span className="text-[10px] uppercase font-bold text-zinc-500 tracking-wide">
            Authoritative
          </span>
        </div>
      </div>
      
      {decision.reason && (
        <p className={`text-sm mt-2 ${config.textColor} opacity-90`}>
          {decision.reason}
        </p>
      )}
      
      {decision.evaluation_reference && (
        <div className="mt-3 pt-2 border-t border-black/5 flex items-center justify-between">
          <span className="text-xs font-mono text-zinc-500">
            Ref: {decision.evaluation_reference.split('-')[0]}
          </span>
        </div>
      )}
    </div>
  );
}
