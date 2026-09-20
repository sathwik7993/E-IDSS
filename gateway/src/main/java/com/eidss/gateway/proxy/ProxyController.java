package com.eidss.gateway.proxy;

import com.eidss.gateway.audit.AuditService;
import com.eidss.gateway.common.ApiError;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;

/**
 * Single fan-out point for every /api/** call the console makes. Forwards method, body, query
 * string and content-type to the FastAPI backend and returns its response verbatim (including
 * binary-safe multipart handling for image upload on /api/inspect). Access control itself is
 * enforced declaratively in SecurityConfig, before a request ever reaches here — this
 * controller's own job is purely proxy + audit.
 *
 * <p>More specific controllers (AuditController's "/api/audit" and "/api/audit/verify") take
 * precedence over this "/api/**" wildcard mapping automatically, per Spring MVC's handler
 * mapping specificity rules, so audit reads are served locally rather than proxied.
 */
@RestController
public class ProxyController {

    private final BackendProxyClient backendProxyClient;
    private final AuditService auditService;
    private final ObjectMapper objectMapper;

    public ProxyController(BackendProxyClient backendProxyClient, AuditService auditService,
                            ObjectMapper objectMapper) {
        this.backendProxyClient = backendProxyClient;
        this.auditService = auditService;
        this.objectMapper = objectMapper;
    }

    @RequestMapping("/api/**")
    public ResponseEntity<byte[]> proxy(HttpServletRequest request) {
        long start = System.currentTimeMillis();
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        String username = authentication != null ? authentication.getName() : "anonymous";
        String role = extractRole(authentication);
        String method = request.getMethod();
        String path = request.getRequestURI();

        try {
            ProxyResponse response = backendProxyClient.forward(request);
            long latencyMs = System.currentTimeMillis() - start;

            auditService.recordProxyCall(username, role, method, path, response.status(), latencyMs,
                    response.body());

            HttpHeaders headers = new HttpHeaders();
            if (response.contentType() != null) {
                headers.set(HttpHeaders.CONTENT_TYPE, response.contentType());
            }
            return new ResponseEntity<>(response.body(), headers, HttpStatus.valueOf(response.status()));
        } catch (BackendUnavailableException ex) {
            long latencyMs = System.currentTimeMillis() - start;
            byte[] body = toJsonBytes(ApiError.of(502, "Bad Gateway",
                    "The E-IDSS backend service is unreachable at the configured URL. "
                            + "Confirm it is running and eidss.backend.url/BACKEND_URL is correct.",
                    path));

            auditService.recordProxyCall(username, role, method, path, 502, latencyMs, body);

            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body);
        }
    }

    private String extractRole(Authentication authentication) {
        if (authentication == null) {
            return "NONE";
        }
        return authentication.getAuthorities().stream()
                .findFirst()
                .map(GrantedAuthority::getAuthority)
                .map(a -> a.replaceFirst("^ROLE_", ""))
                .orElse("NONE");
    }

    private byte[] toJsonBytes(ApiError error) {
        try {
            return objectMapper.writeValueAsBytes(error);
        } catch (JsonProcessingException e) {
            return ("{\"error\":\"Bad Gateway\"}").getBytes(StandardCharsets.UTF_8);
        }
    }
}
