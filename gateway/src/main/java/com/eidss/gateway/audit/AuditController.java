package com.eidss.gateway.audit;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * Read-only access to the audit trail. Restricted to PLANT_MANAGER by SecurityConfig
 * ("/api/audit/**"). Deliberately has no write/delete operations — see
 * {@link AdvisoryAuditRecordStore} for why.
 */
@RestController
public class AuditController {

    private final AuditService auditService;

    public AuditController(AuditService auditService) {
        this.auditService = auditService;
    }

    @GetMapping("/api/audit")
    public List<AuditRecordView> recent(@RequestParam(defaultValue = "100") int limit) {
        return auditService.recent(limit).stream().map(AuditRecordView::from).toList();
    }

    @GetMapping("/api/audit/verify")
    public AuditService.ChainVerification verify() {
        return auditService.verifyChain();
    }
}
