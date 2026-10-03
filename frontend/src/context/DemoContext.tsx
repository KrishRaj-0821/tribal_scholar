import React, { createContext, useContext, useState } from 'react';

export type DemoStep = 
  | 'home'
  | 'schemes'
  | 'wizard'
  | 'upload_ocr'
  | 'officer_queue'
  | 'workbench'
  | 'applicant_status';

export interface AuditEvent {
  id: string;
  audit_event_id: string;
  field_code: string;
  action: string;
  previous_value: any;
  new_value: any;
  previous_trust: string;
  new_trust: string;
  officer: string;
  role: string;
  timestamp: string;
  reason: string;
}

interface DemoContextType {
  currentStep: DemoStep;
  setCurrentStep: (step: DemoStep) => void;
  // Demo Data State
  applicant: {
    name: string;
    otrNo: string;
    applicationId: string;
    state: string;
    district: string;
    category: string;
    declaredIncome: number;
    institution: string;
    course: string;
    academicYear: string;
  };
  uploadProgress: 'idle' | 'uploading' | 'security_check' | 'clamav_scan' | 'safe' | 'ocr_running' | 'ocr_complete';
  ocrData: {
    certificateNumber: string;
    income: number;
    state: string;
    district: string;
    trustLevel: string;
    confidence: number;
    evidenceText: string;
  };
  conflict: {
    hasConflict: boolean;
    type: string;
    declared: number;
    ocr: number;
    status: 'OPEN' | 'RESOLVED';
  };
  verification: {
    status: 'PENDING' | 'VERIFIED' | 'REJECTED' | 'NEEDS_MORE_EVIDENCE' | 'ESCALATED';
    verifiedValue: number | null;
    trustRank: number;
    officer: string;
    role: string;
    auditEvents: AuditEvent[];
  };
  eligibility: {
    incomeRule: 'PASS' | 'FAIL' | 'NEEDS_REVIEW';
    communityRule: 'PASS' | 'FAIL';
    institutionRule: 'PASS' | 'NEEDS_REVIEW';
    overall: 'ELIGIBLE' | 'NEEDS_REVIEW' | 'REJECTED';
    evaluatedAt: string | null;
  };
  // Actions
  resetDemo: () => Promise<void>;
  startStudentDemo: () => void;
  startOfficerDemo: () => void;
  simulateUploadAndOcr: () => void;
  resolveConflict: (decision: 'USE_DOCUMENT_VALUE' | 'USE_APPLICANT_DECLARATION' | 'NEEDS_MORE_EVIDENCE' | 'ESCALATE', reason?: string) => Promise<void>;
  isResetting: boolean;
  actionSuccessMsg: string | null;
}

const API_BASE = ((import.meta as any).env?.VITE_API_URL) || (typeof window !== 'undefined' && window.location.hostname === 'localhost' ? 'http://localhost:8000' : 'https://backend-production-ba69a.up.railway.app');

const initialAuditEvents: AuditEvent[] = [
  {
    id: 'audit-01',
    audit_event_id: 'audit-8f41e0a2-11ef-42b1-9ca4-773b019da012',
    field_code: 'document_security',
    action: 'SECURITY_CLEARED_CLAMAV',
    previous_value: 'SCANNING',
    new_value: 'SAFE',
    previous_trust: 'SYSTEM (30)',
    new_trust: 'SAFE (30)',
    officer: 'system_clamav_daemon',
    role: 'SECURITY_GATE',
    timestamp: '2026-10-02 09:14:22 UTC',
    reason: 'Zero signature match in ClamAV database. Decompression bounded 700px.'
  },
  {
    id: 'audit-02',
    audit_event_id: 'audit-9a14c331-419b-4e89-8d14-884910cf91a4',
    field_code: 'annual_family_income',
    action: 'OCR_PROVISIONAL_EXTRACTION',
    previous_value: null,
    new_value: '450000',
    previous_trust: 'NONE (0)',
    new_trust: 'OCR_PROVISIONAL (10)',
    officer: 'celery_worker_paddleocr',
    role: 'AI_PIPELINE',
    timestamp: '2026-10-02 09:14:35 UTC',
    reason: 'PaddleOCR 3.7.0 multi-lingual Devanagari detection anchor.'
  },
  {
    id: 'audit-03',
    audit_event_id: 'audit-b291fc89-5502-47a1-8d21-9921ef884911',
    field_code: 'annual_family_income',
    action: 'MATERIAL_CONFLICT_FLAGGED',
    previous_value: 'Declared ₹5,00,000 vs OCR ₹4,50,000',
    new_value: 'MATERIAL_CONFLICT',
    previous_trust: 'APPLICANT_DECLARED (20)',
    new_trust: 'CONFLICT_QUEUE (10)',
    officer: 'system_conflict_detector',
    role: 'SYSTEM',
    timestamp: '2026-10-02 09:14:40 UTC',
    reason: 'Discrepancy (₹50,000) exceeds tolerance threshold. Forwarded to officer queue.'
  }
];

const DemoContext = createContext<DemoContextType | undefined>(undefined);

export const DemoProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentStep, setCurrentStep] = useState<DemoStep>('home');
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  // Applicant State
  const [applicant] = useState({
    name: 'Demo ST Applicant',
    otrNo: 'OTR-2026-ST-884912',
    applicationId: 'APP-2026-001DB3',
    state: 'Madhya Pradesh',
    district: 'Mandla',
    category: 'Scheduled Tribe (ST)',
    declaredIncome: 500000,
    institution: 'Synthetic Demo University (IIT Indore, AISHE: U-0570)',
    course: 'Postgraduate (M.Tech Computer Science & Engineering)',
    academicYear: '2026-27'
  });

  // Upload & OCR Progress State
  const [uploadProgress, setUploadProgress] = useState<'idle' | 'uploading' | 'security_check' | 'clamav_scan' | 'safe' | 'ocr_running' | 'ocr_complete'>('idle');

  const [ocrData] = useState({
    certificateNumber: 'TEST-2026-001',
    income: 450000,
    state: 'MADHYA PRADESH',
    district: 'MANDLA',
    trustLevel: 'OCR_PROVISIONAL (Rank 10)',
    confidence: 0.94,
    evidenceText: 'वार्षिक पारिवारिक आय: 450000 रुपये (रुपये चार लाख पचास हजार मात्र)'
  });

  // Conflict State
  const [conflict, setConflict] = useState({
    hasConflict: true,
    type: 'MATERIAL_CONFLICT',
    declared: 500000,
    ocr: 450000,
    status: 'OPEN' as 'OPEN' | 'RESOLVED'
  });

  // Verification State
  const [verification, setVerification] = useState<{
    status: 'PENDING' | 'VERIFIED' | 'REJECTED' | 'NEEDS_MORE_EVIDENCE' | 'ESCALATED';
    verifiedValue: number | null;
    trustRank: number;
    officer: string;
    role: string;
    auditEvents: AuditEvent[];
  }>({
    status: 'PENDING',
    verifiedValue: null,
    trustRank: 10,
    officer: 'Shri S. K. Mahapatra',
    role: 'SCRUTINY_OFFICER (Mandla Zone)',
    auditEvents: initialAuditEvents
  });

  // Eligibility Evaluation State
  const [eligibility, setEligibility] = useState<{
    incomeRule: 'PASS' | 'FAIL' | 'NEEDS_REVIEW';
    communityRule: 'PASS' | 'FAIL';
    institutionRule: 'PASS' | 'NEEDS_REVIEW';
    overall: 'ELIGIBLE' | 'NEEDS_REVIEW' | 'REJECTED';
    evaluatedAt: string | null;
  }>({
    incomeRule: 'NEEDS_REVIEW',
    communityRule: 'PASS',
    institutionRule: 'NEEDS_REVIEW',
    overall: 'NEEDS_REVIEW',
    evaluatedAt: '2026-10-02 09:15:00 UTC'
  });

  // Action: Reset Demo
  const resetDemo = async () => {
    setIsResetting(true);
    setActionSuccessMsg("Resetting demonstration scenario to initial state...");

    try {
      // 1. Attempt to hit the real backend demo reset API
      const response = await fetch(`${API_BASE}/api/v1/verification/demo/reset/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (response.ok) {
        console.log("Backend demo scenario reset successfully.");
      }
    } catch (err) {
      console.warn("Backend reset API unavailable or offline, resetting client state locally:", err);
    }

    // 2. Restore exact statutory initial state
    setUploadProgress('idle');
    setConflict({
      hasConflict: true,
      type: 'MATERIAL_CONFLICT',
      declared: 500000,
      ocr: 450000,
      status: 'OPEN'
    });
    setVerification({
      status: 'PENDING',
      verifiedValue: null,
      trustRank: 10,
      officer: 'Shri S. K. Mahapatra',
      role: 'SCRUTINY_OFFICER (Mandla Zone)',
      auditEvents: initialAuditEvents
    });
    setEligibility({
      incomeRule: 'NEEDS_REVIEW',
      communityRule: 'PASS',
      institutionRule: 'NEEDS_REVIEW',
      overall: 'NEEDS_REVIEW',
      evaluatedAt: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
    });

    setCurrentStep('home');
    setIsResetting(false);
    setActionSuccessMsg("✓ Demo scenario reset: Income = ₹5,00,000 | Certificate = ₹4,50,000 | Conflict = MATERIAL_CONFLICT (Pending Review)");
    setTimeout(() => setActionSuccessMsg(null), 5000);
  };

  // Action: Start Student Demo
  const startStudentDemo = () => {
    setCurrentStep('schemes');
  };

  // Action: Start Officer Demo
  const startOfficerDemo = () => {
    setCurrentStep('officer_queue');
  };

  // Action: Simulate Document Upload & Multi-stage Security Scan
  const simulateUploadAndOcr = () => {
    setUploadProgress('uploading');
    setTimeout(() => {
      setUploadProgress('security_check');
      setTimeout(() => {
        setUploadProgress('clamav_scan');
        setTimeout(() => {
          setUploadProgress('safe');
          setTimeout(() => {
            setUploadProgress('ocr_running');
            setTimeout(() => {
              setUploadProgress('ocr_complete');
              setActionSuccessMsg("✓ Document secured, ClamAV passed, and PaddleOCR provisional extraction complete.");
              setTimeout(() => setActionSuccessMsg(null), 4000);
            }, 1200);
          }, 800);
        }, 800);
      }, 700);
    }, 700);
  };

  // Action: Officer Verification / Conflict Resolution
  const resolveConflict = async (decision: 'USE_DOCUMENT_VALUE' | 'USE_APPLICANT_DECLARATION' | 'NEEDS_MORE_EVIDENCE' | 'ESCALATE', customReason?: string) => {
    let chosenVal = 450000;
    let newStatus: 'VERIFIED' | 'REJECTED' | 'NEEDS_MORE_EVIDENCE' | 'ESCALATED' = 'VERIFIED';
    let defaultReason = "Certificate documentary evidence scrutinised and accepted by officer.";

    if (decision === 'USE_APPLICANT_DECLARATION') {
      chosenVal = 500000;
      defaultReason = "Applicant self-declaration accepted per supplementary gazetted affidavit.";
    } else if (decision === 'NEEDS_MORE_EVIDENCE') {
      newStatus = 'NEEDS_MORE_EVIDENCE';
      defaultReason = "Discrepancy exceeds tolerance threshold; fresh income certificate required.";
    } else if (decision === 'ESCALATE') {
      newStatus = 'ESCALATED';
      defaultReason = "Escalated to District Nodal Officer / Verifying Authority for sanction clarification.";
    }

    const reason = customReason || defaultReason;
    const auditUuid = 'audit-' + crypto.randomUUID();

    // Call real backend conflict resolution if available
    try {
      await fetch(`${API_BASE}/api/v1/verification/demo/status/`);
    } catch (e) {
      console.warn("Backend call skipped; using client simulation.", e);
    }

    const newEvent: AuditEvent = {
      id: `audit-${Date.now()}`,
      audit_event_id: auditUuid,
      field_code: 'annual_family_income',
      action: decision === 'USE_DOCUMENT_VALUE' ? 'FIELD_VERIFIED_DOCUMENT_VALUE' : (decision === 'USE_APPLICANT_DECLARATION' ? 'FIELD_VERIFIED_DECLARATION' : 'DEFICIENCY_RAISED'),
      previous_value: `Declared: ₹5,00,000 (Rank 20) vs OCR: ₹4,50,000 (Rank 10)`,
      new_value: newStatus === 'VERIFIED' ? `₹${chosenVal.toLocaleString('en-IN')} (OFFICER_VERIFIED)` : newStatus,
      previous_trust: 'OCR_PROVISIONAL (10)',
      new_trust: newStatus === 'VERIFIED' ? 'OFFICER_VERIFIED (60)' : 'NEEDS_REVIEW (20)',
      officer: 'Shri S. K. Mahapatra',
      role: 'SCRUTINY_OFFICER (Mandla Zone)',
      timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
      reason: reason
    };

    setConflict(prev => ({
      ...prev,
      status: 'RESOLVED'
    }));

    setVerification(prev => ({
      ...prev,
      status: newStatus,
      verifiedValue: newStatus === 'VERIFIED' ? chosenVal : null,
      trustRank: newStatus === 'VERIFIED' ? 60 : 20,
      auditEvents: [newEvent, ...prev.auditEvents]
    }));

    // Trigger deterministic rule engine reevaluation
    if (newStatus === 'VERIFIED') {
      setEligibility({
        incomeRule: 'PASS', // 450,000 <= 600,000
        communityRule: 'PASS',
        institutionRule: 'NEEDS_REVIEW', // Institute bonafide pending
        overall: 'NEEDS_REVIEW', // Awaiting institutional sanction
        evaluatedAt: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
      });
      setActionSuccessMsg(`✓ Evidence verified by officer: ₹${chosenVal.toLocaleString('en-IN')}. Trust promoted to OFFICER_VERIFIED (Rank 60). Deterministic eligibility engine re-evaluated!`);
    } else {
      setActionSuccessMsg(`Status updated to ${newStatus}. Deficiency notice issued to applicant.`);
    }

    setTimeout(() => setActionSuccessMsg(null), 5000);
  };

  return (
    <DemoContext.Provider
      value={{
        currentStep,
        setCurrentStep,
        applicant,
        uploadProgress,
        ocrData,
        conflict,
        verification,
        eligibility,
        resetDemo,
        startStudentDemo,
        startOfficerDemo,
        simulateUploadAndOcr,
        resolveConflict,
        isResetting,
        actionSuccessMsg
      }}
    >
      {children}
    </DemoContext.Provider>
  );
};

export const useDemo = () => {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error('useDemo must be used within a DemoProvider');
  }
  return context;
};
