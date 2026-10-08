import React from 'react';
import VerificationWorkbench from '../../VerificationWorkbench';

interface VerificationWorkbenchViewProps {
  applicationId?: string;
  onBackToQueue: () => void;
}

export const VerificationWorkbenchView: React.FC<VerificationWorkbenchViewProps> = ({
  applicationId,
  onBackToQueue
}) => {
  return (
    <div className="gov-container py-4 pb-12">
      <VerificationWorkbench
        applicationId={applicationId}
        onBackToQueue={onBackToQueue}
      />
    </div>
  );
};
