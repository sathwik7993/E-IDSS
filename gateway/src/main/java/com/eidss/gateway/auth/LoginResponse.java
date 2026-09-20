package com.eidss.gateway.auth;

public record LoginResponse(String token, String role, String username) {
}
