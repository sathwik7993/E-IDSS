package com.eidss.gateway.common;

import java.time.Instant;

/**
 * Uniform JSON error body used everywhere the gateway short-circuits a request
 * (401, 403, 502) instead of proxying it through.
 */
public record ApiError(Instant timestamp, int status, String error, String message, String path) {

    public static ApiError of(int status, String error, String message, String path) {
        return new ApiError(Instant.now(), status, error, message, path);
    }
}
