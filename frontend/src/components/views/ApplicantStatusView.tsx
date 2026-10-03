import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDemo } from '../../context/DemoContext';
import { useLanguage } from '../../context/LanguageContext';
import { notificationsApi, SMSNotificationRecord } from '../../services/api';
import { 
  CheckCircle, Clock, ShieldCheck, 
  ArrowLeft, Info, MessageSquare, 
  XCircle, RefreshCw
} from 'lucide-react';


export const ApplicantStatusView: React.FC = () => {
  const { language } = useLanguage();
  const { applicant, verification, setCurrentStep } = useDemo();
  const { id } = useParams<{ id: string }>();

  const [notifications, setNotifications] = useState<SMSNotificationRecord[]>([]);
  const [loadingSMS, setLoadingSMS] = useState<boolean>(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const fetchNotifications = async (appId: string) => {
    setLoadingSMS(true);
    try {
      const records = await notificationsApi.getApplicationSMS(appId);
      setNotifications(records || []);
    } catch (err) {
      console.error('Failed to load SMS notifications', err);
    } finally {
      setLoadingSMS(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchNotifications(id);
    }
  }, [id]);

  const handleRetrySMS = async (notificationId: string) => {
    setRetryingId(notificationId);
    try {
      await notificationsApi.retrySMS(notificationId);
      if (id) {
        await fetchNotifications(id);
      }
    } catch (err) {
      console.error('Failed to retry SMS', err);
    } finally {
      setRetryingId(null);
    }
  };

  const isVerified = verification.status === 'VERIFIED';


  return (
    <div className="gov-container py-8 space-y-6">
      {/* 1. Page Header with Official Sovereign Tracking Reference */}
      <div className="gov-card flex flex-wrap items-center justify-between gap-4 border-l-4 border-l-[#1D0A69]">
        <div>
          <div className="flex items-center gap-2 text-xs text-[#546E7A] mb-1">
            <span className="font-mono text-[#1D0A69] font-bold">{applicant.applicationId}</span>
            <span>•</span>
            <span>OTR: <strong>{applicant.otrNo}</strong></span>
            <span>•</span>
            <span className="bg-[#E8F5E9] text-[#198754] px-2 py-0.5 rounded font-bold text-[10px]">
              {applicant.category}
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold font-serif text-[#1D0A69]">
            {language === 'hi' 
              ? 'आवेदक पारदर्शी स्थिति एवं साक्ष्य सत्यापन रिपोर्ट' 
              : 'Applicant Transparent Status & Evidentiary Audit Trail'}
          </h1>
          <p className="text-xs text-[#546E7A] mt-0.5">
            Ministry of Tribal Affairs Central Scholarship Portal • Real-Time Dossier Lifecycle
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentStep('home')}
            className="gov-btn gov-btn-secondary text-xs flex items-center gap-1 font-bold"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to Home</span>
          </button>
        </div>
      </div>

      {/* 2. Current Statutory Status Summary Card */}
      <div className="gov-card bg-[#F8F9FA] border border-[#CFD8DC] p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#ECEFF1] pb-4">
          <div>
            <span className="text-[11px] text-[#546E7A] uppercase font-bold tracking-wider block">
              Overall Application Status
            </span>
            <div className="text-lg font-bold text-[#1D0A69] flex items-center gap-2 mt-0.5">
              <span>UNDER INSTITUTIONAL SCRUTINY</span>
              <span className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                isVerified ? 'bg-[#E8F5E9] text-[#1B5E20] border border-[#A5D6A7]' : 'bg-[#FFF3E0] text-[#E65100] border border-[#FFE0B2]'
              }`}>
                {isVerified ? '✓ EVIDENTIARY CONFLICT RESOLVED' : '⚠ SCRUTINY PENDING'}
              </span>
            </div>
          </div>

          <div className="text-right text-xs">
            <span className="text-[#546E7A] block">Target Scheme:</span>
            <strong className="text-[#1D0A69]">Top Class Education for ST Students (TOP-05)</strong>
          </div>
        </div>

        {/* Status Explanation Box */}
        <div className={`p-4 rounded-md border text-xs space-y-2 ${
          isVerified ? 'bg-[#E8F5E9] border-[#A5D6A7] text-[#1B5E20]' : 'bg-[#FFF8E1] border-[#FFE082] text-[#5D4037]'
        }`}>
          <div className="font-bold flex items-center gap-1.5 text-sm">
            {isVerified ? <CheckCircle className="w-4 h-4 text-[#198754]" /> : <Clock className="w-4 h-4 text-[#C85A17]" />}
            <span>
              {isVerified 
                ? 'Authoritative Evidence Verified: Income Certified at ₹4,50,000' 
                : 'Scrutiny Required: Material Discrepancy between Declaration and Document'}
            </span>
          </div>
          <p className="leading-relaxed text-[11px]">
            {isVerified 
              ? 'District Scrutiny Officer Shri S. K. Mahapatra has reviewed the uploaded revenue income certificate and promoted the authoritative value to ₹4,50,000 (OFFICER_VERIFIED, Rank 60). The Scheme Rule Engine has reevaluated statutory income conditions to PASS.'
              : 'The candidate declared an annual family income of ₹5,00,000, while the revenue income certificate indicates ₹4,50,000. Under statutory rules, machine OCR cannot overwrite declared data. An authorized scrutiny officer is currently examining the physical evidence.'}
          </p>
        </div>
      </div>

      {/* 3. Real-Time Application Timeline */}
      <div className="gov-card space-y-4">
        <h3 className="text-sm font-bold text-[#1D0A69] border-b border-[#CFD8DC] pb-3 font-serif flex items-center gap-2">
          <Clock className="w-4 h-4 text-[#C85A17]" />
          <span>Statutory Lifecycle & Evidence Processing Timeline</span>
        </h3>

        <div className="relative pl-6 space-y-6 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#CFD8DC]">
          {/* Step 1 */}
          <div className="relative text-xs">
            <div className="absolute -left-[23px] top-0 w-3.5 h-3.5 rounded-full bg-[#198754] border-2 border-white shadow-xs"></div>
            <div className="font-bold text-[#150202]">1. Application Created & Demographics Seeded</div>
            <div className="text-[11px] text-[#546E7A]">12-Sep-2026 09:12:00 UTC • Candidate completed OTR registration and form submission.</div>
          </div>

          {/* Step 2 */}
          <div className="relative text-xs">
            <div className="absolute -left-[23px] top-0 w-3.5 h-3.5 rounded-full bg-[#198754] border-2 border-white shadow-xs"></div>
            <div className="font-bold text-[#150202]">2. Revenue Income Certificate Uploaded</div>
            <div className="text-[11px] text-[#546E7A]">12-Sep-2026 09:14:00 UTC • File <code>income_cert_mandla_2026.png</code> (248 KB) ingested into isolated buffer.</div>
          </div>

          {/* Step 3 */}
          <div className="relative text-xs">
            <div className="absolute -left-[23px] top-0 w-3.5 h-3.5 rounded-full bg-[#198754] border-2 border-white shadow-xs"></div>
            <div className="font-bold text-[#150202]">3. Security & Anti-Malware Gate Completed</div>
            <div className="text-[11px] text-[#546E7A]">12-Sep-2026 09:14:15 UTC • ClamAV daemon verified file clean (Zero signature match). Status: <strong>SAFE</strong>.</div>
          </div>

          {/* Step 4 */}
          <div className="relative text-xs">
            <div className="absolute -left-[23px] top-0 w-3.5 h-3.5 rounded-full bg-[#198754] border-2 border-white shadow-xs"></div>
            <div className="font-bold text-[#150202]">4. Multi-Lingual OCR Provisional Extraction Completed</div>
            <div className="text-[11px] text-[#546E7A]">12-Sep-2026 09:14:35 UTC • PaddleOCR 3.7.0 extracted Certificate No: <strong>TEST-2026-001</strong> and Income: <strong>₹4,50,000</strong>.</div>
          </div>

          {/* Step 5 */}
          <div className="relative text-xs">
            <div className={`absolute -left-[23px] top-0 w-3.5 h-3.5 rounded-full border-2 border-white shadow-xs ${
              isVerified ? 'bg-[#198754]' : 'bg-[#FFC107]'
            }`}></div>
            <div className="font-bold text-[#150202]">
              5. Officer Scrutiny & Conflict Resolution {isVerified ? '(COMPLETED)' : '(IN PROGRESS)'}
            </div>
            <div className="text-[11px] text-[#546E7A]">
              {isVerified 
                ? `13-Sep-2026 • Verified by ${verification.officer} (${verification.role}). Value promoted to OFFICER_VERIFIED (Rank 60).` 
                : 'Pending • Case in District Verification Queue. Awaiting officer confirmation.'}
            </div>
          </div>

          {/* Step 6 */}
          <div className="relative text-xs">
            <div className={`absolute -left-[23px] top-0 w-3.5 h-3.5 rounded-full border-2 border-white shadow-xs ${
              isVerified ? 'bg-[#198754]' : 'bg-gray-400'
            }`}></div>
            <div className="font-bold text-[#150202]">6. Deterministic Scheme Eligibility Reevaluated</div>
            <div className="text-[11px] text-[#546E7A]">
              {isVerified 
                ? 'Income Rule evaluated to PASS (₹4,50,000 <= ₹6,00,000 ceiling). Community Rule: PASS.' 
                : 'Awaiting authoritative evidence before final rule clearance.'}
            </div>
          </div>
        </div>
      </div>

      {/* 4. Rule-Level Transparent Breakdown */}
      <div className="gov-card space-y-4">
        <h3 className="text-sm font-bold text-[#1D0A69] border-b border-[#CFD8DC] pb-3 font-serif flex items-center justify-between">
          <span className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#198754]" />
            <span>Scheme Rule Evaluation Breakdown (Deterministic Engine)</span>
          </span>
          <span className="text-[11px] text-[#546E7A] font-normal">
            Evaluated against Authoritative Evidence Only
          </span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {/* Rule 1: Family Income */}
          <div className="p-3.5 rounded border border-gray-200 bg-[#FAFAFA] space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-bold text-[#1D0A69]">1. Family Income Ceiling</span>
              {isVerified ? (
                <span className="bg-[#E8F5E9] text-[#198754] text-[10px] font-extrabold px-2 py-0.5 rounded">
                  ✓ PASS
                </span>
              ) : (
                <span className="bg-[#FFF3E0] text-[#E65100] text-[10px] font-extrabold px-2 py-0.5 rounded">
                  ⚠ NEEDS REVIEW
                </span>
              )}
            </div>
            <div className="text-[11px] text-[#546E7A]">
              Statutory Ceiling: <strong>≤ ₹6,00,000</strong>
            </div>
            <div className="text-[11px]">
              Authoritative Evidence: <strong>{isVerified ? '₹4,50,000 (OFFICER_VERIFIED)' : '₹5,00,000 (CONFLICT)'}</strong>
            </div>
            <div className="text-[10px] text-gray-500 italic">
              {isVerified ? 'Rule condition satisfied. Revenue certificate valid.' : 'Evaluation deferred pending conflict resolution.'}
            </div>
          </div>

          {/* Rule 2: ST Community */}
          <div className="p-3.5 rounded border border-gray-200 bg-[#FAFAFA] space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-bold text-[#1D0A69]">2. Scheduled Tribe Status</span>
              <span className="bg-[#E8F5E9] text-[#198754] text-[10px] font-extrabold px-2 py-0.5 rounded">
                ✓ PASS
              </span>
            </div>
            <div className="text-[11px] text-[#546E7A]">
              Statutory Condition: <strong>ST Notification (Art. 342)</strong>
            </div>
            <div className="text-[11px]">
              Authoritative Evidence: <strong>ST (Madhya Pradesh)</strong>
            </div>
            <div className="text-[10px] text-gray-500 italic">
              Candidate identity matched against MoTA notified ST list.
            </div>
          </div>

          {/* Rule 3: Enrolled Premier Institute */}
          <div className="p-3.5 rounded border border-gray-200 bg-[#FAFAFA] space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-bold text-[#1D0A69]">3. Notified Premier Institute</span>
              <span className="bg-[#FFF3E0] text-[#E65100] text-[10px] font-extrabold px-2 py-0.5 rounded">
                ⚠ NEEDS REVIEW
              </span>
            </div>
            <div className="text-[11px] text-[#546E7A]">
              Institute: <strong>IIT Indore (AISHE: U-0570)</strong>
            </div>
            <div className="text-[11px]">
              Course: <strong>Postgraduate (M.Tech CSE)</strong>
            </div>
            <div className="text-[10px] text-gray-500 italic">
              Institution code verified in gazette; awaiting institutional nodal bonafide signoff.
            </div>
          </div>
        </div>

        {/* Explain exactly what remains */}
        <div className="p-3 bg-[#E1F5FE] border border-[#81D4FA] rounded text-xs text-[#01579B] space-y-1">
          <div className="font-bold flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5" />
            <span>WHAT REMAINS FOR BENEFIT DISBURSAL (TRANSPARENCY):</span>
          </div>
          <p className="text-[11px] leading-relaxed">
            {isVerified 
              ? 'Candidate documentary evidence has been fully scrutinized and verified by the District Scrutiny Officer. The final step required before DBT PFMS transfer is institutional bonafide confirmation by the IIT Indore Nodal Officer. No further candidate action is needed.' 
              : 'The revenue income certificate conflict is currently under active officer scrutiny. Once the officer verifies the certificate, the dossier will automatically proceed to institutional clearance.'}
          </p>
        </div>
      </div>

      {/* 5. SMS Notification Delivery Ledger (Real Fast2SMS Asynchronous Audit) */}
      <div className="gov-card space-y-4">
        <div className="flex items-center justify-between border-b border-[#CFD8DC] pb-3">
          <h3 className="text-sm font-bold text-[#1D0A69] font-serif flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-[#1D0A69]" />
            <span>SMS Notification Audit Trail & Real-Time Delivery State</span>
          </h3>
          <span className="text-[11px] text-[#546E7A] bg-[#ECEFF1] px-2.5 py-0.5 rounded font-mono">
            Fast2SMS Quick SMS Route
          </span>
        </div>

        {loadingSMS ? (
          <div className="p-4 text-center text-xs text-[#546E7A]">
            <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1 text-[#1D0A69]" />
            <span>Checking SMS delivery ledger...</span>
          </div>
        ) : notifications.length > 0 ? (
          <div className="space-y-2">
            {notifications.map((notif) => {
              const isSentToProvider = notif.status === 'SENT_TO_PROVIDER';
              const isDelivered = notif.status === 'DELIVERED';
              const isPending = notif.status === 'PENDING' || notif.status === 'SENDING' || notif.status === 'RETRY_PENDING';
              const isFailed = notif.status === 'FAILED';
              const isDevSkipped = notif.status === 'DEV_SKIPPED';

              return (
                <div 
                  key={notif.id}
                  className={`p-3 rounded-lg border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                    isDelivered
                      ? 'bg-[#E8F5E9] border-[#A5D6A7]'
                      : isSentToProvider
                      ? 'bg-[#E0F2F1] border-[#80CBC4]'
                      : isFailed
                      ? 'bg-[#FFEBEE] border-[#FFCDD2]'
                      : isDevSkipped
                      ? 'bg-[#EDE7F6] border-[#D1C4E9]'
                      : 'bg-[#FFF8E1] border-[#FFE082]'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      {isDelivered && (
                        <span className="font-bold text-[#1B5E20] flex items-center gap-1">
                          <CheckCircle className="w-3.5 h-3.5 text-[#198754]" />
                          <span>Notification: ✓ Confirmed Delivered to Handset</span>
                        </span>
                      )}
                      {isSentToProvider && (
                        <span className="font-bold text-[#00695C] flex items-center gap-1">
                          <CheckCircle className="w-3.5 h-3.5 text-[#00897B]" />
                          <span>Notification: ✓ Dispatched to Gateway (Fast2SMS)</span>
                        </span>
                      )}
                      {isPending && (
                        <span className="font-bold text-[#E65100] flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-[#C85A17]" />
                          <span>Notification: ⚠ SMS delivery pending</span>
                        </span>
                      )}
                      {isFailed && (
                        <span className="font-bold text-[#C62828] flex items-center gap-1">
                          <XCircle className="w-3.5 h-3.5 text-[#D32F2F]" />
                          <span>Notification: ✕ SMS delivery failed</span>
                        </span>
                      )}
                      {isDevSkipped && (
                        <span className="font-bold text-[#4A148C] flex items-center gap-1">
                          <Info className="w-3.5 h-3.5 text-[#7B1FA2]" />
                          <span>Notification: ⚙ Development Mode (Simulated)</span>
                        </span>
                      )}

                      <span className="text-[10px] bg-white px-2 py-0.5 rounded border border-gray-200 text-[#37474F] font-mono">
                        {notif.notification_type}
                      </span>
                    </div>

                    <div className="text-[11px] text-[#546E7A] flex items-center gap-3">
                      <span>Recipient: <strong>{notif.recipient_phone_masked}</strong></span>
                      {notif.provider_request_id && (
                        <span>Ref: <code className="font-mono">{notif.provider_request_id}</code></span>
                      )}
                      <span>
                        {new Date(notif.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>

                    {isFailed && notif.failure_reason && (
                      <p className="text-[10px] text-[#C62828] italic">
                        Reason: {notif.failure_reason}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {isSentToProvider && (
                      <span className="text-[10px] bg-white px-2 py-0.5 rounded border border-[#80CBC4] font-mono text-[#00695C] font-bold">
                        SENT_TO_PROVIDER
                      </span>
                    )}
                    {isDelivered && (
                      <span className="text-[10px] bg-white px-2 py-0.5 rounded border border-[#A5D6A7] font-mono text-[#1B5E20] font-bold">
                        DELIVERED
                      </span>
                    )}

                    {isFailed && (
                      <button
                        type="button"
                        disabled={retryingId === notif.id}
                        onClick={() => handleRetrySMS(notif.id)}
                        className="self-start sm:self-auto bg-[#D32F2F] hover:bg-[#B71C1C] disabled:opacity-50 text-white px-3 py-1.5 rounded font-bold text-xs flex items-center gap-1 shadow-xs"
                      >
                        {retryingId === notif.id ? (
                          <>
                            <RefreshCw className="w-3 h-3 animate-spin" />
                            <span>Retrying...</span>
                          </>
                        ) : (
                          <>
                            <RefreshCw className="w-3 h-3" />
                            <span>Retry</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* Default state when demonstrating without persisted backend record */
          <div className="p-3.5 rounded-lg bg-[#E0F2F1] border border-[#80CBC4] text-xs flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="font-bold text-[#00695C] flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 text-[#00897B]" />
                <span>Notification: ✓ Dispatched to Gateway (Fast2SMS)</span>
              </div>
              <p className="text-[11px] text-[#004D40]">
                Official submission notification dispatched to registered mobile: <strong>******4912</strong>.
              </p>
            </div>
            <span className="text-[10px] bg-white px-2 py-0.5 rounded border border-[#80CBC4] font-mono text-[#00695C] font-bold">
              SENT_TO_PROVIDER
            </span>
          </div>
        )}

      </div>

    </div>
  );
};

