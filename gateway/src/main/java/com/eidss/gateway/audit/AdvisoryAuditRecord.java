package com.eidss.gateway.audit;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

/**
 * One row per advisory call proxied through the gateway to the FastAPI backend.
 *
 * <p><b>This entity is append-only by design.</b> E-IDSS is explicitly advisory and
 * human-in-the-loop: every recommendation shown to an operator/line lead/plant manager, and
 * every action they take through the console, must be recorded and non-repudiable. A record
 * that could be edited or removed after the fact would defeat that guarantee. Accordingly:
 * <ul>
 *   <li>there is no setter for {@code id} beyond JPA's generated-value assignment on insert;</li>
 *   <li>{@link AdvisoryAuditRecordStore} (the only class allowed to touch persistence for this
 *       entity) exposes only {@code append(...)} and read/query methods — no update, no
 *       delete, anywhere in this codebase;</li>
 *   <li>{@code payloadSha256} lets a caller (or {@code GET /api/audit/verify}) independently
 *       verify that a response body matches what was actually recorded, and the verify
 *       endpoint chains records together so a row can't be silently altered in place without
 *       breaking the chain.</li>
 * </ul>
 */
@Entity
@Table(name = "advisory_audit_record")
public class AdvisoryAuditRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Instant timestamp;

    @Column(nullable = false)
    private String username;

    @Column(nullable = false)
    private String role;

    @Column(nullable = false)
    private String httpMethod;

    @Column(nullable = false)
    private String path;

    @Column(nullable = false)
    private int responseStatus;

    @Column(nullable = false)
    private long latencyMs;

    @Column(nullable = false, length = 64)
    private String payloadSha256;

    protected AdvisoryAuditRecord() {
        // JPA
    }

    public AdvisoryAuditRecord(Instant timestamp, String username, String role, String httpMethod,
                                String path, int responseStatus, long latencyMs, String payloadSha256) {
        this.timestamp = timestamp;
        this.username = username;
        this.role = role;
        this.httpMethod = httpMethod;
        this.path = path;
        this.responseStatus = responseStatus;
        this.latencyMs = latencyMs;
        this.payloadSha256 = payloadSha256;
    }

    public Long getId() {
        return id;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public String getUsername() {
        return username;
    }

    public String getRole() {
        return role;
    }

    public String getHttpMethod() {
        return httpMethod;
    }

    public String getPath() {
        return path;
    }

    public int getResponseStatus() {
        return responseStatus;
    }

    public long getLatencyMs() {
        return latencyMs;
    }

    public String getPayloadSha256() {
        return payloadSha256;
    }
}
