package com.eidss.gateway.proxy;

import jakarta.servlet.http.HttpServletRequest;

/**
 * Abstraction over "forward this request to the FastAPI backend and give me back its
 * response verbatim". Split out as an interface so tests can stub the backend call without
 * needing FastAPI running (see RestClientBackendProxyClient for the real implementation).
 */
public interface BackendProxyClient {

    ProxyResponse forward(HttpServletRequest request) throws BackendUnavailableException;
}
