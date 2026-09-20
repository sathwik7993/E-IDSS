package com.eidss.gateway.audit;

import java.time.Instant;

/** Read-only projection of an audit record for the /api/audit listing endpoint. */
public record AuditRecordView(
        Long id,
        Instant timestamp,
        String username,
        String role,
        String httpMethod,
        String path,
        int responseStatus,
        long latencyMs,
        String payloadSha256) {

    public static AuditRecordView from(AdvisoryAuditRecord record) {
        return new AuditRecordView(
                record.getId(),
                record.getTimestamp(),
                record.getUsername(),
                record.getRole(),
                record.getHttpMethod(),
                record.getPath(),
                record.getResponseStatus(),
                record.getLatencyMs(),
                record.getPayloadSha256());
    }
}
