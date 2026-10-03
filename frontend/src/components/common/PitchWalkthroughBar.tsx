import React from 'react';
import { useDemo, DemoStep } from '../../context/DemoContext';
import { 
  Compass, FileText, UploadCloud, ShieldCheck, 
  CheckCircle, RefreshCw, ArrowRight, Play, Home
} from 'lucide-react';

export const PitchWalkthroughBar: React.FC = () => {
  const { 
    currentStep, setCurrentStep, resetDemo, 
    startStudentDemo, startOfficerDemo, isResetting, actionSuccessMsg 
  } = useDemo();

  const steps: { key: DemoStep; label: string; icon: React.ElementType }[] = [
    { key: 'home', label: '1. Landing', icon: Home },
    { key: 'schemes', label: '2. Schemes', icon: Compass },
    { key: 'wizard', label: '3. Application', icon: FileText },
    { key: 'upload_ocr', label: '4. Upload & OCR', icon: UploadCloud },
    { key: 'officer_queue', label: '5. Officer Queue', icon: ShieldCheck },
    { key: 'workbench', label: '6. Verification', icon: ShieldCheck },
    { key: 'applicant_status', label: '7. Final Status', icon: CheckCircle },
  ];

  const currentIdx = steps.findIndex(s => s.key === currentStep);

  const handleNext = () => {
    if (currentIdx < steps.length - 1) {
      setCurrentStep(steps[currentIdx + 1].key);
    }
  };

  return (
    <div className="bg-[#120538] text-white border-b-2 border-[#C85A17] select-none text-xs sticky top-0 z-50 shadow-md">
      {/* Success Notification Bar */}
      {actionSuccessMsg && (
        <div className="bg-[#198754] text-white py-1.5 px-4 text-center font-bold text-xs flex items-center justify-center gap-2 animate-fadeIn">
          <CheckCircle className="w-3.5 h-3.5" />
          <span>{actionSuccessMsg}</span>
        </div>
      )}

      <div className="gov-container py-2 flex flex-wrap items-center justify-between gap-3">
        {/* Left: Pitch Mode Indicator */}
        <div className="flex items-center gap-2">
          <span className="bg-[#C85A17] text-white font-extrabold px-2 py-0.5 rounded text-[10px] tracking-wider uppercase flex items-center gap-1">
            <Play className="w-2.5 h-2.5 fill-current" /> SIH 2026 PITCH DEMO
          </span>
          <span className="hidden sm:inline text-[#CFD8DC] text-[11px]">
            Synthetic ST Journey: <strong>Mandla (MP)</strong>
          </span>
        </div>

        {/* Center: Interactive Stepper Pills */}
        <div className="hidden lg:flex items-center gap-1 overflow-x-auto py-0.5">
          {steps.map((st, i) => {
            const isActive = st.key === currentStep;
            const isPast = currentIdx > i;
            const Icon = st.icon;

            return (
              <button
                key={st.key}
                onClick={() => setCurrentStep(st.key)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-semibold transition-all ${
                  isActive 
                    ? 'bg-[#FFC107] text-[#1D0A69] font-bold shadow-xs' 
                    : isPast 
                    ? 'bg-white/10 text-white/90 hover:bg-white/20' 
                    : 'text-white/60 hover:text-white hover:bg-white/10'
                }`}
              >
                <Icon className={`w-3 h-3 ${isActive ? 'text-[#1D0A69]' : 'text-current'}`} />
                <span>{st.label}</span>
              </button>
            );
          })}
        </div>

        {/* Right: Quick Action Controls */}
        <div className="flex items-center gap-2 text-xs">
          <button
            onClick={startStudentDemo}
            className="bg-[#0F4C81] hover:bg-[#15074D] text-white px-2.5 py-1 rounded font-bold transition-colors flex items-center gap-1 text-[11px]"
            title="Start Candidate Experience"
          >
            <span>Student Demo</span>
          </button>

          <button
            onClick={startOfficerDemo}
            className="bg-[#1D0A69] border border-[#FFC107] hover:bg-[#FFC107] hover:text-[#1D0A69] text-[#FFC107] px-2.5 py-1 rounded font-bold transition-colors flex items-center gap-1 text-[11px]"
            title="Jump to Scrutiny Desk"
          >
            <span>Officer Demo</span>
          </button>

          <button
            disabled={isResetting}
            onClick={resetDemo}
            className="bg-[#C85A17] hover:bg-[#A8450D] text-white px-2.5 py-1 rounded font-bold transition-colors flex items-center gap-1 text-[11px]"
            title="Reset to Initial Conflict State"
          >
            <RefreshCw className={`w-3 h-3 ${isResetting ? 'animate-spin' : ''}`} />
            <span>{isResetting ? 'Resetting...' : 'Reset Demo'}</span>
          </button>

          {currentIdx < steps.length - 1 && (
            <button
              onClick={handleNext}
              className="bg-[#198754] hover:bg-[#146c43] text-white px-2.5 py-1 rounded font-bold transition-colors flex items-center gap-1 text-[11px]"
              title="Advance to Next Step"
            >
              <span>Next</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
