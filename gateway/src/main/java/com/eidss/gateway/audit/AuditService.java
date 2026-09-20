package com.eidss.gateway.audit;

import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;

@Service
public class AuditService {

    private final AdvisoryAuditRecordStore store;

    public AuditService(AdvisoryAuditRecordStore store) {
        this.store = store;
    }

    /** Records one proxied /api/** call. Always an append (insert); see AdvisoryAuditRecordStore. */
    public void recordProxyCall(String username, String role, String httpMethod, String path,
                                 int responseStatus, long latencyMs, byte[] responseBody) {
        String hash = sha256Hex(responseBody == null ? new byte[0] : responseBody);
        AdvisoryAuditRecord record = new AdvisoryAuditRecord(
                Instant.now(), username, role, httpMethod, path, responseStatus, latencyMs, hash);
        store.append(record);
    }

    public List<AdvisoryAuditRecord> recent(int limit) {
        return store.findRecent(limit);
    }

    /**
     * Recomputes a chained hash over every record in insertion (id) order:
     * {@code chain_i = sha256(chain_{i-1} + "|" + id + "|" + timestamp + "|" + username + "|"
     * + role + "|" + httpMethod + "|" + path + "|" + responseStatus + "|" + payloadSha256)},
     * starting from a fixed genesis value. Because each link folds in the previous link's
     * output, changing or removing any historical row (impossible through this app's API, but
     * conceivable via direct DB access) changes every chain hash after it — that's what makes
     * this tamper-evident rather than just a log. "intact" reports whether recomputing the
     * chain succeeded cleanly over a contiguous, monotonically-increasing id sequence with no
     * gaps; there is no separately-stored ledger to compare against in this hackathon build; see
     * the README-level note in AuditController for that caveat.
     */
    public ChainVerification verifyChain() {
        List<AdvisoryAuditRecord> records = store.findAllOrderedById();
        String chain = "GENESIS";
        long expectedId = -1;
        boolean contiguous = true;

        for (AdvisoryAuditRecord record : records) {
            if (expectedId != -1 && record.getId() != expectedId + 1) {
                contiguous = false;
            }
            expectedId = record.getId();

            String input = chain + "|" + record.getId() + "|" + record.getTimestamp() + "|"
                    + record.getUsername() + "|" + record.getRole() + "|" + record.getHttpMethod() + "|"
                    + record.getPath() + "|" + record.getResponseStatus() + "|" + record.getPayloadSha256();
            chain = sha256Hex(input.getBytes(StandardCharsets.UTF_8));
        }

        return new ChainVerification(records.size(), chain, contiguous);
    }

    public static String sha256Hex(byte[] data) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(data);
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }

    public record ChainVerification(int recordCount, String chainHash, boolean intact) {
    }
}
