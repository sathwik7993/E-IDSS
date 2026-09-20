package com.eidss.gateway.proxy;

/** Thrown when the FastAPI backend cannot be reached at all (connection refused/timeout). */
public class BackendUnavailableException extends RuntimeException {

    public BackendUnavailableException(String message, Throwable cause) {
        super(message, cause);
    }
}
