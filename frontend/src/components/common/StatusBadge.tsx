import React from 'react';
import { CheckCircle2, AlertTriangle, Clock, XCircle, ShieldCheck } from 'lucide-react';

export type StatusType = 
  | 'VERIFIED' 
  | 'SUBMITTED' 
  | 'UNDER_SCRUTINY' 
  | 'DEFICIENT' 
  | 'DISBURSED' 
  | 'REJECTED' 
  | 'PENDING';

interface StatusBadgeProps {
  status: StatusType;
  customLabel?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  customLabel,
  size = 'md'
}) => {
  const sizeClasses = size === 'sm' ? 'text-[11px] py-0.5 px-1.5' : 'text-xs py-1 px-2.5';

  switch (status) {
    case 'VERIFIED':
      return (
        <span className={`gov-badge gov-badge-success ${sizeClasses}`}>
          <CheckCircle2 className="w-3 h-3 text-[#198754]" />
          <span>{customLabel || 'Verified'}</span>
        </span>
      );

    case 'DISBURSED':
      return (
        <span className={`gov-badge gov-badge-success ${sizeClasses} bg-[#E8F5E9] border-[#2E7D32]`}>
          <ShieldCheck className="w-3 h-3 text-[#198754]" />
          <span>{customLabel || 'DBT Disbursed'}</span>
        </span>
      );

    case 'DEFICIENT':
      return (
        <span className={`gov-badge gov-badge-warning ${sizeClasses}`}>
          <AlertTriangle className="w-3 h-3 text-[#7A5E00]" />
          <span>{customLabel || 'Action Required'}</span>
        </span>
      );

    case 'UNDER_SCRUTINY':
      return (
        <span className={`gov-badge gov-badge-info ${sizeClasses}`}>
          <Clock className="w-3 h-3 text-[#0288D1]" />
          <span>{customLabel || 'Under Scrutiny'}</span>
        </span>
      );

    case 'SUBMITTED':
      return (
        <span className={`gov-badge gov-badge-info ${sizeClasses}`}>
          <CheckCircle2 className="w-3 h-3 text-[#0288D1]" />
          <span>{customLabel || 'Submitted'}</span>
        </span>
      );

    case 'REJECTED':
      return (
        <span className={`gov-badge gov-badge-danger ${sizeClasses}`}>
          <XCircle className="w-3 h-3 text-[#A71D2A]" />
          <span>{customLabel || 'Rejected with Grounds'}</span>
        </span>
      );

    case 'PENDING':
    default:
      return (
        <span className={`gov-badge bg-[#ECEFF1] text-[#455A64] border border-[#CFD8DC] ${sizeClasses}`}>
          <Clock className="w-3 h-3" />
          <span>{customLabel || 'Pending'}</span>
        </span>
      );
  }
};
