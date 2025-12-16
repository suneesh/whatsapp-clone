import { useState, useEffect } from 'react';
import QRCode from 'qrcode';
import { apiFetch } from '../utils/api';

interface FingerprintModalProps {
  currentUserId: string;
  currentUserFingerprint: string;
  otherUserId: string;
  otherUserFingerprint?: string;
  otherUsername: string;
  initiallyVerified?: boolean;
  onClose: () => void;
}

function formatFingerprint(value: string): string {
  // Format as 12 groups of 5 characters (60 chars total)
  return value
    .replace(/\s+/g, '')
    .match(/.{1,5}/g)
    ?.join(' ')
    .trim() ?? value;
}

function FingerprintModal({
  currentUserId,
  currentUserFingerprint,
  otherUserId,
  otherUserFingerprint,
  otherUsername,
  initiallyVerified = false,
  onClose,
}: FingerprintModalProps) {
  const [isVerified, setIsVerified] = useState(initiallyVerified);
  const [qrCodeUrl, setQrCodeUrl] = useState<string>('');
  const [showMyFingerprint, setShowMyFingerprint] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Generate QR code for other user's fingerprint
    if (otherUserFingerprint) {
      QRCode.toDataURL(otherUserFingerprint, {
        width: 200,
        margin: 2,
        color: {
          dark: '#000000',
          light: '#ffffff',
        },
      })
        .then((url) => setQrCodeUrl(url))
        .catch((err) => console.error('Failed to generate QR code:', err));
    }
  }, [otherUserFingerprint]);

  const handleVerify = async () => {
    if (!otherUserFingerprint) return;

    setLoading(true);
    try {
      const response = await apiFetch('/api/verify-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${currentUserId}`,
        },
        body: JSON.stringify({
          verifiedUserId: otherUserId,
          verifiedFingerprint: otherUserFingerprint,
          verificationMethod: 'manual',
        }),
      });

      if (response.ok) {
        setIsVerified(true);
      } else {
        const error = await response.json();
        console.error('Verification failed:', error);
        alert('Failed to save verification: ' + (error.error || 'Unknown error'));
      }
    } catch (err) {
      console.error('Verification request failed:', err);
      alert('Failed to verify key');
    } finally {
      setLoading(false);
    }
  };

  const handleUnverify = async () => {
    setLoading(true);
    try {
      const response = await apiFetch(`/api/verify-key/${otherUserId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${currentUserId}`,
        },
      });

      if (response.ok) {
        setIsVerified(false);
      } else {
        const error = await response.json();
        console.error('Unverify failed:', error);
        alert('Failed to remove verification: ' + (error.error || 'Unknown error'));
      }
    } catch (err) {
      console.error('Unverify request failed:', err);
      alert('Failed to unverify key');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content fingerprint-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🔐 Encryption Verification</h2>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          <div className="verification-tabs">
            <button
              className={!showMyFingerprint ? 'tab-active' : ''}
              onClick={() => setShowMyFingerprint(false)}
            >
              {otherUsername}
            </button>
            <button
              className={showMyFingerprint ? 'tab-active' : ''}
              onClick={() => setShowMyFingerprint(true)}
            >
              My Fingerprint
            </button>
          </div>

          {showMyFingerprint ? (
            <div className="fingerprint-section">
              <p className="fingerprint-desc">
                This is your encryption fingerprint. Share this with {otherUsername} to allow them to verify you.
              </p>
              <div className="fingerprint-display">
                <code className="fingerprint-code">{formatFingerprint(currentUserFingerprint)}</code>
              </div>
            </div>
          ) : (
            <div className="fingerprint-section">
              {otherUserFingerprint ? (
                <>
                  <p className="fingerprint-desc">
                    Compare this fingerprint with {otherUsername} through a trusted channel (phone call, in person, etc.) to verify their identity.
                  </p>

                  <div className="fingerprint-display">
                    <code className="fingerprint-code">{formatFingerprint(otherUserFingerprint)}</code>
                  </div>

                  {qrCodeUrl && (
                    <div className="qr-code-container">
                      <p className="qr-code-label">QR Code:</p>
                      <img src={qrCodeUrl} alt="QR Code" className="qr-code" />
                      <p className="qr-code-note">Scan this to compare fingerprints</p>
                    </div>
                  )}

                  <div className="verification-status">
                    {isVerified ? (
                      <>
                        <div className="verified-badge">
                          ✓ Verified
                        </div>
                        <p className="verification-note">
                          You have verified this contact's encryption key.
                        </p>
                        <button
                          className="btn-unverify"
                          onClick={handleUnverify}
                          disabled={loading}
                        >
                          Remove Verification
                        </button>
                      </>
                    ) : (
                      <>
                        <p className="verification-note warning">
                          ⚠️ Not verified yet
                        </p>
                        <button
                          className="btn-verify"
                          onClick={handleVerify}
                          disabled={loading}
                        >
                          Mark as Verified
                        </button>
                      </>
                    )}
                  </div>
                </>
              ) : (
                <div className="fingerprint-loading">
                  <p>Establishing encrypted session...</p>
                  <p className="loading-note">The fingerprint will appear once the session is ready.</p>
                </div>
              )}
            </div>
          )}

          <div className="security-info">
            <h3>🛡️ What is this?</h3>
            <p>
              Encryption fingerprints (also called "Safety Numbers") help you verify that your conversation is private and hasn't been intercepted.
            </p>
            <p>
              <strong>To verify:</strong>
            </p>
            <ol>
              <li>Contact {otherUsername} through a trusted channel</li>
              <li>Compare the fingerprint above with theirs</li>
              <li>If they match, click "Mark as Verified"</li>
            </ol>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-modal btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default FingerprintModal;
