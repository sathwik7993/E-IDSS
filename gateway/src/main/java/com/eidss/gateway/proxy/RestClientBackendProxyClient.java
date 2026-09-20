package com.eidss.gateway.proxy;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.Part;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpRequest;
import org.springframework.http.client.ClientHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/**
 * Forwards a request to the FastAPI backend using Spring's synchronous RestClient and returns
 * the response verbatim (status, body bytes, content-type). Handles both ordinary bodies
 * (JSON, form-urlencoded, empty) and multipart/form-data (image upload for /api/inspect),
 * rebuilding the multipart body binary-safely from the incoming servlet Parts.
 */
@Component
public class RestClientBackendProxyClient implements BackendProxyClient {

    private final RestClient restClient;

    public RestClientBackendProxyClient(@Value("${eidss.backend.url}") String backendUrl) {
        this.restClient = RestClient.builder().baseUrl(backendUrl).build();
    }

    @Override
    public ProxyResponse forward(HttpServletRequest request) throws BackendUnavailableException {
        String uriPath = request.getRequestURI();
        String query = request.getQueryString();
        String target = query != null ? uriPath + "?" + query : uriPath;
        HttpMethod method = HttpMethod.valueOf(request.getMethod());
        String contentType = request.getContentType();

        try {
            RestClient.RequestBodySpec spec = restClient.method(method).uri(target);

            if (contentType != null && contentType.toLowerCase(Locale.ROOT).startsWith("multipart/")) {
                MultiValueMap<String, Object> parts = buildMultipartBody(request);
                return spec.body(parts).exchange(this::toProxyResponse, false);
            }

            byte[] raw = request.getInputStream().readAllBytes();
            if (raw.length > 0) {
                if (contentType != null) {
                    spec = spec.header(HttpHeaders.CONTENT_TYPE, contentType);
                }
                return spec.body(raw).exchange(this::toProxyResponse, false);
            }
            return spec.exchange(this::toProxyResponse, false);
        } catch (ResourceAccessException ex) {
            throw new BackendUnavailableException("Backend unreachable: " + target, ex);
        } catch (IOException ex) {
            throw new BackendUnavailableException("Failed reading/forwarding request body for " + target, ex);
        }
    }

    private ProxyResponse toProxyResponse(HttpRequest req, ClientHttpResponse resp) throws IOException {
        byte[] body;
        try (InputStream in = resp.getBody()) {
            body = in.readAllBytes();
        }
        String respContentType = resp.getHeaders().getFirst(HttpHeaders.CONTENT_TYPE);
        return new ProxyResponse(resp.getStatusCode().value(), body, respContentType);
    }

    private MultiValueMap<String, Object> buildMultipartBody(HttpServletRequest request) throws IOException {
        MultiValueMap<String, Object> parts = new LinkedMultiValueMap<>();
        try {
            for (Part part : request.getParts()) {
                byte[] partBytes;
                try (InputStream in = part.getInputStream()) {
                    partBytes = in.readAllBytes();
                }
                String submittedFileName = part.getSubmittedFileName();
                if (submittedFileName != null) {
                    ByteArrayResource resource = new ByteArrayResource(partBytes) {
                        @Override
                        public String getFilename() {
                            return submittedFileName;
                        }
                    };
                    parts.add(part.getName(), resource);
                } else {
                    parts.add(part.getName(), new String(partBytes, StandardCharsets.UTF_8));
                }
            }
        } catch (ServletException ex) {
            throw new IOException("Failed to read multipart request parts", ex);
        }
        return parts;
    }
}
