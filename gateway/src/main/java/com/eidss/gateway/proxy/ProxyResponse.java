package com.eidss.gateway.proxy;

/** Verbatim response captured from the FastAPI backend: status, raw body bytes, content type. */
public record ProxyResponse(int status, byte[] body, String contentType) {
}
