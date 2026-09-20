package com.eidss.gateway.auth;

import com.eidss.gateway.common.ApiError;
import com.eidss.gateway.security.JwtService;
import com.eidss.gateway.security.Role;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AuthController {

    private final AuthenticationManager authenticationManager;
    private final JwtService jwtService;

    public AuthController(AuthenticationManager authenticationManager, JwtService jwtService) {
        this.authenticationManager = authenticationManager;
        this.jwtService = jwtService;
    }

    @PostMapping("/auth/login")
    public ResponseEntity<?> login(@RequestBody LoginRequest request) {
        try {
            Authentication authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(request.username(), request.password()));

            String roleName = authentication.getAuthorities().stream()
                    .findFirst()
                    .map(GrantedAuthority::getAuthority)
                    .map(a -> a.replaceFirst("^ROLE_", ""))
                    .orElseThrow(() -> new BadCredentialsException("No role assigned"));

            Role role = Role.valueOf(roleName);
            String token = jwtService.issue(authentication.getName(), role);
            return ResponseEntity.ok(new LoginResponse(token, role.name(), authentication.getName()));
        } catch (BadCredentialsException | IllegalArgumentException ex) {
            ApiError error = ApiError.of(HttpStatus.UNAUTHORIZED.value(), "Unauthorized",
                    "Invalid username or password.", "/auth/login");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(error);
        }
    }
}
