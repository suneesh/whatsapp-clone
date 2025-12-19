import { useCallback, useEffect, useState } from 'react';
import { KeyManager, MAX_UPLOAD_PREKEYS, ONE_TIME_PREKEY_TARGET, SIGNED_PREKEY_TTL_MS } from '../crypto/KeyManager';
import { PrekeyBundlePayload } from '../crypto/types';
import { SessionManager } from '../crypto/SessionManager';
import { StoredSessionRecord } from '../storage/KeyStorage';
import { apiFetch } from '../utils/api';
import { SerializedEncryptedMessage } from '../crypto/RatchetEngine';

interface UseE2EEResult {
  ready: boolean;
  initializing: boolean;
  fingerprint: string | null;
  error: string | null;
  ensureSession: (peerId: string) => Promise<void>;
  sessions: Record<string, SessionViewState>;
  encryptMessage: (peerId: string, plaintext: string) => Promise<SerializedEncryptedMessage>;
  decryptMessage: (peerId: string, encrypted: SerializedEncryptedMessage) => Promise<string>;
  resetE2EE: () => Promise<void>;
}

export type SessionViewStatus = 'idle' | 'establishing' | 'ready' | 'error';

export interface SessionViewState {
  status: SessionViewStatus;
  fingerprint?: string;
  updatedAt: number;
  error: string | null;
}

interface PrekeyStatusResponse {
  oneTimePrekeyCount: number;
  signedPrekeyKeyId: number | null;
  signedPrekeyCreatedAt: number | null;
}

const SERVER_PREKEY_MINIMUM = 20;
const STATUS_POLL_INTERVAL_MS = 5 * 60 * 1000;

async function uploadBundle(userId: string, bundle: PrekeyBundlePayload): Promise<void> {
  const response = await apiFetch('/api/users/prekeys', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${userId}`,
    },
    body: JSON.stringify(bundle),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || 'Failed to upload prekey bundle');
  }
}

async function fetchPrekeyStatus(userId: string): Promise<PrekeyStatusResponse> {
  const response = await apiFetch('/api/users/prekeys/status', {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${userId}`,
    },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || 'Failed to fetch prekey status');
  }

  const data = (await response.json()) as PrekeyStatusResponse;
  return {
    oneTimePrekeyCount: data.oneTimePrekeyCount ?? 0,
    signedPrekeyKeyId: data.signedPrekeyKeyId ?? null,
    signedPrekeyCreatedAt: data.signedPrekeyCreatedAt ?? null,
  };
}

export function useE2EE(userId: string | undefined): UseE2EEResult {
  const [manager, setManager] = useState<KeyManager | null>(null);
  const [initializing, setInitializing] = useState(false);
  const [ready, setReady] = useState(false);
  const [fingerprint, setFingerprint] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionManager, setSessionManager] = useState<SessionManager | null>(null);
  const [sessions, setSessions] = useState<Record<string, SessionViewState>>({});

  const syncPrekeys = useCallback(
    async (km: KeyManager) => {
      const bundle = await km.getPendingBundle();
      if (!bundle) {
        return;
      }

      const hasSignedPrekey = bundle.signedPrekey !== null;
      const hasOneTimePrekeys = bundle.oneTimePrekeys.length > 0;
      if (!hasSignedPrekey && !hasOneTimePrekeys) {
        return;
      }

      if (!userId) {
        return;
      }

      await uploadBundle(userId, bundle);
      await km.markBundleUploaded(bundle);
    },
    [userId]
  );

  const sessionRecordToView = useCallback((record: StoredSessionRecord): SessionViewState => {
    const baseStatus: SessionViewStatus =
      record.status === 'ready'
        ? 'ready'
        : record.status === 'error'
        ? 'error'
        : 'establishing';
    return {
      status: baseStatus,
      fingerprint: record.remoteFingerprint,
      updatedAt: record.updatedAt,
      error: record.lastError ?? null,
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (!userId) {
        setManager(null);
        setFingerprint(null);
        setReady(false);
        return;
      }

      setInitializing(true);
      const km = new KeyManager(userId);
      try {
        await km.initialize();
        await syncPrekeys(km);
        const userFingerprint = await km.getFingerprint();
        if (cancelled) {
          return;
        }
        setManager(km);
        setFingerprint(userFingerprint);
        setReady(true);
        setError(null);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        console.error('[E2EE] Initialization failed:', errorMsg, err);
        console.warn('[E2EE] Falling back to unencrypted mode');
        if (!cancelled) {
          // Set ready to true anyway - allow app to work without E2EE
          setReady(true);
          setError(null);
        }
      } finally {
        if (!cancelled) {
          setInitializing(false);
        }
      }
    }

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, [userId, syncPrekeys]);

  useEffect(() => {
    let cancelled = false;
    if (!manager || !userId) {
      setSessionManager(null);
      setSessions({});
      return () => {
        cancelled = true;
      };
    }

    const sm = new SessionManager(userId, manager);
    setSessionManager(sm);
    sm.listSessions().then((records) => {
      if (cancelled) {
        return;
      }
      const mapped: Record<string, SessionViewState> = {};
      records.forEach((record) => {
        mapped[record.peerId] = sessionRecordToView(record);
      });
      setSessions(mapped);
    });

    return () => {
      cancelled = true;
    };
  }, [manager, userId, sessionRecordToView]);

  const ensureSession = useCallback(
    async (peerId: string) => {
      if (!sessionManager || !peerId || !userId || peerId === userId) {
        return;
      }
      setSessions((prev) => ({
        ...prev,
        [peerId]: {
          status: 'establishing',
          fingerprint: prev[peerId]?.fingerprint,
          updatedAt: Date.now(),
          error: null,
        },
      }));
      try {
        const record = await sessionManager.ensureSession(peerId);
        setSessions((prev) => ({
          ...prev,
          [peerId]: {
            status: 'ready',
            fingerprint: record.remoteFingerprint,
            updatedAt: record.updatedAt,
            error: null,
          },
        }));
      } catch (err) {
        setSessions((prev) => ({
          ...prev,
          [peerId]: {
            status: 'error',
            fingerprint: prev[peerId]?.fingerprint,
            updatedAt: Date.now(),
            error: (err as Error).message,
          },
        }));
        throw err;
      }
    },
    [sessionManager, userId]
  );

  const encryptMessage = useCallback(
    async (peerId: string, plaintext: string): Promise<SerializedEncryptedMessage> => {
      if (!sessionManager) {
        throw new Error('E2EE not initialized');
      }
      return await sessionManager.encryptMessage(peerId, plaintext);
    },
    [sessionManager]
  );

  const decryptMessage = useCallback(
    async (peerId: string, encrypted: SerializedEncryptedMessage): Promise<string> => {
      if (!sessionManager) {
        throw new Error('E2EE not initialized');
      }
      return await sessionManager.decryptMessage(peerId, encrypted);
    },
    [sessionManager]
  );

  useEffect(() => {
    if (!manager || !userId || typeof window === 'undefined') {
      return;
    }

    let cancelled = false;
    let intervalId: number | undefined;

    const evaluatePrekeyStatus = async () => {
      try {
        const status = await fetchPrekeyStatus(userId);
        let stagedNewMaterial = false;

        const deficit = ONE_TIME_PREKEY_TARGET - status.oneTimePrekeyCount;
        if (status.oneTimePrekeyCount < SERVER_PREKEY_MINIMUM && deficit > 0) {
          const batchSize = Math.min(deficit, MAX_UPLOAD_PREKEYS);
          await manager.queueOneTimePrekeys(batchSize);
          stagedNewMaterial = true;
        }

        const needsSignedPrekey = !status.signedPrekeyCreatedAt
          || Date.now() - status.signedPrekeyCreatedAt > SIGNED_PREKEY_TTL_MS;
        if (needsSignedPrekey) {
          await manager.rotateSignedPrekey();
          stagedNewMaterial = true;
        }

        if (stagedNewMaterial) {
          await syncPrekeys(manager);
        }
      } catch (err) {
        if (!cancelled) {
          console.warn('[E2EE] Prekey status check failed', err);
        }
      }
    };

    // Run immediately then on interval
    evaluatePrekeyStatus();
    intervalId = window.setInterval(evaluatePrekeyStatus, STATUS_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (intervalId) {
        window.clearInterval(intervalId);
      }
    };
  }, [manager, userId, syncPrekeys]);

  const resetE2EE = useCallback(async () => {
    if (!manager || !userId) {
      throw new Error('E2EE not initialized');
    }

    console.log('[useE2EE] Resetting E2EE...');
    setInitializing(true);
    setError(null);

    try {
      // Clear and reinitialize
      await manager.resetE2EE();
      
      // Sync new keys
      await syncPrekeys(manager);
      
      // Get new fingerprint
      const identity = await manager.getIdentityMaterial();
      setFingerprint(identity.fingerprint);
      
      // Recreate session manager
      const sm = new SessionManager(userId, manager);
      setSessionManager(sm);
      
      // Clear session states
      setSessions({});
      
      setReady(true);
      console.log('[useE2EE] Reset complete');
    } catch (err) {
      console.error('[useE2EE] Reset failed:', err);
      setError((err as Error).message);
      throw err;
    } finally {
      setInitializing(false);
    }
  }, [manager, userId, syncPrekeys]);

  return {
    ready,
    initializing,
    fingerprint,
    error,
    ensureSession,
    sessions,
    encryptMessage,
    decryptMessage,
    resetE2EE,
  };
}
