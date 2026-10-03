import React from 'react';
import VerificationWorkbench from '../../VerificationWorkbench';
import { useDemo } from '../../context/DemoContext';
import { 
  ArrowLeft, Clock, ChevronRight, AlertTriangle, CheckCircle
} from 'lucide-react';

interface VerificationWorkbenchViewProps {
  applicationId?: string;
  onBackToQueue: () => void;
}

export const VerificationWorkbenchView: React.FC<VerificationWorkbenchViewProps> = ({
  applicationId = 'APP-2026-001DB3',
  onBackToQueue
}) => {
  const { applicant, verification } = useDemo();
  const isVerified = verification.status === 'VERIFIED';

  return (
    <div className="space-y-4 pb-12">
      {/* 1. Official Government Scrutiny Navigation Bar */}
      <div className="bg-[#1D0A69] text-white py-3 px-4 shadow-sm select-none border-b-2 border-[#C85A17]">
        <div className="gov-container flex flex-wrap items-center justify-between gap-3">
          {/* Left: Breadcrumbs & Back */}
          <div className="flex items-center gap-3">
            <button
              onClick={onBackToQueue}
              className="flex items-center gap-1.5 text-xs font-bold bg-[#0F4C81] hover:bg-[#15074D] px-3 py-1.5 rounded transition-colors text-white"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Queue (जांच सूची)</span>
            </button>

            <div className="hidden sm:flex items-center gap-1.5 text-xs text-[#CFD8DC]">
              <span>Scrutiny Queue</span>
              <ChevronRight className="w-3 h-3 text-[#90A4AE]" />
              <span className="font-mono text-[#FFC107] font-bold">{applicant.applicationId || applicationId}</span>
              <ChevronRight className="w-3 h-3 text-[#90A4AE]" />
              <span className="text-white font-semibold">Evidence Scrutiny & OCR Audit</span>
            </div>
          </div>

          {/* Right: Authenticated Officer Context & Live Session Timer */}
          <div className="flex items-center gap-4 text-xs">
            <div className="hidden md:block text-right">
              <div className="font-bold text-white">{verification.officer || 'S. K. Mahapatra (District Scrutiny Officer)'}</div>
              <div className="text-[11px] text-[#CFD8DC]">District Welfare Office, Mandla, Madhya Pradesh</div>
            </div>

            <div className="flex items-center gap-1.5 bg-[#15074D] border border-[#546E7A] px-2.5 py-1 rounded font-mono text-[#FFC107] text-xs">
              <Clock className="w-3.5 h-3.5 text-[#FFC107]" />
              <span>Session: 28:14</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Candidate Context Summary Strip */}
      <div className="gov-container">
        <div className="gov-card bg-[#F4F6F8] p-3 flex flex-wrap items-center justify-between gap-3 border-l-4 border-l-[#1D0A69]">
          <div className="flex flex-wrap items-center gap-4 text-xs">
            <div>
              <span className="text-[10px] text-[#546E7A] uppercase font-bold block">Candidate:</span>
              <strong className="text-[#150202] text-sm">{applicant.name || 'Demo ST Applicant'} ({applicant.otrNo || 'OTR-2026-ST-884912'})</strong>
            </div>

            <div className="border-l border-[#CFD8DC] pl-4">
              <span className="text-[10px] text-[#546E7A] uppercase font-bold block">Target Scheme:</span>
              <strong className="text-[#1D0A69]">Top Class Education for ST Students (TOP-05)</strong>
            </div>

            <div className="border-l border-[#CFD8DC] pl-4">
              <span className="text-[10px] text-[#546E7A] uppercase font-bold block">Enrolled Institution:</span>
              <strong className="text-[#150202]">{applicant.institution || 'Synthetic Demo University (IIT Indore)'}</strong>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isVerified ? (
              <span className="gov-badge gov-badge-success text-xs font-bold flex items-center gap-1">
                <CheckCircle className="w-3.5 h-3.5 text-[#198754]" />
                <span>OFFICER VERIFIED (Conflict Resolved)</span>
              </span>
            ) : (
              <span className="gov-badge gov-badge-danger text-xs font-bold flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5 text-[#C85A17]" />
                <span>MATERIAL CONFLICT (Pending Review)</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* 3. The Interactive 3-Panel Verification Workbench */}
      <div className="gov-container">
        <VerificationWorkbench />
      </div>
    </div>
  );
};
