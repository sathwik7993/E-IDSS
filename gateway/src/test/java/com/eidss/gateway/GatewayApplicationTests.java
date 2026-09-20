package com.eidss.gateway;

import com.eidss.gateway.proxy.BackendProxyClient;
import com.eidss.gateway.proxy.BackendUnavailableException;
import com.eidss.gateway.proxy.ProxyResponse;
import com.eidss.gateway.security.JwtService;
import com.eidss.gateway.security.Role;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.nio.charset.StandardCharsets;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * End-to-end tests against the real Spring context, with the FastAPI backend call stubbed out
 * via a mocked {@link BackendProxyClient} so nothing here needs the actual FastAPI service
 * running.
 */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class GatewayApplicationTests {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private BackendProxyClient backendProxyClient;

    @BeforeEach
    void stubBackend() {
        when(backendProxyClient.forward(any())).thenReturn(
                new ProxyResponse(200, "{\"ok\":true}".getBytes(StandardCharsets.UTF_8),
                        MediaType.APPLICATION_JSON_VALUE));
    }

    private String tokenFor(Role role) {
        return jwtService.issue(role.name().toLowerCase(), role);
    }

    @Test
    void loginWithValidCredentialsReturnsToken() throws Exception {
        mockMvc.perform(post("/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"operator\",\"password\":\"operator123\"}"))
                .andExpect(status().isOk())
                .andExpect(result -> {
                    JsonNode json = objectMapper.readTree(result.getResponse().getContentAsString());
                    org.junit.jupiter.api.Assertions.assertTrue(json.has("token"));
                    org.junit.jupiter.api.Assertions.assertEquals("OPERATOR", json.get("role").asText());
                    org.junit.jupiter.api.Assertions.assertEquals("operator", json.get("username").asText());
                });
    }

    @Test
    void loginWithInvalidCredentialsReturns401() throws Exception {
        mockMvc.perform(post("/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"operator\",\"password\":\"wrong-password\"}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void operatorTokenIsRefusedOnEconomicsEndpoint() throws Exception {
        mockMvc.perform(get("/api/economics/margin")
                        .header("Authorization", "Bearer " + tokenFor(Role.OPERATOR)))
                .andExpect(status().isForbidden());
    }

    @Test
    void plantManagerTokenIsAllowedOnEconomicsEndpoint() throws Exception {
        mockMvc.perform(get("/api/economics/margin")
                        .header("Authorization", "Bearer " + tokenFor(Role.PLANT_MANAGER)))
                .andExpect(status().isOk());
    }

    @Test
    void unauthenticatedRequestToApiIsRejected() throws Exception {
        mockMvc.perform(get("/api/health"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void proxiedCallWritesAuditRecordAndVerifyReportsIntact() throws Exception {
        // Make a proxied call as an operator (allowed endpoint).
        mockMvc.perform(get("/api/metrics")
                        .header("Authorization", "Bearer " + tokenFor(Role.OPERATOR)))
                .andExpect(status().isOk());

        // Only PLANT_MANAGER can read the audit trail.
        String managerToken = tokenFor(Role.PLANT_MANAGER);

        mockMvc.perform(get("/api/audit?limit=10")
                        .header("Authorization", "Bearer " + managerToken))
                .andExpect(status().isOk())
                .andExpect(result -> {
                    JsonNode json = objectMapper.readTree(result.getResponse().getContentAsString());
                    org.junit.jupiter.api.Assertions.assertTrue(json.isArray());
                    org.junit.jupiter.api.Assertions.assertTrue(json.size() >= 1);
                    JsonNode first = json.get(0);
                    org.junit.jupiter.api.Assertions.assertEquals("/api/metrics", first.get("path").asText());
                    org.junit.jupiter.api.Assertions.assertEquals("operator", first.get("username").asText());
                    org.junit.jupiter.api.Assertions.assertTrue(first.get("payloadSha256").asText().length() == 64);
                });

        mockMvc.perform(get("/api/audit/verify")
                        .header("Authorization", "Bearer " + managerToken))
                .andExpect(status().isOk())
                .andExpect(result -> {
                    JsonNode json = objectMapper.readTree(result.getResponse().getContentAsString());
                    org.junit.jupiter.api.Assertions.assertTrue(json.get("recordCount").asInt() >= 1);
                    org.junit.jupiter.api.Assertions.assertTrue(json.get("intact").asBoolean());
                    org.junit.jupiter.api.Assertions.assertTrue(json.get("chainHash").asText().length() == 64);
                });
    }

    @Test
    void backendUnavailableReturns502WithJsonBody() throws Exception {
        when(backendProxyClient.forward(any()))
                .thenThrow(new BackendUnavailableException("down", new java.net.ConnectException("refused")));

        mockMvc.perform(get("/api/metrics")
                        .header("Authorization", "Bearer " + tokenFor(Role.OPERATOR)))
                .andExpect(status().isBadGateway())
                .andExpect(result -> {
                    JsonNode json = objectMapper.readTree(result.getResponse().getContentAsString());
                    org.junit.jupiter.api.Assertions.assertEquals(502, json.get("status").asInt());
                });
    }
}
