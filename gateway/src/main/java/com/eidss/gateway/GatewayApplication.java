package com.eidss.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * E-IDSS governance gateway.
 *
 * <p>Sits in front of the FastAPI intelligence service and adds the two things that turn a
 * demo into something a plant would actually trust: role-based access control across the
 * Operator / Line Lead / Plant Manager roles, and an immutable, tamper-evident audit trail of
 * every advisory call made through it (the system is advisory and human-in-the-loop, so every
 * recommendation shown to a person and every action taken must be non-repudiable).
 */
@SpringBootApplication
public class GatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
