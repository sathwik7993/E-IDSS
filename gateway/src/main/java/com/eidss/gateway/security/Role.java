package com.eidss.gateway.security;

/**
 * The three operator roles E-IDSS's console supports. Each is a strict superset of the one
 * before it in terms of what it may reach (see SecurityConfig for the exact path grants).
 */
public enum Role {
    OPERATOR,
    LINE_LEAD,
    PLANT_MANAGER;

    public String authority() {
        return "ROLE_" + name();
    }
}
