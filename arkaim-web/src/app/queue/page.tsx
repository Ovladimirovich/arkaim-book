'use client';

import { ReviewQueuePanel } from '@/widgets/review-queue/review-queue-panel';
import { ProtectedRoute, RoleGuard } from '@/shared/lib/guards';

export default function QueuePage() {
  return (
    <ProtectedRoute>
      <RoleGuard roles={['admin']}>
        <ReviewQueuePanel />
      </RoleGuard>
    </ProtectedRoute>
  );
}
